// Limited real-token user provider. Other runtime interfaces remain native.
// No fabricated identities, age groups, privileges, entitlement or token values.
#define FAIL ((int)0x80004005)
#define INVALID ((int)0x80070057)
#define NOTIMPL ((int)0x80004001)
#define NOUSER ((int)0x89245100)
struct Packet {U64 magic,expires,xuid;unsigned age,privKnown;unsigned char priv[32];char tags[4][128];char tokens[3][16384];U64 generation;};
static struct Packet cred;
static int authenticated, handleMarker;
static void* uservt[50];static void* tagvt[4];
static struct {void**vt;} userObj={uservt},tagObj={tagvt};
static int tablesReady;
static void* copy(void*d,const void*s,U64 n){unsigned char*a=d;const unsigned char*b=s;while(n--)*a++=*b++;return d;}
static int eq(const char*a,const char*b){if(!a||!b)return 0;while(*a&&*a==*b){a++;b++;}return *a==*b;}
static int bounded(const char*s,unsigned cap){for(unsigned i=0;i<cap;i++)if(!s[i])return 1;return 0;}
IMP int DeleteFileA(const char*);
IMP DWORD GetCurrentProcessId(void);
IMP U64 GetTickCount64(void);
static U64 credLock,lastCheck;
static int readAuth(void){
 char path[2048]={0};if(!dcPath(path,sizeof(path),"signed-out"))return NOUSER;
 if(GetFileAttributesA(path)!=0xffffffffUL){authenticated=0;memset(&cred,0,sizeof(cred));return NOUSER;}
 if(!dcPath(path,sizeof(path),"session.bin"))return NOUSER;
 H f=CreateFileA(path,0x80000000,7,0,3,128,0);
 if(f==(H)-1){authenticated=0;return NOUSER;}
 struct Packet*p=HeapAlloc(GetProcessHeap(),8,sizeof(*p));if(!p){CloseHandle(f);return FAIL;}
 DWORD n=0;int ok=ReadFile(f,p,sizeof(*p),&n,0);CloseHandle(f);U64 now;GetSystemTimeAsFileTime(&now);
 int r=0;
 if(!ok||n!=sizeof(*p)||p->magic!=0x3247444952425858ULL||!p->xuid||!p->generation||p->expires<=now||p->age>3)r=FAIL;
 for(unsigned i=0;!r&&i<4;i++)if(!bounded(p->tags[i],128))r=FAIL;
 for(unsigned i=0;!r&&i<3;i++)if(!p->tokens[i][0]||!bounded(p->tokens[i],16384))r=FAIL;
 if(!r&&cred.xuid&&p->xuid!=cred.xuid)r=NOUSER;
 if(!r){copy(&cred,p,sizeof(cred));authenticated=1;}else authenticated=0;
 memset(p,0,sizeof(*p));HeapFree(GetProcessHeap(),0,p);return r;
}
static int live(void){
 AcquireSRWLockExclusive(&credLock);U64 tick=GetTickCount64(),now;GetSystemTimeAsFileTime(&now);
 if(!lastCheck||tick-lastCheck>=1000||cred.expires<=now){readAuth();lastCheck=tick;}
 int r=authenticated&&cred.expires>now;ReleaseSRWLockExclusive(&credLock);return r;
}
static int valid(void*u){return u==&handleMarker&&live();}
static int loadAuth(void){AcquireSRWLockExclusive(&credLock);int r=readAuth();lastCheck=GetTickCount64();ReleaseSRWLockExclusive(&credLock);return r;}

