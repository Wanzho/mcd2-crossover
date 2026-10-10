import contextlib, io, json, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helper'))
import internal_errors as errors
import diagnostics
class AuthError(Exception): pass
class ErrorTests(unittest.TestCase):
 def test_catalog_unique_and_complete(self):
  rows=json.loads(Path(errors.__file__).with_name('error_codes.json').read_text())
  self.assertEqual(len(rows),len(errors.CATALOG))
  self.assertEqual(rows,json.loads((Path(__file__).resolve().parents[1]/'docs/error-codes.json').read_text()))
  for r in rows:
   self.assertEqual(set(r),{'code','check','expected','observed','next_step'})
   self.assertTrue(all(r.values()))
 def test_auth_routes(self):
  for message,code in errors.AUTH_CODES.items():self.assertEqual(errors.auth_code(AuthError(message),'launch'),code)
  self.assertEqual(errors.auth_code(OSError('https://user:password@host/?token=SECRET'),'launch'),3199)
  self.assertEqual(errors.auth_code(AuthError('network request failed'),'sign-out'),4001)
  self.assertEqual(errors.auth_code(AuthError('network request failed'),'stop-game'),4002)
 def test_setup_routes(self):
  self.assertEqual(errors.setup_code(subprocess.CalledProcessError(22,['curl','SECRET']), 'dependencies'),2201)
  self.assertEqual(errors.setup_code(RuntimeError('checksum'),'dependencies'),2202)
  self.assertEqual(errors.setup_code(RuntimeError(),'visual-cpp'),2203)
  self.assertEqual(errors.setup_code(RuntimeError(),'steam'),2204)
  self.assertEqual(errors.setup_code(PermissionError(13,'SECRET'),'files'),2205)
 def test_protocol_contains_no_exception_text(self):
  stream=io.StringIO()
  with contextlib.redirect_stderr(stream):errors.emit(3001,OSError(13,'SECRET-TOKEN'))
  value=stream.getvalue();self.assertNotIn('SECRET',value)
  self.assertEqual(json.loads(value.split(':',1)[1]),{'code':3001,'system_code':13})
 def test_export_error_without_recording(self):
  with tempfile.TemporaryDirectory() as t:
   home=Path(t)/'home';home.mkdir()
   (home/'internal-error.json').write_text(json.dumps({'code':3001,'system_code':13,'token':'SECRET','path':'/Users/private','observed':'SECRET'}))
   self.assertTrue(diagnostics.status(home)['available'])
   output=Path(t)/'report.zip';diagnostics.export(home,output)
   with zipfile.ZipFile(output) as z:
    blob=b''.join(z.read(n) for n in z.namelist())
    self.assertNotIn(b'SECRET',blob);self.assertNotIn(b'/Users/private',blob)
    report=json.loads(z.read('internal-error.json'));self.assertEqual(report['code'],3001)
    self.assertEqual(report['system_code'],13);self.assertEqual(report['observed'],errors.CATALOG[3001]['observed'])
 def test_export_rejects_unknown_code_and_symlink(self):
  with tempfile.TemporaryDirectory() as t:
   home=Path(t)/'home';home.mkdir();p=home/'internal-error.json'
   for content in ({'code':9999},{'code':True},{'code':'3001'}):
    p.write_text(json.dumps(content))
    with self.assertRaises(diagnostics.NoRecordingError):diagnostics.export(home,Path(t)/'report.zip')
   p.unlink();target=Path(t)/'sensitive';target.write_text('{"code":3001}');p.symlink_to(target)
   with self.assertRaises(diagnostics.NoRecordingError):diagnostics.export(home,Path(t)/'report.zip')
if __name__=='__main__':unittest.main()
