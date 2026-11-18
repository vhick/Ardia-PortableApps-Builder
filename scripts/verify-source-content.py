#!/usr/bin/env python3
"""Verify pinned Ardia source bytes without confusing Git line-endings with tampering.

Preflight reads the immutable repository blob through the GitHub API. Git for
Windows may materialize that same blob using CRLF. Compare raw git blob bytes
against API's SHA-256, and accept ONLY CRLF/LF differences in checked-out files.
Never skip the manifest provenance check or substitute a different engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

MANIFEST = 'scripts/windows/engine/prebuilt.json'
LOCKFILE = 'pnpm-lock.yaml'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


class VerificationError(RuntimeError):
    pass


def git_blob(repo: pathlib.Path, relpath: str) -> tuple[bytes, str]:
    try:
        proc = subprocess.run(
            ['git', '-C', str(repo), 'show', 'HEAD:' + relpath],
            capture_output=True, check=True,
        )
        obj = subprocess.run(
            ['git', '-C', str(repo), 'rev-parse', 'HEAD:' + relpath],
            capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f'Unable to retrieve immutable Git source {relpath}: {exc}') from exc
    blob_sha = obj.stdout.decode('ascii', errors='strict').strip().lower()
    if not HEX40.fullmatch(blob_sha):
        raise VerificationError(f'Unexpected Git blob identity for {relpath}: {blob_sha}')
    return proc.stdout, blob_sha


def allowed_worktree_bytes(repo: pathlib.Path, relpath: str, original: bytes) -> str:
    path = repo / pathlib.PurePosixPath(relpath)
    try:
        actual = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f'Checked-out file missing/unreadable: {relpath}: {exc}') from exc
    if actual == original:
        return 'byte-identical'
    # Git for Windows can materialize text blobs as CRLF. This comparison does
    # not allow arbitrary changes, reformatting, insertion or profile writes.
    if actual.replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n'):
        return 'line-ending-only'
    raise VerificationError(
        f'Checked-out {relpath} differs from verified Git object beyond line endings; '
        'refusing to continue'
    )


def verify(repo: pathlib.Path, identity_path: pathlib.Path) -> dict:
    try:
        identity = json.loads(identity_path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise VerificationError(f'Unable to read verified preflight identity: {exc}') from exc
    expected_manifest_sha = str(identity.get('engine_manifest_sha256') or '').lower()
    if not HEX64.fullmatch(expected_manifest_sha):
        raise VerificationError('Preflight did not include a valid engine manifest SHA-256')
    raw, blob_sha = git_blob(repo, MANIFEST)
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_manifest_sha:
        raise VerificationError(
            f'Immutable Git manifest differs from preflight: {actual_sha} != {expected_manifest_sha}'
        )
    preflight_blob_sha = str(identity.get('engine_manifest_blob_sha') or '').lower()
    if preflight_blob_sha and blob_sha != preflight_blob_sha:
        raise VerificationError(
            f'Immutable Git blob object differs from preflight: {blob_sha} != {preflight_blob_sha}'
        )
    manifest_checkout = allowed_worktree_bytes(repo, MANIFEST, raw)
    try:
        manifest = json.loads(raw.decode('utf-8-sig'))
    except ValueError as exc:
        raise VerificationError(f'Invalid upstream engine manifest JSON: {exc}') from exc
    windows_x64 = manifest.get('x64')
    if not isinstance(windows_x64, dict):
        raise VerificationError('Upstream engine manifest has no Windows x64 configuration')
    if (manifest.get('release') != identity.get('engine_release')
            or windows_x64.get('asset') != identity.get('engine_asset')
            or str(windows_x64.get('sha256', '')).lower() != str(identity.get('engine_sha256', '')).lower()
            or str(manifest.get('chromium', '')) != str(identity.get('engine_chromium', ''))):
        raise VerificationError('Immutable manifest does not match preflight-approved engine identity')
    lock_raw, lock_blob_sha = git_blob(repo, LOCKFILE)
    lock_checkout = allowed_worktree_bytes(repo, LOCKFILE, lock_raw)
    lock_sha = hashlib.sha256(lock_raw).hexdigest()
    identity['lockfile_sha256'] = lock_sha
    identity['lockfile_git_blob_sha'] = lock_blob_sha
    identity['source_manifest_checkout'] = manifest_checkout
    identity['source_lockfile_checkout'] = lock_checkout
    identity_path.write_text(json.dumps(identity, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'SOURCE-INSPECTED: immutable engine manifest SHA-256 {actual_sha} (worktree: {manifest_checkout})')
    print(f'SOURCE-INSPECTED: immutable pnpm-lock.yaml SHA-256 {lock_sha} (worktree: {lock_checkout})')
    print(f'PREFLIGHT CROSS-CHECK: {identity["engine_release"]} / {identity["engine_asset"]} / {identity["engine_sha256"]}')
    return identity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', required=True, type=pathlib.Path)
    parser.add_argument('--repo', required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        verify(args.repo.resolve(), args.identity.resolve())
    except VerificationError as exc:
        print(f'SOURCE VERIFICATION BLOCKED: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
