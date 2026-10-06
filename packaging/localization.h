#import <Foundation/Foundation.h>

static NSString *mcd2LocalizationResources;
static NSString *mcd2LanguagePreference;
static NSDictionary *mcd2LanguageMetadata;
static NSBundle *mcd2LanguageBundle;
static NSString *mcd2LanguageOverride;

static NSArray<NSDictionary *> *MCD2Languages(void) {
    id languages = mcd2LanguageMetadata[@"languages"];
    return [languages isKindOfClass:NSArray.class] ? languages : @[@{@"id":@"en", @"name":@"English"}];
}
static NSString *MCD2MatchLanguage(NSString *candidate) {
    if (![candidate isKindOfClass:NSString.class]) return nil;
    NSString *tag = [[candidate stringByReplacingOccurrencesOfString:@"_" withString:@"-"] lowercaseString];
    for (NSDictionary *language in MCD2Languages())
        if ([[language[@"id"] lowercaseString] isEqual:tag]) return language[@"id"];
    NSDictionary *aliases = mcd2LanguageMetadata[@"aliases"];
    for (NSString *alias in aliases)
        if ([[alias lowercaseString] isEqual:tag]) return aliases[alias];
    if ([tag hasPrefix:@"zh-"]) {
        return ([tag containsString:@"hant"] || [tag containsString:@"-tw"] || [tag containsString:@"-hk"] || [tag containsString:@"-mo"]) ? @"zh-Hant" : @"zh-Hans";
    }
    if ([tag isEqual:@"zh"]) return @"zh-Hans";
    if ([tag hasPrefix:@"pt-"] || [tag isEqual:@"pt"]) return [tag containsString:@"-br"] ? @"pt-BR" : @"pt-PT";
    if ([tag hasPrefix:@"es-"] || [tag isEqual:@"es"]) return ([tag isEqual:@"es"] || [tag hasPrefix:@"es-es"]) ? @"es-ES" : @"es-419";
    NSString *base = [tag componentsSeparatedByString:@"-"].firstObject;
    for (NSDictionary *language in MCD2Languages())
        if ([language[@"id"] isEqual:base]) return language[@"id"];
    return nil;
}
static NSString *MCD2LanguageChoice(void) {
    NSString *choice = mcd2LanguageOverride ?: [[NSString stringWithContentsOfFile:mcd2LanguagePreference encoding:NSUTF8StringEncoding error:nil] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
    if ([choice isEqual:@"system"] || !choice.length) return @"system";
    for (NSDictionary *language in MCD2Languages()) if ([language[@"id"] isEqual:choice]) return choice;
    return @"system";
}
static NSString *MCD2CurrentLanguage(void) {
    NSString *choice = MCD2LanguageChoice();
    if (![choice isEqual:@"system"]) return choice;
    for (NSString *candidate in NSLocale.preferredLanguages) {
        NSString *language = MCD2MatchLanguage(candidate);
        if (language) return language;
    }
    return @"en";
}
static void MCD2RefreshLanguage(void) {
    NSString *path = [mcd2LocalizationResources stringByAppendingPathComponent:[MCD2CurrentLanguage() stringByAppendingString:@".lproj"]];
    mcd2LanguageBundle = [NSBundle bundleWithPath:path];
}
static void MCD2ConfigureLocalization(NSString *resourcesPath, NSString *preferencePath) {
    mcd2LocalizationResources = resourcesPath;
    mcd2LanguagePreference = preferencePath;
    NSData *data = [NSData dataWithContentsOfFile:[resourcesPath stringByAppendingPathComponent:@"localization/languages.json"]];
    id metadata = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
    mcd2LanguageMetadata = [metadata isKindOfClass:NSDictionary.class] ? metadata : @{};
    MCD2RefreshLanguage();
}
static NSString *L(NSString *source) {
    return [mcd2LanguageBundle localizedStringForKey:source value:source table:@"Localizable"] ?: source;
}
static BOOL MCD2SelectLanguage(NSString *choice) {
    BOOL valid = [choice isEqual:@"system"];
    for (NSDictionary *language in MCD2Languages()) if ([language[@"id"] isEqual:choice]) valid = YES;
    if (!valid) return NO;
    NSFileManager *manager = NSFileManager.defaultManager;
    NSString *folder = mcd2LanguagePreference.stringByDeletingLastPathComponent;
    NSDictionary *attributes = [manager attributesOfItemAtPath:folder error:nil];
    if (attributes && ![attributes[NSFileType] isEqual:NSFileTypeDirectory]) return NO;
    if (![manager createDirectoryAtPath:folder withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:nil]) return NO;
    if (![[choice stringByAppendingString:@"\n"] writeToFile:mcd2LanguagePreference atomically:YES encoding:NSUTF8StringEncoding error:nil]) return NO;
    [manager setAttributes:@{NSFilePosixPermissions:@0600} ofItemAtPath:mcd2LanguagePreference error:nil];
    mcd2LanguageOverride = choice;
    MCD2RefreshLanguage();
    return YES;
}

static BOOL MCD2KnownText(NSString *text) {
    static NSDictionary *english;
    if (!english) {
        NSData *data = [NSData dataWithContentsOfFile:[mcd2LocalizationResources stringByAppendingPathComponent:@"localization/en.json"]];
        id value = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
        english = [value isKindOfClass:NSDictionary.class] ? value : @{};
    }
    return english[text] != nil;
}
