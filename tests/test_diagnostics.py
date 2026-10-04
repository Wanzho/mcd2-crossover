import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'helper/diagnostics.py'
spec = importlib.util.spec_from_file_location('diagnostics', SCRIPT)
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / 'private-support'
        self.now = int(time.time())

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        self.home.mkdir(exist_ok=True)
        path = self.home / name
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
        return path

    def test_default_off_does_not_create_home_or_record(self):
        self.assertFalse(diagnostics.status(self.home)['active'])
        self.assertFalse(diagnostics.record(self.home, 'launch', {'outcome': 'started'}))
        self.assertFalse(self.home.exists())

    def test_start_sets_private_timed_flag_and_moves_only_known_logs_to_private_backup(self):
        private = {'session.bin': b'real-token-keep', 'settings.json': b'{}',
                   'unrelated.log': b'leave this alone', 'status.json': b'{}'}
        for name, data in private.items():
            self.write(name, data)
        self.write('http.log', 'old recording')
        result = diagnostics.start(self.home, self.now)
        self.assertTrue(result['active'])
        self.assertEqual(result['seconds_remaining'], 3600)
        flag = json.loads((self.home / diagnostics.FLAG).read_text())
        self.assertEqual(flag, {'version': 1, 'started': self.now, 'expires': self.now + 3600})
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.home / diagnostics.FLAG).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.home / 'app.log').stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.home / 'http.log').exists())
        self.assertTrue(result['previous_recording_kept'])
        backup = next((self.home / 'recordings').iterdir())
        self.assertEqual((backup / 'http.log').read_text(), 'old recording')
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / 'http.log').stat().st_mode & 0o777, 0o600)
        for name, data in private.items():
            self.assertEqual((self.home / name).read_bytes(), data)

    def test_auto_expiry_is_shared_with_bridge_and_stops_flag(self):
        diagnostics.start(self.home, self.now)
        self.assertTrue(diagnostics.enabled(self.home, self.now + 3599))
        self.assertFalse(diagnostics.enabled(self.home, self.now + 3600))
        self.assertFalse((self.home / diagnostics.FLAG).exists())
        self.assertTrue((self.home / diagnostics.STATE).exists())
        self.assertFalse(diagnostics.record(self.home, 'launch', now=self.now + 3600))

    def test_legacy_invalid_or_unbounded_flags_do_not_enable_logging(self):
        examples = [b'1', b'{}', b'{"version":true,"started":1,"expires":2}',
                    b'{"version":1,"started":NaN,"expires":Infinity}',
                    json.dumps({'version': 1, 'started': self.now, 'expires': self.now + 3601}).encode(),
                    json.dumps({'version': 1, 'started': self.now + 1, 'expires': self.now + 3600}).encode()]
        for data in examples:
            with self.subTest(data=data):
                self.write(diagnostics.FLAG, data)
                self.assertFalse(diagnostics.enabled(self.home, self.now))
                self.assertFalse((self.home / diagnostics.FLAG).exists())

    def test_stop_preserves_logs_and_never_touches_account_data(self):
        diagnostics.start(self.home, self.now)
        self.write('session.bin', 'synthetic-secret')
        self.write('http.log', 'diagnostic loaded\n')
        result = diagnostics.stop(self.home, self.now + 5)
        self.assertFalse(result['active'])
        self.assertEqual(result['stopped'], self.now + 5)
        self.assertEqual((self.home / 'session.bin').read_text(), 'synthetic-secret')
        self.assertEqual((self.home / 'http.log').read_text(), 'diagnostic loaded\n')

    def test_previous_recordings_are_preserved_but_never_exported(self):
        diagnostics.start(self.home, self.now)
        self.write('http.log', 'old-secret-recording\n')
        diagnostics.start(self.home, self.now + 10)
        self.write('http.log', 'diagnostic loaded\n')
        target = self.root / 'new-recording.zip'
        diagnostics.export(self.home, target, self.now + 20)
        backup = next((self.home / 'recordings').iterdir())
        self.assertEqual((backup / 'http.log').read_text(), 'old-secret-recording\n')
        with zipfile.ZipFile(target) as archive:
            self.assertFalse(any(name.startswith('recordings/') for name in archive.namelist()))
            self.assertNotIn(b'old-secret-recording', b'\n'.join(archive.read(name) for name in archive.namelist()))

    def test_no_recording_export_is_refused_without_creating_empty_archive(self):
        target = self.root / 'empty.zip'
        with self.assertRaises(diagnostics.NoRecordingError):
            diagnostics.export(self.home, target)
        self.assertFalse(target.exists())

    def test_start_refuses_symlink_backup_folder_without_touching_logs(self):
        diagnostics.start(self.home, self.now)
        outside = self.root / 'outside-recordings'
        outside.mkdir()
        (self.home / 'recordings').symlink_to(outside, target_is_directory=True)
        self.write('http.log', 'diagnostic loaded\n')
        with self.assertRaises(ValueError):
            diagnostics.start(self.home, self.now + 2)
        self.assertTrue((self.home / diagnostics.FLAG).exists())
        self.assertEqual((self.home / 'http.log').read_text(), 'diagnostic loaded\n')
        self.assertEqual(list(outside.iterdir()), [])

    def test_start_rejects_symlink_without_clearing_existing_recording(self):
        diagnostics.start(self.home, self.now)
        self.write('http.log', 'diagnostic loaded\n')
        outside = self.root / 'do-not-touch'
        outside.write_text('account secret')
        (self.home / 'auth.log').symlink_to(outside)
        with self.assertRaises(ValueError):
            diagnostics.start(self.home, self.now + 10)
        self.assertTrue((self.home / diagnostics.FLAG).exists())
        self.assertEqual((self.home / 'http.log').read_text(), 'diagnostic loaded\n')
        self.assertEqual(outside.read_text(), 'account secret')

    def test_home_symlink_is_not_followed_for_recording_or_export(self):
        target = self.root / 'outside'
        target.mkdir()
        self.home.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            diagnostics.start(self.home)
        with self.assertRaises(ValueError):
            diagnostics.export(self.home, self.root / 'logs.zip')
        self.assertEqual(list(target.iterdir()), [])

    def test_app_events_drop_arbitrary_output_paths_accounts_and_secrets(self):
        diagnostics.start(self.home, self.now)
        fields = {'outcome': 'failed', 'store': 'launcher', 'app_version': '0.1.1', 'error_code': 63,
                  'stdout': 'secret-token', 'email': 'account@example.com', 'game': '/Users/Alice/game',
                  'elapsed_seconds': 8, 'refresh_token': 'private-refresh'}
        self.assertTrue(diagnostics.record(self.home, 'launch', fields, self.now))
        self.assertFalse(diagnostics.record(self.home, 'secret-token', fields, self.now))
        row = json.loads((self.home / 'app.log').read_text().splitlines()[-1])
        self.assertEqual(row, {'event': 'launch', 'outcome': 'failed', 'store': 'launcher',
                              'app_version': '0.1.1', 'error_code': 63, 'elapsed_seconds': 8})
        for secret in ('secret-token', 'account@example.com', 'Alice', 'private-refresh'):
            self.assertNotIn(secret, (self.home / 'app.log').read_text())

    def test_auth_log_exports_only_known_status_fields(self):
        secret = 'synthetic-secret-token'
        rows = [json.dumps({'step': 'microsoft-refresh', 'http_status': 400, 'xerr': 2148916233,
                            'oauth_error': 'invalid_grant', 'access_token': secret, 'xuid': 2535400000000000}),
                json.dumps({'step': secret, 'http_status': 400}),
                json.dumps({'step': ['not-a-string'], 'error': secret}),
                'Authorization: Bearer ' + secret]
        safe, report = diagnostics.sanitize('\n'.join(rows).encode(), 'auth.log')
        self.assertNotIn(secret.encode(), safe)
        self.assertNotIn(b'2535400000000000', safe)
        self.assertEqual(json.loads(safe), {'step': 'microsoft-refresh', 'http_status': 400,
                                           'xerr': 2148916233, 'oauth_error': 'invalid_grant'})
        self.assertEqual(report, {'rows': 1, 'omitted_rows': 3})

    def test_adapter_logs_keep_framing_and_status_without_identity_or_request_text(self):
        lines = [
            'diagnostic loaded',
            'option=10065 result=0 CAfile=Z:\\Users\\Alice\\private\\curl-ca-bundle.crt',
            'connection curl=0 http=400 host=vex.minecraftservices.com',
            'connection curl=0 http=400 host=account-secret@example.com?access_token=private',
            'playfab route=Client/LoginWithSteam http=400 createAccount=true serviceSpecific=true '
            'ticketHexLength=1024 titleMatches=true errorCode=1001 error=InvalidSteamTicket decodedBodyBytes=128',
            'playfab route=Client/AccountSecret/SecretToken http=400 error=BearerSyntheticToken decodedBodyBytes=18',
            'playfab framing contentEncodingPresent=0 transferEncodingPresent=0 chunked=0 expectPresent=0 '
            'contentLengthHeaders=1 declaredLengthValid=1 declaredBodyBytes=1890 outgoingWireBodyBytes=1890 '
            'payloadBodyBytes=1890 declaredMatchesPayload=true',
            'playfab header source=wire name=Authorization nameValid=1',
            'playfab header source=wire name=BearerSecretToken nameValid=1',
            'playfab Content-Type source=wire rawValueBytes=17 valueBytesWithoutLeadingOWS=16 leadingOWSBytes=1 unusualBytes=0',
            'playfab response-format contentType=1 encoding=0 bodyKind=json hint=InvalidSteamTicket hint=Content-Type',
            'playfab redacted-server-error: Alice secret-synthetic-token',
            'POST https://vex.minecraftservices.com/login?token=secret-synthetic-token',
            '{"access_token":"secret-synthetic-token"}',
        ]
        safe, report = diagnostics.sanitize('\n'.join(lines).encode(), 'http.log')
        text = safe.decode()
        for secret in ('Alice', 'private', 'account-secret', 'BearerSecretToken',
                       'AccountSecret', 'SecretToken', 'BearerSyntheticToken', 'secret-synthetic-token'):
            self.assertNotIn(secret, text)
        self.assertIn('host=vex.minecraftservices.com', text)
        self.assertIn('host=[other-host]', text)
        self.assertIn('declaredMatchesPayload=true', text)
        self.assertIn('error=InvalidSteamTicket', text)
        self.assertIn('name=authorization', text)
        self.assertIn('name=[other-header]', text)
        self.assertIn('CAfile=[local-certificate-bundle]', text)
        self.assertIn('hint=Content-Type', text)
        self.assertEqual(report['omitted_rows'], 2)

    def test_runtime_log_omits_unknown_text_and_untrusted_hosts(self):
        lines = [
            'XUserAddByIdWithUi matches authenticated user 0x00000001',
            'Service token result 0x80004005',
            'Unsupported XUserIsStoreUser 0x80004001',
            'api.minecraftservices.com 0x00000000',
            'Refused token host: account-secret.example.com 0x80004001',
            'Alice logged in 0x00000000',
            '2535400000000000 0x00000000',
            'access_token=secret-token',
        ]
        safe, report = diagnostics.sanitize('\n'.join(lines).encode(), 'runtime.log')
        text = safe.decode()
        self.assertIn('matches authenticated user 0x00000001', text)
        self.assertIn('Refused token host: [other-host]', text)
        for private in ('Alice', 'account-secret', '2535400000000000', 'secret-token'):
            self.assertNotIn(private, text)
        self.assertEqual(report['omitted_rows'], 3)

    def test_export_stops_and_contains_only_sanitized_whitelist_with_private_modes(self):
        diagnostics.start(self.home, self.now)
        self.write('settings.json', json.dumps({'app_version': '0.1.1', 'store': 'steam',
                                              'game': '/Users/Alice/private-game', 'bottle': 'private-bottle'}))
        self.write('session.bin', 'secret-session')
        self.write('installation.json', 'private-installation')
        self.write('other.log', 'secret-other')
        self.write('http.log', 'connection curl=0 http=200 host=83156.playfabapi.com\nsecret-token\n')
        self.write('auth.log', '{"step":"xbox-user-auth","http_status":200,"Token":"secret-xbox"}\n')
        self.write('runtime.log', 'Service token result 0x00000000\n')
        target = self.root / 'support.zip'
        result = diagnostics.export(self.home, target, self.now + 10)
        self.assertTrue(result['saved'])
        self.assertFalse(diagnostics.enabled(self.home))
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(archive.namelist(), sorted(archive.namelist()))
            self.assertEqual(set(archive.namelist()), {'READ ME.txt', 'manifest.json',
                             'logs/app.log', 'logs/auth.log', 'logs/http.log', 'logs/runtime.log'})
            all_data = b'\n'.join(archive.read(name) for name in archive.namelist())
            for secret in ('Alice', 'private-game', 'private-bottle', 'secret-session',
                           'private-installation', 'secret-other', 'secret-token', 'secret-xbox'):
                self.assertNotIn(secret.encode(), all_data)
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['app_version'], '0.1.1')
            self.assertEqual(manifest['store'], 'steam')
            self.assertEqual(manifest['logs']['http.log']['omitted_rows'], 1)
            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.external_attr >> 16 & 0o777, 0o600)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.home / 'session.bin').read_text(), 'secret-session')

    def test_export_is_repeatable_and_does_not_follow_log_symlink(self):
        diagnostics.start(self.home, self.now)
        private = self.root / 'account.txt'
        private.write_text('secret-keychain-value')
        (self.home / 'auth.log').symlink_to(private)
        first, second = self.root / 'first.zip', self.root / 'second.zip'
        diagnostics.export(self.home, first, self.now + 10)
        diagnostics.export(self.home, second, self.now + 10)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertNotIn('logs/auth.log', archive.namelist())
            self.assertNotIn(b'secret-keychain-value', archive.read('manifest.json'))
        self.assertEqual(private.read_text(), 'secret-keychain-value')

    def test_export_is_capped_and_preserves_recent_diagnostic_rows(self):
        diagnostics.start(self.home, self.now)
        huge = b'unknown-secret-line\n' * 20000 + b'connection curl=0 http=400 host=vex.minecraftservices.com\n'
        self.write('http.log', huge)
        target = self.root / 'capped.zip'
        diagnostics.export(self.home, target, self.now + 1)
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(archive.read('logs/http.log'), b'connection curl=0 http=400 host=vex.minecraftservices.com\n')
            manifest = json.loads(archive.read('manifest.json'))
            self.assertTrue(manifest['logs']['http.log']['input_capped'])
            self.assertLess(len(archive.read('logs/http.log')), diagnostics.MAX_LOG_BYTES)

    def test_export_rejects_targets_inside_private_home_and_symlinks(self):
        diagnostics.start(self.home, self.now)
        outside = self.root / 'other.zip'
        outside.write_text('preserve')
        linked = self.root / 'linked.zip'
        linked.symlink_to(outside)
        for target in (self.home / 'session.zip', linked, self.root / 'session.bin'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                diagnostics.export(self.home, target)
        self.assertTrue(diagnostics.enabled(self.home))
        self.assertEqual(outside.read_text(), 'preserve')

    def test_cli_json_and_error_messages_never_echo_private_paths(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'start', '--home', str(self.home)],
                                capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(result.stdout)['active'])
        self.assertNotIn(str(self.home), result.stdout)
        bad = subprocess.run([sys.executable, str(SCRIPT), 'export', '--home', str(self.home),
                              '--output', str(self.home / 'session.zip')], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stdout)['ok'])
        self.assertNotIn(str(self.home), bad.stdout + bad.stderr)

    def test_malformed_json_rows_are_ignored_and_numeric_ids_do_not_pass_fields(self):
        app, _ = diagnostics.sanitize(b'{"event":"launch","store":[],"outcome":{},"error_code":2535400000000000}\n', 'app.log')
        self.assertEqual(json.loads(app), {'event': 'launch'})
        http, report = diagnostics.sanitize(b'playfab route=secretOperation http=400 decodedBodyBytes=2535400000000000\n', 'http.log')
        self.assertEqual(http, b'playfab route=[other-operation] http=400\n')
        self.assertEqual(report['omitted_rows'], 0)

    def test_truncated_adapter_rows_do_not_interrupt_export(self):
        partial, report = diagnostics.sanitize(b'playfab route=\n', 'http.log')
        self.assertEqual(partial, b'')
        self.assertEqual(report, {'rows': 0, 'omitted_rows': 1})
        rows = [
            b'playfab route=Client/LoginWithSteam http=400 error=InvalidSteamTicket decodedBodyBytes=128',
            b'connection curl=0 http=400 host=vex.minecraftservices.com',
            b'option=10065 result=0 CAfile=Z:\\Users\\Alice\\curl-ca-bundle.crt',
            b'playfab known streamed body bytes=1890 result=0',
            b'playfab header source=wire name=Content-Type nameValid=1',
            b'playfab framing declaredBodyBytes=1890 declaredMatchesPayload=true',
        ]
        for row in rows:
            for length in range(len(row) + 1):
                with self.subTest(row=row, length=length):
                    diagnostics.sanitize(row[:length] + b'\n', 'http.log')
        diagnostics.start(self.home, self.now)
        self.write('http.log', 'diagnostic loaded\nplayfab route=\n')
        output = self.root / 'partial-recording.zip'
        diagnostics.export(self.home, output, self.now + 1)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.read('logs/http.log'), b'diagnostic loaded\n')
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['logs']['http.log']['omitted_rows'], 1)


if __name__ == '__main__':
    unittest.main()
