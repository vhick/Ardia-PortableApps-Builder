#!/usr/bin/env python3
"""Static compiled-PE flag presence check, not a runtime behavior guarantee.

MSVC embeds the active adjacent wide-string literal as UTF-16LE. This verifies
that the selected fixed switches really appeared in the built root launcher.
Does not prove upstream Ardia recognizes or honors a given Chromium argument.
"""
import argparse
from pathlib import Path
import sys
from launcher_options import FLAGS, load_manifest
from data_layout import load_manifest as load_layout


def check(path, manifest, layout_manifest=None):
    options = load_manifest(manifest)
    exe = Path(path).read_bytes()
    if exe[:2] != b'MZ':
        raise ValueError('Expected a compiled Windows PE launcher, not a script')
    expected = ''.join(' ' + arg for arg in options['enabled_arguments'])
    if expected and expected.encode('utf-16le') not in exe:
        raise ValueError('Compiled launcher does not contain the full selected UTF-16 flag sequence')
    for _key, arg, _default, _status in FLAGS:
        if arg not in options['enabled_arguments'] and (' ' + arg).encode('utf-16le') in exe:
            raise ValueError('Compiled launcher unexpectedly contains disabled flag ' + arg)
    if layout_manifest is not None:
        layout = load_layout(layout_manifest)
        if layout['layout'].encode('utf-16le') not in exe:
            raise ValueError('Compiled launcher lacks the selected UTF-16 data layout marker')
        alternate = 'legacy-profile-v1' if layout['windows_style_data'] else 'windows-appdata-mirror-v2'
        if alternate.encode('utf-16le') in exe:
            raise ValueError('Compiled launcher unexpectedly embeds the unselected layout marker')
    print('STATIC compiled launcher flag/layout verification passed; runtime behavior not tested')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--exe', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--data-layout')
    args = p.parse_args()
    check(args.exe, args.manifest, args.data_layout)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as ex:
        print('ERROR:', ex, file=sys.stderr)
        sys.exit(1)
