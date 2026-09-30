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
        bridge.atomic(self.home/'logging.enabled',b'1')
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

if __name__=='__main__':unittest.main()
