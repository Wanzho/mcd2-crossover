import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup', ROOT/'scripts/startup.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

VDF = '''"UserLocalConfigStore"
{
 "Software" { "Valve" { "Steam" { "apps" {
  "1912410" { "LastPlayed" "1234" "LaunchOptions" "-old \\\"option\\\"" }
  // Another game and unrelated settings must retain their exact bytes.
  "123" { "LaunchOptions" "-user-setting" "Cloud" { "value" "same" } }
 } "OtherSetting" "keep" } } }
 "friends" { "fixture" "untouched" }
}
'''

def registry(minor=51):
    return '[Software\\\\Microsoft\\\\VisualStudio\\\\14.0\\\\VC\\\\Runtimes\\\\X64]\n"Installed"=dword:00000001\n"Major"=dword:0000000e\n"Minor"=dword:'+f'{minor:08x}'+'\n'

def runtime(bottle, minor=51):
    bottle.mkdir(parents=True,exist_ok=True); (bottle/'system.reg').write_text(registry(minor))
    dlls=bottle/'drive_c/windows/system32';dlls.mkdir(parents=True,exist_ok=True)
    for n in ('msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll','ucrtbase.dll'):(dlls/n).write_bytes(b'dll fixture')

class StartupTests(unittest.TestCase):
    def test_launch_options_preserve_other_settings_and_escaping(self):
        value='"C:\\windows\\system32\\cmd.exe" /c ""C:\\Game Folder\\MCD2CrossoverLaunch.cmd" %command%"'
        changed,previous=s.launch_options(VDF,value)
        self.assertEqual(previous,'-old "option"')
        unchanged='"123" { "LaunchOptions" "-user-setting" "Cloud" { "value" "same" } }'
        self.assertIn(unchanged,changed);self.assertIn('"friends" { "fixture" "untouched" }',changed)
        self.assertEqual(s.launch_options(changed,value)[0],changed)
        self.assertEqual(s.launch_options(changed,previous)[0],VDF)

    def test_insert_missing_app_or_option(self):
        without_option=VDF.replace(' "LaunchOptions" "-old \\\"option\\\""','')
        added,previous=s.launch_options(without_option,'test')
        self.assertIsNone(previous);self.assertEqual(s.launch_options(added,'test')[0],added)
        without_app=VDF.replace('  "1912410" { "LastPlayed" "1234" "LaunchOptions" "-old \\\"option\\\"" }\n','')
        added,previous=s.launch_options(without_app,'test')
        self.assertIsNone(previous);self.assertEqual(s.launch_options(added,'test')[0],added)

    def test_invalid_or_duplicate_config_refused(self):
        for value in ('bad settings', VDF+'{', VDF.replace('"LastPlayed" "1234"','"LaunchOptions" "duplicate"')):
            with self.assertRaises(ValueError):s.launch_options(value,'test')

    def test_real_runtime_not_older_installer(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t)/'bottle';runtime(b)
            self.assertTrue(s.vc_installed(b))
            with patch.object(s.subprocess,'run') as run:s.ensure_vc(b,'Test',Path(t));run.assert_not_called()
            runtime(b,41);self.assertFalse(s.vc_installed(b))
            runtime(b,42);self.assertTrue(s.vc_installed(b))
            (b/'drive_c/windows/system32/vcruntime140_1.dll').unlink();self.assertFalse(s.vc_installed(b))

    def test_installed_vc_registry_key_case_does_not_trigger_repair(self):
        # Microsoft's 14.51 installer writes lowercase x64 in a real Wine
        # registry, with a timestamp after the section name.
        keys = (
            r'Software\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64',
            r'Software\\Wow6432Node\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64',
            r'software\\MICROSOFT\\VISUALSTUDIO\\14.0\\vc\\runtimes\\X64',
        )
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); b = root/'bottle'; runtime(b)
            for key in keys:
                with self.subTest(key=key):
                    values = registry().split('\n', 1)[1]
                    (b/'system.reg').write_text('['+key+'] 1790798677\n#time=1dd5116ebb6a508\n'+values)
                    self.assertTrue(s.vc_installed(b))
                    with patch.object(s.subprocess, 'run') as run:
                        s.ensure_vc(b, 'Test', root)
                        run.assert_not_called()
            (b/'system.reg').write_text(registry().replace('X64', 'x86'))
            self.assertFalse(s.vc_installed(b))

    def test_registered_wine_builtin_runtime_is_not_microsoft_runtime(self):
        with tempfile.TemporaryDirectory() as t:
            b = Path(t)/'bottle'
            for name in ('msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'):
                with self.subTest(name=name):
                    runtime(b, 42)
                    self.assertTrue(s.vc_installed(b))
                    (b/'drive_c/windows/system32'/name).write_bytes(b'MZ\0\0Wine builtin DLL\0')
                    self.assertFalse(s.vc_installed(b))

    def test_real_vc_with_wine_ucrt_does_not_trigger_repair(self):
        # Both working real bottles retain Wine's UCRT after Microsoft's VC
        # installer replaces the three VC DLLs. Requiring a native UCRT loops.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); b = root/'bottle'; runtime(b)
            (b/'drive_c/windows/system32/ucrtbase.dll').write_bytes(b'MZ\0Wine builtin DLL\0')
            self.assertTrue(s.vc_installed(b))
            with patch.object(s.subprocess, 'run') as commands:
                s.ensure_vc(b, 'Test', root)
                commands.assert_not_called()
            (b/'drive_c/windows/system32/ucrtbase.dll').unlink()
            self.assertFalse(s.vc_installed(b))

    def test_wine_builtin_runtime_opens_real_installer(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); b = root/'bottle'; runtime(b, 42)
            (b/'drive_c/windows/system32/msvcp140.dll').write_bytes(b'MZ\0Wine builtin DLL\0')
            def run(args, **kwargs):
                if args[0] == '/usr/bin/curl':
                    Path(args[-1]).write_bytes(b'MZ'+b'\0'*1000000)
                else:
                    self.assertEqual(args[0], s.WINE)
                    self.assertNotIn('/quiet', args)
                    runtime(b)
                return subprocess.CompletedProcess(args, 0)
            with patch.object(s.subprocess, 'run', side_effect=run) as commands:
                s.ensure_vc(b, 'Test', root)
                self.assertEqual(commands.call_count, 2)
            self.assertTrue(s.vc_installed(b))

    def test_missing_vc_uses_microsoft_license_ui(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);b=root/'bottle';b.mkdir()
            def run(args,**kwargs):
                if args[0]=='/usr/bin/curl':Path(args[-1]).write_bytes(b'MZ'+b'\0'*1000000)
                else:
                    self.assertEqual(args[-1],str(root/'vc_redist.x64.exe'))
                    self.assertNotIn('/quiet',args);self.assertNotIn('/passive',args)
                    runtime(b)
                return subprocess.CompletedProcess(args,0)
            with patch.object(s.subprocess,'run',side_effect=run):s.ensure_vc(b,'Test',root)
            self.assertFalse((root/'vc_redist.x64.exe').exists())

    def test_backup_and_launch_route(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);b=root/'Bottle';game=b/'drive_c/Game Folder';game.mkdir(parents=True)
            cfg=b/'drive_c/Program Files (x86)/Steam/userdata/fixture/config/localconfig.vdf';cfg.parent.mkdir(parents=True);cfg.write_bytes(VDF.encode())
            (game/s.LAUNCHER).write_bytes(b'previous command');backup=root/'backup';backup.mkdir()
            def write(p,data):p.write_bytes(data)
            s.install_launch(b,game,backup,write)
            self.assertEqual((backup/'steam-0-localconfig.vdf').read_bytes(),VDF.encode())
            self.assertEqual((backup/s.LAUNCHER).read_bytes(),b'previous command')
            self.assertIn(b'Shipping.exe" Dungeons -windowed',(game/s.LAUNCHER).read_bytes())
            self.assertNotIn(b'SteamDeck',(game/s.LAUNCHER).read_bytes())
            self.assertIn('MCD2CrossoverLaunch.cmd',cfg.read_text())

    def test_failed_download_uses_bundled_installer_and_checks_result(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);b=root/'bottle';b.mkdir();game=root/'game'
            bundled=game/'Engine/Extras/Redist/en-us/vc_redist.x64.exe';bundled.parent.mkdir(parents=True);bundled.write_bytes(b'bundled installer fixture')
            def run(args,**kwargs):
                if args[0]=='/usr/bin/curl':
                    Path(args[-1]).write_bytes(b'partial download')
                    raise subprocess.CalledProcessError(22,args)
                self.assertEqual(args[-1],str(bundled));self.assertNotIn('/quiet',args)
                runtime(b,42)
                return subprocess.CompletedProcess(args,0)
            with patch.object(s.subprocess,'run',side_effect=run):s.ensure_vc(b,'Test',root,game)
            self.assertTrue(s.vc_installed(b));self.assertFalse((root/'vc_redist.x64.exe').exists())
            self.assertTrue(bundled.exists())
            # Even an installer reporting success cannot replace the real check.
            (b/'system.reg').unlink()
            with patch.object(s.subprocess,'run',side_effect=[subprocess.CalledProcessError(22,['curl']),subprocess.CompletedProcess([],0)]):
                with self.assertRaisesRegex(RuntimeError,'did not finish'):s.ensure_vc(b,'Test',root,game)

if __name__=='__main__':unittest.main()
