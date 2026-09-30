#import <Cocoa/Cocoa.h>

@interface Launcher : NSObject <NSApplicationDelegate, NSWindowDelegate>
@property NSWindow *window;
@property NSTask *task;
@property NSTextField *label;
@property BOOL working;
@property BOOL cancelling;
@property BOOL signingOut;
@end

@implementation Launcher
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [NSApp activateIgnoringOtherApps:YES];
    NSString *command = [NSBundle.mainBundle objectForInfoDictionaryKey:@"DCCommand"];
    if (![@[@"launch", @"sign-out"] containsObject:command]) { [NSApp terminate:nil]; return; }
    BOOL signingOut = [command isEqualToString:@"sign-out"];
    self.signingOut = signingOut; self.working = YES;
    NSMenu *menu = [NSMenu new]; NSMenuItem *item = [NSMenuItem new]; [menu addItem:item];
    item.submenu = [NSMenu new]; [item.submenu addItemWithTitle:@"Quit" action:@selector(terminate:) keyEquivalent:@"q"]; NSApp.mainMenu = menu;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,430,signingOut ? 130 : 174) styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
    self.window.delegate = self;
    self.window.title = signingOut ? @"Signing out" : @"Minecraft Dungeons II";
    NSTextField *label = [NSTextField wrappingLabelWithString:signingOut ? @"Removing your saved Microsoft sign-in…" : @"Checking Xbox sign-in…\nIf a code window appears, finish signing in and leave it open."];
    label.frame = NSMakeRect(24,signingOut ? 56 : 100,382,52); self.label = label; [self.window.contentView addSubview:label];
    NSProgressIndicator *bar = [[NSProgressIndicator alloc] initWithFrame:NSMakeRect(24,signingOut ? 24 : 68,382,16)];
    bar.indeterminate = YES; [bar startAnimation:nil]; [self.window.contentView addSubview:bar];
    if (!signingOut) {
        NSButton *cancel = [NSButton buttonWithTitle:@"Cancel Launch" target:self action:@selector(cancel:)];
        cancel.frame = NSMakeRect(266,20,140,28); cancel.keyEquivalent = @"\e"; [self.window.contentView addSubview:cancel];
    }
    [self.window center]; [self.window makeKeyAndOrderFront:nil];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
        NSString *home = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/DungeonsCrossOver"];
        NSTask *task = [NSTask new]; task.executableURL = [NSURL fileURLWithPath:[home stringByAppendingPathComponent:@"python/bin/python"]];
        NSData *settingsData = [NSData dataWithContentsOfFile:[home stringByAppendingPathComponent:@"settings.json"]];
        NSDictionary *settings = settingsData ? [NSJSONSerialization JSONObjectWithData:settingsData options:0 error:nil] : nil;
        NSString *bottle = [settings[@"bottle"] isKindOfClass:NSString.class] ? settings[@"bottle"] : @"Steam";
        task.arguments = @[@"-I", @"-B", [home stringByAppendingPathComponent:@"runtime/bridge.py"], command, @"--bottle", bottle];
        NSMutableDictionary *environment = [NSProcessInfo.processInfo.environment mutableCopy];
        environment[@"PYTHONDONTWRITEBYTECODE"] = @"1"; task.environment = environment;
        NSPipe *pipe = [NSPipe pipe]; task.standardOutput = pipe; task.standardError = pipe;
        self.task = task; NSError *error; BOOL started = !self.cancelling && [task launchAndReturnError:&error];
        if (started && self.cancelling && task.running) [task terminate];
        if (started) { [pipe.fileHandleForReading readDataToEndOfFile]; [task waitUntilExit]; }
        BOOL ok = started && task.terminationStatus == 0;
        dispatch_async(dispatch_get_main_queue(), ^{
            self.working = NO;
            [self.window close];
            if ((!ok || signingOut) && !self.cancelling) {
                NSAlert *a = [NSAlert new];
                a.messageText = ok ? @"Signed out" : @"Couldn’t finish";
                a.informativeText = ok ? @"Your Microsoft refresh token and local session were removed. The game was left open." : @"Check your connection and try again. If the problem continues, run the installer again. No sign-in details were logged.";
                [a runModal];
            }
            [NSApp terminate:nil];
        });
    });
}
- (void)cancel:(id)sender {
    if (self.signingOut || self.cancelling) return;
    self.cancelling = YES; self.label.stringValue = @"Cancelling launch…";
    if (self.task.running) [self.task terminate];
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if (self.working) { [self cancel:nil]; return NSTerminateCancel; }
    return NSTerminateNow;
}
- (BOOL)windowShouldClose:(NSWindow *)sender {
    if (self.working) { [self cancel:nil]; return NO; }
    [NSApp terminate:nil]; return YES;
}
@end

int main(void) {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication; app.activationPolicy = NSApplicationActivationPolicyRegular;
        Launcher *launcher = [Launcher new]; app.delegate = launcher; [app run];
    }
    return 0;
}
