// Discover by bundle identity, not the app's filename. Do not execute candidates.
static NSString *MCD2CrossOverError(NSString *path) {
    if (!path.length) return @"CrossOver was not found. Click Choose CrossOver and select your CrossOver app.";
    NSDictionary *info = [NSDictionary dictionaryWithContentsOfFile:[path stringByAppendingPathComponent:@"Contents/Info.plist"]];
    if (![info[@"CFBundleIdentifier"] isEqual:@"com.codeweavers.CrossOver"])
        return [NSString stringWithFormat:@"Cannot read a CrossOver app at %@. Click Choose CrossOver to select it again.",path];
    if (![NSFileManager.defaultManager isExecutableFileAtPath:[path stringByAppendingPathComponent:@"Contents/SharedSupport/CrossOver/bin/wine"]])
        return @"The selected CrossOver app is missing its Wine executable. Choose another CrossOver app.";
    return nil;
}
static NSString *MCD2FindCrossOver(NSString *supportPath) {
    NSData *data = [NSData dataWithContentsOfFile:[supportPath stringByAppendingPathComponent:@"crossover-app.json"]];
    if (data) {
        id saved = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
        if ([saved isKindOfClass:NSDictionary.class] && [saved[@"path"] isKindOfClass:NSString.class]) return saved[@"path"];
        return nil;
    }
    for (NSString *folder in @[@"/Applications",[NSHomeDirectory() stringByAppendingPathComponent:@"Applications"]]) {
        NSMutableArray *names = [NSMutableArray arrayWithObject:@"CrossOver.app"];
        [names addObjectsFromArray:[[NSFileManager.defaultManager contentsOfDirectoryAtPath:folder error:nil] sortedArrayUsingSelector:@selector(localizedStandardCompare:)] ?: @[]];
        for (NSString *name in names) {
            if (![name.pathExtension.lowercaseString isEqual:@"app"]) continue;
            NSString *path = [folder stringByAppendingPathComponent:name];
            if (!MCD2CrossOverError(path)) return path;
        }
    }
    NSURL *registered = [NSWorkspace.sharedWorkspace URLForApplicationWithBundleIdentifier:@"com.codeweavers.CrossOver"];
    return registered && !MCD2CrossOverError(registered.path) ? registered.path : nil;
}
