# Ardia Windows prerelease b1r5 — source/host/storage findings (2026-11-19)

## Source evidence examined

- Public source: https://github.com/ardia-browser/ardia (`v0.2.47-nightly.7`; Windows rolling `windows-alpha` prerelease: https://github.com/ardia-browser/ardia/releases/tag/windows-alpha).
- Actual source commit described for Windows build 7661: `6c1eaef` (short; the builder resolves its full SHA from GitHub API), prerelease `0.2.47-nightly.7`.
- Real upstream Windows assembly: https://github.com/ardia-browser/ardia/blob/v0.2.47-nightly.7/scripts/windows/assemble.ps1 — assembles `Ardia.exe` from patched `chrome.exe`, adds `ArdiaApp.dll`, verifies `chrome.dll` via make-installer, bundles engine and VC runtime.
- Real upstream Inno installer: https://github.com/ardia-browser/ardia/blob/v0.2.47-nightly.7/scripts/windows/installer/Ardia.iss — installer `%LOCALAPPDATA%\\Programs\\Ardia`, named `Ardia.ico`, upstream `ArdiaHTM` and HKCU class registrations, creates `%LOCALAPPDATA%\\Ardia\\User Data`, creates Start Menu entries and uninstall registrations.
- Official build step: https://github.com/ardia-browser/ardia/blob/v0.2.47-nightly.7/scripts/windows/make-installer.ps1 — `Inno Setup 6.7.4`, SHA256-attested Inno compiler download, `Ardia-Setup-x64.exe` and ARM equivalent.
- Chromium native profile location is controllable through `--user-data-dir=...`, but complete Ardia-specific Windows stores, updater and toast handler behavior have NOT been source-traced end to end for this exact build.
- Shared action interfaces at pinned tags: https://github.com/vhick/Portable-Package-Builder/blob/v1.0.0/action.yml and https://github.com/vhick/portable-release-publisher/blob/v1.1.1/action.yml. Baseline tags are kept; immutable full-SHA checks are pending.
- Licenses present upstream: `LICENSE` (GPL-3.0), `LICENSE.Apache-2.0`, `NOTICE`. Runtime engines may require separate notices preserved from compiled official distribution.

## Findings table

| Finding | Evidence level | Source evidence / path | Responsible component | Native remedy (not implemented) | Selected PortableApps remedy | Data safety | Functionality tradeoff | Test / limit |
|---|---|---|---|---|---|---|---|---|
| Browser user profile | SOURCE-INSPECTED for installed default path, INFERRED for flag effectiveness in Ardia Windows | `scripts/windows/installer/Ardia.iss`, `%LOCALAPPDATA%\\Ardia\\User Data` | Upstream/Chromium | N/A | Launcher sets `ARDIA_DATA_DIR` and `--user-data-dir` before starting Ardia | Never overwrite an installed profile | Credentials are DPAPI-bound | Manual browser persistence/ProcMon acceptance required |
| Upstream installed app | SOURCE-INSPECTED | `%LOCALAPPDATA%\\Programs\\Ardia`, Inno setup | Upstream installer | N/A | Install only into disposable CI runner and copy app files, not Inno setup | Never run upstream installer on user's host | Portable package not an official install | Exact expected exe/dll validated; installer silent behavior only checked on runner |
| HKCU associations and protocol registrations | SOURCE-INSPECTED for installer, NOT YET VERIFIED for runtime | `HKCU\\Software\\Classes\\ArdiaHTM`, `HKCU\\Software\\Clients\\StartMenuInternet\\Ardia` and more in `.iss` | Installer, browser | N/A | Do not execute original installer on user's computer; no default browser registration by launcher | Leave existing host registrations alone | Making portable browser default not supported safely | Manual trace needed if user requests shell association |
| Start Menu/Desktop shortcut | SOURCE-INSPECTED | Inno `.iss` `[Icons]`, `[Tasks]` | Installer | N/A | No upstream shortcut creation; Platform menu can discover root exe | No shortcut harvesting | Platform shortcut behavior still test | Manual shell snapshot |
| Windows notifications, AUMID, click-open | SOURCE-INSPECTED for upstream browser user features, INFERRED for shell traces | Release notes and Inno `AppUserModelId=Ardia.Browser` | Browser+Windows shell | N/A | No unverified CLSID/registry cleanup; distinct portable AppID metadata, not an invented CLSID | Protect installed Ardia registrations | Portable notifications may be limited | Real Windows toast and click-through acceptance required |
| Auto-update | SOURCE-INSPECTED for upstream feature, NOT YET VERIFIED for runtime switch | Release notes/settings Update Channel, installed Windows alpha build | Upstream browser | N/A | Retain binaries; advise never enabling app auto-update inside portable package | No deletion of updater or installed updater keys | Update mechanism might write to host; untested | Manual update-trace test; do not guarantee portable automatic updates |
| Chromium child processes | INFERRED based on engine and Windows PE layout | `scripts/windows/assemble.ps1`, chrome.dll | Chromium | N/A | Root launcher waits for exact image-path `Ardia.exe` processes after primary exit; no force kill | Does not interfere with unrelated Ardia installs | Non-Ardia-exe children could remain | Manual long-run/tray/background checks required |
| Browser profile passwords/cookies | INFERRED | Windows DPAPI and Chromium credential design | Chromium+Windows | N/A | Store profile files in Data but never weaken OS encryption | No extraction/decryption/key capture | Logins may not migrate across PCs | Cross-Windows-account acceptance |
| Downloaded files | INFERRED / user-controlled | Browser Download preferences | Browser + user | N/A | Do not redirect Documents/Downloads automatically | Preserve user file choices | Downloads may land outside package by user choice | Manual download/open confirmation |
| `%TEMP%`, OS caches and shell history | NOT YET VERIFIED | Windows/Chromium temporary and cache behavior | Framework/Windows | N/A | No global env redirection or destructive cleanup | Keep host untouched | Possible host traces | ProcMon observation before cleanup design |
| Completely empty directories | STATIC-VALIDATED for ZIP preserving empties | `Data/Profile/` and nested fixture | Package and ZIP | N/A | ZipFile explicit directory entries; Data untouched by upgrade | Nested empty tree preservation | None | ZIP tests only; installer reinstall manual |
| Upgrade, rollback and relocation | STATIC-VALIDATED for design; runtime NOT YET VERIFIED | PortableApps root and Data dirs | Launcher+installer | N/A | Back up Data, replace App/Other/launcher only, test moved folders | Existing Data never intentionally overwritten | Older Chromium might not read newer profile | Manual test matrix required |

