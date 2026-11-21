# b1r10 independent validation matrix

| Stage | Evidence | Result |
| --- | --- | --- |
| Existing b1r9 regression checks | `python -m unittest discover -s tests -q` | 63 tests preserved and passing locally |
| Exact release tag and GitHub classification | Offline mocked GitHub API tests | STATIC-VALIDATED |
| Exact official asset ID | Offline mocked GitHub API tests | STATIC-VALIDATED |
| Required setup SHA-256 and GitHub digest comparison | Mocked resolver + fake downloaded files | STATIC-VALIDATED |
| Required Ardia.exe SHA-256 on staged package | Mocked binary fixtures | STATIC-VALIDATED |
| Distinct release identities when asset digest or ID changes | Offline fixture tests | STATIC-VALIDATED |
| Named versioned pre-release tag | Offline fixture tests | STATIC-VALIDATED |
| Workflow YAML parsing | Python YAML parser | STATIC-VALIDATED |
| Builder ZIP integrity | ZIP testzip and SHA-256 | STATIC-VALIDATED |
| Real Windows upstream build or exact asset download | None this turn | NOT YET VERIFIED |
| Windows MSVC compile for b1r10 | None this turn | NOT YET VERIFIED |
| Browser internal Windows alpha build number 7929 | Not extracted from binary by the build | NOT YET VERIFIED |
| Interactive app launch and real profile isolation | No Windows GUI session | NOT YET VERIFIED |
| Actual pinned package installer and publication | Not run this turn | NOT YET VERIFIED |

GitHub Stable means the release is non-prerelease. It is not a guarantee of a stable Windows engine, nor proof that the version shown by Ardia inside Windows matches the GitHub tag. SHA checks attest bytes only. Checksums do not retrieve deleted release files.
