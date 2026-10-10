import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import runpy
import unittest
from contextlib import ExitStack, redirect_stderr
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('copy_install',Path(__file__).parents[1]/'scripts/install.py')
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


class CopyInstallationTests(unittest.TestCase):
    """All executable calls and dependency downloads are intercepted."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.user = Path(self.temp.name).resolve()/'user'
        self.home = self.user/'Library/Application Support/DungeonsCrossOver'
        self.bottle = self.user/'Library/Application Support/CrossOver/Bottles/Test'
        self.source = Path(self.temp.name)/'source'
        for name in ('build/keychain','build/signin-ui.exe','build/xgameruntime.dll','build/XCurl.dll',
                     'helper/bridge.py','helper/diagnostics.py','helper/localization.py','helper/internal_errors.py','helper/error_codes.json',
                     'helper/session_watch.py','scripts/game_process.py','scripts/crossover.py'):
            file = self.source/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'synthetic build fixture')
        env = self.home/'python/bin/python';env.parent.mkdir(parents=True);env.write_bytes(b'not executed')
        (self.source/'localization').mkdir()
        (self.source/'localization/en.json').write_text('{"Play":"Play"}')
        (self.source/'localization/languages.json').write_text('{"languages":[{"id":"en"}]}')
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(install,'ROOT',self.source))
        self.stack.enter_context(patch.object(install,'HOME',self.home))
        self.stack.enter_context(patch.object(install,'crossover_app',return_value=self.source))
        self.stack.enter_context(patch.object(Path,'home',return_value=self.user))
        self.run = self.stack.enter_context(patch.object(install.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='',stderr='')))
        self.steam_stop = self.stack.enter_context(patch.object(install,'stop_steam'))
        self.vc = self.stack.enter_context(patch.object(install,'ensure_vc'))
        self.archive = self.stack.enter_context(patch.object(install,'archive',side_effect=AssertionError('No network call allowed in this test')))

    def tearDown(self):
        self.stack.close();self.temp.cleanup()

    def copy(self, platform='WinGDK', name='Dungeons-WinGDK-Shipping.exe'):
        self.game = self.bottle/'drive_c/Game'
        self.binary = self.game/'Dungeons/Binaries'/platform
        self.binary.mkdir(parents=True)
        (self.game/'MicrosoftGame.config').write_bytes(b'<Game/>')
        self.executable = self.binary/name
        self.executable.write_bytes(b'untouched synthetic game')
        self.hashes = {}
        for name in install.HASHES:
            value = ('synthetic '+name).encode()
            (self.binary/name).write_bytes(value)
            self.hashes[name] = install.digest(value)
        self.stack.enter_context(patch.object(install,'HASHES',self.hashes))

    def invoke(self, *options):
        with patch.object(sys,'argv',['install.py','--bottle','Test','--game',str(self.executable),*options]):
            install.main()

    def steam_config(self):
        config = self.bottle/'drive_c/Program Files (x86)/Steam/userdata/fixture/config/localconfig.vdf'
        config.parent.mkdir(parents=True)
        config.write_bytes(b'"UserLocalConfigStore" { "Software" { "Valve" { "Steam" { "apps" { "1912410" {} } } } } }')
        return config

    def fake_process(self, physical, windows=None, active_after=0):
        # All executable calls remain intercepted, including the Python
        # cryptography availability check performed by setup.
        queries = 0
        windows = windows or install.windows_path(physical, self.bottle)
        def run(args, **kwargs):
            nonlocal queries
            if args == ['/bin/ps','-axo','pid=,comm=']:
                queries += 1
                text = '701 '+windows+'\n' if queries > active_after else ''
                return subprocess.CompletedProcess(args,0,stdout=text,stderr='')
            if args == ['/usr/sbin/lsof','-a','-p','701','-Fpn']:
                return subprocess.CompletedProcess(args,0,stdout='p701\nn'+str(physical)+'\n',stderr='')
            self.assertEqual(args[0],str(self.home/'python/bin/python'))
            self.assertIn('cryptography',args[-1])
            return subprocess.CompletedProcess(args,0,stdout='',stderr='')
        self.run.side_effect = run

    def test_launcher_install_does_not_read_stop_or_change_steam(self):
        self.copy()
        (self.binary/'XCurl.dll').write_bytes(b'original game curl')
        (self.home/'session.bin').write_bytes(b'synthetic session left intact')
        with patch.object(install,'configs',side_effect=AssertionError('Launcher setup must not access Steam')):
            self.invoke()
        settings = json.loads((self.home/'settings.json').read_text())
        self.assertEqual(settings['store'],'launcher')
        self.assertEqual(settings['launcher'],'direct')
        self.assertTrue(settings['experimental'])
        self.assertEqual(settings['game'],str(self.game))
        self.assertEqual(settings['binary'],str(self.binary))
        self.assertEqual(settings['game_exe'],r'C:\Game\Dungeons\Binaries\WinGDK\Dungeons-WinGDK-Shipping.exe')
        self.assertNotIn('steam_exe',settings)
        self.steam_stop.assert_not_called()
        self.assertFalse((self.game/'MCD2CrossoverLaunch.cmd').exists())
        record = json.loads((self.home/'installation.json').read_text())
        self.assertIsNone(record['steam_launch_options'])
        self.assertEqual((Path(record['backup'])/'XCurl.dll').read_bytes(),b'original game curl')
        self.assertEqual(self.executable.read_bytes(),b'untouched synthetic game')
        self.assertEqual((self.home/'session.bin').read_bytes(),b'synthetic session left intact')
        self.assertTrue((self.home/'runtime/diagnostics.py').is_file())

    def test_steam_setup_preserves_launch_settings_for_other_games(self):
        self.copy('Win64','Dungeons-Win64-Shipping.exe')
        config = self.bottle/'drive_c/Program Files (x86)/Steam/userdata/fixture/config/localconfig.vdf'
        config.parent.mkdir(parents=True)
        original = b'"UserLocalConfigStore" { "Software" { "Valve" { "Steam" { "apps" { "1912410" {} "123" { "LaunchOptions" "-unchanged" } } } } } }'
        config.write_bytes(original)
        self.invoke()
        self.steam_stop.assert_called_once_with(self.bottle,'Test')
        settings = json.loads((self.home/'settings.json').read_text())
        self.assertEqual(settings['store'],'steam')
        self.assertFalse(settings['experimental'])
        self.assertTrue((self.game/'MCD2CrossoverLaunch.cmd').is_file())
        self.assertIn('"123" { "LaunchOptions" "-unchanged" }',config.read_text())
        record = json.loads((self.home/'installation.json').read_text())
        self.assertEqual((Path(record['backup'])/'steam-0-localconfig.vdf').read_bytes(),original)

    def test_launcher_check_only_leaves_copy_and_settings_untouched(self):
        self.copy()
        before = {str(p.relative_to(self.game)):p.read_bytes() for p in self.game.rglob('*') if p.is_file()}
        with patch.object(install,'configs',side_effect=AssertionError('No Steam lookup allowed')):
            self.invoke('--check-only')
        self.vc.assert_not_called();self.steam_stop.assert_not_called()
        self.assertFalse((self.home/'settings.json').exists())
        after = {str(p.relative_to(self.game)):p.read_bytes() for p in self.game.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_selected_running_copy_cannot_be_overridden_before_any_mutation(self):
        self.copy()
        self.fake_process(self.executable)
        before = {str(p):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        for options in ((),('--ignore-other-game-detection',)):
            with self.subTest(options=options), self.assertRaises(install.RunningGameError) as failure:
                self.invoke(*options)
            self.assertEqual((failure.exception.marker,failure.exception.exit_code),('MCD2_RUNNING_SELECTED',20))
        self.vc.assert_not_called();self.steam_stop.assert_not_called();self.archive.assert_not_called()
        after = {str(p):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_shared_d1_warning_requires_explicit_retry_flag(self):
        self.copy('Win64','Dungeons-Win64-Shipping.exe');self.steam_config()
        d1=self.bottle/'drive_c/Program Files (x86)/Steam/steamapps/common/MinecraftDungeons/Dungeons/Binaries/Win64/Dungeons-Win64-Shipping.exe'
        d1.parent.mkdir(parents=True);d1.write_bytes(b'untouched D1 fixture')
        self.fake_process(d1)
        with self.assertRaises(install.RunningGameError) as failure:
            self.invoke()
        self.assertEqual((failure.exception.marker,failure.exception.exit_code),('MCD2_RUNNING_SHARED_STEAM',21))
        self.vc.assert_not_called();self.steam_stop.assert_not_called()
        self.invoke('--ignore-other-game-detection')
        self.steam_stop.assert_called_once_with(self.bottle,'Test')
        self.assertEqual(d1.read_bytes(),b'untouched D1 fixture')

    def test_game_started_during_vc_check_prevents_steam_shutdown(self):
        self.copy('Win64','Dungeons-Win64-Shipping.exe');config=self.steam_config()
        (self.binary/'XCurl.dll').write_bytes(b'original curl')
        before=config.read_bytes()
        self.fake_process(self.executable,active_after=1)
        with self.assertRaises(install.RunningGameError) as failure:
            self.invoke('--ignore-other-game-detection')
        self.assertEqual(failure.exception.exit_code,20)
        self.vc.assert_called_once();self.steam_stop.assert_not_called()
        self.assertEqual(config.read_bytes(),before)
        self.assertEqual((self.binary/'XCurl.dll').read_bytes(),b'original curl')

    def test_game_started_after_preparation_prevents_final_dll_publication(self):
        self.copy('Win64','Dungeons-Win64-Shipping.exe');self.steam_config()
        (self.binary/'XCurl.dll').write_bytes(b'original curl')
        self.fake_process(self.executable,active_after=2)
        with self.assertRaises(install.RunningGameError) as failure:
            self.invoke('--ignore-other-game-detection')
        self.assertEqual(failure.exception.exit_code,20)
        self.steam_stop.assert_called_once()
        self.assertEqual((self.binary/'XCurl.dll').read_bytes(),b'original curl')
        self.assertFalse((self.home/'settings.json').exists())
        self.assertFalse((self.game/'MCD2CrossoverLaunch.cmd').exists())

    def test_check_only_ignores_shared_steam_activity_without_mutations(self):
        self.copy('Win64','Dungeons-Win64-Shipping.exe');self.steam_config()
        d1=self.bottle/'drive_c/Other/Dungeons/Binaries/Win64/Dungeons-Win64-Shipping.exe'
        d1.parent.mkdir(parents=True);d1.write_bytes(b'untouched D1 fixture')
        self.fake_process(d1)
        before={str(p):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        self.invoke('--check-only')
        self.vc.assert_not_called();self.steam_stop.assert_not_called()
        after={str(p):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_cli_marker_and_exit_are_stable_for_running_check_only(self):
        self.copy();self.fake_process(self.executable)
        before={str(p):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        stderr=io.StringIO()
        argv=['install.py','--bottle','Test','--game',str(self.executable),'--check-only','--ignore-other-game-detection']
        with patch.object(sys,'argv',argv),redirect_stderr(stderr),self.assertRaises(SystemExit) as failure:
            runpy.run_path(str(Path(__file__).parents[1]/'scripts/install.py'),run_name='__main__')
        self.assertEqual(failure.exception.code,20)
        self.assertEqual(stderr.getvalue().splitlines()[0],'MCD2_RUNNING_SELECTED')
        after={str(p):p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        self.assertEqual(before,after)


if __name__ == '__main__':
    unittest.main()
