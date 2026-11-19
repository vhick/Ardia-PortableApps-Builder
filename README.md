# Ardia PortableApps Windows x64 — Source-Builder Kit b1r9

## b1r9 — protect against incomplete upgrades (stale b1r7 tests in the b1r8 GitHub run)

**LOG-OBSERVED:** On the b1r8 GitHub run (`logs_120282255983.zip`), unit tests failed before Visual Studio checks because the repository's `tests/test_local.py` still expected `b1r7`. The distributed b1r8 ZIP already contains the b1r8 version of that test. This discrepancy indicates a *mixed-version checkout*, not an Ardia or MSVC failure. b1r9 includes a new `BUILDER_REVISION` file, a fail-fast consistency check before testing, and dynamic test expectations. If an older file remains after extraction, GitHub Actions names it and asks for a complete overwrite.

**Important with GitHub Desktop:** Extract all kit contents **directly** into the cloned repository root, not into an `Ardia-PortableApps-Builder-Kit-b1r9` subdirectory. Enable replacement/overwrite of existing files. Check that `tests/test_local.py`, `tests/test_msvc_preflight.py`, `.github/workflows/build.yml`, `BUILDER_REVISION`, and `scripts/check-builder-revision.py` are committed together; push the commit and make sure the new workflow run shows its commit SHA. No manual Git initialization, upstream fork, compiler or installer is needed locally. Run `python scripts/check-builder-revision.py` locally if Python is available, or rely on the early Windows runner check.

**Status:** b1r9's static/offline consistency fix is locally testable; the b1r8 workflow did not reach the b1r8 new MSVC initializer fixtures. Windows application compilation and actual portable browser acceptance still require a complete run.

## b1r8 — isolate Visual Studio initialization failures with documented fallback

**LOG-OBSERVED:** b1r7 GitHub Actions (`logs_120277176694.zip`) passed 38 local Python tests, the real Windows CMD spaced-path/exit-code test, and Visual Studio 2022 discovery; the preflight then failed exit 21 while calling `vcvars64.bat`. Because b1r7 redirected initializer stdout to `nul`, the log cannot identify why that batch returned an error. Ardia did not reach compilation.

**Fix:** Try Microsoft's documented `VsDevCmd.bat -arch=amd64 -host_arch=amd64 -no_logo` first, and `vcvars64.bat` only as a second independent initialization method. Each runs in a new `cmd.exe` process; initialization output and errors are visible in GitHub Actions. Only failures to initialize the toolchain or find `cl.exe`/`link.exe` trigger fallback. Actual C++ compile/link/test errors stop immediately rather than being mislabeled as toolchain failures. The identical helper drives all three real C++ steps.

A controlled Windows fixture checks fallback, separate process environments, and fail-closed behavior before the real MSVC smoke test. **This does not claim b1r8 MSVC or Ardia compilation succeeded.** The actual `cl.exe` preflight must compile, link and execute a small C++ program before source download/build proceeds. All six experimental switches and `Data\Ardia` remain unchanged.

## b1r7 — fix Windows CMD/MSVC batch quoting with spaces

**LOG-OBSERVED:** b1r6 GitHub Actions `logs_120055928085.zip` reached Visual Studio
2022 (`C:\Program Files\Microsoft Visual Studio\2022\Enterprise`) and passed all
36 Python tests, but the initial compiler probe failed with exit code 21.
Windows reported `'"' is not recognized`, `'C:\Program' is not recognized`,
and `'" >nul' is not recognized`. This is an incorrect nested CMD command
invocation, **not missing MSVC**.

**Fix:** `msvc-tools.ps1` now has a single `Invoke-ArdiaMsvcBatch` helper that
passes a double-quoted batch path directly through .NET's
`ProcessStartInfo.Arguments` as `/D /S /C ""path with spaces.cmd""`, bypassing
PowerShell's native command-line argument re-quoting. The preflight, launcher
argument tests, and final launcher compiler all use this helper. The workflow
also runs a new standalone batch-path/exit-code regression before any costly
downloads, then compiles and executes a trivial C++ fixture in a deliberately
spaced directory. Compiler results are judged by the real process exit code.

