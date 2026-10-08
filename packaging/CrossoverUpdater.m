#import "CrossoverUpdater.h"
#import <Sparkle/Sparkle.h>
// CrossOver's proc_pidpath can be explorer.exe for every Windows process.
// ps comm reads the Windows process name without exposing its arguments.
static BOOL isGameOrSignInName(NSString *command) {
    NSString *name = [[[command stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet]
        stringByReplacingOccurrencesOfString:@"\\" withString:@"/"] lastPathComponent].lowercaseString;
    return [@[@"dungeons-win64-shipping.exe", @"dungeons-wingdk-shipping.exe", @"dungeons.exe",
              @"mcd1-auth-broker", @"mcd1-native-auth-relay"] containsObject:name];
}
static BOOL gameOrSignInRunning(void) {
    NSTask *task = [NSTask new];
    task.executableURL = [NSURL fileURLWithPath:@"/bin/ps"];
    task.arguments = @[@"-axo", @"comm="];
    NSPipe *output = [NSPipe pipe];
    task.standardOutput = output;
    task.standardError = [NSFileHandle fileHandleWithNullDevice];
    if (![task launchAndReturnError:nil]) return YES;
    NSData *data = [output.fileHandleForReading readDataToEndOfFile];
    [task waitUntilExit];
    if (task.terminationStatus != 0 || data.length == 0 || data.length > 2000000) return YES;
    NSString *names = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    if (!names) return YES;
    for (NSString *name in [names componentsSeparatedByString:@"\n"])
        if (isGameOrSignInName(name)) return YES;
    return NO;
}

@interface CrossoverUpdater () <SPUUpdaterDelegate, NSMenuItemValidation>
@property SPUStandardUpdaterController *controller;
@property(copy) BOOL (^busyCheck)(void);
@property(copy) void (^pendingInstall)(void);
@property NSTimer *installWait;
@end

@implementation CrossoverUpdater
+ (instancetype)shared {
    static CrossoverUpdater *instance;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ instance = [self new]; });
    return instance;
}
- (void)startWithBusyCheck:(BOOL (^)(void))busyCheck {
    self.busyCheck = busyCheck;
    if (self.controller) return;
    self.controller = [[SPUStandardUpdaterController alloc] initWithStartingUpdater:NO
        updaterDelegate:self userDriverDelegate:nil];
    [self.controller startUpdater];
}
- (BOOL)busy { return (self.busyCheck && self.busyCheck()) || gameOrSignInRunning(); }
- (void)addItemsToMenu:(NSMenu *)menu {
    NSMenuItem *check = [menu addItemWithTitle:NSLocalizedString(@"Check for Updates…", nil)
        action:@selector(checkForUpdates:) keyEquivalent:@""];
    check.target = self;
    NSMenuItem *automatic = [menu addItemWithTitle:NSLocalizedString(@"Automatically Install Updates", nil)
        action:@selector(toggleAutomatic:) keyEquivalent:@""];
    automatic.target = self;
}
- (void)checkForUpdates:(id)sender { [self.controller checkForUpdates:sender]; }
- (void)toggleAutomatic:(id)sender {
    SPUUpdater *updater = self.controller.updater;
    BOOL enable = !(updater.automaticallyChecksForUpdates && updater.automaticallyDownloadsUpdates);
    updater.automaticallyChecksForUpdates = enable;
    updater.automaticallyDownloadsUpdates = enable;
}
- (BOOL)validateMenuItem:(NSMenuItem *)item {
    if (item.action == @selector(checkForUpdates:)) return self.controller.updater.canCheckForUpdates;
    if (item.action == @selector(toggleAutomatic:)) {
        item.state = self.controller.updater.automaticallyChecksForUpdates &&
            self.controller.updater.automaticallyDownloadsUpdates ? NSControlStateValueOn : NSControlStateValueOff;
    }
    return YES;
}
- (BOOL)allowsNewOperation {
    if (!self.controller.updater.sessionInProgress && !self.pendingInstall) return YES;
    NSAlert *alert = [NSAlert new];
    alert.messageText = NSLocalizedString(@"An update is in progress", nil);
    alert.informativeText = NSLocalizedString(@"Finish or cancel the update before starting the game or changing its setup.", nil);
    [alert runModal];
    return NO;
}
- (BOOL)mustWaitBeforeQuitting {
    return (self.pendingInstall || self.controller.updater.sessionInProgress) && [self busy];
}
- (BOOL)updater:(SPUUpdater *)updater mayPerformUpdateCheck:(SPUUpdateCheck)check error:(NSError **)error {
    if (![self busy]) return YES;
    if (error) *error = [NSError errorWithDomain:@"CrossoverUpdater" code:1 userInfo:@{
        NSLocalizedDescriptionKey:NSLocalizedString(@"Quit Dungeons and finish sign-in or setup before updating.", nil)}];
    return NO;
}
- (BOOL)updater:(SPUUpdater *)updater shouldPostponeRelaunchForUpdate:(SUAppcastItem *)item
    untilInvokingBlock:(void (^)(void))installHandler {
    if (![self busy]) return NO;
    self.pendingInstall = installHandler;
    __weak CrossoverUpdater *weakSelf = self;
    self.installWait = [NSTimer scheduledTimerWithTimeInterval:15 repeats:YES block:^(NSTimer *timer) {
        CrossoverUpdater *owner = weakSelf;
        if (!owner || !owner.pendingInstall) { [timer invalidate]; return; }
        if ([owner busy]) return;
        void (^finish)(void) = owner.pendingInstall;
        owner.pendingInstall = nil;
        [timer invalidate]; owner.installWait = nil;
        finish();
    }];
    self.installWait.tolerance = 5;
    return YES;
}
@end
