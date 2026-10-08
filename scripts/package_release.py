#!/usr/bin/env python3
"""Make a drag-to-Applications DMG without game files or Microsoft binaries."""
import argparse, hashlib, json, plistlib, re, shutil, subprocess, sys, tarfile, tempfile, zipfile
from pathlib import Path
from localize import native_resources
from updater import dependency, settings as update_settings, embed as embed_updater

ROOT=Path(__file__).resolve().parents[1]
PYTHON_URL='https://github.com/astral-sh/python-build-standalone/releases/download/20260929/cpython-3.13.15%2B20260929-aarch64-apple-darwin-install_only_stripped.tar.gz'
PYTHON_SHA256='d66c67f16148c7454b1509c32747175f7669c8b8e105b97b92a0000d66af6e6e'

def run(args):subprocess.run(list(map(str,args)),check=True)

def source_origin(version):
    def git(*args):
        return subprocess.check_output(['git','-C',str(ROOT),*args])
    if git('status','--porcelain=v1','--untracked-files=no').strip():
        raise SystemExit('Commit or discard tracked source changes before packaging a release.')
    names=git('ls-files','-z').decode().split('\0')
    return {'schema_version':1,'version':version,'intended_tag':'v'+version,
            'source_commit':git('rev-parse','HEAD').decode().strip(),
            'source_tree':git('rev-parse','HEAD^{tree}').decode().strip(),
            'tracked_source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                     for name in sorted(names) if name}}

def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def finder_layout(stage, python):
    layout=ROOT/'build/layout-tools'
    if not (layout/'ds_store').exists():
        run([python/'bin/python3','-I','-B','-m','pip','install','--only-binary=:all:','--no-compile',
             '--target',layout,'ds-store==1.3.1','mac-alias==2.2.3'])
    sys.path.insert(0,str(layout))
    from ds_store import DSStore
    with DSStore.open(str(stage/'.DS_Store'),'w+') as store:
        store['.']['bwsp']={'ShowStatusBar':False,'ShowToolbar':False,'ShowSidebar':False,
                            'ShowTabView':False,'WindowBounds':'{{240, 160}, {660, 400}}'}
        store['.']['icvp']={'viewOptionsVersion':1,'backgroundType':1,
                            'backgroundColorRed':0.94,'backgroundColorGreen':0.95,'backgroundColorBlue':0.96,
                            'iconSize':96.0,'gridSpacing':100.0,'textSize':14.0,'labelOnBottom':True,
                            'arrangeBy':'none','showItemInfo':False,'showIconPreview':True}
        store['.']['vstl']=('type',b'icnv')
        store['MCD2 Crossover.app']['Iloc']=(180,160)
        store['Applications']['Iloc']=(460,160)
        store['READ ME.txt']['Iloc']=(320,315)

def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.1.4');p.add_argument('--gdk-archive',type=Path,required=True)
    p.add_argument('--runtime-app',type=Path,help='Reuse the verified, pinned Python runtime from an existing local app without modifying it.')
    p.add_argument('--stage-only',action='store_true',help='Verify the signed app and save its stage without creating a DMG.')
    args=p.parse_args()
    installed_version=re.search(r"^VERSION = '([^']+)'",(ROOT/'scripts/install.py').read_text(),re.M)
    if not installed_version or installed_version[1]!=args.version:
        raise SystemExit('App version must match scripts/install.py VERSION before packaging.')
    origin=source_origin(args.version)
    cache=ROOT/'build/release-cache';cache.mkdir(parents=True,exist_ok=True)
    python=cache/'python'
    if args.runtime_app:
        runtime_origin=args.runtime_app/'Contents/Resources/runtime-origin.json'
        expected={'python_url':PYTHON_URL,'python_sha256':PYTHON_SHA256,
                  'packages':{'cryptography':'46.0.7','cffi':'2.1.1','pycparser':'3.0'}}
        if json.loads(runtime_origin.read_text())!=expected:
            raise SystemExit('The supplied app does not contain the pinned runtime.')
        run(['/usr/bin/codesign','--verify','--deep','--strict',args.runtime_app])
        python=args.runtime_app/'Contents/Resources/python'
    else:
        archive=cache/'python-arm64.tar.gz'
        if not archive.exists():run(['/usr/bin/curl','--fail','--location','--silent','--show-error',PYTHON_URL,'-o',archive])
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=PYTHON_SHA256:raise SystemExit('Python runtime checksum mismatch.')
        if not python.exists():
            with tarfile.open(archive) as z:z.extractall(cache,filter='data')
    # An unchanged rebuild can use its verified, pinned libraries offline.
    # Avoid invoking pip (and updating its cache) for an already ready runtime.
    check=subprocess.run([str(python/'bin/python3'),'-I','-B','-c',
        'from importlib.metadata import version; '
        'assert all(version(p)==v for p,v in {"cryptography":"46.0.7","cffi":"2.1.1","pycparser":"3.0"}.items()); '
        'from cryptography.hazmat.primitives.asymmetric import ec; ec.generate_private_key(ec.SECP256R1())'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if check.returncode:
        if args.runtime_app:raise SystemExit('The supplied app runtime failed validation; it was left unchanged.')
        run([python/'bin/python3','-I','-B','-m','pip','install','--only-binary=:all:','--no-compile','cryptography==46.0.7','cffi==2.1.1','pycparser==3.0'])
    # Stage outside synced Documents folders: Finder can add package attributes
    # there while a code signature is being sealed.
    stage=Path(tempfile.mkdtemp(prefix='dungeons-release-'))/'MCD2 Crossover';stage.mkdir()
    app=stage/'MCD2 Crossover.app';contents=app/'Contents';resources=contents/'Resources'
    (contents/'MacOS').mkdir(parents=True);resources.mkdir()
    metadata=native_resources(resources)
    shutil.copytree(ROOT/'localization',resources/'localization')
    (contents/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'installer','CFBundleIdentifier':'org.dungeons-crossover.app',
        'CFBundleDevelopmentRegion':'en','CFBundleLocalizations':[row['id'] for row in metadata['languages']],
        'CFBundleName':'MCD2 Crossover','CFBundleDisplayName':'MCD2 Crossover','CFBundleIconFile':'AppIcon.icns',
        'CFBundleVersion':args.version,'CFBundleShortVersionString':args.version,'CFBundlePackageType':'APPL','LSMinimumSystemVersion':'13.0',
        'NSHighResolutionCapable':True, **update_settings('mcd2')}))
    sparkle=dependency(ROOT/'build/sparkle')
    embed_updater(app,sparkle)
    run(['clang','-arch','arm64','-mmacosx-version-min=13.0','-fobjc-arc','-O2','-framework','Cocoa','-framework','UniformTypeIdentifiers','-F',sparkle,'-framework','Sparkle','-Wl,-rpath,@executable_path/../Frameworks',ROOT/'packaging/installer.m',ROOT/'packaging/CrossoverUpdater.m','-o',contents/'MacOS/installer'])
    shutil.copy2(ROOT/'assets/AppIcon.icns',resources/'AppIcon.icns')
    for folder,names in {'scripts':['install.py','startup.py','game_copy.py','game_process.py'],'helper':['bridge.py','diagnostics.py','localization.py','requirements.txt'],'build':['keychain','signin-ui.exe','xgameruntime.dll','XCurl.dll']}.items():
        dest=resources/folder;dest.mkdir()
        for name in names:shutil.copy2(ROOT/folder/name,dest/name)
    shutil.copytree(python,resources/'python',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # pip entry points in standalone distributions can contain the build prefix.
    # The installed runtime is invoked directly; regenerate these relative to it.
    for name in ('pip','pip3','pip3.13'):
        script=resources/'python/bin'/name
        script.write_text('#!/bin/sh\nexec "$(dirname "$0")/python3" -m pip "$@"\n');script.chmod(0o755)
    # This developer-only generator is unused by the helper. pip gives it an
    # absolute build-interpreter shebang, so leave it out of the runtime bundle.
    (resources/'python/bin/cffi-gen-src').unlink(missing_ok=True)
    licenses=resources/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'LICENSE',licenses/'Dungeons-CrossOver-LICENSE.txt')
    if args.runtime_app:
        gdk_license=(args.runtime_app/'Contents/Resources/licenses/Microsoft-GDK-LICENSE.md').read_bytes()
    else:
        with zipfile.ZipFile(args.gdk_archive) as z:gdk_license=z.read('LICENSE.md')
    if not gdk_license.strip():raise SystemExit('Microsoft GDK license is empty.')
    (licenses/'Microsoft-GDK-LICENSE.md').write_bytes(gdk_license)
    (resources/'runtime-origin.json').write_text(json.dumps({'python_url':PYTHON_URL,'python_sha256':PYTHON_SHA256,
        'packages':{'cryptography':'46.0.7','cffi':'2.1.1','pycparser':'3.0'}},indent=2)+'\n')
    source_manifest=resources/'source-origin.json'
    write_json(source_manifest,origin)
    shutil.copy2(ROOT/'packaging/READ ME.txt',stage/'READ ME.txt')
    (stage/'Applications').symlink_to('/Applications',target_is_directory=True)
    finder_layout(stage,resources/'python')
    forbidden={'session.bin','settings.json','installation.json','status.json','logging.enabled',
               'xgameruntime-native.dll','xgameruntime-adapter-thunks.dll','curl-compat.dll','Dungeons-Win64-Shipping.exe','Dungeons-WinGDK-Shipping.exe'}
    private_prefix=str(Path.home()).encode()
    for path in app.rglob('*'):
        if path.is_file():
            if path.name in forbidden or path.suffix in {'.log','.nupkg'} or private_prefix in path.read_bytes():
                raise SystemExit('Release privacy check failed: '+str(path.relative_to(app)))
    # Finder metadata is not executable content and can invalidate a code seal.
    # Only remove these two attributes from this newly generated package.
    for attribute in ('com.apple.FinderInfo','com.apple.ResourceFork'):
        subprocess.run(['/usr/bin/xattr','-r','-d',attribute,str(app)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if source_origin(args.version)!=origin:
        raise SystemExit('Tracked source changed during packaging. Start again from a clean commit.')
    # Preserve vendor signatures on nested Sparkle helpers. Seal the outer app
    # again after recording the bundled helper hashes.
    run(['/usr/bin/codesign','--force','--sign','-',app])
    origin['bundled_build_sha256']={str(path.relative_to(resources)):hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in sorted((resources/'build').iterdir()) if path.is_file()}
    write_json(source_manifest,origin)
    run(['/usr/bin/codesign','--force','--sign','-',app])
    run(['/usr/bin/codesign','--verify','--deep','--strict',app])
    release=ROOT/'build/releases';release.mkdir(exist_ok=True)
    dest=release/f'MCD2-Crossover-{args.version}-arm64.dmg'
    manifest={'stage':str(stage),'app':str(app),'archive':str(dest),'sha256':None,
              'source_commit':origin['source_commit'],'source_tree':origin['source_tree'],
              'version':args.version,'intended_tag':origin['intended_tag'],'source_origin':origin}
    manifest_path=ROOT/'build/release-build.json'
    write_json(manifest_path,manifest)
    if args.stage_only:
        print('Signed app:',app);print('Stage:',stage);print('Build manifest:',manifest_path)
        return
    dest.unlink(missing_ok=True)
    run(['/usr/bin/hdiutil','create','-volname','MCD2 Crossover','-srcfolder',stage,'-format','UDZO','-ov',dest])
    digest=hashlib.sha256(dest.read_bytes()).hexdigest()
    (release/(dest.name+'.sha256')).write_text(digest+'  '+dest.name+'\n')
    write_json(release/(dest.name+'.source.json'),{'archive':dest.name,'sha256':digest,**origin})
    manifest['sha256']=digest
    write_json(manifest_path,manifest)
    print('Release:',dest);print('SHA-256:',digest)

if __name__=='__main__':main()
