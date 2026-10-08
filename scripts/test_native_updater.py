#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='native-updater-tests-') as folder:
    binary=Path(folder)/'tests'
    subprocess.run(['xcrun','swiftc','-swift-version','5','-parse-as-library','-O','-target','arm64-apple-macos13.0',
        '-module-cache-path',str(Path(folder)/'modules'),'-framework','Cocoa','-framework','CryptoKit',
        str(root/'packaging/CrossoverUpdater.swift'),str(root/'tests/native_updater_tests.swift'),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
