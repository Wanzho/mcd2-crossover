typedef unsigned long long U64;
typedef unsigned long DWORD;
typedef void* H;
#define IMP __declspec(dllimport)
#define W(s) ((const unsigned short*)L##s)
IMP H GetModuleHandleA(const char*);
IMP H GetStdHandle(DWORD);
IMP int ReadFile(H,void*,DWORD,DWORD*,void*);
IMP int MultiByteToWideChar(unsigned,DWORD,const char*,int,unsigned short*,int);
IMP H CreateThread(void*,U64,DWORD(*)(void*),void*,DWORD,DWORD*);
IMP int CloseHandle(H);
IMP void Sleep(DWORD);
IMP void ExitProcess(unsigned);
IMP H FindWindowW(const unsigned short*,const unsigned short*);
IMP int PostMessageW(H,unsigned,U64,long long);
static H self;
static struct Prompt {
 char url[1024],code[128];
 unsigned short wideUrl[1024],wideCode[128],labels[9][4096];
 volatile unsigned done,closed;
} prompt;
#include "localized-prompt-ui.inc"
static int equal(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static int line(char*b,unsigned n){
 DWORD got;char c;unsigned i=0;
 while(ReadFile(GetStdHandle((DWORD)-10),&c,1,&got,0)&&got){
  if(c=='\n'){b[i]=0;return 1;}
  if(c!='\r'){if(!c||i+1>=n)return 0;b[i++]=c;}
 }
 return 0;
}
static int wide(const char*s,unsigned short*out,unsigned size){return MultiByteToWideChar(65001,8,s,-1,out,size)>0;}
static int label(unsigned short*out){
 char count[8],bytes[4096];if(!line(count,sizeof(count))||!count[0])return 0;
 unsigned n=0;for(unsigned i=0;count[i];i++){if(count[i]<'0'||count[i]>'9')return 0;n=n*10+count[i]-'0';if(n>=sizeof(bytes))return 0;}
 if(!n)return 0;DWORD got;unsigned offset=0;
 while(offset<n){if(!ReadFile(GetStdHandle((DWORD)-10),bytes+offset,n-offset,&got,0)||!got)return 0;offset+=got;}
 for(unsigned i=0;i<n;i++)if(!bytes[i])return 0;bytes[n]=0;
 char end;if(!ReadFile(GetStdHandle((DWORD)-10),&end,1,&got,0)||got!=1||end!='\n')return 0;
 return wide(bytes,out,4096);
}
static DWORD watch(void*p){
 char b[16];line(b,16);prompt.closed=1;
 while(!prompt.done){H window=FindWindowW(W("DungeonsRemoteLoginCopyPrompt"),prompt.labels[0]);if(window)PostMessageW(window,0x10,0,0);Sleep(100);}return 0;
}
void mainCRTStartup(void){
 static const char*english[]={
 "Minecraft Dungeons II — Xbox Sign-In","Sign in using your browser or phone:","Copy link","Copy code",
 "Click the link or code to copy it. Leave this window open while signing in.\nIt closes automatically when the sign-in attempt finishes.",
 "Cancel sign-in","Link copied","Code copied","Try copying again"};
 self=GetModuleHandleA(0);if(!line(prompt.url,sizeof(prompt.url)))ExitProcess(2);
 int version2=equal(prompt.url,"MCD2_PROMPT_V2");
 if(version2&&!line(prompt.url,sizeof(prompt.url)))ExitProcess(2);
 if(!line(prompt.code,sizeof(prompt.code))||!wide(prompt.url,prompt.wideUrl,1024)||!wide(prompt.code,prompt.wideCode,128))ExitProcess(2);
 for(unsigned i=0;i<9;i++)if(version2?!label(prompt.labels[i]):!wide(english[i],prompt.labels[i],4096))ExitProcess(2);
 H t=CreateThread(0,0,watch,0,0,0);if(t)CloseHandle(t);
 runPrompt(&prompt);prompt.done=1;ExitProcess(prompt.closed?0:1);
}
