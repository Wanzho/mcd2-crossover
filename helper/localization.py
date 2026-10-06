"""Shared, offline UI catalogs. No authentication or diagnostic data is read."""
import json
import plistlib
import subprocess
from pathlib import Path

PROMPT_KEYS = (
    'Minecraft Dungeons II — Xbox Sign-In',
    'Sign in using your browser or phone:',
    'Copy link', 'Copy code',
    'Click the link or code to copy it. Leave this window open while signing in.\nIt closes automatically when the sign-in attempt finishes.',
    'Cancel sign-in', 'Link copied', 'Code copied', 'Try copying again',
)


def match_language(candidate, metadata):
    if not isinstance(candidate, str):
        return None
    tag = candidate.replace('_', '-').lower()
    languages = {row['id'].lower(): row['id'] for row in metadata['languages']}
    if tag in languages:
        return languages[tag]
    aliases = {key.lower(): value for key, value in metadata.get('aliases', {}).items()}
    if tag in aliases:
        return aliases[tag]
    if tag.startswith('zh-') or tag == 'zh':
        return 'zh-Hant' if any(part in tag for part in ('hant', '-tw', '-hk', '-mo')) else 'zh-Hans'
    if tag.startswith('pt-') or tag == 'pt':
        return 'pt-BR' if '-br' in tag else 'pt-PT'
    if tag.startswith('es-') or tag == 'es':
        return 'es-ES' if tag == 'es' or tag.startswith('es-es') else 'es-419'
    return languages.get(tag.split('-')[0])


def system_languages():
    try:
        result = subprocess.run(['/usr/bin/defaults', 'read', '-g', 'AppleLanguages'],
                                capture_output=True, timeout=3, check=False)
        try:
            value = plistlib.loads(result.stdout) if result.returncode == 0 else None
        except (ValueError, plistlib.InvalidFileException):
            value = None
        if isinstance(value, list):
            return value
        # defaults renders an OpenStep array; ask plutil to convert the bounded
        # preference output, without reading any account or app preferences.
        if len(result.stdout) < 16384 and result.returncode == 0:
            converted = subprocess.run(['/usr/bin/plutil', '-convert', 'json', '-o', '-', '--', '-'],
                                       input=result.stdout, capture_output=True, timeout=3, check=False)
            value = json.loads(converted.stdout) if converted.returncode == 0 else None
            if isinstance(value, list):
                return value
    except (OSError, ValueError, subprocess.SubprocessError, plistlib.InvalidFileException):
        pass
    return ['en']


def load_catalog(home, root=None, preferred=None):
    folder = Path(root) if root is not None else Path(__file__).resolve().parent / 'localization'
    if not folder.is_dir():
        folder = Path(__file__).resolve().parents[1] / 'localization'
    try:
        metadata = json.loads((folder / 'languages.json').read_text())
        ids = {row['id'] for row in metadata['languages']}
        try:
            choice = (Path(home) / 'ui-language').read_text().strip()
        except OSError:
            choice = 'system'
        locale = choice if choice in ids else next(
            (match_language(tag, metadata) for tag in (preferred if preferred is not None else system_languages())
             if match_language(tag, metadata)), 'en')
        catalog = json.loads((folder / (locale + '.json')).read_text())
        return catalog if isinstance(catalog, dict) else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def prompt_payload(url, code, home):
    # Versioned, length-delimited UTF-8 labels preserve embedded line breaks.
    # This pipe is private to the sign-in UI and is never written to logs.
    if any(char in url + code for char in ('\r', '\n', '\0')):
        raise ValueError('invalid prompt fields')
    catalog = load_catalog(home)
    payload = ('MCD2_PROMPT_V2\n' + url + '\n' + code + '\n').encode()
    for key in PROMPT_KEYS:
        value = catalog.get(key, key)
        data = value.encode('utf-8')
        if not data or len(data) >= 4096 or b'\0' in data:
            raise ValueError('invalid prompt label')
        payload += str(len(data)).encode() + b'\n' + data + b'\n'
    return payload
