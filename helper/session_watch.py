"""Bounded, native-only observation of a launcher-owned game session.

Never starts Wine to inspect processes. Never closes a pre-existing Steam or
another Windows application. A minimized/hidden game keeps its window ID and
is not treated as closed. No screen recording or accessibility permission.
"""
import argparse
import ctypes as C
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from game_process import _open_files, _bottle_file, _other_bottle_file, _same_file

WINE = '/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine'
HOME = Path.home() / 'Library/Application Support/DungeonsCrossOver'
SYSTEM = {'services.exe', 'winedevice.exe', 'plugplay.exe', 'svchost.exe',
          'explorer.exe', 'rpcss.exe', 'conhost.exe', 'wineboot.exe', 'winewrapper.exe', 'wuauserv.exe'}
STEAM = {'steam.exe', 'steamwebhelper.exe', 'steamservice.exe',
         'gameoverlayui.exe', 'gameoverlayui64.exe', 'steamerrorreporter.exe',
         'steamerrorreporter64.exe', 'crashhandler.exe', 'crashhandler64.exe'}
SHIPPING = {'dungeons-win64-shipping.exe', 'dungeons-wingdk-shipping.exe'}


def run(args):
    return subprocess.run(args, capture_output=True, text=True, errors='strict', timeout=5)


def rows():
    result = run(['/bin/ps', '-axo', 'pid=,lstart=,comm='])
    if result.returncode: raise RuntimeError('process query failed')
    found = {}
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 6)
        if len(fields) != 7: raise RuntimeError('incomplete process query')
        pid = int(fields[0]); command = fields[6]
        found[pid] = (' '.join(fields[1:6]), command,
                      command.replace('\\', '/').rsplit('/', 1)[-1].lower())
    return found


def files(pid):
    result = run(['/usr/sbin/lsof', '-a', '-p', str(pid), '-Fpn'])
    return _open_files(result.stdout, pid) if result.returncode == 0 else None


def bottle_rows(bottle, snapshot):
    """Unknown Windows identities block cleanup; unrelated native apps do not."""
    result = {}
    candidates = [(p, row) for p, row in snapshot.items() if row[2].endswith('.exe')]
    if len(candidates) > 128: return None
    for pid, row in candidates:
        normalized = row[1].lower().replace('\\', '/')
        if row[2] in SYSTEM and re.fullmatch(r'[a-z]:/windows/(system32|syswow64)/[^/]+', normalized):
            # These services often map no bottle files. They never authorize
            # closing an application and are stopped only by the idle-prefix
            # shutdown after every non-service process has been checked.
            continue
        paths = files(pid)
        if paths is None:
            if pid in rows(): return None
            continue
        vendor = Path(WINE).parent.parent / 'lib/wine/x86_64-windows' / row[2]
        if row[2] in SYSTEM and vendor in paths: continue
        if any(_bottle_file(p, bottle) for p in paths): result[pid] = row
        elif not any(_other_bottle_file(p, bottle) for p in paths): return None
    return result


def steam_was_running(bottle):
    # Uncertainty means the user owns Steam, so leave it open after the game.
    try:
        for pid, row in rows().items():
            if row[2] != 'steam.exe': continue
            paths = files(pid)
            if paths is None or any(_bottle_file(p, bottle) for p in paths): return True
        return False
    except (OSError, ValueError, subprocess.SubprocessError): return True


