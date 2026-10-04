"""Exercise the actual native logging gate without Wine or a user's bottle."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class NativeLoggingGateTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('clang'), 'Clang required for native gate check')
    def test_expiry_and_invalid_flags(self):
        source = r'''
#include <stdio.h>
#include <string.h>
typedef unsigned long DWORD;
typedef void *H;
#define IMP
static H self;
static const char *fixture;
static unsigned long long clockSeconds = 2000000000ULL;
static unsigned len(const char*s){return s?(unsigned)strlen(s):0;}
static void append(char*b,unsigned cap,const char*s){if(s)strncat(b,s,cap-strlen(b)-1);}
H CreateFileA(const char*p,DWORD a,DWORD s,void*v,DWORD c,DWORD f,H h){return fixture?(H)1:(H)-1;}
int CloseHandle(H f){return 1;}
DWORD GetEnvironmentVariableA(const char*n,char*b,DWORD c){return 0;}
DWORD GetModuleFileNameA(H m,char*b,DWORD c){return 0;}
DWORD GetFileAttributesA(const char*p){return 0;}
int ReadFile(H f,void*b,DWORD c,DWORD*n,void*v){*n=strlen(fixture);if(*n>c)*n=c;memcpy(b,fixture,*n);return 1;}
void GetSystemTimeAsFileTime(unsigned long long*t){*t=clockSeconds*10000000ULL+116444736000000000ULL;}
#include "paths.inc"
static int check(const char*s,int want){fixture=s;int got=dcLogging();if(got!=want){fprintf(stderr,"gate returned %d expected %d\n",got,want);return 1;}return 0;}
int main(void){
 dcPathsReady=1;strcpy(dcRoot,"Z:\\private");
 int bad=0;
 bad+=check(0,0);
 bad+=check("enabled",0);
 bad+=check("{\"version\":1,\"started\":1999999990,\"expires\":2000003590}",1);
 bad+=check("{\"version\":1,\"started\":1999996400,\"expires\":2000000000}",0);
 bad+=check("{\"version\":1,\"started\":1999996399,\"expires\":1999999999}",0);
 bad+=check("{\"version\":1,\"started\":2000001000,\"expires\":2000004600}",0);
 bad+=check("{\"version\":1,\"started\":1999999990,\"expires\":2100000000}",0);
 bad+=check("{\"version\":2,\"started\":1999999990,\"expires\":2000003590}",0);
 bad+=check("{\"version\":1,\"started\":1999999990,\"expires\":\"2000003590\"}",0);
 return bad?1:0;
}
'''
        with tempfile.TemporaryDirectory(prefix='mcd2-logging-gate-') as folder:
            root = Path(folder)
            (root / 'probe.c').write_text(source)
            subprocess.run(['clang', '-I', str(ROOT / 'src'), str(root / 'probe.c'), '-o', str(root / 'probe')], check=True, capture_output=True)
            subprocess.run([str(root / 'probe')], check=True, capture_output=True)

if __name__ == '__main__':
    unittest.main()
