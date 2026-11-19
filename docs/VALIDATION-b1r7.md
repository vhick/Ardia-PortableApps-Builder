# b1r7 data-layout checkbox validation evidence

## Local STATIC-VALIDATED

- Current automated `unittest` fixture suite validates both selected layout manifests, distinct IDs, C++ header generation, PE marker check logic, selection-aware stage/validate/ZIP, tampered identity refusal, installer script branches, and legacy regression behavior. It does not compile real Windows C++ on Linux.
- Workflow YAML is parsed and checked for typed Boolean input and build-time propagation.
- No generated launcher binary or upstream browser distribution is bundled in the builder ZIP.

## NOT YET VERIFIED

- Actual Windows GitHub Actions b1r7 MSVC compilation of each layout.
- GUI first run, browser session/extension persistence, browser restart and update behavior.
- Full Local/Roaming write containment and Windows KnownFolder bypasses.
- Existing installed Ardia coexistence and manual junction behavior; no concurrent-profile guarantees.
- Cross-version PortableApps installer behavior for both layout choices.
- GitHub release publication of b1r7 artifacts.

## Acceptance checklist on Windows

1. Build checked and unchecked variants separately; confirm both GitHub releases have unique tags and matching `Other/Source/data-layout.json`.
2. Fresh checked: verify only `Data\Local\Ardia\User Data` and `Data\Roaming\Ardia` exist inside the ZIP; browse, bookmark, exit, restart; inspect per-folder changes.
3. Fresh unchecked: verify only `Data\Profile` is staged; browse, bookmark, exit, restart; inspect changes.
4. Back up Data, then test checked build against a populated b1r5 `Data\Profile` and confirm the existing profile remains intact.
5. Back up Data, then test unchecked build against a populated mirrored Data and confirm the launcher REFUSES to launch without modifying profiles.
6. Run same-version installer reinstall tests with seeded files and completely empty directory trees in each layout.
7. Check `%LOCALAPPDATA%\Ardia` and `%APPDATA%\Ardia` and Windows notifications before/after. Only try manual installed-to-portable junctions after successful isolated testing and complete backups; never concurrent browsers.

Until observed, classify each interactive Windows scenario NOT YET VERIFIED.
