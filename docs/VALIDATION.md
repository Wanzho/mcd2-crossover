# Testing

Tested on an M5 Pro with CrossOver 26.3. Setup and direct Steam launch were confirmed on 30 September 2026. This build supports Apple Silicon only.

## Confirmed

- Setup and **Play** reached the game. The portable repair also reached the game twice, including a launch with the longer-lived sign-in.
- Setup passed in a second bottle after the Visual C++ detection fix. The repeated Repair prompt was gone. Both tested bottles already had Microsoft Visual C++ installed.
- Launching directly from Steam reached the game with MCD2 Crossover closed. Steam uses the launch option saved during setup.
- Saved sign-in and forced token renewal worked with logging off. Renewal continued with the launcher closed, and the Microsoft refresh token remained in macOS Keychain.
- Installed files matched the build, the Steam launch command was present, and the WASD mod’s Wine override was preserved.

## Local checks

Automated checks cover setup, backups, Steam launch settings, missing Visual C++, sign-out and cancellation using disposable files and synthetic accounts.

Change Bottle opens the bottle picker, rejects a missing game folder and returns to the previous selection on Cancel. A disposable second-bottle check installed all repair files from the official dependency archives, configured Steam and preserved the shared account/session and the previous bottle’s files. This was an installation check; it did not test gameplay in a fresh bottle.

Visual C++ tests cover both registry views and mixed casing, opening the installer for Wine builtin VC DLLs, and accepting Microsoft’s three VC DLLs with Wine’s UCRT. Read-only checks rejected three bottles with builtin VC DLLs and accepted both working bottles with native VC DLLs. The corrected detector also recognized the second bottle’s installed 14.51 runtime. No bottle commands ran during these checks; the registry, runtime DLLs and Steam settings were unchanged.

## Not yet tested

- Installing Visual C++ in a bottle where it is missing.
- Longer play sessions, missions, multiplayer and other Macs.
- Downloading and opening the app through Gatekeeper. The app is not notarized.

## 0.1.1

The confirmed Steam gameplay results above belong to the previous build; they do not establish Launcher compatibility.

Added a game-copy browser, an experimental Minecraft Launcher selection and a corner **Troubleshooting…** button for opt-in recording and ZIP export.

57 automated checks passed with both system Python and the app's bundled Python. They cover copy selection, the Steam and direct launch routes, recording expiry, filtered exports and malformed log lines. The native app compiled, the native one-hour expiry check passed, and the troubleshooting button and sheet were visually inspected. These checks used disposable files and synthetic accounts; no live bottle was changed.

The signed 0.1.1 app passed installation checks for Steam, a second bottle and a Launcher fixture using the official dependency archives. Backups, the relocated Python runtime and unchanged account/session files were verified. These checks do not establish Launcher gameplay support.

No owned Launcher/non-Steam build is available for a gameplay test. The direct CrossOver launch may still fail at Windows Store licensing. Signing into a linked Microsoft account does not transfer a Steam game license to the Launcher edition.
