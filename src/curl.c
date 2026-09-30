typedef unsigned long DWORD;
typedef void *HANDLE;
__declspec(dllimport) HANDLE LoadLibraryA(const char*);
__declspec(dllimport) void* GetProcAddress(HANDLE,const char*);
__declspec(dllimport) HANDLE CreateFileA(const char*,DWORD,DWORD,void*,DWORD,DWORD,HANDLE);
__declspec(dllimport) int WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);
__declspec(dllimport) int CloseHandle(HANDLE);
void* memset(void*p,int v,unsigned long long n){volatile unsigned char*c=p;while(n--)*c++=v;return p;}
static HANDLE module,self;
#define IMP __declspec(dllimport)
#define H HANDLE
static unsigned len(const char*s){unsigned n=0;while(s&&s[n])n++;return n;}
static void pathAppend(char*b,unsigned cap,const char*s){unsigned n=len(b);while(s&&*s&&n+1<cap)b[n++]=*s++;b[n]=0;}
#define append pathAppend
#include "paths.inc"
#undef append
static char trustedCA[2048];
static void setupCA(void){if(trustedCA[0])return;DWORD n=GetModuleFileNameA(self,trustedCA,sizeof(trustedCA));if(!n||n>=sizeof(trustedCA)){trustedCA[0]=0;return;}while(n&&trustedCA[n-1]!='\\'&&trustedCA[n-1]!='/')n--;trustedCA[n]=0;pathAppend(trustedCA,sizeof(trustedCA),"curl-ca-bundle.crt");}
static void* fn(const char*s){if(!module)module=LoadLibraryA("curl-compat.dll");return GetProcAddress(module,s);}
static void logline(const char*s){if(!dcLogging())return;char path[2048]={0};if(!dcPath(path,sizeof(path),"http.log"))return;DWORD n=len(s),w;HANDLE h=CreateFileA(path,4,3,0,4,128,0);if(h!=(HANDLE)-1){WriteFile(h,s,n,&w,0);CloseHandle(h);}}
static int append(char*b,int n,const char*s){while(*s&&n<490)b[n++]=*s++;return n;}
static int number(char*b,int n,int v){char t[12];int k=0;if(v<0){b[n++]='-';v=-v;}do{t[k++]='0'+v%10;v/=10;}while(v&&k<11);while(k)b[n++]=t[--k];return n;}
#include "framing.inc"
static void result(void*easy,int code){
 int(*get)(void*,int,...)=fn("curl_easy_getinfo");char*url=0;long status=0;
 get(easy,0x100001,&url);get(easy,0x200002,&status);
 traceResult(easy,status);restoreRequestSize(trace(easy,0));
 char b[512];int n=append(b,0,"connection curl=");n=number(b,n,code);n=append(b,n," http=");n=number(b,n,status);n=append(b,n," host=");
 if(url){const char*p=url;while(*p&&*p!=':')p++;if(*p==':'&&p[1]=='/'&&p[2]=='/')p+=3;else p=url;int count=0;while(*p&&*p!='/'&&*p!='?'&&*p!='#'&&n<450&&count++<180)b[n++]=*p++;}
 b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
}
struct Msg{int type;void*easy;union{void*p;int code;}data;};
__declspec(dllexport) struct Msg* curl_multi_info_read(void*m,int*remaining){struct Msg*(*call)(void*,int*)=fn("curl_multi_info_read");struct Msg*r=call(m,remaining);if(r&&r->type==1)result(r->easy,r->data.code);return r;}
__declspec(dllexport) int curl_easy_perform(void*e){int(*call)(void*)=fn("curl_easy_perform");applyRequestSize(e);int r=call(e);result(e,r);return r;}
__declspec(dllexport) int curl_multi_add_handle(void*m,void*e){int(*call)(void*,void*)=fn("curl_multi_add_handle");applyRequestSize(e);int r=call(m,e);if(r)restoreRequestSize(trace(e,0));return r;}
__declspec(dllexport) int curl_global_init(long flags){int(*call)(long)=fn("curl_global_init");logline("diagnostic loaded\r\n");return call(flags);}
__declspec(dllexport) int curl_easy_setopt(void*e,int opt,void*value){
 int(*call)(void*,int,...)=fn("curl_easy_setopt");
 // Unreal supplies an OpenSSL 1.1 SSL_CTX callback, but this library uses
 // LibreSSL. Refuse unsupported customization honestly instead of passing an
 // incompatible SSL_CTX to the game. libcurl still verifies peers and hosts.
 if((opt==20108||opt==10109)&&value){logline("Incompatible SSL_CTX customization refused: CURLE_NOT_BUILT_IN\r\n");return 4;}
 // Keep ordinary peer and hostname verification when context customization is
 // unavailable. NULL CAINFO cannot remove the explicitly configured trust file.
 if((opt==64&&!value)||(opt==81&&(unsigned long long)value<2)||(opt==10065&&!value)){logline("Unsupported TLS verification reduction refused\r\n");return 4;}
 struct Trace*t=trace(e,1);
 if(t&&(opt==20094||opt==10095||opt==41||opt==20011||opt==10001||opt==10023)){
  if(opt==20094)t->debug=value;
  if(opt==10095)t->debugdata=value;
  if(opt==41)t->verbose=(int)(unsigned long long)value;
  if(opt==20011)t->write=value;
  if(opt==10001)t->writedata=value;
  if(opt==10023)t->headers=value;
  int r=call(e,opt,value);if(!r&&t->apiSelected)configureTrace(t);return r;
 }
 if(t&&opt==10002)restoreRequestSize(t);
 int r=call(e,opt,value);
 if(!r&&t&&(opt==60||opt==30120)){t->originalPostSize=opt==60?(long)(unsigned long long)value:(long long)value;t->sizeOverrideApplied=0;}
 if(!r&&t&&(opt==14||opt==30115)){t->originalUploadSize=opt==14?(long)(unsigned long long)value:(long long)value;t->sizeOverrideApplied=0;}
 if(!r&&t&&opt==46)t->upload=value!=0;
 if(!r&&t&&opt==10002){
  erase(t->incoming,sizeof(t->incoming));erase(t->outgoing,sizeof(t->outgoing));t->inlen=t->outlen=0;t->inoverflow=t->outoverflow=t->contenttype=t->encoding=0;
  t->selected=selectedURL(value);t->apiSelected=apiURL(value,t->operation);configureTrace(t);
 }
 if(r||opt==10065||opt==64||opt==81||opt==216){char b[512];int n=append(b,0,"option=");n=number(b,n,opt);n=append(b,n," result=");n=number(b,n,r);if(opt==10065&&value){n=append(b,n," CAfile=");n=append(b,n,(char*)value);}else if(opt==64||opt==81||opt==216){n=append(b,n," value=");n=number(b,n,(int)(unsigned long long)value);}b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);}
 return r;
}

