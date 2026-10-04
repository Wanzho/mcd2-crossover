// Installer-generated sidecar contains only the per-user data directory.
// It is deliberately outside source control. No account or token is stored here.
IMP DWORD GetEnvironmentVariableA(const char*,char*,DWORD);
IMP DWORD GetModuleFileNameA(H,char*,DWORD);
IMP int ReadFile(H,void*,DWORD,DWORD*,void*);
IMP DWORD GetFileAttributesA(const char*);
IMP void GetSystemTimeAsFileTime(unsigned long long*);
static char dcRoot[2048];
static int dcPathsReady;
static int dcPath(char*out,unsigned cap,const char*leaf){
 if(!dcPathsReady){
  char path[2048]={0};DWORD n=GetModuleFileNameA(self,path,sizeof(path));
  if(!n||n>=sizeof(path))return 0;
  while(n&&path[n-1]!='\\'&&path[n-1]!='/')n--;path[n]=0;
  append(path,sizeof(path),"dungeons-crossover.ini");
  H f=CreateFileA(path,0x80000000,3,0,3,128,0);
  if(f==(H)-1)return 0;DWORD got=0;
  int ok=ReadFile(f,dcRoot,sizeof(dcRoot)-1,&got,0);CloseHandle(f);
  if(!ok||!got||got>=sizeof(dcRoot)-1)return 0;
  while(got&&(dcRoot[got-1]=='\n'||dcRoot[got-1]=='\r'))dcRoot[--got]=0;
  if(got<3||dcRoot[1]!=':'||(dcRoot[2]!='\\'&&dcRoot[2]!='/')){dcRoot[0]=0;return 0;}
  dcPathsReady=1;
 }
 out[0]=0;if(len(dcRoot)+len(leaf)+2>=cap)return 0;
 append(out,cap,dcRoot);append(out,cap,"\\");append(out,cap,leaf);return 1;
}
// The opt-in flag is time limited. Check it on every write, including when the
// Mac app is closed, so diagnostics never become a permanent game setting.
static unsigned long long dcFlagNumber(const char*json,const char*key){
 for(unsigned i=0;json[i];i++){
  unsigned j=0;while(key[j]&&json[i+j]==key[j])j++;if(key[j])continue;
  unsigned k=i+j;while(json[k]==' '||json[k]=='\t')k++;if(json[k++]!=':')return 0;
  while(json[k]==' '||json[k]=='\t')k++;
  unsigned long long n=0;unsigned digits=0;
  while(json[k]>='0'&&json[k]<='9'){if(++digits>12)return 0;n=n*10+(json[k++]-'0');}
  if(!digits)return 0;
  if(json[k]=='.'){k++;if(json[k]<'0'||json[k]>'9')return 0;while(json[k]>='0'&&json[k]<='9')k++;}
  while(json[k]==' '||json[k]=='\t')k++;
  return json[k]==','||json[k]=='}'?n:0;
 }
 return 0;
}
static int dcLogging(void){
 char p[2048]={0},flag[256]={0};if(!dcPath(p,sizeof(p),"logging.enabled"))return 0;
 H f=CreateFileA(p,0x80000000,3,0,3,128,0);if(f==(H)-1)return 0;
 DWORD got=0;int ok=ReadFile(f,flag,sizeof(flag)-1,&got,0);CloseHandle(f);
 if(!ok||!got||got>=sizeof(flag)-1||flag[0]!='{')return 0;
 unsigned long long started=dcFlagNumber(flag,"\"started\""),expires=dcFlagNumber(flag,"\"expires\""),ticks;
 if(dcFlagNumber(flag,"\"version\"")!=1||expires<=started||expires-started>3601)return 0;
 GetSystemTimeAsFileTime(&ticks);if(ticks<116444736000000000ULL)return 0;
 unsigned long long now=(ticks-116444736000000000ULL)/10000000;
 return started<=now+5&&expires>now;
}
