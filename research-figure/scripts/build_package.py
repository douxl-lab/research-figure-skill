#!/usr/bin/env python3
"""Create a complete, reproducible Skill ZIP. Never include private state or fonts."""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from upstreams import read_lock, verify_entry
from check_repository import check_paths
ROOT = Path(__file__).resolve().parents[1]


def build(output: Path, root: Path = ROOT) -> dict:
    root = root.resolve()
    output = output.expanduser().resolve()
    if output == root or root in output.parents or output.exists():
        raise ValueError('Use a fresh ZIP path outside the installed Skill')
    for entry in read_lock(root)['kernels'].values():
        verify_entry(root, entry)
    files = sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Repo checker knows the exact installable directory and locked vendor inventory.
    if root.name != 'research-figure':
        raise ValueError('Package root must be named research-figure')
    names = [p.relative_to(root.parent).as_posix() for p in files]
    issues = check_paths(root.parent, names)
    if issues:
        raise ValueError('Package contains disallowed files: ' + '; '.join(issues))
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p, name in zip(files, names):
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 3, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, p.read_bytes())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    raw = output.read_bytes()
    return {'status':'PACKAGED_NOT_HOST_INSTALLED', 'path':str(output), 'files':len(files),
            'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(),
            'notice':'Complete kernels/assets/licenses included; Python/system/model access remains environmental'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    a=p.parse_args()
    try:
        print(json.dumps(build(a.out), indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'status':'BLOCKED','error':str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
