#!/usr/bin/env python3
"""Create a signed appcast; upload the resulting feed and archives together."""
import argparse, subprocess
from pathlib import Path
from updater import dependency

def main():
    p = argparse.ArgumentParser()
    p.add_argument('archives', type=Path)
    p.add_argument('--download-url-prefix', required=True)
    p.add_argument('--critical', action='store_true', help='Use only for a verified important bug fix; write the reason in release notes.')
    p.add_argument('--keychain-account', default='org.wanzho.crossover.updates')
    args = p.parse_args()
    if not args.download_url_prefix.startswith('https://'):
        p.error('Public updates must use HTTPS.')
    if args.critical and not any(args.archives.glob('*.html')):
        p.error('An important bug fix needs HTML release notes next to its update archive.')
    vendor = dependency(Path(__file__).resolve().parents[1] / 'build/sparkle')
    command = [str(vendor/'bin/generate_appcast'), '--account', args.keychain_account,
        '--download-url-prefix', args.download_url_prefix, '--maximum-deltas', '0', '--embed-release-notes']
    if args.critical: command += ['--critical-update-version', '']
    subprocess.run([*command, str(args.archives)], check=True)
    subprocess.run([str(vendor/'bin/sign_update'), '--account', args.keychain_account,
        '--verify', str(args.archives/'appcast.xml')], check=True)

if __name__ == '__main__': main()