class Windows:
    def __init__(self):
        self.cf = C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.cg = C.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
        ptr = C.c_void_p
        for name, args, result in [
            ('CFStringCreateWithCString', [ptr, C.c_char_p, C.c_uint32], ptr),
            ('CFArrayGetCount', [ptr], C.c_long),
            ('CFArrayGetValueAtIndex', [ptr, C.c_long], ptr),
            ('CFDictionaryGetValue', [ptr, ptr], ptr),
            ('CFNumberGetValue', [ptr, C.c_int, ptr], C.c_bool),
            ('CFBooleanGetValue', [ptr], C.c_bool), ('CFRelease', [ptr], None)]:
            fn = getattr(self.cf, name); fn.argtypes = args; fn.restype = result
        self.cg.CGWindowListCopyWindowInfo.argtypes = [C.c_uint32, C.c_uint32]
        self.cg.CGWindowListCopyWindowInfo.restype = ptr
        self.keys = {k: self.cf.CFStringCreateWithCString(None, k.encode(), 0x08000100)
                     for k in ('kCGWindowOwnerPID', 'kCGWindowNumber', 'kCGWindowLayer',
                               'kCGWindowBounds', 'kCGWindowIsOnscreen', 'Width', 'Height')}

    def value(self, d, key): return self.cf.CFDictionaryGetValue(d, self.keys[key])

    def number(self, d, key):
        v = self.value(d, key); number = C.c_double()
        if not v or not self.cf.CFNumberGetValue(v, 13, C.byref(number)):
            raise RuntimeError('window metadata unavailable')
        return number.value

    def snapshot(self, pid):
        array = self.cg.CGWindowListCopyWindowInfo(16, 0)  # all, excluding desktop
        if not array: return None
        all_ids, visible = set(), set()
        try:
            for i in range(self.cf.CFArrayGetCount(array)):
                d = self.cf.CFArrayGetValueAtIndex(array, i)
                if self.number(d, 'kCGWindowOwnerPID') != pid: continue
                ident = int(self.number(d, 'kCGWindowNumber'))
                bounds = self.value(d, 'kCGWindowBounds'); shown = self.value(d, 'kCGWindowIsOnscreen')
                if (bounds and self.number(d, 'kCGWindowLayer') == 0
                    and self.number(bounds, 'Width') >= 240 and self.number(bounds, 'Height') >= 180):
                    all_ids.add(ident)
                    if shown and self.cf.CFBooleanGetValue(shown): visible.add(ident)
            return all_ids, visible
        finally: self.cf.CFRelease(array)


class WindowLifetime:
    def __init__(self):
        self.known = set(); self.absent_since = None
        self.previous_ids = None; self.recreated = set()

    def closed(self, observation, now):
        if observation is None:
            self.absent_since = None
            return False
        all_ids, visible = observation
        # A replacement window may first appear hidden (Spaces/full-screen).
        # Conservatively preserve it even before it becomes visible.
        if self.previous_ids is not None and self.known:
            self.recreated |= all_ids - self.previous_ids
        self.previous_ids = set(all_ids)
        self.known |= visible
        if not self.known or (self.known | self.recreated) & all_ids:
            self.absent_since = None
            return False
        if self.absent_since is None: self.absent_since = now
        return now - self.absent_since >= 60


def downloads_pending(bottle, game):
    # Fail closed if an installed library cannot be inspected. Include external
    # libraries so a background download never loses its Steam client.
    steamapps = bottle / 'drive_c/Program Files (x86)/Steam/steamapps'
    libraries = {steamapps, game.parent.parent}
    try:
        vdf = (steamapps / 'libraryfolders.vdf').read_text()
        for drive, tail in re.findall(r'"path"\s+"([A-Za-z]):[\\]+([^"\r\n]+)"', vdf):
            root = bottle / 'dosdevices' / (drive.lower() + ':')
            if drive.lower() == 'c': root = bottle / 'drive_c'
            libraries.add(root.joinpath(*re.split(r'[\\]+', tail)) / 'steamapps')
        for library in libraries:
            if not library.is_dir(): return True
            for p in library.glob('appmanifest_*.acf'):
                text = p.read_text(); values = dict(re.findall(r'"(StateFlags|BytesToDownload|BytesDownloaded)"\s+"(\d+)"', text))
                if 'StateFlags' not in values: return True
                if int(values['StateFlags']) & (256 | 1048576 | 33554432): return True
                if int(values.get('BytesToDownload', 0)) > int(values.get('BytesDownloaded', 0)): return True
        return False
    except (OSError, ValueError): return True


def event(name):
    # Only status codes, never account names, paths, arguments or credentials.
    path = HOME / 'session-cleanup.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps({'event': name, 'at': time.time()})); temp.chmod(0o600); temp.replace(path)


