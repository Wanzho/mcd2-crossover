#!/usr/bin/env python3
"""Short, opt-in recordings and a deliberately limited support ZIP.

Only this module's known status fields and the adapter's known diagnostic
formats are exported. Session files, settings, raw server replies, game files
and Keychain data are never copied into the archive.
"""
import argparse
import json
import os
import re
import stat
import sys
import time
import uuid
import zipfile
from pathlib import Path

HOME = Path.home() / 'Library/Application Support/DungeonsCrossOver'
MAX_SECONDS = 3600
MAX_LOG_BYTES = 256 * 1024
MAX_LINE_BYTES = 2048
LOG_FILES = ('app.log', 'auth.log', 'http.log', 'runtime.log')
FLAG = 'logging.enabled'
STATE = 'recording.json'
STORES = {'steam', 'launcher', 'direct', 'unknown'}
OUTCOMES = {'started', 'success', 'failed', 'cancelled', 'ready', 'unsupported'}
EVENTS = {
    'recording_started', 'setup', 'setup_started', 'setup_completed', 'setup_failed',
    'launch', 'launch_started', 'launch_requested', 'launch_failed', 'sign_out',
    'sign_out_started', 'sign_out_completed', 'sign_out_failed', 'game_selected',
    'copy_checked', 'connectivity', 'renewal', 'stop_game',
}
AUTH_STEPS = {
    'device-code-start', 'device-code-poll', 'microsoft-refresh', 'device-auth',
    'xbox-user-auth', 'xsts-xbox', 'xsts-minecraft', 'xsts-playfab',
    'renewal-complete', 'forced-renewal-failed', 'silent-renewal-failed',
}
OAUTH_ERRORS = {
    'authorization_pending', 'slow_down', 'invalid_grant', 'invalid_client',
    'access_denied', 'expired_token', 'invalid_request',
}
RUNTIME_LABELS = {
    'Native runtime initialization', 'Native async failure after user login',
    'Adapter user handle validation', 'Runtime class requested',
    'Runtime interface requested', 'Native interface request failed',
    'Measured HTTPS connectivity', 'Connectivity level',
    'Connectivity notification registered', 'Unavailable native connectivity interface',
    'Native networking feature available', 'Keychain-backed ForceRefresh result',
    'User interface requested', 'Unsupported user API', 'dupUser', 'closeUser',
    'XUserAddAsync options', 'No valid real session', 'XUserAddResult',
    'XUserAddByIdWithUi no valid session', 'XUserAddByIdWithUi matches authenticated user',
    'XUserAddByIdWithUiResult', 'localId', 'findLocal', 'getId', 'findId', 'guest',
    'state', 'age', 'Privilege requested', 'Gamertag component',
    'Service token requested', 'Service token result', 'changeRegister', 'changeUnregister',
}
USER_APIS = {
    'XUserQueryInterface', 'XUserAddRef', 'XUserRelease', 'XUserDuplicateHandle',
    'XUserCloseHandle', 'XUserCompare', 'XUserGetMaxUsers', 'XUserAddAsync',
    'XUserAddResult', 'XUserGetLocalId', 'XUserFindLocal', 'XUserGetId', 'XUserFindId',
    'XUserIsGuest', 'XUserGetState', 'XUserAgeGroup', 'XUserCheckPrivilege',
    'XUserResolvePrivilegeAsync', 'XUserResolvePrivilegeResult', 'XUserGetGamertag',
    'XUserGetTokenAndSignatureAsync', 'XUserGetTokenAndSignatureUtf16Async',
    'XUserGetTokenAndSignatureSize', 'XUserGetTokenAndSignatureResult',
    'XUserGetTokenAndSignatureUtf16Result', 'XUserRegisterChange', 'XUserUnregisterChange',
    'XUserSignoutDeferral', 'XUserCloseDeferral', 'XUserAddByIdAsync', 'XUserAddByIdResult',
    'XUserMSATokenAsync', 'XUserMSATokenResult', 'XUserMSATokenSize', 'XUserIsStoreUser',
    'XUserRemoteHandlers', 'XUserRemoteCancel', 'XUserSpopHandlers', 'XUserSpopComplete',
    'XUserSignoutPresent', 'XUserSignoutAsync', 'XUserSignoutResult',
}
HTTP_CONSTANTS = {
    'diagnostic loaded', 'curl_global_init_mem called', 'curl_easy_init called',
    'Incompatible SSL_CTX customization refused: CURLE_NOT_BUILT_IN',
    'Unsupported TLS verification reduction refused',
}
HEADERS = {
    'accept', 'accept-encoding', 'authorization', 'content-type', 'content-length',
    'content-encoding', 'transfer-encoding', 'expect', 'host', 'user-agent',
    'connection', 'cache-control', 'x-authorization', 'x-playfabsdk', 'x-requestid',
    'x-xbl-contract-version',
}
ROUTES = {
    'Client/LoginWithSteam', 'Client/LoginWithXbox', 'Client/GetAccountInfo',
    'Client/LinkXboxAccount', 'Client/GetUserData', 'Client/GetUserReadOnlyData',
    'Client/GetTitleData', 'Client/GetPlayerProfile', 'Client/GetUserInventory',
    'Authentication/GetEntityToken', 'title-api', 'minecraft-service',
}
SERVER_ERRORS = {
    'InvalidSteamTicket', 'AccountNotFound', 'SteamNotEnabledForTitle',
    'InvalidContentType', 'InvalidParams', 'InvalidRequest', 'InvalidJSONContent',
    'ServiceUnavailable', 'NotAuthenticated', 'InvalidXboxLiveToken',
    'InvalidSignature', 'AccountBanned', 'APIRequestLimitExceeded', 'BadRequest',
}
HINTS = {
    'Bad Request', 'Invalid Header', 'Invalid Hostname', 'Invalid Verb',
    'Request Header Or Cookie Too Large', 'Access Denied', 'InvalidSteamTicket',
    'AccountNotFound', 'SteamNotEnabledForTitle', 'TicketIsServiceSpecific',
    'Invalid request', 'Content-Length', 'Content-Type', 'unsupported media type',
    'application/json', 'application/octet-stream',
}


