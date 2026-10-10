#!/usr/bin/env python3
"""Research Figure Skill v0.3.1 — creative-first design with model-aware prompts.

No external services execute without explicit --allow-external.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from auditing import audit_file
from core import RFSValidationError, hash_file, load_and_validate, write_json
from diagram import render_diagram
from external import call_paperbanana, create_handoff, doctor, paperbanana_status
from plotting import render_plot
from prompting import save_prompt_pack, save_comparison
from model_catalog import catalog
from reconstruction import create_reconstruction_package, audit_reconstruction_package
import bridge


def _emit(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _load(spec_path: str) -> tuple[dict, dict]:
    spec, report = load_and_validate(spec_path)
    if not report["valid"]:
        raise RFSValidationError("Invalid FigureSpec:\n  " + "\n  ".join(report["errors"]))
    return spec, report


def route(spec: dict, engine: str = "auto", allow_external: bool = False) -> dict:
    """Select the appropriate *creation* path; do not infer native editability."""
    kind = spec["type"]
    if kind == "quantitative":
        if engine not in {"auto", "plot-matplotlib"}:
            raise RFSValidationError(f"Measured data cannot be rendered through {engine}; use plot-matplotlib")
        return {"engine": "plot-matplotlib", "reason": "True numerical data -> reproducible code; no image-model redraw", "externally_authorized": False, "degraded": False}
    if kind in {"editable_reconstruction", "evidence_panel"}:
        if engine != "auto":
            raise RFSValidationError(f"{kind} requires native/image preservation backend; use handoff or reconstruction-package")
        return {"engine": "handoff", "reason": "Requires a separate source-grounded native or empirical-image backend", "externally_authorized": False, "degraded": False}
    if kind == "architecture":
        creative = spec.get("generation", {}).get("intent", "creative") == "creative"
        if engine == "native-svg":
            return {"engine": "native-svg", "reason": "Explicit native SVG selected, suitable only for simple exact topology", "externally_authorized": False,
                    "degraded": creative, "unmet_intent": "Visual design exploration not provided by SVG" if creative else None}
        if engine == "prompt-only":
            return {"engine": "prompt-only", "reason": "Compile model-adapted figure prompt and textual design brief; host image generation not run", "externally_authorized": False, "degraded": False}
        if engine == "paperbanana":
            if not allow_external:
                raise RFSValidationError("PaperBanana needs explicit authorization before using --allow-external")
            if not paperbanana_status()["ready"]:
                raise RFSValidationError("PaperBanana unavailable; run doctor; use prompt-only with a capable host image model")
            return {"engine": "paperbanana", "reason": "Existing multi-agent design generator, no duplicate outer planner/stylist loop", "externally_authorized": True, "degraded": False}
        if engine == "auto":
            if creative:
                if allow_external and paperbanana_status()["ready"]:
                    return {"engine": "paperbanana", "reason": "Creative diagram with authorized, configured PaperBanana", "externally_authorized": True, "degraded": False}
                return {"engine": "prompt-only", "reason": "Creative-first: prepare professional prompt and design brief for host image model; do NOT substitute ugly SVG", "externally_authorized": False, "degraded": False,
                        "unmet_execution": "Image generation by a capable host / authorized provider is still pending"}
            return {"engine": "native-svg", "reason": "Explicit exact-intent structural draft; image model not required", "externally_authorized": False, "degraded": False}
    raise RFSValidationError(f"Unsupported route type={kind!r}, engine={engine!r}")


def _ensure_new(out: Path, names: tuple[str, ...], overwrite: bool) -> None:
    existing = [out / name for name in names if (out / name).exists()]
    existing.extend(p for p in out.glob("paperbanana_*.png") if p not in existing)
    if existing and not overwrite:
        raise RFSValidationError("Output exists (use --overwrite for an intentional rerun): " + ", ".join(str(p) for p in existing))
    if existing and overwrite:
        # Only delete reserved RFS output names after explicit --overwrite.
        # In particular, stale multi-candidate PaperBanana PNGs must not be
        # presented as if the current run had created them.
        for p in existing:
            if p.is_file():
                p.unlink()


def command_run(args: argparse.Namespace) -> dict:
    if bridge.is_canonical(args.spec):
        spec = bridge._api()[1].load_spec(args.spec)
        plan = bridge.explain_route(spec, engine=args.engine, allow_external=args.allow_external)
        if plan["engine"] == "plot-matplotlib":
            return bridge.render_plot_v1(spec, args.out)
        if plan["engine"] == "prompt-only":
            return bridge.compile_draft(spec, args.out,
                model=args.model or "auto", provider=args.provider or "any",
                priority=args.priority, registry=args.model_registry)
        return bridge.generate(args.spec, args.out, candidates=args.candidates,
              allow_external=args.allow_external, timeout=args.timeout,
              image_model=args.paperbanana_image_model)
    spec, validation = _load(args.spec)
    plan = route(spec, engine=args.engine, allow_external=args.allow_external)
    out = Path(args.out).expanduser().resolve()
    if plan["engine"] == "handoff":
        raise RFSValidationError("No local renderer for this figure type. Use handoff or reconstruction-package")
    if args.model is not None and plan["engine"] != "prompt-only":
        raise RFSValidationError("--model configures direct prompt compilation only; it does not override PaperBanana or numeric plot models")
    _ensure_new(out, ("manifest.json", "figure.svg", "figure.pdf", "figure.png", "paperbanana.png", "paperbanana_0.png"), args.overwrite)
    out.mkdir(parents=True, exist_ok=True)
    prompt_pack = None
    if spec["type"] == "architecture" and spec.get("generation", {}).get("intent", "creative") == "creative":
        prompt_pack = save_prompt_pack(spec, args.spec, out / "creative-prompts",
                                       profile=args.profile, overwrite=args.overwrite,
                                       model=args.model, provider=args.provider,
                                       priority=args.priority, registry=args.model_registry)
    if plan["engine"] == "prompt-only":
        if prompt_pack is None:
            prompt_pack = save_prompt_pack(spec, args.spec, out / "creative-prompts",
                                           profile=args.profile, overwrite=args.overwrite,
                                           model=args.model, provider=args.provider,
                                           priority=args.priority, registry=args.model_registry)
        result = {"engine": "prompt-only", "artifacts": [], "supporting_files": [prompt_pack["prompt"], prompt_pack["design_brief"]],
                  "known_limitations": ["Prompt creation is NOT image generation", "Human/model scientific and visual review still pending"]}
    elif plan["engine"] == "native-svg":
        result = render_diagram(spec, out / "figure.svg")
    elif plan["engine"] == "plot-matplotlib":
        result = render_plot(spec, args.spec, out)
    elif plan["engine"] == "paperbanana":
        result = call_paperbanana(spec, out, allow_external=args.allow_external,
                                  candidates=args.candidates, timeout=args.timeout,
                                  image_model=args.paperbanana_image_model)
    else:
        raise RFSValidationError(f"Unknown creation engine: {plan['engine']}")
    requested = list(spec.get("delivery", {}).get("formats", []))
    produced_formats = sorted({Path(p).suffix.lstrip(".").lower() for p in result["artifacts"]})
    pending_formats = sorted(set(requested) - set(produced_formats))
    if plan["engine"] == "prompt-only":
        delivery_state = "PROMPT_READY_NOT_RENDERED"
    else:
        delivery_state = "ARTIFACT_CREATED" if not pending_formats and not plan.get("degraded", False) else "PARTIAL_OUTPUT"
    manifest = {
        "format": "rfs-manifest/0.3", "figure_id": spec["figure_id"],
        "spec_path": str(Path(args.spec).expanduser().resolve()), "spec_sha256": hash_file(args.spec),
        "route": plan, "validation_warnings": validation["warnings"],
        "result": result, "prompt_pack": prompt_pack,
        "delivery": {"status": delivery_state, "requested_formats": requested,
                     "produced_formats": produced_formats, "pending_formats": pending_formats,
                     "degraded": bool(plan.get("degraded", False))},
        "artifact_sha256": {Path(p).name: hash_file(p) for p in result["artifacts"]},
        "verification": "Scientific interpretation, exact text, creative-visual quality and final file render remain PENDING"
    }
    write_json(out / "manifest.json", manifest)
    return {"status": delivery_state, "manifest": str((out / "manifest.json").resolve()),
            "route": plan, "artifacts": result["artifacts"],
            "prompt_pack": prompt_pack, "pending_formats": pending_formats,
            "limitations": result.get("known_limitations", []), "scientific_interpretation": "PENDING"}


def command_audit(args: argparse.Namespace) -> dict:
    if bridge.is_canonical(args.spec):
        return bridge.audit_bundle(args.spec, args.artifact)
    spec, _ = _load(args.spec)
    report = audit_file(spec, args.spec, args.artifact)
    dest = Path(args.output).expanduser().resolve() if args.output else Path(args.artifact).expanduser().resolve().parent / f"audit-{Path(args.artifact).suffix.lstrip('.').lower()}.json"
    write_json(dest, report)
    return {"overall": report["overall"], "audit_report": str(dest),
            "checks": {name: value["status"] for name, value in report["checks"].items()}}


def command_handoff(args: argparse.Namespace) -> dict:
    if bridge.is_canonical(args.spec):
        raise RFSValidationError("Canonical v1 native handoff requires a verified --bundle and image-bound design notes; use reconstruction-package")
    spec, _ = _load(args.spec)
    out = Path(args.out).expanduser().resolve()
    _ensure_new(out, ("handoff.md", "handoff.json"), args.overwrite)
    return create_handoff(spec, args.spec, out, args.backend, args.reference)


def command_prompt(args: argparse.Namespace) -> dict:
    if bridge.is_canonical(args.spec):
        if args.stage != "draft" or args.reference or args.change or args.region:
            raise RFSValidationError("Canonical image edits require PaperBanana actual reference-image editing; no prompt-only substitution")
        return bridge.compile_draft(bridge._api()[1].load_spec(args.spec), args.out,
                                    model=args.model or "auto", provider=args.provider or "any",
                priority=args.priority, registry=args.model_registry)
    spec, _ = _load(args.spec)
    return save_prompt_pack(spec, args.spec, args.out, profile=args.profile,
                            stage=args.stage, reference=args.reference, change=args.change,
                            region=args.region, overwrite=args.overwrite,
                            model=args.model, provider=args.provider,
                            priority=args.priority, registry=args.model_registry)


def add_model_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", help="Exact registered image model ID, or auto; absent uses legacy --profile")
    parser.add_argument("--provider", choices=["any", "openai", "gemini"], default="any",
                        help="Provider restriction for auto model selection; advisory, not account access check")
    parser.add_argument("--priority", choices=["speed", "balanced", "quality", "precise_edit"], default="balanced")
    parser.add_argument("--model-registry", help="Optional updated local JSON model registry path; no automatic network fetch")


def command_compare(args: argparse.Namespace) -> dict:
    if bridge.is_canonical(args.spec):
        raise RFSValidationError("For canonical v1, compare actual PaperBanana candidates through its Critic. Generic image comparison is NOT a scientific verification")
    spec, _ = _load(args.spec)
    return save_comparison(spec, args.spec, args.images, args.out, overwrite=args.overwrite)


def command_reconstruction_package(args: argparse.Namespace) -> dict:
    if bridge.is_canonical(args.spec):
        if not args.bundle:
            raise RFSValidationError("Canonical reconstruction requires an actual --bundle and image-bound --design-notes")
        return bridge.prepare_editable(args.spec, args.bundle, args.design_notes,
                args.out, backend=args.backend, approved=args.approved)
    if not args.reference:
        raise RFSValidationError("Legacy reconstruction requires --reference")
    spec, _ = _load(args.spec)
    return create_reconstruction_package(spec, args.spec, reference=args.reference,
        notes=args.design_notes, out=args.out, backend=args.backend, approved=args.approved,
        overwrite=args.overwrite)


def main() -> int:
    p = argparse.ArgumentParser(prog="rfs", description="Research Figure — reproducible diagrams, numeric charts, optional agent handoffs")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Inspect optional dependencies without executing external tools")
    models = sub.add_parser("models", help="List date-verified image model candidates and offline routing suggestions")
    models.add_argument("--provider", choices=["any", "openai", "gemini"], default="any")
    models.add_argument("--priority", choices=["speed", "balanced", "quality", "precise_edit"], default="balanced")
    models.add_argument("--stage", choices=["draft", "refine"], default="draft")
    models.add_argument("--model-registry", help="Optional updated local JSON model registry path")
    valid = sub.add_parser("validate", help="Validate FigureSpec, evidence refs and CSV structure")
    valid.add_argument("--spec", required=True)
    r = sub.add_parser("route", help="Choose one creation route; does not execute it")
    r.add_argument("--spec", required=True)
    r.add_argument("--engine", choices=["auto", "native-svg", "paperbanana", "plot-matplotlib", "prompt-only"], default="auto")
    r.add_argument("--allow-external", action="store_true")
    run = sub.add_parser("run", help="Generate actual SVG/plots or optionally invoke installed PaperBanana")
    run.add_argument("--spec", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--engine", choices=["auto", "native-svg", "paperbanana", "plot-matplotlib", "prompt-only"], default="auto")
    run.add_argument("--allow-external", action="store_true", help="Explicitly authorizes external PaperBanana API and possible downloads")
    run.add_argument("--profile", default="generic", help="Prompt adapter key from assets/prompts/model-profiles.json")
    add_model_options(run)
    run.add_argument("--candidates", type=int, default=2)
    run.add_argument("--timeout", type=int, default=1800, help="External invocation timeout in seconds")
    run.add_argument("--paperbanana-image-model", help="Explicit PaperBanana image model override, subject to upstream SDK support")
    run.add_argument("--overwrite", action="store_true")
    pg = sub.add_parser("prompt", help="Compile an image-model prompt and written design brief; NO image-model call")
    pg.add_argument("--spec", required=True)
    pg.add_argument("--stage", choices=["draft", "refine"], default="draft")
    pg.add_argument("--profile", default="generic", help="Prompt adapter key from assets/prompts/model-profiles.json")
    add_model_options(pg)
    pg.add_argument("--reference", help="Existing image to attach in a refinement call")
    pg.add_argument("--change", help="Exactly what to repair in the reference image")
    pg.add_argument("--region", help="Scope of local change")
    pg.add_argument("--out", required=True)
    pg.add_argument("--overwrite", action="store_true")
    cmp = sub.add_parser("compare", help="Prepare blind scientific candidate comparison prompt; NO vision review performed")
    cmp.add_argument("--spec", required=True)
    cmp.add_argument("--images", nargs="+", required=True)
    cmp.add_argument("--out", required=True)
    cmp.add_argument("--overwrite", action="store_true")
    pkg = sub.add_parser("reconstruction-package", help="Package FigureSpec + actual visual reference + detailed written design notes")
    pkg.add_argument("--spec", required=True)
    pkg.add_argument("--reference", help="Legacy reference; canonical v1 uses --bundle")
    pkg.add_argument("--bundle", help="Verified canonical v1 PaperBanana candidate bundle")
    pkg.add_argument("--design-notes", required=True)
    pkg.add_argument("--backend", choices=["paper-fig", "sivia", "drawio"], default="paper-fig")
    pkg.add_argument("--approved", action="store_true", help="Only if user has approved this specific reference design")
    pkg.add_argument("--out", required=True)
    pkg.add_argument("--overwrite", action="store_true")
    ap = sub.add_parser("audit-package", help="Verify reconstruction package bytes; native rendering stays PENDING")
    ap.add_argument("--package", required=True)
    hand = sub.add_parser("handoff", help="Create host-executable instructions; does NOT produce PPTX")
    hand.add_argument("--spec", required=True)
    hand.add_argument("--backend", choices=["paper-fig", "sivia"], required=True)
    hand.add_argument("--reference", help="Optional pre-approved reference image / SVG / PDF")
    hand.add_argument("--out", required=True)
    hand.add_argument("--overwrite", action="store_true")
    audit = sub.add_parser("audit", help="Audit existing artifact bytes; unperformed quality checks remain PENDING")
    audit.add_argument("--spec", required=True)
    audit.add_argument("--artifact", required=True)
    audit.add_argument("--output")
    args = p.parse_args()
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "models":
            result = catalog(provider=args.provider, priority=args.priority,
                             stage=args.stage, registry=args.model_registry)
        elif args.command == "validate":
            if bridge.is_canonical(args.spec):
                spec = bridge._api()[1].load_spec(args.spec)
                result = {"figure_id": spec["figure_id"], "valid": True,
                          "schema_version": "1.0.0", "scientific_review": "PENDING"}
            else:
                spec, report = load_and_validate(args.spec)
                result = {"figure_id": spec.get("figure_id"), **report}
            _emit(result)
            return 0 if report["valid"] else 2
        elif args.command == "route":
            if bridge.is_canonical(args.spec):
                spec = bridge._api()[1].load_spec(args.spec)
                result = {"figure_id": spec["figure_id"], "schema_version": "1.0.0",
                          "plan": bridge.explain_route(spec, engine=args.engine, allow_external=args.allow_external),
                          "scientific_review": "PENDING"}
            else:
                spec, report = _load(args.spec)
                result = {"figure_id": spec["figure_id"], "plan": route(spec, args.engine, args.allow_external),
                          "source_warnings": report["warnings"]}
        elif args.command == "run":
            result = command_run(args)
        elif args.command == "prompt":
            result = command_prompt(args)
        elif args.command == "compare":
            result = command_compare(args)
        elif args.command == "reconstruction-package":
            result = command_reconstruction_package(args)
        elif args.command == "audit-package":
            result = bridge.audit_handoff(args.package) if (Path(args.package) / "manifest.json").is_file() else audit_reconstruction_package(args.package)
        elif args.command == "handoff":
            result = command_handoff(args)
        elif args.command == "audit":
            result = command_audit(args)
        else:
            raise RFSValidationError(f"Unknown command {args.command}")
        _emit(result)
        return 0
    except (RFSValidationError, ValueError) as exc:
        _emit({"status": "ERROR", "reason": str(exc)})
        return 2
    except (PermissionError, FileNotFoundError, OSError) as exc:
        _emit({"status": "ERROR", "reason": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())