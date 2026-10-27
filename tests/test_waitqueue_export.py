import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helper"))
import diagnostics

MESSAGES = ("wait-queue fix applied", "wait-queue fix already present",
            "wait-queue fix not applicable to this Wine build",
            "wait-queue fix could not be applied")

class WaitQueueExport(unittest.TestCase):
    def test_patch_status_survives_actual_zip_export(self):
        for message in MESSAGES:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as folder:
                home = Path(folder) / "home"
                diagnostics.start(home, 2000000000)
                (home / "http.log").write_text("[t=2000000001000 p=42 th=43] " + message + "\n")
                target = Path(folder) / "support.zip"
                diagnostics.export(home, target, 2000000010)
                with zipfile.ZipFile(target) as archive:
                    self.assertIn(message, archive.read("logs/http.log").decode())
                    report = json.loads(archive.read("manifest.json"))
                    self.assertEqual(report["logs"]["http.log"]["omitted_rows"], 0)

    def test_only_exact_constants_are_accepted(self):
        for message in MESSAGES:
            for suffix in (" token=PRIVATE_SENTINEL", " /private/account", "?secret=PRIVATE_SENTINEL"):
                safe, report = diagnostics.sanitize((message + suffix + "\n").encode(), "http.log")
                self.assertNotIn(b"PRIVATE_SENTINEL", safe)
                self.assertEqual(safe, b"")
                self.assertEqual(report["omitted_rows"], 1)

if __name__ == "__main__":
    unittest.main()
