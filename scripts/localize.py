#!/usr/bin/env python3
"""Validate the shared catalogs and create Apple's native string resources."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def catalogs(root=ROOT):
    folder = Path(root) / 'localization'
    metadata = json.loads((folder / 'languages.json').read_text())
    english = json.loads((folder / 'en.json').read_text())
    if not english or any(key != value for key, value in english.items()):
        raise ValueError('Invalid English localization catalog')
    result = {}
    for language in metadata['languages']:
        locale = language['id']
        data = json.loads((folder / (locale + '.json')).read_text())
        if data.keys() != english.keys():
            raise ValueError('Incomplete localization: ' + locale)
        for key, value in data.items():
            if not isinstance(value, str) or not value.strip() or '\r' in value or '\0' in value:
                raise ValueError('Invalid localization text: ' + locale)
            if key.endswith(' ') != value.endswith(' ') or key.count('\n') != value.count('\n'):
                raise ValueError('Localization lost text spacing: ' + locale)
        result[locale] = data
    if len(result) != len(metadata['languages']) or any(value not in result for value in metadata['aliases'].values()):
        raise ValueError('Invalid localization language mapping')
    return result, metadata


def native_resources(destination, root=ROOT):
    data, metadata = catalogs(root)
    destination = Path(destination)
    for locale, strings in data.items():
        folder = destination / (locale + '.lproj')
        folder.mkdir(parents=True, exist_ok=True)
        text = ''.join(json.dumps(key, ensure_ascii=False) + ' = ' +
                       json.dumps(value, ensure_ascii=False) + ';\n'
                       for key, value in strings.items())
        (folder / 'Localizable.strings').write_text(text)
    return metadata


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        native_resources(args.output)
    else:
        data, _ = catalogs()
        print(f'{len(data)} complete catalogs, {len(data["en"])} strings each')
