# MCD2 Crossover — Minecraft Dungeons II on Mac

A macOS setup and sign-in tool for **Minecraft Dungeons II (Minecraft Dungeons 2)** through CrossOver on Apple Silicon.

Repairs Steam startup, runtime dependencies, networking and Microsoft/Xbox sign-in. Requires an existing Steam copy of the game and a Microsoft account.

<img width="588" height="504" alt="Screenshot 2026-10-01 at 01 04 03" src="https://github.com/user-attachments/assets/46ba1909-937e-4134-93e9-4b90c623c628" />

**[Download MCD2 Crossover →](https://github.com/Wanzho/mcd2-crossover/releases/tag/v0.1.8.1)**

## Beta 3

[Try 0.2.0 Beta 3](https://github.com/Wanzho/mcd2-crossover/releases/tag/v0.2.0-beta.3) if you want to help investigate sign-in and **Playing Offline** problems. It includes the earlier beta changes and preserves the Wine wait-queue patch status in saved logs. Check for Updates does not offer beta releases.

After replacing the app, quit the game and run **Set Up** once for the same bottle to install the new adapters. Your saved sign-in stays in place. To send a report, choose **Start Recording**, reproduce the problem, then **Save Logs**.

This is not a confirmed fix for error 0056 or offline play. The corrected recording code has passed automated tests but still needs a recording-on game test.

## Install

Install CrossOver, Windows Steam and Minecraft Dungeons II first. Open Steam and sign in at least once.

1. Download **MCD2-Crossover-0.1.8.1-arm64.dmg** under **Assets** on the download page.
2. Open it and drag **MCD2 Crossover** into **Applications**.
3. Quit the game, then open **MCD2 Crossover** from Applications.
If macOS blocks it, approve it in **System Settings → Privacy & Security**. 
4. Choose your Steam bottle, read the Microsoft license and click **Set Up**. If CrossOver isn't in Applications or has another name, click **Choose CrossOver…** and select it. If **Set Up** stays greyed out, click it anyway to see what's missing. Setup restarts Steam. If Visual C++ is missing, finish the Microsoft installer that opens.
5. Click **Play**. If a Microsoft code window appears, complete sign-in and leave that small window open until it closes. Click the link or code to copy it.

No Terminal commands, Python install or build tools needed. Setup backs up replaced files and leaves your saves and controller mods alone.



## Next time you play

After setup and your first sign-in, you can launch **directly from Steam** in the selected bottle. You don’t need to open the app every time you play.

Sign-in renews in the background, so you normally won’t need another login code. Your saved Microsoft credential stays in macOS Keychain. **Close Window** closes the launcher without stopping the game.

If Steam can’t sign in because the saved session expired or renewal stopped, open **MCD2 Crossover** and click **Play**. It checks sign-in, reconnects if needed and opens the game through Steam.

## Change CrossOver bottles

Quit the game, open **MCD2 Crossover** and click **Change Game Copy…** on the home screen. A compact sheet opens over the launcher. Choose another bottle or game copy and click **Done**. Changing the copy runs setup, restarts Steam in that bottle and backs up replaced files.

Your Microsoft sign-in stays saved. The previous bottle keeps its repair; the app’s Play button now uses the new bottle. **Cancel** takes you back without changing anything. Sign Out is only for removing your saved Microsoft login or switching accounts.

## Sign out or switch accounts

Quit the game, open **MCD2 Crossover**, and click **Sign Out**. This removes the saved Microsoft credential and local session. Click **Play** to sign in again with the account you want.

## What's new in 0.1.8.1

- Large process samples no longer fail just because they exceed 8 MiB. Reports are read incrementally, repeated frames are compacted, and both ends of long thread stacks are retained within bounded limits.
- Capture allows up to 60 seconds for macOS to finish. Timeout, permission denial, missing output and unreadable frames now show distinct messages in the app.
- Save Logs includes sample size, sampling exit code, thread counts and whether any frames were omitted. Raw process headers and sampler output remain private.

This fixes diagnostics collection; it does not claim to fix gameplay freezes.

## What's new in 0.1.8

This release improves investigation of freezes during gameplay. It does **not** claim to fix the reported freeze.

- Timestamped app, authentication, runtime and HTTP diagnostics, with request durations and attempt counts.
- **Game Froze — Capture Diagnostics** takes a short sample of the selected running game and records its CPU and memory usage. It leaves the game running.
- Save Logs includes the sanitized sample, or a clear capture failure result. Capture works even if recording was not started, though earlier events cannot be recovered.
- Internal Error 5003–5005 explain missing processes, ambiguous game selection and sampling failures.

After updating, choose **Repair Setup** once with the game closed to install the updated game diagnostics.

## What's new in 0.1.6

This release fixes first-time setup for people whose **Set Up** button stayed greyed out.

- **Choose CrossOver…** lets setup use CrossOver from any folder or under any name. The app remembers your choice for setup, Play, sign-in and session cleanup. It only accepts CrossOver itself (bundle ID `com.codeweavers.CrossOver`) with its Wine executable.
- Clicking a greyed-out **Set Up** now tells you what's blocking it, such as a missing CrossOver, game folder or license tick.
- The game folder check no longer depends on the bundled Python, and setup now works when macOS has quarantined the app's runtime after a download.
- Existing 0.1.5 setups update in the app with **Check for Updates…** and don't need to run setup again.

Gameplay with the new CrossOver picker hasn't been tested yet.

## Important update: 0.1.5

This release addresses background battery drain after a game session. All users should update.

- Launching with **Play** now watches that game session. If its window is gone for a minute but its process remains, the launcher requests that process to end. Minimized or hidden windows remain running.
- When the launcher started Steam, it closes that Steam session after the game ends, then stops the idle bottle's remaining services. Steam that was already open, another Windows app, and active downloads are preserved.
- The sign-in service now waits for requests instead of checking the disk five times every second. Saved accounts and silent renewal remain available.
- **Check for Updates…** can download, verify and replace future versions inside the app. Versions without this menu need this one manual upgrade.

Session cleanup applies to games launched with this app's **Play** button. It does not change CrossOver's controller settings or reduce rendering load while a game is running.

## Troubleshooting

Still having trouble? [Open an issue here](https://github.com/Wanzho/mcd2-crossover/issues/new/choose).

If **Set Up** is greyed out, click it to see the reason.

For a freeze during gameplay:

1. Update to 0.1.8.1, then use **Repair Setup** with the game closed.
2. Open **Troubleshooting… → Start Recording**, then play normally. Recording expires after one hour.
3. When the game freezes, **leave it open**. In the app, click **Game Froze — Capture Diagnostics**.
4. Wait for the capture result, then click **Save Logs…** and attach the ZIP to your issue. Mention what you were doing when it froze.
5. You can then stop the frozen game through Windows Steam.

Capture samples only the selected game. It does not change Wi-Fi, restart the game, upload logs, or read credentials. The exported sample excludes raw process metadata, personal paths and arbitrary module names. If macOS denies sampling, the app reports that; Activity Monitor's Sample Process is an alternative.

For setup/sign-in problems, start recording, reproduce the problem and save logs. No game launch is needed.

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

Coded with Codex Astra 6 and Sol 6.1, reviewed with Claude Opus 5.5.

## Internal error codes

When an operation fails, MCD2 Crossover shows **Internal Error: 1234** and **See details…**. Expand it to see the check, expected result, observed failure, and suggested next step. Process exit statuses and system error numbers are included when available. These are launcher support codes, not Minecraft or Xbox server error codes.

If **Set Up** is unavailable, click it to see why. Setup validation errors stay hidden until that attempt. **Copy Details** copies a support-safe report; **Troubleshooting… → Save Logs…** includes the last internal error even without starting a recording. If the bundled runtime is unavailable, Save Logs offers a text error report instead. Local validator messages can include the selected path on screen; exported error reports contain catalog text and numeric results, not account data or raw sign-in responses.

See the [complete error-code catalog](docs/error-codes.json). Unknown failures retain a general code rather than guessing a cause. Cancelling launch yourself is shown as cancellation, not an internal error.
