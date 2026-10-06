// Host test shim: runs the actual PE input parser without Wine or a game.
#import <Foundation/Foundation.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#define wide promptWide
#define __declspec(x)
#include "../src/signin-ui.c"

static int useWindow;
static int eventIndex, clipboardFail;
static L64 windowData;
static H clipboardMemory;
static NSString *windowTitle;
static NSMutableArray *controls, *updates, *clipboardCopies;
static NSString *utf16(const unsigned short *text) {
    NSUInteger length = 0; while(text[length]) length++;
    return [[NSString alloc] initWithCharacters:text length:length];
}
static void reportPrompt(void) {
    NSMutableArray *values = [NSMutableArray new];
    for (unsigned i=0;i<9;i++) [values addObject:utf16(prompt.labels[i])];
    NSDictionary *report = @{ @"url": utf16(prompt.wideUrl), @"code": utf16(prompt.wideCode),
        @"labels": values, @"window_title": windowTitle ?: [NSNull null],
        @"controls": controls ?: @[], @"updates": updates ?: @[],
        @"clipboard": clipboardCopies ?: @[] };
    NSData *data = [NSJSONSerialization dataWithJSONObject:report options:0 error:nil];
    fwrite(data.bytes,1,data.length,stdout);
}
H GetModuleValue = (H)1;
H GetModuleHandleA(const char *name) { return GetModuleValue; }
H GetStdHandle(DWORD id) { return (H)stdin; }
int ReadFile(H handle,void *out,DWORD size,DWORD *got,void *unused) {
    *got = fread(out,1,size,(FILE*)handle); return *got > 0;
}
int MultiByteToWideChar(unsigned cp,DWORD flags,const char *bytes,int size,unsigned short *out,int capacity) {
    assert(cp == 65001 && flags == 8 && size == -1);
    NSString *value = [[NSString alloc] initWithBytes:bytes length:strlen(bytes) encoding:NSUTF8StringEncoding];
    if (!value || value.length+1 > capacity) return 0;
    [value getCharacters:out range:NSMakeRange(0,value.length)]; out[value.length] = 0;
    return (int)value.length+1;
}
H CreateThread(void*a,U64 b,DWORD(*c)(void*),void*d,DWORD e,DWORD*f) { return 0; }
int CloseHandle(H h) { return 1; }
void Sleep(DWORD n) {}
H FindWindowW(const unsigned short*a,const unsigned short*b) { return 0; }
int PostMessageW(H a,unsigned b,U64 c,long long d) { return 1; }
void ExitProcess(unsigned code) { if(code != 2) reportPrompt(); free(clipboardMemory); exit(code); }
unsigned short RegisterClassExW(const struct WClass *a) { return 1; }
H CreateWindowExW(DWORD a,const unsigned short*b,const unsigned short*c,DWORD d,int e,int f,int g,int h,H i,H j,H k,void*l) {
    if(!useWindow) return 0;
    if(!i) {
        windowTitle = utf16(c); controls = [NSMutableArray new];
        updates = [NSMutableArray new]; clipboardCopies = [NSMutableArray new]; return (H)1;
    }
    [controls addObject:@{ @"class": utf16(b), @"text": utf16(c), @"id": @((U64)j),
        @"x": @(e), @"y": @(f), @"width": @(g), @"height": @(h) }];
    return (H)(U64)(controls.count+1);
}
L64 DefWindowProcW(H a,unsigned b,U64 c,L64 d) { return 0; }
L64 SetWindowLongPtrW(H a,int b,L64 c) { assert(b == -21); windowData = c; return 0; }
L64 GetWindowLongPtrW(H a,int b) { assert(b == -21); return windowData; }
int DestroyWindow(H h) { return 1; }
void PostQuitMessage(int i) {}
int GetMessageW(struct Msg*a,H b,unsigned c,unsigned d) {
    if(eventIndex == 3) return 0;
    clipboardFail = eventIndex == 2;
    a->window = (H)1; a->message = 0x111;
    a->wp = eventIndex == 1 ? 104 : 103; a->lp = eventIndex == 1 ? 6 : 4;
    eventIndex++; return 1;
}
int TranslateMessage(const struct Msg*a) { return 0; }
L64 DispatchMessageW(const struct Msg*a) { return promptProc(a->window,a->message,a->wp,a->lp); }
int ShowWindow(H a,int b) { return 1; }
int SetForegroundWindow(H h) { return 1; }
L64 SendMessageW(H a,unsigned b,U64 c,L64 d) {
    if(b == 0xC) {
        NSDictionary *control = controls[(U64)a-2];
        [updates addObject:@{ @"id": control[@"id"], @"text": utf16((const unsigned short*)d) }];
    }
    return 0;
}
H GetStockObject(int i) { return 0; }
int OpenClipboard(H h) { return !clipboardFail; }
int EmptyClipboard(void) { free(clipboardMemory); clipboardMemory = 0; return 1; }
H SetClipboardData(unsigned i,H h) {
    assert(i == 13); clipboardMemory = h; [clipboardCopies addObject:utf16(h)]; return h;
}
int CloseClipboard(void) { return 1; }
H GlobalAlloc(unsigned a,U64 b) { assert(a == 2); return malloc(b); }
void* GlobalLock(H h) { return h; }
int GlobalUnlock(H h) { return 1; }
H GlobalFree(H h) { free(h); return 0; }
int MessageBoxW(H a,const unsigned short*b,const unsigned short*c,unsigned d) {
    assert([utf16(b) isEqualToString:utf16(prompt.labels[4])]);
    assert([utf16(c) isEqualToString:utf16(prompt.labels[0])]); return 0;
}
int main(int argc,char **argv) { @autoreleasepool { useWindow = argc > 1; mainCRTStartup(); } }
