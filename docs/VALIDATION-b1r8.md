# Ardia PortableApps b1r8 — findings and validation

## Exact failure in logs_120594038787.zip (November 19, 2026)

- b1r7 succeeded at Python unit tests, source acquisition, upstream binary staging,
  launcher compilation, Windows-style ZIP staging/validation, custom-NSIS installer
  construction, and static installer PE/hash validation.
- b1r7 failed in `scripts/test-installer.ps1` at the initial selected-layout
  directory assertion, with `Installer omitted the selected layout data folder`.
- Upstream package action `vhick/Portable-Package-Builder@v1.0.0`
  `nsis/community-installer.nsi` only embeds launcher/App/Other and creates
  the top-level `Data` directory. It deliberately never overwrites or copies Data.
  Source: https://github.com/vhick/Portable-Package-Builder/blob/v1.0.0/nsis/community-installer.nsi
- The browser launcher creates selected Data subdirectories on first launch,
  but that was NOT tested by the headless installer smoke test.

## b1r8 changes

- Correct the installer smoke test to verify documented top-level `Data` creation,
  check the installed compiled data-layout manifest, seed the selected layout
  explicitly as a controlled fixture, and verify same-version reinstall preserves
  directories (including empty nested ones) and a Unicode marker file.
- Preserve separate layout choices and compile-time launcher flags.
- Keep pinned shared package/publisher versions and `windows-2022` build runner.
- Preserve compatibility for validated `b1r7` and older ZIPs in packaging-only
  validation. Add a regression test for this compatibility.
- Do not modify or attempt to harvest an installed Ardia user profile.

## Evidence rules

- **SOURCE-INSPECTED:** pinned shared action NSIS installer intentionally handles
  only root `Data` and managed `App`/`Other`/launcher.
- **AUTOMATED-RUNTIME-TESTED (b1r7):** upstream installer extraction, launcher
  compilation, ZIP staging, installer creation, static PE/hash validation.
- **FAILED (b1r7):** installer test incorrectly required layout subdirectories
  before first browser launch.
- **STATIC-VALIDATED (b1r8):** local tests and ZIP integrity, see final report.
- **NOT YET VERIFIED (b1r8):** hosted Windows build/test, complete Ardia GUI
  behavior, first-launch profile persistence, notification/registry traces,
  symlink coexistence, cross-version upgrades, and publisher invocation.
- **LIMITATION:** Binary source is official Windows installer extraction rather
  than an official portable distribution or full source compilation.
