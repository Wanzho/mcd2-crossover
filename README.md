# MCD2 Crossover — Minecraft Dungeons II on Mac

A macOS setup and sign-in tool for **Minecraft Dungeons II (Minecraft Dungeons 2)** through CrossOver on Apple Silicon.

Repairs Steam startup, runtime dependencies, networking and Microsoft/Xbox sign-in. Requires an existing Steam copy of the game and a Microsoft account.

<img width="588" height="504" alt="Screenshot 2026-10-01 at 01 04 03" src="https://github.com/user-attachments/assets/46ba1909-937e-4134-93e9-4b90c623c628" />

**[Download MCD2 Crossover →](https://github.com/Wanzho/mcd2-crossover/releases/tag/v0.1.1)**

## Install

Install CrossOver, Windows Steam and Minecraft Dungeons II first. Open Steam and sign in at least once.

1. Download **MCD2-Crossover-0.1.1-arm64.dmg** under **Assets** on the download page.
2. Open it and drag **MCD2 Crossover** into **Applications**.
3. Quit the game, then open **MCD2 Crossover** from Applications.
If macOS blocks it, approve it in **System Settings → Privacy & Security**. 
4. Choose your Steam bottle, read the Microsoft license and click **Set Up**. Setup restarts Steam. If Visual C++ is missing, finish the Microsoft installer that opens.
5. Click **Play**. If a Microsoft code window appears, complete sign-in and leave that small window open until it closes. Click the link or code to copy it.

No Terminal commands, Python install or build tools needed. Setup backs up replaced files and leaves your saves and controller mods alone.



## Next time you play

After setup and your first sign-in, you can launch **directly from Steam** in the selected bottle. You don’t need to open the app every time you play.

Sign-in renews in the background, so you normally won’t need another login code. Your saved Microsoft credential stays in macOS Keychain. **Close Window** closes the launcher without stopping the game.

If Steam can’t sign in because the saved session expired or renewal stopped, open **MCD2 Crossover** and click **Play**. It checks sign-in, reconnects if needed and opens the game through Steam.

## Change CrossOver bottles

Quit the game, open **MCD2 Crossover** and click **Change Bottle…** beside the current bottle on the home screen. Choose another bottle with Windows Steam and Minecraft Dungeons II installed, read the Microsoft license and click **Use This Bottle**. Setup restarts Steam in that bottle and backs up replaced files.

Your Microsoft sign-in stays saved. The previous bottle keeps its repair; the app’s Play button now uses the new bottle. **Cancel** takes you back without changing anything. Sign Out is only for removing your saved Microsoft login or switching accounts.

## Sign out or switch accounts

Quit the game, open **MCD2 Crossover**, and click **Sign Out**. This removes the saved Microsoft credential and local session. Click **Play** to sign in again with the account you want.

## New in 0.1.1

Added game copy selection and troubleshooting logs:

- **Browse Game Copy…** chooses another game copy from the home screen or setup. Select its game folder or `Dungeons-…-Shipping.exe`; the app checks the layout before setup.
- Choose **Steam** or **Minecraft Launcher (experimental)** under **Launcher:** when setting up that copy. The Steam route stays the same. Launcher mode starts an existing Windows game copy through CrossOver and needs its own valid entitlement. A Steam purchase does not unlock the Launcher edition.
- **Troubleshooting…** in the top-right corner opens recording and ZIP export. Logging is off by default, stops after an hour and never uploads anything. Credentials and game saves are excluded from exports.

Launcher support has not been tested with an owned non-Steam copy. Windows Store licensing may still prevent it from running; this is a compatibility attempt, not confirmed Launcher support. It does not install Minecraft Launcher or download the game.

## Troubleshooting

Still having trouble? [Open an issue here](https://github.com/Wanzho/mcd2-crossover/issues/new/choose).

Open **Troubleshooting…**, click **Start Recording** and reproduce the problem. Click **Save Logs…** and attach the ZIP to the issue. Setup and sign-in problems can be recorded with the game closed.

Issues resolved by this application:

- Visual C++ 2015–2022 (x64) prerequisite prompt
- Missing Gaming Services prerequisite prompt
- Repeated Visual C++ Repair prompt
- “Game Runtime is not installed”
- Crash during networking startup
- Xbox “task queue missing”
- Unreal Engine crash during HTTPS setup
- **0060** — Verification failed
- **0063** — Log in failed
- **0064** — Log in failed
- **0020** — Microsoft account linking failed

See [startup and sign-in fixes](docs/FIXES.md) for details.

## Tested

Tested on an **M5 Pro with CrossOver 26.3**. Setup and launch through the app reached the game, setup passed in a second bottle, and launching directly from Steam worked with MCD2 Crossover closed.

## Limitations

Installing Visual C++ where it is missing, longer sessions, multiplayer and other Macs remain untested. Windows Gaming Services itself is not installed by this repair.

Sign-in uses the game’s own Microsoft app ID, not one registered for this tool. Microsoft could block that route, so use it at your own risk.

Apple Silicon only. Steam is supported; Minecraft Launcher remains experimental.

For source builds, dependencies and rollback, see [the technical notes](docs/TECHNICAL.md) and [test results](docs/VALIDATION.md).

Unofficial project. Not affiliated with Mojang, Microsoft or CodeWeavers.

## References

Coded with Codex Astra 6 and Sol 6.1. Reviewed with Claude Opus 5.5.

If you think this is Vibecoding slop, you are always welcome to use something else.
