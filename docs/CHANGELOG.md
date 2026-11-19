## b1r7 — fix CMD /S /C quoting with Visual Studio paths containing spaces

- Inspect uploaded b1r6 log `logs_120055928085.zip`: 36 tests passed, VS 2022 compiler installation was detected, then generated batch invocation failed with `'C:\Program' is not recognized` and exit 21.
- Replace three fragile `& cmd.exe /d /c ('"'+$batch+'"')` calls with shared `Invoke-ArdiaMsvcBatch`, using `.NET ProcessStartInfo.Arguments` for stable `/D /S /C ""...""` batch quoting.
- Add standalone CMD batch quoting and exit code regression, and compile a smoke-test in a path containing spaces.
- Keep `windows-2022`, six existing launch flags, persistent data paths, verified same-source-tag engine fallback, pinned Package Builder/Publisher versions.
- Local-only validation is not Windows CI proof. No app ZIP, installer, or published release was produced in inspected b1r6 run.

## b1r6 — Windows VS2022 MSVC detection correction

- Inspect `logs_120043181553.zip`: immutable source verification and verified setup download pass; b1r5 fails before compilation because MSVC detection returned no installation on `windows-2025-vs2026`.
- Pin Windows Server 2022 image with Visual Studio 2022 VC toolchain.
- Add early `verify-msvc.ps1` toolchain probe before large downloads, with actual `cl.exe` on a minimal C++ fixture invocation.
- Share `msvc-tools.ps1` discovery between the argument tests and launcher compilation; query VC-specific installs first and unfiltered VS installs second, requiring real `vcvars64.bat` plus x64 `cl.exe`.
- Preserve same-tag source/Chromium verification, `Data\Ardia`, six experimental flags, and shared-action versions.
- Status: local tests/static validation only; Windows b1r6 pipeline and browser operation not yet verified.

# b1r5 — Git blob integrity vs Windows checkout line endings, 2026-11-19

- Inspect user-provided b1r4 GitHub Actions log `logs_120033292406.zip`: 22 tests and same-tag setup preflight passed; source check failed at Step 7 because worktree SHA-256 differed from immutable preflight manifest SHA-256.
- Replace platform-dependent `Get-FileHash` manifest comparison with an immutable binary Git blob (`git show HEAD:path`) SHA-256 verification; additionally verify preflight Git object ID and source-derived engine fields.
- Permit only CRLF/LF differences between checked-out copies and pinned Git blobs; reject other worktree modifications, unexpected engine identity, and missing/corrupt files.
- Record pnpm lockfile Git blob SHA-256 independent of Windows line endings.
- Add nine offline test fixtures for genuine checkout versus tampering; preserve six launcher flags, data handling, exact-tag fallback, and pinned action versions.
- This is a verified local builder fix, not a Windows CI or browser portability success claim.

# b1r4 — verified same-source-tag setup engine fallback, 2026-11-18

- Inspect actual b1r3 CI log: 18 tests passed; preflight stopped on three unavailable upstream engine releases (404).
- Add a tightly scoped alternative: when exact Chromium engine release is unavailable, accept only the official versioned Windows x64 setup asset **from the same immutable Ardia source tag** if GitHub publishes its SHA-256 digest.
- Download and SHA-256-check the setup **before** app compilation; fail on missing digest, invalid URL, size mismatch, or API errors.
- Use 7-Zip extraction if possible; otherwise Inno Setup's documented silent mode in an **ephemeral hosted runner** and isolated temp directory. The normal user is never instructed to install upstream Ardia.
- Verify extracted payload's Chromium DLL version and components before using it as an engine donor for upstream source-compiled `ArdiaApp.dll` and `assemble.ps1`.
- Preserve b1r2 experimental launcher flags and Data path behavior, shared NSIS Package Builder v1.0.0 and Release Publisher v1.1.1.
- Add mock tests for safe setup selection and provenance. Windows build/portability remain unverified until real Actions run and manual checks.

# b1r3 — early engine preflight and safe nightly fallback, 2026-11-18

- Inspect each candidate Windows release's immutable source-commit `scripts/windows/engine/prebuilt.json`.
- Verify the exact matching `windows-engine-*` GitHub release and x64 archive asset metadata **before** dependency installation and Windows source compilation.
- Skip source-tag-specific missing engine release/asset (404); fall back to next semantically sorted eligible stable/nightly. Exact `version` never falls back.
- Fail on GitHub API authentication, rate-limit, server errors and unsafe/invalid metadata; never borrow a different engine, disable checksums, or silently download an unrelated setup binary.
- Record the pinned engine identity and manifest SHA-256 in the build identity and verify again after the exact source checkout.
- Add offline fixtures for missing releases, digest mismatches, bad manifests, forbidden API responses and explicit-version behavior; run tests in Actions before the heavy source build.
- Retain all six b1r2 launcher arguments, opt-out, portable Data behavior and pinned Package Builder/Publisher actions.
- A metadata preflight cannot promise a downloadable ZIP or a successful Windows runtime; upstream fetch script still checks the actual archive SHA-256.

# b1r1 — initial source builder, 2026-11-18

- PORTABLEAPPS x64 only, not Native.
- Upstream official Windows release resolver with exact tag, SHA and lockfile provenance.
- Source-builds Ardia Windows UI and uses upstream SHA-256-verified Chromium engine, without installing the upstream Windows setup program.
- Compiles MSVC root launcher setting documented `ARDIA_DATA_DIR` and `ARDIA_CONFIG_DIR` before Ardia starts.
- Generates PortableApps metadata, official upstream icon, notices and source links; checks PE/ZIP and empty Data directory.
- Integrates user-pinned shared NSIS packager and publisher with dry run, no pruning.
- Runtime ShellGuard, updater and notification coexistence explicitly unresolved; no aggressive cleanup.

# b1r2 — browser launch-switch experiment, 2026-11-18

- The genuine compiled C++ launcher now forwards these **six** switches to Ardia by default: `--disable-ardia-update`, `--no-default-browser-check`, `--disable-logging`, `--disable-breakpad`, `--disable-machine-id`, `--disable-encryption-win`.
- Passes switches before normal user-supplied arguments and does not duplicate an identical user-supplied switch (case-insensitive, accepts `--flag=value`).
- Adds `--portable-no-default-flags` launcher-only troubleshooting opt-out; never forwards this control switch to Ardia.
- Adds real header-only C++ unit tests that run on Linux locally and on Windows under the same MSVC toolchain as the launcher. These tests verify assembly and forwarding, **not Ardia's support for any option**.
- Preserves the existing portable-data environment, source build, pinned shared action baselines, installer and release procedures.