**Evidence:** offline static/source checks and C++ flags are locally testable;
actual Windows CMD invocation, Ardia source compilation, installer and GUI
behavior have **not yet been verified** for b1r7. All six requested
launcher flags remain unchanged. `Data\Ardia` profile handling and strict same-tag engine
fallback are unchanged.

## b1r6 MSVC toolchain compatibility and preflight

**Observed issue:** the b1r5 GitHub Actions run used `windows-latest`, which resolved to
`windows-2025-vs2026` (image 20261103.298.1). Before compiling the browser,
`test-launch-flags.ps1` reported `MSVC C++ compiler is unavailable`. This is a
compiler discovery issue, **not evidence that the browser or launcher failed to compile**.

**Change:** `.github/workflows/build.yml` now requests `windows-2022` (Visual Studio
2022 with supported VC x64 tools), rather than the mutable `windows-latest` alias.
The new `scripts/msvc-tools.ps1` is shared by `verify-msvc.ps1`,
`test-launch-flags.ps1` and `compile-launcher.ps1`. It queries `vswhere` with the
VC component requirement, enumerates other installations if that query returns
nothing, and requires `vcvars64.bat` **and** a real x64 `cl.exe` before selecting
a toolchain. The preflight actually invokes `cl.exe` on a minimal C++ fixture, failing **before** the
large upstream setup download if toolchain setup fails. It does not install
compilers, modify host registry settings, or request elevation.

The b1r6 Windows Actions log verifies MSVC discovery under Visual Studio 2022,
but the subsequent batch invocation failed before any C++ compilation. The
b1r7 invocation fix and its regression test still require a new Windows run.


**Mode:** PORTABLEAPPS only. The ZIP you are downloading is the **builder source kit**, not a precompiled browser. GitHub Actions builds the browser and its genuine Windows C++ portable launcher and creates the actual ZIP and `.paf.exe` installer.

**Status:** b1r7 passes 38 offline Python tests (including Windows CRLF checkout, source-tampering, and new CMD-quoting wiring assertions) and local C++ flag tests. The new b1r6 GitHub Actions log passed 36 earlier tests and found VS2022, but failed at CMD batch quoting before app compilation. **b1r7 has not been executed in Windows Actions.** Real browser startup, USB relocation, notification compatibility, installed-app coexistence and installer execution remain unverified. Do not treat this kit as an official PortableApps.com distribution.

## User setup using GitHub Desktop

1. Sign in to GitHub and create a NEW, empty repository such as `Ardia-PortableApps-Builder`. Do **not** fork upstream Ardia. Choose Public if releases should be public; otherwise choose Private.
2. In GitHub Desktop, **File > Clone Repository** and choose this new builder repo. It can be an empty repo. Do not run `git init` or install a local compiler.
3. Extract this entire ZIP **into the cloned repository root**. Confirm the hidden `.github/workflows/build.yml` exists at the root and `README.md` sits beside it. Do not nest it inside another folder.
4. In GitHub Desktop, enter a commit summary, click **Commit to main**, then **Push origin**.
5. On your GitHub repository page, go to **Actions > Ardia PortableApps Source Builder > Run workflow**. Leave `version` blank for automatic release selection. `channel=auto` prefers a stable Windows x64 release, falling back to a versioned nightly if no Windows stable exists. Set `nightly` to always pick nightlies. An exact `v0.2.47-nightly.3` can be requested as long as its source release remains accessible.
6. The initial preflight checks the exact source and engine. If its dedicated engine release is unavailable, the builder uses the **same source-tag’s official Windows setup** only when GitHub publishes a SHA-256 digest. The setup is downloaded and hash-checked **before compiling**. If no verified source is available, it fails without compiling. Leave `version` blank to allow older versioned-nightly fallback, or set an exact tag to prohibit fallback. Leave `publish=true` to publish **only validated ZIP and installer** using the pinned publisher. The publisher first performs a `dry-run=true` check. Set `publish=false` to build/test without publishing.
7. Open the workflow run. Separate lines describe source resolution, Windows source compilation, engine SHA-256 validation, launcher compilation, static ZIP validation, installer generation, and publication.
8. If it succeeds, visit **Releases** in this BUILDER repository and find the newly published portable release for this source version. Download the `ArdiaPortable_...zip` or PortableApps-style `.paf.exe`. GitHub Release supplies `SHA256SUMS.txt`.
9. **ZIP:** extract `ArdiaPortable/` into the desired PortableApps location and launch `ArdiaPortable.exe`. **Installer:** after acceptance tests, install the `.paf.exe` into the PortableApps platform directory, then refresh the PortableApps menu.
10. Upgrade: fully exit the browser, back up the entire `Data/` folder, and install a newer ZIP/installer **over the same ArdiaPortable folder**. Never remove, overwrite or replace `Data/`. On a failed upgrade, close Ardia, retain Data, reinstall prior app files and **restore matching backup Data** if the profile schema changed.

