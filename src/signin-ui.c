typedef unsigned long DWORD;typedef unsigned long long U64;typedef void* H;
#define IMP __declspec(dllimport)
IMP H GetModuleHandleA(const char*);IMP H GetStdHandle(DWORD);IMP int ReadFile(H,void*,DWORD,DWORD*,void*);IMP void ExitProcess(DWORD);
IMP H CreateThread(void*,U64,DWORD(*)(void*),void*,DWORD,DWORD*);IMP int CloseHandle(H);IMP void Sleep(DWORD);
IMP H FindWindowA(const char*,const char*);IMP int PostMessageA(H,unsigned,U64,U64);IMP int MessageBoxA(H,const char*,const char*,unsigned);
static H self;static const char* title="Minecraft Dungeons II - alternative Xbox sign-in";
struct Prompt {void*op;volatile int closed,done;char text[2048];char url[1024];char code[128];};static struct Prompt prompt;
void* memset(void*p,int v,U64 n){volatile unsigned char*c=p;while(n--)*c++=v;return p;}
static unsigned len(const char*s){unsigned n=0;if(s)while(s[n])n++;return n;}
#include "copy-prompt-ui.inc"
static int line(char*b,unsigned n){DWORD got;char c;unsigned i=0;while(ReadFile(GetStdHandle((DWORD)-10),&c,1,&got,0)&&got){if(c=='\n'){b[i]=0;return 1;}if(c!='\r'&&i+1<n)b[i++]=c;}return 0;}
static DWORD watch(void*p){char b[16];line(b,16);prompt.closed=1;while(!prompt.done){H window=FindWindowA("DungeonsRemoteLoginCopyPrompt",title);if(window)PostMessageA(window,0x10,0,0);Sleep(100);}return 0;}
void mainCRTStartup(void){self=GetModuleHandleA(0);if(!line(prompt.url,sizeof(prompt.url))||!line(prompt.code,sizeof(prompt.code)))ExitProcess(2);H t=CreateThread(0,0,watch,0,0,0);if(t)CloseHandle(t);runPrompt(&prompt);prompt.done=1;ExitProcess(prompt.closed?0:1);}
