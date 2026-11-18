# b1r2 — initial source builder, 2026-11-18

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
