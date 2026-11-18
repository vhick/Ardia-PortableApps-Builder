# Ardia PortableApps Windows x64 — Source-Builder Kit b1r2

**Mode:** PORTABLEAPPS only. The ZIP you are downloading is the **builder source kit**, not a precompiled browser. GitHub Actions builds the browser and its genuine Windows C++ portable launcher and creates the actual ZIP and `.paf.exe` installer.

**Status:** Source-reviewed and Linux-local static tests passed. **No Windows Actions build, interactive GUI acceptance, USB relocation, notification compatibility, installed-app coexistence, or real installer execution has yet been run for this kit.** Treat first resulting Windows packages as *experimental* until the manual acceptance checks pass. They are not official PortableApps.com releases.

## User setup using GitHub Desktop

1. Sign in to GitHub and create a NEW, empty repository such as `Ardia-PortableApps-Builder`. Do **not** fork upstream Ardia. Choose Public if releases should be public; otherwise choose Private.
2. In GitHub Desktop, **File > Clone Repository** and choose this new builder repo. It can be an empty repo. Do not run `git init` or install a local compiler.
3. Extract this entire ZIP **into the cloned repository root**. Confirm the hidden `.github/workflows/build.yml` exists at the root and `README.md` sits beside it. Do not nest it inside another folder.
4. In GitHub Desktop, enter a commit summary, click **Commit to main**, then **Push origin**.
5. On your GitHub repository page, go to **Actions > Ardia PortableApps Source Builder > Run workflow**. Leave `version` blank for automatic release selection. `channel=auto` prefers a stable Windows x64 release, falling back to a versioned nightly if no Windows stable exists. Set `nightly` to always pick nightlies. An exact `v0.2.47-nightly.3` can be requested as long as its source release remains accessible.
6. Leave `publish=true` to publish **only validated ZIP and installer** using the pinned publisher. The publisher first performs a `dry-run=true` check. Set `publish=false` to build/test without publishing.
7. Open the workflow run. Separate lines describe source resolution, Windows source compilation, engine SHA-256 validation, launcher compilation, static ZIP validation, installer generation, and publication.
8. If it succeeds, visit **Releases** in this BUILDER repository and find the new `portable-...-b1r2` release. Download the `ArdiaPortable_...zip` or PortableApps-style `.paf.exe`. GitHub Release supplies `SHA256SUMS.txt`.
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

The source reviewed for Windows has `apps/browser/windows/Ardia/Paths.h` with `ARDIA_DATA_DIR`; it chooses the app-owned storage root **before app initialization** and is used in upstream Windows launch tests. The real compiled C++ root launcher resolves paths relative to **its own executable**, sets `ARDIA_DATA_DIR` and `ARDIA_CONFIG_DIR` to `Data\Ardia`, and launches the source-built browser. It safeguards installed-browser registration: if the upstream installed Ardia is registered in this account, the launcher refuses coexistence by default (test-only override in a disposable VM). It also uses a per-folder single-instance lock and rejects Data junctions. It forwards regular CLI arguments, adds the b1r2 experimental defaults documented below, and blocks `--user-data-dir`/`--disk-cache-dir` overrides that could redirect profile data out of the package. It does not touch global `APPDATA`, `USERPROFILE`, `TEMP`, services, firewall, or registry and requires no admin rights. It waits for the main browser process, without force-killing children.

**Do not assume zero host traces.** Ardia's Windows app sets a fixed `Ardia.Browser` AUMID and has notification handling. Browser/Windows shell notifications, default-browser association, shell caches, Windows credentials and auto-updater behavior are **not proven isolated**. Do not set the portable app as your default browser or enable startup registration during tests. This kit DOES NOT run broad ShellGuard or TraceGuard post-exit scavenging because no safe app-owned allowlist for runtime changes was proven. No file, registry key, shortcut or installed browser profile is deleted by the launcher. Further source-level changes and Windows runtime observation may be necessary for full contract compliance.

**Important:** Upstream Ardia Windows includes a self-update flow designed for installed builds. Until independently verified, **do not click Ardia's Check for Updates / Install Update inside the portable app**. Update using this builder's source-built ZIP/installer only. An untested upstream self-update may attempt to launch the standard per-user installer and create host registrations.

## b1r2 experimental default launch arguments

The **compiled ArdiaPortable.exe** now adds these six command-line switches to **every normal Ardia.exe startup**, in this order:

```text
--disable-ardia-update --no-default-browser-check --disable-logging --disable-breakpad --disable-machine-id --disable-encryption-win
```

