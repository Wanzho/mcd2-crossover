// Installer-generated sidecar contains only the per-user data directory.
// It is deliberately outside source control. No account or token is stored here.
IMP DWORD GetEnvironmentVariableA(const char*,char*,DWORD);
IMP DWORD GetModuleFileNameA(H,char*,DWORD);
IMP int ReadFile(H,void*,DWORD,DWORD*,void*);
IMP DWORD GetFileAttributesA(const char*);
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
static int dcLogging(void){char p[2048]={0};return dcPath(p,sizeof(p),"logging.enabled")&&GetFileAttributesA(p)!=0xffffffffUL;}
