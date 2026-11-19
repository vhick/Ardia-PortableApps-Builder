# Choose the portable Data layout in GitHub Actions (b1r7+; b1r8 installer smoke fix)

The main workflow now includes **Windows-style Data folders** (Boolean checkbox, default **checked**).

- **Checked:** Fresh builds stage `Data\Local\Ardia\User Data` and `Data\Roaming\Ardia`. Use this selection if you intend to manually link installed `%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia` TO portable folders, using the instructions below only after backup and full shutdown.
- **Unchecked:** Fresh builds stage only `Data\Profile` (b1r5-compatible). This mode does not provide Local/Roaming folder targets for the two junctions. Never attempt the commands below while using this layout.
- Changing the checkbox **does not migrate Data**. A checked build preserves populated legacy `Data\Profile` through compatibility fallback, so you must separately migrate to a fresh mirrored profile before using the junction commands.
- An unchecked build refuses to start when any existing mirrored browser, application or roaming state is found. This protects the profile on rollback or accidental checkbox changes. Both builds refuse to merge populated layouts.
- Never move/rename/delete Data automatically or run the installed and portable browsers against the same profile concurrently.

See the original b1r6 link instructions below for the manually authorized operations, backups and rollback limits. Existing Windows DLL/known-folder writes and browser update behavior still require runtime verification.

---

# Ardia Portable b1r6 — Windows-style Data layout and safe linking

**Read before linking or changing profiles.** This kit does **not** create, delete,
move, or repair host `%LOCALAPPDATA%` and `%APPDATA%` links automatically.

## 1. Screenshot-to-portable mapping

The user's installed Ardia has **two separate data roots**:

