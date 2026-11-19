#!/usr/bin/env python3
"""Fail fast on partial builder-kit upgrades (especially stale test files).

This checks only project-owned configuration. Historical changelog references remain valid.
Use --root to exercise a disposable fixture; never modifies files.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

VALID_REVISION = re.compile(r"b[1-9][0-9]*r[1-9][0-9]*\Z")
ANY_REVISION = re.compile(r"\bb[1-9][0-9]*r[1-9][0-9]*\b")


def check(root: Path) -> list[str]:
    problems: list[str] = []
    revision_path = root / 'BUILDER_REVISION'
    if not revision_path.is_file():
        return ["Missing BUILDER_REVISION: extract the entire kit into the repository root, including tests/ and .github/"]
    rev = revision_path.read_text(encoding='utf-8-sig').strip()
    if not VALID_REVISION.fullmatch(rev):
        return [f"Invalid BUILDER_REVISION: {rev!r}"]
    expectations: dict[str, list[str]] = {
        '.github/workflows/build.yml': [
            f'package-revision: {rev}',
            f'PortableApps x64 (unofficial {rev})',
            'Check builder kit revision consistency BEFORE tests',
        ],
        'scripts/resolve.py': ["'BUILDER_REVISION'"],
        'scripts/stage.ps1': [f'Unofficial {rev}'],
        'README.md': [f'Source-Builder Kit {rev}'],
        'tests/test_local.py': ['test_kit_uses_current_revision_everywhere', "ROOT/'BUILDER_REVISION'"],
        'tests/test_msvc_preflight.py': ["ROOT/'BUILDER_REVISION'"],
    }
    for relative, tokens in expectations.items():
        p = root / relative
        if not p.is_file():
            problems.append(f'Missing {relative}: copy ALL files from the {rev} kit')
            continue
        data = p.read_text(encoding='utf-8-sig')
        for token in tokens:
            if token not in data:
                problems.append(f'{relative}: missing expected current-version marker {token!r}')
        if relative.startswith('tests/'):
            stale = sorted({v for v in ANY_REVISION.findall(data) if v != rev})
            if stale:
                problems.append(f'{relative}: stale hardcoded version(s) {", ".join(stale)}; overwrite with {rev} file from ZIP')
    p = root / 'docs/LOCAL_VERIFICATION.json'
    if not p.is_file():
        problems.append('Missing docs/LOCAL_VERIFICATION.json')
    else:
        try:
            current = json.loads(p.read_text(encoding='utf-8-sig'))
            if current.get('revision') != rev:
                problems.append(f"docs/LOCAL_VERIFICATION.json: revision={current.get('revision')!r}, expected {rev!r}")
        except (ValueError, UnicodeError) as exc:
            problems.append(f'docs/LOCAL_VERIFICATION.json: invalid JSON: {exc}')
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check(args.root.resolve())
    if errors:
        print('BUILDER VERSION MISMATCH — probably an incomplete GitHub Desktop ZIP overwrite:', file=sys.stderr)
        for err in errors:
            print('  - ' + err, file=sys.stderr)
        print('Fix: extract the entire newest kit into the cloned repository root, replace existing files, and commit ALL changed files.', file=sys.stderr)
        return 2
    version = (args.root/'BUILDER_REVISION').read_text(encoding='utf-8-sig').strip()
    print(f'STATIC-VALIDATED: {version} builder revision is consistent across workflow, tests, resolver, metadata, and staging.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
