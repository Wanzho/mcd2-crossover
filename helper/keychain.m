#import <Foundation/Foundation.h>
#import <Security/Security.h>
#import <LocalAuthentication/LocalAuthentication.h>

// Refresh secrets travel only through anonymous pipes and Keychain Services.
// Never put a secret in argv, environment variables, a file, or diagnostics.
int main(int argc, const char **argv) { @autoreleasepool {
    if (argc != 2) return 2;
    NSString *operation = @(argv[1]);
    if ([operation isEqualToString:@"self-test"]) {
        NSString *account = [[NSUUID UUID] UUIDString];
        NSDictionary *q = @{(__bridge id)kSecClass:(__bridge id)kSecClassGenericPassword,
            (__bridge id)kSecAttrService:@"org.dungeons-crossover.keychain-test",
            (__bridge id)kSecAttrAccount:account, (__bridge id)kSecAttrSynchronizable:@NO};
        NSMutableDictionary *add = [q mutableCopy];
        NSData *original = [@"synthetic-test-only" dataUsingEncoding:NSUTF8StringEncoding];
        add[(__bridge id)kSecValueData] = original;
        OSStatus a = SecItemAdd((__bridge CFDictionaryRef)add,NULL);
        NSMutableDictionary *read = [q mutableCopy]; read[(__bridge id)kSecReturnData] = @YES;
        CFTypeRef data = NULL; OSStatus b = SecItemCopyMatching((__bridge CFDictionaryRef)read,&data);
        BOOL matches = b == 0 && [CFBridgingRelease(data) isEqual:original];
        OSStatus c = SecItemUpdate((__bridge CFDictionaryRef)q,(__bridge CFDictionaryRef)@{(__bridge id)kSecValueData:original});
        OSStatus d = SecItemDelete((__bridge CFDictionaryRef)q);
        if(a || b || c || d || !matches) return 4;
        puts("Keychain add/read/update/delete passed with an isolated synthetic item.");
        return 0;
    }
    LAContext *context = [LAContext new];context.interactionNotAllowed = YES;
    NSMutableDictionary *query = [@{
        (__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
        (__bridge id)kSecAttrService: @"org.dungeons-crossover.microsoft-refresh",
        (__bridge id)kSecAttrAccount: @"default",
        (__bridge id)kSecAttrSynchronizable: @NO,
        (__bridge id)kSecUseAuthenticationContext: context
    } mutableCopy];
    OSStatus status;
    if ([operation isEqualToString:@"set"]) {
        NSData *secret = [[NSFileHandle fileHandleWithStandardInput] readDataToEndOfFile];
        if (!secret.length || secret.length > 32768) return 2;
        NSDictionary *attributes = @{(__bridge id)kSecValueData: secret};
        status = SecItemUpdate((__bridge CFDictionaryRef)query, (__bridge CFDictionaryRef)attributes);
        if (status == errSecItemNotFound) {
            [query addEntriesFromDictionary:attributes];
            query[(__bridge id)kSecAttrLabel] = @"Dungeons CrossOver Microsoft sign-in";
            status = SecItemAdd((__bridge CFDictionaryRef)query, NULL);
        }
    } else if ([operation isEqualToString:@"get"]) {
        query[(__bridge id)kSecReturnData] = @YES;
        query[(__bridge id)kSecMatchLimit] = (__bridge id)kSecMatchLimitOne;
        CFTypeRef value = NULL;
        status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &value);
        if (status == errSecSuccess && value) {
            NSData *data = CFBridgingRelease(value);
            [[NSFileHandle fileHandleWithStandardOutput] writeData:data];
        }
    } else if ([operation isEqualToString:@"delete"]) {
        status = SecItemDelete((__bridge CFDictionaryRef)query);
        if (status == errSecItemNotFound) status = errSecSuccess;
    } else return 2;
    if (status == errSecItemNotFound) return 3;
    if (status != errSecSuccess) {
        // Numeric OSStatus only. No query attributes, tokens, or account details.
        fprintf(stderr, "Keychain operation failed (%d).\n", (int)status);
        return 4;
    }
    return 0;
}}