class NoRecordingError(ValueError):
    pass


def _integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def _member(value, choices):
    return isinstance(value, str) and value in choices


def _regular(path):
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def _private_home(home):
    home = Path(home)
    if home.is_symlink():
        raise ValueError('unsafe data folder')
    home.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not home.is_dir():
        raise ValueError('unsafe data folder')
    os.chmod(home, 0o700)
    return home


def _read_json(path):
    if not _regular(path):
        return {}
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, 'rb') as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                return {}
            data = file.read(4097)
        if len(data) > 4096:
            return {}
        value = json.loads(data)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def _atomic(path, data):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _write_json(path, value):
    _atomic(path, (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode())


def _times(doc):
    started, expires = doc.get('started'), doc.get('expires')
    if (type(doc.get('version')) is int and doc['version'] == 1 and _integer(started, 1) and _integer(expires, 1)
            and 0 < expires - started <= MAX_SECONDS):
        return {'version': 1, 'started': started, 'expires': expires}
    return {}


def enabled(home=HOME, now=None):
    """The bridge and native adapters use the same one-hour expiry."""
    home = Path(home)
    if home.is_symlink():
        return False
    now = time.time() if now is None else now
    doc = _times(_read_json(home / FLAG))
    if doc and doc['started'] <= now < doc['expires']:
        return True
    # Removing a local flag never follows a symlink and never touches a log.
    if (home / FLAG).exists() or (home / FLAG).is_symlink():
        (home / FLAG).unlink(missing_ok=True)
    return False


def start(home=HOME, now=None):
    home = _private_home(home)
    # Reject unexpected file types before clearing any previous recording.
    for name in (*LOG_FILES, FLAG, STATE):
        path = home / name
        if (path.exists() or path.is_symlink()) and not _regular(path):
            raise ValueError('unsafe diagnostic file')
    recordings = home / 'recordings'
    if (recordings.exists() or recordings.is_symlink()) and (recordings.is_symlink() or not recordings.is_dir()):
        raise ValueError('unsafe recordings folder')
    stamp = int(time.time() if now is None else now)
    if stamp <= 0:
        raise ValueError('invalid recording time')
    previous_logs = [home / name for name in LOG_FILES if _regular(home / name)]
    (home / FLAG).unlink(missing_ok=True)
    if previous_logs:
        recordings.mkdir(mode=0o700, exist_ok=True)
        os.chmod(recordings, 0o700)
        previous = recordings / (str(stamp) + '-' + uuid.uuid4().hex)
        previous.mkdir(mode=0o700)
        for source in previous_logs:
            destination = previous / source.name
            source.rename(destination)
            os.chmod(destination, 0o600)
        old_state = _times(_read_json(home / STATE))
        if old_state:
            _write_json(previous / STATE, old_state)
    state = {'version': 1, 'started': stamp, 'expires': stamp + MAX_SECONDS}
    if previous_logs:
        state['previous_recording_kept'] = True
    _write_json(home / STATE, state)
    _write_json(home / FLAG, _times(state))
    record(home, 'recording_started', {'outcome': 'started'}, now=stamp)
    return status(home, now=stamp)


def stop(home=HOME, now=None):
    home = Path(home)
    if home.is_symlink():
        raise ValueError('unsafe data folder')
    (home / FLAG).unlink(missing_ok=True)
    previous_state = _read_json(home / STATE)
    state = _times(previous_state)
    if state:
        stamp = int(time.time() if now is None else now)
        state['stopped'] = max(state['started'], min(stamp, state['expires']))
        if previous_state.get('previous_recording_kept') is True:
            state['previous_recording_kept'] = True
        _write_json(home / STATE, state)
    return status(home, now=now)


def status(home=HOME, now=None):
    home = Path(home)
    now = time.time() if now is None else now
    active = enabled(home, now)
    state = _times(_read_json(home / STATE))
    stopped = _read_json(home / STATE).get('stopped')
    files = []
    if not home.is_symlink():
        for name in LOG_FILES:
            path = home / name
            if _regular(path):
                files.append({'name': name, 'bytes': min(path.stat().st_size, MAX_LOG_BYTES),
                              'capped': path.stat().st_size > MAX_LOG_BYTES})
    result = {'ok': True, 'active': active, 'available': bool(files),
              'seconds_remaining': max(0, int(state.get('expires', 0) - now)) if active else 0,
              'expires': state.get('expires'), 'started': state.get('started'), 'logfiles': files}
    if state and _integer(stopped, state['started'], state['expires']):
        result['stopped'] = stopped
    if _read_json(home / STATE).get('previous_recording_kept') is True:
        result['previous_recording_kept'] = True
    return result


def _app_fields(fields):
    result = {}
    if _member(fields.get('outcome'), OUTCOMES):
        result['outcome'] = fields['outcome']
    if _member(fields.get('store'), STORES):
        result['store'] = fields['store']
    version = fields.get('app_version')
    if isinstance(version, str) and re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}', version):
        result['app_version'] = version
    for key, high in [('error_code', 65535), ('elapsed_seconds', MAX_SECONDS)]:
        if _integer(fields.get(key), 0, high):
            result[key] = fields[key]
    return result


