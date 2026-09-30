# Startup and sign-in errors

The repair covers these startup and sign-in failures observed under CrossOver.

| Message or problem | What the repair does |
| --- | --- |
| Visual C++ / Missing Gaming Services | Checks that Visual C++ is really installed. If needed, it opens Microsoft’s installer. It then tells Steam to start the actual game instead of the launcher that keeps asking for prerequisites. |
| “Game Runtime is not installed” | Adds Microsoft’s portable Xbox runtime beside the game. Windows Gaming Services itself isn’t installed. |
| Crash during network startup | Uses curl’s official Windows library and certificate bundle. |
| Xbox task queue unavailable | Initializes the game-local runtime with the game’s original configuration and Microsoft’s async support. |
| 0060: Verification failed | Checks real internet connectivity and supplies a working Microsoft/Xbox sign-in route, so the game can continue online. |
| Unreal crash during HTTPS setup | Stops the game from passing an OpenSSL-only hook into an incompatible library. Certificate checks stay on. |
| 0063: Log in failed | Corrects the Steam-to-PlayFab request’s body size. The server had been rejecting its conflicting transfer headers. |
| 0064: Log in failed | Applies the same correction to the later PlayFab and Minecraft requests too. |
| 0020: Account linking failed | Lets the game retrieve the Xbox account you already signed in with. A different account ID is still rejected. |

## Steam startup and Visual C++

Setup configures Steam to start the shipping executable directly, skipping the prerequisite checker. Early ZIP installers did not set this launch command, so the missing-component prompts returned after a clean reinstall. **The current DMG includes that step.**

The game bundles Visual C++ 14.42. That installer refused to downgrade a bottle with 14.51 already installed. Setup accepts 14.42 or newer. If Visual C++ is missing, it tries Microsoft’s latest download, then the game’s bundled installer if the download fails. It checks the result before continuing.

Runtime detection accepts either `x64` or `X64` in both registry views. The earlier case-sensitive check rejected a successful installation and repeatedly opened Repair.

CrossOver can also register Visual C++ 14.42 while supplying Wine’s builtin DLLs. Setup now rejects those builtin copies of `msvcp140.dll`, `vcruntime140.dll` and `vcruntime140_1.dll`, so they don’t make it skip Microsoft’s installer. It still accepts Wine’s `ucrtbase.dll`: both working bottles retain it after a real Microsoft Visual C++ install. Rejecting that file would send those bottles through Repair again.

## What this doesn’t fix

Intermittent crashes and stalls on the Warden screen have no separate confirmed fix. Other Unreal crashes or occurrences of these error codes may have different causes.

Older-library trials, SteamDeck flags, custom certificate-path overrides and forced Content-Type changes didn’t help. They aren’t included. Your Wine overrides and controller mods are left alone.

If a missing-component prompt returns after verifying or reinstalling the game, open MCD2 Crossover and choose **Repair Setup…** from its menu.
