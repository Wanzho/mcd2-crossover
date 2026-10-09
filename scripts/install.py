#!/usr/bin/env python3
"""Install a locally built adapter into an existing, legitimately owned game.

Game/SDK binaries and authentication data are never part of this repository.
Dependencies are obtained from their original publishers or a local archive.
"""
import argparse, hashlib, io, json, os, plistlib, shutil, subprocess, sys, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from startup import configs, ensure_vc, install_launch, stop_steam, launch_options
from startup import windows_path
from game_copy import inspect_copy, STORES
from game_process import require_idle, RunningGameError
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'helper'))
import diagnostics
HOME = Path.home()/'Library/Application Support/DungeonsCrossOver'
VERSION = '0.1.6'
from crossover import crossover_app
HASHES = {
    'xgameruntime-native.dll':'815d0c5b0aa5c84eb6104168da551a4922f49f8dd02dbdf3bbc5119beec11b59',
    'xgameruntime-adapter-thunks.dll':'862236063d4872f43435384eb4030dfa4b1fb6fbe91fe93969557de18c5f9601',
    'curl-compat.dll':'f31fa58061e162ff4702b37224404df210346df6dff4a49e92d07b8dd5217334',
    'curl-ca-bundle.crt':'1fdcf2a55c9806c4c1e8391cb283871ee3b209d68a2879ce4c0898d949de2545'}
GDK = 'https://api.nuget.org/v3-flatcontainer/microsoft.gdk.windows/2604.4.7897/microsoft.gdk.windows.2604.4.7897.nupkg'
CURL = 'https://curl.se/windows/dl-8.22.0_2/curl-8.22.0_2-win64-mingw.zip'

def digest(data):return hashlib.sha256(data).hexdigest()
def archive(local,url):
    if local:return zipfile.ZipFile(local)
    # macOS curl uses the system trust store, including on a fresh Python install.
    result=subprocess.run(['/usr/bin/curl','--fail','--location','--silent','--show-error',
                           '--connect-timeout','20','--max-time','180',url],capture_output=True,check=True)
    data=result.stdout
    if len(data)>200000000:raise RuntimeError('dependency archive is too large')
    return zipfile.ZipFile(io.BytesIO(data))
def member(z,suffix):
    names=[n for n in z.namelist() if n.endswith(suffix)]
    if len(names)!=1:raise RuntimeError('unexpected dependency archive')
    return z.read(names[0])
