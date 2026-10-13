"""Canonical PaperBanana FigureSpec v1 consumer boundary for RFS.

This adapter never executes generated plotting code. It invokes the authorized
PaperBanana five-agent engine only when expressly requested.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _api():
    # Imported only for canonical FigureSpec v1 operations. The standalone
    # legacy adapter and generic prompt-only workflows remain independent.
    from protocol import contract, interop, prompt_compiler
    return contract, interop, prompt_compiler


def is_canonical(path: str | Path) -> bool:
    try:
        with Path(path).expanduser().open(encoding="utf-8") as stream:
            return json.load(stream).get("schema_version") == "1.0.0"
    except (OSError, ValueError, AttributeError):
        return False


def _json(raw: dict) -> bytes:
    return (json.dumps(raw, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _new_dir(path: str | Path) -> Path:
    _, interop, _ = _api()
    directory = interop.ordinary_path(path)
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir(exist_ok=False)
    return directory


def _peer() -> tuple[Path, str]:
    root = os.environ.get("PAPERBANANA_ROOT", "")
    if not root:
        raise ValueError("Set PAPERBANANA_ROOT to the separately installed PaperBanana checkout")
    _, interop, _ = _api()
    location = interop.ordinary_path(root)
    if not (location / "skill" / "exchange.py").is_file():
        raise ValueError("Installed PaperBanana must provide skill/exchange.py (RFS Exchange v1)")
    python = os.environ.get("PAPERBANANA_PYTHON") or sys.executable
    return location, python


def _check_peer() -> dict:
    _, interop, _ = _api()
    root, python = _peer()
    res = subprocess.run([python, str(root / "skill/exchange.py"), "describe"],
                         cwd=root, capture_output=True, text=True, timeout=30, check=False)
    if res.returncode:
        raise ValueError("PaperBanana exchange preflight failed; verify its dependencies in the selected interpreter")
    try:
        peer = json.loads(res.stdout)
    except ValueError as exc:
        raise ValueError("PaperBanana exchange descriptor is malformed") from exc
    interop.assert_compatible(peer)
    return {"status": "COMPATIBLE", "schema_version": peer["schema_version"],
            "protocol": peer["protocol"], "root": str(root)}


def explain_route(spec: dict, *, engine="auto", allow_external=False) -> dict:
    kind = spec["kind"]
    if kind == "plot":
        if engine not in {"auto", "plot-matplotlib"}:
            raise ValueError("Quantitative figures only use source-data plotting")
        return {"engine": "plot-matplotlib", "requires_external": False}
    if kind == "hybrid":
        raise ValueError("Hybrid figures must be split into a diagram and original-data panels; do not synthesize measurements")
    if engine == "tikz":
        return {"engine": "tikz", "requires_external": False,
                "reason": "Explicit, local source-preserving vector rendering; layout and scientific review remain pending"}
    if engine not in {"auto", "paperbanana", "prompt-only"}:
        raise ValueError("Canonical v1 diagram uses PaperBanana or a host-generation prompt; not raw SVG layout")
    if engine == "paperbanana" and not allow_external:
        raise ValueError("External provider use requires explicit authorization --allow-external")
    return {"engine": "paperbanana" if (engine == "paperbanana" or engine == "auto" and allow_external) else "prompt-only",
            "requires_external": bool(engine == "paperbanana" or engine == "auto" and allow_external)}


def compile_draft(spec: dict, out: str | Path, *, model: str = "auto", provider: str = "any", candidate_id: str = "0",
                  priority: str = "balanced", registry: str | Path | None = None) -> dict:
    contract, interop, compiler = _api()
    spec = contract.validate_figure_spec(spec)
    if spec["kind"] != "diagram":
        raise ValueError("Draft image prompts require a canonical diagram")
    from model_catalog import choose_model
    selection = choose_model(model=model, provider=provider, priority=priority, stage="draft", registry=registry)
    instructions = (f"Layout: {spec['design']['layout']}\nComposition: {spec['design']['composition']}\n"
                    f"Typography: {spec['design']['typography']}\n"
                    "All scientific facts must match the immutable FigureSpec. This is design intent, not observed image QA.")
    capabilities = {"provider": selection["provider"], "model": selection["id"], "supports_system_prompt": False,
                    "supports_reference_image": False, "supports_editing": False,
                    "prompt_notes": ["Preserve exact evidence-bound scientific topology; do not invent experimental values.",
                                     *selection["draft_guidance"]]}
    result = compiler.compile_prompt(spec, instructions, capabilities, candidate_id=candidate_id, stage="design")
    target = _new_dir(out)
    payload = {"figure-spec.json": _json(spec), "prompt.txt": result.prompt.encode("utf-8"),
               "design-intent.md": ("# Pre-image composition intent (not inspected image evidence)\n\n" + instructions + "\n").encode("utf-8")}
    for name, raw in payload.items():
        (target / name).write_bytes(raw)
    manifest = {"format": "rfs-canonical-draft/1.0", "status": "PROMPT_READY_NOT_RENDERED",
                "figure_id": spec["figure_id"], "scientific_fingerprint": contract.scientific_fingerprint(spec),
                "model": selection["id"], "provider": selection["provider"],
                "model_registry_sha256": selection["registry_sha256"],
                "model_access_verified": False,
                "files_sha256": {name: _sha(raw) for name, raw in payload.items()}}
    (target / "manifest.json").write_bytes(_json(manifest))
    return {"status": manifest["status"], "prompt": str(target / "prompt.txt"),
            "design_intent": str(target / "design-intent.md"), "manifest": str(target / "manifest.json")}


def generate(spec_path: str | Path, out: str | Path, *, candidates=2, allow_external=False,
             timeout=1800, image_model=None) -> dict:
    _, interop, _ = _api()
    spec = interop.load_spec(spec_path)
    if not allow_external:
        raise ValueError("Use --allow-external only after authorizing provider input disclosure and possible fees")
    _check_peer()   # Fail before writing files or incurring provider costs.
    target = interop.ordinary_path(out)
    req_path = interop.prepare_request(spec_path, target / "request", candidates=candidates,
                  **({"image_model": image_model} if image_model else {}))
    root, python = _peer()
    try:
        res = subprocess.run([python, str(root / "skill/exchange.py"), "run", "--request", str(req_path), "--allow-external"],
                             cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("PaperBanana timed out; provider may have charged for an unknown outcome") from exc
    artifacts = []
    for folder in sorted((req_path.parent / "generated" / "bundles").glob("*")):
        if folder.is_dir():
            try:
                manifest, _, _ = interop.verify_result(folder, spec)
            except (ValueError, OSError):
                continue
            artifacts.append({"path": str(folder), "candidate_id": manifest["candidate_id"]})
    status = "GENERATED_UNREVIEWED" if res.returncode == 0 and len(artifacts) == candidates else "PARTIAL_OR_FAILED"
    return {"status": status, "request": str(req_path), "bundles": artifacts,
            "candidate_count": len(artifacts),
            "known_limitations": ["Live visual/scientific assessment pending", "No native editable file created"]}


def render_tikz_v1(spec: dict, output: str | Path) -> dict:
    """Explicit canonical v1 local renderer; not a replacement for PaperBanana's creative default."""
    from tikz_renderer import render_tikz
    return render_tikz(spec, output)


