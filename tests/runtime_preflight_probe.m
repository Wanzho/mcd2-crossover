#import <Foundation/Foundation.h>
#import "../packaging/runtime_preflight.h"
int main(int argc,const char **argv) { @autoreleasepool {
 NSString *app=[NSString stringWithUTF8String:argv[1]];
 NSString *error=MCD2PrepareEmbeddedRuntime(app,[app stringByAppendingPathComponent:@"Contents/Resources"]);
 if(error) { fprintf(stderr,"%s\n",error.UTF8String);return 1; } puts("Runtime preparation passed");
 }return 0; }
