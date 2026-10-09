// AppKit regression tests: native validation and click-triggered error UI, synthetic copies.
// No installation, launch, account access, or updater request is performed.
#define main mcd2_production_main
#import "../packaging/installer.m"
#undef main
@implementation CrossoverUpdater
+ (instancetype)shared { static CrossoverUpdater *u; if (!u) u=[self new]; return u; }
- (void)startWithBusyCheck:(BOOL (^)(void))check {}
- (void)addItemsToMenu:(NSMenu *)menu {}
- (BOOL)allowsNewOperation { return YES; }
- (BOOL)mustWaitBeforeQuitting { return NO; }
@end

@interface TestApp : MCD2App
@end
@implementation TestApp
- (void)recordEvent:(NSString *)step outcome:(NSString *)outcome {}
- (void)refreshAccount {}
@end
static void check(BOOL ok,const char *message) { if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);} printf("PASS: %s\n",message); }
int main(int argc,const char **argv) { @autoreleasepool {
 [NSApplication sharedApplication];
 resources=[NSString stringWithUTF8String:argv[1]];
 NSString *fixture=[NSString stringWithUTF8String:argv[2]];
 support=[fixture stringByAppendingPathComponent:@"support"];
 MCD2ConfigureLocalization(resources,[support stringByAppendingPathComponent:@"ui-language"]);
 TestApp *a=[TestApp new]; a.setupMode=YES;
 a.status=[NSTextField labelWithString:@""];a.primary=[MCD2SetupButton new];
 __weak TestApp *weakApp=a;
 ((MCD2SetupButton *)a.primary).blockedAttempt=^{ [weakApp explainBlockedSetup]; };a.license=[NSButton new];
 a.bottles=[NSPopUpButton new];[a.bottles addItemWithTitle:@"Test"];
 a.stores=[NSPopUpButton new];[a.stores addItemsWithTitles:@[@"Steam",@"Launcher"]];
 a.gameCopy=[a inspectCopy:[fixture stringByAppendingPathComponent:@"game"] store:@"steam"];
 check(a.gameCopy!=nil,"valid Steam copy still accepted");
 [a licenseChanged:nil];check(!a.primary.enabled && ![a.status.stringValue containsString:@"license"],"no error before setup attempted");
 [a.primary performClick:nil];check([a.status.stringValue containsString:@"license"],"disabled setup click explains missing license");
 a.license.state=NSControlStateValueOn;[a licenseChanged:nil];check(a.primary.enabled,"valid setup enabled");
 a.gameCopy=[a inspectCopy:[fixture stringByAppendingPathComponent:@"absent"] store:@"steam"];
 [a licenseChanged:nil];check(!a.primary.enabled && [a.status.stringValue containsString:@"no longer exists"],"actual validator error displayed");
 NSString *original=resources;resources=[fixture stringByAppendingPathComponent:@"missing-runtime"];
 a.gameCopy=[a inspectCopy:[fixture stringByAppendingPathComponent:@"game"] store:@"steam"];
 check(a.gameCopy!=nil,"native validation works with no Python runtime at all");
 a.setupAttempted=NO;
 a.runtimeError=@"Runtime preparation failed: read-only filesystem";[a licenseChanged:nil];
 check(![a.status.stringValue containsString:@"read-only"],"runtime error hidden before setup attempted");
 [a.primary mouseDown:[NSEvent mouseEventWithType:NSEventTypeLeftMouseDown location:NSZeroPoint modifierFlags:0 timestamp:0 windowNumber:0 context:nil eventNumber:0 clickCount:1 pressure:1]];
 check(!a.primary.enabled && [a.status.stringValue containsString:@"read-only"],"runtime preparation error is visible");
 a.working=YES;a.setupAttempted=NO;a.status.stringValue=@"Setting up…";
 [a.primary mouseDown:[NSEvent mouseEventWithType:NSEventTypeLeftMouseDown location:NSZeroPoint modifierFlags:0 timestamp:0 windowNumber:0 context:nil eventNumber:0 clickCount:1 pressure:1]];check(!a.setupAttempted && [a.status.stringValue isEqual:@"Setting up…"],"click during setup does not replace progress or start another task");
 a.working=NO;a.runtimeError=nil;resources=original;a.operation=@"setup";[a finished:1 output:@"Synthetic installation failure"];
 check([a.status.stringValue containsString:@"Synthetic installation failure"],"setup failure not replaced by readiness text");
 } return 0; }