def render_plot_v1(spec: dict, output: str | Path) -> dict:
    contract, _, _ = _api()
    spec = contract.validate_figure_spec(spec)
    if spec["kind"] != "plot":
        raise ValueError("Quantitative plotting requires kind=plot and complete supplied source data")
    if len(spec["datasets"]) != 1:
        raise ValueError("Version 1 deterministic plot backend supports exactly one complete dataset; do not discard rows")
    dataset = spec["datasets"][0]
    xcol = dataset.get("encoding", {}).get("x")
    ycol = dataset.get("encoding", {}).get("y")
    series_col = dataset.get("encoding", {}).get("color")
    chart = dataset.get("encoding", {}).get("chart_type", "bar")
    if chart not in {"bar", "line", "scatter"} or not xcol or not ycol:
        raise ValueError("Require explicit x/y and bar, line or scatter encoding; never infer statistics")
    cols = dataset["columns"]
    if xcol not in cols or ycol not in cols or series_col and series_col not in cols:
        raise ValueError("Unknown encoded column")
    rows = [dict(zip(cols, row, strict=True)) for row in dataset["rows"]]
    xy = defaultdict(list)
    for row in rows:
        val = row[ycol]
        if type(val) not in (int, float) or not __import__("math").isfinite(val):
            raise ValueError("Y values must be finite source measurements; no imputation")
        group = str(row[series_col]) if series_col else "single"
        x = row[xcol]
        if chart in {"line", "scatter"} and (type(x) not in (int, float) or not __import__("math").isfinite(x)):
            raise ValueError("Line/scatter X values must be numeric")
        xy[group].append((x, val))
    if chart != "scatter":
        for group, coords in xy.items():
            if len({x for x, y in coords}) != len(coords):
                raise ValueError(f"Repeated X coordinate in group {group}; aggregate only with explicit scientific authorization")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ValueError("Install matplotlib to render supplied data; never substitute a generative numeric chart") from exc
    target = _new_dir(output)
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    palette = spec["design"]["palette"]
    try:
        import numpy as np
        if chart == "bar":
            categories = list(dict.fromkeys(str(x) for coords in xy.values() for x, _ in coords))
            if any(set(map(str, (x for x, _ in coords))) != set(categories) for coords in xy.values()):
                raise ValueError("Incomplete bar grid; refuse to invent missing values")
            width = .75 / len(xy)
            for i, (group, coords) in enumerate(xy.items()):
                values = {str(x): y for x, y in coords}
                ax.bar(np.arange(len(categories)) + (i - (len(xy)-1)/2)*width,
                       [values[x] for x in categories], width*.92, color=palette[i % len(palette)],
                       label=group if len(xy)>1 else None)
            ax.set_xticks(np.arange(len(categories)), categories)
            lower, upper = ax.get_ylim()
            ax.set_ylim(min(0, lower), max(0, upper))
        else:
            for i, (group, coords) in enumerate(xy.items()):
                if chart == "line":
                    coords = sorted(coords)
                    ax.plot([x for x,y in coords], [y for x,y in coords], marker="o",
                            color=palette[i % len(palette)], label=group if len(xy)>1 else None)
                else:
                    ax.scatter([x for x,y in coords], [y for x,y in coords],
                               color=palette[i % len(palette)], label=group if len(xy)>1 else None)
        ax.set_xlabel(xcol + (f" ({dataset['units'][xcol]})" if xcol in dataset.get("units", {}) else ""))
        ax.set_ylabel(ycol + (f" ({dataset['units'][ycol]})" if ycol in dataset.get("units", {}) else ""))
        ax.grid(axis="y", alpha=.18)
        if len(xy)>1:
            ax.legend(frameon=False)
        # Public demonstration fixtures must never look like measured paper results.
        notes = spec.get("provenance", {}).get("notes", [])
        if any(any(flag in str(note).lower() for flag in ("synthetic", "illustrative", "demo fixture")) for note in notes):
            fig.text(.5, .5, "SYNTHETIC DEMO — NOT EMPIRICAL RESULTS", ha="center", va="center",
                     rotation=15, fontsize=14, alpha=.27, color="#842A2A", weight="bold")
        paths = []
        for ext in ("svg", "pdf", "png"):
            name = f"figure.{ext}"
            fig.savefig(target / name, dpi=300, facecolor="white")
            paths.append(name)
    finally:
        plt.close(fig)
    (target / "figure-spec.json").write_bytes(_json(spec))
    # This is fixed RFS-owned source code, not model-generated Python. The output
    # contains its complete original dataset and a repeatable local invocation.
    script = '''#!/usr/bin/env python3
"""Reproduce the associated science-locked plot with the installed RFS v0.4 Skill."""
import json, os, sys
from pathlib import Path
skill = os.environ.get('RFS_SKILL_ROOT')
if not skill:
    raise SystemExit('Set RFS_SKILL_ROOT to your installed research-figure Skill directory')
sys.path.insert(0, str(Path(skill).resolve() / 'scripts'))
from bridge import render_plot_v1
spec = json.loads(Path(__file__).with_name('figure-spec.json').read_text(encoding='utf-8'))
render_plot_v1(spec, sys.argv[1] if len(sys.argv)>1 else str(Path(__file__).parent / 'reproduced'))
'''
    (target / "plot-reproduce.py").write_text(script, encoding="utf-8")
    receipt = {"format": "rfs-quantitative/1.0", "status": "DATA_PLOTTED_SCIENCE_REVIEW_PENDING",
               "source_dataset_sha256": dataset["sha256"], "scientific_fingerprint": contract.scientific_fingerprint(spec),
               "row_count": len(rows), "rfs_version": "0.4.0", "matplotlib_version": matplotlib.__version__,
               "files_sha256": {name: _sha((target / name).read_bytes()) for name in (*paths, "figure-spec.json", "plot-reproduce.py")}}
    (target / "manifest.json").write_bytes(_json(receipt))
    return {"status": receipt["status"], "artifacts": [str(target / n) for n in paths], "manifest": str(target / "manifest.json")}


