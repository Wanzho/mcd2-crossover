#!/usr/bin/env python3
"""Install the release into a disposable game fixture, never the actual game."""
import argparse, importlib.util, json, plistlib, shutil, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode = True

def main():
    p=argparse.ArgumentParser();p.add_argument('--app',type=Path,required=True);p.add_argument('--game',type=Path,required=True)
    p.add_argument('--gdk-archive',type=Path,required=True);p.add_argument('--curl-archive',type=Path,required=True)
    args=p.parse_args();resources=args.app/'Contents/Resources'
    spec=importlib.util.spec_from_file_location('installer',resources/'scripts/install.py')
    install=importlib.util.module_from_spec(spec);spec.loader.exec_module(install)
    actual_run=subprocess.run
    with tempfile.TemporaryDirectory(prefix='dungeons-install-test-') as temp:
        root=Path(temp);user=root/'user';home=user/'Library/Application Support/DungeonsCrossOver'
        bottle=user/'Library/Application Support/CrossOver/Bottles/Fixture'
        game=bottle/'drive_c/Game';binary=game/'Dungeons/Binaries/Win64';binary.mkdir(parents=True)
        config=bottle/'drive_c/Program Files (x86)/Steam/userdata/fixture/config/localconfig.vdf'
        config.parent.mkdir(parents=True)
        original_config=b'"UserLocalConfigStore" { "Software" { "Valve" { "Steam" { "apps" { "1912410" { } "123" { "LaunchOptions" "-keep" } } } } } }'
        config.write_bytes(original_config)
        (game/'MicrosoftGame.config').write_text('<Game/>')
        (binary/'Dungeons-Win64-Shipping.exe').write_bytes(b'untouched game fixture')
        for name in install.HASHES:shutil.copyfile(args.game/'Dungeons/Binaries/Win64'/name,binary/name)
        original=b'original DLL fixture';(binary/'XCurl.dll').write_bytes(original)
        (binary/'xgameruntime.dll').write_bytes(original)
        argv=['install.py','--bottle','Fixture','--game',str(game)]
        def run(argv,*a,**kw):
            if argv[:2]==['ps','-axo']:return subprocess.CompletedProcess(argv,0,stdout='Dungeons-Win64-Shipping.exe\n')
            return actual_run(argv,*a,**kw)
        with patch.object(install,'HOME',home),patch.object(Path,'home',return_value=user),patch.object(sys,'argv',argv),patch.object(install.subprocess,'run',side_effect=run):
            try:install.main()
            except SystemExit as error:assert 'quit the game' in str(error)
            else:raise AssertionError('Installer did not refuse a running game')
            assert not home.exists();assert (binary/'XCurl.dll').read_bytes()==original
        def idle(argv,*a,**kw):
            if argv[:2]==['ps','-axo']:return subprocess.CompletedProcess(argv,0,stdout='')
            return actual_run(argv,*a,**kw)
        with patch.object(install,'HOME',home),patch.object(Path,'home',return_value=user),patch.object(sys,'argv',argv),patch.object(install.subprocess,'run',side_effect=idle),patch.object(install,'ensure_vc'),patch.object(install,'stop_steam'):install.main()
        record=json.loads((home/'installation.json').read_text())
        assert (Path(record['backup'])/'XCurl.dll').read_bytes()==original
        assert (binary/'Dungeons-Win64-Shipping.exe').read_bytes()==b'untouched game fixture'
        for name,digest in record['files'].items():assert install.digest((binary/name).read_bytes())==digest
        assert (home.stat().st_mode&0o777)==0o700
        assert not (home/'session.bin').exists();assert not (home/'logging.enabled').exists()
        job=plistlib.loads((user/'Library/LaunchAgents/org.dungeons-crossover.auth.plist').read_bytes())
        assert job['ProgramArguments'][0]==str(home/'python/bin/python')
        assert job['ProgramArguments'][-1]=='Fixture'
        assert job['KeepAlive']=={'SuccessfulExit':False}
        assert json.loads((home/'settings.json').read_text())['app_version']==install.VERSION
        assert (game/'MCD2CrossoverLaunch.cmd').exists()
        assert (Path(record['backup'])/'steam-0-localconfig.vdf').read_bytes()==original_config
        assert '"123" { "LaunchOptions" "-keep" }' in config.read_text()
        assert not (home/'Sign out.app').exists()
        relocated=actual_run([str(home/'python/bin/python'),'-c','from cryptography.hazmat.primitives.asymmetric import ec; ec.generate_private_key(ec.SECP256R1()); print("relocated runtime OK")'],capture_output=True,text=True,check=True)
        print(relocated.stdout.strip())
        before=(binary/'XCurl.dll').read_bytes()
        before_config=config.read_bytes()
        with patch.object(install,'HOME',home),patch.object(Path,'home',return_value=user),patch.object(sys,'argv',argv+['--prepare-only']),patch.object(install.subprocess,'run',side_effect=run):install.main()
        assert (binary/'XCurl.dll').read_bytes()==before
        assert config.read_bytes()==before_config
        print('Installer smoke check passed: running-game guard, backups, relocated runtime, Steam launch route and prepare-only.')
        # Switching the selected bottle must leave the shared account and the
        # previous bottle's game/Steam files alone.
        session=b'synthetic shared session';(home/'session.bin').write_bytes(session)
        (home/'signed-out').write_bytes(b'synthetic marker left as-is')
        next_bottle=user/'Library/Application Support/CrossOver/Bottles/Second'
        next_game=next_bottle/'drive_c/Game';next_binary=next_game/'Dungeons/Binaries/Win64'
        next_binary.mkdir(parents=True)
        (next_game/'MicrosoftGame.config').write_text('<Game/>')
        (next_binary/'Dungeons-Win64-Shipping.exe').write_bytes(b'second game fixture')
        next_config=next_bottle/'drive_c/Program Files (x86)/Steam/userdata/fixture/config/localconfig.vdf'
        next_config.parent.mkdir(parents=True);next_config.write_bytes(original_config)
        previous_settings=(home/'settings.json').read_bytes()
        with patch.object(install,'HOME',home),patch.object(Path,'home',return_value=user),patch.object(sys,'argv',['install.py','--bottle','Second','--game',str(next_game),'--gdk-archive',str(args.gdk_archive),'--curl-archive',str(args.curl_archive),'--accept-gdk-license']),patch.object(install.subprocess,'run',side_effect=idle),patch.object(install,'ensure_vc'),patch.object(install,'stop_steam'):
            install.main()
        assert json.loads((home/'settings.json').read_text())['bottle']=='Second'
        assert json.loads((home/'settings.json').read_text())['game']==str(next_game)
        assert (home/'session.bin').read_bytes()==session
        assert (home/'signed-out').read_bytes()==b'synthetic marker left as-is'
        assert config.read_bytes()==before_config
        assert (binary/'XCurl.dll').read_bytes()==before
        assert (next_game/'MCD2CrossoverLaunch.cmd').exists()
        record=json.loads((home/'installation.json').read_text())
        for name,digest in record['files'].items():assert install.digest((next_binary/name).read_bytes())==digest
        assert (Path(record['backup'])/'helper/settings.json').read_bytes()==previous_settings
        job=plistlib.loads((user/'Library/LaunchAgents/org.dungeons-crossover.auth.plist').read_bytes())
        assert job['ProgramArguments'][-1]=='Second'
        print('Bottle switch check passed: saved account preserved, new bottle set up, previous bottle intact and settings backed up.')

if __name__=='__main__':main()
