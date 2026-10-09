// Setup discovery must not depend on executing the bundled interpreter.
static BOOL MCD2RegularFile(NSString *path) {
    BOOL directory = NO;
    return [NSFileManager.defaultManager fileExistsAtPath:path isDirectory:&directory] && !directory;
}
static NSDictionary *MCD2InspectCopy(NSString *selected, NSString *store, NSString **error) {
    if (error) *error = nil;
    if (!selected.length) { if(error)*error=@"No game folder is selected. Click Browse Game Copy to choose it."; return nil; }
    NSString *path = selected.stringByExpandingTildeInPath.stringByStandardizingPath.stringByResolvingSymlinksInPath;
    BOOL directory = NO;
    if (![NSFileManager.defaultManager fileExistsAtPath:path isDirectory:&directory]) {
        if(error)*error=[@"The selected game folder or executable no longer exists: " stringByAppendingString:path]; return nil;
    }
    NSString *chosen = directory ? nil : path;
    NSArray *names = @[@"dungeons.exe",@"dungeons-win64-shipping.exe",@"dungeons-wingdk-shipping.exe"];
    if (chosen && ![names containsObject:chosen.lastPathComponent.lowercaseString]) {
        if(error)*error=@"Choose the installed game folder or a Dungeons game executable."; return nil;
    }
    NSString *root = directory ? path : path.stringByDeletingLastPathComponent;
    NSArray *layouts = @[@[@"Win64",@"Dungeons-Win64-Shipping.exe",@"steam"],@[@"WinGDK",@"Dungeons-WinGDK-Shipping.exe",@"launcher"],@[@"WinGDK",@"Dungeons-Win64-Shipping.exe",@"launcher"]];
    for (int depth=0;depth<4;depth++,root=root.stringByDeletingLastPathComponent) {
        if (!MCD2RegularFile([root stringByAppendingPathComponent:@"MicrosoftGame.config"])) continue;
        NSMutableArray *copies=[NSMutableArray new];
        for (NSArray *layout in layouts) {
            NSString *binary=[[root stringByAppendingPathComponent:@"Dungeons/Binaries"] stringByAppendingPathComponent:layout[0]];
            NSString *executable=[binary stringByAppendingPathComponent:layout[1]];
            if (!MCD2RegularFile(executable)) continue;
            if (chosen && ![chosen.lastPathComponent.lowercaseString isEqual:@"dungeons.exe"] && ![chosen isEqual:executable]) continue;
            if ([store isEqual:@"steam"] && ![layout[2] isEqual:@"steam"]) continue;
            NSString *route=[store isEqual:@"auto"] ? layout[2] : store;
            [copies addObject:@{@"root":root,@"binary":binary,@"executable":executable,@"store":route,@"label":[route isEqual:@"steam"] ? @"Steam" : @"Minecraft Launcher (experimental)",@"experimental":@(![route isEqual:@"steam"])}];
        }
        if(copies.count==1) return copies[0];
        if(copies.count>1) { if(error)*error=@"More than one game executable was found. Choose the exact Shipping.exe file."; return nil; }
    }
    if(error)*error=[NSString stringWithFormat:@"Game copy not found in %@. The game folder must contain MicrosoftGame.config and Dungeons/Binaries/Win64/Dungeons-Win64-Shipping.exe (or a supported WinGDK executable).",path];
    return nil;
}
