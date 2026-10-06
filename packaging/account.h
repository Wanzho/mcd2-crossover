#import <Foundation/Foundation.h>
#include <stdint.h>
#include <string.h>

static NSString *MCD2AccountTag(NSString *directory) {
    NSString *tag = nil;
    NSString *path = [directory stringByAppendingPathComponent:@"session.bin"];
    NSDictionary *attributes = [NSFileManager.defaultManager attributesOfItemAtPath:path error:nil];
    // Read only the fixed display-name field, never token bytes.
    if (![NSFileManager.defaultManager fileExistsAtPath:[directory stringByAppendingPathComponent:@"signed-out"]]
        && [attributes[NSFileType] isEqual:NSFileTypeRegular] && [attributes[NSFileSize] unsignedLongLongValue] == 49736) {
        NSFileHandle *file = [NSFileHandle fileHandleForReadingAtPath:path];
        NSData *prefix = [file readDataUpToLength:192 error:nil]; [file closeFile];
        if (prefix.length == 192) {
            const uint8_t *bytes = prefix.bytes; uint64_t magic = 0, expiry = 0;
            memcpy(&magic,bytes,8); memcpy(&expiry,bytes+8,8);
            if (magic == 0x3247444952425858 && expiry > (NSDate.date.timeIntervalSince1970 + 11644473600.0)*10000000.0) {
                NSUInteger count = 0; while (count < 128 && bytes[64+count]) count++;
                if (count && count < 128) tag = [[NSString alloc] initWithBytes:bytes+64 length:count encoding:NSUTF8StringEncoding];
                if (tag && [tag rangeOfCharacterFromSet:NSCharacterSet.controlCharacterSet].location != NSNotFound) tag = nil;
            }
        }
    }
    return tag;
}