| Installed Ardia path | Portable Ardia b1r6 path | Visible examples |
| --- | --- | --- |
| `%LOCALAPPDATA%\Ardia` | `ArdiaPortable\Data\Local\Ardia` | `User Data\`, `Logs\`, `Telemetry\`, `config-schema\`, `session.json`, `launch-guard.json`, `windows-updates.json` and other app state |
| `%LOCALAPPDATA%\Ardia\User Data` | `ArdiaPortable\Data\Local\Ardia\User Data` | Chromium profiles, history, bookmarks, sessions and extensions |
| `%APPDATA%\Ardia` | `ArdiaPortable\Data\Roaming\Ardia` | `config.schema`, `theme.schema` in the provided screenshot |

The launcher passes `--user-data-dir` pointing to the new `User Data` folder and
`ARDIA_DATA_DIR` pointing to `Data\Local\Ardia`. It also overrides `LOCALAPPDATA`
and `APPDATA` **inside the launched process environment** (and children that
inherit it), not in Windows user/system environment settings. This does NOT
change every Windows Known Folder API, background updater or notification API.
The new directory layout is **not yet runtime-validated** with Ardia's Windows
binary; check actual writes with ProcMon before depending on it.

The launcher refuses portable Data locations that are directory reparse points.
This prevents a portable package from unknowingly writing into an installed
browser profile. Creating a link in the **installed-app location pointing to an
existing real portable directory** is possible as a **manual opt-in**. Such a
link intentionally changes host state and removes isolation between the two
Ardia applications. Do not run them at the same time with shared data. When the host paths are junctions, the portable launcher also refuses to start if it detects another `Ardia.exe` already running; this does not prevent someone from starting the installed app afterward.

## 2. Upgrading an existing working b1r5 portable profile

b1r5 stored Chromium and Ardia app state together in `Data\Profile`. There is
no verified, lossless algorithm for splitting those two data types into the new
`User Data` and outer `Ardia` directories without observing the exact build.
Thus b1r6 will **NOT automatically relocate or split** `Data\Profile`.

- Close all Ardia windows and processes and fully exit `ArdiaPortable.exe`.
- Make an **offline backup of the ENTIRE original `Data` folder** before upgrading.
- Replace `App`, `Other`, and the root launcher only. Leave existing `Data` intact.
- If `Data\Profile` has any file or subfolder, b1r6 will continue using that
  legacy location for **both** `--user-data-dir` and `ARDIA_DATA_DIR` and will
  retain b1r5 environment behavior. This is deliberate backward compatibility.
- If both old `Data\Profile` and new `Data\Local\Ardia\User Data` contain data,
  the launcher refuses to start rather than guess which profile is authoritative.

To start a **new profile with the new mirrored layout**, close Ardia and rename
`Data\Profile` to `Data\Profile-b1r5-backup` **after backing up the full Data
folder**. This is a new profile, **not an automatic migration**. Re-import
bookmarks through the browser or use a supported browser sync feature if
available, after checking compatibility. Do not copy live SQLite databases,
password encryption keys, or session files between the two layouts. Retain the
backup until the new browser profile is thoroughly tested.

## 3. Sharing with a normally installed Ardia (advanced / opt-in)

**Safer choice:** keep normal installed and PortableApps profiles separate.
Chromium uses SQLite databases and process locks, so simultaneous access to the
same `User Data` can corrupt history, sessions or extensions. Nightly version
mismatches may also make rollback impossible. Windows DPAPI credentials may
fail after moving to a different account or PC.

If you nevertheless need **one shared profile on the same Windows account**:

1. **Back up all three folders** (`%LOCALAPPDATA%\Ardia`, `%APPDATA%\Ardia`,
   and your PortableApps `Data`) to a separate location. Test the backups.
2. Fully exit *both* Ardia applications. In Task Manager, verify there are no
   `Ardia.exe` processes remaining. Disable automatic startup/update first.
3. Ensure the portable b1r6 profile is already using the **new** layout. If
   `Data\Profile` is populated, follow section 2 first; do not link a legacy
   profile and expect the new layout to be used.
4. **Move the existing installed** `%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia`
   folders to individually named backup locations on a separate disk or a
   non-conflicting backup path. Verify both original installed paths no longer
   exist. **Do not delete either original folder or overwrite the portable one.**
5. Open **Command Prompt** (`cmd.exe`) under the *same Windows user account*.
   Substitute your exact, real portable folder path in both commands. For
   example, if stored in `D:\PortableApps\ArdiaPortable`:

   ```cmd
   mklink /J "%LOCALAPPDATA%\Ardia" "D:\PortableApps\ArdiaPortable\Data\Local\Ardia"
   mklink /J "%APPDATA%\Ardia" "D:\PortableApps\ArdiaPortable\Data\Roaming\Ardia"
   ```

   These commands **create Windows directory junctions** at the *host installed*
   paths. They will fail if those paths still exist. They must never be executed
   with the direction reversed. The portable `Data` folders must remain real
   directories, not links. Windows junctions support local-volume paths;
   behavior on removable, network and cross-machine paths must be assessed
   separately. `mklink /D` can be used for directory symbolic links if properly
   authorized, but this guide deliberately uses `/J` for local folders.
6. Confirm that opening each installed path displays the matching portable
   folder. Start **only one** Ardia binary at a time, test bookmarks/history,
   then fully exit before starting the other. Do not upgrade either executable
   to a different incompatible profile schema while sharing.
7. **To undo:** exit all Ardia processes, identify and remove **only the two
   links you created** (not the portable target folders) and restore the backed-up
   installed directories. Do not run recursive deletion commands on link targets.

**Important:** The shared-profile approach intentionally causes the normally
installed application to write into PortableApps `Data` and defeats isolation.
It is not a requirement for portable functionality and it has not been tested
against all Ardia Windows components. The builder never makes these links.

## 4. Test the layout before regular use

On a disposable Windows profile (without pre-existing installed Ardia data):

1. Extract a new b1r6 package, launch `ArdiaPortable.exe` and browse normally.
2. Confirm `Data\Local\Ardia\User Data` contains Chromium profile files.
3. Set preferences, add a bookmark and close all Ardia processes. Relaunch and
   confirm settings, bookmarks and session persistence.
4. Inspect `Data\Local\Ardia` and `Data\Roaming\Ardia` for Ardia app state.
5. Compare `%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia` before and after with
   ProcMon; do not assume an empty portable roaming folder proves redirect.
6. Repeat with a Unicode/spaces path, drive relocation, exit/crash and reinstall
   preserving a planted empty directory and marker file.
7. Only after all tests should you contemplate manually linking the normal
   installed copy. Preserve all backups.

Microsoft reference: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/mklink

## Difference between ZIP extraction and PortableApps-style installer (b1r8)

- **ZIP extraction:** both selected empty profile directory paths exist immediately.
- **Installer:** the pinned shared `custom-nsis` installer creates only `Data/`,
  leaving profile layout subfolders absent until `ArdiaPortable.exe` is first
  launched. This is intentional; the installer never overwrites existing Data.
- **First launch:** the compiled root launcher creates the selected folder structure
  before starting the browser. Actual Windows profile persistence must still be
  checked manually.
- Before using junctions, launch and close the portable browser **once**, verify
  the intended folders and profile settings, and back up both installed and
  portable profiles. Do not run installed and portable Ardia concurrently.
