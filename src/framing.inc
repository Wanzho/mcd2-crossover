// Restricted, temporary observation of the game's own Steam login request.
// Raw bodies stay in RAM, are bounded, and are wiped after completion. Only
// whitelisted metadata and numeric/error identifiers can reach the log.
typedef unsigned long long SIZE;
typedef struct { void *p; } LOCK;
__declspec(dllimport) void AcquireSRWLockExclusive(LOCK*);
__declspec(dllimport) void ReleaseSRWLockExclusive(LOCK*);
typedef int (*DEBUGFN)(void*,int,char*,SIZE,void*);
typedef SIZE (*WRITEFN)(char*,SIZE,SIZE,void*);
struct Trace {
 void *easy; int selected,apiSelected,verbose; char operation[129]; DEBUGFN debug; void *debugdata;
 WRITEFN write; void *writedata;
 void *headers; int originalCTCount,originalCTKind;
 long long originalPostSize,originalUploadSize; int upload,sizeOverrideApplied;
 SIZE sentBytes,declaredBytes; int declaredSeen,declaredInvalid;
 int contentEncodingSeen,transferEncodingSeen,chunkedSeen,expectSeen;
 unsigned inlen,outlen; int inoverflow,outoverflow,contenttype,encoding;
 char incoming[8193],outgoing[8193];
};
static LOCK tracelock;
static struct Trace traces[128];
static void erase(void*p,SIZE n){volatile unsigned char*s=p;while(n--)*s++=0;}
static struct Trace* trace(void*e,int create){
 struct Trace*r=0;AcquireSRWLockExclusive(&tracelock);
 for(int i=0;i<128;i++)if(traces[i].easy==e){r=&traces[i];break;}
 if(!r&&create)for(int i=0;i<128;i++)if(!traces[i].easy){r=&traces[i];erase(r,sizeof(*r));r->easy=e;r->originalPostSize=r->originalUploadSize=-1;break;}
 ReleaseSRWLockExclusive(&tracelock);return r;
}
static int same(const char*a,const char*b){if(!a)return 0;while(*a&&*a==*b){a++;b++;}return *a==*b;}
static int selectedURL(const char*u){return same(u,"https://83156.playfabapi.com/Client/LoginWithSteam");}
static int begins(const char*u,const char*base){if(!u)return 0;while(*base)if(*u++!=*base++)return 0;return 1;}
static int apiURL(const char*u,char*operation){
 const char*base="https://83156.playfabapi.com/";
 if(begins(u,"https://vex.minecraftservices.com/")){const char*label="minecraft-service";int n=0;while(label[n]){operation[n]=label[n];n++;}operation[n]=0;return 1;}
 if(!begins(u,base))return 0;while(*base){u++;base++;}
 int n=0;while(*u&&*u!='?'&&*u!='#'&&n<128){char c=*u++;if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||c=='/')){const char*label="title-api";n=0;while(label[n]){operation[n]=label[n];n++;}operation[n]=0;return 1;}operation[n++]=c;}
 if(n==128||!n){const char*label="title-api";n=0;while(label[n]){operation[n]=label[n];n++;}}operation[n]=0;return 1;
}
static void capture(char*b,unsigned*n,int*overflow,const char*p,SIZE size){
 if(size>8192-*n){*overflow=1;size=8192-*n;}
 for(SIZE i=0;i<size;i++)b[(*n)++]=p[i];b[*n]=0;
}
static int contains(const char*b,SIZE n,const char*phrase){
 for(SIZE i=0;i<n;i++){SIZE j=0;while(phrase[j]&&i+j<n){char a=b[i+j],c=phrase[j];if(a>='A'&&a<='Z')a+=32;if(c>='A'&&c<='Z')c+=32;if(a!=c)break;j++;}if(!phrase[j])return 1;}return 0;
}
static int boundedSame(const char*p,SIZE n,const char*s){SIZE i=0;while(s[i]){if(i>=n)return 0;char a=p[i],b=s[i];if(a>='A'&&a<='Z')a+=32;if(a!=b)return 0;i++;}return i==n;}
static int unsignedNumber(char*b,int n,SIZE value){char tmp[21];int k=0;do{tmp[k++]='0'+value%10;value/=10;}while(value&&k<20);while(k&&n<480)b[n++]=tmp[--k];return n;}
static void headerMetadata(struct Trace*t,const char*p,SIZE size,const char*source){
 SIZE colon=0;while(colon<size&&p[colon]!=':')colon++;
 int valid=colon>0&&colon<=128&&colon<size;
 for(SIZE i=0;valid&&i<colon;i++){char c=p[i];if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.'))valid=0;}
 char b[512];int n=append(b,0,"playfab header source=");n=append(b,n,source);n=append(b,n," name=");
 if(valid)for(SIZE i=0;i<colon;i++)b[n++]=p[i];else n=append(b,n,"[invalid-or-suppressed]");
 n=append(b,n," nameValid=");n=number(b,n,valid);b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
 if(!valid)return;
 const char*value=p+colon+1;SIZE raw=size-colon-1,leading=0;
 while(leading<raw&&(value[leading]==' '||value[leading]=='\t'))leading++;
 if(boundedSame(p,colon,"content-type")){
  int unusual=0;for(SIZE i=0;i<raw;i++){unsigned char c=value[i];if(c<32||c>126)unusual++;}
  n=append(b,0,"playfab Content-Type source=");n=append(b,n,source);n=append(b,n," rawValueBytes=");n=unsignedNumber(b,n,raw);n=append(b,n," valueBytesWithoutLeadingOWS=");n=unsignedNumber(b,n,raw-leading);n=append(b,n," leadingOWSBytes=");n=unsignedNumber(b,n,leading);n=append(b,n," unusualBytes=");n=number(b,n,unusual);b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
  for(SIZE i=0;i<raw;i++){unsigned char c=value[i];if(c<32||c>126){n=append(b,0,"playfab Content-Type unusual byte source=");n=append(b,n,source);n=append(b,n," offset=");n=unsignedNumber(b,n,i);n=append(b,n," byteDecimal=");n=number(b,n,c);b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);}}
 }
 if(source[0]!='w')return;
 if(boundedSame(p,colon,"content-encoding"))t->contentEncodingSeen=1;
 if(boundedSame(p,colon,"transfer-encoding")){t->transferEncodingSeen=1;if(contains(value,raw,"chunked"))t->chunkedSeen=1;}
 if(boundedSame(p,colon,"expect"))t->expectSeen=1;
 if(boundedSame(p,colon,"content-length")){
  SIZE valueNumber=0,i=leading;int digits=0,invalid=0;
  while(i<raw&&value[i]>='0'&&value[i]<='9'){if(valueNumber>0x7fffffffffffffffULL/10){invalid=1;break;}valueNumber=valueNumber*10+value[i++]-'0';digits++;}
  while(i<raw&&(value[i]==' '||value[i]=='\t'))i++;
  if(!digits||i!=raw)invalid=1;
  if(t->declaredSeen&&t->declaredBytes!=valueNumber)invalid=1;
  t->declaredSeen++;t->declaredInvalid|=invalid;t->declaredBytes=valueNumber;
 }
}
static void outgoingHeaders(struct Trace*t,const char*p,SIZE size){
 t->sentBytes=t->declaredBytes=0;t->declaredSeen=t->declaredInvalid=t->contentEncodingSeen=t->transferEncodingSeen=t->chunkedSeen=t->expectSeen=0;
 SIZE line=0;while(line<size&&p[line]!='\n')line++;
 char b[512];int n=append(b,0,"playfab outgoing request method=");n=append(b,n,size>=5&&p[0]=='P'&&p[1]=='O'&&p[2]=='S'&&p[3]=='T'&&p[4]==' '?"POST":"other");n=append(b,n," headerBlockBytes=");n=unsignedNumber(b,n,size);n=append(b,n," httpVersion=");n=append(b,n,contains(p,line,"HTTP/2")?"2":contains(p,line,"HTTP/1.1")?"1.1":contains(p,line,"HTTP/1.0")?"1.0":"other");b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
 SIZE start=line<size?line+1:line;
 while(start<size){SIZE end=start;while(end<size&&p[end]!='\n')end++;SIZE len=end-start;if(len&&p[start+len-1]=='\r')len--;if(len)headerMetadata(t,p+start,len,"wire");start=end<size?end+1:end;}
}
struct Header {const char*data;struct Header*next;};
// Correct framing from a single validated caller Content-Length on any host.
// This only makes curl agree with the caller; no headers or bodies are replaced.
// The game already
// declares a body length; libcurl must also know it when reading a streamed
// POST. Do not merely remove Transfer-Encoding while retaining chunk bytes.
static void restoreRequestSize(struct Trace*t){
 if(!t||!t->sizeOverrideApplied)return;
 int(*set)(void*,int,...)=fn("curl_easy_setopt");
 int option=t->sizeOverrideApplied==2?30115:30120;long long original=t->sizeOverrideApplied==2?t->originalUploadSize:t->originalPostSize;
 if(!set(t->easy,option,original))t->sizeOverrideApplied=0;
}
static void applyRequestSize(void*e){
 struct Trace*t=trace(e,0);if(!t)return;
 SIZE length=0;int seen=0,invalid=0,explicitTransfer=0;
 for(struct Header*h=t->headers;h;h=h->next){
  const char*p=h->data;if(!p)continue;SIZE colon=0;while(p[colon]&&p[colon]!=':')colon++;
  if(p[colon]!=':')continue;
  if(boundedSame(p,colon,"transfer-encoding")){explicitTransfer=1;continue;}
  if(!boundedSame(p,colon,"content-length"))continue;
  seen++;p+=colon+1;while(*p==' '||*p=='\t')p++;
  SIZE value=0;int digits=0;
  while(*p>='0'&&*p<='9'){
   unsigned digit=*p++-'0';if(value>(0x7fffffffffffffffULL-digit)/10){invalid=1;break;}
   value=value*10+digit;digits++;
  }
  while(*p==' '||*p=='\t')p++;if(!digits||*p)invalid=1;length=value;
 }
 if(seen!=1||invalid||explicitTransfer)return;
 int(*set)(void*,int,...)=fn("curl_easy_setopt");int code=set(e,t->upload?30115:30120,(long long)length);
 if(!code)t->sizeOverrideApplied=t->upload?2:1;
 if(!t->apiSelected)return;
 char b[512];int n=append(b,0,"playfab known streamed body bytes=");n=unsignedNumber(b,n,length);n=append(b,n," result=");n=number(b,n,code);b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
}
static int contentTypeHeader(const char*s){
 const char*k="content-type:";if(!s)return 0;while(*k){char c=*s++;if(c>='A'&&c<='Z')c+=32;if(c!=*k++)return 0;}return 1;
}
static void inspectHeaders(struct Trace*t){
 t->originalCTCount=t->originalCTKind=0;
 for(struct Header*h=t->headers;h;h=h->next)if(contentTypeHeader(h->data)){
  t->originalCTCount++;const char*p=h->data+13;while(*p==' '||*p=='\t')p++;
  SIZE n=0;while(p[n])n++;t->originalCTKind=contains(p,n,"application/json")?1:contains(p,n,"application/octet-stream")?2:contains(p,n,"application/x-www-form-urlencoded")?3:*p?4:5;
 }
}
static int diagnosticDebug(void*e,int kind,char*p,SIZE n,void*data){
 struct Trace*t=data;if(!t||t->easy!=e)return 0;
 if(t->apiSelected&&kind==2)outgoingHeaders(t,p,n);
 if(t->apiSelected&&kind==4){t->sentBytes+=n;capture(t->outgoing,&t->outlen,&t->outoverflow,p,n);}
 if(t->apiSelected&&kind==1){
  if(contains(p,n,"content-type:")){if(contains(p,n,"application/json"))t->contenttype=1;else if(contains(p,n,"text/html"))t->contenttype=2;else if(contains(p,n,"xml"))t->contenttype=3;}
  if(contains(p,n,"content-encoding:")){if(contains(p,n,"gzip"))t->encoding=1;else if(contains(p,n,"br"))t->encoding=2;else if(contains(p,n,"deflate"))t->encoding=3;else if(contains(p,n,"zstd"))t->encoding=4;}
 }
 // Decoded incoming content is captured by diagnosticWrite, not the raw
 // compressed/debug stream. Never copy headers, TLS records, or debug text.
 if(t->verbose&&t->debug)t->debug(e,kind,p,n,t->debugdata);
 return 0;
}
static SIZE diagnosticWrite(char*p,SIZE size,SIZE count,void*data){
 struct Trace*t=data;SIZE n=size*count;
 // This wrapper is installed only when the caller supplied a write callback.
 if(!t||!t->write)return 0;
 if(t->apiSelected&&(!size||n/size==count))capture(t->incoming,&t->inlen,&t->inoverflow,p,n);
 return t->write(p,size,count,t->writedata);
}
static void configureTrace(struct Trace*t){
 int(*set)(void*,int,...)=fn("curl_easy_setopt");
 if(t->apiSelected&&dcLogging()){
  inspectHeaders(t);
  set(t->easy,20094,diagnosticDebug);set(t->easy,10095,t);set(t->easy,41,(void*)1);
  if(t->write){set(t->easy,20011,diagnosticWrite);set(t->easy,10001,t);}
 }else{
  set(t->easy,20094,t->debug);set(t->easy,10095,t->debugdata);set(t->easy,41,(void*)(SIZE)t->verbose);
  set(t->easy,20011,t->write);set(t->easy,10001,t->writedata);
  set(t->easy,10023,t->headers);
 }
}
static const char* findText(const char*b,const char*key){
 for(const char*p=b;*p;p++){const char*q=p,*k=key;while(*q&&*k){char a=*q++,c=*k++;if(a>='A'&&a<='Z')a+=32;if(c>='A'&&c<='Z')c+=32;if(a!=c)break;if(!*k)return p;}}return 0;
}
static int publicWord(const char*p,int len){
 // Only short ordinary words may pass. Numbers, URLs, mixed-case strings,
 // uppercase codes, long strings and credential-like punctuation are removed.
 if(len<1||len>19)return 0;
 if(len==4&&p[0]=='H'&&p[1]=='T'&&p[2]=='T'&&p[3]=='P')return 1;
 for(int i=0;i<len;i++){char c=p[i];if(c>='a'&&c<='z')continue;if(i==0&&c>='A'&&c<='Z')continue;if(c=='-'&&i>0&&i+1<len)continue;return 0;}return 1;
}
static void publicServerText(struct Trace*t){
 if(t->inoverflow)return;const char*body=t->incoming;while(*body==' '||*body=='\r'||*body=='\n'||*body=='\t')body++;if(*body!='<')return;
 const char*p=findText(t->incoming,"<body");if(!p)return;while(*p&&*p!='>')p++;if(*p)p++;
 char b[512];int n=append(b,0,"playfab redacted-server-error:");
 while(*p&&n<390){
  if(*p=='<'){
   if(findText(p,"</body")==p)break;
   if(findText(p,"<script")==p||findText(p,"<style")==p){const char*end=findText(p,findText(p,"<script")==p?"</script>":"</style>");if(!end)break;p=end;}
   while(*p&&*p!='>')p++;if(*p)p++;continue;
  }
  if(*p=='&'){while(*p&&*p!=';'&&*p!='<'&&*p!=' ')p++;if(*p==';')p++;continue;}
  if(*p==' '||*p=='\r'||*p=='\n'||*p=='\t'){p++;continue;}
  const char*start=p;int len=0;while(*p&&*p!='<'&&*p!='&'&&*p!=' '&&*p!='\r'&&*p!='\n'&&*p!='\t'){p++;len++;}
  int trimmed=len;while(trimmed>0&&(start[trimmed-1]=='.'||start[trimmed-1]==','||start[trimmed-1]==':'||start[trimmed-1]==';'||start[trimmed-1]=='!'))trimmed--;
  n=append(b,n," ");if(publicWord(start,trimmed)){for(int i=0;i<trimmed&&n<430;i++)b[n++]=start[i];}else n=append(b,n,"[redacted]");
 }
 b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
}
// Locate an unescaped key at JSON root level. Nested profile or token data
// cannot be mistaken for a permitted diagnostic field.
static const char* field(const char*b,const char*key){
 int depth=0,string=0,escaped=0;
 for(const char*p=b;*p;p++){
  if(string){if(escaped){escaped=0;continue;}if(*p=='\\'){escaped=1;continue;}if(*p=='"')string=0;continue;}
  if(*p=='{'||*p=='['){depth++;continue;}if(*p=='}'||*p==']'){depth--;continue;}
  if(*p=='"'){
   if(depth==1){const char*q=p+1,*k=key;while(*k&&*q==*k){q++;k++;}
    if(!*k&&*q=='"'){q++;while(*q==' '||*q=='\t'||*q=='\r'||*q=='\n')q++;if(*q==':'){q++;while(*q==' '||*q=='\t'||*q=='\r'||*q=='\n')q++;return q;}}
   }string=1;
  }
 }return 0;
}
static const char* boolean(const char*p){
 if(p&&p[0]=='t'&&p[1]=='r'&&p[2]=='u'&&p[3]=='e'&&(p[4]==','||p[4]=='}'||p[4]==' '||p[4]=='\r'||p[4]=='\n'||p[4]=='\t'))return "true";
 if(p&&p[0]=='f'&&p[1]=='a'&&p[2]=='l'&&p[3]=='s'&&p[4]=='e'&&(p[5]==','||p[5]=='}'||p[5]==' '||p[5]=='\r'||p[5]=='\n'||p[5]=='\t'))return "false";
 return "unavailable";
}
static int jsonNumber(const char*p){
 if(!p||*p<'0'||*p>'9')return -1;int value=0,n=0;
 while(*p>='0'&&*p<='9'){if(++n>7)return -1;value=value*10+*p++-'0';}
 if(*p!=','&&*p!='}'&&*p!=' '&&*p!='\r'&&*p!='\n')return -1;return value;
}
static int identifier(const char*p,char*out){
 if(!p||*p++!='"')return 0;int n=0;
 while(*p&&*p!='"'&&n<100){char c=*p++;if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'))return 0;out[n++]=c;}
 if(*p!='"'||!n)return 0;out[n]=0;return 1;
}
static int hexlength(const char*p){
 if(!p||*p++!='"')return -1;int n=0;
 while(*p&&*p!='"'&&n<=8192){char c=*p++;if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')||(c>='A'&&c<='F')))return -1;n++;}
 return *p=='"'&&!(n&1)?n:-1;
}
static long long chunkedPayload(struct Trace*t){
 if(t->outoverflow)return -1;SIZE pos=0,total=0;
 while(pos<t->outlen){SIZE chunk=0;int digits=0;
  while(pos<t->outlen){unsigned char c=t->outgoing[pos];int value=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;if(value<0)break;if(++digits>8)return -1;chunk=chunk*16+value;pos++;}
  if(!digits||pos+2>t->outlen||t->outgoing[pos]!='\r'||t->outgoing[pos+1]!='\n')return -1;pos+=2;if(!chunk)return total;
  if(chunk>t->outlen-pos||pos+chunk+2>t->outlen)return -1;total+=chunk;pos+=chunk;if(t->outgoing[pos]!='\r'||t->outgoing[pos+1]!='\n')return -1;pos+=2;
 }return -1;
}
static void requestFraming(struct Trace*t){
 for(struct Header*h=t->headers;h;h=h->next){SIZE len=0;while(h->data&&h->data[len])len++;if(h->data)headerMetadata(t,h->data,len,"source");}
 char b[512];int n=append(b,0,"playfab framing contentEncodingPresent=");n=number(b,n,t->contentEncodingSeen);n=append(b,n," transferEncodingPresent=");n=number(b,n,t->transferEncodingSeen);n=append(b,n," chunked=");n=number(b,n,t->chunkedSeen);n=append(b,n," expectPresent=");n=number(b,n,t->expectSeen);n=append(b,n," contentLengthHeaders=");n=number(b,n,t->declaredSeen);n=append(b,n," declaredLengthValid=");n=number(b,n,t->declaredSeen>0&&!t->declaredInvalid);n=append(b,n," declaredBodyBytes=");n=unsignedNumber(b,n,t->declaredBytes);n=append(b,n," outgoingWireBodyBytes=");n=unsignedNumber(b,n,t->sentBytes);
 long long payload=t->chunkedSeen?chunkedPayload(t):(long long)t->sentBytes;n=append(b,n," payloadBodyBytes=");if(payload<0)n=append(b,n,"unavailable");else n=unsignedNumber(b,n,payload);
 n=append(b,n," declaredMatchesPayload=");n=append(b,n,!t->declaredSeen||t->declaredInvalid||payload<0?"unavailable":t->declaredBytes==(SIZE)payload?"true":"false");b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
}
static void traceResult(void*easy,long status){
 struct Trace*t=trace(easy,0);if(!t||!t->apiSelected)return;
 requestFraming(t);
 char b[512],name[101];int n=append(b,0,"playfab route=");n=append(b,n,t->operation);n=append(b,n," http=");n=number(b,n,status);
 if(t->selected){
 n=append(b,n," createAccount=");n=append(b,n,t->outoverflow?"unavailable":boolean(field(t->outgoing,"CreateAccount")));
 n=append(b,n," serviceSpecific=");n=append(b,n,t->outoverflow?"unavailable":boolean(field(t->outgoing,"TicketIsServiceSpecific")));
 n=append(b,n," ticketHexLength=");n=number(b,n,t->outoverflow?-1:hexlength(field(t->outgoing,"SteamTicket")));
 const char*title=field(t->outgoing,"TitleId");n=append(b,n," titleMatches=");
 n=append(b,n,!t->outoverflow&&title&&title[0]=='"'&&title[1]=='8'&&title[2]=='3'&&title[3]=='1'&&title[4]=='5'&&title[5]=='6'&&title[6]=='"'?"true":"unavailable");
 }
 // Successful authentication responses can contain credentials. Nothing from
 // them is parsed or logged, beyond the already-known HTTP status.
 if(status>=400&&!t->inoverflow){int code=jsonNumber(field(t->incoming,"errorCode"));if(code>=0){n=append(b,n," errorCode=");n=number(b,n,code);}if(identifier(field(t->incoming,"error"),name)){n=append(b,n," error=");n=append(b,n,name);}}
 n=append(b,n," decodedBodyBytes=");n=number(b,n,t->inlen);b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
 if(status>=400){
  n=append(b,0,"playfab response-format contentType=");n=number(b,n,t->contenttype);n=append(b,n," encoding=");n=number(b,n,t->encoding);
  const unsigned char*p=(const unsigned char*)t->incoming;while(*p==' '||*p=='\r'||*p=='\n'||*p=='\t')p++;
  n=append(b,n," bodyKind=");n=append(b,n,*p=='{'||*p=='['?"json":*p=='<'?"markup":p[0]==0x1f&&p[1]==0x8b?"gzip":*p?"other":"empty");
  static const char*known[]={"Bad Request","Invalid Header","Invalid Hostname","Invalid Verb","Request Header Or Cookie Too Large","Access Denied","InvalidSteamTicket","AccountNotFound","SteamNotEnabledForTitle","TicketIsServiceSpecific","Invalid request","Content-Length","Content-Type","unsupported media type","application/json","application/octet-stream"};
  for(int i=0;i<16;i++)if(contains(t->incoming,t->inlen,known[i])){n=append(b,n," hint=");n=append(b,n,known[i]);}
  b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
  publicServerText(t);
 }
 n=append(b,0,"playfab original-header observation count=");n=number(b,n,t->originalCTCount);n=append(b,n," originalKind=");n=number(b,n,t->originalCTKind);b[n++]='\r';b[n++]='\n';b[n]=0;logline(b);
 erase(t->incoming,sizeof(t->incoming));erase(t->outgoing,sizeof(t->outgoing));t->inlen=t->outlen=0;t->inoverflow=t->outoverflow=0;
}
