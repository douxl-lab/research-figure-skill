#!/usr/bin/env python3
"""RFS capability-aware orchestration. Planning never executes a backend.

The host must execute image tools itself; native preparation is not generation.
No downloads, provider calls, or credential discovery occur implicitly.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from kernels import ALIASES, discover, python_for_design

ROOT = Path(__file__).resolve().parents[1]
MODES = ("auto", "design-native", "design-provider", "tikz",
         "plot-matplotlib", "prompt-only", "layout", "native-svg", "image2-api", "llm-svg")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def make_plan(spec: dict[str, Any], capabilities: dict[str, dict[str, Any]], *,
              mode: str = "auto", host_image_tool: str | None = None,
              allow_external: bool = False, image2_root: Path | None = None,
              dry_run: bool = False) -> dict[str, Any]:
    mode = ALIASES.get(mode, mode)
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    canonical = spec.get("schema_version") == "1.0.0"
    kind = spec.get("kind") if canonical else spec.get("type")
    if kind not in {"diagram", "plot", "architecture", "quantitative", "hybrid",
                    "editable_reconstruction", "evidence_panel"}:
        raise ValueError("Unknown figure kind; validate FigureSpec before orchestration")
    # v0.7 capability maps remain readable; new outputs use neutral kernel IDs.
    capabilities = dict(capabilities)
    for alias, name in (("PaperBanana", "design"), ("CVPR-Figure", "layout")):
        if name not in capabilities and alias in capabilities:
            capabilities[name] = capabilities[alias]
        capabilities.pop(alias, None)
    pb = capabilities["design"]
    cv = capabilities["layout"]
    plan: dict[str, Any] = {
        "format": "rfs-workflow/1.0", "status": "PLANNED_NOT_EXECUTED",
        "mode": None, "capabilities": capabilities,
        "host_image_tool": host_image_tool, "external_authorized": allow_external,
        "image2_root": str(image2_root.resolve()) if image2_root else None, "dry_run": dry_run,
        "references": ["references/orchestration.md"], "blockers": [],
        "verification": {"runtime": "PENDING", "scientific": "PENDING",
                         "visual": "PENDING", "native_editability": "PENDING"},
    }
    if image2_root is not None:
        from image2_adapter import backend_script
        try:
            backend_script(image2_root, "generate")
            backend_script(image2_root, "edit")
        except (ValueError, OSError):
            plan["blockers"].append("Explicit image2-api installation is invalid; do not silently replace it")
    if kind in {"plot", "quantitative"}:
        if mode not in {"auto", "plot-matplotlib"}:
            raise ValueError("Measured data requires plot-matplotlib, never an image generator")
        plan["mode"] = "plot-matplotlib"
    elif kind in {"hybrid", "editable_reconstruction", "evidence_panel"}:
        if mode != "auto":
            raise ValueError("Preserve source images or use the existing verified reconstruction handoff")
        plan.update(mode="source-preserving-handoff", status="HOST_ACTION_REQUIRED")
        plan["references"].extend(["references/reconstruction.md", "references/quality-gates.md"])
    else:
        plan["references"].extend(["references/core-capabilities.md", "references/layout-library.md"])
        if mode == "auto":
            if not canonical and spec.get("generation", {}).get("intent") == "exact":
                mode = "native-svg"
            elif host_image_tool:
                mode = "design-native" if canonical and pb["files"]["skill/native_host.py"] else "bundled-host-workflow"
            elif image2_root is not None and (allow_external or dry_run):
                mode = "image2-api"
            elif allow_external and pb["files"]["skill/exchange.py"]:
                mode = "design-provider"
            else:
                mode = "blocked"
                plan["blockers"].append("No host image tool declared and no authorized design runtime; do not stop at a prompt or substitute plain boxes")
        if mode == "design-native":
            if not canonical:
                plan["blockers"].append("Native host requires canonical FigureSpec v1; do not silently convert legacy evidence")
            if not host_image_tool:
                plan["blockers"].append("An actual host image tool must be available; a CLI coordinator cannot generate images")
            if not pb["files"]["skill/native_host.py"]:
                plan["blockers"].append("Design native coordinator missing; install the pinned runtime or use the labelled bundled host workflow")
        elif mode == "design-provider":
            if not allow_external:
                plan["blockers"].append("Provider disclosure/cost authorization missing")
            if not pb["files"]["skill/exchange.py"]:
                plan["blockers"].append("Design exchange entry missing")
        elif mode == "image2-api":
            if not canonical:
                plan["blockers"].append("image2-api requires canonical FigureSpec v1")
            if image2_root is None:
                plan["blockers"].append("Supply the actual --image2-root installation")
            if not (allow_external or dry_run):
                plan["blockers"].append("Service/data/cost authorization is missing; an offline dry-run needs none")
            plan["references"].append("references/local-image-pipeline.md")
        elif mode == "llm-svg":
            if not canonical:
                plan["blockers"].append("LLM SVG handoff requires canonical FigureSpec v1")
            plan["status"] = "HOST_ACTION_REQUIRED"
            plan["references"].append("references/mechanism-figure-workflow.md")
        elif mode == "layout":
            if not all(cv["files"].values()):
                plan["blockers"].append("Layout renderer/validator missing")
        elif mode == "plot-matplotlib":
            raise ValueError("plot-matplotlib requires measured plot data")
        elif mode == "native-svg" and canonical:
            plan["blockers"].append("Canonical v1 does not support the legacy native-svg renderer; explicitly use TikZ or a reviewed CVPR spec")
        elif mode == "tikz" and not canonical:
            plan["blockers"].append("TikZ requires canonical FigureSpec v1")
        plan["mode"] = mode
        if mode in {"design-native", "design-provider", "bundled-host-workflow", "image2-api"}:
            plan["references"].append("references/design-core.md")
        if mode == "tikz":
            plan["references"].append("references/tikz-workflow.md")
    if dry_run and plan["mode"] != "image2-api":
        plan["blockers"].append("--dry-run is supported only for image2-api; use plan for other routes")
    if plan["blockers"]:
        plan["status"] = "BLOCKED"
    return plan


def _invoke(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int, require_json: bool = True) -> dict[str, Any]:
    """No shell interpolation and no retry of a potentially billable request."""
    try:
        done = subprocess.run(command, cwd=cwd, env=env, text=True,
                              capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Backend timed out; outcome may be unknown. Inspect outputs before retrying") from exc
    if done.returncode:
        # Do not copy external stderr, which may contain private material/keys.
        raise ValueError(f"Backend {Path(command[1]).name} exited {done.returncode}; inspect it locally, no automatic fallback")
    try:
        value = json.loads(done.stdout)
    except ValueError as exc:
        if require_json:
            raise ValueError("Backend returned malformed JSON; do not infer success") from exc
        return {"status": "COMMAND_COMPLETED_OUTPUT_UNPARSED"}
    if not isinstance(value, dict):
        raise ValueError("Backend response must be a JSON object")
    return value


def execute(plan: dict[str, Any], spec: Path, out: Path, *, root: Path = ROOT,
            candidates: int = 2, timeout: int = 1800,
            cvpr_spec: Path | None = None, layout_spec: Path | None = None,
            image2_config: Path | None = None, prompt: Path | None = None) -> dict[str, Any]:
    if plan["status"] == "BLOCKED":
        raise ValueError("; ".join(plan["blockers"]))
    if not 1 <= candidates <= 8 or not 1 <= timeout <= 7200:
        raise ValueError("candidates must be 1..8 and timeout 1..7200")
    root, spec, out = root.resolve(), spec.resolve(), out.resolve()
    if out == root or root in out.parents:
        raise ValueError("Job output must be outside the installed Skill")
    if out.exists():
        raise ValueError("A fresh output directory is required; never overwrite a prior figure")
    mode = ALIASES.get(plan["mode"], plan["mode"])
    cvpr_spec = layout_spec or cvpr_spec
    if mode == "layout" and (cvpr_spec is None or not cvpr_spec.is_file()):
        raise ValueError("Supply a reviewed --layout-spec; layout YAML is NOT FigureSpec v1")
    if mode == "image2-api" and (image2_config is None or prompt is None):
        raise ValueError("image2-api requires --image2-config and a reviewed --prompt file; see local-image-pipeline.md")
    env = dict(os.environ)
    pb_root = plan["capabilities"]["design"]["root"]
    if pb_root:
        env["RFS_DESIGN_ROOT"] = pb_root
        env["PAPERBANANA_ROOT"] = pb_root
    rfs = [sys.executable, str(root / "scripts/rfs.py")]
    validation = _invoke(rfs + ["validate", "--spec", str(spec)], cwd=spec.parent, env=env, timeout=60)
    if validation.get("valid") is not True:
        raise ValueError("FigureSpec validation failed")
    out.mkdir(parents=True, exist_ok=False)
    (out / "workflow-plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        if mode == "design-native":
            pb = Path(pb_root)
            native = [python_for_design(), str(pb / "skill/native_host.py")]
            job = out / "native-job"
            _invoke(native + ["prepare", "--spec", str(spec), "--job", str(job)], cwd=pb, env=env, timeout=60)
            task = _invoke(native + ["next", "--job", str(job)], cwd=pb, env=env, timeout=60)
            result = {"status": "HOST_ACTION_REQUIRED", "mode": mode, "job": str(job),
                      "next_task": task, "instruction": "Execute next/record through all five stages and verify; preparation is NOT image generation"}
        elif mode == "image2-api":
            command = [sys.executable, str(root / "scripts/image2_adapter.py"),
                       "--spec", str(spec), "--prompt", str(prompt.resolve()),
                       "--config", str(image2_config.resolve()), "--image2-root", plan["image2_root"],
                       "--out", str(out / "rendered"), "--candidates", str(candidates)]
            if plan["dry_run"]:
                command.append("--dry-run")
            elif plan["external_authorized"]:
                command.append("--allow-external")
            result = _invoke(command, cwd=spec.parent, env=env, timeout=timeout)
            result["mode"] = mode
        elif mode == "llm-svg":
            (out / "figure-spec.json").write_bytes(spec.read_bytes())
            result = {"status": "HOST_ACTION_REQUIRED", "mode": mode,
                      "scientific_spec": str(out / "figure-spec.json"),
                      "instruction": "The host LLM authors SVG code directly, then renders and inspects it. Do not call the image API or claim a generated SVG yet",
                      "references": plan["references"]}
        elif mode in {"bundled-host-workflow", "source-preserving-handoff"}:
            result = {"status": "HOST_ACTION_REQUIRED", "mode": mode,
                      "references": plan["references"], "scientific_spec": str(spec),
                      "instruction": "Read the bundled module and execute real host tools; do not report a design runtime execution"}
        elif mode == "layout":
            cv = Path(plan["capabilities"]["layout"]["root"])
            prefix = out / "figure"
            render = _invoke([sys.executable, str(cv / "scripts/render.py"), str(cvpr_spec.resolve()),
                              "-o", str(prefix), "-f", "svg,pptx,vsdx"], cwd=cvpr_spec.resolve().parent, env=env, timeout=timeout, require_json=False)
            audit = _invoke([sys.executable, str(cv / "scripts/validate.py"), str(cvpr_spec.resolve()),
                             "--svg", str(prefix.with_suffix(".svg")), "--json"], cwd=cvpr_spec.resolve().parent, env=env, timeout=60)
            files = [str(prefix.with_suffix("." + ext)) for ext in ("svg", "pptx", "vsdx")]
            if not all(Path(p).is_file() and Path(p).stat().st_size for p in files):
                raise ValueError("Layout kernel did not produce all requested files")
            import hashlib
            for name, source in (("figure-spec.json", spec), ("layout-spec.yaml", cvpr_spec)):
                (out / name).write_bytes(source.read_bytes())
            result = {"status": "GENERATED_UNREVIEWED", "mode": mode, "artifacts": files,
                      "artifact_sha256": {Path(f).name: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},
                      "layout_spec_sha256": hashlib.sha256(cvpr_spec.read_bytes()).hexdigest(),
                      "render": render, "audit": audit, "scientific_and_visual_review": "PENDING"}
        else:
            engine = "paperbanana" if mode == "design-provider" else mode
            command = rfs + ["run", "--spec", str(spec), "--out", str(out / "rendered"), "--engine", engine]
            if mode == "design-provider":
                command += ["--allow-external", "--candidates", str(candidates), "--timeout", str(timeout)]
            backend_result = _invoke(command, cwd=spec.parent, env=env, timeout=timeout + 30)
            result = {"status": backend_result.get("status", "BACKEND_RETURNED_REVIEW_REQUIRED"),
                      "mode": mode, "backend_result": backend_result}
    except (ValueError, OSError) as exc:
        (out / "workflow-result.json").write_text(json.dumps({"status": "FAILED_OR_UNKNOWN", "mode": mode,
            "error": str(exc), "retry": "Manual inspection required; no automatic provider retry"}, indent=2) + "\n", encoding="utf-8")
        raise
    (out / "workflow-result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "run", "doctor"))
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--backend-dir", type=Path, help="Explicit parent of design/layout kernel overrides; bundled kernels are the default")
    parser.add_argument("--mode", default="auto", metavar="MODE", help=", ".join(MODES))
    parser.add_argument("--host-image-tool", help="Actual available host tool name; never infer one from installed packages")
    parser.add_argument("--allow-external", action="store_true", help="Only after task/service-specific disclosure and cost authorization")
    parser.add_argument("--image2-root", type=Path, help="Explicit optional image2-api installation; never auto-cloned")
    parser.add_argument("--image2-config", type=Path, help="Project-local service config; no credentials in source")
    parser.add_argument("--prompt", type=Path, help="Reviewed prompt for image2-api")
    parser.add_argument("--dry-run", action="store_true", help="image2-api only: offline request validation, never generation")
    parser.add_argument("--layout-spec", "--cvpr-spec", dest="layout_spec", type=Path)
    parser.add_argument("--candidates", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    try:
        caps = discover(backend_dir=args.backend_dir)
        if args.action == "doctor":
            result = {"status": "DISCOVERY_ONLY", "capabilities": caps,
                      "registry": read_json(ROOT / "assets/capabilities.json"),
                      "notice": "File presence is not dependencies, host access, provider authorization, or runtime compatibility"}
        else:
            if args.spec is None:
                raise ValueError("--spec is required")
            plan = make_plan(read_json(args.spec), caps, mode=args.mode,
                             host_image_tool=args.host_image_tool, allow_external=args.allow_external,
                             image2_root=args.image2_root, dry_run=args.dry_run)
            if args.action == "plan":
                result = plan
            else:
                if args.out is None:
                    raise ValueError("--out is required")
                result = execute(plan, args.spec, args.out, candidates=args.candidates,
                                 timeout=args.timeout, layout_spec=args.layout_spec,
                                 image2_config=args.image2_config, prompt=args.prompt)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result.get("status") == "BLOCKED" else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
