"""Per-user, genuine Microsoft/Xbox authentication for the CrossOver adapter.

Refresh tokens exist only in memory and the macOS Keychain. Diagnostics are
opt-in, contain only whitelisted status fields, and never contain credentials.
"""
import argparse, base64, contextlib, datetime, fcntl, hashlib, json, os
import signal, ssl, struct, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed, decode_dss_signature
sys.path.insert(0,str(Path(__file__).resolve().parent))
import diagnostics
import localization

HOME = Path.home() / 'Library/Application Support/DungeonsCrossOver'
ROOT = Path(__file__).resolve().parent
CLIENT = '00000000497C1B94'
SCOPE = 'service::user.auth.xboxlive.com::MBI_SSL'
ALLOWED = {'login.live.com', 'device.auth.xboxlive.com', 'user.auth.xboxlive.com', 'xsts.auth.xboxlive.com'}
MAGIC = 0x3247444952425858
PACKET = struct.Struct('<QQQII32s512s49152sQ')
REQUEST_MAGIC = 0x3151455242434447
ERROR = 0x80004005
NOUSER = 0x89245100
cancelled = False

def private_home():
    os.umask(0o077)
    HOME.mkdir(parents=True, mode=0o700, exist_ok=True)
    if HOME.is_symlink(): raise RuntimeError('unsafe directory')
    os.chmod(HOME, 0o700)

def atomic(path, data):
    path = Path(path)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally: temp.unlink(missing_ok=True)

