"""Resolve bundled RFS kernels; upstream names are compatibility aliases only."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {'paperbanana-native': 'design-native', 'paperbanana-provider': 'design-provider',
           'cvpr-figure': 'layout', 'vector': 'tikz', 'plot': 'plot-matplotlib'}


def locate(name: str, *, root: Path = ROOT, backend_dir: Path | None = None,
           environ: dict[str, str] | None = None) -> Path | None:
    if name not in {'design', 'layout'}:
        raise ValueError('Unknown RFS kernel')
    env = os.environ if environ is None else environ
    legacy = 'PAPERBANANA_ROOT' if name == 'design' else 'CVPR_FIGURE_ROOT'
    value = env.get('RFS_' + name.upper() + '_ROOT') or env.get(legacy)
    if value:  # An invalid explicit override never silently falls back.
        p = Path(value).expanduser().resolve()
        return p if p.is_dir() else None
    if backend_dir:
        for part in (name, 'PaperBanana' if name == 'design' else 'CVPR-Figure'):
            p = backend_dir.expanduser().resolve() / part
            if p.is_dir():
                return p
        return None
    p = root / 'kernels' / name
    return p.resolve() if p.is_dir() else None


def discover(*, root: Path = ROOT, backend_dir: Path | None = None,
             environ: dict[str, str] | None = None) -> dict:
    env = os.environ if environ is None else environ
    result = {}
    for name, files in (
        ('design', ('skill/native_host.py', 'skill/exchange.py', 'skill/run.py')),
        ('layout', ('scripts/render.py', 'scripts/validate.py')),
    ):
        location = locate(name, root=root, backend_dir=backend_dir, environ=env)
        result[name] = {
            'root': str(location) if location else None,
            'embedded': location == (root / 'kernels' / name).resolve(),
            'files': {f: bool(location and (location / f).is_file()) for f in files},
            'runtime_verified': False,
            'invocation_smoke_tested': False,
        }
    result['design']['dependencies_present'] = {
        m: importlib.util.find_spec(m) is not None for m in ('jsonschema', 'PIL')}
    return result


def python_for_design() -> str:
    import sys
    return os.environ.get('RFS_DESIGN_PYTHON') or os.environ.get('PAPERBANANA_PYTHON') or sys.executable
