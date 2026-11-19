# b1r6 validation evidence — November 19, 2026

## Status at builder-kit authoring

- **SOURCE-INSPECTED / USER-OBSERVED:** Local and Roaming installed Ardia directory layout in user-supplied Windows Explorer screenshots. The observed paths are from a NORMAL installation, not a portable test.
- **STATIC-VALIDATED:** Python regression tests passed (35 tests); PyYAML parsed both workflow definitions; Python scripts syntax-compiled; generated application staging fixture used authentic layout directories and preserved empty ZIP directory entries; prior b1r5 package validation compatibility remained testable.
- **STATIC-VALIDATED:** Host junction guidance is opt-in and not executed by CI. C++ launcher source contains guarded `ARDIA_DATA_DIR`, APPDATA, LOCALAPPDATA and `--user-data-dir` selection before browser initialization and keeps populated b1r5 `Data/Profile` on its old path. Source has conflict/reparse checks. These are **source checks, not Windows executable tests**.
- **NOT YET VERIFIED:** GitHub-hosted Windows/MSVC compilation for b1r6; browser GUI first run, actual Chromium and Ardia data paths; complete Local/Roaming path redirection; embedded updater, shell/notification traces, installed-app coexistence, junction behavior, empty directories under real runtime, installer reinstall with actual b1r6 package, release publication and crash recovery.
- **BASELINE USER-CONFIRMED:** b1r5 worked for this user. That confirms earlier workflow/package functionality to the user's satisfaction but does not validate b1r6's new data layout.

## What must pass on a Windows desktop before declaring b1r6 successful

1. Build b1r6 with GitHub Actions on `windows-2022` using unchanged checkbox selections, confirming MSVC compilation and shared custom-NSIS installer steps.
2. Test **fresh portable** b1r6 with no existing `Data/Profile`. Inspect the new `Data/Local/Ardia/User Data` and `Data/Roaming/Ardia` folders before/after launch and exit.
3. Compare user-installed `%LOCALAPPDATA%/Ardia` and `%APPDATA%/Ardia` via Process Monitor with parent/child PIDs. Do not silently erase host traces.
4. Backup a working b1r5 `Data`, update binaries only, verify b1r6 continues opening its existing `Data/Profile`, retaining session/bookmarks/preferences.
5. Reproduce the conflict case (both legacy and new profiles populated) and confirm b1r6 refuses to launch rather than overwriting/merging either.
6. On disposable test profile ONLY, test optional host-to-portable junctions after backing up original installed Ardia paths. Verify the launcher refuses to start if installed Ardia is already running, then verify normal restart when all instances are closed.
7. Test manual unlink/recovery of installed originals and backups, folder relocation and account-specific credential limits.
8. Check installer upgrade/reinstall against markers under BOTH `Data/Local` and `Data/Roaming`, including nested empty folders.

## Nonconformances carried forward

- Ardia's official Windows pre-release is an *installer*, not a verified source-built portable release. This kit continues using an official installer from an isolated CI runner, as b1r5 did. It does not meet the user's stricter source-built-or-official-portable input requirement.
- Complete app-owned storage / Windows shell trace confinement, notifications, updater suppression and self-update blocking are not verified.
- `--disable-ardia-update` and `--disable-machine-id` are still unverified as accepted switches; `--disable-encryption-win` remains unchecked by default. Compiler flags are controlled by seven GitHub Actions checkboxes.