def prepare_editable(spec_path: str | Path, bundle: str | Path, notes: str | Path, out: str | Path,
                     *, backend="paper-fig", approved=False) -> dict:
    contract, interop, _ = _api()
    if backend not in {"paper-fig", "sivia", "drawio"}:
        raise ValueError("Unsupported editable backend")
    spec = interop.load_spec(spec_path)
    manifest, actual, payloads = interop.verify_result(bundle, spec)
    if actual is None or actual["kind"] != "diagram":
        raise ValueError("Native reconstruction requires an accepted diagram bundle")
    from reconstruction import _validate_design_notes
    notes_text = Path(notes).read_text(encoding="utf-8")
    _validate_design_notes(notes_text)
    image = payloads["image"]
    package = _new_dir(out)
    files = {"figure-spec.json": _json(actual), "reference.png": image,
             "observed-design-notes.md": notes_text.encode("utf-8"),
             "design-intent.md": payloads["design"], "prompt.txt": payloads["prompt"]}
    for name, raw in files.items():
        (package / name).write_bytes(raw)
    (package / "handoff.md").write_text(
        "# Three-source editable reconstruction (NOT EXECUTED)\n\n"
        "Read `figure-spec.json` as the only scientific authority, `reference.png` for actual appearance, "
        "`observed-design-notes.md` for layout, object inventory, connectors and drawing details. "
        "`design-intent.md` is generative intent, not observed evidence. "
        "Rebuild native editable objects in approved layout; do not rasterize whole diagram. "
        "Compare the ACTUAL rendered PPTX/draw.io against `reference.png`, and correct scoped defects. "
        "Never invent missing scientific facts. Approval of the visual does not imply scientific verification.\n",
        encoding="utf-8")
    files["handoff.md"] = (package / "handoff.md").read_bytes()
    receipt = {"format": "rfs-native-handoff/1.0", "status": "READY_NOT_EXECUTED", "backend": backend,
               "approved": bool(approved), "figure_id": actual["figure_id"],
               "scientific_fingerprint": contract.scientific_fingerprint(actual),
               "source_candidate": manifest["candidate_id"],
               "files_sha256": {name: _sha(raw) for name, raw in files.items()},
               "native_file_verified": False, "scientific_review": "PENDING"}
    (package / "manifest.json").write_bytes(_json(receipt))
    return {"status": receipt["status"], "package": str(package), "manifest": str(package / "manifest.json")}


