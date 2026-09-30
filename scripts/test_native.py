#!/usr/bin/env python3
"""Synthetic local ABI/IPC validation; no server request or real account used."""
import argparse, datetime, hashlib, importlib.util, json, shutil, struct, subprocess, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bridge',ROOT/'helper/bridge.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--game',type=Path,required=True);parser.add_argument('--bottle',default='Steam')
    args=parser.parse_args();source=args.game/'Dungeons/Binaries/Win64'
    link=next((Path.home()/'.rustup/toolchains').glob('stable-*/lib/rustlib/*/bin/gcc-ld/lld-link'))
    with tempfile.TemporaryDirectory(prefix='dungeons-adapter-') as temp:
        root=Path(temp);binary=root/'game/Dungeons/Binaries/Win64';binary.mkdir(parents=True)
        home=root/'private';home.mkdir(mode=0o700)
        for name in ('xgameruntime-native.dll','xgameruntime-adapter-thunks.dll'):shutil.copy2(source/name,binary/name)
        shutil.copy2(ROOT/'build/xgameruntime.dll',binary/'xgameruntime.dll')
        shutil.copy2(args.game/'MicrosoftGame.config',root/'game/MicrosoftGame.config')
        (binary/'dungeons-crossover.ini').write_text('Z:'+str(home).replace('/','\\'))
        expected=time.time()+86400
        docs={label:{'Token':'synthetic-'+label,'NotAfter':datetime.datetime.fromtimestamp(expected,datetime.timezone.utc).isoformat(),
                     'DisplayClaims':{'xui':[{'xid':'123','uhs':'fixture','agg':'Adult','prv':'','gtg':'test'}]}}
              for label in ('xbox','minecraft','playfab')}
        b.atomic(home/'session.bin',b.make_packet(docs))
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-fno-builtin','-c',str(ROOT/'tests/native_probe.c'),'-o',str(root/'probe.obj')],check=True)
        subprocess.run([str(link),'/lib','/machine:x64','/def:'+str(ROOT/'tests/probe-kernel32.def'),'/out:'+str(root/'kernel.lib')],check=True)
        subprocess.run([str(link),'/subsystem:console','/entry:mainCRTStartup','/nodefaultlib','/out:'+str(binary/'probe.exe'),str(root/'probe.obj'),str(root/'kernel.lib')],check=True)
        stop=threading.Event();served=[]
        def mock_helper():
            while not stop.is_set():
                for request in home.glob('refresh-*.req'):
                    data=request.read_bytes()
                    if len(data)!=16:continue
                    magic,generation=struct.unpack('<QQ',data)
                    if magic!=b.REQUEST_MAGIC:continue
                    packet=b.make_packet(docs)
                    b.atomic(home/'session.bin',packet)
                    new=struct.unpack_from('<Q',packet,b.PACKET.size-8)[0]
                    assert new!=generation
                    b.atomic(request.with_suffix('.res'),struct.pack('<QQ',0,new));request.unlink(missing_ok=True);served.append(True)
                stop.wait(.02)
        worker=threading.Thread(target=mock_helper);worker.start()
        try:
            run=subprocess.run(['/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine','--bottle',args.bottle,'--debugmsg','-all',str(binary/'probe.exe')],capture_output=True,text=True,errors='replace',timeout=150,cwd=binary)
            print(run.stdout);print('Probe exit:',run.returncode)
            if run.returncode or len(served)!=3:raise SystemExit('Native ABI/ForceRefresh test failed.')
            if list(home.glob('*.log')):raise SystemExit('Default-off logging test failed.')
            print('24-hour fixture accepted; ForceRefresh IPC/native async passed; logging remained off.')
        finally:stop.set();worker.join()

if __name__=='__main__':main()
