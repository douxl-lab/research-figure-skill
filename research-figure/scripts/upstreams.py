#!/usr/bin/env python3
"""Verify or pull selected upstream source into embedded, provenance-locked kernels.

No downloaded code is executed. No git commit/push or provider request is made.
Local modifications/unknown files block replacement; adapters live outside kernels.
"""
from __future__ import annotations
import argparse
import fnmatch
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'assets/upstreams.lock.json'
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
FONT_EXT = {'.ttf', '.otf', '.woff', '.woff2', '.eot', '.pfb', '.pfm'}
TEXT_EXT = {'.py', '.md', '.txt', '.json', '.yaml', '.yml'}
BINARY_EXT = {'.png', '.jpg', '.jpeg', '.svg', '.pptx', '.vsdx'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(raw: str) -> str:
    p = PurePosixPath(raw)
    if not raw or raw != p.as_posix() or p.is_absolute() or any(x in {'.', '..'} for x in p.parts):
        raise ValueError('Unsafe upstream path')
    if '\\' in raw or ':' in raw or any(ord(c) < 32 for c in raw):
        raise ValueError('Unsafe or nonportable upstream path')
    if any(x.startswith('.') for x in p.parts):
        raise ValueError('Hidden upstream files are not part of the kernel')
    return raw


def permitted(raw: str) -> bool:
    try:
        safe_path(raw)
    except ValueError:
        return False
    p = PurePosixPath(raw)
    if p.suffix.lower() in FONT_EXT:
        return False
    if p.name in {'LICENSE', 'NOTICE'}:
        return True
    if p.name == 'SKILL.md' or p.name == 'model_config.yaml':
        return False
    return p.suffix.lower() in TEXT_EXT | BINARY_EXT


def read_lock(root: Path) -> dict:
    if (root / 'kernels').is_symlink() or (root / 'assets').is_symlink() or (root / LOCK).is_symlink():
        raise ValueError('Kernel and lock ancestors must not be symlinks')
    value = json.loads((root / LOCK).read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Upstream lock must be an object')
    if value.get('format') != 'rfs-upstreams/1.0' or not isinstance(value.get('kernels'), dict):
        raise ValueError('Invalid upstream lock')
    for name, entry in value['kernels'].items():
        if name not in {'design', 'layout'} or entry.get('destination') != f'kernels/{name}':
            raise ValueError('Unexpected kernel destination')
        if not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+', entry.get('repository', '')):
            raise ValueError('Expected a public HTTPS GitHub source')
        if not re.fullmatch(r'[0-9a-f]{40}', entry.get('revision', '')):
            raise ValueError('Revision must be an exact Git commit')
        if not isinstance(entry.get('include'), list) or not entry['include'] or not all(isinstance(p, str) for p in entry['include']):
            raise ValueError('Empty upstream selection')
        if not isinstance(entry.get('files'), dict):
            raise ValueError('Missing file inventory')
        for rel, rec in entry.get('files', {}).items():
            if not permitted(rel) or not isinstance(rec, dict) or not re.fullmatch(r'[0-9a-f]{64}', rec.get('sha256', '')):
                raise ValueError('Invalid file inventory')
            if type(rec.get('bytes')) is not int or not 0 <= rec['bytes'] <= MAX_FILE:
                raise ValueError('Invalid inventory byte count')
    return value


def inventory(directory: Path) -> dict:
    result = {}
    if directory.is_symlink():
        raise ValueError('Kernel directory must not be a symlink')
    if not directory.exists():
        return result
    for p in directory.rglob('*'):
        rel = p.relative_to(directory).as_posix()
        # Ordinary import caches are not source; symlinks are never ignored.
        if p.is_symlink():
            raise ValueError(f'Symlink in kernel: {rel}')
        if p.is_dir():
            continue
        if '__pycache__' in p.parts and p.suffix == '.pyc':
            continue
        safe_path(rel)
        if not p.is_file() or p.stat().st_size > MAX_FILE:
            raise ValueError(f'Invalid kernel file: {rel}')
        raw = p.read_bytes()
        result[rel] = {'sha256': digest(raw), 'bytes': len(raw)}
    return result


def verify_entry(root: Path, entry: dict, *, bootstrap: bool = False) -> dict:
    target = root / entry['destination']
    expected = entry.get('files', {})
    actual = inventory(target)
    if not expected and not actual and bootstrap:
        return {'status': 'EMPTY_BOOTSTRAP', 'files': 0}
    if not expected:
        raise ValueError('Kernel is not materialized; explicitly bootstrap the locked revision')
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(p for p in set(actual) & set(expected) if actual[p] != expected[p])
    if missing or extra or changed:
        raise ValueError('Kernel conflict; no overwrite: ' + json.dumps({'missing': missing, 'extra': extra, 'changed': changed}))
    return {'status': 'VERIFIED', 'files': len(actual), 'revision': entry['revision']}


def git(args: list[str], *, cwd: Path | None = None, binary: bool = False) -> bytes | str:
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_CONFIG_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_LFS_SKIP_SMUDGE='1')
    cmd = ['git', '-c', f'core.hooksPath={os.devnull}', '-c', 'core.fsmonitor=false', *args]
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=180, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Git source fetch timed out; installed kernels were not changed') from exc
    if p.returncode:
        raise ValueError('Git source operation failed; installed kernels were not changed')
    return p.stdout if binary else p.stdout.decode('utf-8').strip()


@contextmanager
def source_repo(entry: dict, ref: str, source: Path | None, allow_network: bool):
    if not ref or ref.startswith('-') or any(ord(c) < 32 for c in ref):
        raise ValueError('Invalid upstream ref')
    if source is not None:
        path = source.expanduser().resolve()
        revision = git(['rev-parse', '--verify', '--end-of-options', ref + '^{commit}'], cwd=path)
        yield path, revision
    else:
        if not allow_network:
            raise ValueError('Upstream fetch requires --allow-network; verify is offline')
        with tempfile.TemporaryDirectory(prefix='rfs-upstream-') as temp:
            path = Path(temp)
            git(['init', '--bare', '-q', str(path)])
            git(['fetch', '--depth', '1', '--no-tags', entry['repository'] + '.git', ref], cwd=path)
            revision = git(['rev-parse', '--verify', 'FETCH_HEAD^{commit}'], cwd=path)
            yield path, revision


def selected_snapshot(repo: Path, revision: str, patterns: list[str]) -> dict[str, bytes]:
    listing = git(['ls-tree', '-rz', '--long', revision], cwd=repo, binary=True)
    payload: dict[str, bytes] = {}
    seen = set()
    total = 0
    for row in listing.split(b'\0'):
        if not row:
            continue
        info, raw_path = row.split(b'\t', 1)
        name = raw_path.decode('utf-8')
        if not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
            continue
        safe_path(name)
        if not permitted(name):
            raise ValueError(f'Disallowed selected upstream file: {name}')
        mode, kind, oid, size = info.decode('ascii').split()
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise ValueError(f'Symlink/submodule rejected: {name}')
        if name.casefold() in seen:
            raise ValueError('Case-insensitive filename collision')
        seen.add(name.casefold())
        count = int(size)
        total += count
        if count > MAX_FILE or total > MAX_TOTAL:
            raise ValueError('Upstream snapshot exceeds bounded size')
        raw = git(['cat-file', 'blob', oid], cwd=repo, binary=True)
        if len(raw) != count:
            raise ValueError('Git blob length mismatch')
        suffix = Path(name).suffix.lower()
        if suffix in TEXT_EXT or name in {'LICENSE', 'NOTICE'}:
            raw.decode('utf-8')
            if b'\x00' in raw:
                raise ValueError('NUL in source text')
        if suffix in {'.pptx', '.vsdx'}:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if any(PurePosixPath(n).suffix.lower() in FONT_EXT or '/fonts/' in n.lower() for n in z.namelist()):
                    raise ValueError('Font payloads are not redistributed')
        payload[name] = raw
    if 'LICENSE' not in payload or not payload['LICENSE'].strip():
        raise ValueError('Upstream LICENSE is mandatory')
    return payload


def changed_files(old: dict, new: dict) -> dict:
    return {'added': sorted(set(new) - set(old)), 'removed': sorted(set(old) - set(new)),
            'changed': sorted(p for p in set(old) & set(new) if old[p] != new[p])}


def sync(root: Path, name: str, *, action: str = 'check', ref: str | None = None,
         source: Path | None = None, allow_network: bool = False, bootstrap: bool = False,
         accept_license_change: bool = False) -> dict:
    root = root.expanduser().resolve()
    lock_path = root / LOCK
    before = lock_path.read_bytes()
    lock = read_lock(root)
    if name not in lock['kernels'] or action not in {'check', 'pull'}:
        raise ValueError('Unknown kernel/action')
    entry = lock['kernels'][name]
    verify_entry(root, entry, bootstrap=bootstrap)
    requested = ref or (entry['revision'] if bootstrap else entry.get('branch', 'main'))
    with source_repo(entry, requested, source, allow_network) as (repo, revision):
        payload = selected_snapshot(repo, revision, entry['include'])
    files = {p: {'sha256': digest(raw), 'bytes': len(raw)} for p, raw in sorted(payload.items())}
    delta = changed_files(entry.get('files', {}), files)
    license_changed = digest(payload['LICENSE']) != entry['license_sha256']
    result = {'kernel': name, 'from_revision': entry['revision'], 'to_revision': revision,
              'diff': delta, 'license_changed': license_changed, 'files': len(files),
              'bytes': sum(r['bytes'] for r in files.values()), 'status': 'CHECKED_NOT_APPLIED'}
    if action == 'check':
        return result
    if license_changed and not accept_license_change:
        raise ValueError('Upstream license changed; review terms before --accept-license-change')
    if not any(delta.values()) and revision == entry['revision']:
        return dict(result, status='UP_TO_DATE')
    parent = root / 'kernels'
    parent.mkdir(parents=True, exist_ok=True)
    mutex = parent / '.upstream-sync.lock'
    fd = os.open(mutex, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    target = root / entry['destination']
    try:
        # Same-filesystem staging makes replace atomic on supported local filesystems.
        with tempfile.TemporaryDirectory(prefix='.sync-', dir=parent) as temp:
            stage = Path(temp) / 'new'
            backup = Path(temp) / 'old'
            stage.mkdir()
            for rel, raw in payload.items():
                p = stage / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
            if lock_path.read_bytes() != before:
                raise ValueError('Upstream lock changed concurrently')
            verify_entry(root, entry, bootstrap=bootstrap)
            lock['kernels'][name] = dict(entry, revision=revision, files=files, license_sha256=digest(payload['LICENSE']))
            replacement = lock_path.with_name('.upstreams.lock.new')
            if replacement.exists():
                raise ValueError('Stale lock transaction; inspect before retrying')
            replacement.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            had_old = target.exists()
            swapped = False
            try:
                if had_old:
                    target.rename(backup)
                stage.rename(target)
                swapped = True
                os.replace(replacement, lock_path)
            except BaseException:
                if swapped and target.exists():
                    shutil.rmtree(target)
                if backup.exists():
                    backup.rename(target)
                raise
            finally:
                replacement.unlink(missing_ok=True)
    finally:
        mutex.unlink(missing_ok=True)
    return dict(result, status='UPDATED_UNTESTED', next='Run regression and smoke tests, inspect diff, then git commit. Use git revert for a committed rollback.')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['verify', 'check', 'pull'])
    p.add_argument('--kernel', choices=['design', 'layout', 'all'], default='all')
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--ref', help='Default: tracked branch; bootstrap defaults to locked revision')
    p.add_argument('--source', type=Path, help='Explicit local Git checkout or bare mirror; no network')
    p.add_argument('--allow-network', action='store_true')
    p.add_argument('--bootstrap', action='store_true', help='Only populate empty kernels at locked revisions')
    p.add_argument('--accept-license-change', action='store_true')
    a = p.parse_args()
    results = []
    try:
        lock = read_lock(a.root)
        names = list(lock['kernels']) if a.kernel == 'all' else [a.kernel]
        if a.source and len(names) != 1:
            raise ValueError('--source requires one explicit --kernel')
        for name in names:
            if a.action == 'verify':
                results.append(dict(verify_entry(a.root, lock['kernels'][name]), kernel=name))
            else:
                results.append(sync(a.root, name, action=a.action, ref=a.ref, source=a.source,
                                    allow_network=a.allow_network, bootstrap=a.bootstrap,
                                    accept_license_change=a.accept_license_change))
        print(json.dumps({'status': 'COMPLETE', 'results': results}, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'BLOCKED_OR_PARTIAL', 'completed': results, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
