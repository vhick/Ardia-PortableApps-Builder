#!/usr/bin/env python3
"""Select the newest official Ardia Windows x64 release with its *exact* public engine.

All network requests are GitHub REST API reads against ardia-browser/ardia.
404 on a specific candidate's engine release or manifest means *skip that candidate*;
401, 403, 429, malformed responses and 5xx are fatal, never a fallback signal.
No main, fork, mirror, mismatched engine, or unverified binary substitution.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

API = 'https://api.github.com/repos/ardia-browser/ardia'
TAG = re.compile(r'^v(?P<ver>\d+\.\d+\.\d+)(?:-nightly\.(?P<night>\d+))?$')
ENGINE_RELEASE = re.compile(r'^windows-engine-\d{8}-\d+$')
ENGINE_ASSET = re.compile(r'^ardia-engine-win-x64(?:-[A-Za-z0-9._-]+)?\.zip$')
HEX_SHA = re.compile(r'^[0-9a-f]{40}$')
HEX256 = re.compile(r'^[0-9a-f]{64}$')
REVISION = 'b1r3'


def api(path: str, *, allow_404: bool = False):
    """Public GitHub API request, preserving actual server errors as failures."""
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': f'ArdiaPortableBuilder/{REVISION}',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    req = urllib.request.Request(API + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if allow_404 and exc.code == 404:
            return None
        body = exc.read(300).decode('utf-8', errors='replace')
        raise RuntimeError(f'GitHub API HTTP {exc.code} at {path}: {body}') from exc


def key(release: dict):
    match = TAG.fullmatch(release['tag_name'])
    if not match:
        raise ValueError('Not a numeric Ardia tag')
    return tuple(map(int, match['ver'].split('.'))) + (int(match['night'] or 0),)


def asset(release: dict):
    version = release['tag_name'].removeprefix('v')
    expected = f'Ardia-{version}-windows-x64-setup.exe'
    found = [a for a in release.get('assets', [])
             if a.get('name') == expected and int(a.get('size') or 0) > 1000000
             and a.get('state', 'uploaded') == 'uploaded']
    return found[0] if len(found) == 1 else None


def candidate_order(eligible: list[dict], channel: str):
    sorted_newest = sorted(eligible, key=key, reverse=True)
    if channel != 'auto':
        return sorted_newest
    # Prefer buildable stable releases; if none exists, try the Windows nightlies.
    return ([r for r in sorted_newest if not TAG.fullmatch(r['tag_name'])['night']]
            + [r for r in sorted_newest if TAG.fullmatch(r['tag_name'])['night']])


def manifest_for_commit(commit: str):
    """Read manifest from immutable *commit*, never moving main or unverified tag content."""
    path = '/contents/scripts/windows/engine/prebuilt.json?ref=' + commit
    file_obj = api(path, allow_404=True)
    if file_obj is None:
        return None
    if not isinstance(file_obj, dict) or file_obj.get('type') != 'file' or file_obj.get('encoding') != 'base64':
        raise RuntimeError(f'Unexpected source manifest response for commit {commit}')
    raw = base64.b64decode(file_obj.get('content', '').replace('\n', ''), validate=True)
    if not 0 < len(raw) < 32768:
        raise RuntimeError('Source prebuilt.json has unexpected length')
    document = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(document, dict):
        raise RuntimeError('Source prebuilt.json must be a JSON object')
    entry = document.get('x64')
    if not isinstance(entry, dict):
        raise RuntimeError('Source manifest has no Windows x64 engine')
    release = document.get('release', '')
    engine_asset = entry.get('asset', '')
    sha = str(entry.get('sha256', '')).lower()
    if not ENGINE_RELEASE.fullmatch(release) or not ENGINE_ASSET.fullmatch(engine_asset) or not HEX256.fullmatch(sha):
        raise RuntimeError(f'Invalid Windows x64 engine identity at source commit {commit}')
    return {
        'release': release,
        'asset': engine_asset,
        'sha256': sha,
        'chromium': str(document.get('chromium', '')),
        'manifest_sha256': hashlib.sha256(raw).hexdigest(),
        'manifest_blob_sha': str(file_obj.get('sha', '')),
    }


def check_engine(manifest: dict, *, cache: dict):
    """Require exact named release and uploaded asset, not a same-named asset elsewhere."""
    release_name = manifest['release']
    if release_name not in cache:
        cache[release_name] = api('/releases/tags/' + quote(release_name, safe=''), allow_404=True)
    release = cache[release_name]
    if release is None:
        return None, f'engine release {release_name} is not publicly accessible (404)'
    if release.get('draft') or release.get('tag_name') != release_name:
        return None, f'engine release {release_name} has unexpected identity/draft state'
    matches = [a for a in release.get('assets', [])
               if a.get('name') == manifest['asset'] and int(a.get('size') or 0) > 1000000
               and a.get('state', 'uploaded') == 'uploaded']
    if len(matches) != 1:
        return None, f'engine release {release_name} has no uploaded {manifest["asset"]} asset'
    a = matches[0]
    digest = a.get('digest') or ''
    if digest and digest.lower() != 'sha256:' + manifest['sha256']:
        return None, f'engine asset digest conflicts with source manifest on {release_name}'
    # An API asset listing is only preflight. Upstream fetch-engine.ps1 still
    # downloads the ZIP and checks the actual archive SHA256 before extraction.
    return a, None


def choose(eligible: list[dict], channel: str, requested: str):
    examined = []
    cache = {}
    for release in candidate_order(eligible, channel):
        tag = release['tag_name']
        try:
            commit_obj = api('/commits/' + quote(tag, safe=''), allow_404=True)
            if commit_obj is None:
                examined.append((tag, 'source tag/commit unavailable (404)'))
                continue
            sha = commit_obj.get('sha', '')
            if not HEX_SHA.fullmatch(sha):
                raise RuntimeError(f'Source SHA is invalid for {tag}')
            manifest = manifest_for_commit(sha)
            if manifest is None:
                examined.append((tag, 'immutable source commit has no Windows engine prebuilt.json'))
                continue
            engine_asset, problem = check_engine(manifest, cache=cache)
            if problem:
                examined.append((tag, problem))
                continue
            return release, sha, manifest, engine_asset, examined
        except (ValueError, KeyError, TypeError) as exc:
            # A broken manifest is not a justification to compile or substitute.
            raise RuntimeError(f'Invalid candidate metadata for {tag}: {exc}') from exc
    return None, None, None, None, examined


def resolve(channel: str, requested: str):
    if channel not in ('auto', 'stable', 'nightly'):
        raise ValueError('Channel must be auto/stable/nightly')
    requested = requested.strip()
    if requested and not TAG.fullmatch('v' + requested.removeprefix('v')):
        raise ValueError('Explicit version must be vX.Y.Z or vX.Y.Z-nightly.N')
    sought = 'v' + requested.removeprefix('v') if requested else ''
    releases = []
    for page in range(1, 5):
        batch = api(f'/releases?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise RuntimeError('Invalid GitHub releases list response')
        releases.extend(batch)
        if len(batch) < 100:
            break
    eligible = []
    for release in releases:
        tag = release.get('tag_name', '')
        m = TAG.fullmatch(tag)
        if not m or release.get('draft') or not asset(release):
            continue
        if sought and tag != sought:
            continue
        if channel == 'stable' and m['night']:
            continue
        if channel == 'nightly' and not m['night']:
            continue
        eligible.append(release)
    if not eligible:
        raise RuntimeError('No requested official versioned Windows x64 setup release. No main/fork/mirror fallback.')
    release, commit, manifest, engine_asset, examined = choose(eligible, channel, sought)
    for tag, reason in examined:
        print(f'PREFLIGHT SKIPPED {tag}: {reason}', file=sys.stderr, flush=True)
    if not release:
        context = f'explicit version {sought}' if sought else f'{channel} channel'
        raise RuntimeError(
            f'No buildable official Windows x64 Ardia release on {context}: '
            f'checked {len(examined)} source-tag-specific Chromium engine manifests/releases. '
            'The referenced engines are absent, private, or lack the required asset. '
            'No unrelated Chromium engine or setup binary will be substituted. '
            'Ask upstream to publish its matching engine release or choose a version whose exact engine is public.'
        )
    return release, commit, manifest, engine_asset, examined


def main():
    channel = os.environ.get('ARDIA_CHANNEL', 'auto').lower()
    requested = os.environ.get('ARDIA_VERSION', '')
    release, commit, manifest, engine_asset, examined = resolve(channel, requested)
    tag = release['tag_name']
    version = tag[1:]
    m = TAG.fullmatch(tag)
    package_version = '.'.join(map(str, [*map(int, m['ver'].split('.')), int(m['night'] or 0)]))
    upstream_asset = asset(release)
    upstream_digest = upstream_asset.get('digest') or ''
    if upstream_digest and not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', upstream_digest):
        raise RuntimeError('Unexpected Windows setup asset digest format')
    release_tag = f'portable-{version}-src{commit[:10]}-{REVISION}'
    identity = dict(
        tag=tag, version=version, commit=commit, package_version=package_version,
        asset=upstream_asset['name'], asset_sha256=upstream_digest,
        asset_size=upstream_asset['size'], asset_url=upstream_asset['browser_download_url'],
        channel='nightly' if m['night'] else 'stable', builder_revision=REVISION,
        release_tag=release_tag, engine_release=manifest['release'],
        engine_asset=manifest['asset'], engine_sha256=manifest['sha256'],
        engine_chromium=manifest['chromium'], engine_asset_size=engine_asset['size'],
        engine_manifest_sha256=manifest['manifest_sha256'],
        engine_manifest_blob_sha=manifest['manifest_blob_sha'],
        preflight_skipped=[{'tag': tag, 'reason': reason} for tag, reason in examined],
    )
    os.makedirs('work', exist_ok=True)
    with open('work/identity.json', 'w', encoding='utf-8') as handle:
        json.dump(identity, handle, indent=2, ensure_ascii=False)
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as handle:
            for field in ('tag', 'version', 'commit', 'package_version', 'release_tag'):
                handle.write(f'{field}={identity[field]}\n')
    print(f'PREFLIGHT VERIFIED METADATA: {tag} at {commit}; '
          f'{manifest["release"]}/{manifest["asset"]} ({manifest["sha256"]})')
    print('The actual engine ZIP download and SHA-256 check remain mandatory after compilation.')
    print(json.dumps(identity, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
