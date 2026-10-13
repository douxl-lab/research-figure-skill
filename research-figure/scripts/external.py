"""Optional external adapters and explicit, non-executable skill handoffs."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from core import RFSValidationError, hash_file, write_json
from prompting import design_brief


KEY_NAMES = ("OPENROUTER_API_KEY", "GOOGLE_API_KEY")
RETIRED_IMAGE_MODELS = {
    "gemini-3.1-flash-image-preview": "shut down June 25, 2026",
    "gemini-3-pro-image-preview": "shut down June 25, 2026",
}


def _configured_image_model(root: Path | None) -> tuple[str | None, str | None]:
    if root is None:
        return None, None
    for basename in ("model_config.yaml", "model_config.template.yaml"):
        config_file = root / "configs" / basename
        if not config_file.is_file():
            continue
        try:
            raw = config_file.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r'(?m)^\s*image_gen_model_name\s*:\s*[\x27\x22]?([^\x27\x22\s#]+)', raw)
        if match:
            return match.group(1), basename
    return None, None


def paperbanana_status() -> dict:
    root_raw = os.environ.get("PAPERBANANA_ROOT", "")
    root = Path(root_raw).expanduser().resolve() if root_raw else None
    script = root / "skill" / "run.py" if root else None
    path_ready = bool(script and script.is_file())
    env_key_ready = any(os.environ.get(key, "").strip() for key in KEY_NAMES)
    config_file = root / "configs" / "model_config.yaml" if root else None
    local_config = False
    if config_file and config_file.is_file():
        try:
            cfg_text = config_file.read_text(encoding="utf-8")
            local_config = bool(re.search(r"^\s*(?:google_api_key|openrouter_api_key)\s*:\s*['\"]?[^'\"\s#]+", cfg_text, flags=re.M))
        except OSError:
            pass
    image_model, model_source = _configured_image_model(root)
    deprecated_reason = RETIRED_IMAGE_MODELS.get(image_model or "")
    return {"root": str(root) if root else None,
            "script_found": path_ready,
            "credentials_present": bool(env_key_ready or local_config),
            "ready": bool(path_ready and (env_key_ready or local_config)),
            "configured_image_model": image_model,
            "configured_image_model_source": model_source,
            "image_model_warning": (f"{image_model} was {deprecated_reason}; update config or pass --paperbanana-image-model"
                                    if deprecated_reason else None),
            "note": "Credentials are presence-checked only, never printed or tested against provider"}


def doctor() -> dict:
    import importlib.util
    pb = paperbanana_status()
    pf = os.environ.get("RFS_PAPERFIG_SKILL", "")
    sv = os.environ.get("RFS_SIVIA_SKILL", "")
    return {
        "python": sys.version.split()[0],
        "tikz": {"xelatex": bool(shutil.which("xelatex")), "pdftocairo": bool(shutil.which("pdftocairo")),
                 "ready": bool(shutil.which("xelatex") and shutil.which("pdftocairo"))},
        "matplotlib_available": bool(importlib.util.find_spec("matplotlib")),
        "paperbanana": pb,
        "paper_fig_skill_declared": bool(pf),
        "paper_fig_skill_path_exists": bool(pf and Path(pf).expanduser().exists()),
        "sivia_skill_declared": bool(sv),
        "sivia_skill_path_exists": bool(sv and Path(sv).expanduser().exists()),
        "note": "Declaring an external skill path does not prove the host can invoke that skill"
    }


def _model_brief(spec: dict) -> str:
    nodes = spec.get("diagram", {}).get("nodes", [])
    edges = spec.get("diagram", {}).get("edges", [])
    lines = [
        "Create a scientific method DIAGRAM (not an empirical plot).",
        "Only use the listed, science-relevant objects and directed relationships.",
        "Do not add model modules, numerical results, or unsupported equations.",
        "Any details not listed here are unknown rather than invented.",
        f"Title: {spec['title']}",
        f"Scientific claim: {spec['scientific_claim']}",
        "NODES (IDs and exact displayed labels):"
    ]
    lines.extend(f"- {n['id']}: {n['label'].replace(chr(10), ' / ')}" for n in nodes)
    lines.append("EDGES (source -> target; preserve direction):")
    lines.extend(f"- {e['source']} -> {e['target']}"
                 + (f" [{e['label']}]" if e.get('label') else "")
                 + (" [feedback]" if e.get("feedback") else "")
                 for e in edges)
    if any(e.get("status") != "verified" for e in spec.get("evidence", [])):
        lines.append("MANDATORY: Make the status DRAFT / SCIENTIFIC STRUCTURE UNVERIFIED visible; this does not depict validated code.")
    # PaperBanana owns its internal Retriever/Planner/Stylist/Visualizer/Critic.
    # Feed it a trustworthy *content brief*, not a second complete agent loop.
    if spec.get("design"):
        lines.append("DESIGN INTENT / CONSTRAINTS (illustrative directions only; science above is binding):")
        lines.append(design_brief(spec))
    return "\n".join(lines) + "\n"


def call_paperbanana(spec: dict, out_dir: Path, *, allow_external: bool,
                     candidates: int = 2, timeout: int = 1800,
                     image_model: str | None = None) -> dict:
    if not allow_external:
        raise RFSValidationError("External API/network use not authorized. Re-run with --allow-external only after user approval")
    if not 1 <= candidates <= 8:
        raise RFSValidationError("--candidates must be between 1 and 8")
    if not 60 <= timeout <= 7200:
        raise RFSValidationError("--timeout must be between 60 and 7200 seconds")
    status = paperbanana_status()
    if not status["ready"]:
        raise RFSValidationError("PaperBanana unavailable: set PAPERBANANA_ROOT and provider credentials, then run doctor")
    if image_model is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,128}", image_model):
            raise RFSValidationError("Invalid --paperbanana-image-model identifier")
        if image_model in RETIRED_IMAGE_MODELS:
            raise RFSValidationError("Requested PaperBanana image model has been shut down; use a maintained model")
    elif status.get("image_model_warning"):
        raise RFSValidationError(status["image_model_warning"])
    out_dir.mkdir(parents=True, exist_ok=True)
    input_path = out_dir / "paperbanana-method.txt"
    input_path.write_text(_model_brief(spec), encoding="utf-8")
    output_file = out_dir / "paperbanana.png"
    cmd = [sys.executable, str(Path(status["root"]) / "skill" / "run.py"),
           "--content-file", str(input_path),
           "--caption", spec["title"],
           "--task", "diagram", "--output", str(output_file),
           "--num-candidates", str(candidates), "--retrieval-setting", "none",
           "--exp-mode", "demo_full"]
    if image_model:
        cmd.extend(["--image-gen-model-name", image_model])
    try:
        res = subprocess.run(cmd, cwd=status["root"], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RFSValidationError(f"PaperBanana timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise RFSValidationError(f"Could not start PaperBanana: {exc}") from exc
    # Never persist raw provider output: it may disclose API keys from config files
    # or unpublished method text that cannot be reliably scrubbed with regexes.
    write_json(out_dir / "paperbanana-run.json", {
        "exit_code": res.returncode,
        "requested_image_model_override": image_model,
        "stdout_line_count": len(res.stdout.splitlines()),
        "stderr_line_count": len(res.stderr.splitlines()),
        "note": "Raw provider stdout/stderr intentionally not retained to protect credentials and unpublished source content"
    })
    images = sorted(p for p in out_dir.glob("paperbanana*.png") if p.is_file() and p.stat().st_size > 0)
    if res.returncode != 0 or not images:
        raise RFSValidationError(f"PaperBanana failed (exit={res.returncode}); see paperbanana-run.json and upstream logs in your own controlled environment")
    return {
        "engine": "paperbanana", "artifacts": [str(p.resolve()) for p in images],
        "candidate_count": len(images), "input_path": str(input_path.resolve()),
        "provider_calls_authorized": True,
        "known_limitations": ["AI-generated image not natively editable PPTX", "Generated labels and arrows require human scientific review", "The requested model must also be supported by the installed PaperBanana SDK/provider", "Some PaperBanana versions download a reference dataset even with retrieval=none"]
    }


def create_handoff(spec: dict, spec_path: str | Path, out_dir: Path, backend: str,
                   reference: str | None = None) -> dict:
    if backend not in {"paper-fig", "sivia"}:
        raise RFSValidationError("Handoff backend must be paper-fig or sivia")
    out_dir.mkdir(parents=True, exist_ok=True)
    spec_path = Path(spec_path).expanduser().resolve()
    ref = Path(reference).expanduser().resolve() if reference else None
    if ref and not ref.is_file():
        raise RFSValidationError(f"Approved reference not found: {ref}")
    nodes = spec.get("diagram", {}).get("nodes", [])
    edges = spec.get("diagram", {}).get("edges", [])
    # Rebuild tasks can move across agent contexts: keep a snapshot of the
    # scientific contract, but do not copy raw private datasets by default.
    snapshot_path = out_dir / "figure-spec.snapshot.json"
    write_json(snapshot_path, spec)
    lines = [
        f"# Editable scientific figure handoff — {backend}",
        "",
        "**Handoff only — downstream Skill NOT yet executed.**",
        "",
        f"Figure ID: `{spec['figure_id']}`",
        f"Original FigureSpec: `{spec_path}`",
        f"FigureSpec snapshot: `{snapshot_path.resolve()}`",
        f"Title: {spec['title']}",
        f"Scientific intent: {spec['scientific_claim']}",
        f"Approved visual reference: `{ref}`" if ref else "No approved image supplied; construct from exact scientific structure, use consistent academic style, and preserve change scope.",
        "",
        "## Exact semantic objects",
        *[f"- Node `{n['id']}`: {n['label'].replace(chr(10), ' / ')}" for n in nodes],
        "",
        "## Exact directed connections",
        *[f"- `{e['source']}` -> `{e['target']}`" + (f": {e['label']}" if e.get('label') else "") for e in edges],
        "",
        "## Evidence & editability rules",
        "- Ground every scientific element in the FigureSpec; pending sources remain pending.",
        "- Preserve an approved reference's visual hierarchy and content; do not treat editability as permission to redesign.",
        "- Use native editable text, shapes, and connectors where practical; do not flatten entire figure as one image.",
        "- Keep real scientific imagery as separate source images with editable annotation layers.",
        "- Check actual PPTX/draw.io file and actual target-rendered preview; log any missing verification as PENDING.",
        "- Do not invent empirical measurements, precision, uncertainty, equations, or training/inference paths.",
        "",
        "## Backend-specific instruction",
        ("Use the installed paper-fig Skill to construct a faithful editable PPTX. Its required presentation runtime must be available."
         if backend == "paper-fig" else
         "Use the installed Sivia skills with a supported native PowerPoint/WPS/draw.io backend. Preserve its mandatory review requirements where applicable."),
        "",
        "## Deliverables requested",
        "- Native editable project file (.pptx, or .drawio if requested and supported)",
        "- Preview exported from that same file, not a separately reconstructed PNG",
        "- Short editability and source fidelity report",
    ]
    (out_dir / "handoff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    receipt = {"backend": backend, "status": "NOT_EXECUTED", "figure_id": spec["figure_id"],
               "figure_spec": str(spec_path), "approved_reference": str(ref) if ref else None,
               "approved_reference_sha256": hash_file(ref) if ref else None,
               "spec_snapshot": str(snapshot_path.resolve()),
               "handoff_markdown": str((out_dir / "handoff.md").resolve()),
               "warning": "No PPTX/draw.io output was created by the handoff command"}
    write_json(out_dir / "handoff.json", receipt)
    return receipt
