/* CrossOver fallback for the unavailable XNetworking connectivity interface.
   Measures a TLS-verified, unauthenticated HTTPS connection. It never asserts
   ownership, signs requests, or approves certificates. Other APIs stay unsupported. */
IMP U64 GetTickCount64(void);
struct NetHint {unsigned level,cost,type;unsigned char initialized,approach,over,roaming;};
static unsigned char netClass[16]={0x07,0x69,0xe5,0x37,0x10,0x2f,0xe8,0x41,0xb7,0x2f,0x36,0xed,0xb1,0x85,0x33,0x1a};
static unsigned char netIID[16]={0xb2,0x46,0x23,0xbf,0xaf,0x39,0x58,0x46,0xb5,0xea,0x44,0x71,0x3c,0x7e,0x83,0xb3};
static unsigned char unknownIID[16]={0,0,0,0,0,0,0,0,0xc0,0,0,0,0,0,0,0x46};
static int netGuidEq(const void*a,const void*b){if(!a||!b)return 0;const unsigned char*x=a,*y=b;for(unsigned i=0;i<16;i++)if(x[i]!=y[i])return 0;return 1;}
static int netGuid(const void*a){return netGuidEq(a,netClass)||netGuidEq(a,netIID);}
static U64 netLock,netLast;static struct NetHint measuredHint;
static int measureNet(struct NetHint*h){
 memset(h,0,sizeof(*h));h->level=1;h->cost=0;h->type=0;
 H ws=LoadLibraryA("ws2_32.dll");if(!ws)return (int)0x8007007e;
 int(*startup)(unsigned short,void*)=GetProcAddress(ws,"WSAStartup");int(*cleanup)(void)=GetProcAddress(ws,"WSACleanup");unsigned char wd[512]={0};
 if(!startup||startup(0x202,wd))return (int)0x80004005;h->initialized=1;
 H wh=LoadLibraryA("winhttp.dll");if(!wh){if(cleanup)cleanup();return (int)0x8007007e;}
 H(*open)(const unsigned short*,unsigned,const unsigned short*,const unsigned short*,unsigned)=GetProcAddress(wh,"WinHttpOpen");
 H(*connect)(H,const unsigned short*,unsigned short,unsigned)=GetProcAddress(wh,"WinHttpConnect");
 H(*request)(H,const unsigned short*,const unsigned short*,const unsigned short*,const unsigned short*,const unsigned short**,unsigned)=GetProcAddress(wh,"WinHttpOpenRequest");
 int(*timeouts)(H,int,int,int,int)=GetProcAddress(wh,"WinHttpSetTimeouts");
 int(*send)(H,const unsigned short*,unsigned,void*,unsigned,unsigned,U64)=GetProcAddress(wh,"WinHttpSendRequest");
 int(*receive)(H,void*)=GetProcAddress(wh,"WinHttpReceiveResponse");
 int(*query)(H,unsigned,const unsigned short*,void*,unsigned*,unsigned*)=GetProcAddress(wh,"WinHttpQueryHeaders");
 int(*close)(H)=GetProcAddress(wh,"WinHttpCloseHandle");
 if(!open||!connect||!request||!timeouts||!send||!receive||!query||!close){if(cleanup)cleanup();return (int)0x8007007f;}
 H session=open(L"Dungeons CrossOver connectivity check",0,0,0,0),server=0,req=0;
 unsigned status=0,size=4;int ok=0;
 if(session){timeouts(session,3000,3000,3000,3000);server=connect(session,L"login.live.com",443,0);}
 if(server)req=request(server,L"HEAD",L"/",0,0,0,0x800000);
 if(req&&send(req,0,0,0,0,0,0)&&receive(req,0)&&query(req,19|0x20000000,0,&status,&size,0))ok=status>=200&&status<500;
 if(req)close(req);if(server)close(server);if(session)close(session);if(cleanup)cleanup();
 if(ok)h->level=3;
 loghr("Measured HTTPS connectivity",ok?0:(int)0x80004005);loghr("Connectivity level",h->level);
 return 0;
}
static int netHint(void*self,struct NetHint*h){
 if(!h)return (int)0x80004003;AcquireSRWLockExclusive(&netLock);
 U64 now=GetTickCount64();int r=0;if(!netLast||now-netLast>=10000){r=measureNet(&measuredHint);netLast=GetTickCount64();}
 *h=measuredHint;ReleaseSRWLockExclusive(&netLock);return r;
}
static int netUnsupported(void*self){return (int)0x80004001;}
static unsigned netRef(void*self){return 1;}
static int netQI(void*self,const void*iid,void**p){if(!p)return (int)0x80004003;*p=0;if(netGuid(iid)||netGuidEq(iid,unknownIID)){*p=self;return 0;}return (int)0x80004002;}
struct NetReg{volatile int active,busy;void*queue,*ctx;void(*callback)(void*,const struct NetHint*);struct NetReg*next;};
static struct NetReg*netRegs;static U64 regLock;
static int(*queueSubmit)(void*,unsigned,void*,void(*)(void*,unsigned char));
static int(*queueDuplicate)(void*,void**);static void(*queueClose)(void*);
static void netNotify(void*p,unsigned char cancelled){struct NetReg*r=p;
 AcquireSRWLockExclusive(&regLock);int call=r->active&&!cancelled;if(call)r->busy++;ReleaseSRWLockExclusive(&regLock);
 if(call){struct NetHint h={0};netHint(0,&h);r->callback(r->ctx,&h);AcquireSRWLockExclusive(&regLock);r->busy--;ReleaseSRWLockExclusive(&regLock);}
}
static DWORD netWatch(void*p){struct NetReg*r=p;unsigned prev=0xffffffff;
 while(r->active){struct NetHint h={0};netHint(0,&h);unsigned val=h.level|(h.initialized<<8);
 if(val!=prev){prev=val;if(r->queue&&queueSubmit)queueSubmit(r->queue,1,r,netNotify);else netNotify(r,0);}
 for(unsigned i=0;i<20&&r->active;i++)Sleep(250);
 }if(r->queue&&queueClose)queueClose(r->queue);return 0;
}
static int netRegister(void*self,void*q,void*ctx,void*cb,U64*token){
 if(!cb||!token)return (int)0x80070057;*token=0;
 if(!thunks)thunks=loadSibling("xgameruntime-adapter-thunks.dll");
 if(thunks){queueSubmit=GetProcAddress(thunks,"XTaskQueueSubmitCallback");queueDuplicate=GetProcAddress(thunks,"XTaskQueueDuplicateHandle");queueClose=GetProcAddress(thunks,"XTaskQueueCloseHandle");}
 struct NetReg*r=HeapAlloc(GetProcessHeap(),8,sizeof(*r));if(!r)return (int)0x8007000e;
 if(q){if(!queueSubmit||!queueDuplicate||!queueClose){HeapFree(GetProcessHeap(),0,r);return (int)0x8007007f;}int hr=queueDuplicate(q,&r->queue);if(hr<0){HeapFree(GetProcessHeap(),0,r);return hr;}}
 r->ctx=ctx;r->callback=cb;r->active=1;AcquireSRWLockExclusive(&regLock);r->next=netRegs;netRegs=r;ReleaseSRWLockExclusive(&regLock);
 H t=CreateThread(0,0,netWatch,r,0,0);if(!t){r->active=0;if(r->queue)queueClose(r->queue);return (int)0x80004005;}CloseHandle(t);*token=(U64)r;loghr("Connectivity notification registered",0);return 0;
}
static unsigned char netUnregister(void*self,U64 token,unsigned char wait){
 AcquireSRWLockExclusive(&regLock);struct NetReg*r=netRegs;while(r&&(U64)r!=token)r=r->next;if(r)r->active=0;ReleaseSRWLockExclusive(&regLock);
 if(!r)return 0;if(wait)while(r->busy)Sleep(1);return 1;
}
static void*netVT[21]={netQI,netRef,netRef,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netUnsupported,netHint,netRegister,netUnregister,netUnsupported,netUnsupported,netUnsupported};
static struct{void**vt;}netObject={netVT};
static int tryNetwork(const void*a,const void*b,void**p,int nativeResult){
 if(!netGuid(a)||nativeResult!=(int)0x8924010d)return nativeResult;
 loghr("Unavailable native connectivity interface",nativeResult);return netQI(&netObject,b,p);
}
/* Advertise only the networking feature supplied above. All other feature
   checks and interfaces remain delegated to the native runtime. */
