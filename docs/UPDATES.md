# Signed app updates

The upcoming 0.1.4 app adds **Check for Updates…** and **Automatically Install Updates** to the app menu. Sparkle 2.10.0 downloads, verifies, replaces and relaunches the app. Existing versions need one initial manual upgrade to gain this feature.

Production feed: `https://raw.githubusercontent.com/Wanzho/mcd2-crossover/main/appcast.xml`.
The feed must be published alongside the referenced release archive before distribution. The source URL is configured; publication is a separate release step.

Both the appcast and archives require Ed25519 signatures. The private key stays in the release maintainer's macOS Keychain under account `org.wanzho.crossover.updates`. Never commit or bundle it. The dependency download is pinned by SHA-256 in `scripts/updater.py`; preserve the vendor signatures of Sparkle's nested helpers.

## Packaging

Build normally with `scripts/package_release.py`. Create a ZIP containing the signed app using `ditto -c -k --keepParent`. Put its matching HTML release notes next to the ZIP, then run:

```sh
python3 scripts/make_update_feed.py /path/to/release-folder \
  --download-url-prefix https://github.com/Wanzho/mcd2-crossover/releases/download/v0.1.4/
```

Upload the archive at that exact URL and publish the generated, signed `appcast.xml` to the repository root. Do not edit the signed XML afterward. For a verified important bug fix, write the reason in its release notes and add `--critical`; do not label unverified battery mitigations as a confirmed fix.

## Validation

Disposable copies of both launchers updated from test build 1 to build 2 and relaunched successfully. Strict bundle verification passed. A modified signed feed was rejected. Tests cover setup/game/sign-in blocking, deferred replacement, the quit guard and recovery after the game closes. Wine process names come from `ps comm`, because `proc_pidpath` can report `explorer.exe` for unrelated Windows processes. The updater does not start Wine to inspect processes.

Long-running gameplay and unattended overnight updates have not been tested. No battery fix is claimed by this feature.
