// Generated from helper/error_codes.json. Keep the support catalog in sync.
static NSDictionary *MCD2ErrorCatalog(void) {
    return @{
@1001: @{@"check": @"Find CrossOver", @"expected": @"A selected CrossOver application.", @"observed": @"CrossOver was not found.", @"next_step": @"Click Choose CrossOver and select your app."},
@1002: @{@"check": @"Verify CrossOver identity", @"expected": @"Bundle identifier com.codeweavers.CrossOver.", @"observed": @"The selected app is missing or has a different bundle identifier.", @"next_step": @"Choose your CrossOver app again; its filename can be different."},
@1003: @{@"check": @"Find Wine", @"expected": @"An executable Wine runtime in the selected CrossOver app.", @"observed": @"The Wine executable is missing or cannot run.", @"next_step": @"Choose an intact CrossOver installation."},
@1004: @{@"check": @"Save CrossOver selection", @"expected": @"A writable application support folder.", @"observed": @"The CrossOver selection could not be saved.", @"next_step": @"Check access to your application support folder, then choose the app again."},
@1101: @{@"check": @"Prepare bundled runtime", @"expected": @"A verified app bundle and readable, usable bundled runtime.", @"observed": @"App verification or runtime preparation failed.", @"next_step": @"Copy a fresh download to Applications and reopen it. See the local check result below."},
@1201: @{@"check": @"Find a bottle", @"expected": @"At least one CrossOver bottle containing the game.", @"observed": @"No CrossOver bottles were found.", @"next_step": @"Install the game in CrossOver, then reopen this app."},
@1202: @{@"check": @"Validate game copy", @"expected": @"MicrosoftGame.config and a supported Dungeons Shipping.exe in the selected game folder.", @"observed": @"The selected copy could not be validated.", @"next_step": @"Browse to the installed game folder or select its Shipping.exe file."},
@1203: @{@"check": @"Check license acceptance", @"expected": @"Acceptance of the Microsoft GDK license before setup.", @"observed": @"The license checkbox has not been selected.", @"next_step": @"Read the license and select the checkbox if you accept it."},
@1204: @{@"check": @"Change game copy", @"expected": @"A different game copy or settings selection.", @"observed": @"This copy is already selected.", @"next_step": @"Choose another copy or close the selection sheet."},
@2001: @{@"check": @"Start app helper", @"expected": @"The local helper process starts successfully.", @"observed": @"macOS could not start the helper.", @"next_step": @"Use Repair Setup or reinstall the app; include the system error number when reporting it."},
@2101: @{@"check": @"Check running game", @"expected": @"The selected game is closed before files are replaced.", @"observed": @"The selected game is still running.", @"next_step": @"Quit the game and retry setup."},
@2102: @{@"check": @"Check shared Steam bottle", @"expected": @"No other game using this Steam bottle.", @"observed": @"Another game is using the bottle.", @"next_step": @"Quit that game before retrying setup."},
@2103: @{@"check": @"Identify running game", @"expected": @"A process check that can identify the running game.", @"observed": @"Setup cannot safely identify which game is running.", @"next_step": @"Close Windows games in this bottle, then retry."},
@2201: @{@"check": @"Download dependencies", @"expected": @"A successful download from the dependency publisher.", @"observed": @"The dependency download command failed.", @"next_step": @"Check your connection and retry setup."},
@2202: @{@"check": @"Verify dependencies", @"expected": @"An archive with the expected files and matching checksums.", @"observed": @"Dependency verification failed.", @"next_step": @"Retry with a fresh download; report the code if it repeats."},
@2203: @{@"check": @"Prepare Visual C++", @"expected": @"The required Windows Visual C++ runtime.", @"observed": @"Visual C++ preparation did not complete.", @"next_step": @"Complete Microsoft’s installer and retry setup."},
@2204: @{@"check": @"Prepare Windows Steam", @"expected": @"Steam preparation completes before setup changes game files.", @"observed": @"Windows Steam preparation failed.", @"next_step": @"Quit games using the bottle, then retry setup."},
@2205: @{@"check": @"Write setup files", @"expected": @"Readable source files and writable destination files.", @"observed": @"A file operation failed during setup.", @"next_step": @"Check disk space and folder access, then retry."},
@2299: @{@"check": @"Complete setup", @"expected": @"All setup operations finish successfully.", @"observed": @"An unclassified setup operation failed.", @"next_step": @"Save Logs and report this code with the step that failed."},
@3001: @{@"check": @"Contact Microsoft or Xbox", @"expected": @"A successful authentication network request.", @"observed": @"An authentication network request failed.", @"next_step": @"Check the connection and retry sign-in."},
@3002: @{@"check": @"Authenticate with Microsoft or Xbox", @"expected": @"Microsoft and Xbox accept the authentication request.", @"observed": @"Authentication was rejected.", @"next_step": @"Retry sign-in; if it repeats, check your account in Microsoft/Xbox."},
@3003: @{@"check": @"Complete sign-in before expiry", @"expected": @"Sign-in finishes before its code expires.", @"observed": @"The sign-in code expired.", @"next_step": @"Click Play to start a new sign-in attempt."},
@3004: @{@"check": @"Finish interactive sign-in", @"expected": @"The sign-in window remains open until authentication completes.", @"observed": @"Sign-in was cancelled or its window closed.", @"next_step": @"Click Play and complete sign-in."},
@3005: @{@"check": @"Start background sign-in service", @"expected": @"The background authentication service starts.", @"observed": @"The service could not be started.", @"next_step": @"Use Repair Setup and retry."},
@3006: @{@"check": @"Wait for sign-in readiness", @"expected": @"The background service reports a ready session.", @"observed": @"Sign-in did not finish before the deadline.", @"next_step": @"Retry sign-in and save logs if it repeats."},
@3007: @{@"check": @"Validate authenticated session", @"expected": @"A consistent account identity and usable service tokens.", @"observed": @"The session data did not pass validation.", @"next_step": @"Sign out, then sign in again."},
@3008: @{@"check": @"Find saved sign-in", @"expected": @"A usable saved Microsoft sign-in.", @"observed": @"Sign-in or renewed authentication is required.", @"next_step": @"Click Play and sign in again."},
@3101: @{@"check": @"Locate installed game", @"expected": @"A supported executable at the saved game location.", @"observed": @"The saved game copy or executable is missing or unsupported.", @"next_step": @"Choose Change Game Copy or Repair Setup."},
@3199: @{@"check": @"Launch game", @"expected": @"Sign-in and game launch complete successfully.", @"observed": @"A launch operation failed; no more specific result was available.", @"next_step": @"Save Logs and report the step where it stopped."},
@4001: @{@"check": @"Sign out", @"expected": @"Saved sign-in and local session are removed successfully.", @"observed": @"Sign-out did not complete.", @"next_step": @"Quit the game and retry Sign Out."},
@4002: @{@"check": @"Stop game", @"expected": @"The selected game stops successfully.", @"observed": @"The game-stop operation failed.", @"next_step": @"Use Windows Steam in the selected bottle to stop the game."},
@5001: @{@"check": @"Save troubleshooting logs", @"expected": @"The selected destination accepts the log archive.", @"observed": @"The logs could not be saved.", @"next_step": @"Choose another destination; Copy Details can still copy this error."},
@5002: @{@"check": @"Record troubleshooting logs", @"expected": @"The diagnostic helper can start or stop recording.", @"observed": @"Recording could not be changed.", @"next_step": @"Check folder access or use Repair Setup."}
    };
}
static NSDictionary *MCD2ErrorRecord(NSInteger code, NSNumber *exitCode, NSNumber *systemCode) {
    if (!MCD2ErrorCatalog()[@(code)]) return nil;
    NSMutableDictionary *record=[@{@"code":@(code)} mutableCopy];
    if (exitCode) record[@"exit_status"]=exitCode;
    if (systemCode) record[@"system_code"]=systemCode;
    return record;
}
static NSString *MCD2ErrorText(NSDictionary *record) {
    NSNumber *code=record[@"code"]; NSDictionary *entry=MCD2ErrorCatalog()[code];
    if (!entry) return @"";
    NSMutableString *text=[NSMutableString stringWithFormat:@"Internal Error: %04ld\n\nCheck: %@\n\nExpected: %@\n\nFound: %@\n\nNext step: %@",code.integerValue,entry[@"check"],entry[@"expected"],entry[@"observed"],entry[@"next_step"]];
    if (record[@"exit_status"]) [text appendFormat:@"\n\nProcess exit status: %@",record[@"exit_status"]];
    if (record[@"system_code"]) [text appendFormat:@"\nSystem error number: %@",record[@"system_code"]];
    return text;
}
// Accept only the structured numeric protocol, never arbitrary process output or auth URLs.
static NSDictionary *MCD2ParseError(NSString *output) {
    for (NSString *line in [output componentsSeparatedByCharactersInSet:NSCharacterSet.newlineCharacterSet]) {
        if (![line hasPrefix:@"MCD2_INTERNAL_ERROR:"] || line.length>512) continue;
        NSData *data=[[line substringFromIndex:20] dataUsingEncoding:NSUTF8StringEncoding];
        id value=[NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
        if (![value isKindOfClass:NSDictionary.class]) continue;
        id code=value[@"code"], system=value[@"system_code"];
        if (![code isKindOfClass:NSNumber.class] || !MCD2ErrorCatalog()[code]) continue;
        if (![system isKindOfClass:NSNumber.class]) system=nil;
        return MCD2ErrorRecord([code integerValue],nil,system);
    }
    return nil;
}