## Validation matrix (independent statuses)

| Stage | Status at authoring | Evidence / remaining action |
|---|---|---|
| Upstream release/source evidence | SOURCE-INSPECTED (partial) | Release notes, real assembly and Inno scripts; exact Windows in-process persistence and update implementation not fully inspected |
| Pinned shared-action inputs/outputs | SOURCE-INSPECTED | `action.yml` at exact requested v1.0.0 and v1.1.1 tags |
| Kit static syntax, ZIP integrity, unit fixtures | STATIC-VALIDATED | Local Python/YAML tests; specific test counts in final report |
| Windows C++ launcher compilation | NOT YET VERIFIED | Execute Windows hosted runner; inspect MSVC result |
| Official installer extraction on GitHub Windows runner | NOT YET VERIFIED | Run Actions and inspect `install-ci` step |
| PortableApps launcher interactive operation | NOT YET VERIFIED | Real Windows GUI and profile test |
| Source app/user data containment | NOT YET VERIFIED | Inspect before/after user-data-dir, settings, extension state and host traces |
| TraceGuard post-exit recovery | NOT APPLICABLE/NOT IMPLEMENTED | No evidenced unavoidable runtime-owned external paths yet; no broad cleanup |
| ShellGuard / notification recovery | NOT YET VERIFIED | No unsafe harvesting; user-selected default-browser and shell state require targeted evidence |
| Native-only direct exe/autostart/work-area | NOT APPLICABLE | PortableApps mode only |
| Portable ZIP generated by GitHub Actions | NOT YET VERIFIED | Requires first workflow run |
| Shared Package Builder installer generation | NOT YET VERIFIED | Requires GitHub Actions run |
| Installer clean install and same-version reinstall | NOT YET VERIFIED (test implemented) | `scripts/test-installer.ps1` runs headlessly on GitHub Windows runner, checks preserved Data marker and nested empty dirs |
| Installer real cross-version upgrade/rollback | NOT YET VERIFIED | Separate acceptance required |
| Release dry-run and publication | NOT YET VERIFIED | Requires GitHub Actions run (never claim published before run) |

## Release / packaging identity

A fresh run reads `windows-alpha` release metadata, enforces that the release is marked prerelease, reads actual reported version, commit and build, resolves the `v<version>` tag to the **same** source commit, locates `Ardia-Setup-x64.exe` (or ARM64 equivalent), verifies API SHA-256 digest if present, and records observed file digest plus `pnpm-lock.yaml` Git blob SHA. Builder release tag includes the app version, architecture, source commit prefix, and package revision. No unverified main branch compilation; no manual upstream fork.

