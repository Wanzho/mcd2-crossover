typedef long long L64;
IMP int MessageBoxW(H,const unsigned short*,const unsigned short*,unsigned);
struct WClass {unsigned size,style;L64(*proc)(H,unsigned,U64,L64);int clsExtra,winExtra;H instance,icon,cursor,background;const unsigned short*menu;const unsigned short*name;H smallIcon;};
struct Msg {H window;unsigned message;U64 wp;L64 lp;DWORD time;int x,y;DWORD private;};
IMP unsigned short RegisterClassExW(const struct WClass*);
IMP H CreateWindowExW(DWORD,const unsigned short*,const unsigned short*,DWORD,int,int,int,int,H,H,H,void*);
IMP L64 DefWindowProcW(H,unsigned,U64,L64);
IMP L64 SetWindowLongPtrW(H,int,L64);
IMP L64 GetWindowLongPtrW(H,int);
IMP int DestroyWindow(H);
IMP void PostQuitMessage(int);
IMP int GetMessageW(struct Msg*,H,unsigned,unsigned);
IMP int TranslateMessage(const struct Msg*);
IMP L64 DispatchMessageW(const struct Msg*);
IMP int ShowWindow(H,int);
IMP int SetForegroundWindow(H);
IMP L64 SendMessageW(H,unsigned,U64,L64);
IMP H GetStockObject(int);
IMP int OpenClipboard(H);
IMP int EmptyClipboard(void);
IMP H SetClipboardData(unsigned,H);
IMP int CloseClipboard(void);
IMP H GlobalAlloc(unsigned,U64);
IMP void* GlobalLock(H);
IMP int GlobalUnlock(H);
IMP H GlobalFree(H);
static int copyText(H window,const unsigned short*text){
 unsigned n=0;while(text[n])n++;H memory=GlobalAlloc(2,(n+1)*2);if(!memory)return 0;
 unsigned short*p=GlobalLock(memory);if(!p){GlobalFree(memory);return 0;}
 for(unsigned i=0;i<=n;i++)p[i]=text[i];GlobalUnlock(memory);
 if(!OpenClipboard(window)){GlobalFree(memory);return 0;}
 EmptyClipboard();H result=SetClipboardData(13,memory);CloseClipboard();if(!result)GlobalFree(memory);return result!=0;
}
static L64 promptProc(H window,unsigned msg,U64 wp,L64 lp){
 struct Prompt*q=(struct Prompt*)GetWindowLongPtrW(window,-21);
 if(msg==0x111&&q){unsigned id=wp&65535;
  if(id==101||id==103||id==102||id==104){int link=id==101||id==103;int ok=copyText(window,link?q->wideUrl:q->wideCode);
   H control=(H)lp;if(control&&id>=103)SendMessageW(control,0xC,0,(L64)(ok?(link?q->labels[6]:q->labels[7]):q->labels[8]));return 0;}
  if(id==105){DestroyWindow(window);return 0;}
 }
 if(msg==2){PostQuitMessage(0);return 0;}
 return DefWindowProcW(window,msg,wp,lp);
}
static void addControl(H window,const unsigned short*cls,const unsigned short*text,int x,int y,int width,int height,unsigned id,DWORD style){
 H control=CreateWindowExW(0,cls,text,0x50000000|style,x,y,width,height,window,(H)(U64)id,self,0);
 if(control)SendMessageW(control,0x30,(U64)GetStockObject(17),1);
}
static void runPrompt(struct Prompt*q){
 static const unsigned short*name=W("DungeonsRemoteLoginCopyPrompt");
 struct WClass cls={0};cls.size=sizeof(cls);cls.proc=promptProc;cls.instance=self;cls.background=(H)6;cls.name=name;RegisterClassExW(&cls);
 H window=CreateWindowExW(8,name,q->labels[0],0x00C80000,180,180,720,345,0,0,self,0);
 if(!window){MessageBoxW(0,q->labels[4],q->labels[0],0x10000|0x40000|0x40);return;}
 SetWindowLongPtrW(window,-21,(L64)q);
 addControl(window,W("STATIC"),q->labels[1],20,18,665,34,0,0);
 addControl(window,W("BUTTON"),q->wideUrl,20,62,405,36,101,0x10000);
 addControl(window,W("BUTTON"),q->labels[2],440,62,245,36,103,0x10000);
 addControl(window,W("BUTTON"),q->wideCode,20,110,405,36,102,0x10000);
 addControl(window,W("BUTTON"),q->labels[3],440,110,245,36,104,0x10000);
 addControl(window,W("STATIC"),q->labels[4],20,163,665,90,0,0);
 addControl(window,W("BUTTON"),q->labels[5],440,263,245,32,105,0x10000);
 ShowWindow(window,5);SetForegroundWindow(window);struct Msg msg;
 while(GetMessageW(&msg,0,0,0)>0){TranslateMessage(&msg);DispatchMessageW(&msg);}
}
