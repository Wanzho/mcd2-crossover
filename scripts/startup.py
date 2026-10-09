"""Real VC runtime checks and a Steam-owned launch of the shipping executable."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from crossover import wine
APP_ID = '1912410'
LAUNCHER = 'MCD2CrossoverLaunch.cmd'
VC_URL = 'https://aka.ms/vc14/vc_redist.x64.exe'


def vc_installed(bottle):
    registry = bottle / 'system.reg'
    if not registry.exists():
        return False
    text = registry.read_text(errors='replace')
    # Wine registry names contain doubled backslashes and Windows registry keys
    # are case-insensitive. Microsoft's installer uses lowercase x64; CrossOver
    # and older installers can use different casing or the Wow6432Node view.
    # Check the actual installed values; never manufacture prerequisite entries.
    keys = {
        r'software\\microsoft\\visualstudio\\14.0\\vc\\runtimes\\x64',
        r'software\\wow6432node\\microsoft\\visualstudio\\14.0\\vc\\runtimes\\x64',
    }
    sections = re.split(r'(?m)^\[', text)
    found = any(s.split('\n', 1)[0].split(']', 1)[0].casefold() in keys
                and re.search(r'(?mi)^"Installed"=dword:00000001\s*$', s)
                and re.search(r'(?mi)^"Major"=dword:0000000e\s*$', s)
                and (minor := re.search(r'(?mi)^"Minor"=dword:([0-9a-f]{8})\s*$', s))
                and int(minor[1], 16) >= 42
                for s in sections)
    if not found:
        return False
    dlls = bottle / 'drive_c/windows/system32'
    vc_dlls = ('msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
    try:
        # CrossOver can pre-register VC 14.42 while supplying Wine builtins.
        # Those aren't proof that Microsoft's Visual C++ installer has run.
        # Wine's UCRT remains in both working bottles after a real VC install;
        # require it to exist, but don't mistake it for a missing VC runtime.
        return (dlls / 'ucrtbase.dll').is_file() and all(
            (dlls / name).is_file()
            and b'Wine builtin DLL' not in (dlls / name).read_bytes()
            for name in vc_dlls)
    except OSError:
        return False


def ensure_vc(bottle, name, runtime, game=None):
    if vc_installed(bottle):
        return
    installer = runtime / 'vc_redist.x64.exe'
    # Open Microsoft's own UI so the user can read and accept its license.
    # The current permalink is fetched over HTTPS, never shipped in the DMG.
    try:
        try:
            subprocess.run(['/usr/bin/curl', '--fail', '--location', '--silent', '--show-error',
                            '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '20',
                            '--max-time', '180', VC_URL, '-o', str(installer)], check=True)
            if installer.stat().st_size < 1000000 or installer.read_bytes()[:2] != b'MZ':
                raise RuntimeError('Microsoft’s Visual C++ download was incomplete.')
            executable = installer
        except (subprocess.CalledProcessError, RuntimeError):
            bundled = game / 'Engine/Extras/Redist/en-us/vc_redist.x64.exe' if game else None
            if not bundled or not bundled.is_file():
                raise RuntimeError('Visual C++ could not be downloaded and the bundled installer is missing. Check your connection and try setup again.') from None
            executable = bundled
        result = subprocess.run([wine(), '--bottle', name, '--wait', '--debugmsg', '-all',
                                 str(executable)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode not in (0, 3010) or not vc_installed(bottle):
            raise RuntimeError('Visual C++ setup did not finish. Complete Microsoft’s installer, then try setup again.')
    finally:
        installer.unlink(missing_ok=True)


def windows_path(path, bottle):
    path = path.resolve()
    try:
        return 'C:\\' + str(path.relative_to((bottle / 'drive_c').resolve())).replace('/', '\\')
    except ValueError:
        return 'Z:' + str(path).replace('/', '\\')


def command_text():
    # Steam launches this file, retaining its normal ownership and ticket checks.
    return ('@echo off\r\ncd /d "%~dp0"\r\n'
            '"Dungeons\\Binaries\\Win64\\Dungeons-Win64-Shipping.exe" '
            'Dungeons -windowed -ResX=1600 -ResY=900\r\n').encode()


def quote(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


class Node:
    def __init__(self, name, start, end, value=None, children=None):
        self.name, self.start, self.end = name, start, end
        self.value, self.children = value, children


def parse_vdf(text):
    # Offset-preserving parser: only the target launch value is changed. Comments,
    # Steam account fields and settings for other games retain their exact bytes.
    token = re.compile(r'\s+|//[^\r\n]*|"(?:\\.|[^"\\])*"|[{}]')
    values = []
    pos = 0
    for match in token.finditer(text):
        if text[pos:match.start()].strip():
            raise ValueError('Steam settings could not be read. No settings were changed.')
        pos = match.end()
        if match[0].isspace() or match[0].startswith('//'):
            continue
        raw = match[0]
        value = re.sub(r'\\([\\"])', r'\1', raw[1:-1]) if raw.startswith('"') else raw
        values.append((value, match.start(), match.end(), raw.startswith('"')))
    if text[pos:].strip():
        raise ValueError('Steam settings could not be read. No settings were changed.')
    index = 0
    def read(nested=False):
        nonlocal index
        nodes = []
        while index < len(values):
            key, start, end, quoted = values[index]
            index += 1
            if key == '}' and not quoted:
                if not nested:
                    raise ValueError('Unexpected Steam settings structure.')
                return nodes, end
            if not quoted or index >= len(values):
                raise ValueError('Unexpected Steam settings structure.')
            value, vstart, vend, quoted = values[index]
            index += 1
            if value == '{' and not quoted:
                children, close = read(True)
                nodes.append(Node(key, start, close, children=children))
            elif quoted:
                nodes.append(Node(key, vstart, vend, value=value))
            else:
                raise ValueError('Unexpected Steam settings structure.')
        if nested:
            raise ValueError('Incomplete Steam settings structure.')
        return nodes, len(text)
    return read()[0]


def child(nodes, key):
    matches = [n for n in nodes if n.name.lower() == key.lower()]
    if len(matches) > 1:
        raise ValueError('Duplicate Steam settings. No settings were changed.')
    return matches[0] if matches else None


def launch_options(text, value):
    nodes = parse_vdf(text)
    for key in ('UserLocalConfigStore', 'Software', 'Valve', 'Steam', 'apps'):
        node = child(nodes, key)
        if node is None or node.children is None:
            raise ValueError('Open Steam and sign in once, then run setup again.')
        nodes = node.children
    app = child(nodes, APP_ID)
    newline = '\r\n' if '\r\n' in text else '\n'
    if app is None:
        at = node.end - 1
        addition = f'\t\t\t\t"{APP_ID}"{newline}\t\t\t\t{{{newline}\t\t\t\t\t"LaunchOptions"\t\t{quote(value)}{newline}\t\t\t\t}}{newline}\t\t\t'
        return text[:at] + addition + text[at:], None
    if app.children is None:
        raise ValueError('Unexpected Steam game settings. No settings were changed.')
    option = child(app.children, 'LaunchOptions')
    if option:
        return text[:option.start] + quote(value) + text[option.end:], option.value
    at = app.end - 1
    return text[:at] + f'\t"LaunchOptions"\t\t{quote(value)}{newline}\t\t\t\t' + text[at:], None


def configs(bottle):
    paths = sorted((bottle / 'drive_c/Program Files (x86)/Steam/userdata').glob('*/config/localconfig.vdf'))
    if not paths:
        raise RuntimeError('Open Steam and sign in once, then run setup again.')
    return paths


def steam_running(bottle):
    rows = subprocess.run(['ps', '-axo', 'pid=,comm='], capture_output=True, text=True, check=True).stdout
    for line in rows.splitlines():
        if not line.lower().rstrip().endswith('steam.exe'):
            continue
        pid = line.split(None, 1)[0]
        # Steam's open files identify the bottle even when Wine inherits a Mac
        # working directory. Avoid stopping an unrelated Steam bottle.
        files = subprocess.run(['/usr/sbin/lsof', '-a', '-p', pid, '-Fn'],
                             capture_output=True, text=True).stdout
        if any(p.startswith('n' + str(bottle) + '/') for p in files.splitlines()):
            return True
    return False


def stop_steam(bottle, name):
    if not steam_running(bottle):
        return
    subprocess.Popen([wine(), '--bottle', name, '--debugmsg', '-all',
                      r'C:\Program Files (x86)\Steam\steam.exe', '-shutdown'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 45
    while steam_running(bottle):
        if time.monotonic() > deadline:
            raise RuntimeError('Steam is still open. Quit Steam normally, then run setup again.')
        time.sleep(1)


def install_launch(bottle, game, backup, write):
    command = game / LAUNCHER
    win = windows_path(command, bottle)
    if any(c in win for c in ('"', '%', '\r', '\n')):
        raise ValueError('Move the game to a folder without quotes or % in its name, then try again.')
    option = f'"C:\\windows\\system32\\cmd.exe" /d /s /c ""{win}" %command%"'
    # Read after Steam has exited. Validate every config before changing any.
    changes = []
    for path in configs(bottle):
        data = path.read_bytes()
        updated, previous = launch_options(data.decode('utf-8'), option)
        changes.append((path, data, updated.encode(), previous))
    record = {'command': str(command), 'command_existed': command.exists(), 'steam': []}
    if command.exists():
        shutil.copy2(command, backup / LAUNCHER)
    for index, (path, original, updated, previous) in enumerate(changes):
        name = f'steam-{index}-localconfig.vdf'
        write(backup / name, original)
        write(path, updated)
        record['steam'].append({'path': str(path), 'backup': name, 'previous_options': previous})
    write(command, command_text())
    write(backup / 'startup.json', (json.dumps(record, indent=2) + '\n').encode())
    return option
