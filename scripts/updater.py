"""Native GitHub updater: macOS frameworks only, no Sparkle runtime."""
from pathlib import Path
import subprocess,tempfile
PUBLIC_KEY = 'Coe3cyLyxSxS2uh+24G8eloTBUY9OQzUHgXd0dDhDf0='
def settings(product):
    if product not in ('mcd1','mcd2'): raise ValueError('Unknown product')
    return dict(CrossoverUpdateRepository=f'Wanzho/{product}-crossover',
                CrossoverUpdatePublicKey=PUBLIC_KEY,CrossoverUpdatePreviews=product=='mcd1')
def embed(app, source):
    app,source=Path(app),Path(source)
    frameworks=app/'Contents/Frameworks';frameworks.mkdir(exist_ok=True)
    library=frameworks/'libCrossoverUpdates.dylib'
    with tempfile.TemporaryDirectory(prefix='crossover-updater-build-') as cache:
        subprocess.run(['xcrun','swiftc','-swift-version','5','-parse-as-library','-emit-library',
            '-module-name','CrossoverUpdates','-O','-target','arm64-apple-macos13.0',
            '-module-cache-path',cache,'-framework','Cocoa','-framework','CryptoKit',
            '-Xlinker','-install_name','-Xlinker','@rpath/libCrossoverUpdates.dylib',str(source),'-o',str(library)],check=True)
    subprocess.run(['codesign','--force','--sign','-',str(library)],check=True)
    return frameworks
