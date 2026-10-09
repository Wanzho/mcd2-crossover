#import <sys/xattr.h>
#import <errno.h>
// The user has already opened this app through macOS. Verify its sealed bundle
// before preparing ONLY its embedded runtime; never alter system policy or games.
static NSString *MCD2PrepareEmbeddedRuntime(NSString *appPath, NSString *resourcePath) {
    NSTask *verify=[NSTask new];verify.executableURL=[NSURL fileURLWithPath:@"/usr/bin/codesign"];
    verify.arguments=@[@"--verify",@"--deep",@"--strict",appPath];
    NSPipe *output=[NSPipe pipe];verify.standardOutput=output;verify.standardError=output;
    NSError *error=nil;
    if(![verify launchAndReturnError:&error]) return [@"Could not verify the app: " stringByAppendingString:error.localizedDescription];
    NSData *data=[output.fileHandleForReading readDataToEndOfFile];[verify waitUntilExit];
    if(verify.terminationStatus) return [NSString stringWithFormat:@"App verification failed. Download a fresh copy.\n%@",[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] ?: @""];
    NSString *base=resourcePath.stringByResolvingSymlinksInPath;
    for(NSString *relative in @[@"python",@"build/keychain"]) {
        NSString *root=[base stringByAppendingPathComponent:relative];
        if(![NSFileManager.defaultManager fileExistsAtPath:root]) return [@"Bundled runtime is missing: " stringByAppendingString:relative];
        // Do not traverse a runtime root replaced by a symlink outside the bundle.
        if(![root.stringByResolvingSymlinksInPath hasPrefix:[base stringByAppendingString:@"/"]]) return @"The bundled runtime points outside this app. Download a fresh copy.";
        NSMutableArray *paths=[NSMutableArray arrayWithObject:root];
        __block NSError *walkError=nil;
        BOOL isDirectory=NO;[NSFileManager.defaultManager fileExistsAtPath:root isDirectory:&isDirectory];
        NSDirectoryEnumerator *items=isDirectory ? [NSFileManager.defaultManager enumeratorAtURL:[NSURL fileURLWithPath:root] includingPropertiesForKeys:nil options:0 errorHandler:^BOOL(NSURL *url,NSError *e){ walkError=e; return NO; }] : nil;
        for(NSURL *item in items) [paths addObject:item.path];
        if(walkError) return [@"Could not read the bundled runtime: " stringByAppendingString:walkError.localizedDescription];
        for(NSString *path in paths) {
            // NOFOLLOW keeps Wine-style or Python symlinks from affecting their targets.
            if(getxattr(path.fileSystemRepresentation,"com.apple.quarantine",NULL,0,0,XATTR_NOFOLLOW)<0) {
                if(errno==ENOATTR || errno==ENOTSUP) continue;
                return [NSString stringWithFormat:@"Could not inspect the bundled runtime (%@): %s",relative,strerror(errno)];
            }
            if(removexattr(path.fileSystemRepresentation,"com.apple.quarantine",XATTR_NOFOLLOW)!=0 && errno!=ENOATTR)
                return [NSString stringWithFormat:@"Could not prepare the bundled runtime: %s. Copy MCD2 Crossover to Applications, then reopen it.",strerror(errno)];
        }
    }
    return nil;
}
