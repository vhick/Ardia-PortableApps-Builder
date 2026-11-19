# Ardia Windows Pre-release — PortableApps Builder Kit b1r5


### Select launcher arguments with checkboxes (b1r5)

When you click **Actions → Build Ardia Windows Pre-release PortableApps → Run workflow**, GitHub shows **seven independent on/off checkboxes**. Each controls whether an exact switch is compiled into the root `ArdiaPortable.exe`; no change to source code is needed. Checked means **pass the switch at every browser startup**; unchecked means **do not automatically pass it**. These are build-time choices. To change them later, build a NEW package and keep your existing `Data` folder.

| Checkbox | Default | Meaning |
|---|---|---|
| `no_default_browser_check` | Checked | Default-browser prompt suppression |
| `disable_background_mode` | Checked | Request to disable Chromium background mode; not an all-process shutdown guarantee |
| `disable_logging` | Checked | Chromium logging switch; not a guarantee of no logs |
| `disable_breakpad` | Checked | Chromium crash reporter switch; not a guarantee of zero crash artifacts |
| `disable_machine_id` | Checked | **UNVERIFIED** on Ardia; may have no effect |
| `disable_ardia_update` | Checked | **UNVERIFIED** on Ardia; does NOT prove the updater is disabled |
| `disable_encryption_win` | **Unchecked** | **UNVERIFIED and NOT RECOMMENDED.** Could weaken credential protection if honored. Do not enable on a profile with real passwords/cookies. |

After MSVC compilation, `scripts/verify_launcher_flags.py` checks the actual launcher PE for the enabled UTF-16 switch sequence and confirms unchecked switches are absent; this is static verification, not proof the browser honors them. The workflow uses GitHub's **typed Boolean inputs** (true checkbox controls, not text values). It generates both `launcher/launch_flags.h` before MSVC compilation and `work/launcher-options.json` (a canonical options record). The same validated fingerprint appears in the upstream build identity, ZIP filename, installer package revision, and GitHub release tag. As a result, two different checkbox combinations for the same Ardia commit do not collide. The final package includes `Other/Source/launcher-options.json` so you can inspect exactly which switches were selected. The separate **Packaging only** workflow deliberately DOES NOT have switches; it reuses the choices already compiled into the verified ZIP and must not pretend to change them.

**Security caveat:** Optional extra command-line arguments passed manually to `ArdiaPortable.exe` still work, but may override behaviors. The launcher always protects the mandatory `--user-data-dir` setting. Turning a checkbox off does not force upstream to disable a feature; it only omits that switch. In particular, update prevention is not verified by source/runtime evidence.

### Previous b1r3: Attempted Windows compiler and default argument fixes (19 November 2026)

- b1r3 attempted to fix GitHub Actions Windows MSVC detection by dynamically selecting VS 2026/2022 on `windows-2025`. The subsequent b1r4 CI log proved this detection was not sufficiently reliable; b1r5 instead targets the documented VS 2022 runner.
- Preserve the requested launcher defaults: `--disable-ardia-update`, `--no-default-browser-check`, `--disable-logging`, `--disable-breakpad`, and `--disable-machine-id`. `--no-default-browser-check` was already present. These defaults are centralized in `launcher/launch_flags.h` for review.
- **`--disable-ardia-update` and `--disable-machine-id` are not confirmed to be recognized by Ardia 0.2.47-nightly.7 on Windows.** Passing an unrecognized switch is not proof of disabling anything. Ardia's published Windows alpha release provides Settings › General › Updates › Check Now. Do not enable in-app self-update for a portable copy.
- **`--disable-encryption-win` remains OFF by default** and is available only through an explicitly selected checkbox because it is unverified for this browser and risks breaking Windows-protected credentials if implemented. The launcher still supports explicit user command-line arguments, but disabling credentials is discouraged.
- No change to `--user-data-dir`, `ARDIA_DATA_DIR`, data preservation, pinned packaging/publishing actions, or CI isolation.
- **No update-blocking source patch is claimed.** Actual Windows browser update behavior must be runtime audited separately.



### Previous b1r2: CI fixture and hosted-runner safeguards (19 November 2026)

- Fix the Windows CI safety unit test: explicitly remove GitHub runner variables in the off-runner fixture, instead of mistaking an actual CI runner for a local machine. This caused the `dummy` FileNotFoundError in b1r1.
- Harden Inno extraction and installer smoke tests: require `RUNNER_ENVIRONMENT=github-hosted` as documented by GitHub; refuse self-hosted/private runner environments.
- Add regression tests for the self-hosted case and missing hosted-runner marker. Preserve the original application, launcher, installer engine and publisher wiring.
- No real browser runtime claims: repeat GitHub Actions Windows build and interactive acceptance tests.

