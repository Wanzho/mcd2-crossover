#!/usr/bin/env python3
"""Inspect a game copy without starting it or changing its files.

The layout identifies a launch route, not a license. Minecraft Launcher copies
are experimental; the game's original services still decide ownership.
"""
import argparse
import json
import sys
from pathlib import Path

STORES = ('auto', 'steam', 'launcher')
LAYOUTS = (
    ('Win64', 'Dungeons-Win64-Shipping.exe', 'steam'),
    ('WinGDK', 'Dungeons-WinGDK-Shipping.exe', 'launcher'),
    ('WinGDK', 'Dungeons-Win64-Shipping.exe', 'launcher'),
)
EXECUTABLES = {name.casefold() for _, name, _ in LAYOUTS} | {'dungeons.exe'}


def inspect_copy(selected, store='auto'):
    if store not in STORES:
        raise ValueError('Choose Steam or Minecraft Launcher for this game copy.')
    path = Path(selected).expanduser().resolve()
    if not path.exists():
        raise ValueError('The selected game folder or executable no longer exists.')
    chosen_executable = path if path.is_file() else None
    if chosen_executable and path.name.casefold() not in EXECUTABLES:
        raise ValueError('Choose the game folder or a Dungeons game executable.')
    start = path.parent if chosen_executable else path
    # Support the root, Dungeons/, Binaries/, platform folder, or executable.
    # Do not scan entire drives or launcher libraries for an unrelated copy.
    roots = [start, *list(start.parents)[:3]]
    for root in roots:
        if not (root / 'MicrosoftGame.config').is_file():
            continue
        copies = []
        for platform, name, detected in LAYOUTS:
            binary = root / 'Dungeons/Binaries' / platform
            executable = binary / name
            if not executable.is_file():
                continue
            if chosen_executable and chosen_executable.name.casefold() != 'dungeons.exe' and executable != chosen_executable:
                continue
            if store == 'steam' and detected != 'steam':
                continue
            route = detected if store == 'auto' else store
            copies.append({'root': str(root), 'binary': str(binary),
                           'executable': str(executable), 'store': route,
                           'label': 'Steam' if route == 'steam' else 'Minecraft Launcher (experimental)',
                           'experimental': route == 'launcher'})
        if len(copies) == 1:
            return copies[0]
        if len(copies) > 1:
            raise ValueError('More than one game executable was found. Choose the executable for the copy you want to use.')
    raise ValueError('Game copy not found. Choose the installed Minecraft Dungeons II folder or its shipping executable. MicrosoftGame.config must be in the game folder.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', type=Path, required=True)
    parser.add_argument('--store', choices=STORES, default='auto')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_copy(args.inspect, args.store)))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
