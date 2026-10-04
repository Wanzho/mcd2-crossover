#import <Cocoa/Cocoa.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

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

@interface MCD2DocumentView : NSView
@end
@implementation MCD2DocumentView
- (BOOL)isFlipped { return YES; }
- (void)layout {
    [super layout];
    NSView *stack = self.subviews.firstObject;
    CGFloat height = MAX(self.superview.bounds.size.height, stack.fittingSize.height + 52);
    if (fabs(self.frame.size.height - height) > 1) [self setFrameSize:NSMakeSize(self.frame.size.width,height)];
}
@end

@interface MCD2App : NSObject <NSApplicationDelegate, NSWindowDelegate, NSMenuItemValidation>
@property NSWindow *window;
@property NSScrollView *scroll;
@property NSStackView *stack;
@property NSPopUpButton *bottles;
@property NSPopUpButton *stores;
@property NSTextField *gameLabel;
@property NSTextField *status;
@property NSButton *choose;
@property NSButton *license;
@property NSButton *primary;
@property NSButton *secondary;
@property NSButton *closeButton;
@property NSButton *changeBottleButton;
@property NSButton *recordButton;
@property NSButton *saveLogsButton;
@property NSButton *troubleshootingButton;
@property NSPanel *diagnosticPanel;
@property NSTextField *recordStatus;
@property NSTimer *recordTimer;
@property NSDictionary *gameCopy;
@property NSProgressIndicator *progress;
@property NSString *bottleRoot;
@property NSString *game;
@property NSString *gameSelection;
@property NSString *operation;
@property NSTask *task;
@property BOOL working;
@property BOOL setupMode;
@property BOOL changingBottle;
@property BOOL cancelling;
@property BOOL quitAfterTask;
@property BOOL recording;
@property BOOL diagnosticsBusy;
@property BOOL logsSaved;
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
    NSMenuItem *browse = [appMenu addItemWithTitle:@"Browse Game Copy…" action:@selector(chooseFolder:) keyEquivalent:@"o"]; browse.target = self;
    NSMenuItem *stop = [appMenu addItemWithTitle:@"Force Quit Game…" action:@selector(stopGame:) keyEquivalent:@""]; stop.target = self;
    NSMenuItem *repair = [appMenu addItemWithTitle:@"Repair Setup…" action:@selector(repair:) keyEquivalent:@""]; repair.target = self;
    [appMenu addItem:NSMenuItem.separatorItem];
    [appMenu addItemWithTitle:@"Quit MCD2 Crossover" action:@selector(terminate:) keyEquivalent:@"q"];
    NSMenuItem *help = [[NSMenuItem alloc] initWithTitle:@"Help" action:nil keyEquivalent:@""]; [main addItem:help];
    NSMenu *helpMenu = [NSMenu new]; help.submenu = helpMenu;
    NSMenuItem *guide = [helpMenu addItemWithTitle:@"MCD2 Crossover Help" action:@selector(openHelp:) keyEquivalent:@"?"]; guide.target = self;
    NSMenuItem *troubleshooting = [helpMenu addItemWithTitle:@"Troubleshooting…" action:@selector(openTroubleshooting:) keyEquivalent:@""]; troubleshooting.target = self;
    NSMenuItem *record = [helpMenu addItemWithTitle:@"Start / Stop Recording" action:@selector(toggleRecording:) keyEquivalent:@""]; record.target = self;
    NSMenuItem *save = [helpMenu addItemWithTitle:@"Save Logs…" action:@selector(saveLogs:) keyEquivalent:@""]; save.target = self;
    NSApp.mainMenu = main;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,640,600) styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO];
    self.window.contentMinSize = NSMakeSize(560,420);
    self.window.title = @"MCD2 Crossover"; self.window.delegate = self;
    NSDictionary *saved = settings();
    // Accept the earlier private test labels for the same installed repair.
    BOOL ready = ([saved[@"app_version"] isEqualToString:@"0.2.0"]
        || [saved[@"app_version"] isEqualToString:@"0.2.1"]
        || [saved[@"app_version"] isEqualToString:[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"]])
        && exists([support stringByAppendingPathComponent:@"runtime/bridge.py"])
        && exists([support stringByAppendingPathComponent:@"python/bin/python"])
        && [saved[@"game"] isKindOfClass:NSString.class]
        && exists([(saved[@"binary"] ?: [saved[@"game"] stringByAppendingPathComponent:@"Dungeons/Binaries/Win64"]) stringByAppendingPathComponent:@"xgameruntime.dll"]);
    [self showSetup:!ready];
    [self.window center]; [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
    self.recordTimer = [NSTimer scheduledTimerWithTimeInterval:15 target:self selector:@selector(refreshRecording:) userInfo:nil repeats:YES];
}
- (void)showSetup:(BOOL)setup {
    if (!setup) self.changingBottle = NO;
    self.setupMode = setup;
    self.closeButton = nil;
    self.changeBottleButton = nil;
    self.choose = nil; self.bottles = nil; self.stores = nil; self.license = nil; self.gameCopy = nil; self.gameSelection = nil;
    [self.scroll removeFromSuperview];
    NSRect available = (self.window.screen ?: NSScreen.mainScreen).visibleFrame;
    NSRect frame = self.window.frame; frame.size = NSMakeSize(640,MIN(setup ? 610 : 480, available.size.height - 40));
    frame.origin.y = MAX(available.origin.y,MIN(frame.origin.y,NSMaxY(available)-frame.size.height));
    [self.window setFrame:frame display:YES];
    self.scroll = [[NSScrollView alloc] initWithFrame:self.window.contentView.bounds];
    self.scroll.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable; self.scroll.hasVerticalScroller = YES;
    self.scroll.drawsBackground = NO; [self.window.contentView addSubview:self.scroll];
    MCD2DocumentView *document = [[MCD2DocumentView alloc] initWithFrame:NSMakeRect(0,0,self.scroll.contentSize.width,1000)];
    document.autoresizingMask = NSViewWidthSizable; self.scroll.documentView = document;
    self.stack = [NSStackView new]; self.stack.orientation = NSUserInterfaceLayoutOrientationVertical;
    self.stack.alignment = NSLayoutAttributeLeading; self.stack.spacing = 12; self.stack.translatesAutoresizingMaskIntoConstraints = NO;
    [document addSubview:self.stack];
    [NSLayoutConstraint activateConstraints:@[[self.stack.leadingAnchor constraintEqualToAnchor:document.leadingAnchor constant:28], [self.stack.trailingAnchor constraintEqualToAnchor:document.trailingAnchor constant:-28], [self.stack.topAnchor constraintEqualToAnchor:document.topAnchor constant:24]]];
    NSImageView *icon = [NSImageView new]; icon.image = NSApp.applicationIconImage; icon.imageScaling = NSImageScaleProportionallyUpOrDown;
    [icon.widthAnchor constraintEqualToConstant:64].active = YES; [icon.heightAnchor constraintEqualToConstant:64].active = YES;
    self.troubleshootingButton = [NSButton buttonWithTitle:@"Troubleshooting…" target:self action:@selector(openTroubleshooting:)];
    self.troubleshootingButton.controlSize = NSControlSizeSmall; self.troubleshootingButton.font = [NSFont systemFontOfSize:11];
    self.troubleshootingButton.toolTip = @"Record a problem and save troubleshooting logs";
    [self.troubleshootingButton setContentHuggingPriority:NSLayoutPriorityRequired forOrientation:NSLayoutConstraintOrientationHorizontal];
    NSStackView *heading = [NSStackView stackViewWithViews:@[icon,label(setup ? (self.changingBottle ? @"Change Game Copy" : @"Set Up MCD2 Crossover") : @"Minecraft Dungeons II",24,NSFontWeightSemibold),[NSView new],self.troubleshootingButton]];
    heading.orientation = NSUserInterfaceLayoutOrientationHorizontal; heading.spacing = 16; [self.stack addArrangedSubview:heading];
    BOOL launcher = [settings()[@"store"] isEqualToString:@"launcher"];
    [self.stack addArrangedSubview:label(setup ? @"Choose your CrossOver bottle and installed game copy. Changing copies keeps your Microsoft sign-in saved." : (launcher ? @"Minecraft Launcher support is experimental. Play opens the selected copy in CrossOver; Microsoft still checks game ownership." : @"After setup and your first sign-in, you can play directly from Steam in the selected bottle. This app doesn’t need to stay open."),13,NSFontWeightRegular)];
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
        self.stores = [NSPopUpButton new]; [self.stores addItemsWithTitles:@[@"Steam",@"Minecraft Launcher (experimental)"]];
        self.stores.target = self; self.stores.action = @selector(storeChanged:); self.stores.accessibilityLabel = @"Launcher";
        [self.stores selectItemAtIndex:launcher ? 1 : 0];
        [self.stack addArrangedSubview:[self buttonRow:@[label(@"Launcher:",13,NSFontWeightMedium),self.stores]]];
        self.gameLabel = label(@"",13,NSFontWeightRegular); self.gameLabel.selectable = YES; [self.stack addArrangedSubview:self.gameLabel];
        self.choose = [NSButton buttonWithTitle:@"Browse Game Copy…" target:self action:@selector(chooseFolder:)];
        [self.stack addArrangedSubview:[self buttonRow:@[self.choose]]];
        [self.stack addArrangedSubview:label(@"Quit the game first. Setup backs up replaced files and leaves saves alone. For Steam copies, it also restarts Steam.",13,NSFontWeightRegular)];
        NSButton *view = [NSButton buttonWithTitle:@"View Microsoft License…" target:self action:@selector(viewLicense:)];
        [self.stack addArrangedSubview:[self buttonRow:@[view]]];
        self.license = [NSButton checkboxWithTitle:@"I accept the Microsoft GDK license" target:self action:@selector(licenseChanged:)];
        [self.stack addArrangedSubview:self.license];
    } else {
        NSString *bottle = settings()[@"bottle"];
        self.changeBottleButton = [NSButton buttonWithTitle:@"Change Bottle…" target:self action:@selector(changeBottle:)];
        [self.stack addArrangedSubview:[self buttonRow:@[label([@"CrossOver bottle: " stringByAppendingString:bottle ?: @"Not selected"],13,NSFontWeightMedium),self.changeBottleButton]]];
        self.gameLabel = label([@"Game folder: " stringByAppendingString:[settings()[@"game"] stringByAbbreviatingWithTildeInPath] ?: @"Not selected"],13,NSFontWeightRegular);
        self.gameLabel.selectable = YES; [self.stack addArrangedSubview:self.gameLabel];
        self.choose = [NSButton buttonWithTitle:@"Browse Game Copy…" target:self action:@selector(chooseFolder:)];
        [self.stack addArrangedSubview:[self buttonRow:@[self.choose]]];
        [self.stack addArrangedSubview:label(@"Saved sign-in renews in the background. If the game asks you to sign in again, click Play to reconnect.",13,NSFontWeightRegular)];
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
        if ([saved[@"bottle"] isEqual:self.bottles.titleOfSelectedItem] && [saved[@"game"] isKindOfClass:NSString.class]) {
            self.game = saved[@"game"]; self.gameSelection = self.game;
            if ([saved[@"binary"] isKindOfClass:NSString.class] && [saved[@"game_exe"] isKindOfClass:NSString.class]) self.gameSelection = [saved[@"binary"] stringByAppendingPathComponent:[[saved[@"game_exe"] stringByReplacingOccurrencesOfString:@"\\" withString:@"/"] lastPathComponent]];
            [self updateGame];
        }
        if (!self.bottles.numberOfItems) self.status.stringValue = @"Install the game in a CrossOver bottle, then reopen this app.";
        if (!exists(@"/Applications/CrossOver.app")) self.status.stringValue = @"Install CrossOver in Applications, then reopen this app.";
    }
    [document layoutSubtreeIfNeeded];
    [self refreshRecording:nil];
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
    self.gameSelection = self.game;
    [self updateGame];
}
- (void)updateGame {
    self.gameCopy = [self inspectCopy:self.gameSelection ?: self.game store:self.stores.indexOfSelectedItem == 1 ? @"launcher" : @"steam"];
    BOOL valid = self.gameCopy != nil;
    if (valid) self.game = self.gameCopy[@"root"];
    self.gameLabel.stringValue = valid ? [@"Game folder: " stringByAppendingString:[self.game stringByAbbreviatingWithTildeInPath]] : @"Game copy not found. Browse to its installed folder or Shipping.exe file.";
    if (valid) self.status.stringValue = self.stores.indexOfSelectedItem == 1 ? @"Experimental: requires a Launcher-owned copy. Windows Store licensing may prevent it from running in CrossOver." : @"If Visual C++ is missing, Microsoft’s installer will open for you to finish.";
    [self recordEvent:@"copy_checked" outcome:valid ? @"ready" : @"failed"];
    [self licenseChanged:nil];
}
- (void)licenseChanged:(id)sender {
    if (!self.setupMode || self.working) return;
    self.primary.enabled = self.license.state == NSControlStateValueOn && self.bottles.numberOfItems > 0
        && exists(@"/Applications/CrossOver.app") && self.gameCopy != nil;
    if (self.changingBottle && [self.bottles.titleOfSelectedItem isEqual:settings()[@"bottle"]]
        && [self.game isEqual:settings()[@"game"]]
        && (!settings()[@"binary"] || [self.gameCopy[@"binary"] isEqual:settings()[@"binary"]])
        && ((self.stores.indexOfSelectedItem == 1) == [settings()[@"store"] isEqualToString:@"launcher"])) self.primary.enabled = NO;
}
- (void)storeChanged:(id)sender { [self updateGame]; }
- (NSDictionary *)inspectCopy:(NSString *)path store:(NSString *)store {
    if (!path.length) return nil;
    NSTask *task = [NSTask new]; task.executableURL = [NSURL fileURLWithPath:[resources stringByAppendingPathComponent:@"python/bin/python3"]];
    task.arguments = @[@"-I",@"-B",[resources stringByAppendingPathComponent:@"scripts/game_copy.py"],@"--inspect",path,@"--store",store];
    NSPipe *pipe = [NSPipe pipe]; task.standardOutput = pipe; task.standardError = NSFileHandle.fileHandleWithNullDevice;
    if (![task launchAndReturnError:nil]) return nil;
    NSData *data = [pipe.fileHandleForReading readDataToEndOfFile]; [task waitUntilExit];
    id copy = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    return task.terminationStatus == 0 && [copy isKindOfClass:NSDictionary.class] ? copy : nil;
}
- (void)chooseFolder:(id)sender {
    if (self.working) return;
    BOOL fromHome = !self.setupMode;
    NSOpenPanel *panel = [NSOpenPanel openPanel]; panel.title = @"Choose Minecraft Dungeons II";
    panel.message = @"Choose the installed Minecraft Dungeons II folder or its Dungeons Shipping.exe file.";
    panel.canChooseFiles = YES; panel.canChooseDirectories = YES; panel.allowsMultipleSelection = NO;
    panel.directoryURL = [NSURL fileURLWithPath:self.game ?: settings()[@"game"] ?: self.bottleRoot];
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse result) {
        if (result == NSModalResponseOK) {
            if (fromHome) { self.changingBottle = YES; [self showSetup:YES]; }
            self.game = panel.URL.path;
            self.gameSelection = self.game;
            NSString *chosen = [self.game stringByStandardizingPath];
            for (NSString *name in self.bottles.itemTitles) {
                NSString *prefix = [[[self.bottleRoot stringByAppendingPathComponent:name] stringByStandardizingPath] stringByAppendingString:@"/"];
                if ([chosen hasPrefix:prefix]) { [self.bottles selectItemWithTitle:name]; break; }
            }
            NSDictionary *detected = [self inspectCopy:self.game store:@"auto"];
            if (detected) [self.stores selectItemAtIndex:[detected[@"store"] isEqualToString:@"launcher"] ? 1 : 0];
            [self updateGame];
        }
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
        arguments:@[@"-I",@"-B",[resources stringByAppendingPathComponent:@"scripts/install.py"],@"--bottle",self.bottles.titleOfSelectedItem,@"--game",self.gameCopy[@"executable"],@"--store",self.stores.indexOfSelectedItem == 1 ? @"launcher" : @"steam",@"--accept-gdk-license"]];
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
    self.stores.enabled = NO;
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
    NSString *step = [self.operation isEqualToString:@"sign-out"] ? @"sign_out" : [self.operation isEqualToString:@"stop-game"] ? @"stop_game" : self.operation;
    if (step) [self recordEvent:step outcome:self.cancelling ? @"cancelled" : code ? @"failed" : @"success"];
    if (self.quitAfterTask) { [NSApp terminate:nil]; return; }
    if ([self.operation isEqualToString:@"setup"] && code == 0) { [self showSetup:NO]; self.status.stringValue = @"Setup complete. Press Play to open the game."; return; }
    self.primary.enabled = !self.setupMode; self.secondary.enabled = YES;
    self.closeButton.enabled = YES;
    self.changeBottleButton.enabled = YES;
    self.stores.enabled = YES;
    self.bottles.enabled = YES; self.choose.enabled = YES; self.license.enabled = YES;
    self.secondary.title = self.setupMode ? @"Cancel" : @"Sign Out";
    self.secondary.action = self.setupMode ? @selector(cancel:) : @selector(signOut:); self.secondary.keyEquivalent = self.setupMode ? @"\e" : @"";
    if (self.cancelling) self.status.stringValue = @"Launch cancelled.";
    else if (code) self.status.stringValue = [self.operation isEqualToString:@"setup"] ? [output stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet] : @"Couldn’t finish. Check your connection and try again. You can also choose Repair Setup from the app menu.";
    else if ([self.operation isEqualToString:@"sign-out"]) self.status.stringValue = @"Signed out. Your saved Microsoft credential and local session were removed. Play will ask you to sign in again.";
    else if ([self.operation isEqualToString:@"stop-game"]) self.status.stringValue = @"The game was stopped.";
    else self.status.stringValue = [settings()[@"store"] isEqualToString:@"launcher"] ? @"The selected game copy is opening in CrossOver. Launcher support is experimental." : @"Steam is opening the game. You can close this app now.";
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
- (void)recordEvent:(NSString *)step outcome:(NSString *)outcome {
    if (!self.recording) return;
    NSTask *task = [NSTask new]; task.executableURL = [NSURL fileURLWithPath:[resources stringByAppendingPathComponent:@"python/bin/python3"]];
    task.arguments = @[@"-I",@"-B",[resources stringByAppendingPathComponent:@"helper/diagnostics.py"],@"event",@"--step",step,@"--outcome",outcome];
    task.standardOutput = NSFileHandle.fileHandleWithNullDevice; task.standardError = NSFileHandle.fileHandleWithNullDevice;
    [task launchAndReturnError:nil];
}
- (void)openTroubleshooting:(id)sender {
    if (self.diagnosticPanel) return;
    NSPanel *panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0,0,480,220) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
    panel.title = @"Troubleshooting"; self.diagnosticPanel = panel;
    self.logsSaved = NO;
    NSStackView *stack = [NSStackView new]; stack.orientation = NSUserInterfaceLayoutOrientationVertical; stack.alignment = NSLayoutAttributeLeading; stack.spacing = 14;
    stack.translatesAutoresizingMaskIntoConstraints = NO; [panel.contentView addSubview:stack];
    [NSLayoutConstraint activateConstraints:@[[stack.leadingAnchor constraintEqualToAnchor:panel.contentView.leadingAnchor constant:24], [stack.trailingAnchor constraintEqualToAnchor:panel.contentView.trailingAnchor constant:-24], [stack.topAnchor constraintEqualToAnchor:panel.contentView.topAnchor constant:20]]];
    [stack addArrangedSubview:label(@"Troubleshooting",17,NSFontWeightSemibold)];
    self.recordStatus = label(@"",13,NSFontWeightRegular); self.recordStatus.accessibilityLabel = @"Log recording status"; [stack addArrangedSubview:self.recordStatus];
    [stack addArrangedSubview:label(@"Setup and sign-in issues can be recorded here with the game closed.",13,NSFontWeightRegular)];
    self.recordButton = [NSButton buttonWithTitle:@"Start Recording" target:self action:@selector(toggleRecording:)];
    self.saveLogsButton = [NSButton buttonWithTitle:@"Save Logs…" target:self action:@selector(saveLogs:)];
    NSButton *done = [NSButton buttonWithTitle:@"Done" target:self action:@selector(closeTroubleshooting:)]; done.keyEquivalent = @"\e";
    [stack addArrangedSubview:[self buttonRow:@[self.recordButton,self.saveLogsButton,done]]];
    for (NSView *view in stack.arrangedSubviews) [view.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active = YES;
    [self updateRecording:@{@"active":@(self.recording)}];
    [self.window beginSheet:panel completionHandler:nil]; [self refreshRecording:nil];
}
- (void)closeTroubleshooting:(id)sender {
    [self.window endSheet:self.diagnosticPanel]; self.diagnosticPanel = nil;
    self.recordButton = nil; self.saveLogsButton = nil; self.recordStatus = nil;
}
- (void)diagnostics:(NSString *)command output:(NSString *)path completion:(void (^)(NSDictionary *, BOOL))completion {
    self.diagnosticsBusy = YES; self.recordButton.enabled = NO; self.saveLogsButton.enabled = NO;
    NSTask *task = [NSTask new]; task.executableURL = [NSURL fileURLWithPath:[resources stringByAppendingPathComponent:@"python/bin/python3"]];
    NSMutableArray *args = [@[@"-I",@"-B",[resources stringByAppendingPathComponent:@"helper/diagnostics.py"],command] mutableCopy];
    if (path) [args addObjectsFromArray:@[@"--output",path]];
    task.arguments = args; NSPipe *pipe = [NSPipe pipe]; task.standardOutput = pipe; task.standardError = NSFileHandle.fileHandleWithNullDevice;
    if (![task launchAndReturnError:nil]) {
        self.diagnosticsBusy = NO; self.recordButton.enabled = YES; self.saveLogsButton.enabled = YES;
        if (completion) completion(@{},NO); return;
    }
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
        NSData *data = [pipe.fileHandleForReading readDataToEndOfFile]; [task waitUntilExit];
        id json = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
        dispatch_async(dispatch_get_main_queue(), ^{
            self.diagnosticsBusy = NO; self.recordButton.enabled = YES; self.saveLogsButton.enabled = YES;
            if (completion) completion([json isKindOfClass:NSDictionary.class] ? json : @{},task.terminationStatus == 0);
        });
    });
}
- (void)updateRecording:(NSDictionary *)state {
    self.recording = [state[@"active"] boolValue];
    self.recordButton.title = self.recording ? @"Stop Recording" : @"Start Recording";
    if (!self.logsSaved || self.recording) self.recordStatus.stringValue = self.recording ? @"Recording. Reproduce the problem, then click Save Logs." : @"For in-game problems, click on Start Recording and reproduce the problem in-game.";
    self.troubleshootingButton.toolTip = self.recording ? @"Recording troubleshooting logs — click to stop or save" : @"Record a problem and save troubleshooting logs";
    if (state[@"available"]) self.saveLogsButton.enabled = [state[@"available"] boolValue];
}
- (void)refreshRecording:(id)sender {
    if (self.diagnosticsBusy) return;
    [self diagnostics:@"status" output:nil completion:^(NSDictionary *state, BOOL ok) { if (ok) [self updateRecording:state]; }];
}
- (void)toggleRecording:(id)sender {
    if (self.diagnosticsBusy) return;
    [self diagnostics:self.recording ? @"stop" : @"start" output:nil completion:^(NSDictionary *state, BOOL ok) {
        if (ok) { self.logsSaved = NO; [self updateRecording:state]; }
        else self.recordStatus.stringValue = @"Couldn’t change recording. Check that your account can write to Application Support.";
    }];
}
- (void)saveLogs:(id)sender {
    if (self.diagnosticsBusy) return;
    NSSavePanel *panel = [NSSavePanel savePanel]; panel.title = @"Save Troubleshooting Logs";
    panel.message = @"Save logs to attach to a GitHub issue. Recording stops when saved.";
    NSDateFormatter *format = [NSDateFormatter new]; format.dateFormat = @"yyyy-MM-dd-HHmm";
    panel.nameFieldStringValue = [NSString stringWithFormat:@"MCD2-Crossover-Logs-%@.zip",[format stringFromDate:NSDate.date]];
    panel.allowedContentTypes = @[UTTypeZIP]; panel.canCreateDirectories = YES;
    [panel beginSheetModalForWindow:self.diagnosticPanel ?: self.window completionHandler:^(NSModalResponse response) {
        if (response != NSModalResponseOK) return;
        NSString *destination = panel.URL.path;
        [self diagnostics:@"export" output:destination completion:^(NSDictionary *state, BOOL ok) {
            [self updateRecording:state];
            if (ok) {
                self.logsSaved = YES;
                NSString *text = @"Logs saved, attach to issue in the GitHub page.";
                NSMutableAttributedString *message = [[NSMutableAttributedString alloc] initWithString:text attributes:@{NSFontAttributeName:[NSFont systemFontOfSize:13],NSForegroundColorAttributeName:NSColor.labelColor}];
                [message addAttribute:NSLinkAttributeName value:[NSURL URLWithString:@"https://github.com/Wanzho/mcd2-crossover/issues/new/choose"] range:[text rangeOfString:@"GitHub page"]];
                self.recordStatus.allowsEditingTextAttributes = YES; self.recordStatus.selectable = YES; self.recordStatus.attributedStringValue = message;
            } else self.recordStatus.stringValue = @"Couldn’t save logs. Choose another location and try again.";
            if (ok) [NSWorkspace.sharedWorkspace activateFileViewerSelectingURLs:@[[NSURL fileURLWithPath:destination]]];
        }];
    }];
}
- (void)openHelp:(id)sender { [NSWorkspace.sharedWorkspace openURL:[NSURL URLWithString:@"https://github.com/Wanzho/mcd2-crossover#readme"]]; }
- (BOOL)validateMenuItem:(NSMenuItem *)item {
    if (item.action == @selector(play:) || item.action == @selector(signOut:) || item.action == @selector(stopGame:) || item.action == @selector(changeBottle:)) return !self.working && !self.setupMode;
    if (item.action == @selector(repair:)) return !self.working;
    if (item.action == @selector(chooseFolder:)) return !self.working;
    if (item.action == @selector(toggleRecording:) || item.action == @selector(saveLogs:)) return !self.diagnosticsBusy;
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