// No refresh credential enters Wine. ForceRefresh sends a nonce and generation
// to the native helper, which renews through its own Keychain-backed OAuth flow.
static U64 requestLock,requestCounter;
static int forceRenew(void){
 AcquireSRWLockExclusive(&requestLock);U64 serial=++requestCounter;ReleaseSRWLockExclusive(&requestLock);
 U64 nonce=(GetTickCount64()<<24)^((U64)GetCurrentProcessId()<<8)^serial;
 char leaf[64]="refresh-",request[2048]={0},response[2048]={0};
 for(unsigned i=0;i<16;i++)leaf[8+i]="0123456789abcdef"[(nonce>>((15-i)*4))&15];
 leaf[24]=0;append(leaf,sizeof(leaf),".req");if(!dcPath(request,sizeof(request),leaf))return FAIL;
 leaf[25]='r';leaf[26]='e';leaf[27]='s';if(!dcPath(response,sizeof(response),leaf))return FAIL;
 U64 data[2]={0x3151455242434447ULL,0};AcquireSRWLockExclusive(&credLock);data[1]=cred.generation;U64 id=cred.xuid;ReleaseSRWLockExclusive(&credLock);
 if(!id)return NOUSER;
 H f=CreateFileA(request,0x40000000,0,0,1,128,0);if(f==(H)-1)return FAIL;
 DWORD n=0;int ok=WriteFile(f,data,sizeof(data),&n,0);CloseHandle(f);if(!ok||n!=sizeof(data)){DeleteFileA(request);return FAIL;}
 U64 until=GetTickCount64()+120000;int result=FAIL;
 while(GetTickCount64()<until){
  char stop[2048]={0};if(dcPath(stop,sizeof(stop),"signed-out")&&GetFileAttributesA(stop)!=0xffffffffUL){result=NOUSER;break;}
  H reply=CreateFileA(response,0x80000000,7,0,3,128,0);
  if(reply!=(H)-1){U64 answer[2]={0};n=0;ok=ReadFile(reply,answer,sizeof(answer),&n,0);CloseHandle(reply);
   if(ok&&n==sizeof(answer)){
    result=(int)answer[0];if(!result){result=loadAuth();AcquireSRWLockExclusive(&credLock);
     // Another concurrent genuine refresh may already have advanced the file.
     // Accept that newer issued session, never the pre-request generation.
     if(!result&&(cred.xuid!=id||cred.generation==data[1]||cred.generation<answer[1]))result=NOUSER;
     ReleaseSRWLockExclusive(&credLock);
    }break;
   }
  }Sleep(50);
 }
 DeleteFileA(request);DeleteFileA(response);loghr("Keychain-backed ForceRefresh result",result);return result;
}
// XUser interface identifiers from the reviewed compatibility source; active calls tested against Microsoft thunks.
struct Guid {unsigned a;unsigned short b,c;unsigned char d[8];};
static const struct Guid userGuids[]={
{0x01acd177,0x91f9,0x4763,{0xa3,0x8e,0xcc,0xbb,0x55,0xce,0x32,0xe0}},
{0xeb9bf948,0x18dc,0x4d82,{0xbb,0xcc,0x40,0xe0,0xa8,0x09,0xc4,0xc0}},
{0x1bf2f8c5,0xd507,0x4e52,{0xbb,0x05,0xf7,0x26,0xd0,0xe7,0x11,0x61}},
{0x079415e3,0x6727,0x437f,{0x8e,0x9d,0x8f,0x8f,0x9b,0x24,0x39,0xf7}},
{0x26f3c674,0xa2fe,0x44fa,{0xb6,0xc4,0xa3,0x23,0xbc,0x94,0xff,0x53}},
{0x5131d685,0x4394,0x4ee6,{0x8c,0x18,0xbf,0xb5,0xd4,0xae,0xf1,0xff}}};
static const struct Guid tagGuid={0xcef4fac0,0x7676,0x4a94,{0xa1,0x19,0x4c,0x43,0xf9,0xeb,0x5b,0x74}};
static const struct Guid unknownGuid={0,0,0,{0xc0,0,0,0,0,0,0,0x46}};
static int guidEq(const void*a,const void*b){if(!a||!b)return 0;for(int i=0;i<16;i++)if(((unsigned char*)a)[i]!=((unsigned char*)b)[i])return 0;return 1;}
static int isUserGuid(const void*g){for(int i=0;i<6;i++)if(guidEq(g,&userGuids[i]))return 1;return 0;}
static int isTagGuid(const void*g){return guidEq(g,&tagGuid);}
static void initTables(void);
static int userQI(void*s,const void*g,void**o){if(!o)return INVALID;*o=0;initTables();loghr("User interface requested",g?*(unsigned*)g:0);if(isUserGuid(g)||guidEq(g,&unknownGuid)){*o=&userObj;return 0;}if(isTagGuid(g)){*o=&tagObj;return 0;}return (int)0x80004002;}
static unsigned ref(void*s){return 1;}
static int unsupported(void*s){loghr("Unsupported user API",NOTIMPL);return NOTIMPL;}
static int dupUser(void*s,void*u,void**out){loghr("dupUser",0);if(!out)return INVALID;*out=0;if(!valid(u))return NOUSER;*out=u;return 0;}
static void closeUser(void*s,void*u){loghr("closeUser",0);}
static int compareUser(void*s,void*a,void*b){return a==b?0:(U64)a<(U64)b?-1:1;}
static int maxUsers(void*s,unsigned*out){if(!out)return INVALID;*out=1;return 0;}
struct PD {void*async;U64 size;void*buffer;void*context;};
struct TokenData {U64 tokenSize,signatureSize;void*token;void*signature;};
struct Op {int kind,wide,index;char token[16384];};
static char addIdentity,tokenIdentity;
static int provider(unsigned op,const struct PD*d){struct Op*c=d->context;
 if(op==0)return aschedule(d->async,0);
 if(op==1){int r=c->kind==2?forceRenew():0;
  if(!r&&!live())r=NOUSER;
  if(!r&&c->kind==2){AcquireSRWLockExclusive(&credLock);copy(c->token,cred.tokens[c->index],16384);ReleaseSRWLockExclusive(&credLock);}
  U64 n=c->kind==0?sizeof(void*):sizeof(struct TokenData)+(len(c->token)+1)*(c->wide?2:1);acomplete(d->async,r,r<0?0:n);return 0;}
 if(op==2){if(c->kind==0){*(void**)d->buffer=&handleMarker;return 0;}
 struct TokenData*t=d->buffer;U64 n=len(c->token);t->tokenSize=n+1;t->signatureSize=0;t->token=t+1;t->signature=0;
 if(c->wide){unsigned short*p=t->token;for(U64 i=0;i<=n;i++)p[i]=(unsigned char)c->token[i];}else copy(t->token,c->token,n+1);return 0;}
 if(op==3)return 0; // Work is bounded and already scheduled; it completes normally.
 if(op==4){memset(c,0,sizeof(*c));HeapFree(GetProcessHeap(),0,c);return 0;}
 return INVALID;
}
static int start(void*a,int kind,const char*t,int wide){if(!a||!initAsync())return FAIL;struct Op*c=HeapAlloc(GetProcessHeap(),8,sizeof(*c));if(!c)return FAIL;c->kind=kind;c->wide=wide;if(t)copy(c->token,t,len(t)+1);int r=abegin(a,c,kind?&tokenIdentity:&addIdentity,kind?"RealXboxToken":"RealXboxUser",provider);if(r<0){memset(c,0,sizeof(*c));HeapFree(GetProcessHeap(),0,c);}return r;}
static int startToken(void*a,int index,int wide,int refresh){
 if(!a||!initAsync())return FAIL;struct Op*c=HeapAlloc(GetProcessHeap(),8,sizeof(*c));if(!c)return FAIL;
 c->kind=refresh?2:1;c->wide=wide;c->index=index;AcquireSRWLockExclusive(&credLock);copy(c->token,cred.tokens[index],16384);ReleaseSRWLockExclusive(&credLock);
 int r=abegin(a,c,&tokenIdentity,"RealXboxToken",provider);if(r<0){memset(c,0,sizeof(*c));HeapFree(GetProcessHeap(),0,c);}return r;
}
static int addUser(void*s,unsigned options,void*a){loghr("XUserAddAsync options",options);int r=loadAuth();if(r<0){loghr("No valid real session",r);return r;}return start(a,0,0,0);}
static int addResult(void*s,void*a,void**out){if(!out)return INVALID;*out=0;int r=aresult(a,&addIdentity,sizeof(void*),out,0);loghr("XUserAddResult",r);return r;}
// The native WithUi thunk supplies exactly (self, requested XUID, async).
// Support only the same account verified by the genuine session. A different
// requested user, expired session or missing async block never returns a handle.
static int addById(void*s,U64 id,void*a){
 if(!a)return INVALID;int r=loadAuth();if(r<0){loghr("XUserAddByIdWithUi no valid session",r);return r;}
 int matches=id==cred.xuid;loghr("XUserAddByIdWithUi matches authenticated user",matches);
 if(!matches)return NOUSER;return start(a,0,0,0);
}
static int addByIdResult(void*s,void*a,void**out){if(!out)return INVALID;*out=0;int r=addResult(s,a,out);loghr("XUserAddByIdWithUiResult",r);return r;}
static int localId(void*s,void*u,U64*out){loghr("localId",0);if(!out)return INVALID;if(!valid(u))return NOUSER;*out=1;return 0;}
static int findLocal(void*s,U64 id,void**o){loghr("findLocal",0);return id==1?dupUser(s,&handleMarker,o):NOUSER;}
static int getId(void*s,void*u,U64*out){loghr("getId",0);if(!out)return INVALID;if(!valid(u))return NOUSER;*out=cred.xuid;return 0;}
static int findId(void*s,U64 id,void**o){loghr("findId",0);return live()&&id==cred.xuid?dupUser(s,&handleMarker,o):NOUSER;}
static int guest(void*s,void*u,unsigned char*out){loghr("guest",0);if(!out)return INVALID;if(!valid(u))return NOUSER;*out=0;return 0;}
static int state(void*s,void*u,unsigned*out){loghr("state",0);if(!out)return INVALID;*out=valid(u)?0:2;return u==&handleMarker?0:NOUSER;}
static int age(void*s,void*u,unsigned*out){loghr("age",0);if(!out)return INVALID;*out=0;if(!valid(u))return NOUSER;*out=cred.age;return 0;}
static int privilege(void*s,void*u,unsigned opts,unsigned id,unsigned char*has,unsigned*reason){if(!has)return INVALID;*has=0;if(reason)*reason=0xffffffff;if(!valid(u))return NOUSER;loghr("Privilege requested",id);if(opts||id>=256||!cred.privKnown)return NOTIMPL;*has=(cred.priv[id/8]>>(id%8))&1;if(reason)*reason=*has?0:0xffffffff;return 0;}
static int tag(void*s,void*u,unsigned component,U64 size,char*b,U64*used){if(!valid(u))return NOUSER;if(component>=4||!b)return INVALID;loghr("Gamertag component",component);const char*t=cred.tags[component];if(component!=2&&!t[0])return NOTIMPL;U64 n=len(t)+1;if(used)*used=n;if(size<n)return (int)0x8007007a;copy(b,t,n);return 0;}
static int domain(const char*h,const char*d){unsigned n=len(h),m=len(d);return eq(h,d)||(n>m&&h[n-m-1]=='.'&&eq(h+n-m,d));}
static int tokenIndex(const char*url){char h[256]={0};if(!url)return -1;const char*p="https://";while(*p)if(*url++!=*p++)return -1;unsigned n=0;while(*url&&*url!='/'&&*url!='?'&&*url!='#'){char c=*url++;if(n>=254||c==':'||c=='@'||c=='\\')return -1;h[n++]=(c>='A'&&c<='Z')?c+32:c;}
 loghr(h,0);
 if(eq(h,"api.minecraftservices.com"))return 1;
 if(domain(h,"playfabapi.com"))return 2;
 if(domain(h,"xboxlive.com"))return 0;
 char message[256]={0};append(message,256,"Refused token host: ");append(message,256,h);loghr(message,NOTIMPL);return -1;
}
static int tokenAsync(void*s,void*u,unsigned opts,const char*method,const char*url,U64 nh,const void*headers,U64 nb,const void*body,void*a){if(opts&~1U)return NOTIMPL;if(u!=&handleMarker||(!(opts&1)&&!valid(u)))return NOUSER;int idx=tokenIndex(url);if(idx<0)return NOTIMPL;loghr("Service token requested",idx);return startToken(a,idx,0,opts&1);}
static int token16(void*s,void*u,unsigned opts,const unsigned short*method,const unsigned short*url,U64 nh,const void*headers,U64 nb,const void*body,void*a){if(opts&~1U)return NOTIMPL;if(u!=&handleMarker||!url||(!(opts&1)&&!valid(u)))return NOUSER;char v[2048];unsigned i=0;for(;i<2047&&url[i];i++){if(url[i]>127)return NOTIMPL;v[i]=(char)url[i];}if(url[i])return INVALID;v[i]=0;int idx=tokenIndex(v);if(idx<0)return NOTIMPL;return startToken(a,idx,1,opts&1);}
static int tokenSize(void*s,void*a,U64*n){return asize(a,n);}
static int tokenResult(void*s,void*a,U64 size,void*b,void**ptr,U64*used){if(!ptr)return INVALID;*ptr=0;int r=aresult(a,&tokenIdentity,size,b,used);if(r>=0)*ptr=b;loghr("Service token result",r);return r;}
// This is a single-account provider. Multi-user/signature APIs remain limited.
static int changeRegister(void*s,void*q,void*ctx,void*cb,U64*token){loghr("changeRegister",0);if(!token)return INVALID;*token=1;return 0;}
static unsigned char changeUnregister(void*s,U64 token,unsigned char wait){loghr("changeUnregister",0);return token==1;}
static unsigned char noStore(void*s,void*u){return 0;}
static unsigned char noSignoutUI(void*s){return 0;}
static int unsupported0(void*s){loghr("Unsupported XUserQueryInterface",NOTIMPL);return NOTIMPL;}
static int unsupported1(void*s){loghr("Unsupported XUserAddRef",NOTIMPL);return NOTIMPL;}
static int unsupported2(void*s){loghr("Unsupported XUserRelease",NOTIMPL);return NOTIMPL;}
static int unsupported3(void*s){loghr("Unsupported XUserDuplicateHandle",NOTIMPL);return NOTIMPL;}
static int unsupported4(void*s){loghr("Unsupported XUserCloseHandle",NOTIMPL);return NOTIMPL;}
static int unsupported5(void*s){loghr("Unsupported XUserCompare",NOTIMPL);return NOTIMPL;}
static int unsupported6(void*s){loghr("Unsupported XUserGetMaxUsers",NOTIMPL);return NOTIMPL;}
static int unsupported7(void*s){loghr("Unsupported XUserAddAsync",NOTIMPL);return NOTIMPL;}
static int unsupported8(void*s){loghr("Unsupported XUserAddResult",NOTIMPL);return NOTIMPL;}
static int unsupported9(void*s){loghr("Unsupported XUserGetLocalId",NOTIMPL);return NOTIMPL;}
static int unsupported10(void*s){loghr("Unsupported XUserFindLocal",NOTIMPL);return NOTIMPL;}
static int unsupported11(void*s){loghr("Unsupported XUserGetId",NOTIMPL);return NOTIMPL;}
static int unsupported12(void*s){loghr("Unsupported XUserFindId",NOTIMPL);return NOTIMPL;}
static int unsupported13(void*s){loghr("Unsupported XUserIsGuest",NOTIMPL);return NOTIMPL;}
static int unsupported14(void*s){loghr("Unsupported XUserGetState",NOTIMPL);return NOTIMPL;}
static int unsupported15(void*s){loghr("Unsupported XUserAudioEndpoint",NOTIMPL);return NOTIMPL;}
static int unsupported16(void*s){loghr("Unsupported XUserGamerPictureAsync",NOTIMPL);return NOTIMPL;}
static int unsupported17(void*s){loghr("Unsupported XUserGamerPictureSize",NOTIMPL);return NOTIMPL;}
static int unsupported18(void*s){loghr("Unsupported XUserGamerPictureResult",NOTIMPL);return NOTIMPL;}
static int unsupported19(void*s){loghr("Unsupported XUserAgeGroup",NOTIMPL);return NOTIMPL;}
static int unsupported20(void*s){loghr("Unsupported XUserCheckPrivilege",NOTIMPL);return NOTIMPL;}
static int unsupported21(void*s){loghr("Unsupported XUserResolvePrivilegeAsync",NOTIMPL);return NOTIMPL;}
static int unsupported22(void*s){loghr("Unsupported XUserResolvePrivilegeResult",NOTIMPL);return NOTIMPL;}
static int unsupported23(void*s){loghr("Unsupported XUserTokenAsync",NOTIMPL);return NOTIMPL;}
static int unsupported24(void*s){loghr("Unsupported XUserTokenSize",NOTIMPL);return NOTIMPL;}
static int unsupported25(void*s){loghr("Unsupported XUserTokenResult",NOTIMPL);return NOTIMPL;}
static int unsupported26(void*s){loghr("Unsupported XUserToken16Async",NOTIMPL);return NOTIMPL;}
static int unsupported27(void*s){loghr("Unsupported XUserToken16Size",NOTIMPL);return NOTIMPL;}
static int unsupported28(void*s){loghr("Unsupported XUserToken16Result",NOTIMPL);return NOTIMPL;}
static int unsupported29(void*s){loghr("Unsupported XUserResolveIssueAsync",NOTIMPL);return NOTIMPL;}
static int unsupported30(void*s){loghr("Unsupported XUserResolveIssueResult",NOTIMPL);return NOTIMPL;}
static int unsupported31(void*s){loghr("Unsupported XUserResolveIssue16Async",NOTIMPL);return NOTIMPL;}
static int unsupported32(void*s){loghr("Unsupported XUserResolveIssue16Result",NOTIMPL);return NOTIMPL;}
static int unsupported33(void*s){loghr("Unsupported XUserRegisterChange",NOTIMPL);return NOTIMPL;}
static int unsupported34(void*s){loghr("Unsupported XUserUnregisterChange",NOTIMPL);return NOTIMPL;}
static int unsupported35(void*s){loghr("Unsupported XUserSignoutDeferral",NOTIMPL);return NOTIMPL;}
static int unsupported36(void*s){loghr("Unsupported XUserCloseDeferral",NOTIMPL);return NOTIMPL;}
static int unsupported37(void*s){loghr("Unsupported XUserAddByIdAsync",NOTIMPL);return NOTIMPL;}
static int unsupported38(void*s){loghr("Unsupported XUserAddByIdResult",NOTIMPL);return NOTIMPL;}
static int unsupported39(void*s){loghr("Unsupported XUserMSATokenAsync",NOTIMPL);return NOTIMPL;}
static int unsupported40(void*s){loghr("Unsupported XUserMSATokenResult",NOTIMPL);return NOTIMPL;}
static int unsupported41(void*s){loghr("Unsupported XUserMSATokenSize",NOTIMPL);return NOTIMPL;}
static int unsupported42(void*s){loghr("Unsupported XUserIsStoreUser",NOTIMPL);return NOTIMPL;}
static int unsupported43(void*s){loghr("Unsupported XUserRemoteHandlers",NOTIMPL);return NOTIMPL;}
static int unsupported44(void*s){loghr("Unsupported XUserRemoteCancel",NOTIMPL);return NOTIMPL;}
static int unsupported45(void*s){loghr("Unsupported XUserSpopHandlers",NOTIMPL);return NOTIMPL;}
static int unsupported46(void*s){loghr("Unsupported XUserSpopComplete",NOTIMPL);return NOTIMPL;}
static int unsupported47(void*s){loghr("Unsupported XUserSignoutPresent",NOTIMPL);return NOTIMPL;}
static int unsupported48(void*s){loghr("Unsupported XUserSignoutAsync",NOTIMPL);return NOTIMPL;}
static int unsupported49(void*s){loghr("Unsupported XUserSignoutResult",NOTIMPL);return NOTIMPL;}
static void initTables(void){if(tablesReady)return;uservt[0]=unsupported0;uservt[1]=unsupported1;uservt[2]=unsupported2;uservt[3]=unsupported3;uservt[4]=unsupported4;uservt[5]=unsupported5;uservt[6]=unsupported6;uservt[7]=unsupported7;uservt[8]=unsupported8;uservt[9]=unsupported9;uservt[10]=unsupported10;uservt[11]=unsupported11;uservt[12]=unsupported12;uservt[13]=unsupported13;uservt[14]=unsupported14;uservt[15]=unsupported15;uservt[16]=unsupported16;uservt[17]=unsupported17;uservt[18]=unsupported18;uservt[19]=unsupported19;uservt[20]=unsupported20;uservt[21]=unsupported21;uservt[22]=unsupported22;uservt[23]=unsupported23;uservt[24]=unsupported24;uservt[25]=unsupported25;uservt[26]=unsupported26;uservt[27]=unsupported27;uservt[28]=unsupported28;uservt[29]=unsupported29;uservt[30]=unsupported30;uservt[31]=unsupported31;uservt[32]=unsupported32;uservt[33]=unsupported33;uservt[34]=unsupported34;uservt[35]=unsupported35;uservt[36]=unsupported36;uservt[37]=unsupported37;uservt[38]=unsupported38;uservt[39]=unsupported39;uservt[40]=unsupported40;uservt[41]=unsupported41;uservt[42]=unsupported42;uservt[43]=unsupported43;uservt[44]=unsupported44;uservt[45]=unsupported45;uservt[46]=unsupported46;uservt[47]=unsupported47;uservt[48]=unsupported48;uservt[49]=unsupported49;
 uservt[0]=userQI;uservt[1]=ref;uservt[2]=ref;uservt[3]=dupUser;uservt[4]=closeUser;uservt[5]=compareUser;uservt[6]=maxUsers;uservt[7]=addUser;uservt[8]=addResult;
 uservt[9]=localId;uservt[10]=findLocal;uservt[11]=getId;uservt[12]=findId;uservt[13]=guest;uservt[14]=state;uservt[19]=age;uservt[20]=privilege;
 uservt[23]=tokenAsync;uservt[24]=tokenSize;uservt[25]=tokenResult;uservt[26]=token16;uservt[27]=tokenSize;uservt[28]=tokenResult;uservt[33]=changeRegister;uservt[34]=changeUnregister;uservt[37]=addById;uservt[38]=addByIdResult;uservt[42]=noStore;uservt[47]=noSignoutUI;
 tagvt[0]=userQI;tagvt[1]=ref;tagvt[2]=ref;tagvt[3]=tag;tablesReady=1;
}