**Selected mode: PORTABLEAPPS only**. Builds `ArdiaPortable.exe` as a **real C++/MSVC PE**, supplies `App/Ardia`, `Data/Profile`, PortableApps metadata and upstream icons, creates a ready-to-extract ZIP, invokes the separately pinned shared PortableApps-style NSIS installer, then invokes the separately pinned release publisher twice (dry-run and actual publish).

**Not an official PortableApps.com package or Ardia release.** The Windows upstream build is **unsigned**. This source kit holds no application binary and fetches the exact published official pre-release Windows executable on demand.

## Architecture and upstream source

- Original: https://github.com/ardia-browser/ardia
- Source reviewed: `v0.2.47-nightly.7` associated with Windows rolling `windows-alpha` release and build 7661 (as observed November 19, 2026); the workflow **resolves current release details again on each run**.
- Upstream engine: Chromium + Helium, not Electron. Windows app executable `Ardia.exe`, engine `chrome.dll` and application icon `Ardia.ico`; bundled Windows setup is built with **Inno Setup** (upstream `scripts/windows/installer/Ardia.iss`).
- Input: the **official upstream Windows prerelease Inno executable**. `scripts/release.py` validates GitHub release source tag, resolves its actual source commit, records dependency lockfile blob SHA, downloads the exact x64 or ARM64 asset and verifies its declared GitHub digest when available. It **never compiles unverified main**.
- Upstream Windows setup installs into `%LOCALAPPDATA%\\Programs\\Ardia`, creates `%LOCALAPPDATA%\\Ardia\\User Data`, HKCU browser associations/StartMenuInternet entries and an uninstaller. This is an *installed application*, NOT a portable ZIP.
- To avoid installing that upstream setup on an end user's computer, builder executes the official Inno silent installation only on an **ephemeral GitHub-hosted Windows runner** into `RUNNER_TEMP`. The staged copy excludes `unins*` installer registrations and uninstaller. CI's disposable host mutations do not transfer into the user's Windows installation. If the upstream changes its installer switches or layout, the build **fails closed**.
- Upstream GPL-3.0/Apache-2.0 and NOTICE are downloaded from the verified version source commit. Additional dependency notices in the upstream binary distribution must be reviewed before broad redistribution.
- Workflows are manual dispatch; no paid runner or local compiler needed. The build explicitly rejects already-published tag identities; only an expected GitHub API 404 means not previously published.
- **Contract exception / unresolved blocker:** User's strict input rule allows source-compiled apps or official developer **portable** releases. Upstream presently supplies only a Windows Inno **installer**, not a developer portable archive, and full Chromium source compilation has not been implemented. This kit uses official installer binaries extracted on an isolated CI runner. Consequently the kit is a genuine but **not yet fully contract-conformant implementation candidate**. A clean first-run Windows portability audit and agreement to this binary-source deviation are required before calling it production-ready.

## Portable storage and host safety

The root launcher calculates its actual folder using `GetModuleFileNameW`. Before launching **App\\Ardia\\Ardia.exe**, it creates **Data\\Profile**, sets `ARDIA_DATA_DIR`, and passes Chromium's `--user-data-dir="<actual portable root>\\Data\\Profile"`. No global `%APPDATA%`, `%LOCALAPPDATA%` or `%TEMP%` redirection is attempted. The automatic command line is generated into `launcher/launch_flags.h` from checked workflow options, with verified and unverified flags clearly marked. Additional launcher arguments are forwarded, the current directory is set to `App\\Ardia`, and it waits for the application executable to close and for exact-path Ardia processes to finish. A per-folder mutex prevents accidental simultaneous launches. It never kills processes or deletes other applications' files.

**Critical limitation:** At the time of kit creation, Windows **actual runtime confirmation** that all Ardia-specific stores respect these settings is **not available**. Chromium's browser profile is directed to Data before initialization; browser-created OS notification caches, registered protocols, automatic updater processes and other non-Chromium stores may still touch Windows. The package does **not** claim total host cleanliness and does **not** run broad TraceGuard/ShellGuard cleanup against a potentially installed Ardia. Source-evidenced installer registrations are avoided because the user runs the extracted app, not the upstream installer; users should **not choose Make Default Browser** or enable native updates/autostart. Preserve all detected unknown host state pending attribution rather than deleting it.

