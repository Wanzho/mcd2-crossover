"""Pinned Sparkle dependency and signed-update packaging configuration."""
from pathlib import Path
import hashlib, shutil, subprocess, urllib.request

VERSION = '2.10.0'
SHA256 = 'c2bf58aa8387266ac179357b1415d6f2635f044da8be41042af32425dae6da0c'
PUBLIC_KEY = 'Coe3cyLyxSxS2uh+24G8eloTBUY9OQzUHgXd0dDhDf0='

def dependency(cache):
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f'Sparkle-{VERSION}.tar.xz'
    if not archive.exists():
        with urllib.request.urlopen(f'https://github.com/sparkle-project/Sparkle/releases/download/{VERSION}/{archive.name}', timeout=60) as response:
            data = response.read(80 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise RuntimeError('Sparkle download checksum does not match the pinned release.')
        archive.write_bytes(data)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError('Cached Sparkle archive is invalid.')
    # Re-extract the verified archive so modified cache binaries are not trusted.
    subprocess.run(['tar', '-xJf', str(archive), '-C', str(cache)], check=True)
    return cache

def settings(product):
    if product not in ('mcd1', 'mcd2'): raise ValueError('Unknown product')
    return dict(SUFeedURL=f'https://raw.githubusercontent.com/Wanzho/{product}-crossover/main/appcast.xml',
        SUPublicEDKey=PUBLIC_KEY, SUEnableAutomaticChecks=True, SUAutomaticallyUpdate=True,
        SUEnableInstallerLauncherService=True, SUVerifyUpdateBeforeExtraction=True,
        SURequireSignedFeed=True, SUScheduledCheckInterval=21600)

def embed(app, vendor):
    app, vendor = Path(app), Path(vendor)
    frameworks = app / 'Contents/Frameworks'; frameworks.mkdir(exist_ok=True)
    subprocess.run(['ditto', '--noextattr', '--noacl', str(vendor / 'Sparkle.framework'), str(frameworks / 'Sparkle.framework')], check=True)
    licenses = app / 'Contents/Resources/licenses'; licenses.mkdir(exist_ok=True)
    shutil.copyfile(vendor / 'LICENSE', licenses / 'Sparkle-LICENSE.txt')
