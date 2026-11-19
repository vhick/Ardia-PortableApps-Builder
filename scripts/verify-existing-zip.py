#!/usr/bin/env python3
"""Packaging-only validation: no unchecked extraction, preserve empty dirs, no host writes."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import sys
import zipfile


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--zip', required=True)
    a.add_argument('--sums', required=True)
    a.add_argument('--out', required=True)
    args = a.parse_args()
    zpath = Path(args.zip)
    sums = Path(args.sums).read_text(encoding='utf-8-sig')
    candidates = re.findall(r'(?im)^([0-9a-f]{64})\s+\*?([^\r\n]+)$', sums)
    matches = [h for h, name in candidates if name.strip().replace('\\','/').split('/')[-1] == zpath.name]
    if len(matches) != 1: raise RuntimeError('Expected exactly one ZIP hash in source SHA256SUMS.txt')
    h = hashlib.sha256()
    with zpath.open('rb') as f:
        for block in iter(lambda: f.read(4_194_304), b''): h.update(block)
    if h.hexdigest().lower() != matches[0].lower(): raise RuntimeError('SHA256SUMS mismatch')
    out = Path(args.out)
    if out.exists(): raise RuntimeError('Refusing to overwrite existing staging path')
    with zipfile.ZipFile(zpath) as z:
        items = z.infolist()
        if not items: raise RuntimeError('Empty ZIP')
        total = 0
        for item in items:
            norm = item.filename.replace('\\','/')
            parts = norm.split('/')
            if parts[0] != 'ArdiaPortable' or any(p in ('.','..') for p in parts):
                raise RuntimeError('Unsafe ZIP member ' + norm)
            if '\x00' in norm or norm.startswith('/') or ':' in norm or '\\' in item.filename:
                raise RuntimeError('Unsafe ZIP name')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError('Refusing ZIP symlink member')
            total += item.file_size
            if total > 5_000_000_000: raise RuntimeError('ZIP uncompressed size exceeds safety limit')
        if z.testzip() is not None: raise RuntimeError('ZIP CRC mismatch')
        if not any(x.filename == 'ArdiaPortable/ArdiaPortable.exe' for x in items):
            raise RuntimeError('Missing root launcher in ZIP')
        # Avoid ZipFile.extractall semantics; resolve each path explicitly under work.
        out.mkdir(parents=True)
        for item in items:
            parts = item.filename.replace('\\','/').split('/')[1:]
            if not parts or parts == ['']: continue
            dest = out.joinpath(*parts)
            if item.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as f, dest.open('wb') as target: shutil.copyfileobj(f, target)
    print('Verified existing release ZIP checksum, CRC, names, and extracted layout')


if __name__ == '__main__':
    try: main()
    except Exception as e:
        print('ERROR: ' + str(e), file=sys.stderr)
        sys.exit(1)