def write(path,data,executable=False):
    path=Path(path);temp=path.with_name(path.name+'.installing')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o700 if executable else 0o600)
    try:
        with os.fdopen(fd,'wb') as file:file.write(data)
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bottle',default='Steam')
    parser.add_argument('--game',type=Path)
    parser.add_argument('--store',choices=STORES,default='auto',help='Minecraft Launcher copies are experimental; game ownership is still checked by the original services.')
    parser.add_argument('--gdk-archive',type=Path)
    parser.add_argument('--curl-archive',type=Path)
    parser.add_argument('--accept-gdk-license',action='store_true',help='Accept the Microsoft GDK license linked in README.')
    parser.add_argument('--prepare-only',action='store_true',help='Install helper/dependencies without replacing the running game DLLs.')
    parser.add_argument('--check-only',action='store_true',help='Check the selected game without installing or downloading anything.')
    parser.add_argument('--ignore-other-game-detection',action='store_true',help='Continue past other-game or uncertain process warnings. Steam setup restarts Steam in this bottle. A confirmed running selected copy is always refused.')
    args=parser.parse_args();os.umask(0o077)
    bottle=Path.home()/'Library/Application Support/CrossOver/Bottles'/args.bottle
    selected=args.game or bottle/'drive_c/Program Files (x86)/Steam/steamapps/common/Minecraft Dungeons II'
    copy=inspect_copy(selected,args.store)
    game=Path(copy['root']);binary=Path(copy['binary']);store=copy['store']
    selected_crossover = crossover_app()
    def check_running(shared_steam=False):
        require_idle(copy['executable'], bottle, shared_steam=shared_steam,
                     ignore_other=args.ignore_other_game_detection)
    if not args.prepare_only:
        check_running(shared_steam=store=='steam' and not args.check_only)
        # Only Steam copies need Steam profiles and launch settings.
        if store=='steam':
            for path in configs(bottle):
                launch_options(path.read_bytes().decode('utf-8'), '')
    if args.check_only:
        print('The selected game is ready for installation.');return
    diagnostics.record(HOME,'setup_started',{'outcome':'started','store':store,'app_version':VERSION})
    HOME.mkdir(parents=True,mode=0o700,exist_ok=True);os.chmod(HOME,0o700)
    write(HOME/'crossover-app.json',json.dumps({'path':str(selected_crossover)}).encode())
    runtime=HOME/'runtime';runtime.mkdir(mode=0o700,exist_ok=True)
    if not args.prepare_only:
        ensure_vc(bottle, args.bottle, runtime, game)
        check_running(shared_steam=store=='steam')
        if store=='steam':stop_steam(bottle, args.bottle)
        backup=HOME/'backups'/str(time.time_ns());backup.mkdir(parents=True,mode=0o700)
        # Keep the previous helper/settings too, before updating them. Credentials
        # are not exported into the backup or release.
        for relative in ('runtime/keychain','runtime/signin-ui.exe','runtime/bridge.py','runtime/diagnostics.py','runtime/localization.py','runtime/session_watch.py','runtime/game_process.py','runtime/crossover.py','settings.json','installation.json'):
            previous=HOME/relative
            if previous.is_file():
                dest=backup/'helper'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(previous,dest)
        previous_catalogs=runtime/'localization'
        if previous_catalogs.is_dir() and not previous_catalogs.is_symlink():
            shutil.copytree(previous_catalogs,backup/'helper/runtime/localization')
    for name in ('Microsoft-GDK-LICENSE.md','curl-LICENSE.txt'):
        notice=ROOT/'licenses'/name
        if notice.exists():write(runtime/name,notice.read_bytes())
    dependencies={}
    if all((binary/name).exists() and digest((binary/name).read_bytes())==HASHES[name] for name in HASHES):
        dependencies={name:(binary/name).read_bytes() for name in HASHES}
    else:
        if not args.accept_gdk_license:raise SystemExit('Read the Microsoft GDK license in README, then use --accept-gdk-license to download it.')
        with archive(args.gdk_archive,GDK) as z:
            dependencies['xgameruntime-native.dll']=member(z,'native/260404/windows/bin/x64/xgameruntime.dll')
            dependencies['xgameruntime-adapter-thunks.dll']=member(z,'native/260404/windows/bin/x64/xgameruntime.thunks.dll')
            write(runtime/'Microsoft-GDK-LICENSE.md',member(z,'LICENSE.md'))
        with archive(args.curl_archive,CURL) as z:
            dependencies['curl-compat.dll']=member(z,'/bin/libcurl-x64.dll')
            dependencies['curl-ca-bundle.crt']=member(z,'/bin/curl-ca-bundle.crt')
            license_names=[n for n in z.namelist() if n.endswith('/COPYING.txt')]
            if license_names:write(runtime/'curl-LICENSE.txt',z.read(license_names[0]))
    for name,data in dependencies.items():
        if digest(data)!=HASHES[name]:raise RuntimeError('dependency checksum mismatch: '+name)
    for name in ('keychain','signin-ui.exe'):
        write(runtime/name,(ROOT/'build'/name).read_bytes(),True)
    write(runtime/'bridge.py',(ROOT/'helper/bridge.py').read_bytes())
    write(runtime/'session_watch.py',(ROOT/'helper/session_watch.py').read_bytes())
    write(runtime/'crossover.py',(ROOT/'scripts/crossover.py').read_bytes())
    write(runtime/'game_process.py',(ROOT/'scripts/game_process.py').read_bytes())
    write(runtime/'diagnostics.py',(ROOT/'helper/diagnostics.py').read_bytes())
    write(runtime/'localization.py',(ROOT/'helper/localization.py').read_bytes())
    for catalog in sorted((ROOT/'localization').glob('*.json')):
        destination=runtime/'localization';destination.mkdir(mode=0o700,exist_ok=True)
        write(destination/catalog.name,catalog.read_bytes())
    write(runtime/'curl-ca-bundle.crt',dependencies['curl-ca-bundle.crt'])
    env=HOME/'python'
    bundled=ROOT/'python'
    if not (env/'bin/python').exists():
        if (bundled/'bin/python').exists():shutil.copytree(bundled,env,symlinks=True)
        else:subprocess.run([sys.executable,'-m','venv',str(env)],check=True)
    check=subprocess.run([str(env/'bin/python'),'-c','from cryptography.hazmat.primitives.asymmetric import ec; ec.generate_private_key(ec.SECP256R1())'],capture_output=True)
    if check.returncode:subprocess.run([str(env/'bin/python'),'-m','pip','install','-r',str(ROOT/'helper/requirements.txt')],check=True)
    settings={'crossover_app':str(selected_crossover),'bottle':args.bottle,'game':str(game),'store':store,
              'game_exe':windows_path(Path(copy['executable']),bottle),'binary':str(binary),
              'launcher':'steam' if store=='steam' else 'direct',
              'experimental':copy['experimental']}
    if store=='steam':settings['steam_exe']=r'C:\Program Files (x86)\Steam\steam.exe'
    if args.prepare_only and (HOME/'settings.json').exists():
        settings.update(json.loads((HOME/'settings.json').read_text()))
    agents=Path.home()/'Library/LaunchAgents';agents.mkdir(parents=True,exist_ok=True)
    agent={'Label':'org.dungeons-crossover.auth',
           'ProgramArguments':[str(env/'bin/python'),'-I','-B',str(runtime/'bridge.py'),'serve','--bottle',args.bottle],
           'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':30,
           'ProcessType':'Background','Umask':63}
    write(agents/'org.dungeons-crossover.auth.plist',plistlib.dumps(agent))
    if args.prepare_only:
        write(HOME/'settings.json',json.dumps(settings,indent=2).encode())
        diagnostics.record(HOME,'setup_completed',{'outcome':'success','store':settings.get('store','steam'),'app_version':VERSION})
        print('Per-user helper prepared. The running game and its DLLs were left intact.');return
    # Downloads and installer windows can take time. Recheck immediately before
    # publishing selected game DLLs, with the same explicit retry policy.
    check_running(shared_steam=store=='steam')
    installed={}
    data={**dependencies,'xgameruntime.dll':(ROOT/'build/xgameruntime.dll').read_bytes(),
          'XCurl.dll':(ROOT/'build/XCurl.dll').read_bytes(),
          'dungeons-crossover.ini':('Z:'+str(HOME).replace('/','\\')+'\n').encode()}
    for name,value in data.items():
        dest=binary/name
        if dest.exists():shutil.copy2(dest,backup/name)
        write(dest,value);installed[name]=digest(value)
    option = install_launch(bottle, game, backup, write) if store=='steam' else None
    # Retire the previous separate launchers only after the new setup succeeds.
    for name in ('Minecraft Dungeons II.app','Sign out.app','Launch Minecraft Dungeons II.command','Sign out.command'):
        old = HOME/name
        if old.exists():shutil.move(str(old),str(backup/name))
    settings['app_version'] = VERSION
    write(HOME/'settings.json',json.dumps(settings,indent=2).encode())
    write(HOME/'installation.json',json.dumps({'game':str(game),'binary':str(binary),'executable':copy['executable'],
          'store':store,'experimental':copy['experimental'],'backup':str(backup),'files':installed,
          'steam_launch_options':option},indent=2).encode())
    diagnostics.record(HOME,'setup_completed',{'outcome':'success','store':store,'app_version':VERSION})
    print('Setup complete. Press Play in MCD2 Crossover. '+('Steam will reopen when you play.' if store=='steam' else 'This Minecraft Launcher copy is experimental; the game still checks ownership.'))

if __name__=='__main__':
    try:main()
    except RunningGameError as error:
        if '--check-only' not in sys.argv[1:]:
            diagnostics.record(HOME,'setup_failed',{'outcome':'failed','app_version':VERSION})
        print(error.marker,file=sys.stderr)
        print(str(error),file=sys.stderr)
        raise SystemExit(error.exit_code)
    except (RuntimeError,ValueError,OSError,subprocess.CalledProcessError) as error:
        if '--check-only' not in sys.argv[1:]:
            diagnostics.record(HOME,'setup_failed',{'outcome':'failed','app_version':VERSION})
        raise SystemExit(str(error))
