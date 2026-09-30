#import <Cocoa/Cocoa.h>

static NSString *resources;
static NSString *support;
static NSTextField *label(NSString *text, CGFloat size, NSFontWeight weight) {
    NSTextField *view = [NSTextField wrappingLabelWithString:text];
    view.font = [NSFont systemFontOfSize:size weight:weight];
    view.textColor = NSColor.labelColor;
    return view;
}
static NSDictionary *settings(void) {
    NSData *data = [NSData dataWithContentsOfFile:[support stringByAppendingPathComponent:@"settings.json"]];
    id value = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
    return [value isKindOfClass:NSDictionary.class] ? value : @{};
}
static BOOL exists(NSString *path) { return path && [NSFileManager.defaultManager fileExistsAtPath:path]; }

@interface MCD2App : NSObject <NSApplicationDelegate, NSWindowDelegate, NSMenuItemValidation>
@property NSWindow *window;
@property NSStackView *stack;
@property NSPopUpButton *bottles;
@property NSTextField *gameLabel;
@property NSTextField *status;
@property NSButton *choose;
@property NSButton *license;
@property NSButton *primary;
@property NSButton *secondary;
@property NSButton *closeButton;
@property NSButton *changeBottleButton;
@property NSProgressIndicator *progress;
@property NSString *bottleRoot;
@property NSString *game;
@property NSString *operation;
@property NSTask *task;
@property BOOL working;
@property BOOL setupMode;
@property BOOL changingBottle;
@property BOOL cancelling;
@property BOOL quitAfterTask;
@end