def audit_bundle(spec_path: str | Path, bundle: str | Path) -> dict:
    contract, interop, _ = _api()
    expected = interop.load_spec(spec_path)
    receipt = Path(bundle) / "manifest.json"
    if receipt.is_file():
        summary = json.loads(receipt.read_text(encoding="utf-8"))
        if summary.get("format") == "rfs-tikz/1.0":
            from tikz_renderer import audit_tikz
            return audit_tikz(expected, bundle)
    manifest, actual, files = interop.verify_result(bundle, expected)
    return {"integrity": "PASS", "candidate_id": manifest["candidate_id"],
            "scientific_fingerprint": contract.scientific_fingerprint(actual),
            "scientific_review": "PENDING", "image_review": "PENDING",
            "native_file": None, "editability_review": "NOT_APPLICABLE"}


def audit_handoff(folder: str | Path) -> dict:
    root = Path(folder).expanduser().resolve()
    receipt_path = root / "manifest.json"
    manifest = json.loads(receipt_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "rfs-native-handoff/1.0":
        raise ValueError("Not a canonical editable handoff")
    names = manifest.get("files_sha256", {})
    if not isinstance(names, dict) or not names:
        raise ValueError("Missing handoff file checksums")
    for name, expected in names.items():
        if not isinstance(name,str) or "/" in name or ".." in name or name == "manifest.json":
            raise ValueError("Unsafe handoff path")
        path = root / name
        if not path.is_file() or path.is_symlink() or _sha(path.read_bytes()) != expected:
            raise ValueError("Handoff artifact has been modified: " + name)
    return {"integrity": "PASS", "native_file_created": False,
            "render_verification": "PENDING", "scientific_review": "PENDING"}