def terminate_game(pid, identity, executable, windows, lifetime):
    if rows().get(pid) != identity: return False
    paths = files(pid)
    if not paths or not any(_same_file(p, executable) for p in paths): return False
    if not lifetime.closed(windows.snapshot(pid), time.monotonic()): return False
    os.kill(pid, signal.SIGTERM)
    # Never SIGKILL a game or retry against a PID whose identity changed.
    event('closed_window_process_terminated')
    return True


def cleanup(bottle, game, owned):
    if not owned: event('preexisting_steam_preserved'); return
    selected = bottle_rows(bottle, rows())
    if selected is None or any(row[2] not in SYSTEM | STEAM for row in selected.values()):
        event('other_application_preserved'); return
    if downloads_pending(bottle, game): event('steam_download_preserved'); return
    steam = {p: r for p, r in selected.items() if r[2] == 'steam.exe'}
    if len(steam) > 1: return
    if steam:
        subprocess.Popen([WINE, '--bottle', bottle.name, '--no-wait', '--debugmsg', '-all',
                          r'C:\Program Files (x86)\Steam\steam.exe', '-shutdown'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        event('owned_steam_shutdown_requested')
    for _ in range(12):
        time.sleep(5)
        selected = bottle_rows(bottle, rows())
        if selected is None: return
        if any(row[2] not in SYSTEM | STEAM for row in selected.values()): return
        if any(row[2] in STEAM for row in selected.values()): continue
        # No Windows application remains. Use the selected prefix only; do not
        # stop controllers while Steam, a game, or any other Windows app is open.
        env = os.environ.copy(); env['WINEPREFIX'] = str(bottle)
        subprocess.run([str(Path(WINE).with_name('wineserver')), '-k'], env=env,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        event('idle_bottle_stopped'); return
    event('steam_shutdown_incomplete')


def watch(bottle, game, owned):
    binary = game / 'Dungeons/Binaries'
    names = [p for sub in ('Win64', 'WinGDK') for name in SHIPPING
             for p in (binary / sub).glob('*') if p.name.lower() == name]
    if not names: return
    windows = Windows(); start = time.monotonic(); tracked = {}
    while time.monotonic() - start < 180:
        snapshot = rows()
        for pid, row in snapshot.items():
            if row[2] not in SHIPPING: continue
            paths = files(pid)
            match = next((p for p in names if paths and any(_same_file(q, p) for q in paths)), None)
            if match: tracked[pid] = (row, match, WindowLifetime())
        if tracked: break
        time.sleep(5)
    if not tracked: event('game_start_not_observed'); return
    event('watching_game')
    terminated = {}
    while tracked:
        time.sleep(5); snapshot = rows()
        for pid, (identity, executable, lifetime) in list(tracked.items()):
            if snapshot.get(pid) != identity: del tracked[pid]; continue
            if pid in terminated:
                if time.monotonic() - terminated[pid] >= 60:
                    event('game_exit_incomplete'); return
                continue
            if lifetime.closed(windows.snapshot(pid), time.monotonic()):
                if terminate_game(pid, identity, executable, windows, lifetime):
                    terminated[pid] = time.monotonic()
    cleanup(bottle, game, owned)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--bottle', required=True); p.add_argument('--game', required=True)
    p.add_argument('--owned-steam', action='store_true'); args = p.parse_args()
    os.umask(0o077)
    root = Path.home() / 'Library/Application Support/CrossOver/Bottles'
    bottle = (root / args.bottle).resolve(); game = Path(args.game).resolve()
    if bottle.parent != root.resolve() or not (bottle / 'cxbottle.conf').is_file() or not game.is_dir(): return
    lock = HOME / ('session-watch-' + hashlib.sha256(str(bottle).encode()).hexdigest()[:16] + '.lock')
    with lock.open('a') as f:
        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return
        try: watch(bottle, game, args.owned_steam)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError): event('observation_failed_no_cleanup')


if __name__ == '__main__': main()