def diagnostic(step, status=None, doc=None):
    if not diagnostics.enabled(HOME): return
    row = {'step': step}
    if isinstance(status, int): row['http_status'] = status
    doc = doc or {}
    if isinstance(doc.get('XErr'), int): row['xerr'] = doc['XErr']
    if doc.get('error') in {'authorization_pending','slow_down','invalid_grant','invalid_client','access_denied','expired_token','invalid_request'}:
        row['oauth_error'] = doc['error']
    fd = os.open(HOME / 'auth.log', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a') as f: f.write(json.dumps(row) + '\n')

class AuthError(Exception): pass

def keychain(operation, secret=None):
    helper = HOME / 'runtime/keychain'
    result = subprocess.run([str(helper), operation], input=secret.encode() if secret is not None else None,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if result.returncode == 3 and operation == 'get': return None
    if result.returncode: raise AuthError('Keychain unavailable')
    return result.stdout.decode() if operation == 'get' else None

def post(step, url, form=None, payload=None, extra=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED: raise AuthError('unexpected endpoint')
    if payload is not None:
        data = payload if isinstance(payload, bytes) else json.dumps(payload, separators=(',', ':')).encode()
        ct = 'application/json'
    else:
        data = urllib.parse.urlencode(form).encode(); ct = 'application/x-www-form-urlencoded'
    headers = {'Content-Type': ct, 'Accept': 'application/json'}
    headers.update(extra or {})
    request = urllib.request.Request(url, data=data, headers=headers)
    tls = ssl.create_default_context(cafile=str(HOME / 'runtime/curl-ca-bundle.crt'))
    try:
        with urllib.request.urlopen(request, timeout=15, context=tls) as response:
            status, body = response.status, response.read(131072)
    except urllib.error.HTTPError as e: status, body = e.code, e.read(131072)
    except (urllib.error.URLError, TimeoutError):
        diagnostic(step); raise AuthError('network request failed') from None
    try: doc = json.loads(body)
    except (ValueError, UnicodeError): doc = {}
    if not isinstance(doc, dict): doc = {}
    diagnostic(step, status, doc)
    return status, doc

def b64(value): return base64.urlsafe_b64encode(value).rstrip(b'=').decode()

def device():
    key = ec.generate_private_key(ec.SECP256R1()); pub = key.public_key().public_numbers()
    proof = {'use':'sig','alg':'ES256','kty':'EC','crv':'P-256',
             'x':b64(pub.x.to_bytes(32,'big')),'y':b64(pub.y.to_bytes(32,'big'))}
    body = json.dumps({'RelyingParty':'http://auth.xboxlive.com','TokenType':'JWT',
                      'Properties':{'AuthMethod':'ProofOfPossession','Id':'{'+str(uuid.uuid4())+'}',
                                    'DeviceType':'Win32','SerialNumber':'{'+str(uuid.uuid4())+'}',
                                    'Version':'10.0.19041','ProofKey':proof}}, separators=(',', ':')).encode()
    version = struct.pack('!I',1); stamp = struct.pack('!Q',time.time_ns()//100+116444736000000000)
    message = version+b'\0'+stamp+b'\0POST\0/device/authenticate\0\0'+body[:8192]+b'\0'
    signature = key.sign(hashlib.sha256(message).digest(),ec.ECDSA(Prehashed(hashes.SHA256())))
    r,s = decode_dss_signature(signature)
    encoded = base64.b64encode(version+stamp+r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode()
    status,doc = post('device-auth','https://device.auth.xboxlive.com/device/authenticate',payload=body,
                      extra={'Signature':encoded,'x-xbl-contract-version':'1'})
    if status != 200 or not doc.get('Token'): raise AuthError('device authentication failed')
    return doc['Token']

def services_for(access):
    dt = device()
    ticket = access if access.startswith(('t=','d=')) else ('d=' if access.startswith('eyJ') else 't=')+access
    status,user = post('xbox-user-auth','https://user.auth.xboxlive.com/user/authenticate',
                      payload={'Properties':{'AuthMethod':'RPS','SiteName':'user.auth.xboxlive.com','RpsTicket':ticket},
                               'RelyingParty':'http://auth.xboxlive.com','TokenType':'JWT'})
    if status != 200 or not user.get('Token'): raise AuthError('Xbox sign-in rejected')
    services = {}
    for label,rp in [('xbox','http://xboxlive.com'),('minecraft','rp://api.minecraftservices.com/'),('playfab','http://playfab.xboxlive.com/')]:
        status,doc = post('xsts-'+label,'https://xsts.auth.xboxlive.com/xsts/authorize',
                          payload={'Properties':{'SandboxId':'RETAIL','UserTokens':[user['Token']],'DeviceToken':dt},
                                   'RelyingParty':rp,'TokenType':'JWT'})
        if status != 200 or not doc.get('Token'): raise AuthError('Xbox service token rejected')
        services[label] = doc
    return services

def make_packet(services, expected_xuid=None, now=None):
    now = time.time() if now is None else now
    if set(services) != {'xbox','minecraft','playfab'}: raise AuthError('incomplete session')
    identities = set(); claims = None; deadlines = []
    for label,doc in services.items():
        xui = doc.get('DisplayClaims',{}).get('xui',[])
        if len(xui) != 1 or not xui[0].get('uhs'): raise AuthError('invalid identity')
        if xui[0].get('xid'): identities.add(str(xui[0]['xid']))
        if label == 'xbox': claims = xui[0]
        value = datetime.datetime.fromisoformat(doc['NotAfter'].replace('Z','+00:00'))
        if value.tzinfo is None: raise AuthError('invalid expiry')
        deadlines.append(value.timestamp())
    if len(identities) != 1 or not claims.get('xid') or str(claims['xid']) not in identities:
        raise AuthError('inconsistent identity')
    xid = int(claims['xid'])
    if xid <= 0 or (expected_xuid is not None and xid != expected_xuid): raise AuthError('account changed')
    expires = min(deadlines)  # Exactly the earliest Xbox NotAfter; no diagnostic cap.
    if expires <= now + 120: raise AuthError('token already expiring')
    age = {'Child':1,'Teen':2,'Adult':3}.get(claims.get('agg'),0)
    privileges = claims.get('prv'); known = isinstance(privileges,str); bits = bytearray(32)
    if known:
        for item in privileges.split():
            value = int(item)
            if not 0 <= value < 256: raise AuthError('invalid privileges')
            bits[value//8] |= 1 << (value%8)
    def field(value, size):
        value = value.encode('utf-8')
        if len(value) >= size or b'\0' in value: raise AuthError('invalid token field')
        return value.ljust(size,b'\0')
    tags = field(claims.get('gtg',''),128)+field('',128)*3
    tokens = b''.join(field('XBL3.0 x='+str(services[label]['DisplayClaims']['xui'][0]['uhs'])+';'+services[label]['Token'],16384)
                      for label in ['xbox','minecraft','playfab'])
    generation = time.time_ns()
    return PACKET.pack(MAGIC,int(expires*10000000)+116444736000000000,xid,age,int(known),bytes(bits),tags,tokens,generation)

def session_meta():
    try:
        packet = (HOME/'session.bin').read_bytes()
        if len(packet) != PACKET.size: return None
        magic,expiry,xuid,*_,generation = PACKET.unpack(packet)
        if magic != MAGIC: return None
        return {'expires':(expiry-116444736000000000)/10000000,'xuid':xuid,'generation':generation}
    except (OSError,struct.error): return None

@contextlib.contextmanager
def credential_lock():
    with open(HOME/'credential.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield

def renew():
    with credential_lock():
        if (HOME/'signed-out').exists(): raise AuthError('signed out')
        refresh = keychain('get')
        if not refresh: raise AuthError('sign-in required')
        status,doc = post('microsoft-refresh','https://login.live.com/oauth20_token.srf',
                          form={'client_id':CLIENT,'scope':SCOPE,'grant_type':'refresh_token','refresh_token':refresh})
        if status != 200 or not doc.get('access_token'): raise AuthError('renewal rejected')
        previous = session_meta()
        packet = make_packet(services_for(doc['access_token']), previous['xuid'] if previous else None)
        if (HOME/'signed-out').exists(): raise AuthError('signed out')
        if doc.get('refresh_token'): keychain('set',doc['refresh_token'])
        atomic(HOME/'session.bin',packet)
    diagnostic('renewal-complete')

def interactive(bottle):
    status,start = post('device-code-start','https://login.live.com/oauth20_connect.srf',
                        form={'client_id':CLIENT,'scope':SCOPE,'response_type':'device_code'})
    if status != 200 or not start.get('device_code'): raise AuthError('could not start sign-in')
    url = start.get('verification_uri') or 'https://www.microsoft.com/link'
    if urllib.parse.urlsplit(url).hostname not in {'www.microsoft.com','microsoft.com','login.live.com'}:
        raise AuthError('unexpected sign-in address')
    ui = subprocess.Popen(['/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine',
                           '--bottle',bottle,'--debugmsg','-all',str(HOME/'runtime/signin-ui.exe')],
                          stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    ui.stdin.write(localization.prompt_payload(url,start['user_code'],HOME));ui.stdin.flush()
    try:
        deadline = time.monotonic()+min(start.get('expires_in',600)-5,600)
        interval = max(start.get('interval',5),5)
        while time.monotonic() < deadline:
            if cancelled: raise AuthError('launch cancelled')
            if ui.poll() is not None: raise AuthError('sign-in cancelled')
            time.sleep(interval)
            status,doc = post('device-code-poll','https://login.live.com/oauth20_token.srf',
                              form={'client_id':CLIENT,'grant_type':'urn:ietf:params:oauth:grant-type:device_code',
                                    'device_code':start['device_code']})
            if status == 200 and doc.get('access_token'):
                packet = make_packet(services_for(doc['access_token']))
                with credential_lock():
                    if doc.get('refresh_token'): keychain('set',doc['refresh_token'])
                    (HOME/'signed-out').unlink(missing_ok=True)
                    atomic(HOME/'session.bin',packet)
                return
            if doc.get('error') == 'slow_down': interval += 5
            elif doc.get('error') != 'authorization_pending': raise AuthError('sign-in rejected')
        raise AuthError('sign-in expired')
    finally:
        if ui.poll() is None:
            try: ui.stdin.write(b'close\n');ui.stdin.flush();ui.stdin.close();ui.wait(timeout=8)
            except (BrokenPipeError,subprocess.TimeoutExpired): ui.terminate()

def ready(state):
    atomic(HOME/'status.json',json.dumps({'state':state,'pid':os.getpid(),'updated':time.time()}).encode())

def serve(bottle, allow_interactive):
    with open(HOME/'daemon.lock','a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return
        ready('starting')
        try:
            meta = session_meta()
            if not meta or meta['expires'] < time.time()+300:
                if keychain('get') and not (HOME/'signed-out').exists(): renew()
                elif allow_interactive: interactive(bottle)
                else: raise AuthError('sign-in required')
        except AuthError:
            ready('sign-in-required'); return
        ready('ready'); last_attempt = 0; last_heartbeat = time.time()
        while not (HOME/'signed-out').exists():
            meta = session_meta()
            if not meta: break
            requests = sorted(HOME.glob('refresh-*.req'))
            for request in requests[:32]:
                if len(request.stem) != 24 or any(c not in '0123456789abcdef' for c in request.stem[8:]):
                    request.unlink(missing_ok=True); continue
                code = ERROR; generation = 0
                try:
                    data = request.read_bytes()
                    if len(data) != 16: raise AuthError('invalid request')
                    magic,old = struct.unpack('<QQ',data)
                    if magic != REQUEST_MAGIC: raise AuthError('invalid request')
                    current = session_meta()
                    if not current or current['generation'] == old: renew()
                    current = session_meta()
                    if not current or current['generation'] == old or current['expires'] <= time.time():
                        raise AuthError('no fresh session')
                    code = 0; generation = current['generation']
                except (AuthError,OSError,ValueError,KeyError): diagnostic('forced-renewal-failed')
                atomic(request.with_suffix('.res'),struct.pack('<QQ',code,generation))
                request.unlink(missing_ok=True)
            now = time.time()
            if now-last_heartbeat > 30:
                ready('ready');last_heartbeat = now
            if meta['expires']-now < 300 and now-last_attempt > 60:
                last_attempt = now
                try: renew()
                except AuthError: diagnostic('silent-renewal-failed')
            for response in HOME.glob('refresh-*.res'):
                if now-response.stat().st_mtime > 120: response.unlink(missing_ok=True)
            time.sleep(0.2)
        ready('signed-out')

def sign_out():
    atomic(HOME/'signed-out',b'1')
    with credential_lock():
        keychain('delete')
        (HOME/'session.bin').unlink(missing_ok=True)
        for pattern in ('refresh-*.req','refresh-*.res'):
            for file in HOME.glob(pattern): file.unlink(missing_ok=True)
    ready('signed-out')
    print('Signed out. The Microsoft refresh token and local session were deleted.')

def launch(bottle):
    if cancelled: raise AuthError('launch cancelled')
    diagnostics.record(HOME,'launch_started',{'outcome':'started'})
    status = HOME/'status.json'
    active = False
    try:
        state = json.loads(status.read_text())
        with open(HOME/'daemon.lock','a') as lock:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                fcntl.flock(lock,fcntl.LOCK_UN)
            except BlockingIOError:
                active = state['state'] in {'starting','ready'}
    except (OSError,ValueError,KeyError): pass
    if not active:
        status.unlink(missing_ok=True)
        meta = session_meta()
        if not meta or meta['expires'] < time.time()+300:
            if keychain('get') and not (HOME/'signed-out').exists(): renew()
            else: interactive(bottle)
        # launchd owns renewal independently of the launcher and Codex.
        agent = Path.home()/'Library/LaunchAgents/org.dungeons-crossover.auth.plist'
        domain = 'gui/'+str(os.getuid())
        subprocess.run(['/bin/launchctl','bootstrap',domain,str(agent)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        result = subprocess.run(['/bin/launchctl','kickstart',domain+'/org.dungeons-crossover.auth'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if result.returncode: raise AuthError('background service unavailable')
    print('Waiting for Microsoft/Xbox sign-in. Complete the small sign-in window if it appears.')
    for _ in range(1500):
        if cancelled: raise AuthError('launch cancelled')
        try:
            state = json.loads(status.read_text())['state']
            if state == 'ready': break
            if state in {'sign-in-required','signed-out'}: raise AuthError('sign-in required')
        except (OSError,ValueError,KeyError): pass
        time.sleep(0.5)
    else: raise AuthError('sign-in did not finish')
    if cancelled: raise AuthError('launch cancelled')
    settings = json.loads((HOME/'settings.json').read_text())
    command,working_directory=launch_command(settings,bottle)
    subprocess.Popen(command,cwd=working_directory,
                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    diagnostics.record(HOME,'launch_requested',{'outcome':'success','store':settings.get('store','steam'),'app_version':settings.get('app_version')})
    print(('Steam launch requested.' if settings.get('store','steam')=='steam' else 'Experimental Minecraft Launcher game launch requested. The game still checks ownership.')+' Silent renewal continues in the background.')

def launch_command(settings,bottle):
    """Choose a launch route without changing authentication or entitlement."""
    command=['/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine',
             '--bottle',bottle,'--debugmsg','-all']
    store=settings.get('store','steam')
    if store=='steam':
        return command+[settings.get('steam_exe',r'C:\Program Files (x86)\Steam\steam.exe'),'-applaunch','1912410'],None
    if store!='launcher':raise AuthError('unknown game source')
    game=Path(settings['game']);binary=Path(settings['binary']);executable=settings['game_exe']
    # Refuse arbitrary commands or stale copy paths from hand-edited settings.
    if not game.is_dir() or not binary.is_dir() or not (game/'MicrosoftGame.config').is_file():
        raise AuthError('game copy missing')
    if binary.name not in {'Win64','WinGDK'} or binary.resolve()!=(game/'Dungeons/Binaries'/binary.name).resolve():
        raise AuthError('unknown game layout')
    names={'Dungeons-Win64-Shipping.exe','Dungeons-WinGDK-Shipping.exe'}
    if not isinstance(executable,str) or len(executable)<4 or executable[1:3]!=':\\' or executable[0].upper() not in {'C','Z'} or any(c in executable for c in ('\x00','\r','\n')) or executable.replace('\\','/').rsplit('/',1)[-1] not in names:
        raise AuthError('game executable missing')
    selected=binary/executable.replace('\\','/').rsplit('/',1)[-1]
    if not selected.is_file():
        raise AuthError('game executable missing')
    # Use only the validated file in the selected game. A stale or hand-edited
    # saved Windows directory must never redirect launch to another executable.
    selected=selected.resolve()
    drive=(Path.home()/'Library/Application Support/CrossOver/Bottles'/bottle/'drive_c').resolve()
    try:target='C:\\'+str(selected.relative_to(drive)).replace('/','\\')
    except ValueError:target='Z:'+str(selected).replace('/','\\')
    return command+[target,'Dungeons','-windowed','-ResX=1600','-ResY=900'],str(game)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command',choices=['serve','launch','sign-out','stop-game','status','logs-on','logs-off'])
    parser.add_argument('--bottle',default='Steam');parser.add_argument('--interactive',action='store_true')
    args = parser.parse_args();private_home()
    if args.command == 'launch':
        def cancel(signum, frame):
            global cancelled
            cancelled = True
        # Finish any token rotation already in progress, then stop before the game
        # launches. Interactive sign-in observes the flag and closes its window.
        signal.signal(signal.SIGTERM,cancel)
    if args.command == 'serve': serve(args.bottle,args.interactive)
    elif args.command == 'launch': launch(args.bottle)
    elif args.command == 'stop-game':
        # User-requested recovery for a stuck game, scoped to the chosen bottle.
        selected=json.loads((HOME/'settings.json').read_text())
        executable=selected.get('game_exe','Dungeons-Win64-Shipping.exe').replace('\\','/').rsplit('/',1)[-1]
        if executable not in {'Dungeons-Win64-Shipping.exe','Dungeons-WinGDK-Shipping.exe'}:
            raise AuthError('unknown game executable')
        subprocess.run(['/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine',
                        '--bottle',args.bottle,'--wait','--debugmsg','-all','taskkill.exe',
                        '/F','/IM',executable,'/T'],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    elif args.command == 'sign-out': sign_out()
    elif args.command == 'status':
        meta = session_meta();print(json.dumps({'session_present':meta is not None,
                                              'seconds_remaining':round(meta['expires']-time.time()) if meta else 0}))
    elif args.command == 'logs-on': diagnostics.start(HOME)
    elif args.command == 'logs-off': diagnostics.stop(HOME)

if __name__ == '__main__':
    try: main()
    except (AuthError,OSError,ValueError,KeyError) as error:
        if sys.argv[1:2]==['launch']:diagnostics.record(HOME,'launch_failed',{'outcome':'failed'})
        # Do not stringify exceptions: urllib/server/OS errors may include secrets.
        print('Sign-in helper could not complete the operation. No authentication details were logged.',file=sys.stderr)
        sys.exit(1)
