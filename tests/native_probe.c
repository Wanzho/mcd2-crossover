typedef unsigned long D;typedef unsigned long long U;typedef void*H;
#define I __declspec(dllimport)
I H LoadLibraryA(const char*);I void*GetProcAddress(H,const char*);I H GetStdHandle(D);I int WriteFile(H,const void*,D,D*,void*);I void ExitProcess(D);I void Sleep(D);
void*memset(void*p,int v,U n){volatile unsigned char*c=p;while(n--)*c++=v;return p;}
static void out(const char*s){D n=0,w;while(s[n])n++;WriteFile(GetStdHandle(-11),s,n,&w,0);}
static void num(const char*s,int v){char b[11]="0x00000000";out(s);for(int i=9;i>=2;i--){b[i]="0123456789ABCDEF"[v&15];v=(unsigned)v>>4;}out(b);out("\r\n");}
struct A{void*q,*c,*cb;char internal[32];};struct P{void*a;U size;void*buffer;void*context;};
static int(*schedule)(void*,unsigned);static void(*complete)(void*,int,U);static char ident;
static int provider(unsigned op,struct P*d){if(op==0)return schedule(d->a,0);if(op==1)complete(d->a,0,8);if(op==2)*(U*)d->buffer=42;return 0;}
void mainCRTStartup(void){H m=LoadLibraryA("xgameruntime-adapter-thunks.dll");if(!m)ExitProcess(9);
 int(*init)(void)=GetProcAddress(m,"XGameRuntimeInitialize");int(*begin)(void*,void*,void*,const char*,void*)=GetProcAddress(m,"XAsyncBegin");schedule=GetProcAddress(m,"XAsyncSchedule");complete=GetProcAddress(m,"XAsyncComplete");int(*status)(void*,int)=GetProcAddress(m,"XAsyncGetStatus");int(*result)(void*,void*,U,void*,U*)=GetProcAddress(m,"XAsyncGetResult");
 int r=init();num("Runtime init ",r);if(r<0)ExitProcess(10);
 unsigned tid=0;int(*title)(unsigned*)=GetProcAddress(m,"XGameGetXboxTitleId");num("Title lookup ",title(&tid));num("Title ID ",tid);
 int(*sys)(U,char*,U*);static char systemBuf[1024];U used=0;
 sys=GetProcAddress(m,"XSystemGetXboxLiveSandboxId");if(sys)num("Sandbox lookup ",sys(sizeof(systemBuf),systemBuf,&used));
 sys=GetProcAddress(m,"XSystemGetAppSpecificDeviceId");if(sys)num("App device lookup ",sys(sizeof(systemBuf),systemBuf,&used));
 struct A a={0};r=begin(&a,0,&ident,"Bridge queue smoke test",provider);num("Native provider begin ",r);if(r<0)ExitProcess(11);r=status(&a,1);num("Native provider completion ",r);U value=0;r=result(&a,&ident,8,&value,0);num("Native provider result ",r);if(r<0||value!=42)ExitProcess(12);
 int(*add)(unsigned,void*)=GetProcAddress(m,"XUserAddAsync");int(*userResult)(void*,void**)=GetProcAddress(m,"XUserAddResult");int(*id)(void*,U*)=GetProcAddress(m,"XUserGetId");int(*priv)(void*,unsigned,unsigned,unsigned char*,unsigned*)=GetProcAddress(m,"XUserCheckPrivilege");
 struct A b={0};r=add(1,&b);num("User add ",r);if(r<0)ExitProcess(r==(int)0x89245100?0:13);
 r=status(&b,1);num("User completion ",r);void*u=0;if(r>=0)r=userResult(&b,&u);num("User result ",r);if(r<0||!u)ExitProcess(14);U uid=0;r=id(u,&uid);num("Fixture identity available ",r);if(r<0||!uid)ExitProcess(15);
 int(*byId)(U,void*)=GetProcAddress(m,"XUserAddByIdWithUiAsync");int(*byResult)(void*,void**)=GetProcAddress(m,"XUserAddByIdWithUiResult");if(!byId||!byResult)ExitProcess(30);
 struct A match={0},other={0};if(byId(uid,0)!=(int)0x80070057)ExitProcess(31);
 if(byId(uid^1,&other)!=(int)0x89245100)ExitProcess(32);out("Different ID and missing async block correctly refused\r\n");
 r=byId(uid,&match);num("Add-by-ID same authenticated account ",r);if(r<0)ExitProcess(33);r=status(&match,1);num("Add-by-ID completion ",r);if(r<0)ExitProcess(34);void*same=0;r=byResult(&match,&same);num("Add-by-ID result ",r);if(r<0||same!=u)ExitProcess(35);out("Same fixture user handle returned through Microsoft thunks\r\n");
 unsigned char(*handleValid)(void*)=GetProcAddress(m,"XSystemIsHandleValid");if(handleValid){num("Adapter user handle validity ",handleValid(u));if(!handleValid(u)||handleValid(0)||handleValid((void*)1234))ExitProcess(26);out("Invalid handles correctly refused\r\n");}unsigned char has=1;unsigned reason=0;r=priv(u,0,65535,&has,&reason);if(r>=0||has)ExitProcess(16);out("Unknown privilege correctly refused\r\n");
 int(*tok)(void*,unsigned,const char*,const char*,U,const void*,U,const void*,void*)=GetProcAddress(m,"XUserGetTokenAndSignatureAsync");
 int(*tsize)(void*,U*)=GetProcAddress(m,"XUserGetTokenAndSignatureResultSize");int(*tresult)(void*,U,void*,void**,U*)=GetProcAddress(m,"XUserGetTokenAndSignatureResult");
 struct A c={0};r=tok(u,0,"GET","https://untrusted.invalid/",0,0,0,0,&c);if(r>=0)ExitProcess(17);out("Unrecognized service correctly refused\r\n");
 r=tok(u,0,"GET","https://api.minecraftservices.com/",0,0,0,0,&c);num("Token start ",r);if(r<0)ExitProcess(18);r=status(&c,1);if(r<0)ExitProcess(19);U size=0;r=tsize(&c,&size);static char buffer[32768];if(r<0||size>sizeof(buffer)||size<33)ExitProcess(20);void*ptr=0;r=tresult(&c,sizeof(buffer),buffer,&ptr,0);num("Token result ",r);if(r<0||ptr!=buffer)ExitProcess(21);memset(buffer,0,sizeof(buffer));out("Fixture service token delivered without logging its value\r\n");
 struct A forced={0};r=tok(u,1,"GET","https://api.minecraftservices.com/",0,0,0,0,&forced);num("ForceRefresh start ",r);if(r<0)ExitProcess(40);r=status(&forced,1);num("ForceRefresh completion ",r);if(r<0)ExitProcess(41);r=tresult(&forced,sizeof(buffer),buffer,&ptr,0);num("ForceRefresh result ",r);if(r<0||ptr!=buffer)ExitProcess(42);memset(buffer,0,sizeof(buffer));out("ForceRefresh returned a newly renewed session through native async thunks\r\n");
 struct A f1={0},f2={0};if(tok(u,1,"GET","https://api.minecraftservices.com/",0,0,0,0,&f1)<0||tok(u,1,"GET","https://api.minecraftservices.com/",0,0,0,0,&f2)<0)ExitProcess(43);
 if(status(&f1,1)<0||status(&f2,1)<0)ExitProcess(44);
 if(tresult(&f1,sizeof(buffer),buffer,&ptr,0)<0)ExitProcess(45);memset(buffer,0,sizeof(buffer));
 if(tresult(&f2,sizeof(buffer),buffer,&ptr,0)<0)ExitProcess(46);memset(buffer,0,sizeof(buffer));
 out("Concurrent ForceRefresh results both returned valid newly issued sessions\r\n");ExitProcess(0);
}
