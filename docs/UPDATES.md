# Native in-app updates

**Check for Updates…** queries this project's GitHub releases. **Automatically Check for Updates** checks when the app opens, at most once per day. An available release shows its notes and **Update Now**. Clicking it downloads, verifies, replaces and reopens the app; no manual DMG installation is needed in a writable Applications folder.

Only macOS Cocoa, Foundation and CryptoKit are used. There is no Sparkle runtime, update service or permanent polling process. The flow follows wasdmod's native updater. Older launcher releases need one initial manual upgrade to gain in-app updates.

## Trust and installation

Each release includes an app ZIP, `update.json` and `update.sig`. The signature is standard Ed25519 over the exact JSON bytes. A public key pinned in the app verifies the manifest; its SHA-256 and byte count bind the archive. Allowed HTTPS download and redirect hosts are restricted to GitHub. The extracted app must match the signed bundle ID, version and build and pass strict code-signature verification.

MCD1 opts into preview releases. MCD2 uses stable releases. Version comparison handles numeric components and preview identifiers.

The updater waits while Dungeons, sign-in or setup is running. A pending update blocks new launch/setup actions. The replacement uses an atomic directory swap and retains the old app until the new one confirms startup. A failed relaunch restores the old app. A read-only folder is reported without modifying the original. Game files, saved settings and account data are outside the replacement.

## Release assets

Build the app normally and create its ZIP using `ditto -c -k --keepParent`. Put plain-text release notes beside it. Generate the manifest and signature:

```sh
python3 scripts/make_update_feed.py --app '/path/MCD2 Crossover.app' \
  --archive /path/release/MCD2-Crossover-0.1.5-arm64.zip \
  --notes /path/release/notes.txt --signing-tool /path/to/sign_update
```

The existing maintainer-only `sign_update` command can sign the manifest using the existing Keychain key. It comes from Sparkle's release tools but is not linked, shipped or needed by users. Another standard Ed25519 signer can produce the same detached signature. Never export the release private key into an app or repository.

Upload the ZIP, `update.json` and `update.sig` to the matching GitHub release. Do not alter the manifest after signing. Set `--important` only for a verified important fix and explain it in the release notes. No permanent Wine battery fix is claimed by this updater.