__declspec(dllexport) int curl_global_init_mem(long flags,void*a,void*b,void*c,void*d,void*e){int(*call)(long,void*,void*,void*,void*,void*)=fn("curl_global_init_mem");logline("curl_global_init_mem called\r\n");return call(flags,a,b,c,d,e);}
__declspec(dllexport) void* curl_easy_init(void){void*(*call)(void)=fn("curl_easy_init");int(*set)(void*,int,...)=fn("curl_easy_setopt");logline("curl_easy_init called\r\n");void*e=call();if(e){setupCA();set(e,10065,trustedCA);set(e,64,(void*)1);set(e,81,(void*)2);trace(e,1);}return e;}
int DllMain(HANDLE m,DWORD why,void*r){if(why==1)self=m;return 1;}

__declspec(dllexport) void curl_easy_cleanup(void*e){
 void(*call)(void*)=fn("curl_easy_cleanup");call(e);
 struct Trace*t=trace(e,0);if(t){AcquireSRWLockExclusive(&tracelock);erase(t,sizeof(*t));ReleaseSRWLockExclusive(&tracelock);}
}
__declspec(dllexport) void curl_easy_reset(void*e){
 void(*call)(void*)=fn("curl_easy_reset");int(*set)(void*,int,...)=fn("curl_easy_setopt");call(e);
 struct Trace*t=trace(e,1);if(t){erase(t,sizeof(*t));t->easy=e;t->originalPostSize=t->originalUploadSize=-1;}
 setupCA();set(e,10065,trustedCA);set(e,64,(void*)1);set(e,81,(void*)2);
}
__declspec(dllexport) void* curl_easy_duphandle(void*e){
 void*(*call)(void*)=fn("curl_easy_duphandle");void*r=call(e);if(!r)return 0;
 struct Trace*source=trace(e,0),*target=trace(r,1);
 if(target&&source){target->selected=source->selected;target->apiSelected=source->apiSelected;for(int i=0;i<129;i++)target->operation[i]=source->operation[i];target->verbose=source->verbose;target->debug=source->debug;target->debugdata=source->debugdata;target->write=source->write;target->writedata=source->writedata;target->headers=source->headers;target->originalPostSize=source->originalPostSize;target->originalUploadSize=source->originalUploadSize;target->upload=source->upload;target->sizeOverrideApplied=source->sizeOverrideApplied;configureTrace(target);}
 else if(!target){int(*set)(void*,int,...)=fn("curl_easy_setopt");set(r,20094,source?source->debug:0);set(r,10095,source?source->debugdata:0);set(r,41,(void*)(unsigned long long)(source?source->verbose:0));if(source){set(r,20011,source->write);set(r,10001,source->writedata);set(r,10023,source->headers);}}
 return r;
}
