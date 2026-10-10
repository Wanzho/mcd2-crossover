#import <Cocoa/Cocoa.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import "localization.h"
#import "account.h"
#import "game_copy_native.h"
#import "crossover_app.h"
#import "runtime_preflight.h"
#import "internal_errors.h"
#import "CrossoverUpdater.h"

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

// Preserve the disabled appearance while letting an attempted click explain why.
@interface MCD2SetupButton : NSButton
@property (copy) void (^blockedAttempt)(void);
@end
@implementation MCD2SetupButton
- (void)mouseDown:(NSEvent *)event {
    if (!self.enabled && self.blockedAttempt) { self.blockedAttempt(); return; }
    [super mouseDown:event];
}
- (void)performClick:(id)sender {
    if (!self.enabled && self.blockedAttempt) { self.blockedAttempt(); return; }
    [super performClick:sender];
}
- (BOOL)accessibilityPerformPress {
    if (!self.enabled && self.blockedAttempt) { self.blockedAttempt(); return YES; }
    return [super accessibilityPerformPress];
}
@end

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
@property NSPanel *selectionPanel;
@property NSStackView *selectionStack;
@property NSDictionary *homeUIState;
@property BOOL selectionLicenseAccepted;
@property NSTextField *recordStatus;
@property NSTimer *recordTimer;
@property NSDictionary *gameCopy;
@property NSString *selectionError;
@property NSString *runtimeError;
@property NSDictionary *internalError;
@property NSString *localErrorDetail;
@property NSStackView *errorView;
@property NSButton *detailsButton;
@property NSScrollView *detailsScroll;
@property NSTextView *detailsText;
@property BOOL detailsExpanded;
@property BOOL setupAttempted;
@property NSString *crossoverApp;
@property NSString *crossoverPreferenceError;
@property NSTextField *crossoverLabel;
@property NSButton *chooseCrossoverButton;
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
@property BOOL launchAfterSetup;
@property (strong) NSTextField *accountLabel;
@end