def record(home, event, fields=None, now=None):
    """Record only controlled app events; arbitrary text and paths are ignored."""
    home = Path(home)
    if not _member(event, EVENTS) or not enabled(home, now):
        return False
    row = {'event': event, **_app_fields(fields or {})}
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(home / 'app.log', flags, 0o600)
        with os.fdopen(fd, 'a') as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                return False
            if os.fstat(file.fileno()).st_size >= MAX_LOG_BYTES:
                return False
            file.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n')
        return True
    except OSError:
        return False


def _host(value):
    # An unknown host can contain an account label or a secret. Export only
    # established public service domains, replacing every other hostname.
    if not re.fullmatch(r'[a-z0-9.-]{1,180}', value):
        return '[other-host]'
    for domain in ('minecraftservices.com', 'xboxlive.com', 'playfabapi.com', 'live.com', 'microsoft.com'):
        if value == domain:
            return value
        if value.endswith('.' + domain):
            prefix = value[:-len(domain)-1]
            allowed = {'api', 'vex', 'login', 'device.auth', 'user.auth', 'xsts.auth', 'www', '83156'}
            return value if prefix in allowed else '[other-host]'
    return '[other-host]'


def _json_row(line, name):
    try:
        doc = json.loads(line)
    except (ValueError, UnicodeError):
        return None
    if not isinstance(doc, dict):
        return None
    if name == 'app.log':
        if not _member(doc.get('event'), EVENTS):
            return None
        result = {'event': doc['event'], **_app_fields(doc)}
    else:
        if not _member(doc.get('step'), AUTH_STEPS):
            return None
        result = {'step': doc['step']}
        if _integer(doc.get('http_status'), 100, 599):
            result['http_status'] = doc['http_status']
        if _integer(doc.get('xerr'), 0, 2**32 - 1):
            result['xerr'] = doc['xerr']
        if _member(doc.get('oauth_error'), OAUTH_ERRORS):
            result['oauth_error'] = doc['oauth_error']
    return json.dumps(result, sort_keys=True, separators=(',', ':'))


