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