## Actual layout (after source build)

```
ArdiaPortable/
  ArdiaPortable.exe              genuine MSVC-built x64 launcher
  App/
    AppInfo/appinfo.ini
    AppInfo/appicon.ico
    AppInfo/appicon_16.png
    AppInfo/appicon_32.png
    Ardia/Ardia.exe               actual upstream-source-built Windows app
    Ardia/ArdiaApp.dll
    Ardia/chrome.dll
    Ardia/...                     complete engine and UI dependencies
  Data/Ardia/                    portable user profile and app-owned data
  Other/Source/                  upstream licenses, notices, source identity
```

## Portability strategy

The source reviewed for Windows has `apps/browser/windows/Ardia/Paths.h` with `ARDIA_DATA_DIR`; it chooses the app-owned storage root **before app initialization** and is used in upstream Windows launch tests. The real compiled C++ root launcher resolves paths relative to **its own executable**, sets `ARDIA_DATA_DIR` and `ARDIA_CONFIG_DIR` to `Data\Ardia`, and launches the source-built browser. It safeguards installed-browser registration: if the upstream installed Ardia is registered in this account, the launcher refuses coexistence by default (test-only override in a disposable VM). It also uses a per-folder single-instance lock and rejects Data junctions. It forwards regular CLI arguments, preserves the b1r2 experimental defaults documented below, and blocks `--user-data-dir`/`--disk-cache-dir` overrides that could redirect profile data out of the package. It does not touch global `APPDATA`, `USERPROFILE`, `TEMP`, services, firewall, or registry and requires no admin rights. It waits for the main browser process, without force-killing children.

**Do not assume zero host traces.** Ardia's Windows app sets a fixed `Ardia.Browser` AUMID and has notification handling. Browser/Windows shell notifications, default-browser association, shell caches, Windows credentials and auto-updater behavior are **not proven isolated**. Do not set the portable app as your default browser or enable startup registration during tests. This kit DOES NOT run broad ShellGuard or TraceGuard post-exit scavenging because no safe app-owned allowlist for runtime changes was proven. No file, registry key, shortcut or installed browser profile is deleted by the launcher. Further source-level changes and Windows runtime observation may be necessary for full contract compliance.

**Important:** Upstream Ardia Windows includes a self-update flow designed for installed builds. Until independently verified, **do not click Ardia's Check for Updates / Install Update inside the portable app**. Update using this builder's source-built ZIP/installer only. An untested upstream self-update may attempt to launch the standard per-user installer and create host registrations.

## Default launcher arguments (retained from b1r2)

The **compiled ArdiaPortable.exe** now adds these six command-line switches to **every normal Ardia.exe startup**, in this order:

```text
--disable-ardia-update --no-default-browser-check --disable-logging --disable-breakpad --disable-machine-id --disable-encryption-win
```

These are **trial arguments**, not Ardia source patches. Upstream Windows Ardia was **not verified to recognize** `--disable-ardia-update`, `--disable-machine-id`, or `--disable-encryption-win`. The last two are commonly used in modified Brave/Chromium distributions, but might be completely ignored by Ardia. `--no-default-browser-check`, `--disable-logging` and `--disable-breakpad` have Chromium usage/evidence, but their effect in this specific Ardia build still requires testing. **Do not assume** the update command prevents Ardia's in-app installer updater. Follow the existing update restrictions.

**Security:** If `--disable-encryption-win` is implemented in a particular browser build, it can disable some Windows encryption protections for browser secrets. Do not use existing sensitive accounts/passwords until source and runtime tests establish precisely what it does. If unrecognized, it will not solve cross-PC password portability. Avoid copying an installed browser's profile into portable `Data` to test this.

