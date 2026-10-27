#!/usr/bin/env python3
"""Short, opt-in recordings and a deliberately limited support ZIP.

Only this module's known status fields and the adapter's known diagnostic
formats are exported. Session files, settings, raw server replies, saved games
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

sys.path.insert(0, str(Path(__file__).resolve().parent))

import diagnostic_schema

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
    'copy_checked', 'connectivity', 'renewal', 'stop_game', 'freeze_capture',
}
AUTH_STEPS = {
    'device-code-start', 'device-code-poll', 'microsoft-refresh', 'device-auth',
    'xbox-user-auth', 'xsts-xbox', 'xsts-minecraft', 'xsts-playfab',
    'renewal-started', 'renewal-failed', 'renewal-complete', 'forced-renewal-failed', 'silent-renewal-failed',
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
    'ForceRefresh started', 'ForceRefresh elapsed milliseconds', 'Service token requested', 'Service token result', 'changeRegister', 'changeUnregister',
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
    'wait-queue fix applied', 'wait-queue fix already present',
    'wait-queue fix not applicable to this Wine build',
    'wait-queue fix could not be applied',
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
    for name in (*LOG_FILES, FLAG, STATE, 'freeze.json', 'freeze-runtime.json'):
        path = home / name
        if (path.exists() or path.is_symlink()) and not _regular(path):
            raise ValueError('unsafe diagnostic file')
    recordings = home / 'recordings'
    if (recordings.exists() or recordings.is_symlink()) and (recordings.is_symlink() or not recordings.is_dir()):
        raise ValueError('unsafe recordings folder')
    stamp = int(time.time() if now is None else now)
    if stamp <= 0:
        raise ValueError('invalid recording time')
    previous_logs = [home / name for name in (*LOG_FILES, 'freeze.json', 'freeze-runtime.json') if _regular(home / name)]
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


def _internal_error_report(home, now=None):
    if Path(home).is_symlink():
        return None
    catalog_path = Path(__file__).with_name("error_codes.json")
    catalog = {row["code"]: row for row in json.loads(catalog_path.read_text())} if catalog_path.is_file() else {}
    error = _read_json(Path(home) / 'internal-error.json')
    code = error.get('code')
    if type(code) is not int or code not in catalog:
        return None
    report = dict(catalog[code])
    for key in ('exit_status', 'system_code'):
        if type(error.get(key)) is int:
            report[key] = error[key]
    # mtime is a file observation, not proof of when the error occurred.
    now = time.time() if now is None else now
    try:
        modified = (Path(home) / 'internal-error.json').lstat().st_mtime
        recording = _times(_read_json(Path(home) / STATE))
        relation = 'unknown'
        if modified > now:
            relation = 'after_export_clock'
        elif recording:
            relation = ('predates_recording' if modified < recording['started']
                        else 'at_or_after_recording_start')
        report['time_context'] = {
            'source': 'file_mtime', 'modified_unix_seconds': modified,
            'recording_relation': relation, 'freshness': 'unverified',
            'note': 'Saved error; file modification time is not the error occurrence time or evidence of a current failure.',
        }
    except OSError:
        report['time_context'] = {'source': 'unavailable', 'freshness': 'unverified'}
    return report


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
    game_available = False
    if not home.is_symlink():
        _, game_status = _game_log_entries(_read_json(home / 'settings.json'), metadata_only=True)
        game_available = game_status['status'] == 'available'
    from runtime_capture import saved_report
    result = {'ok': True, 'active': active, 'available': saved_report(home) is not None or game_available or bool(files) or _freeze_report(home) is not None or _internal_error_report(home) is not None,
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
    if isinstance(version, str) and re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){2,3}(?:-(?:alpha|beta|rc)\.\d{1,3})?', version):
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
    row = {'event': event, 'timestamp_ms': int((time.time() if now is None else now)*1000), **_app_fields(fields or {})}
    return append_json(home / 'app.log', row)


def append_json(path, row):
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, 'a') as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode): return False
            if os.fstat(file.fileno()).st_size >= MAX_LOG_BYTES: return False
            file.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n')
        return True
    except OSError:
        return False


def timing_fields(doc):
    result = {}
    for key, limit in [('timestamp_ms', 9999999999999), ('elapsed_ms', 86400000), ('attempt', 1000000), ('pid', 2**32-1), ('thread_id', 2**32-1)]:
        if _integer(doc.get(key), 0, limit): result[key] = doc[key]
    if _member(doc.get('phase'), {'started','completed','failed'}): result['phase']=doc['phase']
    return result


def _freeze_report(home):
    from freeze_capture import safe_report
    if Path(home).is_symlink(): return None
    path=Path(home)/'freeze.json'
    if not _regular(path): return None
    try:
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as f:
            data=f.read(4*1024*1024+1)
        if len(data)>4*1024*1024:return None
        return safe_report(json.loads(data))
    except (OSError,ValueError,TypeError): return None


def _host(value):
    # An unknown host can contain an account label or a secret. Export only
    # established public service domains, replacing every other hostname.
    return value if value in diagnostic_schema.HOSTS | diagnostic_schema.AUTH_HOSTS else '[other-host]'


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
    result.update(timing_fields(doc))
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
    if line.startswith('request '):
        match=re.fullmatch(r'request id=(\d{1,9}) phase=(started|completed) elapsed_ms=(\d{1,8})(?: curl=(-?\d{1,3}) http=(\d{1,3}))?',line)
        return line if match and int(match[3])<=86400000 else None
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
        prefix = ''
        if name in {'runtime.log','http.log'}:
            envelope=diagnostic_schema.ENVELOPE.match(line)
            if envelope:
                if any(int(v)>2**32-1 for v in envelope.groups()[1:]): omitted+=1; continue
                prefix=envelope[0];line=line[envelope.end():]
        if name in {'auth.log', 'app.log'}:
            row = _json_row(line, name)
        elif line.startswith('diag '):
            structured = diagnostic_schema.parse(line)
            row = diagnostic_schema.render(structured) if structured else None
        elif name == 'runtime.log':
            row = _runtime_row(line)
        else:
            row = _http_row(line)
        if row is None:
            omitted += 1
        else:
            accepted.append(prefix + row)
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



def _sanitize_game_log(data):
    """Keep diagnostic text, omitting identity/authentication rows and paths."""
    rows, omitted = [], 0
    sensitive = re.compile(r'(?i)(authorization|bearer|cookie|token|password|secret|'
                           r'gamertag|username|user\s*name|loginid|account|xuid|'
                           r'playfabid|entityid|machineid|command\s*line|user\s*:|computer\s*name)')
    for line in data.decode('utf-8', errors='replace').splitlines():
        if len(line.encode('utf-8')) > MAX_LINE_BYTES or sensitive.search(line):
            omitted += 1
            continue
        line = re.sub(r'https?://[^\s<>"\x27]+', '[URL]', line, flags=re.I)
        line = re.sub(r'\b[^\s@]+@[^\s@]+\.[^\s@]+', '[EMAIL]', line)
        line = re.sub(r'(?i)\b[A-Z]:[\\/][^\r\n]*', '[PATH]', line)
        line = re.sub(r'(?<![\w.])/(?:Users|home|private|Volumes|Applications|tmp)/[^\r\n]*', '[PATH]', line)
        line = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '[ID]', line)
        line = re.sub(r'\b\d{12,}\b', '[ID]', line)
        line = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', line)
        rows.append(line)
    return ('\n'.join(rows) + ('\n' if rows else '')).encode(), omitted


def _game_log_entries(settings, metadata_only=False):
    report = {'status': 'not_selected', 'files': [], 'skipped_files': 0}
    entries = {}
    bottle = settings.get('bottle')
    if not isinstance(bottle, str) or not bottle or bottle in ('.', '..') or '/' in bottle or '\\' in bottle:
        return entries, report
    root = Path.home() / 'Library/Application Support/CrossOver/Bottles' / bottle
    try:
        root = root.resolve(strict=True)
        users = root / 'drive_c/users'
        # Permit an intentionally relocated bottle, but not links below it.
        def plain(path):
            relative = path.relative_to(root)
            cursor = root
            for part in relative.parts:
                cursor /= part
                if cursor.is_symlink():
                    return False
            return True
        if not plain(users) or not users.is_dir():
            report['status'] = 'missing'
            return entries, report
        candidates = []
        with os.scandir(users) as profiles:
            profile_paths = []
            for index, profile in enumerate(profiles):
                if index >= 16:
                    report['profiles_limited'] = True
                    break
                if profile.is_dir(follow_symlinks=False):
                    profile_paths.append(Path(profile.path))
        for profile in sorted(profile_paths):
            folder = profile / 'AppData/Local/Dungeons2/Saved/Logs'
            if not plain(folder) or not folder.is_dir():
                continue
            # Bound directory enumeration as well as file content reads.
            with os.scandir(folder) as items:
                for index, item in enumerate(items):
                    if index >= 256:
                        report['directory_limited'] = True
                        break
                    if item.name.lower().endswith('.log') and item.is_file(follow_symlinks=False):
                        candidates.append((item.stat(follow_symlinks=False).st_mtime, Path(item.path)))
        if metadata_only:
            report['status'] = 'available' if candidates else 'missing'
            return entries, report
        candidates.sort(key=lambda item: item[0], reverse=True)
        report['skipped_files'] = max(0, len(candidates) - 4)
        for modified, path in candidates[:4]:
            try:
                snapshot = _log_snapshot(path)
                if snapshot is None:
                    report['skipped_files'] += 1
                    continue
                raw, capped = snapshot
                safe, omitted = _sanitize_game_log(raw)
                name = 'game-logs/log-%02d.log' % (len(entries) + 1)
                entries[name] = safe
                report['files'].append({'archive_name': name, 'kind': 'cef' if path.name.lower() == 'cef3.log' else 'game',
                                        'modified_unix_seconds': int(modified), 'input_capped': capped,
                                        'omitted_rows': omitted, 'exported_bytes': len(safe)})
            except OSError:
                report['skipped_files'] += 1
        report['status'] = 'included' if entries else 'missing'
    except OSError:
        report['status'] = 'unavailable'
    return entries, report

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
    # Error reports remain exportable even if no optional recording was started.
    error_report = _internal_error_report(home, now)
    if error_report:
        entries['internal-error.json'] = (json.dumps(error_report,indent=2)+'\n').encode()
    from runtime_capture import saved_report
    windows = saved_report(home)
    if windows: entries['freeze-runtime.json'] = (json.dumps(windows,indent=2)+'\n').encode()
    freeze = _freeze_report(home)
    if freeze: entries['freeze.json'] = (json.dumps(freeze,indent=2)+'\n').encode()
    settings = _read_json(home / 'settings.json')
    game_entries, game_report = _game_log_entries(settings)
    entries.update(game_entries)
    if not reports and 'internal-error.json' not in entries and not freeze and not windows and not game_entries:
        raise NoRecordingError('no recording available')
    settings = _read_json(home / 'settings.json')
    safe_settings = _app_fields({'store': settings.get('store'), 'app_version': settings.get('app_version')})
    manifest = {
        'format_version': 2,
        'exporter_build': '20261022.2',
        'application': 'MCD2 Crossover',
        **safe_settings,
        'recording': {key: state[key] for key in ('started', 'expires', 'stopped') if state.get(key) is not None},
        'logs': reports,
        'diagnostic_coverage': diagnostic_schema.coverage(entries, reports),
        'game_logs': game_report,
        'privacy': 'Helper logs contain allowlisted status fields. Game logs contain bounded diagnostic text with sensitive rows omitted and paths, URLs, emails and identifiers filtered. Review before sharing. Saved games, browser caches, session files, settings and Keychain data are not copied.',
    }
    entries['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    entries['READ ME.txt'] = (
        'MCD2 Crossover troubleshooting recording\n\n'
        'Recording stops when this ZIP is saved. The adapters stop recording after one hour even if '
        'the app is closed. Only known status fields are exported; unknown log rows are omitted.\n'
        'Game logs are collected from the selected bottle, independently of Start Recording.\n'
        'game-logs/ contains up to four recent log tails (256 KiB per input file), with sensitive rows omitted and paths redacted.\n'
        'Review diagnostic text before sharing. Saved games and browser caches are never copied.\n'
        'freeze-runtime.json contains per-stage Windows thread counts, debugger state, stacks and bottle process roles. Failures and partial results are retained.\n'
        'Host process entries are runtime candidates across the Mac; only the Windows process list is scoped to the selected bottle.\n'
        'These snapshots do not record which process previously requested a suspension.\n'
        'freeze.json contains an on-demand game sample and resource snapshot, when captured.\n'
        'Helper times are Unix milliseconds (UTC). Game log timestamps retain their original format; their timezone may be unknown.\n'
        'Capture before quitting the frozen game. Add what happened when opening an issue.\n'
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
    parser.add_argument('command', choices=('start', 'stop', 'status', 'export', 'event', 'capture'))
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
        elif args.command == 'capture':
            from freeze_capture import capture
            result = capture(args.home)
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
