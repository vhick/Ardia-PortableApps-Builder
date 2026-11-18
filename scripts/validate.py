#!/usr/bin/env python3
"""Validate real files and ZIP layouts. Does not claim interactive GUI portability."""
import hashlib,json,os,pathlib,struct,sys,zipfile,configparser

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def pe(path,expected=0x8664):
    with open(path,'rb') as f:
        if f.read(2)!=b'MZ':raise RuntimeError(f'Not a PE file: {path}')
        f.seek(0x3c);offset=struct.unpack('<I',f.read(4))[0]
        if offset<64 or offset>path.stat().st_size-24:raise RuntimeError(f'Invalid PE offset: {path}')
        f.seek(offset)
        if f.read(4)!=b'PE\0\0':raise RuntimeError(f'PE signature missing: {path}')
        cpu=struct.unpack('<H',f.read(2))[0]
        if cpu!=expected:raise RuntimeError(f'Wrong PE architecture {cpu:#x}: {path}')
        return cpu

def stage(root):
    req=['ArdiaPortable.exe','App/Ardia/Ardia.exe','App/Ardia/ArdiaApp.dll',
         'App/Ardia/chrome.dll','App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico',
         'App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png',
         'Other/Source/LICENSE','Other/Source/LICENSE.Apache-2.0','Other/Source/NOTICE',
         'Other/Source/build-identity.json','Other/Source/SOURCE.txt',
         'Other/Source/ArdiaPortable.cpp','Other/Source/ArdiaLaunchFlags.h','Other/Source/LICENSE.builder','Other/Source/engine-prebuilt.json']
    for item in req:
        target=root/item
        if not target.is_file() or target.stat().st_size==0:raise RuntimeError('Missing/empty '+str(target))
    for item in ('ArdiaPortable.exe','App/Ardia/Ardia.exe','App/Ardia/ArdiaApp.dll','App/Ardia/chrome.dll'):
        pe(root/item)
    for item in ('App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png'):
        if (root/item).read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('Invalid PNG '+item)
    if (root/'App/Ardia/Ardia.test-build').exists():raise RuntimeError('Test build marker in distributable')
    ini=configparser.ConfigParser(interpolation=None)
    ini.read(root/'App/AppInfo/appinfo.ini',encoding='utf-8')
    if ini.get('Control','Start')!='ArdiaPortable.exe':raise RuntimeError('Invalid root launch metadata')
    if ini.get('Details','AppID')!='ArdiaBrowserPortableVhick':raise RuntimeError('Wrong package identity')
    if not (root/'Data/Ardia').is_dir():raise RuntimeError('Persistent Data placeholder missing')
    identity=json.loads((root/'Other/Source/build-identity.json').read_text(encoding='utf-8'))
    if ini.get('Version','PackageVersion')!=identity['package_version']:raise RuntimeError('Inconsistent package version')
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+',identity['package_version']):raise RuntimeError('PackageVersion must have four numeric parts')
    if not re.fullmatch(r'[0-9a-f]{40}',identity['commit']):raise RuntimeError('Missing exact upstream source commit')
    if not re.fullmatch(r'[0-9a-f]{64}',identity.get('lockfile_sha256','')):raise RuntimeError('Missing lockfile checksum identity')
    if not ini.get('Version','DisplayVersion').startswith(identity['version']):raise RuntimeError('Inconsistent display version')
    print('STATIC-VALIDATED: PE x64, icons, metadata, upstream binaries, Data and source attribution')
    return identity

def main():
    root=pathlib.Path(sys.argv[1]).resolve()
    out=pathlib.Path(sys.argv[2]).resolve()
    id=stage(root)
    if root==out or root in out.parents:raise RuntimeError('Output cannot be inside source folder')
    out.mkdir(parents=True,exist_ok=True)
    name=f"ArdiaPortable_{id['version']}_x64_{id['builder_revision']}.zip"
    result=out/name
    if result.exists():raise RuntimeError('Refusing to overwrite '+str(result))
    with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for p in sorted(root.rglob('*')):
            relative=str(p.relative_to(root.parent)).replace(os.sep,'/')
            if p.is_symlink():raise RuntimeError('Unexpected symlink in staging '+str(p))
            if p.is_dir():z.writestr(relative+'/',b'')
            else:z.write(p,relative)
    with zipfile.ZipFile(result) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP checksum failure')
        if not any(n.endswith('/Data/Ardia/') for n in z.namelist()):raise RuntimeError('Data directory lost')
        if not any(n.endswith('/ArdiaPortable.exe') for n in z.namelist()):raise RuntimeError('Root EXE lost')
        if not all(n.startswith('ArdiaPortable/') for n in z.namelist()):raise RuntimeError('ZIP contains wrong root')
    checksum=digest(result)
    (out/'sha256sum.txt').write_text(f'{checksum}  {name}\n',encoding='ascii')
    print('ZIP-VALIDATED:',result,checksum,'size',result.stat().st_size)
if __name__=='__main__':main()
