"""Reconstruct and hash-check the already reviewed RFS integration source tree."""
import base64
import bz2
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

BASE = 'b04d8ce43d5215ec5dd63bbf06e54601283230d8'
RAW_SHA = 'e97ccc0605860e3249b28fbbbc8dabf73be11d7ce7f8ba7ec2f973ac1182be44'
REPAIRS_SHA = 'a28c0980e670723775171b53fbcd105a4b05a1e8b43ccea8e988f182d52b1e89'
FINAL_TREE = 'ff16f4fed4fe2b4c31364fd403d95f2e033318cb'
root = Path(sys.argv[1]).resolve()
design = Path(sys.argv[2]).resolve()
layout = Path(sys.argv[3]).resolve()
transport = root / '.github/rfs-upgrade'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(*cmd):
    return subprocess.check_output(cmd, cwd=root, text=True).strip()


def path_for(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or str(p) != name:
        raise ValueError('Invalid payload path')
    target = root / name
    if target.is_symlink() or any(x.is_symlink() for x in target.parents if x != root):
        raise ValueError('Symlink in source destination')
    return target


encoded = ''.join((transport / f'payload-{i:02}.b64').read_text() for i in range(6))
raw = bz2.decompress(base64.b64decode(encoded, validate=True))
if sha(raw) != RAW_SHA:
    raise ValueError('Transport payload hash mismatch')
payload = json.loads(raw)
repairs_raw = (transport / 'repairs.json').read_bytes()
if sha(repairs_raw) != REPAIRS_SHA:
    raise ValueError('Repair payload hash mismatch')
repairs = json.loads(repairs_raw)
# This is a clean, ephemeral runner checkout; no user's local work is reset.
run('git', 'checkout', '--detach', BASE)
for name, record in payload.items():
    target = path_for(name)
    old = target.read_bytes() if target.exists() else b''
    if 'base_sha256' in record and sha(old) != record['base_sha256']:
        raise ValueError('Baseline drift: ' + name)
    if record.get('delete'):
        target.unlink()
        continue
    if 'new' in record:
        result = record['new'].encode('utf-8')
    else:
        lines = old.decode('utf-8').splitlines(keepends=True)
        for start, stop, replacement in reversed(record['edits']):
            lines[start:stop] = [replacement]
        result = ''.join(lines).encode('utf-8')
        if sha(result) != record['sha256']:
            raise ValueError('Reconstruction mismatch: ' + name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result)
for name, record in repairs.items():
    raw = record['content'].encode('utf-8')
    if sha(raw) != record['sha256']:
        raise ValueError('Repair content mismatch')
    target = path_for(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
for name, source in [('design', design), ('layout', layout)]:
    subprocess.run([sys.executable, str(root/'research-figure/scripts/upstreams.py'), 'pull',
                    '--kernel', name, '--source', str(source), '--bootstrap'], cwd=root, check=True)
lock_name = 'research-figure/assets/upstreams.lock.json'
if sha((root/lock_name).read_bytes()) != payload[lock_name]['completed_sha256']:
    raise ValueError('Materialized upstream inventory mismatch')
run('git', 'add', '-A')
tree = run('git', 'write-tree')
if tree != FINAL_TREE:
    raise ValueError(f'Tested source tree mismatch: {tree} != {FINAL_TREE}')
print(json.dumps({'status':'EXACT_TESTED_TREE_RECONSTRUCTED', 'tree':tree, 'base':BASE}))
