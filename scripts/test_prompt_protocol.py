#!/usr/bin/env python3
"""Run the actual sign-in input parser with a host shim and synthetic codes."""
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ui_locale', ROOT / 'helper/localization.py')
ui = importlib.util.module_from_spec(spec); spec.loader.exec_module(ui)


def payload(url, code, labels):
    wire = ('MCD2_PROMPT_V2\n' + url + '\n' + code + '\n').encode('utf-8')
    for label in labels:
        data = label.encode('utf-8')
        wire += str(len(data)).encode() + b'\n' + data + b'\n'
    return wire


def check(binary, wire, url, code, labels, window=False):
    result = subprocess.run([str(binary)] + (['--window'] if window else []),
                            input=wire, capture_output=True)
    assert result.returncode == 1, (result.returncode, result.stderr)
    report = json.loads(result.stdout)
    assert report['url'] == url and report['code'] == code, report
    assert report['labels'] == labels, (report['labels'], labels)
    if window:
        assert report['window_title'] == labels[0]
        assert [row['text'] for row in report['controls']] == [
            labels[1], url, labels[2], code, labels[3], labels[4], labels[5]]
        assert [row['class'] for row in report['controls']] == [
            'STATIC', 'BUTTON', 'BUTTON', 'BUTTON', 'BUTTON', 'STATIC', 'BUTTON']
        assert [row['id'] for row in report['controls']] == [0, 101, 103, 102, 104, 0, 105]
        assert report['clipboard'] == [url, code]
        assert report['updates'] == [
            {'id': 103, 'text': labels[6]}, {'id': 104, 'text': labels[7]}, {'id': 103, 'text': labels[8]}]
    else:
        assert report['window_title'] is None and not report['controls']
        assert not report['clipboard'] and not report['updates']


def main():
    with tempfile.TemporaryDirectory(prefix='mcd2-prompt-test-') as directory:
        directory = Path(directory)
        binary = directory / 'probe'
        # Match the PE build's -fno-builtin: macOS wcslen uses 32-bit wchar_t,
        # so optimizing our 16-bit scan into that host function corrupts the probe.
        subprocess.run(['clang', '-fobjc-arc', '-fshort-wchar', '-fno-builtin', '-O1', '-framework', 'Foundation',
                        str(ROOT / 'tests/prompt_protocol_probe.m'), '-o', str(binary)], check=True)
        count = 0
        for file in sorted((ROOT / 'localization').glob('*.json')):
            if file.stem == 'languages':
                continue
            (directory / 'ui-language').write_text(file.stem)
            wire = ui.prompt_payload('https://www.microsoft.com/link', 'FAKE-CODE', directory)
            catalog = json.loads(file.read_text())
            labels = [catalog[key] for key in ui.PROMPT_KEYS]
            for window in (False, True):
                check(binary, wire, 'https://www.microsoft.com/link', 'FAKE-CODE', labels, window)
            count += 1
        for window in (False, True):
            check(binary, b'https://www.microsoft.com/link\nFAKE-CODE\n',
                  'https://www.microsoft.com/link', 'FAKE-CODE', list(ui.PROMPT_KEYS), window)
            check(binary, b'https://www.microsoft.com/link\r\nFAKE-CODE\r\n',
                  'https://www.microsoft.com/link', 'FAKE-CODE', list(ui.PROMPT_KEYS), window)
        # Supplement real catalogs with surrogate pairs, combining characters,
        # embedded label line breaks, and the actual wire-size boundaries.
        labels = ['中文・日本語・한국어 — café e\u0301 🗝️\nSecond line'] * 9
        check(binary, payload('https://example.invalid/登录', '合成-🗝️', labels),
              'https://example.invalid/登录', '合成-🗝️', labels, True)
        labels = ['x' * 4095] * 9
        check(binary, payload('u' * 1023, 'c' * 127, labels),
              'u' * 1023, 'c' * 127, labels)
        header = b'MCD2_PROMPT_V2\nURL\nCODE\n'
        malformed = [b'', b'URL\n', b'URL\nCODE', b'URL\0\nCODE\n',
                     b'URL\nCODE\0\n', b'\xff\nCODE\n', b'URL\n\xff\n',
                     b'u' * 1024 + b'\nCODE\n', b'URL\n' + b'c' * 128 + b'\n',
                     header, header + b'0\n', header + b'4096\n', header + b'5000\n',
                     header + b'-1\n', header + b'1x\n', header + b'9999999\n',
                     header + b'3\n\xff\xff\xff\n', header + b'2\n\xc0\xaf\n',
                     header + b'3\n\xed\xa0\x80\n', header + b'3\nx\0x\n',
                     header + b'4\nxx', header + b'3\nabcX',
                     payload('URL', 'CODE', ['valid'] * 8)]
        for wire in malformed:
            result = subprocess.run([str(binary)], input=wire, capture_output=True)
            assert result.returncode == 2 and not result.stdout, (wire[:80], result.returncode, result.stderr)
        print(f'Sign-in parser passed: {count} Unicode catalogs in window/fallback paths, legacy protocol, '
              f'UTF-16 controls/clipboard, size boundaries and {len(malformed)} malformed inputs. No Wine or account used.')


if __name__ == '__main__':
    main()