For troubleshooting, run `ArdiaPortable.exe --portable-no-default-flags` to start without these six default switches. It does not disable the portable profile redirection or normal host-protection checks. All other normal command-line arguments are still forwarded and preserved. Supplying one of the six switches explicitly does not cause a duplicate. The helper is included as `launcher/ArdiaLaunchFlags.h` and copied to the output package's `Other/Source/`.

**Verification:** C++ launch-option construction tests were run locally; the workflow now runs the same tests using Windows MSVC. These checks prove only the launch-command construction; there is no Windows browser runtime evidence in this kit. If Ardia offers Chromium's `chrome://version`, check the running command line there to see what was passed (listing a switch does **not** prove its behavior).

## b1r5 immutable-Git manifest verification fix (retained)

The b1r4 CI run selected `v0.2.47-nightly.5` and the verified same-tag setup fallback, but stopped at **Step 7**: the source manifest SHA-256 computed on the Windows checkout (`ad913cc1...`) did not match the preflight's immutable GitHub API blob (`9c3ec2a0...`). The most likely cause is Git for Windows converting LF line endings to CRLF. A mismatch alone does not conclusively prove the cause. This fix verifies the exact Git blob bytes and checks the materialized file independently.

- New `scripts/verify-source-content.py` reads manifest and lockfile from the immutable `HEAD:path` Git objects in **binary mode**, rather than relying on Windows worktree file bytes.
- Requires the Git manifest SHA-256 to match preflight **exactly** and (when present) the Git object ID to match the GitHub API blob ID. Validates the approved engine release, archive name, SHA-256 and Chromium version.
- Checks that the worktree copy differs, at most, by LF/CRLF line endings. Any other changes to the manifest or lockfile **fail closed**.
- Records the version-stable Git blob SHA-256 for `pnpm-lock.yaml` in the build identity, not a platform-specific CRLF hash.
- Tests cover identical and CRLF checkouts, tampered worktree manifest or lockfile, wrong preflight hash, wrong Git object ID, missing files and incompatible engine identity.
- Does **not** relax source provenance, engine SHA-256, same-tag setup requirements, or installer publication gates. All b1r4 fallback behavior and six experimental launcher flags are retained.

**Evidence:** b1r4 Step 7 and b1r5 Step 10 failures are LOG-OBSERVED; source-integrity tests are STATIC-VALIDATED. Windows Actions b1r7 compilation, official setup extraction, real browser launch, installer and publisher remain NOT YET VERIFIED.

## b1r4 verified official same-tag Windows setup fallback (retained)

**Why:** In the user-supplied b1r3 GitHub Actions logs (`logs_120006987741.zip`), all 18 tests passed, but source preflight failed because the Chromium engine releases for nightlies .5, .4 and .3 returned GitHub 404. No app was compiled in that run.

**How this setup fallback works:**

1. Resolves a Windows release in **official** `ardia-browser/ardia`; its source tag and full commit SHA are fixed. Rejects moving `main`, unknown forks, unverifiable releases and unexpected asset names.
2. Reads source-commit-locked `scripts/windows/engine/prebuilt.json` and checks for the corresponding official published engine release and binary. An available engine is always preferred.
3. If the **exact engine release is inaccessible**, checks ONLY the **same source tag's** official Windows x64 setup asset with a published GitHub `sha256:` digest, expected filename, asset ID and download URL. An unversioned `windows-alpha` pointer is not substituted. An explicit version never silently switches source tags.
4. Downloads and checks the entire setup against the published GitHub SHA-256 and exact reported size **before** Node dependencies or Windows compilation. If the hash is absent or incorrect, stops safely.
5. Builds the actual upstream Windows `ArdiaApp.dll` from the pinned source. In a disposable hosted CI runner, tries to unpack the authenticated same-tag setup without running it using 7-Zip. If extraction is unsupported, the builder may run the official Inno Setup installer **silently into an isolated runner temporary directory**. These temporary runner registrations are **not** copied into the portable ZIP. This is not an official developer portable distribution.
6. Verifies the extracted payload contains `Ardia.exe`, `ArdiaApp.dll` and `chrome.dll`, and checks `chrome.dll`'s version against the original source engine manifest. Rejects unexpected junctions. Uses its verified Chromium runtime while replacing the installer app component with the compiled source app through upstream `assemble.ps1`.
7. Records source commit, dependency lockfile hash, engine strategy, original manifest, downloaded SHA-256 and builder revision in `Other/Source/build-identity.json`. Builds and checks the independent PortableApps ZIP first, then calls the pinned shared installer and publisher.

