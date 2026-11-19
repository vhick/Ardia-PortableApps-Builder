// Auditable default flags for Ardia Windows alpha.
// Only the flags marked VERIFIED are known Chromium switches.
// Ardia-specific switches may be ignored; they DO NOT provide an updater guarantee.
#pragma once
static constexpr const wchar_t* ARDIA_PORTABLE_DEFAULT_FLAGS =
    L" --no-default-browser-check"         // VERIFIED: Chromium default browser prompt
    L" --disable-background-mode"           // Chromium background-mode request; not a complete child shutdown guarantee
    L" --disable-logging"                  // VERIFIED: Chromium logging switch; does not suppress every app log
    L" --disable-breakpad"                 // VERIFIED: Chromium crash reporter switch; not proof of no crash artifacts
    L" --disable-machine-id"               // UNVERIFIED for Ardia Windows: may be ignored
    L" --disable-ardia-update";            // UNVERIFIED for Ardia Windows: does NOT guarantee updates are disabled
// Intentionally omitted: --disable-encryption-win.
// Suppressing Windows credential encryption could expose passwords/cookies.
