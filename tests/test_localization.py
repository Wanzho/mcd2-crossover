import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ui_localization', ROOT / 'helper/localization.py')
ui = importlib.util.module_from_spec(spec); spec.loader.exec_module(ui)
spec = importlib.util.spec_from_file_location('catalog_build', ROOT / 'scripts/localize.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)


class LocalizationTests(unittest.TestCase):
    def test_complete_native_catalogs_round_trip(self):
        catalogs, metadata = build.catalogs()
        self.assertEqual(len(catalogs), 18)
        with tempfile.TemporaryDirectory() as folder:
            build.native_resources(folder)
            for language, expected in catalogs.items():
                path = Path(folder) / (language + '.lproj') / 'Localizable.strings'
                result = subprocess.run(['/usr/bin/plutil', '-convert', 'json', '-o', '-', str(path)],
                                        check=True, capture_output=True)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_regional_aliases_and_fallback(self):
        _, metadata = build.catalogs()
        expected = {'en-GB':'en', 'fr-CA':'fr', 'zh-CN':'zh-Hans', 'zh-Hant-HK':'zh-Hant',
                    'zh_TW':'zh-Hant', 'pt-BR':'pt-BR', 'pt-PT':'pt-PT', 'pt':'pt-PT',
                    'es-MX':'es-419', 'es-AR':'es-419', 'es-ES':'es-ES', 'uk-UA':'uk',
                    'xx-YY':None}
        for candidate, language in expected.items():
            with self.subTest(candidate=candidate):
                self.assertEqual(ui.match_language(candidate, metadata), language)

    def test_preference_and_system_language(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ui-language'
            self.assertEqual(ui.load_catalog(folder, preferred=['xx', 'de-DE'])['Play'], 'Spielen')
            path.write_text('ja\n')
            self.assertEqual(ui.load_catalog(folder, preferred=['de'])['Play'], 'プレイ')
            path.write_text('../../invalid\n')
            self.assertEqual(ui.load_catalog(folder, preferred=['en'])['Play'], 'Play')

    def test_prompt_protocol_preserves_unicode_and_body_newline(self):
        catalogs, _ = build.catalogs()
        with tempfile.TemporaryDirectory() as folder:
            for language, catalog in catalogs.items():
                (Path(folder) / 'ui-language').write_text(language)
                wire = ui.prompt_payload('https://www.microsoft.com/link', 'FAKE-CODE', folder)
                marker, url, code, rest = wire.split(b'\n', 3)
                self.assertEqual(marker, b'MCD2_PROMPT_V2')
                self.assertEqual(code, b'FAKE-CODE')
                values = []
                for key in ui.PROMPT_KEYS:
                    size, rest = rest.split(b'\n', 1)
                    length = int(size)
                    values.append(rest[:length].decode('utf-8'))
                    self.assertEqual(rest[length:length+1], b'\n')
                    rest = rest[length+1:]
                    self.assertEqual(values[-1], catalog[key])
                self.assertEqual(rest, b'')
                self.assertEqual(values[4].count('\n'), 1)

    def test_refuses_protocol_field_injection(self):
        with self.assertRaises(ValueError):
            ui.prompt_payload('https://www.microsoft.com/link\nclose', 'FAKE', '/nonexistent')

    def test_default_preference_format_is_converted(self):
        result = subprocess.CompletedProcess([], 0, stdout=b'(\n    "zh-Hant-TW",\n    "en-GB"\n)')
        converted = subprocess.CompletedProcess([], 0, stdout=b'["zh-Hant-TW","en-GB"]')
        with patch.object(ui.subprocess, 'run', side_effect=[result, converted]):
            self.assertEqual(ui.system_languages(), ['zh-Hant-TW', 'en-GB'])


if __name__ == '__main__':
    unittest.main()
