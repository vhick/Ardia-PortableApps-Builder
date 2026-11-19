#!/usr/bin/env python3
"""Official Ardia Windows alpha resolver, acquisition, staging and strict static validation.
No third-party Python dependencies. Default invocation never installs software locally.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from urllib import request, error, parse
import zipfile

# Same-directory helper is used both by the CLI and the independent fixture tests.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launcher_options
import data_layout

REPO = 'ardia-browser/ardia'
API = 'https://api.github.com/repos/' + REPO
UA = 'ArdiaPortableBuilder/1.0 (source-attested Windows pre-release packaging)'
REVISION = 'b1r8'


def die(s):
    raise RuntimeError(s)


def sha256(file):
    h = hashlib.sha256()
    with Path(file).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def fetch(url, destination=None, token=None):
    parsed = parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in (
        'api.github.com', 'github.com', 'raw.githubusercontent.com',
        'objects.githubusercontent.com', 'release-assets.githubusercontent.com'):
        die('Untrusted URL: ' + url)
    headers = {'User-Agent': UA, 'Accept': 'application/vnd.github+json'}
    if token and parsed.hostname in ('api.github.com', 'github.com'):
        headers['Authorization'] = 'Bearer ' + token
    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=90) as r:
            if r.status != 200: die('Unexpected HTTP ' + str(r.status))
            if destination:
                dest = Path(destination); dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('wb') as file: shutil.copyfileobj(r, file, length=1024 * 1024)
                return str(dest)
            return r.read()
    except error.HTTPError as ex:
        die('HTTP ' + str(ex.code) + ' fetching ' + url + ' (API failures are fatal)')


def japi(endpoint, token):
    return json.loads(fetch(API + endpoint, token=token).decode('utf-8'))


def pe_machine(path):
    with open(path, 'rb') as f:
        if f.read(2) != b'MZ': die('Not an MZ executable: ' + str(path))
        f.seek(0x3c); ofs = struct.unpack('<I', f.read(4))[0]
        if ofs < 64 or ofs > 1_000_000: die('Bad PE offset')
        f.seek(ofs)
        if f.read(4) != b'PE\0\0': die('Not a PE executable')
        return struct.unpack('<H', f.read(2))[0]


def writejson(path, obj):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def resolve(args):
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    data = japi('/releases/tags/windows-alpha', token)
    if data.get('draft') or not data.get('prerelease'): die('Windows-alpha release is missing or not a published prerelease')
    # Upstream rolling alpha release notes explicitly state actual version, build, and commit.
    body = data.get('body') or ''
    match = re.search(r'Ardia\s+(0\.\d+\.\d+-nightly\.\d+)\s+for\s+Windows,\s+build\s+(\d+)\s+\(commit\s+`?([a-f0-9]{7,40})`?\)', body, re.I)
    if not match: die('Cannot attest source version+commit in Windows alpha release body')
    version, build, prefix = match.groups()
    if args.version and args.version.strip('v') != version:
        die('Requested version is not current in the official rolling windows-alpha release: ' + version)
    commit = japi('/commits/' + prefix, token)['sha']
    if not commit.startswith(prefix.lower()): die('Source commit mismatch')
    version_commit = japi('/commits/v' + version, token)['sha']
    if version_commit != commit: die('Windows release binary version differs from source tag commit; aborting')
    options = launcher_options.load_manifest(args.launcher_options)
    layout = data_layout.load_manifest(args.data_layout)
    arch = args.arch
    asset_name = 'Ardia-Setup-' + arch + '.exe'
    assets = [a for a in data.get('assets', []) if a.get('name') == asset_name]
    if len(assets) != 1 or assets[0].get('size', 0) < 1024 * 1024: die('Missing/invalid official Windows asset ' + asset_name)
    asset = assets[0]
    source_meta = japi('/contents/pnpm-lock.yaml?ref=' + parse.quote(commit), token)
    lock_sha = source_meta.get('sha', '')
    if not re.fullmatch(r'[a-f0-9]{40}', lock_sha): die('Cannot verify source lockfile identity')
    actual = {'upstream_repository': REPO, 'release_tag': 'windows-alpha',
              'version': version, 'version_tag': 'v' + version,
              'source_commit': commit, 'build': int(build), 'arch': arch,
              'asset_name': asset_name, 'asset_url': asset['browser_download_url'],
              'asset_id': asset['id'], 'asset_size': asset['size'],
              'asset_api_digest': asset.get('digest') or '',
              'source_lock_git_blob_sha': lock_sha, 'package_revision': REVISION,
              'launcher_options': options, 'launcher_flags_fingerprint': options['fingerprint'],
              'data_layout': layout, 'data_layout_fingerprint': layout['fingerprint'],
              'builder_repository_commit': os.environ.get('GITHUB_SHA', 'local-unverified'),
              'release_tag_for_builder': 'portable-ardia-' + version + '-' + arch + '-' + commit[:12] + '-' + REVISION + '-f' + options['fingerprint'] + '-d' + layout['fingerprint'],
              'portable_data_layout': layout['layout'],
              'source_method': 'Official developer Windows pre-release Inno Setup installer; copied from isolated CI installation'}
    writejson(args.identity, actual)
    print('Resolved official Windows pre-release:', version, 'commit', commit, arch)



def assert_new_builder_release(args):
    """Permit precisely 404 as absent; API 401/403/429/5xx are fatal."""
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        die('GITHUB_REPOSITORY is missing/unsafe')
    if not re.fullmatch(r'portable-[A-Za-z0-9._-]+', args.tag):
        die('Invalid reserved release tag')
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    url = f'https://api.github.com/repos/{repo}/releases/tags/{parse.quote(args.tag, safe="")}'
    headers = {'User-Agent': UA, 'Accept': 'application/vnd.github+json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    try:
        with request.urlopen(request.Request(url, headers=headers), timeout=45):
            die('A release with this identity already exists. Refusing to republish/overwrite: ' + args.tag)
    except error.HTTPError as ex:
        if ex.code == 404: print('Verified builder release tag not previously published:', args.tag); return
        die(f'GitHub release API returned HTTP {ex.code}; refusing to treat this as absent')

def acquire(args):
    src = json.loads(Path(args.identity).read_text(encoding='utf-8'))
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    path = Path(args.out); path.parent.mkdir(parents=True, exist_ok=True)
    fetch(src['asset_url'], path, token)
    digest = sha256(path)
    if src['asset_api_digest']:
        declared = src['asset_api_digest'].removeprefix('sha256:').lower()
        if declared != digest: die('Asset SHA256 differs from official release API digest')
        src['digest_attestation'] = 'GitHub release API digest matched'
    else:
        src['digest_attestation'] = 'Observed SHA-256 only; no published digest available in release API'
    if pe_machine(path) not in (0x8664, 0xAA64, 0x14c): die('Official installer is not a Windows PE')
    src['download_sha256'] = digest
    writejson(args.identity, src)
    print('Downloaded', path, 'SHA256', digest, src['digest_attestation'])


def assert_hosted_windows_ci():
    """Reject destructive installer invocation off an ephemeral GitHub-hosted Windows runner.

    Check BEFORE reading user-supplied identity/installer paths. The explicit hosted
    requirement rejects self-hosted runners, including personal Windows workstations
    registered with GitHub Actions.
    """
    if (os.name != 'nt'
            or os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('RUNNER_OS') != 'Windows'
            or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'
            or not os.environ.get('RUNNER_TEMP')):
        die('Refusing upstream installer: requires an ephemeral GitHub-hosted Windows runner')


def install_in_isolated_ci(args):
    assert_hosted_windows_ci()
    meta = json.loads(Path(args.identity).read_text(encoding='utf-8'))
    installer = Path(args.installer).resolve()
    if sha256(installer) != meta['download_sha256']: die('Installer changed after hash verification')
    target = Path(args.out).resolve()
    if target.exists(): die('Fresh isolated install location must not exist')
    if not str(target).lower().startswith(str(Path(os.environ['RUNNER_TEMP']).resolve()).lower() + os.sep):
        die('Install target must be underneath GitHub runner temp')
    # Do not mutate an existing installed Ardia; only a disposable hosted VM.
    installed_host = Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Ardia'
    if installed_host.exists(): die('Pre-existing Ardia installation on runner, refusing to continue')
    log = target.parent / 'ardia-upstream-install.log'
    argv = [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
            '/NOICONS', '/CURRENTUSER', '/DIR=' + str(target), '/LOG=' + str(log)]
    result = subprocess.run(argv, check=False, timeout=420)
    if result.returncode != 0: die('Official Inno Setup exited ' + str(result.returncode))
    if not (target / 'Ardia.exe').is_file() or not (target / 'chrome.dll').is_file():
        die('Inno setup did not place expected full Ardia.exe and chrome.dll at requested target')
    if pe_machine(target / 'Ardia.exe') != {'x64': 0x8664, 'arm64': 0xAA64}[meta['arch']]:
        die('Wrong upstream Ardia.exe architecture')
    print('Upstream binary staged from official Inno installation under disposable GitHub runner.')


def stage(args):
    meta = json.loads(Path(args.identity).read_text(encoding='utf-8'))
    origin = Path(args.install).resolve()
    root = Path(args.out).resolve()
    if root.exists(): die('Refusing to overwrite staging directory')
    app = root / 'App' / 'Ardia'
    # The official setup creates its own shortcuts/uninstaller; neither goes into portable package.
    exclude = {'unins000.exe', 'unins000.dat', 'unins000.msg', 'unins000.ini'}
    shutil.copytree(origin, app, ignore=lambda d, files: [f for f in files if f.lower() in exclude])
    if meta.get('portable_data_layout') == 'windows-appdata-mirror-v2':
        (root / 'Data' / 'Local' / 'Ardia' / 'User Data').mkdir(parents=True)
        (root / 'Data' / 'Roaming' / 'Ardia').mkdir(parents=True)
    elif meta.get('portable_data_layout') == 'legacy-profile-v1':
        (root / 'Data' / 'Profile').mkdir(parents=True)
    else:
        die('Invalid selected portable profile layout')
    (root / 'Other' / 'Source').mkdir(parents=True)
    if pe_machine(app / 'Ardia.exe') != {'x64': 0x8664, 'arm64': 0xAA64}[meta['arch']]:
        die('Wrong staged application architecture')
    launcher = Path(args.launcher)
    if not launcher.is_file() or pe_machine(launcher) != {'x64': 0x8664, 'arm64': 0xAA64}[meta['arch']]:
        die('Missing/invalid compiled launcher for architecture')
    shutil.copy2(launcher, root / 'ArdiaPortable.exe')
    icon = origin / 'Ardia.ico'
    if not icon.is_file(): die('Expected official Ardia.ico not present; no fabricated icon fallback')
    info = root / 'App' / 'AppInfo'; info.mkdir(parents=True)
    shutil.copy2(icon, info / 'appicon.ico')
    pkg = re.fullmatch(r'0\.(\d+)\.(\d+)-nightly\.(\d+)', meta['version'])
    if not pkg: die('Unexpected prerelease package version')
    package_version = '0.' + '.'.join(pkg.groups())
    appinfo = f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=Ardia Browser Portable (Unofficial)
AppID=ArdiaBrowserPortableCommunity
BaseAppName=Ardia
Publisher=Ardia upstream; unofficial portable community build
Homepage=https://github.com/ardia-browser/ardia
Category=Internet
Description=Unofficial PortableApps-style packaging of Ardia Windows pre-release
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true
EULAVersion=1

[Version]
PackageVersion={package_version}
DisplayVersion={meta['version']} ({REVISION})

[Control]
Icons=1
Start=ArdiaPortable.exe
'''
    (info / 'appinfo.ini').write_text(appinfo, encoding='utf-8')
    meta['upstream_app_exe_sha256'] = sha256(app / 'Ardia.exe')
    meta['launcher_sha256'] = sha256(root / 'ArdiaPortable.exe')
    launcher_opts = meta.get('launcher_options')
    if meta['package_revision'] == REVISION:
        launcher_options.validate_manifest(launcher_opts)
        if meta['launcher_flags_fingerprint'] != launcher_opts['fingerprint']:
            die('Launcher options fingerprint differs from identity')
        layout = data_layout.validate_manifest(meta.get('data_layout'))
        if meta.get('data_layout_fingerprint') != layout['fingerprint'] or meta.get('portable_data_layout') != layout['layout']:
            die('Compiled layout identity mismatch')
    # Keep source attribution in final package.
    source_files = ['LICENSE', 'LICENSE.Apache-2.0', 'NOTICE']
    for filename in source_files:
        url = f'https://raw.githubusercontent.com/{REPO}/{meta["source_commit"]}/{filename}'
        fetch(url, root / 'Other' / 'Source' / filename)
    writejson(args.identity, meta)
    if launcher_opts:
        writejson(root / 'Other' / 'Source' / 'launcher-options.json', launcher_opts)
    if meta['package_revision'] == REVISION:
        writejson(root / 'Other' / 'Source' / 'data-layout.json', meta['data_layout'])
    shutil.copy2(args.identity, root / 'Other' / 'Source' / 'build-identity.json')
    manual = Path(__file__).resolve().parents[1] / 'docs' / 'UPGRADE-AND-LINKS.md'
    if not manual.is_file(): die('Missing data-migration/link safety manual')
    shutil.copy2(manual, root / 'Other' / 'Source' / 'UPGRADE-AND-LINKS.md')
    (root / 'README.txt').write_text(
        'Ardia Portable (Unofficial)\n'
        'Start ArdiaPortable.exe at the root. Never start App\\Ardia\\Ardia.exe directly.\n'
        + ('Selected data layout: ' + meta['portable_data_layout'] + '\n')
        + ('Windows-style: Data\\Local\\Ardia\\User Data and Data\\Roaming\\Ardia.\n'
           if meta['portable_data_layout'] == 'windows-appdata-mirror-v2'
           else 'Legacy-style: Data\\Profile holds browser profile and Ardia data.\n')
        + 'Existing Data is never automatically migrated; a mirror build honors a populated b1r5 Data\\Profile.\n'
        'Do not set this browser as Windows default or enable auto-start/update.\n'
        'Windows DPAPI-protected credentials may not migrate between accounts/computers.\n'
        'Browser crashes, Windows notification caches, OS history, downloads and user-approved\n'
        'default-browser registrations may still leave host traces.\n'
        'The builder documents safe upgrades and links in Other\\Source\\UPGRADE-AND-LINKS.md.\n'
        'See Other\\Source and the kit documentation for licenses and limits.\n', encoding='utf-8')
    if launcher_opts:
        with (root / 'README.txt').open('a', encoding='utf-8') as f:
            f.write('Launcher flags fixed at package build time (change checkboxes and rebuild):\n')
            for arg in launcher_opts['enabled_arguments']:
                f.write('  ' + arg + '\n')
            f.write('Options fingerprint: ' + launcher_opts['fingerprint'] + '\n')
            f.write('Updater and machine-ID switches are unverified; encryption switch may reduce protection.\n')
    print('Staged', root)


def validate(args):
    root = Path(args.root)
    meta = json.loads(Path(args.identity).read_text(encoding='utf-8'))
    must = ['ArdiaPortable.exe', 'App/AppInfo/appinfo.ini', 'App/AppInfo/appicon.ico',
            'App/AppInfo/appicon_16.png', 'App/AppInfo/appicon_32.png',
            'App/Ardia/Ardia.exe', 'App/Ardia/chrome.dll',
            'Data/Local/Ardia/User Data', 'Data/Roaming/Ardia',
            'Other/Source/LICENSE', 'Other/Source/NOTICE', 'Other/Source/build-identity.json']
    # A previously published b1r5 ZIP may still be passed to packaging-only.
    # Its compiled launcher uses the legacy Data/Profile layout and must NOT be
    # relabeled as though it used the b1r6 mirrored profile path.
    layout = meta.get('portable_data_layout', 'legacy-profile-v1')
    if layout not in ('windows-appdata-mirror-v2', 'legacy-profile-v1'):
        die('Unknown portable data layout in build identity')
    if layout == 'legacy-profile-v1':
        must = [x for x in must if not x.startswith('Data/')] + ['Data/Profile']
    elif meta.get('package_revision') not in ('b1r6', 'b1r7', REVISION):
        die('Unrecognized package revision for mirrored profile layout')
    for rel in must:
        if not (root / rel).exists(): die('Missing required staged path: ' + rel)
    if layout == 'windows-appdata-mirror-v2' and (root / 'Data' / 'Profile').exists():
        die('Mirrored ZIP unexpectedly includes legacy Data/Profile')
    if meta.get('package_revision') in ('b1r7', REVISION):
        actual_options = launcher_options.validate_manifest(meta.get('launcher_options'))
        if meta.get('launcher_flags_fingerprint') != actual_options['fingerprint']:
            die('Launcher options identity hash mismatch')
        options_file = root / 'Other' / 'Source' / 'launcher-options.json'
        if launcher_options.load_manifest(options_file) != actual_options:
            die('Portable launcher options manifest differs from package identity')
        layout_data = data_layout.validate_manifest(meta.get('data_layout'))
        if layout_data['layout'] != layout or layout_data['fingerprint'] != meta.get('data_layout_fingerprint'):
            die('Selected layout identity mismatch')
        if data_layout.load_manifest(root / 'Other' / 'Source' / 'data-layout.json') != layout_data:
            die('Compiled layout manifest differs from package identity')
        other_layout = root / ('Data/Profile' if layout == 'windows-appdata-mirror-v2' else 'Data/Local/Ardia/User Data')
        if other_layout.exists(): die('New configurable-layout package contains both data layout roots')
    for filename in ['ArdiaPortable.exe', 'App/Ardia/Ardia.exe']:
        if pe_machine(root / filename) != {'x64': 0x8664, 'arm64': 0xAA64}[meta['arch']]:
            die('Wrong PE machine: ' + filename)
    if sha256(root / 'App/Ardia/Ardia.exe') != meta['upstream_app_exe_sha256']:
        die('Upstream application binary hash changed')
    if sha256(root / 'ArdiaPortable.exe') != meta['launcher_sha256']:
        die('Launcher hash changed')
    cfg = (root / 'App/AppInfo/appinfo.ini').read_text(encoding='utf-8')
    if 'AppID=ArdiaBrowserPortableCommunity' not in cfg or 'Start=ArdiaPortable.exe' not in cfg:
        die('Invalid PortableApps metadata')
    if any((root / 'App/Ardia').glob('unins*')): die('Installed-app uninstaller files leaked into package')
    exe_bytes = (root / 'ArdiaPortable.exe').read_bytes()
    if b'MZ' != exe_bytes[:2]: die('Root launcher is not compiled PE')
    import collections
    files = [p for p in root.rglob('*') if p.is_file()]
    print('STATIC validation passed', len(files), 'files; runtime portability NOT verified')


def makezip(args):
    root = Path(args.root)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists(): die('Refusing to overwrite existing ZIP')
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in sorted(root.rglob('*')):
            rel = '/'.join([root.name] + list(p.relative_to(root).parts))
            if p.is_dir():
                zi = zipfile.ZipInfo(rel + '/', date_time=(2026, 1, 1, 0, 0, 0))
                z.writestr(zi, b'')
            else: z.write(p, rel)
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        if bad: die('ZIP CRC failure: ' + bad)
        names = z.namelist()
        if (root / 'Data' / 'Profile').is_dir():
            folders = ('Data/Profile/',)
        else:
            folders = ('Data/Local/Ardia/User Data/', 'Data/Roaming/Ardia/')
        for folder in folders:
            if root.name + '/' + folder not in names: die('Empty portable data directory missing in ZIP: ' + folder)
    print('Validated ZIP', out, 'SHA256', sha256(out))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('resolve'); r.add_argument('--identity', required=True); r.add_argument('--arch', choices=['x64','arm64'], default='x64'); r.add_argument('--version', default=''); r.add_argument('--launcher-options', required=True); r.add_argument('--data-layout', required=True)
    a = sub.add_parser('acquire'); a.add_argument('--identity', required=True); a.add_argument('--out', required=True)
    i = sub.add_parser('install-ci'); i.add_argument('--identity', required=True); i.add_argument('--installer', required=True); i.add_argument('--out', required=True)
    s = sub.add_parser('stage'); s.add_argument('--identity', required=True); s.add_argument('--install', required=True); s.add_argument('--launcher', required=True); s.add_argument('--out', required=True)
    v = sub.add_parser('validate'); v.add_argument('--identity', required=True); v.add_argument('--root', required=True)
    z = sub.add_parser('zip'); z.add_argument('--root', required=True); z.add_argument('--out', required=True)
    c = sub.add_parser('check-tag'); c.add_argument('--tag', required=True)
    args = ap.parse_args(); {'resolve':resolve, 'acquire':acquire, 'install-ci':install_in_isolated_ci, 'stage':stage, 'validate':validate, 'zip':makezip, 'check-tag':assert_new_builder_release}[args.cmd](args)

if __name__ == '__main__':
    try: main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as ex:
        print('ERROR:', ex, file=sys.stderr); sys.exit(1)
