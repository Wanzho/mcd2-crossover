"""Resolve the user's CrossOver installation without starting it."""
import json
import os
import plistlib
from pathlib import Path

WINE_RELATIVE = 'Contents/SharedSupport/CrossOver/bin/wine'


def validate_app(path):
    app = Path(path).expanduser().resolve()
    try:
        with (app / 'Contents/Info.plist').open('rb') as stream:
            info = plistlib.load(stream)
            identifier = info.get('CFBundleIdentifier') if isinstance(info, dict) else None
        if identifier != 'com.codeweavers.CrossOver':
            raise ValueError('The selected app is not CrossOver.')
        wine = app / WINE_RELATIVE
        if not wine.is_file() or not os.access(wine, os.X_OK):
            raise ValueError('The selected CrossOver app is missing its Wine executable.')
    except (OSError, plistlib.InvalidFileException) as error:
        raise ValueError(f'Cannot read the selected CrossOver app: {app}. Choose CrossOver again.') from error
    return app


def crossover_app():
    preference = Path.home() / 'Library/Application Support/DungeonsCrossOver/crossover-app.json'
    selected = os.environ.get('MCD2_CROSSOVER_APP')
    if not selected and preference.exists():
        try:
            selected = json.loads(preference.read_text())['path']
            if not isinstance(selected, str) or not selected:
                raise ValueError('empty path')
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError('Cannot read the saved CrossOver selection. Choose CrossOver again.') from error
    if selected:
        # Never silently launch a different installation if a saved one moved.
        return validate_app(selected)
    for directory in (Path('/Applications'), Path.home() / 'Applications'):
        candidates = [directory / 'CrossOver.app', *sorted(directory.glob('*.app'))]
        for candidate in candidates:
            try:
                return validate_app(candidate)
            except ValueError:
                continue
    raise ValueError('CrossOver was not found. Click Choose CrossOver and select your CrossOver app.')


def wine():
    return str(crossover_app() / WINE_RELATIVE)
