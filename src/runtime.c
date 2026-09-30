// CrossOver compatibility adapter. Credentials come from genuine Microsoft/Xbox
// authentication; the original game services still decide ownership and access.
typedef unsigned long DWORD;
typedef unsigned long long U64;
typedef void* H;
#define IMP __declspec(dllimport)
IMP H LoadLibraryA(const char*);
IMP void* GetProcAddress(H,const char*);
IMP DWORD GetModuleFileNameA(H,char*,DWORD);
IMP H CreateFileA(const char*,DWORD,DWORD,void*,DWORD,DWORD,H);
IMP int WriteFile(H,const void*,DWORD,DWORD*,void*);
IMP int CloseHandle(H);
IMP H CreateThread(void*,U64,DWORD(*)(void*),void*,DWORD,DWORD*);
IMP void Sleep(DWORD);
IMP H GetProcessHeap(void);
IMP void* HeapAlloc(H,DWORD,U64);
IMP int HeapFree(H,DWORD,void*);
IMP void AcquireSRWLockExclusive(void*);
IMP void ReleaseSRWLockExclusive(void*);
IMP int MessageBoxA(H,const char*,const char*,unsigned);
IMP H FindWindowA(const char*,const char*);
IMP int PostMessageA(H,unsigned,U64,U64);
static H self,real,thunks;
static U64 lock;
static int installed;
static int (*nativeInit)(U64,U64,U64,void*);
static int (*nativeQuery)(const void*,const void*,void**);
static int (*cancelPrompt)(void*);
static const char* title="Minecraft Dungeons II - Xbox sign-in";

void* memset(void*p,int v,U64 n){volatile unsigned char*c=p;while(n--)*c++=v;return p;}
static unsigned len(const char*s){unsigned n=0;if(s)while(s[n])n++;return n;}
static void append(char*b,unsigned cap,const char*s){unsigned n=len(b);if(s)while(*s&&n+1<cap)b[n++]=*s++;b[n]=0;}

#include "paths.inc"
static void loghr(const char*msg,int hr){
 if(!dcLogging())return;char logpath[2048]={0};if(!dcPath(logpath,sizeof(logpath),"runtime.log"))return;
 char line[256]={0};append(line,256,msg);append(line,256," 0x");unsigned n=len(line);
 for(int i=7;i>=0;i--)line[n++]="0123456789ABCDEF"[((unsigned)hr>>(i*4))&15];
 line[n++]='\r';line[n++]='\n';
 H f=CreateFileA(logpath,4,3,0,4,128,0);if(f!=(H)-1){DWORD w;WriteFile(f,line,n,&w,0);CloseHandle(f);}
}
static H loadSibling(const char*name){char path[1024]={0};DWORD n=GetModuleFileNameA(self,path,1024);if(!n||n>=1024)return 0;while(n&&path[n-1]!='\\'&&path[n-1]!='/')n--;path[n]=0;append(path,1024,name);return LoadLibraryA(path);}
static int ensureReal(void){if(real)return 1;real=loadSibling("xgameruntime-native.dll");if(!real)return 0;nativeInit=GetProcAddress(real,"InitializeApiImplEx2");nativeQuery=GetProcAddress(real,"QueryApiImpl");return nativeInit&&nativeQuery;}

IMP int ReadFile(H,void*,DWORD,DWORD*,void*);
IMP void GetSystemTimeAsFileTime(U64*);
static int (*abegin)(void*,void*,const void*,const char*,void*);
static int (*aschedule)(void*,unsigned);
static void (*acomplete)(void*,int,U64);
static int (*aresult)(void*,const void*,U64,void*,U64*);
static int (*asize)(void*,U64*);
static int asyncReady;
static int initAsync(void){
 if(asyncReady)return 1;
 thunks=loadSibling("xgameruntime-adapter-thunks.dll");if(!thunks)return 0;
 int(*init)(void)=GetProcAddress(thunks,"XGameRuntimeInitialize");if(!init||init()<0)return 0;
 abegin=GetProcAddress(thunks,"XAsyncBegin");aschedule=GetProcAddress(thunks,"XAsyncSchedule");
 acomplete=GetProcAddress(thunks,"XAsyncComplete");aresult=GetProcAddress(thunks,"XAsyncGetResult");asize=GetProcAddress(thunks,"XAsyncGetResultSize");
 asyncReady=abegin&&aschedule&&acomplete&&aresult&&asize;return asyncReady;
}

