typedef long long L64;
struct WClass {unsigned size,style;L64(*proc)(H,unsigned,U64,L64);int clsExtra,winExtra;H instance,icon,cursor,background;const char*menu;const char*name;H smallIcon;};
struct Msg {H window;unsigned message;U64 wp;L64 lp;DWORD time;int x,y;DWORD private;};
IMP unsigned short RegisterClassExA(const struct WClass*);
IMP H CreateWindowExA(DWORD,const char*,const char*,DWORD,int,int,int,int,H,H,H,void*);
IMP L64 DefWindowProcA(H,unsigned,U64,L64);
IMP L64 SetWindowLongPtrA(H,int,L64);
IMP L64 GetWindowLongPtrA(H,int);
IMP int DestroyWindow(H);
IMP void PostQuitMessage(int);
IMP int GetMessageA(struct Msg*,H,unsigned,unsigned);
IMP int TranslateMessage(const struct Msg*);
IMP L64 DispatchMessageA(const struct Msg*);
IMP int ShowWindow(H,int);
IMP int SetForegroundWindow(H);
IMP L64 SendMessageA(H,unsigned,U64,L64);
IMP H GetStockObject(int);
IMP int OpenClipboard(H);
IMP int EmptyClipboard(void);
IMP H SetClipboardData(unsigned,H);
IMP int CloseClipboard(void);
IMP H GlobalAlloc(unsigned,U64);
IMP void* GlobalLock(H);
IMP int GlobalUnlock(H);
IMP H GlobalFree(H);
static int copyText(H window,const char*text){
 unsigned n=len(text);H memory=GlobalAlloc(2,(n+1)*2);if(!memory)return 0;
 unsigned short*p=GlobalLock(memory);if(!p){GlobalFree(memory);return 0;}
 for(unsigned i=0;i<=n;i++)p[i]=(unsigned char)text[i];GlobalUnlock(memory);
 if(!OpenClipboard(window)){GlobalFree(memory);return 0;}
 EmptyClipboard();H result=SetClipboardData(13,memory);CloseClipboard();if(!result)GlobalFree(memory);return result!=0;
}
static L64 promptProc(H window,unsigned msg,U64 wp,L64 lp){
 struct Prompt*q=(struct Prompt*)GetWindowLongPtrA(window,-21);
 if(msg==0x111&&q){unsigned id=wp&65535;
  if(id==101||id==103||id==102||id==104){int link=id==101||id==103;int ok=copyText(window,link?q->url:q->code);
   H control=(H)lp;if(control&&id>=103)SendMessageA(control,0xC,0,(L64)(ok?(link?"Link copied":"Code copied"):"Try copying again"));return 0;}
  if(id==105){DestroyWindow(window);return 0;}
 }
 if(msg==2){PostQuitMessage(0);return 0;}
 return DefWindowProcA(window,msg,wp,lp);
}
static void addControl(H window,const char*cls,const char*text,int x,int y,int width,int height,unsigned id,DWORD style){
 H control=CreateWindowExA(0,cls,text,0x50000000|style,x,y,width,height,window,(H)(U64)id,self,0);
 if(control)SendMessageA(control,0x30,(U64)GetStockObject(17),1);
}
static void runPrompt(struct Prompt*q){
 static const char*name="DungeonsRemoteLoginCopyPrompt";
 struct WClass cls={0};cls.size=sizeof(cls);cls.proc=promptProc;cls.instance=self;cls.background=(H)6;cls.name=name;RegisterClassExA(&cls);
 H window=CreateWindowExA(8,name,title,0x00C80000,180,180,620,285,0,0,self,0);
 if(!window){MessageBoxA(0,q->text,title,0x10000|0x40000|0x40);return;}
 SetWindowLongPtrA(window,-21,(L64)q);
 addControl(window,"STATIC","Sign in using your browser or phone:",20,18,570,24,0,0);
 addControl(window,"BUTTON",q->url,20,55,405,34,101,0x10000);
 addControl(window,"BUTTON","Copy link",440,55,145,34,103,0x10000);
 addControl(window,"BUTTON",q->code,20,101,405,34,102,0x10000);
 addControl(window,"BUTTON","Copy code",440,101,145,34,104,0x10000);
 addControl(window,"STATIC","Click the link or code to copy it. Leave this window open while signing in.\nIt closes automatically when the sign-in attempt finishes.",20,150,570,44,0,0);
 addControl(window,"BUTTON","Cancel sign-in",425,202,160,30,105,0x10000);
 ShowWindow(window,5);SetForegroundWindow(window);struct Msg msg;
 while(GetMessageA(&msg,0,0,0)>0){TranslateMessage(&msg);DispatchMessageA(&msg);}
}
