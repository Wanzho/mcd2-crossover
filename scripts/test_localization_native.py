#!/usr/bin/env python3
"""Exercise native string lookup and account display with disposable data."""
import json
import subprocess
import tempfile
from pathlib import Path
from localize import native_resources, ROOT

SOURCE = r'''
#import <Foundation/Foundation.h>
#import "localization.h"
#import "account.h"
static void check(BOOL ok) { if (!ok) abort(); }
int main(int argc, char **argv) { @autoreleasepool {
    NSString *resources = @(argv[1]), *home = @(argv[2]);
    MCD2ConfigureLocalization(resources,[home stringByAppendingPathComponent:@"ui-language"]);
    NSDictionary *cases = @{@"en-GB":@"en",@"fr-CA":@"fr",@"es-MX":@"es-419",@"es-AR":@"es-419",@"es-ES":@"es-ES",@"pt-BR":@"pt-BR",@"pt-PT":@"pt-PT",@"zh-Hant-TW":@"zh-Hant",@"zh-Hans-CN":@"zh-Hans",@"zh_TW":@"zh-Hant",@"uk-UA":@"uk"};
    for (NSString *tag in cases) check([MCD2MatchLanguage(tag) isEqual:cases[tag]]);
    check(MCD2MatchLanguage(@"unrecognized") == nil);
    for (NSDictionary *language in MCD2Languages()) {
        NSString *locale = language[@"id"];
        check(MCD2SelectLanguage(locale)); check([MCD2CurrentLanguage() isEqual:locale]);
        NSString *path = [[resources stringByAppendingPathComponent:@"localization"] stringByAppendingPathComponent:[locale stringByAppendingString:@".json"]];
        NSDictionary *catalog = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:path] options:0 error:nil];
        for (NSString *key in catalog) check([L(key) isEqual:catalog[key]]);
        check([L(@"unknown key") isEqual:@"unknown key"]);
    }
    check(!MCD2SelectLanguage(@"../../invalid"));
    NSString *session = [home stringByAppendingPathComponent:@"session.bin"];
    NSMutableData *packet = [NSMutableData dataWithLength:49736];
    uint64_t magic = 0x3247444952425858, expiry = (NSDate.date.timeIntervalSince1970 + 11644473600.0 + 3600)*10000000.0;
    memcpy(packet.mutableBytes,&magic,8); memcpy((uint8_t*)packet.mutableBytes+8,&expiry,8);
    NSData *tag = [@"Synthetic玩家" dataUsingEncoding:NSUTF8StringEncoding];
    memcpy((uint8_t*)packet.mutableBytes+64,tag.bytes,tag.length);
    [packet writeToFile:session atomically:YES];
    check([MCD2AccountTag(home) isEqual:@"Synthetic玩家"]);
    NSString *signedOut = [home stringByAppendingPathComponent:@"signed-out"];
    [@"" writeToFile:signedOut atomically:YES encoding:NSUTF8StringEncoding error:nil];
    check(MCD2AccountTag(home) == nil); [NSFileManager.defaultManager removeItemAtPath:signedOut error:nil];
    expiry = 116444736000000000; memcpy((uint8_t*)packet.mutableBytes+8,&expiry,8);
    [packet writeToFile:session atomically:YES]; check(MCD2AccountTag(home) == nil);
    expiry = (NSDate.date.timeIntervalSince1970 + 11644473600.0 + 3600)*10000000.0;
    memcpy((uint8_t*)packet.mutableBytes+8,&expiry,8); memset((uint8_t*)packet.mutableBytes+64,0,128);
    memcpy((uint8_t*)packet.mutableBytes+64,"bad\nname",8); [packet writeToFile:session atomically:YES]; check(MCD2AccountTag(home) == nil);
    memset((uint8_t*)packet.mutableBytes+64,255,128); [packet writeToFile:session atomically:YES]; check(MCD2AccountTag(home) == nil);
    [packet setLength:192]; [packet writeToFile:session atomically:YES]; check(MCD2AccountTag(home) == nil);
    [NSFileManager.defaultManager removeItemAtPath:session error:nil]; check(MCD2AccountTag(home) == nil);
    return 0;
} }
'''


def main():
    with tempfile.TemporaryDirectory(prefix='mcd2-native-localization-') as folder:
        folder = Path(folder)
        resources = folder / 'Resources'; resources.mkdir()
        metadata = native_resources(resources)
        import shutil
        shutil.copytree(ROOT / 'localization', resources / 'localization')
        home = folder / 'user'; home.mkdir()
        source = folder / 'probe.m'; source.write_text(SOURCE)
        binary = folder / 'probe'
        subprocess.run(['clang', '-fobjc-arc', '-O2', '-framework', 'Foundation', '-I', str(ROOT / 'packaging'),
                        str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary), str(resources), str(home)], check=True)
        assert (home / 'ui-language').stat().st_mode & 0o777 == 0o600
        print(f'Native lookup passed for {len(metadata["languages"])} languages; regional selection and synthetic account display passed.')


if __name__ == '__main__':
    main()
