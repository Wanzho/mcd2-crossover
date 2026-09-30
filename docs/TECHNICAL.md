# Technical notes

## Components

The Mac app handles setup, Play, Change Bottle and Sign Out. `scripts/install.py` installs the repair into an existing Steam game; `scripts/startup.py` checks Visual C++ and sets this game’s Steam launch option. Steam starts the shipping executable through a small command file, so its ownership checks still run. Once setup and sign-in are complete, that Steam route works without opening the app; the per-user LaunchAgent owns renewal.

`xgameruntime.dll` is a compatibility adapter. Microsoft’s genuine runtime and async thunks sit beside it. The adapter supplies the missing user and connectivity interfaces, using the real Xbox account and tokens. It doesn’t approve ownership or invent privileges.

`XCurl.dll` loads the official curl library. It declines an incompatible OpenSSL hook and gives curl the body size when the game supplied one valid Content-Length without Transfer-Encoding. Body bytes, other headers and callbacks are preserved.

## Sign-in storage

The helper is `bridge.py`. Its access session expires at the earliest Xbox NotAfter. The refresh token stays in a nonsynchronizing Keychain item: service `org.dungeons-crossover.microsoft-refresh`, account `default`. It reaches the native Keychain helper through a pipe, never a command argument or log.

Local session files use mode 600 inside a mode-700 folder. A per-user LaunchAgent renews roughly five minutes before expiry and handles ForceRefresh. Sign Out deletes the Keychain item and local session; it doesn’t revoke an already-issued Microsoft token or close the game.

The data folder is `~/Library/Application Support/DungeonsCrossOver/`. It keeps the same name across app updates. The sidecar tells the DLLs where to find it, so no user path is compiled into the build.

Change Bottle opens setup for another installed game. Nothing is written until you run setup; Cancel returns home. Setup updates the selected bottle and LaunchAgent arguments, with backups, but does not delete the shared session or touch its Keychain item. Previous bottles keep their installed repair and share the same Microsoft sign-in. The app’s Play and Force Quit commands use the currently selected bottle. Sign Out removes the shared login for all repaired bottles.

## Build

Install LLVM or Rust for `lld-link`, plus Apple’s command-line build tools. Then:

```sh
python3 scripts/build.py
python3 -m pip install -r helper/requirements.txt
python3 -m unittest discover -s tests -v
```

To install a source build:

```sh
python3 scripts/install.py --bottle Steam --game '/path/to/Minecraft Dungeons II' --accept-gdk-license
```

Read Microsoft’s license before using that flag. `--check-only` makes no changes. `--prepare-only` updates the Mac helper without replacing game files or launch settings. Use `--gdk-archive` and `--curl-archive` for local dependency archives.

The installer downloads [Microsoft GDK 2604.4.7897](https://www.nuget.org/packages/Microsoft.GDK.Windows/2604.4.7897) and [curl’s Windows build](https://curl.se/windows/), checking the extracted files against pinned hashes. The app bundles [Astral’s standalone Python](https://github.com/astral-sh/python-build-standalone), cryptography, cffi and pycparser, with their license notices. No Microsoft or game binaries are shipped in the DMG.

To package the app:

```sh
python3 scripts/package_release.py --gdk-archive /path/to/microsoft.gdk.windows.nupkg
```

Build releases from a clean checkout and rebuild the compatibility binaries with `scripts/build.py` first. The app’s `source-origin.json` records the source commit and file hashes; the DMG’s `.source.json` sidecar ties that commit to the download’s checksum. The release tag should point to that same commit.

The native test uses synthetic tokens and makes no sign-in request:

```sh
python3 scripts/test_native.py --game '/path/to/Minecraft Dungeons II'
```

## Undo the repair

Quit the game and Steam, then restore the replaced DLLs and sidecar from the backup listed in `installation.json`. The backup’s `startup.json` records the previous Steam launch option: restore only that value for AppID 1912410, rather than replacing all of Steam’s current settings. Remove `MCD2CrossoverLaunch.cmd` if setup created it.

Use **Sign Out** in MCD2 Crossover to remove the saved login. To stop renewal permanently:

```sh
launchctl bootout "gui/$(id -u)/org.dungeons-crossover.auth"
```

Then remove `~/Library/LaunchAgents/org.dungeons-crossover.auth.plist`. The installer doesn’t change saves, the shipping executable or Wine DLL overrides.

## Debugging

Logging is off by default. To enable it temporarily:

```sh
"$HOME/Library/Application Support/DungeonsCrossOver/python/bin/python" \
  "$HOME/Library/Application Support/DungeonsCrossOver/runtime/bridge.py" logs-on
```

Use `logs-off` to stop it. Logs keep selected status codes and framing details, without tokens, passwords, account IDs or full URLs. Review them before sharing.

Only one account is supported. AllUsers and request signatures are still unsupported; multiplayer may need more work. Non-ASCII Wine paths also need testing.

Useful references: [Microsoft’s cross-platform runtime](https://learn.microsoft.com/en-us/gaming/gdk/docs/features/common/user/xuser-crossplatform), [add-by-ID](https://learn.microsoft.com/en-us/gaming/gdk/docs/reference/system/xuser/functions/xuseraddbyidwithuiasync), [ForceRefresh](https://learn.microsoft.com/en-us/gaming/gdk/docs/reference/system/xuser/enums/xusergettokenandsignatureoptions), and [Apple Keychain](https://developer.apple.com/documentation/security/keychain_services).