**Limitations:** This fallback's setup extraction, assembly and Chromium version equality have **not yet run in Windows Actions**. Some Inno Setup variants may not support the assumed unattended extraction/install path, and exact engine DLL version could differ; the builder is designed to stop rather than silently ship mismatched binaries. The official upstream Windows setup may temporarily register a browser on the hosted CI runner; that is not a change to your own computer and must not be confused with a portable runtime test. The resulting browser's background child processes, updater, host registry behavior, notifications and portable credential mobility still require manual acceptance.

**Why not use `windows-alpha` directly?** That is an independently moving nightly alias. the builder accepts only a versioned setup asset belonging to the selected source tag; no silent cross-commit substitutions. The user can test `nightly` channel with `version` blank for numeric selection or specify a tagged release intentionally.

## Build provenance and licensing

- Only official `ardia-browser/ardia` versioned release tags with Windows x64 assets are eligible. Unversioned aliases like `windows-alpha`, `main`, unverified forks and unofficial mirrors are **not** silently selected.
- GitHub API resolves tag to full commit SHA; source checkout SHA and tag are checked. `pnpm-lock.yaml` is SHA-256 recorded, and dependencies are installed with `--frozen-lockfile`.
- The Windows application is compiled using the upstream React Native Windows recipe; its Chromium engine comes either from the source-matched, SHA-256-pinned engine ZIP or the source-tag-identical, SHA-256-verified official Windows setup. The Chromium engine itself is not built from source on GitHub Free runners.
- Upstream `scripts/windows/assemble.ps1` combines the app and engine. A separate C++ MSVC build produces `ArdiaPortable.exe`.
- Source for the selected upstream tag is at `https://github.com/ardia-browser/ardia/tree/<tag>`. Upstream supplies GPL-3.0, Apache-2.0, and dependency attribution under `LICENSE`, `LICENSE.Apache-2.0`, and `NOTICE`; copied into `Other/Source`. Users should review full Chromium/Helium/uBlock obligations and ensure source availability with binary distribution.
- The resulting package is unofficial, unsigned unless the source upstream provides signing, and **not certified** by PortableApps.com. Windows SmartScreen and antivirus can show warnings.
- Shared Package Builder is **`vhick/Portable-Package-Builder@v1.0.0`**, engine **`custom-nsis`**. Shared Release Publisher is **`vhick/portable-release-publisher@v1.1.1`**, keep=3, prune=false. These are pinned baselines, not upgrade requests.

## Limitations and troubleshooting

- If there is no publicly accessible matching engine **and** no verified official same-tag setup, preflight fails before compilation. Inspect `Preflight Windows release...` for the exact failure; missing GitHub-published SHA-256 is intentionally not bypassed.
- If React Native compilation fails, use `Compile real Ardia Windows application from source` logs. The upstream Windows source is rapidly changing; exact tag compatibility is not guaranteed.
- If the upstream engine download or official same-tag setup download fails, or a SHA/version mismatch occurs, stop. Do not bypass the integrity verification. Downloaded files are independently checked before compilation.
- If `ArdiaPortable.exe` reports missing `chrome.dll` or `ArdiaApp.dll`, upstream app assembly failed: do not copy a different browser's binaries.
- If GitHub Action `installer` fails, the validated ZIP (if created) is preserved as a temporary **failure-only** workflow artifact. Do not claim a successful installer.
- If an installed Ardia is detected, use a separate Windows test account. Do not disable the guard in daily use. On a disposable coexistence VM only, `--allow-installed-coexistence-test` bypasses it for acceptance testing.
- If the app fails to start from a USB drive, test on a local NTFS folder, then a path with spaces/Unicode; do not copy/import the installed Ardia profile without separate migration testing.
- If passwords stop working after moving computers, Windows DPAPI / browser encryption may bind secrets to the old Windows account; carry a safe password export if needed, not an assumed decrypting workaround.
- The PortableApps-style installer has not been manually exercised for reinstall/upgrade/data retention. Run the acceptance tests before treating it as production ready.

Read `docs/AUDIT_AND_ACCEPTANCE.md` for the verification matrix and manual acceptance steps.