**Credentials:** Windows DPAPI-protected passwords/cookies may not function if moved between Windows accounts/computers. Do not disable encryption or copy credential keys. Standard downloads/saved files will go to user-selected or browser-configured locations; do not equate this with an app-owned profile store. Browser profile schema downgrade and sync issues are possible with nightlies.

## GitHub Desktop — beginner setup

1. On github.com create a **new separate** repository named `Ardia-Portable-Builder`, public or private as desired. Do **not** fork upstream Ardia or change an installed browser.
2. In **GitHub Desktop**, choose **File → Clone repository** and clone your new empty repository. If you prefer, create a local repository in GitHub Desktop and **Publish repository**.
3. Download this kit ZIP, extract all files to the **repository root**. Make sure hidden `.github/workflows/` is included.
4. In GitHub Desktop, commit with summary **`Initial Ardia Windows prerelease PortableApps builder b1r5`**. Push via **Push origin**.
5. Open the repository on github.com → **Actions** → **Build Ardia Windows Pre-release PortableApps** → **Run workflow**. Keep `x64` for most Windows PCs; select `arm64` only for ARM Windows PCs. Leave `requested_version` empty for current published Windows alpha. `publish=true` publishes if checks pass.
6. In the Actions run, inspect `Resolve`, `Download`, `Compile`, `Stage`, `ZIP`, `Installer`, **dry-run publisher** and **actual publisher** steps separately. A failed step prevents publication.
7. From your builder repository's **Releases**, download the `.zip` (ready to extract) or `.paf.exe` (PortableApps-*style* installer). The release publisher also creates `SHA256SUMS.txt`.
8. For ZIP: extract its `ArdiaPortable` folder somewhere writable, then double-click the **root** `ArdiaPortable.exe`. For PortableApps Platform, put the folder in your PortableApps directory and refresh the menu. Do **not** launch `App\\Ardia\\Ardia.exe` directly.
9. Settings/bookmarks/sessions/extensions should live in `ArdiaPortable\\Data\\Profile`; confirm through the first-run acceptance tests before relying on it.
10. To upgrade: **fully close Ardia and the launcher**, make a backup of the entire `Data` folder, replace the `App`, `Other` and root launcher files from the new ZIP, and leave `Data` intact. Never copy `Data` from an empty new ZIP over existing profile data.
11. To roll back: back up the current `Data`, restore the previous binaries; if the browser's data schema changed, restore the **matching backup of Data** from that previous version rather than attempting to open a newer profile with an older Chromium engine.
12. **Packaging only:** After a validated ZIP is published, Actions → **Packaging only** → provide the existing release tag, exact ZIP filename, and a **new** output tag beginning `portable-`. This produces a fresh installer without downloading/rebuilding upstream.

### Windows runtime acceptance (must be done manually)

Using a disposable Windows test account **without important pre-existing browser data**: inspect normal and installed-Ardia profile locations before/after first launch, set preferences, add bookmarks, install an extension, exit all Ardia processes, relaunch, relocate folder/drive, retest. Use Process Monitor with filters for `Ardia.exe` and confirmed children to inspect writes to `%APPDATA%`, `%LOCALAPPDATA%`, registry and notifications. Compare to a separately installed Ardia user profile. Confirm settings/session persistence, browser windows, links, HTTPS, downloads, extensions, pop-ups, new profiles, notifications and click-to-open. Test the ZIP and `.paf.exe` installer independently on clean Windows, reinstall/upgrade preserving seeded Data files **and nested empty trees**. Unexpected host writes or lost credentials should be documented before regular use. **Do not run registry cleanup broadly.**

### Provenance / behavior caveats

- `Windows compilation`: expected when GitHub Actions MSVC step succeeds, not executed in this Linux authoring environment.
- `Ready-to-extract ZIP`: generated in GitHub Actions, not included inside this builder kit.
- `PortableApps installer`: generated from the ZIP staging using `vhick/Portable-Package-Builder@v1.0.0`, default `custom-nsis`; a hosted-runner fresh-install/reinstall Data-protection smoke test runs, but true cross-version upgrade, rollback and GUI are still manual. Not PortableApps.com certified.
- `Release`: published using `vhick/portable-release-publisher@v1.1.1` only after publisher dry-run succeeds, if `publish=true`.
- Shared action **pinned tag interfaces** were inspected in upstream GitHub `action.yml` at the named tags (source-dir/output-dir/engine/running-exe/package-revision and files/tag/prune/dry-run); exact full commit SHAs were not independently obtained here, so tags remain in this initial builder pending production immutable pin audit.
- This builder is **not proof of zero Windows traces**; no runtime tests on a real Windows desktop or PortableApps host have been completed for this kit.

