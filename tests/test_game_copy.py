import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / 'scripts'
spec = importlib.util.spec_from_file_location('game_copy', SCRIPTS/'game_copy.py')
game_copy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game_copy)


class GameCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()/'Game Copy'

    def tearDown(self):
        self.temp.cleanup()

    def copy(self, platform='Win64', name='Dungeons-Win64-Shipping.exe'):
        binary = self.root/'Dungeons/Binaries'/platform
        binary.mkdir(parents=True)
        (self.root/'MicrosoftGame.config').write_text('<Game/>')
        executable = binary/name
        executable.write_bytes(b'synthetic executable')
        return executable

    def test_root_folder_platform_folder_and_executable_find_same_steam_copy(self):
        executable = self.copy()
        expected = game_copy.inspect_copy(self.root)
        for selected in (self.root/'Dungeons', executable.parent, executable):
            self.assertEqual(game_copy.inspect_copy(selected), expected)
        self.assertEqual(expected['store'], 'steam')
        self.assertFalse(expected['experimental'])

    def test_wingdk_is_experimental_and_cannot_be_selected_as_steam(self):
        executable = self.copy('WinGDK', 'Dungeons-WinGDK-Shipping.exe')
        found = game_copy.inspect_copy(executable)
        self.assertEqual(found['store'], 'launcher')
        self.assertTrue(found['experimental'])
        with self.assertRaises(ValueError):
            game_copy.inspect_copy(self.root, 'steam')

    def test_explicit_launcher_route_accepts_win64_without_claiming_ownership(self):
        self.copy()
        found = game_copy.inspect_copy(self.root, 'launcher')
        self.assertEqual(found['store'], 'launcher')
        self.assertTrue(found['experimental'])
        self.assertNotIn('licensed', found)

    def test_multiple_shipping_executables_require_a_specific_selection(self):
        steam = self.copy()
        self.copy('WinGDK', 'Dungeons-WinGDK-Shipping.exe')
        with self.assertRaises(ValueError):
            game_copy.inspect_copy(self.root)
        self.assertEqual(game_copy.inspect_copy(steam)['store'], 'steam')

    def test_bootstrapper_selection_resolves_shipping_executable(self):
        executable = self.copy()
        bootstrapper = self.root/'Dungeons.exe'
        bootstrapper.write_bytes(b'synthetic prerequisite checker')
        self.assertEqual(game_copy.inspect_copy(bootstrapper)['executable'], str(executable))

    def test_unrelated_file_or_incomplete_game_is_refused(self):
        executable = self.copy()
        with self.assertRaises(ValueError):
            game_copy.inspect_copy(self.root/'MicrosoftGame.config')
        (self.root/'MicrosoftGame.config').unlink()
        with self.assertRaises(ValueError):
            game_copy.inspect_copy(executable)

    def test_inspection_cli_does_not_change_the_copy(self):
        executable = self.copy()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/'game_copy.py'),
                                 '--inspect', str(executable)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['root'], str(self.root))
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
