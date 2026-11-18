# Source audit, portability findings and acceptance — b1r3

## Sources inspected (Nov 18, 2026)

Official upstream: `https://github.com/ardia-browser/ardia`; versioned Windows release example `v0.2.47-nightly.3`. Versioned Windows x64 and ARM64 are supplied as **per-user Inno Setup installers**, not proven portable binaries. The main repository is predominantly macOS with a Windows React Native Windows application, Chromium 157/Helium engine and pnpm lockfile. Windows compilation follows `.github/workflows/windows.yml`: Node 24; pnpm; `npx react-native run-windows --release --arch x64 ...`; `fetch-engine.ps1` using `scripts/windows/engine/prebuilt.json` pinned SHA256; `assemble.ps1` to merge compiled `ArdiaApp.dll` and prebuilt engine into `Ardia.exe`/`chrome.dll`.

## Evidence-specific findings

| Finding | Source evidence | Path | Component | NATIVE remedy | PORTABLEAPPS remedy | Data safety | Tradeoff | Test | Limitation/status |
|---|---|---|---|---|---|---|---|---|---|
| App local storage defaults to host | `apps/browser/windows/Ardia/Paths.h`, `DataDirectory()` | `%LOCALAPPDATA%\Ardia` | Ardia Windows | Not selected | launcher sets `ARDIA_DATA_DIR=Data\Ardia` prelaunch | no existing host folder copied/deleted | none expected | first launch, settings/relaunch | SOURCE-INSPECTED; GUI untested |
| App configuration | upstream `launch-smoke.ps1` `ARDIA_CONFIG_DIR` set alongside data | app-selected directory | Ardia Windows | Not selected | same folder `Data\Ardia` | isolated custom config | none expected | config save/restart | SOURCE-INSPECTED; actual runtime untested |
| Engine browser profiles | upstream Windows `launch-smoke.ps1` and `Paths.h`; references `DataDirectory()/Chromium` and `--user-data-dir` gate | app-selected `Chromium` child | Ardia/Chromium | Not selected | use documented data env; do NOT force arbitrary external profile switches | no profile harvesting | user-supplied profile override blocked | browsing/bookmarks/login | INFERRED complete containment; must observe |
| App identity for taskbar/notifications | `AppIcon.h` fixed `kAppUserModelId=L"Ardia.Browser"`, `Ardia.cpp` installs notifications | AUMID, Windows-managed caches and possible CLSID | Windows shell / Ardia | Not selected | leave runtime registrations alone pending isolated acceptance | never remove installed-app AUMID | portable and installed identities may overlap | notification/click-to-open with installed app | SOURCE-INSPECTED, unresolved coexistence |
| Installer browser registrations | upstream `scripts/windows/installer/Ardia.iss` | HKCU Classes, RegisteredApplications, Start Menu shortcut | Upstream installer ONLY | Not selected | don't include/re-run upstream installer; shared independent NSIS creates portable package | host entries not copied | portable not default browser | before-first-run checks | SOURCE-INSPECTED; installer runtime untested |
| Automatic updates | Windows release notes, upstream Windows install and relaunch scripts | normal installed user app paths | Upstream app/installer | Not selected | updates via builder only; self-update avoided until tested | retains Data on package replacement | in-app update disabled by user behavior only | check update menu without performing install | SOURCE-INSPECTED; unresolved host-change risk |
| Credentials | Chromium/Windows OS encrypted browser state | portable Data + Windows OS credential protection | Chromium / Windows | Not selected | profile stored locally, no unsafe crypto bypass | never decrypt, no host credential migration | cross-account password mobility unverified | login/restart/USB drive | NOT YET VERIFIED |
| Empty directories and crash | source app-selected portable data root | `Data\Ardia` | Ardia/launcher | Not selected | direct redirection; ZIP includes empty Data directory; no scavenging | no host deletes/overwrites | no host recovery if unseen writes | empty tree / crash / restart | STATIC-VALIDATED ZIP only |

## Acceptance and evidence boundaries

| Stage | Status at kit creation |
|---|---|
| Source mechanisms and build chain | SOURCE-INSPECTED |
| Python source resolver tests | STATIC-VALIDATED (4 tests) |
| Kit ZIP integrity | STATIC-VALIDATED when generated |
| Compiler / real root launcher in Windows | NOT YET VERIFIED |
| Upstream source build | NOT YET VERIFIED |
| Independently validated finished PortableApps ZIP | NOT YET VERIFIED |
| Actual PortableApps launcher, browser profile persistence | NOT YET VERIFIED |
| TraceGuard recovery | NOT APPLICABLE to intentionally redirected paths; residual host writes NOT YET VERIFIED |
| ShellGuard / notification identity | NOT YET VERIFIED / UNRESOLVED |
| Background processes and complete exit | NOT YET VERIFIED |
| Windows self-update and host registration | NOT YET VERIFIED / UNRESOLVED |
| Installer generation | NOT YET VERIFIED |
| Installer reinstall / upgrade without Data loss | NOT YET VERIFIED |
| Shared Release Publisher | Source interface checked, publication NOT YET VERIFIED |
| Windows manual USB/Unicode/relocation tests | NOT YET VERIFIED |

## Manual Windows acceptance (separate test account/VM recommended)