@implementation MCD2App
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    resources = NSBundle.mainBundle.resourcePath;
    support = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/DungeonsCrossOver"];
    self.bottleRoot = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/CrossOver/Bottles"];
    NSMenu *main = [NSMenu new];
    NSMenuItem *application = [NSMenuItem new]; [main addItem:application];
    NSMenu *appMenu = [NSMenu new]; application.submenu = appMenu;
    NSMenuItem *about = [appMenu addItemWithTitle:@"About MCD2 Crossover" action:@selector(orderFrontStandardAboutPanel:) keyEquivalent:@""]; about.target = NSApp;
    [appMenu addItem:NSMenuItem.separatorItem];
    NSMenuItem *play = [appMenu addItemWithTitle:@"Play" action:@selector(play:) keyEquivalent:@"p"]; play.target = self;
    NSMenuItem *signout = [appMenu addItemWithTitle:@"Sign Out" action:@selector(signOut:) keyEquivalent:@""]; signout.target = self;
    NSMenuItem *change = [appMenu addItemWithTitle:@"Change Bottle…" action:@selector(changeBottle:) keyEquivalent:@""]; change.target = self;
    NSMenuItem *stop = [appMenu addItemWithTitle:@"Force Quit Game…" action:@selector(stopGame:) keyEquivalent:@""]; stop.target = self;
    NSMenuItem *repair = [appMenu addItemWithTitle:@"Repair Setup…" action:@selector(repair:) keyEquivalent:@""]; repair.target = self;
    [appMenu addItem:NSMenuItem.separatorItem];
    [appMenu addItemWithTitle:@"Quit MCD2 Crossover" action:@selector(terminate:) keyEquivalent:@"q"];
    NSMenuItem *help = [[NSMenuItem alloc] initWithTitle:@"Help" action:nil keyEquivalent:@""]; [main addItem:help];
    NSMenu *helpMenu = [NSMenu new]; help.submenu = helpMenu;
    NSMenuItem *guide = [helpMenu addItemWithTitle:@"MCD2 Crossover Help" action:@selector(openHelp:) keyEquivalent:@"?"]; guide.target = self;
    NSApp.mainMenu = main;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,600,540) styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable backing:NSBackingStoreBuffered defer:NO];
    self.window.title = @"MCD2 Crossover"; self.window.delegate = self;
    NSDictionary *saved = settings();
    // Accept the earlier private test labels for the same installed repair.
    BOOL ready = ([saved[@"app_version"] isEqualToString:@"0.2.0"]
        || [saved[@"app_version"] isEqualToString:@"0.2.1"]
        || [saved[@"app_version"] isEqualToString:[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"]])
        && exists([support stringByAppendingPathComponent:@"runtime/bridge.py"])
        && exists([support stringByAppendingPathComponent:@"python/bin/python"])
        && [saved[@"game"] isKindOfClass:NSString.class]
        && exists([saved[@"game"] stringByAppendingPathComponent:@"MCD2CrossoverLaunch.cmd"])
        && exists([saved[@"game"] stringByAppendingPathComponent:@"Dungeons/Binaries/Win64/xgameruntime.dll"]);
    [self showSetup:!ready];
    [self.window center]; [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
}
- (void)showSetup:(BOOL)setup {
    if (!setup) self.changingBottle = NO;
    self.setupMode = setup;
    self.closeButton = nil;
    self.changeBottleButton = nil;
    [self.stack removeFromSuperview];
    NSRect frame = self.window.frame; frame.size = NSMakeSize(600, setup ? 690 : 480);
    [self.window setFrame:frame display:YES];
    self.stack = [NSStackView new]; self.stack.orientation = NSUserInterfaceLayoutOrientationVertical;
    self.stack.alignment = NSLayoutAttributeLeading; self.stack.spacing = 16; self.stack.translatesAutoresizingMaskIntoConstraints = NO;
    [self.window.contentView addSubview:self.stack];
    [NSLayoutConstraint activateConstraints:@[[self.stack.leadingAnchor constraintEqualToAnchor:self.window.contentView.leadingAnchor constant:28], [self.stack.trailingAnchor constraintEqualToAnchor:self.window.contentView.trailingAnchor constant:-28], [self.stack.topAnchor constraintEqualToAnchor:self.window.contentView.topAnchor constant:24]]];
    NSImageView *icon = [NSImageView new]; icon.image = NSApp.applicationIconImage; icon.imageScaling = NSImageScaleProportionallyUpOrDown;
    [icon.widthAnchor constraintEqualToConstant:64].active = YES; [icon.heightAnchor constraintEqualToConstant:64].active = YES;
    NSStackView *heading = [NSStackView stackViewWithViews:@[icon,label(setup ? (self.changingBottle ? @"Change CrossOver Bottle" : @"Set Up MCD2 Crossover") : @"Minecraft Dungeons II",24,NSFontWeightSemibold)]];
    heading.orientation = NSUserInterfaceLayoutOrientationHorizontal; heading.spacing = 16; [self.stack addArrangedSubview:heading];
    [self.stack addArrangedSubview:label(setup ? (self.changingBottle ? @"Choose a bottle with Windows Steam and Minecraft Dungeons II installed. Your Microsoft sign-in stays saved." : @"Set up game startup and Xbox sign-in for your Steam copy in CrossOver.") : @"After setup and your first sign-in, you can play directly from Steam in the selected bottle. This app doesn’t need to stay open.",13,NSFontWeightRegular)];
    if (setup) {
        self.bottles = [NSPopUpButton new]; self.bottles.target = self; self.bottles.action = @selector(bottleChanged:); self.bottles.accessibilityLabel = @"CrossOver bottle";
        NSMutableArray *names = [NSMutableArray new];
        for (NSString *name in [NSFileManager.defaultManager contentsOfDirectoryAtPath:self.bottleRoot error:nil])
            if (exists([[self.bottleRoot stringByAppendingPathComponent:name] stringByAppendingPathComponent:@"cxbottle.conf"])) [names addObject:name];
        [names sortUsingSelector:@selector(localizedStandardCompare:)]; [self.bottles addItemsWithTitles:names];
        NSString *savedBottle = settings()[@"bottle"];
        if ([names containsObject:savedBottle]) [self.bottles selectItemWithTitle:savedBottle];
        else if ([names containsObject:@"Steam"]) [self.bottles selectItemWithTitle:@"Steam"];
        NSStackView *row = [NSStackView stackViewWithViews:@[label(@"CrossOver Bottle",13,NSFontWeightMedium),self.bottles]];
        row.orientation = NSUserInterfaceLayoutOrientationHorizontal; row.spacing = 16; [self.bottles.widthAnchor constraintGreaterThanOrEqualToConstant:260].active = YES;
        [self.stack addArrangedSubview:row];
        self.gameLabel = label(@"",13,NSFontWeightRegular); self.gameLabel.selectable = YES; [self.stack addArrangedSubview:self.gameLabel];
        self.choose = [NSButton buttonWithTitle:@"Choose Game Folder…" target:self action:@selector(chooseFolder:)];
        [self.stack addArrangedSubview:[self buttonRow:@[self.choose]]];
        [self.stack addArrangedSubview:label(@"Quit the game first. Setup restarts Steam, backs up replaced files and leaves your saves alone.",13,NSFontWeightRegular)];
        NSButton *view = [NSButton buttonWithTitle:@"View Microsoft License…" target:self action:@selector(viewLicense:)];
        [self.stack addArrangedSubview:[self buttonRow:@[view]]];
        self.license = [NSButton checkboxWithTitle:@"I accept the Microsoft GDK license" target:self action:@selector(licenseChanged:)];
        [self.stack addArrangedSubview:self.license];
    } else {
        NSString *bottle = settings()[@"bottle"];
        self.changeBottleButton = [NSButton buttonWithTitle:@"Change Bottle…" target:self action:@selector(changeBottle:)];
        [self.stack addArrangedSubview:[self buttonRow:@[label([@"CrossOver bottle: " stringByAppendingString:bottle ?: @"Not selected"],13,NSFontWeightMedium),self.changeBottleButton]]];
        [self.stack addArrangedSubview:label(@"Saved sign-in renews in the background. If Steam asks you to sign in again, open this app and click Play to reconnect.",13,NSFontWeightRegular)];
    }
    self.status = label(setup ? @"If Visual C++ is missing, Microsoft’s installer will open for you to finish." : @"To change Microsoft accounts, quit the game and choose Sign Out.",13,NSFontWeightRegular);
    self.status.accessibilityLabel = @"Status"; [self.stack addArrangedSubview:self.status];
    self.progress = [NSProgressIndicator new]; self.progress.style = NSProgressIndicatorStyleBar; self.progress.indeterminate = YES; self.progress.hidden = YES; [self.stack addArrangedSubview:self.progress];
    self.secondary = [NSButton buttonWithTitle:setup ? @"Cancel" : @"Sign Out" target:self action:setup ? @selector(cancel:) : @selector(signOut:)];
    self.primary = [NSButton buttonWithTitle:setup ? (self.changingBottle ? @"Use This Bottle" : @"Set Up") : @"Play" target:self action:setup ? @selector(install:) : @selector(play:)]; self.primary.keyEquivalent = @"\r";
    self.secondary.keyEquivalent = setup ? @"\e" : @"";
    NSView *actions = [NSView new]; self.primary.translatesAutoresizingMaskIntoConstraints = NO; self.secondary.translatesAutoresizingMaskIntoConstraints = NO;
    [actions addSubview:self.primary]; [actions addSubview:self.secondary]; [self.stack addArrangedSubview:actions];
    [NSLayoutConstraint activateConstraints:@[[actions.heightAnchor constraintEqualToConstant:32], [self.primary.trailingAnchor constraintEqualToAnchor:actions.trailingAnchor], [self.primary.centerYAnchor constraintEqualToAnchor:actions.centerYAnchor], [self.secondary.centerYAnchor constraintEqualToAnchor:actions.centerYAnchor], [self.secondary.trailingAnchor constraintEqualToAnchor:self.primary.leadingAnchor constant:-12], [self.primary.widthAnchor constraintGreaterThanOrEqualToConstant:100], [self.secondary.widthAnchor constraintGreaterThanOrEqualToConstant:100]]];
    if (!setup) {
        self.closeButton = [NSButton buttonWithTitle:@"Close Window" target:self action:@selector(closeWindow:)];
        self.closeButton.keyEquivalent = @"\e"; self.closeButton.translatesAutoresizingMaskIntoConstraints = NO; [actions addSubview:self.closeButton];
        [NSLayoutConstraint activateConstraints:@[[self.closeButton.centerYAnchor constraintEqualToAnchor:actions.centerYAnchor], [self.closeButton.trailingAnchor constraintEqualToAnchor:self.secondary.leadingAnchor constant:-12], [self.closeButton.widthAnchor constraintGreaterThanOrEqualToConstant:116]]];
    }
    for (NSView *view in self.stack.arrangedSubviews) [view.widthAnchor constraintEqualToAnchor:self.stack.widthAnchor].active = YES;
    if (setup) {
        [self bottleChanged:nil];
        NSDictionary *saved = settings();
        if ([saved[@"bottle"] isEqual:self.bottles.titleOfSelectedItem] && [saved[@"game"] isKindOfClass:NSString.class]) { self.game = saved[@"game"]; [self updateGame]; }
        if (!self.bottles.numberOfItems) self.status.stringValue = @"Install Steam and the game in a CrossOver bottle, then reopen this app.";
        if (!exists(@"/Applications/CrossOver.app")) self.status.stringValue = @"Install CrossOver in Applications, then reopen this app.";
    }
}
- (NSView *)buttonRow:(NSArray *)buttons {
    NSStackView *row = [NSStackView stackViewWithViews:buttons]; row.orientation = NSUserInterfaceLayoutOrientationHorizontal; row.alignment = NSLayoutAttributeCenterY;
    // A trailing spacer keeps controls at their natural size.
    [row addArrangedSubview:[NSView new]]; return row;
}
- (void)bottleChanged:(id)sender {
    if (self.working) return;
    NSString *bottle = self.bottles.titleOfSelectedItem;
    self.game = bottle ? [[self.bottleRoot stringByAppendingPathComponent:bottle] stringByAppendingPathComponent:@"drive_c/Program Files (x86)/Steam/steamapps/common/Minecraft Dungeons II"] : nil;
    [self updateGame];
}
- (void)updateGame {
    BOOL valid = exists([self.game stringByAppendingPathComponent:@"MicrosoftGame.config"])
        && exists([self.game stringByAppendingPathComponent:@"Dungeons/Binaries/Win64/Dungeons-Win64-Shipping.exe"]);
    self.gameLabel.stringValue = valid ? [@"Game folder: " stringByAppendingString:[self.game stringByAbbreviatingWithTildeInPath]] : @"Game folder not found. Choose the folder where Steam installed Minecraft Dungeons II.";
    [self licenseChanged:nil];
}
- (void)licenseChanged:(id)sender {
    if (!self.setupMode || self.working) return;
    self.primary.enabled = self.license.state == NSControlStateValueOn && self.bottles.numberOfItems > 0
        && exists(@"/Applications/CrossOver.app") && exists([self.game stringByAppendingPathComponent:@"MicrosoftGame.config"])
        && exists([self.game stringByAppendingPathComponent:@"Dungeons/Binaries/Win64/Dungeons-Win64-Shipping.exe"]);
    if (self.changingBottle && [self.bottles.titleOfSelectedItem isEqual:settings()[@"bottle"]]
        && [self.game isEqual:settings()[@"game"]]) self.primary.enabled = NO;
}
- (void)chooseFolder:(id)sender {
    if (self.working || !self.setupMode) return;
    NSOpenPanel *panel = [NSOpenPanel openPanel]; panel.title = @"Choose Minecraft Dungeons II";
    panel.message = @"Select the installed game folder inside Steam’s steamapps/common folder.";
    panel.canChooseFiles = NO; panel.canChooseDirectories = YES; panel.allowsMultipleSelection = NO;
    panel.directoryURL = [NSURL fileURLWithPath:self.bottleRoot];
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse result) {
        if (result == NSModalResponseOK) { self.game = panel.URL.path; [self updateGame]; }
    }];
}
- (void)viewLicense:(id)sender {
    NSString *text = [NSString stringWithContentsOfFile:[resources stringByAppendingPathComponent:@"licenses/Microsoft-GDK-LICENSE.md"] encoding:NSUTF8StringEncoding error:nil];
    NSPanel *panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0,0,620,440) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO]; panel.title = @"Microsoft GDK License";
    NSScrollView *scroll = [[NSScrollView alloc] initWithFrame:NSMakeRect(20,60,580,360)]; scroll.hasVerticalScroller = YES; scroll.borderType = NSBezelBorder;
    NSTextView *view = [[NSTextView alloc] initWithFrame:NSMakeRect(0,0,560,360)]; view.editable = NO; view.font = [NSFont systemFontOfSize:13]; view.string = text ?: @"License file missing. Download the app again."; view.verticallyResizable = YES; view.textContainer.widthTracksTextView = YES; scroll.documentView = view;
    [panel.contentView addSubview:scroll];
    NSButton *done = [NSButton buttonWithTitle:@"Done" target:self action:@selector(closeLicense:)]; done.frame = NSMakeRect(512,16,88,28); done.keyEquivalent = @"\r"; [panel.contentView addSubview:done];
    [self.window beginSheet:panel completionHandler:nil];
}
- (void)closeLicense:(NSButton *)sender { [self.window endSheet:sender.window]; }
- (void)install:(id)sender {
    if (self.working || !self.setupMode || !self.primary.enabled) return;
    [self run:@"setup" executable:[resources stringByAppendingPathComponent:@"python/bin/python3"]
        arguments:@[@"-I",@"-B",[resources stringByAppendingPathComponent:@"scripts/install.py"],@"--bottle",self.bottles.titleOfSelectedItem,@"--game",self.game,@"--accept-gdk-license"]];
}
- (void)play:(id)sender { if (!self.working && !self.setupMode) [self bridge:@"launch"]; }
- (void)signOut:(id)sender { if (!self.working && !self.setupMode) [self bridge:@"sign-out"]; }
- (void)stopGame:(id)sender {
    if (self.working || self.setupMode) return;
    NSAlert *alert = [NSAlert new]; alert.messageText = @"Force quit Minecraft Dungeons II?";
    alert.informativeText = @"Use this if the game is stuck. Unsaved progress may be lost.";
    [alert addButtonWithTitle:@"Cancel"]; [alert addButtonWithTitle:@"Force Quit"];
    [alert beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response) {
        if (response == NSAlertSecondButtonReturn) [self bridge:@"stop-game"];
    }];
}
- (void)bridge:(NSString *)command {
    NSString *bottle = settings()[@"bottle"];
    if (![bottle isKindOfClass:NSString.class]) { [self showSetup:YES]; return; }
    [self run:command executable:[support stringByAppendingPathComponent:@"python/bin/python"]
        arguments:@[@"-I",@"-B",[support stringByAppendingPathComponent:@"runtime/bridge.py"],command,@"--bottle",bottle]];
}
- (void)run:(NSString *)operation executable:(NSString *)executable arguments:(NSArray *)arguments {
    self.working = YES; self.cancelling = NO; self.operation = operation;
    self.primary.enabled = NO; self.bottles.enabled = NO; self.choose.enabled = NO; self.license.enabled = NO;
    self.changeBottleButton.enabled = NO;
    self.secondary.enabled = [operation isEqualToString:@"launch"];
    self.closeButton.enabled = [operation isEqualToString:@"launch"];
    if (self.secondary.enabled) { self.secondary.title = @"Cancel Launch"; self.secondary.action = @selector(cancel:); self.secondary.keyEquivalent = @"\e"; }
    self.progress.hidden = NO; [self.progress startAnimation:nil];
    self.status.stringValue = [operation isEqualToString:@"setup"] ? @"Setting up… If Microsoft’s Visual C++ installer opens, complete it to continue."
        : [operation isEqualToString:@"launch"] ? @"Checking sign-in… If a code window appears, finish signing in and leave it open."
        : [operation isEqualToString:@"stop-game"] ? @"Closing the stuck game…" : @"Removing your saved Microsoft sign-in…";
    NSTask *task = [NSTask new]; self.task = task; task.executableURL = [NSURL fileURLWithPath:executable]; task.arguments = arguments;
    NSPipe *pipe = [NSPipe pipe]; task.standardOutput = pipe; task.standardError = pipe;
    NSError *error;
    if (![task launchAndReturnError:&error]) { [self finished:1 output:@"Couldn’t start. Choose Repair Setup from the MCD2 Crossover menu, or download the app again."]; return; }
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
        NSData *data = [pipe.fileHandleForReading readDataToEndOfFile]; [task waitUntilExit];
        NSString *output = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] ?: @"";
        dispatch_async(dispatch_get_main_queue(), ^{ [self finished:task.terminationStatus output:output]; });
    });
}
- (void)finished:(int)code output:(NSString *)output {
    self.working = NO; self.task = nil; [self.progress stopAnimation:nil]; self.progress.hidden = YES;
    if (self.quitAfterTask) { [NSApp terminate:nil]; return; }
    if ([self.operation isEqualToString:@"setup"] && code == 0) { [self showSetup:NO]; self.status.stringValue = @"Setup complete. Press Play to open the game."; return; }
    self.primary.enabled = !self.setupMode; self.secondary.enabled = YES;
    self.closeButton.enabled = YES;
    self.changeBottleButton.enabled = YES;
    self.bottles.enabled = YES; self.choose.enabled = YES; self.license.enabled = YES;
    self.secondary.title = self.setupMode ? @"Cancel" : @"Sign Out";
    self.secondary.action = self.setupMode ? @selector(cancel:) : @selector(signOut:); self.secondary.keyEquivalent = self.setupMode ? @"\e" : @"";
    if (self.cancelling) self.status.stringValue = @"Launch cancelled.";
    else if (code) self.status.stringValue = [self.operation isEqualToString:@"setup"] ? [output stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet] : @"Couldn’t finish. Check your connection and try again. You can also choose Repair Setup from the app menu.";
    else if ([self.operation isEqualToString:@"sign-out"]) self.status.stringValue = @"Signed out. Your saved Microsoft credential and local session were removed. Play will ask you to sign in again.";
    else if ([self.operation isEqualToString:@"stop-game"]) self.status.stringValue = @"The game was stopped.";
    else self.status.stringValue = @"Steam is opening the game. You can close this app now.";
    [self licenseChanged:nil];
}
- (void)cancel:(id)sender {
    if (!self.working) {
        if (self.setupMode && self.changingBottle) [self showSetup:NO];
        else [NSApp terminate:nil];
        return;
    }
    if (![self.operation isEqualToString:@"launch"]) return;
    self.cancelling = YES; self.status.stringValue = @"Cancelling launch…"; self.secondary.enabled = NO;
    if (self.task.running) [self.task terminate];
}
- (void)changeBottle:(id)sender {
    if (self.working || self.setupMode) return;
    self.changingBottle = YES; [self showSetup:YES];
}
- (void)repair:(id)sender { if (!self.working) { self.changingBottle = NO; [self showSetup:YES]; } }
- (void)closeWindow:(id)sender { [self.window performClose:sender]; }
- (void)openHelp:(id)sender { [NSWorkspace.sharedWorkspace openURL:[NSURL URLWithString:@"https://github.com/Wanzho/mcd2-crossover#readme"]]; }
- (BOOL)validateMenuItem:(NSMenuItem *)item {
    if (item.action == @selector(play:) || item.action == @selector(signOut:) || item.action == @selector(stopGame:) || item.action == @selector(changeBottle:)) return !self.working && !self.setupMode;
    if (item.action == @selector(repair:)) return !self.working;
    return YES;
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if (!self.working) return NSTerminateNow;
    if ([self.operation isEqualToString:@"launch"]) { self.quitAfterTask = YES; [self cancel:nil]; }
    return NSTerminateCancel;
}
- (BOOL)windowShouldClose:(NSWindow *)sender { [NSApp terminate:nil]; return NO; }
- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)visible { [self.window makeKeyAndOrderFront:nil]; return YES; }
@end

int main(void) {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication; app.activationPolicy = NSApplicationActivationPolicyRegular;
        MCD2App *delegate = [MCD2App new]; app.delegate = delegate; [app run];
    }
    return 0;
}