@implementation MCD2App
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    resources = NSBundle.mainBundle.resourcePath;
    support = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/DungeonsCrossOver"];
    self.crossoverApp = MCD2FindCrossOver(support);
    self.runtimeError = MCD2PrepareEmbeddedRuntime(NSBundle.mainBundle.bundlePath, resources);
    self.bottleRoot = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/CrossOver/Bottles"];
    MCD2ConfigureLocalization(resources,[support stringByAppendingPathComponent:@"ui-language"]);
    __weak MCD2App *weakSelf = self;
    [[CrossoverUpdater shared] startWithBusyCheck:^BOOL { return weakSelf.working; }];
    [self buildMenu];
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,700,600) styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO];
    self.window.contentMinSize = NSMakeSize(660,420);
    self.window.title = @"MCD2 Crossover"; self.window.delegate = self;
    NSDictionary *saved = settings();
    // Accept the earlier private test labels for the same installed repair.
    BOOL ready = ([saved[@"app_version"] isEqualToString:@"0.2.0"]
        || [saved[@"app_version"] isEqualToString:@"0.2.1"]
        || [saved[@"app_version"] isEqualToString:@"0.1.2"]
        || [saved[@"app_version"] isEqualToString:@"0.1.3"]
        || [saved[@"app_version"] isEqualToString:@"0.1.4"]
        || [saved[@"app_version"] isEqualToString:@"0.1.5"]
        || [saved[@"app_version"] isEqualToString:@"0.1.5.1"]
        || [saved[@"app_version"] isEqualToString:@"0.1.6"]
        || [saved[@"app_version"] isEqualToString:[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"]])
        && exists([support stringByAppendingPathComponent:@"runtime/bridge.py"])
        && exists([support stringByAppendingPathComponent:@"runtime/localization.py"])
        && exists([support stringByAppendingPathComponent:@"runtime/localization/en.json"])
        && exists([support stringByAppendingPathComponent:@"python/bin/python"])
        && [saved[@"game"] isKindOfClass:NSString.class]
        && exists([(saved[@"binary"] ?: [saved[@"game"] stringByAppendingPathComponent:@"Dungeons/Binaries/Win64"]) stringByAppendingPathComponent:@"xgameruntime.dll"]);
    [self showSetup:!ready || self.runtimeError != nil];
    [self.window center]; [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
    self.recordTimer = [NSTimer scheduledTimerWithTimeInterval:15 target:self selector:@selector(refreshRecording:) userInfo:nil repeats:YES];
}
- (void)buildMenu {
    NSMenu *main = [NSMenu new];
    NSMenuItem *application = [NSMenuItem new]; [main addItem:application];
    NSMenu *appMenu = [NSMenu new]; application.submenu = appMenu;
    NSMenuItem *about = [appMenu addItemWithTitle:L(@"About MCD2 Crossover") action:@selector(orderFrontStandardAboutPanel:) keyEquivalent:@""]; about.target = NSApp;
    [[CrossoverUpdater shared] addItemsToMenu:appMenu];
    [appMenu addItem:NSMenuItem.separatorItem];
    NSMenuItem *play = [appMenu addItemWithTitle:L(@"Play") action:@selector(play:) keyEquivalent:@"p"]; play.target = self;
    NSMenuItem *signout = [appMenu addItemWithTitle:L(@"Sign Out") action:@selector(signOut:) keyEquivalent:@""]; signout.target = self;
    NSMenuItem *change = [appMenu addItemWithTitle:L(@"Change Game Copy") action:@selector(changeBottle:) keyEquivalent:@""]; change.target = self;
    NSMenuItem *browse = [appMenu addItemWithTitle:L(@"Browse Game Copy…") action:@selector(chooseFolder:) keyEquivalent:@"o"]; browse.target = self;
    NSMenuItem *stop = [appMenu addItemWithTitle:L(@"Force Quit Game…") action:@selector(stopGame:) keyEquivalent:@""]; stop.target = self;
    NSMenuItem *repair = [appMenu addItemWithTitle:L(@"Repair Setup…") action:@selector(repair:) keyEquivalent:@""]; repair.target = self;
    NSMenuItem *language = [appMenu addItemWithTitle:L(@"Language…") action:@selector(changeLanguage:) keyEquivalent:@""]; language.target = self;
    [appMenu addItem:NSMenuItem.separatorItem];
    [appMenu addItemWithTitle:L(@"Quit MCD2 Crossover") action:@selector(terminate:) keyEquivalent:@"q"];
    NSMenuItem *help = [[NSMenuItem alloc] initWithTitle:L(@"Help") action:nil keyEquivalent:@""]; [main addItem:help];
    NSMenu *helpMenu = [NSMenu new]; help.submenu = helpMenu;
    NSMenuItem *guide = [helpMenu addItemWithTitle:L(@"MCD2 Crossover Help") action:@selector(openHelp:) keyEquivalent:@"?"]; guide.target = self;
    NSMenuItem *troubleshooting = [helpMenu addItemWithTitle:L(@"Troubleshooting…") action:@selector(openTroubleshooting:) keyEquivalent:@""]; troubleshooting.target = self;
    NSMenuItem *record = [helpMenu addItemWithTitle:L(@"Start / Stop Recording") action:@selector(toggleRecording:) keyEquivalent:@""]; record.target = self;
    NSMenuItem *save = [helpMenu addItemWithTitle:L(@"Save Logs…") action:@selector(saveLogs:) keyEquivalent:@""]; save.target = self;
    NSApp.mainMenu = main;
}
- (void)changeLanguage:(id)sender {
    if (self.working || self.window.attachedSheet) return;
    NSAlert *alert = [NSAlert new]; alert.messageText = L(@"App Language");
    alert.informativeText = L(@"Choose the language used by MCD2 Crossover.");
    NSPopUpButton *languages = [[NSPopUpButton alloc] initWithFrame:NSMakeRect(0,0,320,28) pullsDown:NO];
    [languages addItemWithTitle:L(@"Use System Language")]; languages.lastItem.representedObject = @"system";
    for (NSDictionary *language in MCD2Languages()) {
        [languages addItemWithTitle:language[@"name"]]; languages.lastItem.representedObject = language[@"id"];
    }
    for (NSMenuItem *item in languages.itemArray) if ([item.representedObject isEqual:MCD2LanguageChoice()]) [languages selectItem:item];
    languages.accessibilityLabel = L(@"App Language"); alert.accessoryView = languages;
    [alert addButtonWithTitle:L(@"Apply")]; [alert addButtonWithTitle:L(@"Cancel")];
    [alert beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response) {
        if (response != NSAlertFirstButtonReturn) return;
        NSString *bottle = self.bottles.titleOfSelectedItem;
        NSString *selection = self.gameSelection;
        NSInteger store = self.stores.indexOfSelectedItem;
        NSControlStateValue accepted = self.license.state;
        if (!MCD2SelectLanguage(languages.selectedItem.representedObject)) { NSBeep(); return; }
        [self buildMenu]; [self showSetup:self.setupMode];
        if (self.setupMode) {
            if ([self.bottles.itemTitles containsObject:bottle]) [self.bottles selectItemWithTitle:bottle];
            [self.stores selectItemAtIndex:store]; self.gameSelection = selection;
            self.license.state = accepted; [self updateGame];
        }
    }];
}
- (void)refreshAccount {
    if (!self.accountLabel) return;
    NSString *tag = MCD2AccountTag(support);
    self.accountLabel.stringValue = tag.length ? [L(@"Signed in to: ") stringByAppendingString:tag] : L(@"Not signed in");
}
- (NSInteger)crossOverErrorCode {
    if (!self.crossoverApp.length) return 1001;
    NSDictionary *info=[NSDictionary dictionaryWithContentsOfFile:[self.crossoverApp stringByAppendingPathComponent:@"Contents/Info.plist"]];
    return [info[@"CFBundleIdentifier"] isEqual:@"com.codeweavers.CrossOver"] ? 1003 : 1002;
}
- (void)addErrorDetailsToStack:(NSStackView *)stack {
    self.errorView=[NSStackView new]; self.errorView.orientation=NSUserInterfaceLayoutOrientationVertical;
    self.errorView.alignment=NSLayoutAttributeLeading; self.errorView.spacing=8;
    self.detailsButton=[NSButton buttonWithTitle:@"See details…" target:self action:@selector(toggleErrorDetails:)];
    self.detailsButton.bezelStyle=NSBezelStyleDisclosure; self.detailsButton.buttonType=NSButtonTypeOnOff;
    [self.errorView addArrangedSubview:self.detailsButton];
    self.detailsScroll=[NSScrollView new]; self.detailsScroll.hasVerticalScroller=YES;
    self.detailsScroll.borderType=NSBezelBorder;
    self.detailsText=[[NSTextView alloc] initWithFrame:NSMakeRect(0,0,600,220)]; self.detailsText.editable=NO; self.detailsText.selectable=YES;
    self.detailsText.font=[NSFont systemFontOfSize:12]; self.detailsText.textColor=NSColor.labelColor;
    self.detailsText.textContainerInset=NSMakeSize(8,8); self.detailsText.verticallyResizable=YES; self.detailsText.horizontallyResizable=NO;
    self.detailsText.minSize=NSMakeSize(0,220); self.detailsText.maxSize=NSMakeSize(CGFLOAT_MAX,CGFLOAT_MAX);
    self.detailsText.autoresizingMask=NSViewWidthSizable; self.detailsText.textContainer.widthTracksTextView=YES;
    self.detailsScroll.documentView=self.detailsText;
    [self.errorView addArrangedSubview:self.detailsScroll];
    [self.detailsScroll.widthAnchor constraintEqualToAnchor:self.errorView.widthAnchor].active=YES;
    [self.detailsScroll.heightAnchor constraintEqualToConstant:220].active=YES;
    [self.errorView addArrangedSubview:[NSButton buttonWithTitle:@"Copy Details" target:self action:@selector(copyErrorDetails:)]];
    [stack addArrangedSubview:self.errorView];
    [self renderError];
}
- (void)renderError {
    self.errorView.hidden=self.internalError==nil;
    self.detailsScroll.hidden=!self.detailsExpanded;
    self.errorView.arrangedSubviews.lastObject.hidden=!self.detailsExpanded;
    self.detailsButton.state=self.detailsExpanded ? NSControlStateValueOn : NSControlStateValueOff;
    self.detailsButton.title=self.detailsExpanded ? @"Hide details" : @"See details…";
    NSString *text=MCD2ErrorText(self.internalError);
    // Specific validator output stays local; exported diagnostics use only catalog text and numbers.
    if (self.localErrorDetail.length) text=[text stringByAppendingFormat:@"\n\nLocal check result: %@",self.localErrorDetail];
    self.detailsText.string=text;
    [self resizeCopySheet];
}
- (void)toggleErrorDetails:(id)sender { self.detailsExpanded=!self.detailsExpanded; [self renderError]; }
- (void)copyErrorDetails:(id)sender {
    [NSPasteboard.generalPasteboard clearContents];
    [NSPasteboard.generalPasteboard setString:MCD2ErrorText(self.internalError) forType:NSPasteboardTypeString];
}
- (void)clearError { self.internalError=nil; self.localErrorDetail=nil; self.detailsExpanded=NO; [self renderError]; }
- (void)reportError:(NSInteger)code exit:(NSNumber *)exitCode system:(NSNumber *)systemCode local:(NSString *)local {
    NSDictionary *record=MCD2ErrorRecord(code,exitCode,systemCode);
    if (!record) return;
    BOOL changed=![record isEqual:self.internalError];
    self.internalError=record; self.localErrorDetail=local;
    if (changed) self.detailsExpanded=NO;
    self.status.stringValue=[NSString stringWithFormat:@"Internal Error: %04ld — %@",code,MCD2ErrorCatalog()[@(code)][@"observed"]];
    self.status.hidden=NO;
    // A small last-error record, without paths, account data or raw process output.
    if (changed && support.length && ![[NSFileManager.defaultManager attributesOfItemAtPath:support error:nil][NSFileType] isEqual:NSFileTypeSymbolicLink]) {
        if ([NSFileManager.defaultManager createDirectoryAtPath:support withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:nil]) {
            NSData *data=[NSJSONSerialization dataWithJSONObject:record options:0 error:nil];
            NSString *path=[support stringByAppendingPathComponent:@"internal-error.json"];
            if (![[NSFileManager.defaultManager attributesOfItemAtPath:path error:nil][NSFileType] isEqual:NSFileTypeSymbolicLink]) {
                [data writeToFile:path options:NSDataWritingAtomic error:nil];
                [NSFileManager.defaultManager setAttributes:@{NSFilePosixPermissions:@0600} ofItemAtPath:path error:nil];
            }
        }
    }
    [self renderError];
}
- (void)showSetup:(BOOL)setup {
    if (self.selectionPanel) [self dismissCopySheet];
    if (!setup) self.changingBottle = NO;
    self.internalError = nil; self.localErrorDetail = nil; self.detailsExpanded = NO;
    self.setupMode = setup;
    self.setupAttempted = NO;
    self.accountLabel = nil;
    self.crossoverLabel = nil; self.chooseCrossoverButton = nil;
    self.closeButton = nil;
    self.changeBottleButton = nil;
    self.choose = nil; self.gameLabel = nil; self.bottles = nil; self.stores = nil; self.license = nil; self.gameCopy = nil; self.gameSelection = nil;
    [self.scroll removeFromSuperview];
    NSRect available = (self.window.screen ?: NSScreen.mainScreen).visibleFrame;
    NSRect frame = self.window.frame; frame.size = NSMakeSize(700,MIN(setup ? 610 : 480, available.size.height - 40));
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
    self.troubleshootingButton = [NSButton buttonWithTitle:L(@"Troubleshooting…") target:self action:@selector(openTroubleshooting:)];
    self.troubleshootingButton.controlSize = NSControlSizeSmall; self.troubleshootingButton.font = [NSFont systemFontOfSize:11];
    self.troubleshootingButton.toolTip = L(@"Record a problem and save troubleshooting logs");
    [self.troubleshootingButton setContentHuggingPriority:NSLayoutPriorityRequired forOrientation:NSLayoutConstraintOrientationHorizontal];
    NSStackView *heading = [NSStackView stackViewWithViews:@[icon,label(setup ? L(@"Set Up MCD2 Crossover") : @"Minecraft Dungeons II",24,NSFontWeightSemibold),[NSView new],self.troubleshootingButton]];
    heading.orientation = NSUserInterfaceLayoutOrientationHorizontal; heading.spacing = 16; [self.stack addArrangedSubview:heading];
    BOOL launcher = [settings()[@"store"] isEqualToString:@"launcher"];
    [self.stack addArrangedSubview:label(setup ? L(@"Choose your CrossOver bottle and installed game copy. Changing copies keeps your Microsoft sign-in saved.") : (launcher ? L(@"Minecraft Launcher support is experimental. Play opens the selected copy in CrossOver; Microsoft still checks game ownership.") : L(@"After setup and your first sign-in, you can play directly from Steam in the selected bottle. This app doesn’t need to stay open.")),13,NSFontWeightRegular)];
    self.accountLabel = label(@"",13,NSFontWeightMedium); [self.stack addArrangedSubview:self.accountLabel];
    [self refreshAccount];
    if (setup) {
        [self addCopySelectionControlsToStack:self.stack];
        [self.stack addArrangedSubview:label(L(@"Quit the game first. Setup backs up replaced files and leaves saves alone. For Steam copies, it also restarts Steam."),13,NSFontWeightRegular)];
        NSButton *view = [NSButton buttonWithTitle:L(@"View Microsoft License…") target:self action:@selector(viewLicense:)];
        [self.stack addArrangedSubview:[self buttonRow:@[view]]];
        self.license = [NSButton checkboxWithTitle:L(@"I accept the Microsoft GDK license") target:self action:@selector(licenseChanged:)];
        [self.stack addArrangedSubview:self.license];
    } else {
        [self addCrossOverSelectionToStack:self.stack];
        NSString *bottle = settings()[@"bottle"];
        self.changeBottleButton = [NSButton buttonWithTitle:L(@"Change Game Copy") target:self action:@selector(changeBottle:)];
        [self.stack addArrangedSubview:[self buttonRow:@[label([L(@"CrossOver bottle: ") stringByAppendingString:bottle ?: L(@"Not selected")],13,NSFontWeightMedium),self.changeBottleButton]]];
        [self.stack addArrangedSubview:label(L(@"Saved sign-in renews in the background. If the game asks you to sign in again, click Play to reconnect."),13,NSFontWeightRegular)];
    }
    self.status = label(setup ? L(@"If Visual C++ is missing, Microsoft’s installer will open for you to finish.") : L(@"To change Microsoft accounts, quit the game and choose Sign Out."),13,NSFontWeightRegular);
    self.status.accessibilityLabel = L(@"Status"); [self.stack addArrangedSubview:self.status];
    [self addErrorDetailsToStack:self.stack];
    self.progress = [NSProgressIndicator new]; self.progress.style = NSProgressIndicatorStyleBar; self.progress.indeterminate = YES; self.progress.hidden = YES; [self.stack addArrangedSubview:self.progress];
    self.secondary = [NSButton buttonWithTitle:setup ? L(@"Cancel") : L(@"Sign Out") target:self action:setup ? @selector(cancel:) : @selector(signOut:)];
    self.primary = [MCD2SetupButton buttonWithTitle:setup ? L(@"Set Up") : L(@"Play") target:self action:setup ? @selector(install:) : @selector(play:)]; self.primary.keyEquivalent = @"\r";
    __weak MCD2App *weakSelf = self;
    ((MCD2SetupButton *)self.primary).blockedAttempt = ^{ [weakSelf explainBlockedSetup]; };
    self.secondary.keyEquivalent = setup ? @"\e" : @"";
    NSView *actions = [NSView new]; self.primary.translatesAutoresizingMaskIntoConstraints = NO; self.secondary.translatesAutoresizingMaskIntoConstraints = NO;
    [actions addSubview:self.primary]; [actions addSubview:self.secondary]; [self.stack addArrangedSubview:actions];
    [NSLayoutConstraint activateConstraints:@[[actions.heightAnchor constraintEqualToConstant:32], [self.primary.trailingAnchor constraintEqualToAnchor:actions.trailingAnchor], [self.primary.centerYAnchor constraintEqualToAnchor:actions.centerYAnchor], [self.secondary.centerYAnchor constraintEqualToAnchor:actions.centerYAnchor], [self.secondary.trailingAnchor constraintEqualToAnchor:self.primary.leadingAnchor constant:-12], [self.primary.widthAnchor constraintGreaterThanOrEqualToConstant:100], [self.secondary.widthAnchor constraintGreaterThanOrEqualToConstant:100]]];
    if (!setup) {
        self.closeButton = [NSButton buttonWithTitle:L(@"Close Window") target:self action:@selector(closeWindow:)];
        self.closeButton.keyEquivalent = @"\e"; self.closeButton.translatesAutoresizingMaskIntoConstraints = NO; [actions addSubview:self.closeButton];
        [NSLayoutConstraint activateConstraints:@[[self.closeButton.centerYAnchor constraintEqualToAnchor:actions.centerYAnchor], [self.closeButton.trailingAnchor constraintEqualToAnchor:self.secondary.leadingAnchor constant:-12], [self.closeButton.widthAnchor constraintGreaterThanOrEqualToConstant:116]]];
    }
    for (NSView *view in self.stack.arrangedSubviews) [view.widthAnchor constraintEqualToAnchor:self.stack.widthAnchor].active = YES;
    if (setup) {
        [self selectSavedCopy];
    }
    [document layoutSubtreeIfNeeded];
    [self refreshRecording:nil];
}
- (void)addCrossOverSelectionToStack:(NSStackView *)stack {
    self.crossoverLabel = label(@"",13,NSFontWeightRegular);
    self.crossoverLabel.selectable = YES;
    self.chooseCrossoverButton = [NSButton buttonWithTitle:@"Choose CrossOver…" target:self action:@selector(chooseCrossOver:)];
    [stack addArrangedSubview:[self buttonRow:@[label(@"CrossOver App",13,NSFontWeightMedium),self.chooseCrossoverButton]]];
    [stack addArrangedSubview:self.crossoverLabel];
    [self refreshCrossOverLabel];
}
- (void)refreshCrossOverLabel {
    self.crossoverLabel.stringValue = self.crossoverApp.length ? self.crossoverApp.stringByAbbreviatingWithTildeInPath : L(@"Not selected");
}
- (void)chooseCrossOver:(id)sender {
    if (self.working) return;
    NSOpenPanel *panel = [NSOpenPanel openPanel];
    panel.title = @"Choose CrossOver";
    panel.message = @"Select the CrossOver app you use for this game. Its name and location can be different.";
    panel.allowedContentTypes = @[UTTypeApplicationBundle];
    panel.canChooseFiles = YES; panel.canChooseDirectories = NO;
    panel.treatsFilePackagesAsDirectories = NO; panel.allowsMultipleSelection = NO;
    panel.directoryURL = [NSURL fileURLWithPath:self.crossoverApp.stringByDeletingLastPathComponent ?: @"/Applications"];
    [panel beginSheetModalForWindow:self.selectionPanel ?: self.window completionHandler:^(NSModalResponse result) {
        if (result != NSModalResponseOK) return;
        self.crossoverApp = panel.URL.path.stringByResolvingSymlinksInPath;
        self.crossoverPreferenceError = nil;
        if (!MCD2CrossOverError(self.crossoverApp)) {
            NSError *error = nil;
            BOOL saved = [NSFileManager.defaultManager createDirectoryAtPath:support withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:&error];
            NSData *data = [NSJSONSerialization dataWithJSONObject:@{@"path":self.crossoverApp} options:0 error:&error];
            if (saved) saved = [data writeToFile:[support stringByAppendingPathComponent:@"crossover-app.json"] options:NSDataWritingAtomic error:&error];
            if (!saved) self.crossoverPreferenceError = [@"Could not save the CrossOver selection: " stringByAppendingString:error.localizedDescription ?: @"Unknown error"];
        }
        if (!self.setupMode) { [self showSetup:YES]; }
        [self refreshCrossOverLabel]; [self licenseChanged:nil]; [self resizeCopySheet];
    }];
}
- (void)addCopySelectionControlsToStack:(NSStackView *)stack {
    [self addCrossOverSelectionToStack:stack];
    self.bottles = [NSPopUpButton new]; self.bottles.target = self; self.bottles.action = @selector(bottleChanged:); self.bottles.accessibilityLabel = L(@"CrossOver bottle");
    NSMutableArray *names = [NSMutableArray new];
    for (NSString *name in [NSFileManager.defaultManager contentsOfDirectoryAtPath:self.bottleRoot error:nil])
        if (exists([[self.bottleRoot stringByAppendingPathComponent:name] stringByAppendingPathComponent:@"cxbottle.conf"])) [names addObject:name];
    [names sortUsingSelector:@selector(localizedStandardCompare:)]; [self.bottles addItemsWithTitles:names];
    NSString *savedBottle = settings()[@"bottle"];
    if ([names containsObject:savedBottle]) [self.bottles selectItemWithTitle:savedBottle];
    else if ([names containsObject:@"Steam"]) [self.bottles selectItemWithTitle:@"Steam"];
    NSStackView *row = [NSStackView stackViewWithViews:@[label(L(@"CrossOver Bottle"),13,NSFontWeightMedium),self.bottles]];
    row.orientation = NSUserInterfaceLayoutOrientationHorizontal; row.spacing = 16; [self.bottles.widthAnchor constraintGreaterThanOrEqualToConstant:260].active = YES;
    [stack addArrangedSubview:row];
    self.stores = [NSPopUpButton new]; [self.stores addItemsWithTitles:@[@"Steam",L(@"Minecraft Launcher (experimental)")]];
    self.stores.target = self; self.stores.action = @selector(storeChanged:); self.stores.accessibilityLabel = L(@"Launcher:");
    [self.stores selectItemAtIndex:[settings()[@"store"] isEqualToString:@"launcher"] ? 1 : 0];
    [stack addArrangedSubview:[self buttonRow:@[label(L(@"Launcher:"),13,NSFontWeightMedium),self.stores]]];
    self.gameLabel = label(@"",13,NSFontWeightRegular); self.gameLabel.selectable = YES; [stack addArrangedSubview:self.gameLabel];
    self.choose = [NSButton buttonWithTitle:L(@"Browse Game Copy…") target:self action:@selector(chooseFolder:)];
    [stack addArrangedSubview:[self buttonRow:@[self.choose]]];
}
- (void)selectSavedCopy {
    [self bottleChanged:nil];
    NSDictionary *saved = settings();
    if ([saved[@"bottle"] isEqual:self.bottles.titleOfSelectedItem] && [saved[@"game"] isKindOfClass:NSString.class]) {
        self.game = saved[@"game"]; self.gameSelection = self.game;
        if ([saved[@"binary"] isKindOfClass:NSString.class] && [saved[@"game_exe"] isKindOfClass:NSString.class])
            self.gameSelection = [saved[@"binary"] stringByAppendingPathComponent:[[saved[@"game_exe"] stringByReplacingOccurrencesOfString:@"\\" withString:@"/"] lastPathComponent]];
        [self updateGame];
    }
}
- (BOOL)isSavedCopySelected {
    NSDictionary *saved = settings();
    return [self.crossoverApp.stringByResolvingSymlinksInPath isEqual:[(saved[@"crossover_app"] ?: @"/Applications/CrossOver.app") stringByResolvingSymlinksInPath]]
        && [self.bottles.titleOfSelectedItem isEqual:saved[@"bottle"]]
        && [self.gameCopy[@"root"] isEqual:saved[@"game"]]
        && [self.gameCopy[@"binary"] isEqual:saved[@"binary"]]
        && [saved[@"store"] isEqual:(self.stores.indexOfSelectedItem == 1 ? @"launcher" : @"steam")];
}
- (void)resizeCopySheet {
    if (!self.selectionPanel) return;
    [self.selectionPanel.contentView layoutSubtreeIfNeeded];
    [self.selectionPanel setContentSize:NSMakeSize(650,MAX(280,ceil(self.selectionStack.fittingSize.height)+48))];
}
- (void)showCopySheet {
    if (self.working || self.setupMode || self.window.attachedSheet) return;
    NSMutableDictionary *state = [NSMutableDictionary new];
    for (NSString *key in @[@"internalError",@"localErrorDetail",@"errorView",@"detailsButton",@"detailsScroll",@"detailsText",@"detailsExpanded",@"crossoverLabel",@"chooseCrossoverButton",@"bottles",@"stores",@"gameLabel",@"status",@"choose",@"license",@"primary",@"secondary",@"closeButton",@"changeBottleButton",@"progress",@"game",@"gameSelection",@"gameCopy",@"setupMode",@"changingBottle"]) {
        state[key] = [self valueForKey:key] ?: NSNull.null;
    }
    self.homeUIState = state;
    self.internalError = nil; self.localErrorDetail = nil; self.detailsExpanded = NO;
    self.setupMode = YES; self.changingBottle = YES; self.setupAttempted = NO;
    self.closeButton = nil; self.changeBottleButton = nil;
    NSPanel *panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0,0,650,340) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
    panel.title = L(@"Change Game Copy"); self.selectionPanel = panel;
    NSStackView *stack = [NSStackView new]; self.selectionStack = stack;
    stack.orientation = NSUserInterfaceLayoutOrientationVertical; stack.alignment = NSLayoutAttributeLeading; stack.spacing = 16;
    stack.translatesAutoresizingMaskIntoConstraints = NO; [panel.contentView addSubview:stack];
    [NSLayoutConstraint activateConstraints:@[[stack.leadingAnchor constraintEqualToAnchor:panel.contentView.leadingAnchor constant:24], [stack.trailingAnchor constraintEqualToAnchor:panel.contentView.trailingAnchor constant:-24], [stack.topAnchor constraintEqualToAnchor:panel.contentView.topAnchor constant:24]]];
    [stack addArrangedSubview:label(L(@"Choose your CrossOver bottle and installed game copy. Changing copies keeps your Microsoft sign-in saved."),13,NSFontWeightRegular)];
    [self addCopySelectionControlsToStack:stack];
    [stack addArrangedSubview:label(L(@"Quit the game first. Setup backs up replaced files and leaves saves alone. For Steam copies, it also restarts Steam."),13,NSFontWeightRegular)];
    // Setup already accepted these terms. Ask again only if this build carries different terms.
    NSData *bundledLicense = [NSData dataWithContentsOfFile:[resources stringByAppendingPathComponent:@"licenses/Microsoft-GDK-LICENSE.md"]];
    NSData *installedLicense = [NSData dataWithContentsOfFile:[support stringByAppendingPathComponent:@"runtime/Microsoft-GDK-LICENSE.md"]];
    self.selectionLicenseAccepted = bundledLicense.length && [bundledLicense isEqual:installedLicense];
    self.license = nil;
    self.status = label(@"",13,NSFontWeightRegular); self.status.accessibilityLabel = L(@"Status"); self.status.hidden = YES;
    [stack addArrangedSubview:self.status];
    [self addErrorDetailsToStack:stack];
    self.progress = [NSProgressIndicator new]; self.progress.style = NSProgressIndicatorStyleBar; self.progress.indeterminate = YES; self.progress.hidden = YES;
    [stack addArrangedSubview:self.progress];
    self.secondary = [NSButton buttonWithTitle:L(@"Cancel") target:self action:@selector(cancel:)]; self.secondary.keyEquivalent = @"\e";
    self.primary = [MCD2SetupButton buttonWithTitle:L(@"Done") target:self action:@selector(commitCopy:)]; self.primary.keyEquivalent = @"\r";
    __weak MCD2App *weakSelf = self;
    ((MCD2SetupButton *)self.primary).blockedAttempt = ^{ [weakSelf explainBlockedSetup]; };
    NSStackView *actions = [NSStackView stackViewWithViews:@[[NSView new],self.secondary,self.primary]];
    actions.orientation = NSUserInterfaceLayoutOrientationHorizontal; actions.spacing = 12; actions.alignment = NSLayoutAttributeCenterY;
    for (NSButton *button in @[self.secondary,self.primary]) {
        [button.widthAnchor constraintGreaterThanOrEqualToConstant:88].active = YES;
        [button setContentHuggingPriority:NSLayoutPriorityRequired forOrientation:NSLayoutConstraintOrientationHorizontal];
    }
    [stack addArrangedSubview:actions];
    for (NSView *view in stack.arrangedSubviews) [view.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active = YES;
    [self selectSavedCopy];
    [self resizeCopySheet];
    [self.window beginSheet:panel completionHandler:nil];
}
- (void)dismissCopySheet {
    if (!self.selectionPanel) return;
    [self.window endSheet:self.selectionPanel]; [self.selectionPanel orderOut:nil];
    self.selectionPanel = nil; self.selectionStack = nil;
    NSDictionary *state = self.homeUIState; self.homeUIState = nil;
    for (NSString *key in state) [self setValue:state[key] == NSNull.null ? nil : state[key] forKey:key];
    self.selectionLicenseAccepted = NO;
    [self refreshCrossOverLabel];
}
- (void)commitCopy:(id)sender {
    if (self.working || !self.selectionPanel || !self.primary.enabled) return;
    if ([self isSavedCopySelected]) { [self dismissCopySheet]; return; }
    self.launchAfterSetup = NO;
    if (self.selectionLicenseAccepted) { [self startSetup:NO]; return; }
    NSString *text = [NSString stringWithContentsOfFile:[resources stringByAppendingPathComponent:@"licenses/Microsoft-GDK-LICENSE.md"] encoding:NSUTF8StringEncoding error:nil];
    if (!text.length) { self.status.stringValue = L(@"License file missing. Download the app again."); self.status.hidden = NO; [self resizeCopySheet]; return; }
    NSAlert *alert = [NSAlert new]; alert.messageText = L(@"Microsoft GDK License");
    NSScrollView *scroll = [[NSScrollView alloc] initWithFrame:NSMakeRect(0,0,500,240)]; scroll.hasVerticalScroller = YES; scroll.borderType = NSBezelBorder;
    NSTextView *view = [[NSTextView alloc] initWithFrame:NSMakeRect(0,0,480,240)]; view.editable = NO; view.font = [NSFont systemFontOfSize:13]; view.string = text; view.verticallyResizable = YES; view.textContainer.widthTracksTextView = YES; scroll.documentView = view;
    alert.accessoryView = scroll;
    [alert addButtonWithTitle:L(@"I accept the Microsoft GDK license")]; [alert addButtonWithTitle:L(@"Cancel")];
    [alert beginSheetModalForWindow:self.selectionPanel completionHandler:^(NSModalResponse response) {
        if (response == NSAlertFirstButtonReturn) { self.selectionLicenseAccepted = YES; [self startSetup:NO]; }
    }];
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
    self.gameLabel.stringValue = [L(@"Game folder: ") stringByAppendingString:[(self.gameSelection ?: self.game ?: @"—") stringByAbbreviatingWithTildeInPath]];
    if (valid) self.status.stringValue = self.stores.indexOfSelectedItem == 1 ? L(@"Experimental: requires a Launcher-owned copy. Windows Store licensing may prevent it from running in CrossOver.") : L(@"If Visual C++ is missing, Microsoft’s installer will open for you to finish.");
    [self recordEvent:@"copy_checked" outcome:valid ? @"ready" : @"failed"];
    [self licenseChanged:nil];
    [self resizeCopySheet];
}
- (void)explainBlockedSetup {
    if (!self.setupMode || self.working) return;
    self.setupAttempted = YES;
    [self licenseChanged:nil];
}
- (void)licenseChanged:(id)sender {
    if (!self.setupMode || self.working) return;
    NSString *blocked = nil; NSInteger errorCode = 0;
    if (self.runtimeError) blocked = self.runtimeError;
    else if (self.crossoverPreferenceError) blocked = self.crossoverPreferenceError;
    else if (MCD2CrossOverError(self.crossoverApp)) blocked = MCD2CrossOverError(self.crossoverApp);
    else if (!self.bottles.numberOfItems)
        blocked = L(@"Install the game in a CrossOver bottle, then reopen this app.");
    else if (!self.gameCopy)
        blocked = self.selectionError ?: L(@"Game copy not found. Browse to its installed folder or Shipping.exe file.");
    else if (!self.selectionPanel && self.license.state != NSControlStateValueOn)
        blocked = @"Accept the Microsoft GDK license to enable Set Up.";
    else if (!self.selectionPanel && self.changingBottle && [self isSavedCopySelected] && [self.bottles.titleOfSelectedItem isEqual:settings()[@"bottle"]]
        && [self.game isEqual:settings()[@"game"]]
        && (!settings()[@"binary"] || [self.gameCopy[@"binary"] isEqual:settings()[@"binary"]])
        && ((self.stores.indexOfSelectedItem == 1) == [settings()[@"store"] isEqualToString:@"launcher"]))
        blocked = @"This game copy is already selected. Choose another copy or click Cancel.";
    if (blocked) {
        if (self.runtimeError) errorCode=1101;
        else if (self.crossoverPreferenceError) errorCode=1004;
        else if (MCD2CrossOverError(self.crossoverApp)) errorCode=[self crossOverErrorCode];
        else if (!self.bottles.numberOfItems) errorCode=1201;
        else if (!self.gameCopy) errorCode=1202;
        else if (!self.selectionPanel && self.license.state != NSControlStateValueOn) errorCode=1203;
        else errorCode=1204;
    }
    self.primary.enabled = blocked == nil;
    self.status.stringValue = (self.setupAttempted ? blocked : nil) ?: (self.stores.indexOfSelectedItem == 1 ? L(@"Experimental: requires a Launcher-owned copy. Windows Store licensing may prevent it from running in CrossOver.") : L(@"If Visual C++ is missing, Microsoft’s installer will open for you to finish."));
    if (self.setupAttempted && blocked) [self reportError:errorCode exit:nil system:nil local:blocked];
    else [self clearError];
    if (self.selectionPanel && self.setupAttempted && blocked) self.status.hidden = NO;
    [self resizeCopySheet];
}
- (void)storeChanged:(id)sender { [self updateGame]; }
- (NSDictionary *)inspectCopy:(NSString *)path store:(NSString *)store {
    NSString *error=nil;
    NSDictionary *copy=MCD2InspectCopy(path,store,&error);
    self.selectionError=error;
    return copy;
}
- (void)chooseFolder:(id)sender {
    if (self.working) return;
    if (!self.setupMode) { [self showCopySheet]; if (!self.selectionPanel) return; }
    NSOpenPanel *panel = [NSOpenPanel openPanel]; panel.title = L(@"Choose Minecraft Dungeons II");
    panel.message = L(@"Choose the installed Minecraft Dungeons II folder or its Dungeons Shipping.exe file.");
    panel.canChooseFiles = YES; panel.canChooseDirectories = YES; panel.allowsMultipleSelection = NO;
    panel.directoryURL = [NSURL fileURLWithPath:self.game ?: settings()[@"game"] ?: self.bottleRoot];
    [panel beginSheetModalForWindow:self.selectionPanel ?: self.window completionHandler:^(NSModalResponse result) {
        if (result == NSModalResponseOK) {
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
    NSPanel *panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0,0,620,440) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO]; panel.title = L(@"Microsoft GDK License");
    NSScrollView *scroll = [[NSScrollView alloc] initWithFrame:NSMakeRect(20,60,580,360)]; scroll.hasVerticalScroller = YES; scroll.borderType = NSBezelBorder;
    NSTextView *view = [[NSTextView alloc] initWithFrame:NSMakeRect(0,0,560,360)]; view.editable = NO; view.font = [NSFont systemFontOfSize:13]; view.string = text ?: L(@"License file missing. Download the app again."); view.verticallyResizable = YES; view.textContainer.widthTracksTextView = YES; scroll.documentView = view;
    [panel.contentView addSubview:scroll];
    NSButton *done = [NSButton buttonWithTitle:L(@"Done") target:self action:@selector(closeLicense:)]; done.frame = NSMakeRect(512,16,88,28); done.keyEquivalent = @"\r"; [panel.contentView addSubview:done];
    [self.window beginSheet:panel completionHandler:nil];
}
- (void)closeLicense:(NSButton *)sender { [self.window endSheet:sender.window]; }
- (void)install:(id)sender {
    if (self.working) return;
    [self explainBlockedSetup];
    if (!self.primary.enabled) return;
    if (![[CrossoverUpdater shared] allowsNewOperation]) return;
    self.launchAfterSetup = NO;
    [self startSetup:NO];
}
- (void)startSetup:(BOOL)override {
    if (![[CrossoverUpdater shared] allowsNewOperation]) return;
    if (self.working || !self.setupMode || !self.primary.enabled) return;
    NSMutableArray *arguments = [@[@"-I",@"-B",[resources stringByAppendingPathComponent:@"scripts/install.py"],@"--bottle",self.bottles.titleOfSelectedItem,@"--game",self.gameCopy[@"executable"],@"--store",self.stores.indexOfSelectedItem == 1 ? @"launcher" : @"steam",@"--accept-gdk-license"] mutableCopy];
    if (override) [arguments addObject:@"--ignore-other-game-detection"];
    [self run:@"setup" executable:[resources stringByAppendingPathComponent:@"python/bin/python3"]
        arguments:arguments];
}
- (void)showRunningGame:(int)code output:(NSString *)output {
    NSArray *markers = @[@"MCD2_RUNNING_SELECTED",@"MCD2_RUNNING_SHARED_STEAM",@"MCD2_RUNNING_AMBIGUOUS"];
    if (![[output componentsSeparatedByCharactersInSet:NSCharacterSet.newlineCharacterSet] containsObject:markers[code-20]]) return;
    NSAlert *alert = [NSAlert new]; alert.messageText = L(@"Game Detected");
    alert.informativeText = code == 20 ? L(@"The selected game is running. Open it without reinstalling its files, or quit it and try setup again.")
        : (code == 21 ? L(@"Another game is using this Steam bottle.") : L(@"Setup couldn’t verify which game is running."));
    [alert addButtonWithTitle:L(@"Cancel")];
    [alert addButtonWithTitle:L(@"It isn’t open!")];
    NSDictionary *saved = settings();
    BOOL canOpen = code == 20 && [saved[@"game"] isEqual:self.game] && [saved[@"bottle"] isEqual:self.bottles.titleOfSelectedItem] && [saved[@"binary"] isEqual:self.gameCopy[@"binary"]]
        && [saved[@"store"] isEqual:(self.stores.indexOfSelectedItem == 1 ? @"launcher" : @"steam")];
    if (canOpen) [alert addButtonWithTitle:L(@"Open Game")];
    [alert beginSheetModalForWindow:self.selectionPanel ?: self.window completionHandler:^(NSModalResponse response) {
        if (response == NSAlertSecondButtonReturn) { self.launchAfterSetup = YES; [self startSetup:code != 20]; }
        else if (canOpen && response == NSAlertThirdButtonReturn) { [self showSetup:NO]; [self play:nil]; }
    }];
}
- (NSString *)setupError:(NSString *)output {
    NSString *text = [output stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
    if ([text containsString:@"MCD2_RUNNING_SELECTED"]) return L(@"The selected game is still running. Quit it before replacing its files.");
    if ([text containsString:@"MCD2_RUNNING_SHARED_STEAM"]) return L(@"Another game is using this Steam bottle.");
    if ([text containsString:@"MCD2_RUNNING_AMBIGUOUS"]) return L(@"Setup couldn’t verify which game is running.");
    if (MCD2KnownText(text)) return L(text);
    if (text.length > 8192) text = [@"…\n" stringByAppendingString:[text substringFromIndex:text.length-8192]];
    return text.length ? text : L(@"Couldn’t finish setup. Save the logs and try again.");
}
- (void)play:(id)sender { if (![[CrossoverUpdater shared] allowsNewOperation]) return; if (!self.working && !self.setupMode) [self bridge:@"launch"]; }
- (void)signOut:(id)sender { if (!self.working && !self.setupMode) [self bridge:@"sign-out"]; }
- (void)stopGame:(id)sender {
    if (self.working || self.setupMode) return;
    NSAlert *alert = [NSAlert new]; alert.messageText = L(@"Force quit Minecraft Dungeons II?");
    alert.informativeText = L(@"Use this if the game is stuck. Unsaved progress may be lost.");
    [alert addButtonWithTitle:L(@"Cancel")]; [alert addButtonWithTitle:L(@"Force Quit")];
    [alert beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response) {
        if (response == NSAlertSecondButtonReturn) [self bridge:@"stop-game"];
    }];
}
- (void)bridge:(NSString *)command {
    NSString *crossoverError = self.crossoverPreferenceError ?: MCD2CrossOverError(self.crossoverApp);
    if (crossoverError) { [self reportError:self.crossoverPreferenceError ? 1004 : [self crossOverErrorCode] exit:nil system:nil local:crossoverError]; return; }
    if (self.runtimeError) { [self reportError:1101 exit:nil system:nil local:self.runtimeError]; return; }
    if (![command isEqualToString:@"stop-game"] && ![[CrossoverUpdater shared] allowsNewOperation]) return;
    NSString *bottle = settings()[@"bottle"];
    if (![bottle isKindOfClass:NSString.class]) { [self showSetup:YES]; return; }
    [self run:command executable:[support stringByAppendingPathComponent:@"python/bin/python"]
        arguments:@[@"-I",@"-B",[resources stringByAppendingPathComponent:@"helper/bridge.py"],command,@"--bottle",bottle]];
}
- (void)run:(NSString *)operation executable:(NSString *)executable arguments:(NSArray *)arguments {
    [self clearError];
    self.working = YES; self.cancelling = NO; self.operation = operation;
    self.chooseCrossoverButton.enabled = NO;
    self.primary.enabled = NO; self.bottles.enabled = NO; self.choose.enabled = NO; self.license.enabled = NO;
    self.changeBottleButton.enabled = NO;
    self.stores.enabled = NO;
    self.secondary.enabled = [operation isEqualToString:@"launch"];
    self.closeButton.enabled = [operation isEqualToString:@"launch"];
    if (self.secondary.enabled) { self.secondary.title = L(@"Cancel Launch"); self.secondary.action = @selector(cancel:); self.secondary.keyEquivalent = @"\e"; }
    self.progress.hidden = NO; [self.progress startAnimation:nil];
    if (self.selectionPanel) self.status.hidden = NO;
    self.status.stringValue = [operation isEqualToString:@"setup"] ? L(@"Setting up… If Microsoft’s Visual C++ installer opens, complete it to continue.")
        : [operation isEqualToString:@"launch"] ? L(@"Checking sign-in… If a code window appears, finish signing in and leave it open.")
        : [operation isEqualToString:@"stop-game"] ? L(@"Closing the stuck game…") : L(@"Removing your saved Microsoft sign-in…");
    [self resizeCopySheet];
    NSTask *task = [NSTask new]; self.task = task;
    NSMutableDictionary *environment = [NSProcessInfo.processInfo.environment mutableCopy];
    if (self.crossoverApp.length) environment[@"MCD2_CROSSOVER_APP"] = self.crossoverApp;
    task.environment = environment;
    task.executableURL = [NSURL fileURLWithPath:executable]; task.arguments = arguments;
    NSPipe *pipe = [NSPipe pipe]; task.standardOutput = pipe; task.standardError = pipe;
    NSError *error;
    if (![task launchAndReturnError:&error]) {
        [self finished:1 output:@""];
        [self reportError:2001 exit:nil system:@(error.code) local:nil]; return;
    }
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
    if ([self.operation isEqualToString:@"setup"] && code == 0) { BOOL launch = self.launchAfterSetup; self.launchAfterSetup = NO; [self showSetup:NO]; self.status.stringValue = L(@"Setup complete. Press Play to open the game."); if (launch) [self play:nil]; return; }
    self.chooseCrossoverButton.enabled = YES;
    self.primary.enabled = !self.setupMode; self.secondary.enabled = YES;
    self.closeButton.enabled = YES;
    self.changeBottleButton.enabled = YES;
    self.stores.enabled = YES;
    self.bottles.enabled = YES; self.choose.enabled = YES; self.license.enabled = YES;
    self.secondary.title = self.setupMode ? L(@"Cancel") : L(@"Sign Out");
    self.secondary.action = self.setupMode ? @selector(cancel:) : @selector(signOut:); self.secondary.keyEquivalent = self.setupMode ? @"\e" : @"";
    [self licenseChanged:nil];
    if (self.cancelling) { [self clearError]; self.status.stringValue = L(@"Launch cancelled."); }
    else if (code) {
        NSDictionary *detail=MCD2ParseError(output);
        NSInteger errorCode=[detail[@"code"] integerValue];
        if (!errorCode) errorCode=[self.operation isEqual:@"setup"] ? ((code>=20 && code<=22) ? 2101+code-20 : 2299) : [self.operation isEqual:@"sign-out"] ? 4001 : [self.operation isEqual:@"stop-game"] ? 4002 : 3199;
        [self reportError:errorCode exit:@(code) system:detail[@"system_code"] local:nil];
    }
    else if ([self.operation isEqualToString:@"sign-out"]) self.status.stringValue = L(@"Signed out. Your saved Microsoft credential and local session were removed. Play will ask you to sign in again.");
    else if ([self.operation isEqualToString:@"stop-game"]) self.status.stringValue = L(@"The game was stopped.");
    else self.status.stringValue = [settings()[@"store"] isEqualToString:@"launcher"] ? L(@"The selected game copy is opening in CrossOver. Launcher support is experimental.") : L(@"Steam is opening the game. You can close this app now.");
    [self refreshAccount];
    [self resizeCopySheet];
    if ([self.operation isEqualToString:@"setup"] && code >= 20 && code <= 22) [self showRunningGame:code output:output];
}
- (void)cancel:(id)sender {
    if (!self.working) {
        if (self.selectionPanel) { [self dismissCopySheet]; return; }
        if (self.setupMode && self.changingBottle) [self showSetup:NO];
        else [NSApp terminate:nil];
        return;
    }
    if (![self.operation isEqualToString:@"launch"]) return;
    self.cancelling = YES; self.status.stringValue = L(@"Cancelling launch…"); self.secondary.enabled = NO;
    if (self.task.running) [self.task terminate];
}
- (void)changeBottle:(id)sender {
    if (self.working || self.setupMode) return;
    [self showCopySheet];
}
- (void)repair:(id)sender { if (!self.working) { self.changingBottle = NO; [self showSetup:YES]; } }
- (void)closeWindow:(id)sender { [self.window performClose:sender]; }
- (void)recordEvent:(NSString *)step outcome:(NSString *)outcome {
    if (!self.recording || self.runtimeError) return;
    NSTask *task = [NSTask new]; task.executableURL = [NSURL fileURLWithPath:[resources stringByAppendingPathComponent:@"python/bin/python3"]];
    task.arguments = @[@"-I",@"-B",[resources stringByAppendingPathComponent:@"helper/diagnostics.py"],@"event",@"--step",step,@"--outcome",outcome];
    task.standardOutput = NSFileHandle.fileHandleWithNullDevice; task.standardError = NSFileHandle.fileHandleWithNullDevice;
    [task launchAndReturnError:nil];
}
- (void)openTroubleshooting:(id)sender {
    if (self.diagnosticPanel || self.window.attachedSheet) return;
    NSPanel *panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0,0,600,280) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
    panel.title = L(@"Troubleshooting"); self.diagnosticPanel = panel;
    self.logsSaved = NO;
    NSStackView *stack = [NSStackView new]; stack.orientation = NSUserInterfaceLayoutOrientationVertical; stack.alignment = NSLayoutAttributeLeading; stack.spacing = 14;
    stack.translatesAutoresizingMaskIntoConstraints = NO; [panel.contentView addSubview:stack];
    [NSLayoutConstraint activateConstraints:@[[stack.leadingAnchor constraintEqualToAnchor:panel.contentView.leadingAnchor constant:24], [stack.trailingAnchor constraintEqualToAnchor:panel.contentView.trailingAnchor constant:-24], [stack.topAnchor constraintEqualToAnchor:panel.contentView.topAnchor constant:20]]];
    [stack addArrangedSubview:label(L(@"Troubleshooting"),17,NSFontWeightSemibold)];
    if (self.internalError) {
        [stack addArrangedSubview:label([NSString stringWithFormat:@"Internal Error: %04ld",[self.internalError[@"code"] integerValue]],13,NSFontWeightMedium)];
        [stack addArrangedSubview:[NSButton buttonWithTitle:@"Copy Details" target:self action:@selector(copyErrorDetails:)]];
    }
    self.recordStatus = label(@"",13,NSFontWeightRegular); self.recordStatus.accessibilityLabel = L(@"Log recording status"); [stack addArrangedSubview:self.recordStatus];
    [stack addArrangedSubview:label(L(@"Setup and sign-in issues can be recorded here with the game closed."),13,NSFontWeightRegular)];
    self.recordButton = [NSButton buttonWithTitle:L(@"Start Recording") target:self action:@selector(toggleRecording:)];
    self.saveLogsButton = [NSButton buttonWithTitle:L(@"Save Logs…") target:self action:@selector(saveLogs:)];
    NSButton *done = [NSButton buttonWithTitle:L(@"Done") target:self action:@selector(closeTroubleshooting:)]; done.keyEquivalent = @"\e";
    [stack addArrangedSubview:[self buttonRow:@[self.recordButton,self.saveLogsButton,done]]];
    for (NSView *view in stack.arrangedSubviews) [view.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active = YES;
    [self updateRecording:@{@"active":@(self.recording)}];
    [stack layoutSubtreeIfNeeded];
    [panel setContentSize:NSMakeSize(600,MAX(240,stack.fittingSize.height+40))];
    [self.window beginSheet:panel completionHandler:nil]; [self refreshRecording:nil];
}
- (void)closeTroubleshooting:(id)sender {
    [self.window endSheet:self.diagnosticPanel]; self.diagnosticPanel = nil;
    self.recordButton = nil; self.saveLogsButton = nil; self.recordStatus = nil;
}
- (void)diagnostics:(NSString *)command output:(NSString *)path completion:(void (^)(NSDictionary *, BOOL))completion {
    if (self.runtimeError) { self.recordStatus.stringValue = self.runtimeError; completion(@{},NO); return; }
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
    self.recordButton.title = self.recording ? L(@"Stop Recording") : L(@"Start Recording");
    [self refreshAccount];
    if (!self.logsSaved || self.recording) self.recordStatus.stringValue = self.recording ? L(@"Recording. Reproduce the problem, then click Save Logs.") : L(@"For in-game problems, click on Start Recording and reproduce the problem in-game.");
    self.troubleshootingButton.toolTip = self.recording ? L(@"Recording troubleshooting logs — click to stop or save") : L(@"Record a problem and save troubleshooting logs");
    if (state[@"available"]) self.saveLogsButton.enabled = [state[@"available"] boolValue] || self.internalError != nil;
}
- (void)refreshRecording:(id)sender {
    if (self.diagnosticsBusy || self.runtimeError) return;
    [self diagnostics:@"status" output:nil completion:^(NSDictionary *state, BOOL ok) { if (ok) [self updateRecording:state]; }];
}
- (void)toggleRecording:(id)sender {
    if (self.diagnosticsBusy) return;
    [self diagnostics:self.recording ? @"stop" : @"start" output:nil completion:^(NSDictionary *state, BOOL ok) {
        if (ok) { self.logsSaved = NO; [self updateRecording:state]; }
        else { [self reportError:5002 exit:nil system:nil local:nil]; self.recordStatus.stringValue = @"Internal Error: 5002 — Could not change recording. See details in the launcher."; }
    }];
}
- (void)saveLogs:(id)sender {
    if (self.diagnosticsBusy) return;
    NSSavePanel *panel = [NSSavePanel savePanel]; panel.title = L(@"Save Troubleshooting Logs");
    panel.message = L(@"Save logs to attach to a GitHub issue. Recording stops when saved.");
    NSDateFormatter *format = [NSDateFormatter new]; format.dateFormat = @"yyyy-MM-dd-HHmm";
    panel.nameFieldStringValue = [NSString stringWithFormat:@"MCD2-Crossover-Logs-%@.zip",[format stringFromDate:NSDate.date]];
    BOOL nativeOnly=self.runtimeError != nil;
    if (nativeOnly) panel.nameFieldStringValue=@"MCD2-Crossover-Error.txt";
    panel.allowedContentTypes = nativeOnly ? @[UTTypePlainText] : @[UTTypeZIP]; panel.canCreateDirectories = YES;
    [panel beginSheetModalForWindow:self.diagnosticPanel ?: self.window completionHandler:^(NSModalResponse response) {
        if (response != NSModalResponseOK) return;
        NSString *destination = panel.URL.path;
        if (nativeOnly) {
            if (!self.internalError) [self reportError:1101 exit:nil system:nil local:self.runtimeError];
            NSError *error=nil;
            BOOL ok=[MCD2ErrorText(self.internalError) writeToFile:destination atomically:YES encoding:NSUTF8StringEncoding error:&error];
            if (!ok) [self reportError:5001 exit:nil system:@(error.code) local:nil];
            self.recordStatus.stringValue=ok ? @"Error details saved." : @"Internal Error: 5001 — Could not save details.";
            return;
        }
        [self diagnostics:@"export" output:destination completion:^(NSDictionary *state, BOOL ok) {
            [self updateRecording:state];
            if (ok) {
                self.logsSaved = YES;
                NSString *text = L(@"Logs saved, attach to issue in the GitHub page.");
                NSMutableAttributedString *message = [[NSMutableAttributedString alloc] initWithString:text attributes:@{NSFontAttributeName:[NSFont systemFontOfSize:13],NSForegroundColorAttributeName:NSColor.labelColor}];
                [message addAttribute:NSLinkAttributeName value:[NSURL URLWithString:@"https://github.com/Wanzho/mcd2-crossover/issues/new/choose"] range:NSMakeRange(0,text.length)];
                self.recordStatus.allowsEditingTextAttributes = YES; self.recordStatus.selectable = YES; self.recordStatus.attributedStringValue = message;
            } else { [self reportError:5001 exit:nil system:nil local:nil]; self.recordStatus.stringValue = @"Internal Error: 5001 — Could not save logs. Copy Details is still available."; }
            if (ok) [NSWorkspace.sharedWorkspace activateFileViewerSelectingURLs:@[[NSURL fileURLWithPath:destination]]];
        }];
    }];
}
- (void)openHelp:(id)sender { [NSWorkspace.sharedWorkspace openURL:[NSURL URLWithString:@"https://github.com/Wanzho/mcd2-crossover#readme"]]; }
- (BOOL)validateMenuItem:(NSMenuItem *)item {
    if (item.action == @selector(play:) || item.action == @selector(signOut:) || item.action == @selector(stopGame:) || item.action == @selector(changeBottle:)) return !self.working && !self.setupMode;
    if (item.action == @selector(repair:)) return !self.working && !self.window.attachedSheet;
    if (item.action == @selector(chooseFolder:)) return !self.working && !self.window.attachedSheet;
    if (item.action == @selector(toggleRecording:) || item.action == @selector(saveLogs:)) return !self.diagnosticsBusy;
    return YES;
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if ([[CrossoverUpdater shared] mustWaitBeforeQuitting]) return NSTerminateCancel;
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
