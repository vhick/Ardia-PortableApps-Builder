# Ardia Windows Stable / Pre-release PortableApps Builder Kit b1r9

## New b1r9 option: release channel (Stable or Pre-release)

In GitHub **Actions > Build Ardia Windows PortableApps (Stable or Pre-release) > Run workflow**, choose:

| Setting | Choose | Behavior |
|---|---|---|
| `release_channel` | **`prerelease`** (default) | Preserve proven b1r8 behavior: use the exact official **`windows-alpha`** GitHub **pre-release**, currently a rolling Windows alpha. |
| `release_channel` | **`stable`** | Find latest *non-prerelease GitHub release that itself attaches* a Windows installer for selected CPU; numeric-version sorting. |
| `requested_version` | Blank (default) | Latest suitable release in the selected channel. For Pre-release, current `windows-alpha` only. |
| `requested_version` | `0.2.47` | Requires exact version on selected channel. Stable: requires official Windows installer attached to `v0.2.47`; Pre-release: requires `windows-alpha` to currently report that version. |
| `architecture` | `x64` | Conventional Intel/AMD Windows computers. |
| `architecture` | `arm64` | Windows ARM systems. |
| `windows_style_data_folders` | Checked (default) | `Data/Local/Ardia/User Data` and `Data/Roaming/Ardia`. |
| `windows_style_data_folders` | Unchecked | Original `Data/Profile` layout. |
| `disable_encryption_win` | Unchecked (default) | Preserve default browser credential protection. |

