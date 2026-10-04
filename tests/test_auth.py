import datetime, importlib.util, json, struct, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bridge',Path(__file__).parents[1]/'helper/bridge.py')
bridge = importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)

def services(expiries=(86400,7200,43200), xid='123'):
    now = time.time()
    return {label:{'Token':'synthetic-test-token-'+label,
                   'NotAfter':datetime.datetime.fromtimestamp(now+seconds,datetime.timezone.utc).isoformat(),
                   'DisplayClaims':{'xui':[{'xid':xid,'uhs':'synthetic','agg':'Adult','prv':'','gtg':'test'}]}}
            for label,seconds in zip(('xbox','minecraft','playfab'),expiries)}

class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.home = Path(self.temp.name)
        self.home_patch = patch.object(bridge,'HOME',self.home);self.home_patch.start()
        bridge.private_home()
    def tearDown(self):self.home_patch.stop();self.temp.cleanup()
    def test_uses_earliest_server_notafter_without_twenty_minute_cap(self):
        docs = services();packet = bridge.make_packet(docs)
        expiry = (struct.unpack_from('<Q',packet,8)[0]-116444736000000000)/10000000
        expected = datetime.datetime.fromisoformat(docs['minecraft']['NotAfter']).timestamp()
        self.assertAlmostEqual(expiry,expected,places=5)
        self.assertGreater(expiry-time.time(),7100)
    def test_expired_token_is_refused(self):
        with self.assertRaises(bridge.AuthError):bridge.make_packet(services((86400,-1,43200)))
    def test_other_account_is_refused(self):
        with self.assertRaises(bridge.AuthError):bridge.make_packet(services(),expected_xuid=124)
    def test_mixed_identity_is_refused(self):
        docs = services();docs['minecraft']['DisplayClaims']['xui'][0]['xid']='456'
        with self.assertRaises(bridge.AuthError):bridge.make_packet(docs)
    def test_renewal_rotates_only_keychain_secret_and_issues_fresh_session(self):
        calls=[]
        def kc(op,secret=None):
            calls.append((op,secret));return 'synthetic-refresh-original' if op=='get' else None
        reply=(200,{'access_token':'synthetic-access','refresh_token':'synthetic-refresh-rotated'})
        with patch.object(bridge,'keychain',side_effect=kc),patch.object(bridge,'post',return_value=reply),patch.object(bridge,'services_for',return_value=services()):
            bridge.renew()
        self.assertIn(('set','synthetic-refresh-rotated'),calls)
        self.assertGreater(bridge.session_meta()['expires']-time.time(),7100)
        for file in self.home.iterdir():
            self.assertNotIn(b'synthetic-refresh',file.read_bytes())
            self.assertNotIn(b'synthetic-access',file.read_bytes())
        self.assertEqual((self.home/'session.bin').stat().st_mode&0o777,0o600)
        self.assertFalse((self.home/'auth.log').exists())
    def test_rejected_renewal_never_extends_existing_expiry(self):
        packet=bridge.make_packet(services());bridge.atomic(self.home/'session.bin',packet)
        with patch.object(bridge,'keychain',return_value='synthetic-refresh'),patch.object(bridge,'post',return_value=(400,{'error':'invalid_grant'})):
            with self.assertRaises(bridge.AuthError):bridge.renew()
        self.assertEqual((self.home/'session.bin').read_bytes(),packet)
    def test_sign_out_deletes_keychain_and_session(self):
        bridge.atomic(self.home/'session.bin',bridge.make_packet(services()))
        bridge.atomic(self.home/'refresh-0000000000000001.req',b'synthetic')
        with patch.object(bridge,'keychain') as kc:bridge.sign_out();kc.assert_called_once_with('delete')
        self.assertFalse((self.home/'session.bin').exists())
        self.assertTrue((self.home/'signed-out').exists())
        self.assertEqual(list(self.home.glob('refresh-*.req')),[])
    def test_logging_is_off_then_whitelisted_only(self):
        secret='secret-that-must-never-be-logged'
        bridge.diagnostic('test',200,{'Token':secret,'refresh_token':secret})
        self.assertFalse((self.home/'auth.log').exists())
        bridge.diagnostics.start(self.home)
        bridge.diagnostic('test',400,{'Token':secret,'refresh_token':secret,'error':'invalid_grant','XErr':123})
        row=json.loads((self.home/'auth.log').read_text())
        self.assertEqual(row,{'step':'test','http_status':400,'oauth_error':'invalid_grant','xerr':123})
        self.assertNotIn(secret,(self.home/'auth.log').read_text())
    def test_cancelled_launch_keeps_session_and_does_not_start_steam(self):
        packet=bridge.make_packet(services());bridge.atomic(self.home/'session.bin',packet)
        with patch.object(bridge,'cancelled',True),patch.object(bridge.subprocess,'Popen') as start:
            with self.assertRaises(bridge.AuthError):bridge.launch('Steam')
            start.assert_not_called()
        self.assertEqual((self.home/'session.bin').read_bytes(),packet)
    def test_legacy_settings_keep_steam_launch_route(self):
        command,cwd=bridge.launch_command({'steam_exe':r'C:\Steam\steam.exe'},'Original')
        self.assertIsNone(cwd)
        self.assertEqual(command[-3:],[r'C:\Steam\steam.exe','-applaunch','1912410'])
        self.assertIn('Original',command)
    def test_launcher_game_launch_uses_selected_executable_and_game_directory(self):
        game=self.home/'game';binary=game/'Dungeons/Binaries/WinGDK';binary.mkdir(parents=True)
        (game/'MicrosoftGame.config').write_text('<Game/>')
        (binary/'Dungeons-WinGDK-Shipping.exe').write_bytes(b'synthetic executable')
        settings={'store':'launcher','game':str(game),'binary':str(binary),
                  'game_exe':r'C:\Game\Dungeons\Binaries\WinGDK\Dungeons-WinGDK-Shipping.exe'}
        command,cwd=bridge.launch_command(settings,'Launcher Test')
        self.assertEqual(cwd,str(game))
        expected='Z:'+str((binary/'Dungeons-WinGDK-Shipping.exe').resolve()).replace('/','\\')
        self.assertIn(expected,command)
        self.assertNotIn(settings['game_exe'],command)
        self.assertNotIn('-applaunch',command)
        self.assertFalse(any('steam.exe' in value for value in command))
        self.assertEqual(command[-4:],['Dungeons','-windowed','-ResX=1600','-ResY=900'])
    def test_launcher_refuses_unknown_layout_or_executable(self):
        game=self.home/'game';binary=game/'Dungeons/Binaries/WinGDK';binary.mkdir(parents=True)
        (game/'MicrosoftGame.config').write_text('<Game/>')
        (binary/'Dungeons-WinGDK-Shipping.exe').write_bytes(b'synthetic executable')
        settings={'store':'launcher','game':str(game),'binary':str(binary),'game_exe':r'C:\Game\not-a-game.exe'}
        with self.assertRaises(bridge.AuthError):bridge.launch_command(settings,'Test')
        settings.update(binary=str(self.home),game_exe=r'C:\Game\Dungeons-WinGDK-Shipping.exe')
        with self.assertRaises(bridge.AuthError):bridge.launch_command(settings,'Test')
    def test_launcher_launch_uses_ready_helper_without_starting_steam(self):
        game=self.home/'game';binary=game/'Dungeons/Binaries/WinGDK';binary.mkdir(parents=True)
        (game/'MicrosoftGame.config').write_text('<Game/>')
        (binary/'Dungeons-WinGDK-Shipping.exe').write_bytes(b'synthetic executable')
        settings={'store':'launcher','game':str(game),'binary':str(binary),
                  'game_exe':r'C:\Game\Dungeons\Binaries\WinGDK\Dungeons-WinGDK-Shipping.exe'}
        bridge.atomic(self.home/'settings.json',json.dumps(settings).encode())
        bridge.atomic(self.home/'status.json',b'{"state":"ready"}')
        with patch.object(bridge.fcntl,'flock',side_effect=BlockingIOError),patch.object(bridge.subprocess,'Popen') as spawn,patch.object(bridge.subprocess,'run') as external,patch.object(bridge,'keychain',side_effect=AssertionError('Ready helper must not read a credential')):
            bridge.launch('Launcher Test')
        external.assert_not_called()
        spawn.assert_called_once()
        command=spawn.call_args.args[0]
        expected='Z:'+str((binary/'Dungeons-WinGDK-Shipping.exe').resolve()).replace('/','\\')
        self.assertIn(expected,command)
        self.assertNotIn(settings['game_exe'],command)
        self.assertNotIn('-applaunch',command)
        self.assertEqual(spawn.call_args.kwargs['cwd'],str(game))
    def test_launcher_launch_derives_c_path_in_selected_bottle(self):
        game=self.home/'Library/Application Support/CrossOver/Bottles/Launcher Test/drive_c/Game Folder'
        binary=game/'Dungeons/Binaries/Win64';binary.mkdir(parents=True)
        (game/'MicrosoftGame.config').write_text('<Game/>')
        (binary/'Dungeons-Win64-Shipping.exe').write_bytes(b'synthetic executable')
        settings={'store':'launcher','game':str(game),'binary':str(binary),
                  'game_exe':r'Z:\Unrelated\Dungeons-Win64-Shipping.exe'}
        with patch.object(Path,'home',return_value=self.home):
            command,cwd=bridge.launch_command(settings,'Launcher Test')
        self.assertIn(r'C:\Game Folder\Dungeons\Binaries\Win64\Dungeons-Win64-Shipping.exe',command)
        self.assertNotIn(settings['game_exe'],command)
        self.assertEqual(cwd,str(game))

if __name__=='__main__':unittest.main()