These are **trial arguments**, not Ardia source patches. Upstream Windows Ardia was **not verified to recognize** `--disable-ardia-update`, `--disable-machine-id`, or `--disable-encryption-win`. The last two are commonly used in modified Brave/Chromium distributions, but might be completely ignored by Ardia. `--no-default-browser-check`, `--disable-logging` and `--disable-breakpad` have Chromium usage/evidence, but their effect in this specific Ardia build still requires testing. **Do not assume** the update command prevents Ardia's in-app installer updater. Follow the existing update restrictions.

**Security:** If `--disable-encryption-win` is implemented in a particular browser build, it can disable some Windows encryption protections for browser secrets. Do not use existing sensitive accounts/passwords until source and runtime tests establish precisely what it does. If unrecognized, it will not solve cross-PC password portability. Avoid copying an installed browser's profile into portable `Data` to test this.

For troubleshooting, run `ArdiaPortable.exe --portable-no-default-flags` to start without these six default switches. It does not disable the portable profile redirection or normal host-protection checks. All other normal command-line arguments are still forwarded and preserved. Supplying one of the six switches explicitly does not cause a duplicate. The helper is included as `launcher/ArdiaLaunchFlags.h` and copied to the output package's `Other/Source/`.

**Verification:** C++ launch-option construction tests were run locally; the workflow now runs the same tests using Windows MSVC. These checks prove only the launch-command construction; there is no Windows browser runtime evidence in this kit. If Ardia offers Chromium's `chrome://version`, check the running command line there to see what was passed (listing a switch does **not** prove its behavior).

## Build provenance and licensing

- Only official `ardia-browser/ardia` versioned release tags with Windows x64 assets are eligible. Unversioned aliases like `windows-alpha`, `main`, unverified forks and unofficial mirrors are **not** silently selected.
- GitHub API resolves tag to full commit SHA; source checkout SHA and tag are checked. `pnpm-lock.yaml` is SHA-256 recorded, and dependencies are installed with `--frozen-lockfile`.
- The Windows application is compiled using the upstream React Native Windows recipe; the browser's Chromium engine is downloaded **by upstream `scripts/windows/fetch-engine.ps1` with a release-locked SHA-256 check**, rather than recompiling the huge Chromium engine on GitHub Free runners.
- Upstream `scripts/windows/assemble.ps1` combines the app and engine. A separate C++ MSVC build produces `ArdiaPortable.exe`.
- Source for the selected upstream tag is at `https://github.com/ardia-browser/ardia/tree/<tag>`. Upstream supplies GPL-3.0, Apache-2.0, and dependency attribution under `LICENSE`, `LICENSE.Apache-2.0`, and `NOTICE`; copied into `Other/Source`. Users should review full Chromium/Helium/uBlock obligations and ensure source availability with binary distribution.
- The resulting package is unofficial, unsigned unless the source upstream provides signing, and **not certified** by PortableApps.com. Windows SmartScreen and antivirus can show warnings.
- Shared Package Builder is **`vhick/Portable-Package-Builder@v1.0.0`**, engine **`custom-nsis`**. Shared Release Publisher is **`vhick/portable-release-publisher@v1.1.1`**, keep=3, prune=false. These are pinned baselines, not upgrade requests.

## Limitations and troubleshooting

- If the workflow finds no Windows release, it fails closed instead of substituting a Mac/Linux build or unverified `main` source.
- If React Native compilation fails, use `Compile real Ardia Windows application from source` logs. The upstream Windows source is rapidly changing; exact tag compatibility is not guaranteed.
- If `fetch-engine.ps1` reports a SHA mismatch, stop. Never bypass the checksum.
- If `ArdiaPortable.exe` reports missing `chrome.dll` or `ArdiaApp.dll`, upstream app assembly failed: do not copy a different browser's binaries.
- If GitHub Action `installer` fails, the validated ZIP (if created) is preserved as a temporary **failure-only** workflow artifact. Do not claim a successful installer.
- If an installed Ardia is detected, use a separate Windows test account. Do not disable the guard in daily use. On a disposable coexistence VM only, `--allow-installed-coexistence-test` bypasses it for acceptance testing.
- If the app fails to start from a USB drive, test on a local NTFS folder, then a path with spaces/Unicode; do not copy/import the installed Ardia profile without separate migration testing.
- If passwords stop working after moving computers, Windows DPAPI / browser encryption may bind secrets to the old Windows account; carry a safe password export if needed, not an assumed decrypting workaround.
- The PortableApps-style installer has not been manually exercised for reinstall/upgrade/data retention. Run the acceptance tests before treating it as production ready.

Read `docs/AUDIT_AND_ACCEPTANCE.md` for the verification matrix and manual acceptance steps.