def _runtime_row(line):
    match = re.fullmatch(r'(.{1,256}) 0x([0-9A-Fa-f]{8})', line)
    if not match:
        return None
    label, code = match.groups()
    if label in RUNTIME_LABELS or label.startswith('Unsupported ') and label[12:] in USER_APIS:
        return label + ' 0x' + code.upper()
    if label.startswith('Refused token host: '):
        return 'Refused token host: ' + _host(label[20:]) + ' 0x' + code.upper()
    host = _host(label)
    return 'Token host: ' + host + ' 0x' + code.upper() if host != '[other-host]' else None


def _pairs(text, numeric=(), enums=None):
    """Rebuild a diagnostic row instead of trying to redact arbitrary text."""
    result = []
    enums = enums or {}
    for key in numeric:
        match = re.search(r'(?<!\S)' + re.escape(key) + r'=(-?\d{1,12})(?=\s|$)', text)
        if match and -1 <= int(match[1]) <= 64 * 1024 * 1024:
            result.append(key + '=' + str(int(match[1])))
    for key, choices in enums.items():
        match = re.search(r'(?<!\S)' + re.escape(key) + r'=([^\s]+)', text)
        if match and match[1] in choices:
            result.append(key + '=' + match[1])
    return ' '.join(result)


def _http_row(line):
    if line in HTTP_CONSTANTS:
        return line
    match = re.fullmatch(r'connection curl=(-?\d{1,3}) http=(\d{1,3}) host=(.*)', line)
    if match:
        return f'connection curl={match[1]} http={match[2]} host={_host(match[3])}'
    if line.startswith('option='):
        fields = _pairs(line, ('option', 'result', 'value'))
        if not fields.startswith('option='):
            return None
        return fields + (' CAfile=[local-certificate-bundle]' if ' CAfile=' in line else '')
    numeric = ('rawValueBytes', 'valueBytesWithoutLeadingOWS', 'leadingOWSBytes', 'unusualBytes',
               'offset', 'byteDecimal', 'headerBlockBytes', 'contentEncodingPresent',
               'transferEncodingPresent', 'chunked', 'expectPresent', 'contentLengthHeaders',
               'declaredLengthValid', 'declaredBodyBytes', 'outgoingWireBodyBytes',
               'payloadBodyBytes', 'http', 'ticketHexLength', 'decodedBodyBytes', 'errorCode',
               'contentType', 'encoding', 'count', 'originalKind', 'nameValid')
    enums = {'source': {'wire', 'source'}, 'method': {'POST', 'other'}, 'httpVersion': {'1.0', '1.1', '2', 'other'},
             'declaredMatchesPayload': {'true', 'false', 'unavailable'},
             'createAccount': {'true', 'false', 'unavailable'}, 'serviceSpecific': {'true', 'false', 'unavailable'},
             'titleMatches': {'true', 'unavailable'}, 'bodyKind': {'json', 'markup', 'gzip', 'other', 'empty'},
             'error': SERVER_ERRORS}
    if line.startswith('playfab known streamed body bytes='):
        match = re.fullmatch(r'playfab known streamed body bytes=(\d{1,9}) result=(-?\d{1,3})', line)
        return line if match and int(match[1]) <= 64 * 1024 * 1024 else None
    if line.startswith('playfab redacted-server-error:'):
        return 'playfab server error text omitted; see response-format hints'
    prefixes = ('playfab header ', 'playfab Content-Type ', 'playfab Content-Type unusual byte ',
                'playfab outgoing request ', 'playfab framing ', 'playfab response-format ',
                'playfab original-header observation ')
    prefix = next((p for p in sorted(prefixes, key=len, reverse=True) if line.startswith(p)), None)
    if line.startswith('playfab route='):
        match = re.match(r'playfab route=([^\s]+)', line)
        if not match:
            return None
        route = match[1]
        prefix = 'playfab route=' + (route if route in ROUTES else '[other-operation]') + ' '
    if not prefix:
        return None
    fields = _pairs(line, numeric, enums)
    if prefix == 'playfab header ':
        match = re.search(r'(?<!\S)name=([^\s]+)', line)
        if match:
            name = match[1].lower()
            fields += ' name=' + (name if name in HEADERS else '[other-header]')
    if prefix == 'playfab response-format ':
        # Preserve only exact predefined hints, never free-form server text.
        for hint in sorted(HINTS):
            if re.search(r' hint=' + re.escape(hint) + r'(?= hint=|$)', line):
                fields += ' hint=' + hint
    return (prefix + fields).strip() if fields else None


