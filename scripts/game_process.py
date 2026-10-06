"""Read-only identity checks for the selected Dungeons copy.

Wine's Windows executable paths can be identical in different bottles. A
process name alone is therefore only a candidate. PID-scoped open-file
metadata ties the candidate to the physical game file and CrossOver bottle.
No file contents, command-line arguments, account data, or raw query output
are recorded. Query failures remain distinguishable from an idle game.
"""
from dataclasses import dataclass
from pathlib import Path
import os
import subprocess

SELECTED = 'MCD2_RUNNING_SELECTED'
SHARED = 'MCD2_RUNNING_SHARED_STEAM'
AMBIGUOUS = 'MCD2_RUNNING_AMBIGUOUS'
MAX_QUERY_BYTES = 2_000_000
MAX_CANDIDATES = 64
GAME_NAMES = {'dungeons-win64-shipping.exe', 'dungeons-wingdk-shipping.exe', 'dungeons.exe'}


class RunningGameError(RuntimeError):
    def __init__(self, marker, exit_code, message):
        super().__init__(message)
        self.marker = marker
        self.exit_code = exit_code


@dataclass(frozen=True)
class ProcessReport:
    selected_pids: tuple = ()
    shared_pids: tuple = ()
    ambiguous: bool = False


def _physical_path(value):
    if not isinstance(value, str) or not value.startswith('/') or any(c in value for c in ('\0', '\r', '\n')):
        return None
    # lsof retains the mapped pathname when a file was unlinked. Treat that as
    # still active instead of allowing replacement of its neighbours.
    if value.endswith(' (deleted)'):
        value = value[:-10]
    try:
        return Path(value).resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def _same_file(path, selected):
    if path == selected:
        return True
    try:
        return os.path.samefile(path, selected)
    except (OSError, ValueError):
        return False


def _within(path, directory):
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _bottle_file(path, bottle):
    try:
        relative = path.relative_to(bottle)
        # Wine can inherit a Mac working directory. A cwd directory under the
        # bottle does not establish that the process belongs to this bottle.
        if path.is_dir():
            return False
        return (len(relative.parts) >= 2 and relative.parts[0] in {'drive_c', 'dosdevices'}) or (
            len(relative.parts) == 1 and relative.parts[0] in {'system.reg', 'user.reg', 'userdef.reg', 'cxbottle.conf'})
    except (ValueError, OSError):
        return False


def _other_bottle_file(path, bottle):
    try:
        relative = path.relative_to(bottle.parent)
        if len(relative.parts) < 2 or relative.parts[0] == bottle.name:
            return False
        return _bottle_file(path, bottle.parent / relative.parts[0])
    except ValueError:
        return False


def _candidate(command):
    normalized = command.casefold().replace('\\', '/')
    name = normalized.rsplit('/', 1)[-1]
    if name in GAME_NAMES:
        return True
    # Protect other Steam games in the same bottle from a setup-triggered
    # Steam restart too. Steam's own helpers live outside steamapps/common.
    return '/steamapps/common/' in normalized and name.endswith('.exe')


def _process_rows(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_QUERY_BYTES:
        return [], True
    rows, seen, uncertain = [], set(), False
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.lstrip().split(None, 1)
        if len(fields) != 2 or not fields[0].isascii() or not fields[0].isdigit():
            uncertain = True
            continue
        pid = int(fields[0])
        command = fields[1].rstrip()
        if pid == 0 and not _candidate(command):
            continue
        if pid <= 0 or pid > 0x7fffffff or pid in seen or not command or any(ord(c) < 32 for c in command):
            uncertain = True
            continue
        seen.add(pid)
        if _candidate(command):
            if len(rows) >= MAX_CANDIDATES:
                uncertain = True
                continue
            rows.append((pid, command))
    return rows, uncertain


def _open_files(text, pid):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_QUERY_BYTES:
        return None
    lines = text.splitlines()
    # -Fpn explicitly requests PID and name fields. Refuse mixed/reused PIDs.
    identities = [line[1:] for line in lines if line.startswith('p')]
    if identities != [str(pid)]:
        return None
    paths = []
    for line in lines:
        if line.startswith('n'):
            path = _physical_path(line[1:])
            if path is not None:
                paths.append(path)
    return paths or None


def inspect_processes(executable, bottle, *, shared_steam=False, run=None):
    """Return confirmed identities and uncertainty, never guessed positives."""
    run = subprocess.run if run is None else run
    executable, bottle = Path(executable).resolve(), Path(bottle).resolve()
    selected, shared, uncertain = [], [], False
    try:
        result = run(['/bin/ps', '-axo', 'pid=,comm='], capture_output=True, text=True,
                     errors='strict', timeout=3, check=False)
        if result.returncode:
            return ProcessReport(ambiguous=True)
        candidates, uncertain = _process_rows(result.stdout)
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        return ProcessReport(ambiguous=True)
    for pid, _command in candidates:
        try:
            result = run(['/usr/sbin/lsof', '-a', '-p', str(pid), '-Fpn'],
                         capture_output=True, text=True, errors='strict', timeout=2, check=False)
            files = _open_files(result.stdout, pid) if result.returncode == 0 else None
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
            files = None
        if files is None:
            uncertain = True
            continue
        if any(_same_file(path, executable) for path in files):
            selected.append(pid)
            continue
        # A running bootstrapper belongs to the same copy and can start its
        # shipping process while setup is replacing files.
        if len(executable.parents) >= 4:
            bootstrapper = executable.parents[3] / 'Dungeons.exe'
            if any(_same_file(path, bootstrapper) for path in files):
                selected.append(pid)
                continue
        if not shared_steam:
            # Physical executable evidence is needed to clear a candidate,
            # rather than treating arbitrary DLL mappings as proof of another
            # copy. Do not mistake an unreadable process for an idle one.
            if not any(_candidate(str(path)) for path in files):
                uncertain = True
            continue
        if any(_bottle_file(path, bottle) for path in files):
            shared.append(pid)
        elif any(_other_bottle_file(path, bottle) for path in files):
            # Explicit evidence for another bottle, despite identical C: paths.
            continue
        else:
            # External Steam libraries still need a bottle identity before a
            # Steam restart. A current directory or basename is insufficient.
            uncertain = True
    return ProcessReport(tuple(selected), tuple(shared), uncertain)


def require_idle(executable, bottle, *, shared_steam=False, ignore_other=False, run=None):
    report = inspect_processes(executable, bottle, shared_steam=shared_steam, run=run)
    if report.selected_pids:
        raise RunningGameError(SELECTED, 20,
            'The selected Minecraft Dungeons II copy is running. Finish and quit the game before replacing its files.')
    if ignore_other:
        # This user-requested retry authorizes continuing past other-game or
        # uncertain metadata warnings. It never overrides selected-file proof.
        return report
    if report.shared_pids:
        raise RunningGameError(SHARED, 21,
            'Another game is running in this CrossOver bottle. Setup restarts its Steam; finish that game first, or explicitly choose to continue.')
    if report.ambiguous:
        raise RunningGameError(AMBIGUOUS, 22,
            'The running-game check could not identify every process. If Minecraft Dungeons II is closed, choose “It isn’t open!” to retry. Steam setup restarts Steam in the selected bottle.')
    return report