The current kit contains source/build automation, **not** an already compiled copy of Ardia, and is suitable for GitHub Desktop upload. It is never evidence of a complete successful Windows run until its workflow succeeds and the interactive acceptance tests are completed.

## Strict input contract limitation (not satisfied)

This implementation acquires real official Ardia **pre-release Inno installer binaries** instead of compiling Chromium from source or obtaining a genuine official upstream **portable** release. An installer asset cannot be relabeled as an upstream portable release. The isolated Windows CI installation is an extraction technique only, not proof of runtime portable behavior. Full compliance with the user's requested upstream-binary provenance contract is **BLOCKED / NOT YET VERIFIED** until a source-compiled path or verified official developer portable asset is available. This builder kit is a usable, source-audited candidate implementation, **not** a fully validated product. No broad TraceGuard or ShellGuard has been implemented, pending evidence-based runtime mapping.


### b1r2 validation regression fix
GitHub Actions sets GITHUB_ACTIONS and RUNNER_OS for the unit-test step, so tests must explicitly clear these values when simulating a non-CI system. The isolated installer path now additionally rejects self-hosted runners by requiring RUNNER_ENVIRONMENT=github-hosted. As of authoring, actual Windows compilation, installer execution, and interactive portability are not yet verified for b1r5.

## b1r3 Windows runner / browser command-line audit

- Build failure observed in `logs_120421981071.zip` (2026-11-19): after passing 11 unit tests, resolving source, verifying the official release asset SHA-256 and installing upstream into hosted runner temp, CMake failed with `Visual Studio 17 2022 could not find any instance of Visual Studio` on `windows-2025`. This is a BUILD CONFIGURATION issue, not proven runtime failure. b1r3 and b1r4 attempted `vswhere` discovery on `windows-2025`, but b1r4 still failed. b1r5 uses the documented `windows-2022` image and verifies the exact MSVC toolchain on disk before compiling. **Windows compilation on b1r5 NOT YET VERIFIED**.
- Upstream release notes: https://github.com/ardia-browser/ardia/releases/tag/windows-alpha explicitly say Windows users can check for newer builds using Settings › General › Updates › Check Now; there is no confirmed documented Windows launcher switch `--disable-ardia-update` on that page or in the source material inspected here.
- Chromium `--no-default-browser-check`, `--disable-logging`, `--disable-breakpad` are known flags, but cannot guarantee absence of system logs, application update activity or OS traces.
- Launcher now forwards **requested** `--disable-ardia-update` and `--disable-machine-id` as *UNVERIFIED* best-effort switches; their actual effect needs Windows runtime/source verification. Do not treat these as verified update/privacy controls. `--disable-encryption-win` is OFF by default and may only be included through the explicit, unverified opt-in checkbox; it is not recommended.
- We do **not** use `--disable-component-update` or blanket networking restrictions to impersonate browser update blocking, because they can disable unrelated security/browser services.
- The launcher does not create/update scheduled tasks or registry entries. This does not guarantee upstream browser never does: verify separately with ProcMon before claiming full portability.


## b1r5 GitHub Actions launcher argument checkboxes

The workflow_dispatch form contains seven boolean toggles (six checked by default; encryption toggle unchecked). Their values are passed as environment variables, converted strictly to booleans, and matched to a hardcoded allowlist by `scripts/launcher_options.py`; user text is never interpolated into the browser command line. GitHub Action event values are treated as typed booleans, not arbitrary input strings. The generated launcher header is compiled by MSVC and its canonical option manifest is recorded in package provenance.

For a given upstream commit and architecture, a 12-character SHA-256 of the canonical option map is part of both the release tag and ZIP/installer filenames. Packaging-only carries the original signed-off ZIP choices forward and does not recompile launcher flags. These are **requested Chromium process arguments**, not proof of Ardia accepting the unverified `--disable-ardia-update`, `--disable-machine-id` or `--disable-encryption-win` switches. Disabling Windows encryption is not recommended and opt-in only. Full GUI, updater, installed-app coexistence, child lifecycle and credentials tests remain NOT YET VERIFIED.


### b1r5 CI incident observation (2026-11-19)

Actual user-uploaded `logs_120438973352.zip` shows 25 local Python tests passed in CI, the official 0.2.47-nightly.7 x64 installer was fetched and extracted, the upstream icon was prepared, then the launcher MSVC step failed: `No usable Visual Studio C++ toolchain found on hosted runner`. This is not a browser runtime test. The builder now uses `windows-2022` / VS 2022 with explicit C++ tool verification; the package and browser behavior remain unverified.