def sanitize(data, name):
    """Return UTF-8 bytes and counts without leaking unknown diagnostic rows."""
    accepted, omitted = [], 0
    for raw in data.splitlines():
        if len(raw) > MAX_LINE_BYTES:
            omitted += 1
            continue
        try:
            line = raw.decode('utf-8', errors='strict')
        except UnicodeError:
            omitted += 1
            continue
        if name in {'auth.log', 'app.log'}:
            row = _json_row(line, name)
        elif name == 'runtime.log':
            row = _runtime_row(line)
        else:
            row = _http_row(line)
        if row is None:
            omitted += 1
        else:
            accepted.append(row)
    data = ('\n'.join(accepted) + ('\n' if accepted else '')).encode()
    return data, {'rows': len(accepted), 'omitted_rows': omitted}


def _log_snapshot(path):
    if not _regular(path):
        return None
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode):
            return None
        capped = info.st_size > MAX_LOG_BYTES
        if capped:
            file.seek(-MAX_LOG_BYTES, os.SEEK_END)
            file.readline(MAX_LINE_BYTES + 1)  # Discard the incomplete leading row.
        data = file.read(MAX_LOG_BYTES)
    return data, capped


def export(home, output, now=None):
    home, output = Path(home), Path(output)
    if output.suffix.lower() != '.zip' or output.is_symlink():
        raise ValueError('choose a ZIP file')
    if output.resolve().is_relative_to(home.resolve()):
        raise ValueError('choose a ZIP outside the private data folder')
    if not output.parent.is_dir() or output.exists() and not _regular(output):
        raise ValueError('unsafe export destination')
    state = stop(home, now)
    entries, reports = {}, {}
    for name in LOG_FILES:
        snapshot = _log_snapshot(home / name)
        if snapshot is None:
            continue
        raw, capped = snapshot
        safe, report = sanitize(raw, name)
        report['input_capped'] = capped
        reports[name] = report
        entries['logs/' + name] = safe
    if not reports:
        raise NoRecordingError('no recording available')
    settings = _read_json(home / 'settings.json')
    safe_settings = _app_fields({'store': settings.get('store'), 'app_version': settings.get('app_version')})
    manifest = {
        'format_version': 1,
        'application': 'MCD2 Crossover',
        **safe_settings,
        'recording': {key: state[key] for key in ('started', 'expires', 'stopped') if state.get(key) is not None},
        'logs': reports,
        'privacy': 'Only selected status codes, request framing and app events are included. '
                   'Unknown rows and server text are omitted. No tokens, passwords, account IDs, '
                   'user paths, session files, settings files, Keychain data or game files are included.',
    }
    entries['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    entries['READ ME.txt'] = (
        'MCD2 Crossover troubleshooting recording\n\n'
        'Recording stops when this ZIP is saved. The adapters stop recording after one hour even if '
        'the app is closed. Only known status fields are exported; unknown log rows are omitted.\n'
        'No Microsoft credentials, account IDs, paths, game files or saved games are included.\n'
        'Add a short description of what happened and a screenshot when opening an issue.\n'
    ).encode()
    temp = output.with_name(output.name + '.' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb') as file, zipfile.ZipFile(file, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(entries.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100600 << 16
                archive.writestr(info, data)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    return {'ok': True, 'active': False, 'saved': True, 'logfiles': list(reports),
            'omitted_rows': sum(item['omitted_rows'] for item in reports.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('start', 'stop', 'status', 'export', 'event'))
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--step', choices=sorted(EVENTS))
    parser.add_argument('--outcome', choices=sorted(OUTCOMES))
    args = parser.parse_args()
    try:
        if args.command == 'export':
            if args.output is None:
                parser.error('export needs --output')
            result = export(args.home, args.output)
        elif args.command == 'event':
            if args.step is None:
                parser.error('event needs --step')
            result = {'ok': True, 'recorded': record(args.home, args.step, {'outcome': args.outcome})}
        else:
            result = globals()[args.command](args.home)
    except NoRecordingError:
        print(json.dumps({'ok': False, 'error': 'No recording is available. Choose Start Recording, reproduce the problem, then Save Logs.'}))
        return 1
    except (OSError, ValueError, TypeError):
        # File paths and server/account details must not appear in error text.
        print(json.dumps({'ok': False, 'error': 'Could not complete the log operation. Choose a regular ZIP file outside the private data folder.'}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
