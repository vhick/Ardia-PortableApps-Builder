## b1r9 mixed-version checkout acceptance

- **LOG-OBSERVED (b1r8 GitHub run):** Step 4 ran 41 Python tests: 39 passed, 2 failed. `tests/test_local.py` still asserted `b1r7` against a `b1r8` workflow. The first failure occurred before the Windows MSVC fixture or application compilation.
- **SOURCE-INSPECTED (b1r8 distribution ZIP):** The distributed kit already expected `b1r8`. A GitHub checkout did not have the same test file as the ZIP. Root cause of the incomplete upgrade is not independently verified.
- **STATIC-VALIDATED (b1r9):** Before test discovery, `scripts/check-builder-revision.py` checks `BUILDER_REVISION` against workflow installer revision, release titles, resolver, staging, README, metadata and tests. Controlled fixtures reject stale b1r7 test files, wrong installer revision and missing workflow.
- **NEXT WINDOWS CHECK:** The first new step must report `STATIC-VALIDATED: b1r9 builder revision is consistent...`, then all Python tests pass, followed by the batch-quoting and MSVC fallback tests. No browser or installer runtime verification is implied by these checks.

## b1r8 Windows MSVC initialization acceptance

- In CI, "Verify CMD batch quoting" should pass as it did in the b1r7 run.
- Next, "Test isolated MSVC initializer fallback" must print the deliberate primary failure, select the secondary fixture, and fail safely when no initializer is available. This is NOT a real compiler test.
- "Verify Windows x64 MSVC toolchain" must show diagnostics from `VsDevCmd.bat` and/or `vcvars64.bat`, then compile/link/run an actual C++ fixture. If both fail, stop before downloading upstream dependencies and retain the visible error messages.
- `test-launch-flags.ps1` and `compile-launcher.ps1` must use the same initializer selection and fail closed on true compiler errors. Do not treat any of this as browser runtime validation.

# Source audit, portability findings and acceptance — b1r7

## Sources inspected (Nov 18, 2026)

Official upstream: `https://github.com/ardia-browser/ardia`; versioned Windows release example `v0.2.47-nightly.3`. Versioned Windows x64 and ARM64 are supplied as **per-user Inno Setup installers**, not proven portable binaries. The main repository is predominantly macOS with a Windows React Native Windows application, Chromium 157/Helium engine and pnpm lockfile. Windows compilation follows `.github/workflows/windows.yml`: Node 24; pnpm; `npx react-native run-windows --release --arch x64 ...`; `fetch-engine.ps1` using `scripts/windows/engine/prebuilt.json` pinned SHA256; `assemble.ps1` to merge compiled `ArdiaApp.dll` and prebuilt engine into `Ardia.exe`/`chrome.dll`.

## Evidence-specific findings