static unsigned char featureGuid[16]={0x87,0xfe,0x36,0x88,0xb9,0xed,0xe3,0x4f,0x8d,0xad,0x05,0xf0,0xd2,0xcd,0x5b,0x40};
static unsigned char networkFeature(void*self,unsigned feature){
 struct Proxy*p=self;unsigned char(*f)(void*,unsigned)=(*(void***)p->obj)[3];
 unsigned char available=f(p->obj,feature);
 if(feature==10){loghr("Native networking feature available",available);return 1;}
 return available;
}
static int featureQI(void*self,const void*iid,void**p){
 if(!p)return (int)0x80004003;*p=0;struct Proxy*w=self;
 if(netGuidEq(iid,featureGuid)||netGuidEq(iid,unknownIID)){
  unsigned(*add)(void*)=(*(void***)w->obj)[1];add(w->obj);*p=self;return 0;
 }
 int(*qi)(void*,const void*,void**)=(*(void***)w->obj)[0];return qi(w->obj,iid,p);
}
static unsigned featureRelease(void*self){
 struct Proxy*p=self;unsigned(*release)(void*)=(*(void***)p->obj)[2];
 unsigned refs=release(p->obj);if(!refs)HeapFree(GetProcessHeap(),0,p);return refs;
}
static void*featureVT[4]={featureQI,pass1,featureRelease,networkFeature};
static void wrapFeature(const void*a,const void*b,void**p){
 if(!netGuidEq(a,featureGuid)||!netGuidEq(b,featureGuid))return;
 struct Proxy*w=HeapAlloc(GetProcessHeap(),0,sizeof(*w));
 if(w){w->vt=featureVT;w->obj=*p;*p=w;}
}
