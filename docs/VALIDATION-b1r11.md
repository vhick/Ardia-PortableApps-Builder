# b1r11 validation record — exact Windows setup SHA lookup

- **SOURCE INSPECTED:** b1r10 `scripts/release.py` selects channel/release before hashing downloaded setup. Its SHA fields are fail-closed assertions, not release search.
- **STATIC-VALIDATED:** b1r11 SHA discovery searches <=500 official GitHub releases within the user-selected release channel. Only correct Windows asset names, GitHub-published sha256 digests and valid release classification are eligible.
- **STATIC-VALIDATED:** all 91 local Python unittest fixtures pass, including stable release hash matching, rolling Windows alpha matching, missing digest, wrong channel, wrong hash, duplicate hash, exact tag constraint, version constraint, and asset ID pin.
- **STATIC-VALIDATED:** YAML parsing and ZIP testzip integrity verified for created builder archive.
- **NOT VERIFIED:** live GitHub discovery of Windows build 7929, official setup hash match for the user's local installer, actual Windows compile/installation, real Ardia application version shown after launch, complete host-state portability.
- **Data safety:** b1r11 does not alter launcher profile redirection or existing Data storage. Keep backups and never change layout or update browser resources while it is running.
- **Source limitation:** official installer extraction is not a source-built browser and does not satisfy the strict upstream source-build/official-portable-binary input contract.