| Finding | Source evidence | Path | Component | NATIVE remedy | PORTABLEAPPS remedy | Data safety | Tradeoff | Test | Limitation/status |
|---|---|---|---|---|---|---|---|---|---|
| App local storage defaults to host | `apps/browser/windows/Ardia/Paths.h`, `DataDirectory()` | `%LOCALAPPDATA%\Ardia` | Ardia Windows | Not selected | launcher sets `ARDIA_DATA_DIR=Data\Ardia` prelaunch | no existing host folder copied/deleted | none expected | first launch, settings/relaunch | SOURCE-INSPECTED; GUI untested |
| App configuration | upstream `launch-smoke.ps1` `ARDIA_CONFIG_DIR` set alongside data | app-selected directory | Ardia Windows | Not selected | same folder `Data\Ardia` | isolated custom config | none expected | config save/restart | SOURCE-INSPECTED; actual runtime untested |
| Engine browser profiles | upstream Windows `launch-smoke.ps1` and `Paths.h`; references `DataDirectory()/Chromium` and `--user-data-dir` gate | app-selected `Chromium` child | Ardia/Chromium | Not selected | use documented data env; do NOT force arbitrary external profile switches | no profile harvesting | user-supplied profile override blocked | browsing/bookmarks/login | INFERRED complete containment; must observe |
| App identity for taskbar/notifications | `AppIcon.h` fixed `kAppUserModelId=L"Ardia.Browser"`, `Ardia.cpp` installs notifications | AUMID, Windows-managed caches and possible CLSID | Windows shell / Ardia | Not selected | leave runtime registrations alone pending isolated acceptance | never remove installed-app AUMID | portable and installed identities may overlap | notification/click-to-open with installed app | SOURCE-INSPECTED, unresolved coexistence |
| Installer browser registrations | upstream `scripts/windows/installer/Ardia.iss` | HKCU Classes, RegisteredApplications, Start Menu shortcut | Upstream installer ONLY | Not selected | optional silent original install in **ephemeral CI runner temp** only; copy binary files, never registrations; shared independent NSIS creates portable package | runner entries never packaged | portable not default browser | before-first-run checks | SOURCE-INSPECTED; installer runtime untested |
| Automatic updates | Windows release notes, upstream Windows install and relaunch scripts | normal installed user app paths | Upstream app/installer | Not selected | updates via builder only; self-update avoided until tested | retains Data on package replacement | in-app update disabled by user behavior only | check update menu without performing install | SOURCE-INSPECTED; unresolved host-change risk |
| Credentials | Chromium/Windows OS encrypted browser state | portable Data + Windows OS credential protection | Chromium / Windows | Not selected | profile stored locally, no unsafe crypto bypass | never decrypt, no host credential migration | cross-account password mobility unverified | login/restart/USB drive | NOT YET VERIFIED |
| Empty directories and crash | source app-selected portable data root | `Data\Ardia` | Ardia/launcher | Not selected | direct redirection; ZIP includes empty Data directory; no scavenging | no host deletes/overwrites | no host recovery if unseen writes | empty tree / crash / restart | STATIC-VALIDATED ZIP only |

## Acceptance and evidence boundaries

| Stage | Status at kit creation |
|---|---|
| Source mechanisms and build chain | SOURCE-INSPECTED |
| Python source resolver + integrity tests | STATIC-VALIDATED (36 tests) |
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


## b1r4 engine/setup fallback acceptance

- **LOG-OBSERVED (b1r3):** All 18 resolver tests passed, then the engine dependency gate reported 404 for `windows-engine-20261116-4`, `windows-engine-20261116-2`, `windows-engine-20261115-7`. No application compilation or portable ZIP occurred in that run.
- **SOURCE-INSPECTED:** An upstream exact-tag official Windows setup is available in versioned releases. The separate `windows-alpha` release moves forward and is not used as a source substitute.
- **STATIC-VALIDATED (b1r6):** Resolver selects a public engine when possible, else only a verified official *same-tag* Windows setup with strict download URL, asset name, ID, SHA-256 digest and source SHA controls. Setup hash is verified before compilation. The original manifest hash is rechecked after checkout.
- **OFFLINE-TESTED:** Python fixture tests cover same-tag fallback, digest absence, wrong URL, foreign asset metadata, mismatched engine SHA, GitHub 403 and numeric version sorting. C++ launcher tests retained from b1r2.
- **NOT YET VERIFIED:** Windows `7z`/Inno unattended extraction, exact Chromium file-version match, actual assembly, executable startup, notifications, process shutdown, shell and registry traces, ZIP installer behavior and release publication.
- **CI SAFETY:** 7-Zip extraction is preferred; Inno silent `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /DIR=...` is a fallback limited to a temporary folder in a hosted runner (runner-only transient registrations may occur). No upstream setup program is executed on the user's computer. Test in a disposable VM before personal use.

Suggested b1r6 steps: (1) Run `channel=nightly` with blank version. (2) Verify preflight chooses `official_setup` and the **GitHub-published setup SHA-256** matches the downloaded file before app compilation. (3) Review the engine extraction and Chromium-version step, then app assembly and headless dependency verifier. (4) Only use a resulting ZIP/installer after independent interactive profile, restart, notification and update tests.

