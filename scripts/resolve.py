#!/usr/bin/env python3
"""Resolve an official Ardia Windows x64 release and commit, never main."""
import json, os, re, sys, urllib.request, urllib.error
from urllib.parse import quote
API='https://api.github.com/repos/ardia-browser/ardia'
TAG=re.compile(r'^v(?P<ver>\d+\.\d+\.\d+)(?:-nightly\.(?P<night>\d+))?$')

def api(path):
    req=urllib.request.Request(API+path,headers={'Accept':'application/vnd.github+json','User-Agent':'ArdiaPortableBuilder/1.0','X-GitHub-Api-Version':'2022-11-28',**({'Authorization':'Bearer '+os.environ['GH_TOKEN']} if os.environ.get('GH_TOKEN') else {})})
    try:
        with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        print(f'GitHub API HTTP {e.code} at {path}: {e.read(500)!r}',file=sys.stderr);raise

def key(release):
    match=TAG.fullmatch(release['tag_name']); ver=tuple(map(int,match['ver'].split('.')))
    return ver+(int(match['night'] or 0),)

def asset(release):
    version=release['tag_name'].removeprefix('v')
    names={f'Ardia-{version}-windows-x64-setup.exe'}
    found=[a for a in release.get('assets',[]) if a['name'] in names and a.get('size',0)>1000000]
    return found[0] if len(found)==1 else None

def main():
    channel=os.environ.get('ARDIA_CHANNEL','auto').lower()
    requested=os.environ.get('ARDIA_VERSION','').strip()
    if channel not in ('auto','stable','nightly'):raise ValueError('channel must be auto/stable/nightly')
    if requested and not TAG.fullmatch(requested if requested.startswith('v') else 'v'+requested):raise ValueError('Explicit version must be vX.Y.Z or vX.Y.Z-nightly.N')
    releases=[]
    for page in range(1,5):
        batch=api('/releases?per_page=100&page='+str(page))
        if not isinstance(batch,list):raise RuntimeError('Invalid GitHub releases response')
        releases.extend(batch)
        if len(batch)<100:break
    eligible=[]
    for rel in releases:
        tag=rel.get('tag_name','')
        m=TAG.fullmatch(tag)
        if not m or rel.get('draft') or not asset(rel):continue
        if requested and tag!=('v'+requested.removeprefix('v')):continue
        if channel=='stable' and m['night']:continue
        if channel=='nightly' and not m['night']:continue
        eligible.append(rel)
    if not eligible:raise RuntimeError('No suitable official Windows x64 release with a versioned setup asset. No fallback to main, aliases or unrelated binaries.')
    if not requested and channel=='auto':
        stable=[r for r in eligible if not TAG.fullmatch(r['tag_name'])['night']]
        if stable:eligible=stable
    rel=max(eligible,key=key)
    a=asset(rel)
    tag=rel['tag_name'];version=tag[1:]
    commit=api('/commits/'+quote(tag,safe='')).get('sha','')
    if not re.fullmatch(r'[0-9a-f]{40}',commit):raise RuntimeError('Could not resolve tag to immutable 40-character commit')
    upstream_digest=a.get('digest') or ''
    if upstream_digest and not re.fullmatch(r'sha256:[0-9a-f]{64}',upstream_digest):raise RuntimeError('Unexpected release asset digest format')
    m=TAG.fullmatch(tag)
    nums=[*map(int,m['ver'].split('.')),int(m['night'] or 0)]
    pkg='.'.join(map(str,nums))
    rev='b1r2'
    release_tag=f'portable-{version}-src{commit[:10]}-{rev}'
    identity=dict(tag=tag,version=version,commit=commit,package_version=pkg,asset=a['name'],asset_sha256=upstream_digest,asset_size=a['size'],asset_url=a['browser_download_url'],channel='nightly' if m['night'] else 'stable',builder_revision=rev,release_tag=release_tag)
    os.makedirs('work',exist_ok=True)
    with open('work/identity.json','w',encoding='utf-8') as f:json.dump(identity,f,indent=2,ensure_ascii=False)
    path=os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path,'a',encoding='utf-8') as f:
            for field in ('tag','version','commit','package_version','release_tag'):
                f.write(f'{field}={identity[field]}\n')
    print(json.dumps(identity,indent=2))
if __name__=='__main__': main()
