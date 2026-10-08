#import <Cocoa/Cocoa.h>
NS_ASSUME_NONNULL_BEGIN
@interface CrossoverUpdater : NSObject
+ (instancetype)shared;
- (void)startWithBusyCheck:(BOOL (^)(void))busyCheck;
- (void)addItemsToMenu:(NSMenu *)menu;
- (BOOL)allowsNewOperation;
- (BOOL)mustWaitBeforeQuitting;
@end
NS_ASSUME_NONNULL_END