## b1r6 source-check regression acceptance

- **LOG-OBSERVED (b1r4):** Windows preflight resolved nightly.5 and the exact official setup fallback. Step 7 compared the Windows working-tree `prebuilt.json` SHA-256 `ad913cc115cafc7e7b2f5a681fb19796301153fa7e6137c7ba056639c0294960` with preflight blob SHA-256 `9c3ec2a097531903beef9e4de089527bdd496a988fe62e4ce295cc711ff303dd` and failed. No setup download or source build ran. Windows line-ending conversion is a plausible cause but not conclusively observed in the log.
- **STATIC-VALIDATED (b1r6):** `scripts/verify-source-content.py` uses binary Git object content to validate original preflight SHA-256 and Git blob identity; only worktree CRLF/LF changes are permitted, while real content tampering and mismatched metadata remain fatal. Local regression fixtures test the acceptance and rejection behavior.
- **NOT YET VERIFIED:** A real b1r6 Windows Action run that reaches the setup downloader, source compilation, assembly, installer and publication; interactive portability testing stays outstanding.

To check a b1r6 GitHub run, look for `SOURCE-INSPECTED: immutable engine manifest SHA-256 ... (worktree: line-ending-only)` in Step 7. `byte-identical` is also acceptable. If the immutable Git object hash itself differs, stop and inspect the chosen commit; do not bypass integrity protection.

## b1r6 Windows MSVC preflight — log-grounded evidence

- **LOG-OBSERVED (b1r5):** `logs_120043181553.zip` shows runner `windows-2025-vs2026 20261103.298.1`; resolver/integrity tests passed (31), immutable source manifest was verified, and SHA-256 of the original official x64 setup matched GitHub metadata. Step 10 failed at `scripts/test-launch-flags.ps1:7` because its `vswhere -requires` query did not identify an MSVC toolchain. No Ardia source compilation, Windows launcher compilation, ZIP, installer or release occurred in that run.
- **STATIC-VALIDATED (b1r6):** Hosted runner changed from `windows-latest` to documented `windows-2022` with Visual Studio 2022 C++ tools. `scripts/msvc-tools.ps1` discovers a complete compiler across compatible VS installs. `scripts/verify-msvc.ps1` compiles and runs a minimal C++ smoke-test before the large setup download. Both the launcher argument tests and its real compiler use the same shared lookup.
- **NOT YET VERIFIED:** Actual `windows-2022` toolchain preflight, source build, engine extraction, compiled launcher, portable browser ZIP, NSIS package, GitHub release and manual Windows portability behavior are pending a new Actions run. A static test is not a Windows compiler execution.


## b1r7 — MSVC cmd.exe quoting correction

- **LOG-OBSERVED (b1r6):** `logs_120055928085.zip` passed all 36 offline Python tests; runner `windows-2022` detected `C:\Program Files\Microsoft Visual Studio\2022\Enterprise`. The MSVC batch preflight failed with CMD errors (`'"'`, `'C:\Program'`, `'" >nul'` not recognized) and exit code 21. This is a batch invocation/quotation failure, not evidence of a missing compiler.
- **STATIC-VALIDATED (b1r7):** Added shared `Invoke-ArdiaMsvcBatch`, feeding raw `/D /S /C ""absolute path.cmd""` into .NET `ProcessStartInfo.Arguments`. All three compiler scripts use it and check the process's explicit exit code.
- **NOT YET VERIFIED:** New Windows workflow step runs a command quoting regression in a path containing spaces and verifies a sentinel and deliberate nonzero exit code. Compiler preflight compiles/runs a fixture in a path containing spaces. These require a real Windows Actions run to be marked pass.
- Browser source compilation, profile portability, ShellGuard/TraceGuard, notifications, installer execution and release publication remain not verified.