## Files

- `.github/workflows/build.yml` — single-job official prerelease acquisition → genuine MSVC launcher → staging → ZIP → pinned installer → dry-run and publish.
- `.github/workflows/package-only.yml` — verifies source ZIP and checksum then builds another `.paf.exe`.
- `launcher/main.cpp`, `CMakeLists.txt`, `resource.rc` — real native launcher implementation; compiled per requested CPU.
- `scripts/verify_launcher_flags.py` — confirms the compiled Windows launcher contains selected options and excludes unchecked options (static only).
- `scripts/launcher_options.py` — checked-option to fixed switch allowlist, generated C++ header, manifest and stable SHA-256 option variant.
- `scripts/release.py` — GitHub release/version/source/lockfile attestation, Windows-only runner extraction, assembly, validation, ZIP and hashes.
- `scripts/make-icons.ps1` — derives PNG icons from official upstream ICO.
- `scripts/verify-installer.ps1` — checks `.paf.exe` PE structure and SHA.
- `scripts/test-installer.ps1` — hosted-Windows-only NSIS /S fresh-install and same-version reinstall test with seeded Data and nested empty-tree preservation.
- `scripts/verify-existing-zip.py` — zip-slip/symlink/CRC/SHA check for packaging only.
- `tests/test_builder.py` — isolated static/safety fixtures, not application runtime simulation.
- `docs/AUDIT.md` — paths, findings, evidence stages and limitations.

## Troubleshooting

- **`Cannot attest source`**: rolling Windows release changed its format or version tag doesn't identify actual Windows source. Stop; audit before updating parser.
- **`Official GitHub digest unavailable`**: SHA recorded locally but there is no independent digest; upstream identity still resolves by official asset and source tag.
- **`Inno setup did not place ...`**: packaging was changed, or silent `/DIR` override stopped working. Do not copy an incomplete folder into a release.
- **`Missing icon`**: upstream icon changed; update the specific path after inspection; do not fabricate a brand icon.
- **`Source commit differs`**: Windows alpha and source prerelease tags disagree. Stop until source provenance verified.
- **`MSVC` failure**: `vswhere` selects an installed VS 2026/2022 C++ instance; ensure `cmake --help` lists the matching generator. Inspect actual C++ errors in Actions; do not publish dummy EXE.
- **`Windows startup returns immediately`**: open from root launcher, verify profile folder writable, inspect app and Event Viewer logs. Do not delete profile or switch to installed Ardia profile.
- **`Launcher stays running`**: it holds the per-folder lock while exact-path Ardia processes remain. Close all portable browser windows and subprocesses normally.
- **`Installer action fails`**: the independently validated ZIP is uploaded as a short-lived 3-day **Actions workflow artifact**, where available, rather than silently discarded. Release publication stays blocked. The upload is recovery-only, not a publisher replacement.
- **`Rollback`**: if a newer Chromium schema changed Data, use the matching older Data backup.

For usage of third-party logos in redistributed packages, follow the upstream licensing notices and avoid implying upstream endorsement.


## b1r5 Windows compiler reliability fix

The 2026-11-19 b1r4 CI run passed Python tests and downloaded/extracted the Ardia alpha, but did **not** compile the launcher: `vswhere` reported no qualifying Visual Studio C++ installation on `windows-2025`. b1r5 pins the build to GitHub-hosted `windows-2022`, which GitHub documents as including Visual Studio 2022 and both x64 and ARM64 tools. `scripts/build-launcher.ps1` enumerates all VS 2022 editions via `vswhere -all -prerelease`, falls back to the documented Enterprise location, and checks `vcvarsall.bat`, the target-specific `cl.exe`, and CMake generator support before compilation. The workflow itself remains fully unattended.

This corrects the **toolchain discovery design**, but it is not a claim that Windows compilation, browser portability, installer behavior, or release publishing has been tested with b1r5. If the next GitHub Actions run fails, inspect the compiler diagnostics before changing any packaging or user-data logic. The upstream Inno installer remains a non-portable release, so the original source-built/official portable-input contract remains unmet.

If using the workflow checkboxes, keep `--disable-encryption-win` unchecked unless you intentionally accept the unverified security and credential portability implications. The b1r4 CI log shows it was checked in that run.