#include "user.inc"
int InitializeApiImplEx2(U64 a,U64 b,U64 mode,void*options){
 if(!ensureReal())return (int)0x8007007e;
 char localConfig[2048]={0};DWORD pathSize=GetModuleFileNameA(self,localConfig,sizeof(localConfig));
 if(!pathSize||pathSize>=sizeof(localConfig))return (int)0x8007007e;while(pathSize&&localConfig[pathSize-1]!='\\'&&localConfig[pathSize-1]!='/')pathSize--;localConfig[pathSize]=0;append(localConfig,sizeof(localConfig),"..\\..\\..\\MicrosoftGame.config");
 struct{unsigned version,flags;const char*file;} opt={1,0,localConfig};
 int r=nativeInit(a,b,mode,options?options:&opt);loghr("Native runtime initialization",r);
 return r;
}
int InitializeApiImpl(U64 a,U64 b){return InitializeApiImplEx2(a,b,0,0);}
int InitializeApiImplEx(U64 a,U64 b,U64 mode){return InitializeApiImplEx2(a,b,mode,0);}
struct Proxy{void**vt;void*obj;};
extern void pass0(void);
extern void pass1(void);
extern void pass2(void);
extern void pass3(void);
extern void pass4(void);
extern void pass5(void);
extern void pass6(void);
extern void pass7(void);
extern void pass8(void);
extern void pass9(void);
extern void pass10(void);
extern void pass11(void);
extern void pass12(void);
extern void pass13(void);
extern void pass14(void);
extern void pass15(void);
extern void pass16(void);
extern void pass17(void);
extern void pass18(void);
extern void pass19(void);
extern void pass20(void);
extern void pass21(void);
extern void pass22(void);
extern void pass23(void);
extern void pass24(void);
extern void pass25(void);
extern void pass26(void);
extern void pass27(void);
extern void pass28(void);
extern void pass29(void);
extern void pass30(void);
extern void pass31(void);
extern void pass32(void);
extern void pass33(void);
extern void pass34(void);
extern void pass35(void);
extern void pass36(void);
extern void pass37(void);
extern void pass38(void);
extern void pass39(void);
extern void pass40(void);
extern void pass41(void);
extern void pass42(void);
extern void pass43(void);
extern void pass44(void);
extern void pass45(void);
extern void pass46(void);
extern void pass47(void);
extern void pass48(void);
extern void pass49(void);
extern void pass50(void);
extern void pass51(void);
extern void pass52(void);
extern void pass53(void);
extern void pass54(void);
extern void pass55(void);
extern void pass56(void);
extern void pass57(void);
extern void pass58(void);
extern void pass59(void);
extern void pass60(void);
extern void pass61(void);
extern void pass62(void);
extern void pass63(void);
extern void pass64(void);
extern void pass65(void);
extern void pass66(void);
extern void pass67(void);
extern void pass68(void);
extern void pass69(void);
extern void pass70(void);
extern void pass71(void);
extern void pass72(void);
extern void pass73(void);
extern void pass74(void);
extern void pass75(void);
extern void pass76(void);
extern void pass77(void);
extern void pass78(void);
extern void pass79(void);
extern void pass80(void);
extern void pass81(void);
extern void pass82(void);
extern void pass83(void);
extern void pass84(void);
extern void pass85(void);
extern void pass86(void);
extern void pass87(void);
extern void pass88(void);
extern void pass89(void);
extern void pass90(void);
extern void pass91(void);
extern void pass92(void);
extern void pass93(void);
extern void pass94(void);
extern void pass95(void);
extern void pass96(void);
extern void pass97(void);
extern void pass98(void);
extern void pass99(void);
extern void pass100(void);
extern void pass101(void);
extern void pass102(void);
extern void pass103(void);
extern void pass104(void);
extern void pass105(void);
extern void pass106(void);
extern void pass107(void);
extern void pass108(void);
extern void pass109(void);
extern void pass110(void);
extern void pass111(void);
extern void pass112(void);
extern void pass113(void);
extern void pass114(void);
extern void pass115(void);
extern void pass116(void);
extern void pass117(void);
extern void pass118(void);
extern void pass119(void);
extern void pass120(void);
extern void pass121(void);
extern void pass122(void);
extern void pass123(void);
extern void pass124(void);
extern void pass125(void);
extern void pass126(void);
extern void pass127(void);
static void* threadvt[128]={pass0,pass1,pass2,pass3,pass4,pass5,pass6,pass7,pass8,pass9,pass10,pass11,pass12,pass13,pass14,pass15,pass16,pass17,pass18,pass19,pass20,pass21,pass22,pass23,pass24,pass25,pass26,pass27,pass28,pass29,pass30,pass31,pass32,pass33,pass34,pass35,pass36,pass37,pass38,pass39,pass40,pass41,pass42,pass43,pass44,pass45,pass46,pass47,pass48,pass49,pass50,pass51,pass52,pass53,pass54,pass55,pass56,pass57,pass58,pass59,pass60,pass61,pass62,pass63,pass64,pass65,pass66,pass67,pass68,pass69,pass70,pass71,pass72,pass73,pass74,pass75,pass76,pass77,pass78,pass79,pass80,pass81,pass82,pass83,pass84,pass85,pass86,pass87,pass88,pass89,pass90,pass91,pass92,pass93,pass94,pass95,pass96,pass97,pass98,pass99,pass100,pass101,pass102,pass103,pass104,pass105,pass106,pass107,pass108,pass109,pass110,pass111,pass112,pass113,pass114,pass115,pass116,pass117,pass118,pass119,pass120,pass121,pass122,pass123,pass124,pass125,pass126,pass127};
static int asyncStatus(struct Proxy*p,void*a,unsigned char wait){int(*f)(void*,void*,unsigned char)=(*(void***)p->obj)[3];int r=f(p->obj,a,wait);if(r<0&&(unsigned)r!=0x8000000a)loghr("Native async failure after user login",r);return r;}
static void wrapThread(void**p){threadvt[3]=asyncStatus;struct Proxy*w=HeapAlloc(GetProcessHeap(),0,sizeof(*w));if(w){w->vt=threadvt;w->obj=*p;*p=w;}}
static void* systemvt[128]={pass0,pass1,pass2,pass3,pass4,pass5,pass6,pass7,pass8,pass9,pass10,pass11,pass12,pass13,pass14,pass15,pass16,pass17,pass18,pass19,pass20,pass21,pass22,pass23,pass24,pass25,pass26,pass27,pass28,pass29,pass30,pass31,pass32,pass33,pass34,pass35,pass36,pass37,pass38,pass39,pass40,pass41,pass42,pass43,pass44,pass45,pass46,pass47,pass48,pass49,pass50,pass51,pass52,pass53,pass54,pass55,pass56,pass57,pass58,pass59,pass60,pass61,pass62,pass63,pass64,pass65,pass66,pass67,pass68,pass69,pass70,pass71,pass72,pass73,pass74,pass75,pass76,pass77,pass78,pass79,pass80,pass81,pass82,pass83,pass84,pass85,pass86,pass87,pass88,pass89,pass90,pass91,pass92,pass93,pass94,pass95,pass96,pass97,pass98,pass99,pass100,pass101,pass102,pass103,pass104,pass105,pass106,pass107,pass108,pass109,pass110,pass111,pass112,pass113,pass114,pass115,pass116,pass117,pass118,pass119,pass120,pass121,pass122,pass123,pass124,pass125,pass126,pass127};
static unsigned char systemValid(struct Proxy*p,void*h){
 if(h==&handleMarker){unsigned char r=valid(h);loghr("Adapter user handle validation",r);return r;}
 unsigned char(*f)(void*,void*)=(*(void***)p->obj)[7];return f(p->obj,h);
}
static void wrapSystem(void**p){systemvt[7]=systemValid;struct Proxy*w=HeapAlloc(GetProcessHeap(),0,sizeof(*w));if(w){w->vt=systemvt;w->obj=*p;*p=w;}}
static unsigned seenClasses[64],nClasses;
#include "network.inc"
int QueryApiImpl(const void*a,const void*b,void**p){
 if(!p)return (int)0x80004003;
 unsigned cls=a?*(unsigned*)a:0;int seen=0;for(unsigned i=0;i<nClasses;i++)if(seenClasses[i]==cls)seen=1;if(!seen&&nClasses<64){seenClasses[nClasses++]=cls;loghr("Runtime class requested",cls);loghr("Runtime interface requested",b?*(unsigned*)b:0);}
 if(isUserGuid(a)||isTagGuid(a))return userQI(&userObj,b,p);
 if(!ensureReal())return (int)0x8007007e;int r=nativeQuery(a,b,p);r=tryNetwork(a,b,p,r);if(r>=0&&p&&*p)wrapFeature(a,b,p);if(r<0)loghr("Native interface request failed",r);if(r>=0&&p&&*p&&cls==0x073b7dcb)wrapThread(p);if(r>=0&&p&&*p&&cls==0xe349bd1a)wrapSystem(p);return r;
}
void UninitializeApiImpl(void){if(ensureReal()){void(*f)(void)=GetProcAddress(real,"UninitializeApiImpl");f();}}
int DllCanUnloadNow(void){if(!ensureReal())return 1;int(*f)(void)=GetProcAddress(real,"DllCanUnloadNow");return f();}
void XErrorReport(int code,const unsigned short*message){if(ensureReal()){void(*f)(int,const unsigned short*)=GetProcAddress(real,"XErrorReport");f(code,message);}}
int DllMain(H module,DWORD reason,void*reserved){if(reason==1)self=module;return 1;}
