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
 TestApp *a=[TestApp new]; a.setupMode=YES; a.crossoverApp=MCD2FindCrossOver(support);
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
 [a licenseChanged:nil];check(!a.primary.enabled && [a.status.stringValue containsString:@"1202"] && [a.localErrorDetail containsString:@"no longer exists"],"actual validator error displayed");
 NSString *original=resources;resources=[fixture stringByAppendingPathComponent:@"missing-runtime"];
 a.gameCopy=[a inspectCopy:[fixture stringByAppendingPathComponent:@"game"] store:@"steam"];
 check(a.gameCopy!=nil,"native validation works with no Python runtime at all");
 a.setupAttempted=NO;
 a.runtimeError=@"Runtime preparation failed: read-only filesystem";[a licenseChanged:nil];
 check(![a.localErrorDetail containsString:@"read-only"],"runtime error hidden before setup attempted");
 [a.primary mouseDown:[NSEvent mouseEventWithType:NSEventTypeLeftMouseDown location:NSZeroPoint modifierFlags:0 timestamp:0 windowNumber:0 context:nil eventNumber:0 clickCount:1 pressure:1]];
 check(!a.primary.enabled && [a.localErrorDetail containsString:@"read-only"],"runtime preparation error is visible");
 a.working=YES;a.setupAttempted=NO;a.status.stringValue=@"Setting up…";
 [a.primary mouseDown:[NSEvent mouseEventWithType:NSEventTypeLeftMouseDown location:NSZeroPoint modifierFlags:0 timestamp:0 windowNumber:0 context:nil eventNumber:0 clickCount:1 pressure:1]];check(!a.setupAttempted && [a.status.stringValue isEqual:@"Setting up…"],"click during setup does not replace progress or start another task");
 NSString *custom=[fixture stringByAppendingPathComponent:@"Other Apps/crossover renamed.app"];
 NSString *bin=[custom stringByAppendingPathComponent:@"Contents/SharedSupport/CrossOver/bin"];
 [NSFileManager.defaultManager createDirectoryAtPath:bin withIntermediateDirectories:YES attributes:nil error:nil];
 [@{@"CFBundleIdentifier":@"com.codeweavers.CrossOver"} writeToFile:[custom stringByAppendingPathComponent:@"Contents/Info.plist"] atomically:YES];
 NSString *winePath=[bin stringByAppendingPathComponent:@"wine"];
 [@"synthetic, never executed" writeToFile:winePath atomically:YES encoding:NSUTF8StringEncoding error:nil];
 [NSFileManager.defaultManager setAttributes:@{NSFilePosixPermissions:@0755} ofItemAtPath:winePath error:nil];
 check(MCD2CrossOverError(custom)==nil,"native picker accepts renamed CrossOver outside Applications");
 [NSFileManager.defaultManager createDirectoryAtPath:support withIntermediateDirectories:YES attributes:nil error:nil];
 [[NSJSONSerialization dataWithJSONObject:@{@"path":custom} options:0 error:nil] writeToFile:[support stringByAppendingPathComponent:@"crossover-app.json"] atomically:YES];
 check([MCD2FindCrossOver(support) isEqual:custom],"saved custom CrossOver restored on next launch");
 a.crossoverApp=[fixture stringByAppendingPathComponent:@"Moved.app"];a.setupAttempted=NO;a.working=NO;a.runtimeError=nil;
 [a licenseChanged:nil];check(!a.primary.enabled && ![a.status.stringValue containsString:@"1002"],"missing selected CrossOver error hidden until setup click");
 [a.primary performClick:nil];check([a.status.stringValue containsString:@"1002"],"setup click explains missing selected CrossOver");
 a.crossoverApp=custom;
 a.working=NO;a.runtimeError=nil;resources=original;a.operation=@"setup";[a finished:1 output:@"Synthetic installation failure"];
 check([a.status.stringValue containsString:@"2299"],"setup failure not replaced by readiness text");

 NSStackView *stack=[NSStackView new]; [a addErrorDetailsToStack:stack];
 check(!a.errorView.hidden && !a.detailsExpanded && a.detailsScroll.hidden,"error starts collapsed");
 [a toggleErrorDetails:nil];
 check(!a.detailsScroll.hidden && [a.detailsText.string containsString:@"Expected:"] && [a.detailsText.string containsString:@"Next step:"],"details expand with context");
 [a clearError];check(a.errorView.hidden && !a.internalError,"clearing hides stale error details");
 a.operation=@"launch"; a.setupMode=NO;
 [a finished:1 output:@"MCD2_INTERNAL_ERROR:{\"code\":3001,\"token\":\"SECRET\",\"system_code\":13}"];
 check([a.internalError[@"code"] integerValue]==3001,"structured network error reaches actual completion handler");
 check(![a.detailsText.string containsString:@"SECRET"] && [a.detailsText.string containsString:@"13"],"details retain numeric metadata without secret fields");
 check(MCD2ParseError(@"MCD2_INTERNAL_ERROR:{\"code\":9999}")==nil,"unknown code rejected");
 a.saveLogsButton=[NSButton new];[a updateRecording:@{@"available":@NO}];
 check(a.saveLogsButton.enabled,"error-only report can be saved without recording");
 check(MCD2ParseError(@"MCD2_INTERNAL_ERROR:bad json")==nil,"malformed protocol rejected");
 check(MCD2ParseError(@"MCD2_INTERNAL_ERROR:{\"code\":\"3001\"}")==nil,"string code rejected");
 a.cancelling=YES;[a finished:1 output:@"MCD2_INTERNAL_ERROR:{\"code\":3004}"];
 check(a.internalError==nil && [a.status.stringValue isEqual:@"Launch cancelled."],"intentional cancel is not an internal error");
 a.cancelling=NO;[a finished:0 output:@""];
 check(a.errorView.hidden,"success hides previous error");
 NSDictionary *saved=[NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:[support stringByAppendingPathComponent:@"internal-error.json"]] options:0 error:nil];
 check([saved[@"code"] integerValue]==3001 && saved.count==3,"last-error export record contains only code and numeric metadata");
 } return 0; }