1. On a clean Windows 11 x64 VM, create folder `C:\Portable Test\ArdiaPortable`, extract the generated ZIP. Confirm no upstream Ardia installer is run on this VM.
2. Optional read-only host baseline: `pwsh -File scripts/manual-snapshot.ps1 -Phase before -Folder audit`. This script is in the **builder kit**, not generated browser ZIP.
3. Double-click `ArdiaPortable.exe`. Complete onboarding, change settings, create bookmarks, install an extension, browse, download a file into a user-chosen portable destination, log in if safe with test accounts, then close ALL Ardia windows and verify child processes have exited.
4. Verify `%LOCALAPPDATA%\Ardia`, `%APPDATA%\Ardia`, desktop/startup shortcuts and HKCU browser registration differences against the baseline. Never delete or move ambiguous pre-existing files. Repeat the read-only snapshot with `-Phase after` and compare.
5. Relaunch, check settings, bookmarks, history, extensions and sessions. Confirm `Data\Ardia` contains profiles, databases, cache and nested empty trees created by the app. Check password mobility across Windows accounts separately; DPAPI may limit it.
6. Repeat from a path with Unicode characters/spaces and a changed drive letter, fully closed between tests. Confirm data stays with the folder.
7. Install standard Ardia into a **separate test user/account**, then test portable and installed browsers side-by-side using `--allow-installed-coexistence-test` only inside that disposable VM; normally the launcher blocks registered installed Ardia. Check AUMID, taskbar icon grouping, notifications, clicking notifications, and installed app browser registrations. If shared AUMID causes problems, **do not publish as fully compliant**.
8. Test abnormal termination with only test data. Reopen; confirm profile integrity and no user data lost. Do not force-kill real personal browser sessions.
9. Test the PortableApps-style installer in a clean VM, verify no unexpected host registrations, close Ardia, reinstall/upgrade into same directory and compare Data file hashes and empty directory list. Perform rollback with a matching Data backup if schema changed.
10. Do **not** test the built-in updater on a real installed or personal account. Use an isolated disposable VM and separately inspect whether it launches the standard installer.

**Release policy:** CI compilation/ZIP/installer success indicates only the separately tested stages passed. These manual acceptance checks are needed before labeling runtime portability USER-CONFIRMED.

## b1r2 experimental switch acceptance (not yet runtime verified)

The compiled launcher adds the six experimental default switches in `launcher/ArdiaLaunchFlags.h`. A portable-only `--portable-no-default-flags` option allows a clean comparison without them. No source inspection proved that Ardia recognizes the update-disabling, machine-ID or encryption switches; the last two originated in patched Brave/Chromium ecosystems. Never treat switch presence as proof of effect.

On a disposable Windows VM and brand-new Ardia profile:

1. Start portable Ardia normally. If Chromium's `chrome://version` is supported, inspect its command-line line for the six switches.
2. Exit all browser processes; relaunch with `ArdiaPortable.exe --portable-no-default-flags`. Check that the six default switches are absent, and existing `Data` remains in place.
3. Run browser settings, bookmarks, profile persistence and normal restart checks in both modes. Confirm no regression.
4. Compare updater UI behavior; do **not** launch the normal Windows installer. A switch named `--disable-ardia-update` does not establish the updater was disabled.
5. For encryption testing, use **only fake credentials**, and check whether any Windows/OS-level encryption changes; do not use real passwords to infer safety.
6. Check default-browser associations, crash reporting, logging and installed-browser coexistence separately, without deleting any host state.

Evidence: **C++ UNIT-TESTED locally** for command-line assembly; **NOT YET VERIFIED** for actual Ardia switch support, Windows GUI, updater suppression, cross-device credential portability and security consequences.


## b1r3 dependency availability and fallback acceptance

- **SOURCE-INSPECTED (upstream):** Each source version ships `scripts/windows/engine/prebuilt.json` with a release tag, an x64 engine archive name and a SHA-256. `scripts/windows/fetch-engine.ps1` downloads the named archive with `gh release download` and verifies the archive hash before extraction.
- **USER GITHUB LOG OBSERVATION (b1r2):** Windows source compilation passed; the engine fetch failed because upstream release `windows-engine-20261116-4` was not publicly accessible. This is not evidence about launcher or browser runtime.
- **STATIC-VALIDATED (b1r3):** New resolver reads the manifest from the candidate's immutable source SHA and uses GitHub release/asset metadata to reject inaccessible engine releases before compilation. A later Windows source-check step verifies the local manifest hash and engine identity match preflight.
- **OFFLINE-UNIT-TESTED:** Synthetic GitHub response fixtures exercise missing engine 404, fallback to an earlier official release, exact-version fail-closed, mismatched engine checksum, missing asset, malformed manifest path, GitHub 403, and channel preference.
- **NOT YET VERIFIED:** The b1r3 workflow has not executed on GitHub Actions. Successful metadata lookup cannot guarantee actual network download of a large engine ZIP or its SHA-256. The unmodified upstream fetch script enforces the archive hash. GUI runtime, profile persistence, shell modifications and installer upgrade behavior remain manual Windows acceptance tasks.

Suggested b1r3 acceptance steps: (1) Run `channel=nightly`, blank `version` and inspect the preflight log for skipped tags. (2) If none qualify, confirm the workflow stopped before `pnpm install` and C++/React Native compilation. (3) If one qualifies, confirm source commit and manifest SHA checks before build, followed by upstream engine ZIP hash verification. (4) Only after a validated ZIP and installer exist, run the original manual profile/session, restart, notification, installed-app coexistence and upgrade tests.
