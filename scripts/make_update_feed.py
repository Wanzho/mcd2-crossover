#!/usr/bin/env python3
"""Create update.json and update.sig for a native GitHub release updater."""
import argparse,base64,hashlib,json,plistlib,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--notes',type=Path,required=True)
    p.add_argument('--important',action='store_true',help='Only for a verified important fix described in the notes.')
    p.add_argument('--signing-tool',type=Path,required=True,help='Ed25519 sign_update release tool (maintainer only; never bundled).')
    p.add_argument('--keychain-account',default='org.wanzho.crossover.updates')
    a=p.parse_args()
    info=plistlib.loads((a.app/'Contents/Info.plist').read_bytes())
    if a.archive.suffix!='.zip':p.error('Use a ZIP containing the signed .app.')
    subprocess.run(['codesign','--verify','--deep','--strict',str(a.app)],check=True)
    data=a.archive.read_bytes();notes=a.notes.read_text().strip()
    if not notes:p.error('Release notes are required.')
    manifest=dict(schema=1,bundleIdentifier=info['CFBundleIdentifier'],version=info['CFBundleShortVersionString'],
        build=info['CFBundleVersion'],archive=a.archive.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
        minimumSystemVersion=info['LSMinimumSystemVersion'],notes=notes,important=a.important)
    dest=a.archive.parent/'update.json';dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    signature=subprocess.check_output([str(a.signing_tool),'--account',a.keychain_account,'-p',str(dest)],text=True).strip()
    if len(base64.b64decode(signature,validate=True))!=64:raise RuntimeError('Invalid signature returned by signer')
    (dest.parent/'update.sig').write_text(signature+'\n')
    print('Upload the ZIP, update.json and update.sig to the same GitHub release. Do not edit the signed JSON.')
if __name__=='__main__':main()
