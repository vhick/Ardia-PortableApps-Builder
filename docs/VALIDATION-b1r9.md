# b1r9 validation and acceptance notes — 2026-11-21

## Scope

This revision adds selectable Stable / Pre-release GitHub release channels to the user-confirmed working b1r8 builder. The launcher source and Windows-2022 MSVC tooling are unchanged. Pre-release remains the default.

## SOURCE-INSPECTED (upstream public references)

- `https://github.com/ardia-browser/ardia/releases/tag/v0.2.47` is listed as non-prerelease. Its presence does **not** establish that the GitHub release itself has an attached Windows installer for every CPU.
- `https://github.com/ardia-browser/ardia/releases/tag/windows-alpha` is marked prerelease and links a Windows x64/ARM64 setup executable. Its release notes may label Windows version `0.2.47` rather than a `-nightly.N` suffix.
- GitHub Actions supports `choice` inputs for workflow_dispatch. Shared Package Builder `v1.0.0` and Release Publisher `v1.1.1` interfaces remain unchanged.

## STATIC-VALIDATED (local source / fixtures)

- 63/63 Python tests passed.
- Both YAML workflow files parsed; main workflow contains 12 inputs including `release_channel`, selected data layout, seven launcher argument Boolean inputs, target CPU and publish.
- Tests prove no silent Stable → windows-alpha fallback, including when official Stable exists but has only Mac assets.
- Stable asset selection requires non-prerelease GitHub metadata, a numeric stable tag, a matching first-party Windows setup asset, exact release-bound download URL and immutable upstream source tag identity; tag and asset metadata are recorded in the manifest.
- Selected Windows alpha is classified as prerelease even if upstream advertises a bare numeric version.
- Numeric Stable sorting (`0.2.10` above `0.2.9`), separate channel release identity, PAF version ordering and stable staging fixtures passed.
- Legacy b1r7/b1r8 package-only identity/manifest validation and both `Data` folder layouts remain supported.

## NOT YET VERIFIED

- Whether the latest non-prerelease `v0.2.47` actually provides a suitable Windows setup asset attached to that exact release. If not, Stable intentionally fails safely.
- GitHub-hosted Windows compilation and application/installer generation under b1r9.
- Stable Windows installer authentication, user-profile runtime persistence, notification behavior, installed-browser coexistence, external host traces, junction sharing and rollback.
- Upstream browser is acquired through an official Inno setup on an isolated runner, **not compiled from source** or acquired from an official portable distribution. Strict source/official portable input contract remains unsatisfied.

## Safe first CI test

- Run Pre-release x64 with the previously working b1r8 flags/layout, and publish off until results reviewed.
- Then run Stable x64; expect an informative resolver failure if official stable Windows installers are not attached. Do not relabel alpha as stable.
- Back up the complete Data directory before testing output; never run installed and portable Ardia concurrently with shared/junctioned profiles.