**Important upstream distinction:** The official [v0.2.47 GitHub release](https://github.com/ardia-browser/ardia/releases/tag/v0.2.47) is a *non-prerelease* release; the separate [Windows alpha release](https://github.com/ardia-browser/ardia/releases/tag/windows-alpha) is officially a *prerelease*, even when it describes the underlying application version as `0.2.47`. The non-prerelease release page has not been independently verified to contain a suitable Windows installer. The Stable choice **must not silently use** the Windows-alpha installer or pretend it is stable. If the requested stable Windows asset is absent, the workflow stops at resolver with an actionable error before downloading or installing anything. It does not publish misleading artifacts. When no exact stable version is requested, it scans official GitHub releases (up to 500 records) and picks the **highest numeric stable version that has a Windows installer** for the selected CPU, if one exists.

The builder does **not** force source branch `main`, manufacture Windows binaries from a Mac release, reuse a macOS binary, or automatically choose the newer but unrelated nightlies. For a reliable build today, select **Pre-release** until the upstream official Stable channel provides a verifiable Windows asset.

### Quick GitHub Desktop update from working b1r8

1. Back up your existing *portable browser's* `Data` directory. Do **not** extract this builder over the portable browser itself.
2. Extract the complete **b1r9 builder ZIP** into your separate builder **repository root**, replacing old source files, and include the hidden `.github/workflows` folder.
3. GitHub Desktop commit summary: `Add stable and prerelease Ardia release selection (b1r9)`.
4. Push origin. Open GitHub repository > Actions > **Build Ardia Windows PortableApps (Stable or Pre-release)** > Run workflow.
5. Choose `prerelease` for the previously working Windows alpha; choose `stable` only to request a verified non-prerelease Windows installer. Leave `requested_version` blank unless targeting an exact matching version.
6. Keep the known-good architecture, Windows-style Data checkbox, and seven launch-flag selections. Strongly recommend **unchecking `--disable-encryption-win`**. The `--disable-ardia-update` and `--disable-machine-id` flags are still unverified.
7. If the chosen channel has an official Windows asset and the workflow succeeds, download the generated `ArdiaPortable_<channel>_<version>_<arch>_b1r9_...zip` and the `.paf.exe` from **Releases**. Read the release manifest under `Other/Source/build-identity.json` for the exact upstream tag, SHA, asset, channel, flags and data layout.
8. Never delete or overwrite your populated `Data` when updating. Use the supplied safe data-layout/upgrade guide and test Windows profile portability before linking profiles shared with an installed browser.

### Package versioning and immutable identity

- Stable and prerelease releases use **distinct** release tags, ZIP names and installer revisions, avoiding collisions even if both identify Ardia version `0.2.47`.
- Stable `0.2.47` uses PortableApps `PackageVersion=0.2.47.9999` (the `.9999` suffix is an **installer ordering marker only**). The real upstream version remains `DisplayVersion=0.2.47` and in `build-identity.json`.
- Pre-release `0.2.47-nightly.7` uses `PackageVersion=0.2.47.7`, `DisplayVersion=0.2.47-nightly.7`. A Windows alpha classified by GitHub as a prerelease might still report **application version `0.2.47`**; this is correctly recorded as `release_channel=prerelease` and uses the lower `PackageVersion=0.2.47.9998` (the true stable uses `.9999`) even though the version has no `nightly` suffix.
- The shared Package Builder remains `vhick/Portable-Package-Builder@v1.0.0`, `custom-nsis` (not the official PortableApps.com Installer); the publisher remains `vhick/portable-release-publisher@v1.1.1` (dry-run first; then publish), with `keep-releases=3` and `prune=false`.
- The packaging-only workflow keeps the original release channel, profile layout and compiled flags of its verified source ZIP. It does **not** convert a prerelease ZIP to Stable.

### Verification caveat

**63 offline Python tests passed** for b1r9, including stable/prerelease classification, numeric sorting, missing-stable-asset refusal, strict official asset URL, source-tag identity, staging fixtures, PAF metadata, profile preservation, and regressions. Workflow YAML parsed, and the builder ZIP was verified. This is **not** a live Windows build or a successful official Stable Windows download. Real Stable Windows source assets, executable behavior, installer execution, browser persistence, OS-managed traces, profile sharing, and Windows notifications require separate Windows verification. See `docs/VALIDATION-b1r9.md`.

## Existing b1r8-and-earlier feature documentation (retained)

# Ardia Windows Pre-release PortableApps Builder Kit b1r8

## Data folder structure workflow checkbox (introduced in b1r7, retained in b1r8)

**You can now build either of TWO real application-specific data layouts.**
Actions > Build Ardia Windows Pre-release PortableApps > Run workflow:

| Checkbox | Default | Freshly built package layout | Intended use |
|---|---|---|---|
| `windows_style_data_folders` **checked** | **YES** | `ArdiaPortable\Data\Local\Ardia\User Data` + `ArdiaPortable\Data\Roaming\Ardia` | Match normal Windows Ardia `%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia`; optional *manual* host-to-portable junctions |
| `windows_style_data_folders` **unchecked** | NO | `ArdiaPortable\Data\Profile` | Continue the earlier b1r5 single-profile layout without splitting data |

This choice is **compiled into the native C++ root launcher** at build time, not merely used as an installer naming convention. Both `--user-data-dir` and `ARDIA_DATA_DIR` receive the selected path *before* launching Ardia. In the Windows-style option, `APPDATA` and `LOCALAPPDATA` are also supplied to the browser process and its descendants. Those per-child environment variables cannot intercept all Windows known-folder API writes, shell state, or updater activity: Windows runtime testing remains necessary.

**Data safety when switching modes:**

- Both modes are entirely inside PortableApps `Data` on a NEW install; the output ZIP contains only the selected layout, including its empty directories.
- For a populated older `Data\Profile` installation, a Windows-style build preserves and continues opening that old profile unchanged rather than silently moving it. A truly new mirrored profile requires *explicit* backed-up migration or a fresh installation.
- A legacy-style build **refuses to run** when it detects existing Windows-style browser or Ardia application state. If both layouts contain data, BOTH builds refuse to merge them. Keep the matching layout when upgrading a used profile.
- The launcher never deletes, moves or overwrites old profiles and does not automatically make junctions, registry entries, or shortcuts.
- If you want the manual installed-to-portable junctions demonstrated in `docs/UPGRADE-AND-LINKS.md`, build with this checkbox **checked**, start a genuinely fresh mirror profile, test it first, and follow the manual backup and linking instructions. Never run installed and portable Ardia concurrently against linked profiles.
- Changing this checkbox means **build a NEW ZIP/installer**. It does not toggle an already compiled `.exe`. The *Packaging only* workflow keeps the layout of the original validated ZIP.

Build identity and recovery: new `Other/Source/data-layout.json` (validated schema and fingerprint) and the layout hash appear in the release tag, ZIP filename and installer revision. The workflow checks the selected layout marker in the compiled PE and uses layout-aware fresh install/reinstall tests on the hosted Windows runner.

**The other seven launcher switch checkboxes, safe `--disable-encryption-win` default OFF, `windows-2022` MSVC build procedure, pinned Package Builder and Release Publisher, and browser extraction method remain unchanged.** The extraction method is an upstream Windows installer on an isolated CI runner, so this still is *not* a source-built browser or an official developer portable release. A passing static test or CI package build alone does not verify zero host traces, actual profile portability, or Windows GUI behavior.

### b1r8 quick setup / GitHub Desktop

1. Download and extract the entire b1r8 builder ZIP over your existing **builder repository root**, including `.github`, **not** over your installed portable browser folder.
2. In GitHub Desktop, commit `Fix installer Data layout smoke test for shared NSIS action (b1r8)` and push.
3. Open Actions > **Build Ardia Windows Pre-release PortableApps** > **Run workflow**.
4. Keep **Windows-style Data folders** checked to create Local/Roaming folders compatible with the screenshot; uncheck it for the original single `Data\Profile` structure. Set the other seven checkboxes as before.
5. Download the generated ZIP or PortableApps-style installer from a successful release. Back up the complete existing portable `Data` directory *before* any upgrade. Do not copy either builder ZIP or a new blank `Data` on top of your user data.

## Older implementation history (b1r6 and earlier)



## b1r6: Installed-Ardia-compatible Data layout (November 19, 2026)

The user's screenshots identify **two installed Windows paths** (`%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia`). The b1r6 **fresh-install** PortableApps layout mirrors these safely:

```text
ArdiaPortable/
  ArdiaPortable.exe
  App/Ardia/...
  Data/
    Local/
      Ardia/
        User Data/        <- Chromium profiles, history, extensions
        (Ardia app files are written here as supported)
    Roaming/
      Ardia/              <- roaming config/schema files if app respects child APPDATA
  Other/Source/UPGRADE-AND-LINKS.md
```

Before launch the C++ wrapper sets `--user-data-dir` to the real portable `Data\Local\Ardia\User Data`, `ARDIA_DATA_DIR` to real portable `Data\Local\Ardia`, and for **new layout only** uses inherited process-local `LOCALAPPDATA=Data\Local` and `APPDATA=Data\Roaming`. These are **per-process** environment values, not global Windows settings, and do **not** intercept every Windows known-folder API. There is **no** unauthorized copying or deleting of installed `%LOCALAPPDATA%\Ardia` or `%APPDATA%\Ardia` content. Exact roaming behavior remains to be tested on Windows.

**Safe existing b1r5 upgrades:** b1r5 stored app and Chromium state together in `Data\Profile`. If this folder contains **anything**, b1r6 continues using it unchanged, including the old environment behavior. The launcher **refuses to run** if both the old and new Chromium profile locations contain data; it never guesses which should win. To adopt the new mirror layout, back up `Data`, close all Ardia processes, rename legacy `Data\Profile` to a safe backup folder, and start a new profile. Do not attempt to split or import unknown Chromium files automatically. Read `docs/UPGRADE-AND-LINKS.md` before any manual migration.

**Linking is opt-in and host-affecting.** The safe link direction (after separate backups and after original installed paths cease to exist) is from the installed Windows `%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia` **to** these portable directories. Never automatically link the portable `Data` directories **to** an installed Ardia profile, since that breaks portable isolation. Never run both browser copies simultaneously while sharing a profile; this can corrupt SQLite session/history state. The builder **does not create or remove junctions**. With optional host junctions present, the launcher refuses to start when it detects a different running `Ardia.exe` process; it cannot prevent the installed browser from being started later.

All seven b1r5 workflow argument checkboxes, `windows-2022` compiler setup, pinned shared actions and b1r5 safety behavior otherwise remain present. **Local static tests do not establish that actual Ardia Windows runtime fully uses these folders.**

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

**Selected mode: PORTABLEAPPS only**. Builds `ArdiaPortable.exe` as a **real C++/MSVC PE**, supplies `App/Ardia`, `Data/Local/Ardia/User Data` and `Data/Roaming/Ardia`, PortableApps metadata and upstream icons, creates a ready-to-extract ZIP, invokes the separately pinned shared PortableApps-style NSIS installer, then invokes the separately pinned release publisher twice (dry-run and actual publish).

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

The root launcher calculates its actual folder using `GetModuleFileNameW`. Before launching **App\\Ardia\\Ardia.exe** on a **fresh** b1r6 profile, it creates **Data\\Local\\Ardia\\User Data** and **Data\\Roaming\\Ardia**, sets `ARDIA_DATA_DIR` to the portable `Data\\Local\\Ardia`, sets the child environment's `LOCALAPPDATA` and `APPDATA` to the respective portable parent folders, and passes Chromium's `--user-data-dir="<actual portable root>\\Data\\Local\\Ardia\\User Data"`. Existing populated b1r5 `Data\\Profile` remains in legacy compatibility mode; the launcher refuses conflicting nonempty profiles. No **global** `%APPDATA%`, `%LOCALAPPDATA%` or `%TEMP%` changes are made. The automatic command line is generated into `launcher/launch_flags.h` from checked workflow options, with verified and unverified flags clearly marked. Additional launcher arguments are forwarded, the current directory is set to `App\\Ardia`, and it waits for the application executable to close and for exact-path Ardia processes to finish. A per-folder mutex prevents accidental simultaneous launches. It never kills processes or deletes other applications' files.

**Critical limitation:** At the time of kit creation, Windows **actual runtime confirmation** that all Ardia-specific stores respect these settings is **not available**. Chromium's browser profile is directed to Data before initialization; browser-created OS notification caches, registered protocols, automatic updater processes and other non-Chromium stores may still touch Windows. The package does **not** claim total host cleanliness and does **not** run broad TraceGuard/ShellGuard cleanup against a potentially installed Ardia. Source-evidenced installer registrations are avoided because the user runs the extracted app, not the upstream installer; users should **not choose Make Default Browser** or enable native updates/autostart. Preserve all detected unknown host state pending attribution rather than deleting it.

**Credentials:** Windows DPAPI-protected passwords/cookies may not function if moved between Windows accounts/computers. Do not disable encryption or copy credential keys. Standard downloads/saved files will go to user-selected or browser-configured locations; do not equate this with an app-owned profile store. Browser profile schema downgrade and sync issues are possible with nightlies.

## GitHub Desktop — beginner setup

1. On github.com create a **new separate** repository named `Ardia-Portable-Builder`, public or private as desired. Do **not** fork upstream Ardia or change an installed browser.
2. In **GitHub Desktop**, choose **File → Clone repository** and clone your new empty repository. If you prefer, create a local repository in GitHub Desktop and **Publish repository**.
3. Download this kit ZIP, extract all files to the **repository root**. Make sure hidden `.github/workflows/` is included.
4. In GitHub Desktop, commit with summary **`Adjust Ardia PortableApps Data layout to mirror Windows Local/Roaming (b1r6)`**. Push via **Push origin**.
5. Open the repository on github.com → **Actions** → **Build Ardia Windows Pre-release PortableApps** → **Run workflow**. Keep `x64` for most Windows PCs; select `arm64` only for ARM Windows PCs. Leave `requested_version` empty for current published Windows alpha. `publish=true` publishes if checks pass.
6. In the Actions run, inspect `Resolve`, `Download`, `Compile`, `Stage`, `ZIP`, `Installer`, **dry-run publisher** and **actual publisher** steps separately. A failed step prevents publication.
7. From your builder repository's **Releases**, download the `.zip` (ready to extract) or `.paf.exe` (PortableApps-*style* installer). The release publisher also creates `SHA256SUMS.txt`.
8. For ZIP: extract its `ArdiaPortable` folder somewhere writable, then double-click the **root** `ArdiaPortable.exe`. For PortableApps Platform, put the folder in your PortableApps directory and refresh the menu. Do **not** launch `App\\Ardia\\Ardia.exe` directly.
9. For fresh b1r6 installs, test settings/bookmarks/sessions/extensions under `ArdiaPortable\\Data\\Local\\Ardia\\User Data`, plus app state in `Data\\Local\\Ardia` and any roaming config in `Data\\Roaming\\Ardia`. Existing populated b1r5 `Data\\Profile` stays in legacy compatibility mode. See `docs/UPGRADE-AND-LINKS.md`.
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
- `docs/UPGRADE-AND-LINKS.md` — b1r5 preservation, safe new profile adoption and optional manually approved installed-Ardia junction instructions. Also distributed in `Other/Source` of the generated package.

## Troubleshooting

- **`Cannot attest source`**: rolling Windows release changed its format or version tag doesn't identify actual Windows source. Stop; audit before updating parser.
- **`Official GitHub digest unavailable`**: SHA recorded locally but there is no independent digest; upstream identity still resolves by official asset and source tag.
- **`Inno setup did not place ...`**: packaging was changed, or silent `/DIR` override stopped working. Do not copy an incomplete folder into a release.
- **`Missing icon`**: upstream icon changed; update the specific path after inspection; do not fabricate a brand icon.
- **`Source commit differs`**: Windows alpha and source prerelease tags disagree. Stop until source provenance verified.
- **`MSVC` failure**: `vswhere` selects an installed VS 2026/2022 C++ instance; ensure `cmake --help` lists the matching generator. Inspect actual C++ errors in Actions; do not publish dummy EXE.
- **`Windows startup returns immediately`**: open from root launcher, verify both Data\Local and Data\Roaming writable, inspect app and Event Viewer logs. If two nonempty profile locations are present, back up Data and resolve the conflict without deletion. Do not switch to an installed Ardia profile automatically.
- **`Launcher stays running`**: it holds the per-folder lock while exact-path Ardia processes remain. Close all portable browser windows and subprocesses normally.
- **`Installer action fails`**: the independently validated ZIP is uploaded as a short-lived 3-day **Actions workflow artifact**, where available, rather than silently discarded. Release publication stays blocked. The upload is recovery-only, not a publisher replacement.
- **`Rollback`**: if a newer Chromium schema changed Data, use the matching older Data backup.

For usage of third-party logos in redistributed packages, follow the upstream licensing notices and avoid implying upstream endorsement.


## b1r5 Windows compiler reliability fix

The 2026-11-19 b1r4 CI run passed Python tests and downloaded/extracted the Ardia alpha, but did **not** compile the launcher: `vswhere` reported no qualifying Visual Studio C++ installation on `windows-2025`. b1r5 pins the build to GitHub-hosted `windows-2022`, which GitHub documents as including Visual Studio 2022 and both x64 and ARM64 tools. `scripts/build-launcher.ps1` enumerates all VS 2022 editions via `vswhere -all -prerelease`, falls back to the documented Enterprise location, and checks `vcvarsall.bat`, the target-specific `cl.exe`, and CMake generator support before compilation. The workflow itself remains fully unattended.

This corrects the **toolchain discovery design**, but it is not a claim that Windows compilation, browser portability, installer behavior, or release publishing has been tested with b1r5. If the next GitHub Actions run fails, inspect the compiler diagnostics before changing any packaging or user-data logic. The upstream Inno installer remains a non-portable release, so the original source-built/official portable-input contract remains unmet.

If using the workflow checkboxes, keep `--disable-encryption-win` unchecked unless you intentionally accept the unverified security and credential portability implications. The b1r4 CI log shows it was checked in that run.


## b1r8: installer Data layout and preserving existing folders

**Two package formats behave differently on first install.** The independently generated
ZIP contains the selected (initially empty) `Data/Local/Ardia` plus `Data/Roaming/Ardia`
folders or `Data/Profile`. The pinned `vhick/Portable-Package-Builder@v1.0.0`
`custom-nsis` installer intentionally packages only `App`, `Other`, and
`ArdiaPortable.exe`; it creates **only** the root `Data` directory. This is a
safety feature: on upgrades it does **not** overwrite users' `Data` content.

On the first launch, the **compiled ArdiaPortable.exe** initializes the selected
profile layout inside `Data` before starting Ardia. The installer smoke test
in CI now models that step with a *test-only fixture* and checks that a subsequent
silent reinstall preserves a seeded user file and completely empty nested folders.
No browser is launched during that headless test, and therefore CI does not
prove real Ardia profile persistence. Both checkbox positions are covered by
static packaging fixtures. Do not share a profile with installed Ardia before
manual Windows runtime checks.

The original verified b1r7 ZIP may remain in a failed run's temporary Actions
artifact. The b1r8 builder kit does **not** contain a compiled browser or launcher.
See `docs/VALIDATION-b1r8.md`.

