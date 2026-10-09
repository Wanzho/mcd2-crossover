import json
import os
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import crossover


class CrossOverSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home_patch = patch.object(Path, 'home', return_value=self.root)
        self.home_patch.start()
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.home_patch.stop)
        self.addCleanup(self.env_patch.stop)

    def app(self, name='External Apps/crossover custom.app', identity='com.codeweavers.CrossOver'):
        app = self.root / name
        (app/'Contents').mkdir(parents=True)
        (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':identity}))
        wine = app/crossover.WINE_RELATIVE
        wine.parent.mkdir(parents=True)
        wine.write_text('#!/bin/sh\nexit 99\n')  # Must never execute during discovery.
        wine.chmod(0o755)
        return app

    def save(self, app):
        config = self.root/'Library/Application Support/DungeonsCrossOver/crossover-app.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({'path':str(app)}))
        return config

    def test_saved_renamed_external_app_is_used(self):
        app=self.app(); self.save(app)
        self.assertEqual(crossover.crossover_app(),app.resolve())
        self.assertEqual(crossover.wine(),str(app.resolve()/crossover.WINE_RELATIVE))

    def test_environment_passes_selection_to_installer(self):
        saved=self.app('Old.app'); selected=self.app('New Location/New.app'); self.save(saved)
        with patch.dict(os.environ, {'MCD2_CROSSOVER_APP':str(selected)}):
            self.assertEqual(crossover.crossover_app(),selected.resolve())

    def test_missing_saved_app_does_not_fall_back(self):
        self.save(self.root/'Removed.app')
        with self.assertRaisesRegex(ValueError,'Choose CrossOver again'):
            crossover.crossover_app()

    def test_unrelated_app_and_broken_wine_rejected(self):
        with self.assertRaisesRegex(ValueError,'not CrossOver'):
            crossover.validate_app(self.app('Other.app','org.other.app'))
        app=self.app(); (app/crossover.WINE_RELATIVE).chmod(0o644)
        with self.assertRaisesRegex(ValueError,'missing its Wine executable'):
            crossover.validate_app(app)

    def test_malformed_preference_requires_reselection(self):
        config=self.save(self.root/'Removed.app'); config.write_text('[]')
        with self.assertRaisesRegex(ValueError,'saved CrossOver selection'):
            crossover.crossover_app()

    def test_steam_and_launcher_commands_use_selection(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helper'))
        import bridge
        app=self.app(); self.save(app)
        game=self.root/'game'; binary=game/'Dungeons/Binaries/WinGDK'; binary.mkdir(parents=True)
        (game/'MicrosoftGame.config').touch(); (binary/'Dungeons-WinGDK-Shipping.exe').touch()
        for store in ('steam','launcher'):
            command,_=bridge.launch_command({'store':store,'game':str(game),'binary':str(binary),'game_exe':r'C:\game\Dungeons-WinGDK-Shipping.exe'},'Grounded 2')
            self.assertEqual(command[0],str(app.resolve()/crossover.WINE_RELATIVE))
            self.assertEqual(command[2],'Grounded 2')

if __name__ == '__main__': unittest.main()
