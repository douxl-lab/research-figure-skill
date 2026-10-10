"""Provider-adapted creative prompts and candidate review receipts.

No network, model execution or image inspection occurs here. These files are
instructions for a capable host agent/image tool, never evidence of a result.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core import ASSETS, RFSValidationError, hash_file, read_json, write_json
from model_catalog import choose_model

PROFILE_FILE = ASSETS / "prompts" / "model-profiles.json"
VALID_STAGES = {"draft", "refine"}


def _profiles() -> dict[str, Any]:
    return read_json(PROFILE_FILE)


def _check_raster_image(path: Path) -> None:
    """Fast header preflight, not a complete decoder/vision review."""
    if not path.is_file() or path.stat().st_size < 48 or path.stat().st_size > 150 * 1024 * 1024:
        raise RFSValidationError(f"Candidate image missing, empty, or over local size limit: {path}")
    with path.open("rb") as handle:
        h = handle.read(32)
    ext = path.suffix.lower()
    valid = ((ext == ".png" and h.startswith(b"\x89PNG\r\n\x1a\n") and h[12:16] == b"IHDR" and int.from_bytes(h[16:20], "big") > 0 and int.from_bytes(h[20:24], "big") > 0)
             or (ext in {".jpg", ".jpeg"} and h.startswith(b"\xff\xd8\xff"))
             or (ext == ".webp" and h.startswith(b"RIFF") and h[8:12] == b"WEBP"))
    if not valid:
        raise RFSValidationError(f"Candidate is not a plausible image of its declared type: {path}")


def _out_dir(folder: str | Path, files: tuple[str, ...], overwrite: bool) -> Path:
    out = Path(folder).expanduser().resolve()
    stale = [out / name for name in files if (out / name).exists()]
    if stale and not overwrite:
        raise RFSValidationError("Prompt output exists; supply --overwrite to replace: " + ", ".join(map(str, stale)))
    out.mkdir(parents=True, exist_ok=True)
    return out


def _bullet(lines: list[str]) -> str:
    return "\n".join("- " + str(x).strip() for x in lines if str(x).strip()) or "- Not specified; do not invent details."


def _sci_inventory(spec: dict) -> str:
    nodes = spec.get("diagram", {}).get("nodes", [])
    edges = spec.get("diagram", {}).get("edges", [])
    node_rows = []
    for idx, n in enumerate(nodes, 1):
        note = " [VISUAL EMPHASIS]" if n.get("emphasis") else ""
        src = ", ".join(n.get("evidence_refs", [])) or "unattributed"
        node_rows.append(f"{idx}. id=`{n['id']}`; label={json.dumps(n['label'], ensure_ascii=False)}{note}; evidence={src}")
    edge_rows = []
    for idx, e in enumerate(edges, 1):
        edge_rows.append(f"{idx}. {e['source']} -> {e['target']}"
            + (f"; exact annotation={json.dumps(e['label'], ensure_ascii=False)}" if e.get("label") else "")
            + ("; FEEDBACK edge" if e.get("feedback") else "")
            + "; evidence=" + (", ".join(e.get("evidence_refs", [])) or "unattributed"))
    return "## Binding node inventory\n" + "\n".join(node_rows) + "\n\n## Binding directed edges\n" + "\n".join(edge_rows)


def design_brief(spec: dict) -> str:
    """Human-readable design guidance complementary to FigureSpec and an image.

    Positions inferred from a candidate image are intentionally not invented.
    """
    if spec.get("type") != "architecture":
        raise RFSValidationError("Design brief requires an architecture FigureSpec")
    d = spec.get("design", {})
    g = spec.get("generation", {})
    style = spec.get("style", {})
    pending = [e.get("id", "unknown") for e in spec.get("evidence", []) if e.get("status") != "verified"]
    exact_labels = [n["label"].replace("\n", " / ") for n in spec["diagram"]["nodes"]]
    return (f"# Scientific figure design brief — {spec['figure_id']}\n\n"
      "**Status: design intentions, not an automatically validated image or an approved editable file.**\n\n"
      f"## Scientific message\n{spec['scientific_claim']}\n\n"
      f"## Figure archetype and reading path\n- Archetype: `{g.get('archetype', 'overview')}`\n"
      f"- Reading direction: `{d.get('reading_path', 'left_to_right')}`\n"
      f"- Style preset: `{style.get('theme', 'academic-clean')}`\n"
      f"- Focal point: {d.get('visual_priority') or 'Scientifically distinctive mechanism, verified against sources'}\n\n"
      f"{_sci_inventory(spec)}\n\n"
      "## Layout and object guidance (design intention, not measured coordinates)\n"
      + _bullet(d.get("layout_notes", [])) + "\n\n"
      "## Text and scientific notation instructions\n"
      + _bullet(["Use exactly these labels: " + "; ".join(json.dumps(s, ensure_ascii=False) for s in exact_labels)] + d.get("text_notes", [])) + "\n\n"
      "## Connector rules\n"
      + _bullet(["Directed edges must remain attached to their correct source and target; avoid line-to-label overlaps and gratuitous cross-panel routes."] + d.get("connector_notes", [])) + "\n\n"
      "## Asset and editability plan\n"
      + _bullet(["Native editable text, regular modules, arrows and connectors wherever practical.",
                 "Complex illustration may be one *atomic* image layer only if it cannot be faithfully reconstructed.",
                 "Actual measured/example images must remain original source pixels with separate native labels."] + d.get("asset_notes", [])) + "\n\n"
      "## Forbidden or unsupported\n"
      + _bullet(["No fabricated experimental values, equations, or missing scientific mechanisms.",
                 "Do not represent a bitmap pasted in PPTX as fully editable."] + d.get("avoid", [])) + "\n\n"
      "## Unresolved scientific sources\n"
      + (", ".join(pending) if pending else "None marked pending; independent scientific review still required") + "\n\n"
      "## After selecting an image\n"
      "Record in design-notes.md the actual region positions, proportions, connector lanes, background/shape treatments, and intentionally non-native assets. "
      "These are *not inferred or certified by this script*. Resolve any conflict with the binding scientific structure before reconstruction.\n")


def build_prompt(spec: dict, *, profile: str, stage: str = "draft", reference: str | None = None,
                 change: str | None = None, region: str | None = None,
                 model: str | None = None, provider: str = "any", priority: str = "balanced",
                 registry: str | Path | None = None) -> str:
    if spec.get("type") != "architecture":
        raise RFSValidationError("Generative architecture prompt requires type=architecture; use code plotting for numerical data")
    profiles = _profiles()
    if stage not in VALID_STAGES:
        raise RFSValidationError("Prompt stage must be draft or refine")
    target = choose_model(model=model, provider=provider, priority=priority,
                          stage=stage, registry=registry) if model else None
    if target:
        profile = target["prompt_profile"]
    if profile not in profiles:
        raise RFSValidationError(f"Unknown profile {profile!r}; choose {', '.join(profiles)}")
    if stage == "refine":
        if not reference or not (change or "").strip() or Path(reference).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise RFSValidationError("Refinement requires an existing --reference image and a nonempty --change request")
        _check_raster_image(Path(reference).expanduser().resolve())
    elif reference or change or region:
        raise RFSValidationError("--reference, --change, and --region are only valid for --stage refine")
    g = spec.get("generation", {})
    d = spec.get("design", {})
    t = spec.get("target", {})
    theme = spec.get("style", {}).get("theme", "academic-clean")
    unverified = [e.get("id", "unknown") for e in spec.get("evidence", []) if e.get("status") != "verified"]
    size = f"{t.get('width_px', 1600)} × {t.get('height_px', 900)} pixels target; adapt aspect ratio if the image tool restricts size"
    if unverified:
        evidence_note = ("PROVISIONAL SCIENTIFIC DRAFT. Evidence references still pending: " + ", ".join(unverified)
                         + ". Do not depict uncertain relations as established experimentally. A draft status must remain visible in review usage.")
    else:
        evidence_note = "Sources are listed as verified by the FigureSpec author, but figure-level scientific review remains necessary."
    preface = ("You are creating a research-paper figure. Scientific structure below is a binding content constraint, not an invitation to invent facts. "
               "Use the design requirements for composition and illustrative language, but do not replace named modules or directed connections.\n\n")
    sections = [
      "# RFS — model-adapted scientific diagram prompt\n\n" + preface,
      "## 1 · Figure intent and evidence\n"
        + f"Archetype: {g.get('archetype', 'overview')}\n\nTitle for context (do NOT print as an in-figure title unless explicitly requested): {spec['title']}\n"
        + f"Single takeaway: {spec['scientific_claim']}\n\nEvidence policy: {evidence_note}\n",
      "## 2 · Non-negotiable scientific structure\n" + _sci_inventory(spec) + "\n",
      "## 3 · Spatial composition and connector routing\n"
        + f"Reading path: {d.get('reading_path', 'left_to_right')}.\nTarget dimensions: {size}.\n"
        + f"Focal hierarchy: {d.get('visual_priority') or 'Give the distinctive research mechanism visual priority without suppressing necessary context.'}\n"
        + "Organize related inputs/outputs into meaningful zones. Minimize long crisscross paths; avoid arrows piercing labels or unrelated modules. "
          "Use locally grouped branches or a readable inset when the topology is dense, but do not change relationships.\n"
        + "Additional layout notes:\n" + _bullet(d.get("layout_notes", [])) + "\n"
        + "Connector constraints:\n" + _bullet(d.get("connector_notes", [])) + "\n",
      "## 4 · Publication visual grammar and provider adaptation\n"
        + f"Style preset identity: {theme}. Academic visual hierarchy rather than UI cards or a marketing infographic. "
          "Distinguish scientific roles with a restrained, consistent palette; make content legible at final paper width and also in grayscale. "
          "Do not fill every whitespace region merely for decoration.\n"
        + _bullet(profiles[profile]["generation_guidance"] if stage == "draft" else profiles[profile]["refinement_guidance"])
        + ("\n\nTarget image-generation model: `" + target["id"] + "` (" + target["provider"] + "). "
           "This selection is an offline candidate only; host must verify access, exact endpoint and parameters.\n"
           + _bullet(target["draft_guidance"] if stage == "draft" else target["refinement_guidance"])
           if target else "") + "\n",
      "## 5 · Exact typography and editable handoff awareness\n"
        + "Text must match the node/edge labels literally (including capitalization). Avoid extra prose or invented symbols. "
          "Make labels readable as rendered; a later editable reconstruction will replace uncertain image-text with verified native text. "
          "Reserve clean separation between arrows and labels, and keep complex illustration elements distinct from semantic boxes.\n"
        + _bullet(d.get("text_notes", [])) + "\n",
      "## 6 · Negative constraints and output contract\n"
        + "No fabricated numerical results, charts, formulas, data, modality types, training arrows, gradients or modules. "
          "No overlapping text, ambiguous arrowheads, self-crossing cable bundles, dense spaghetti routing, cropped items, unrelated decorative watermarks, logos or non-scientific ornamental icons. A small required DRAFT / UNVERIFIED marker is allowed when scientific evidence is pending. "
          "No figure title inside image. The required output is a *visual draft* (PNG/JPEG as supported), NOT a native editable PPTX/draw.io.\n"
        + _bullet(d.get("avoid", [])) + "\n"
    ]
    if stage == "refine":
        ref = Path(reference).expanduser().resolve()
        sections.insert(1, "## Refinement-only scope (overrides global creative exploration)\n"
                     + f"Reference image: {ref.name} (sha256 {hash_file(ref)}). The host must attach the actual image to the image-edit call.\n"
                     + f"Changed region: {region or 'Only the region affected by the requested defect'}\n"
                     + f"Change request: {change.strip()}\n"
                     + "Preserve all unaffected regions pixel-compositionally where supported. Do not reinterpret approved layout, scientific relations or style. "
                       "If the correction requires a scientific topology change, request source review before modifying it.\n")
    return "\n\n".join(sections) + "\n"


def save_prompt_pack(spec: dict, spec_path: str | Path, out: str | Path, *, profile: str,
                     stage: str = "draft", reference: str | None = None,
                     change: str | None = None, region: str | None = None,
                     overwrite: bool = False, model: str | None = None,
                     provider: str = "any", priority: str = "balanced",
                     registry: str | Path | None = None) -> dict:
    out_dir = _out_dir(out, ("figure-prompt.md", "design-brief.md", "prompt-receipt.json", "model-call-plan.json"), overwrite)
    selected = choose_model(model=model, provider=provider, priority=priority,
                            stage=stage, registry=registry) if model else None
    prompt = build_prompt(spec, profile=profile, stage=stage, reference=reference, change=change,
                          region=region, model=model, provider=provider, priority=priority,
                          registry=registry)
    p = out_dir / "figure-prompt.md"
    p.write_text(prompt, encoding="utf-8")
    brief = out_dir / "design-brief.md"
    brief.write_text(design_brief(spec), encoding="utf-8")
    receipt = {
      "format": "rfs-prompt-pack/0.3.1", "status": "PROMPT_READY_NOT_RENDERED",
      "figure_id": spec["figure_id"], "profile": selected["prompt_profile"] if selected else profile, "stage": stage,
      "spec_path": str(Path(spec_path).expanduser().resolve()), "spec_sha256": hash_file(spec_path),
      "reference": str(Path(reference).expanduser().resolve()) if reference else None,
      "reference_sha256": hash_file(reference) if reference else None,
      "render_verified": False, "provider_execution": "NOT_EXECUTED",
      "model_id": selected["id"] if selected else None,
      "model_registry_sha256": selected["registry_sha256"] if selected else None,
      "model_registry_verified_at": selected["registry_verified_at"] if selected else None,
      "hashes": {p.name: hash_file(p), brief.name: hash_file(brief)},
      "note": "Compile locally. Attach reference image separately for edit prompts; do not assume model parsed local file path."
    }
    if selected:
        plan = {
          "status": "ADVISORY_NOT_SUBMITTED", "model_id": selected["id"],
          "provider": selected["provider"], "stage": stage,
          "selection_reason": selected["selection"], "priority": priority,
          "interface_hint": selected["interface"],
          "parameters_to_check": selected.get("parameters_to_check", {}),
          "input_requirements": ("Attach actual reference image bytes with edit request; "
                                  "file path in prompt is not the image") if stage == "refine" else "Scientific FigureSpec in compiled prompt",
          "registry_verified_at": selected["registry_verified_at"],
          "registry_sha256": selected["registry_sha256"],
          "provider_access_verified": False,
          "provider_api_call_performed": False,
          "warning": "Hints are not executable API payloads. Verify live model/SDK support and user authorization before any external call."
        }
        write_json(out_dir / "model-call-plan.json", plan)
        receipt["hashes"]["model-call-plan.json"] = hash_file(out_dir / "model-call-plan.json")
    write_json(out_dir / "prompt-receipt.json", receipt)
    return {"status": receipt["status"], "prompt": str(p), "design_brief": str(brief), "receipt": str(out_dir / "prompt-receipt.json"),
            "model_profile": receipt["profile"], "stage": stage,
            "model_id": selected["id"] if selected else None,
            "model_call_plan": str(out_dir / "model-call-plan.json") if selected else None}


def save_comparison(spec: dict, spec_path: str | Path, images: list[str], out: str | Path, overwrite: bool = False) -> dict:
    if spec.get("type") != "architecture":
        raise RFSValidationError("Candidate visual comparisons require type=architecture")
    if not 2 <= len(images) <= 8:
        raise RFSValidationError("Provide 2–8 candidate images")
    paths = [Path(x).expanduser().resolve() for x in images]
    if len(set(paths)) != len(paths) or any(not p.is_file() or p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} for p in paths):
        raise RFSValidationError("Candidate images must be distinct existing PNG/JPEG/WebP files")
    for p in paths:
        _check_raster_image(p)
    if len({hash_file(p) for p in paths}) != len(paths):
        raise RFSValidationError("Candidate images must have distinct file contents")
    out_dir = _out_dir(out, ("comparison-prompt.md", "comparison-receipt.json"), overwrite)
    desc = "\n".join(f"- Candidate {i}: {p.name}; SHA256 {hash_file(p)}" for i,p in enumerate(paths, 1))
    prompt = (f"# Blind scientific figure candidate review — {spec['figure_id']}\n\n"
              "The host must attach all candidate images. Local paths alone do not convey their visual contents. "
              "Before showing the preferred candidate, compare each candidate without inventing missing detail.\n\n"
              f"## Scientific target\n{spec['scientific_claim']}\n\n{_sci_inventory(spec)}\n\n"
              f"## Candidate inventory\n{desc}\n\n"
              "## Review procedure\n"
              "1. For each candidate, verify all *visible* nodes/edges and exact label readability; mark uninspectable facts PENDING.\n"
              "2. Judge primary reading spine, visual hierarchy, manuscript-width text legibility, visual distinctness, crossings and occlusions.\n"
              "3. Name scientific errors separately from visual deficiencies. No beauty score offsets scientific falsity.\n"
              "4. Select a candidate only if its scientific semantics can be repaired or pass; otherwise recommend a new draft.\n"
              "5. Write a precise region-level repair list and updated textual design guidance; do not silently alter scientific topology.\n\n"
              "## Response format\nFor each candidate: semantic findings, visual findings, status PASS/FAIL/PENDING, proposed fixes. "
              "Then give the preferred candidate, justification, remaining risks and any human approval required.\n")
    p = out_dir / "comparison-prompt.md"
    p.write_text(prompt, encoding="utf-8")
    receipt = {"format": "rfs-comparison/0.3", "status": "REVIEW_PROMPT_READY_NOT_EXECUTED",
               "figure_id": spec["figure_id"], "spec_path": str(Path(spec_path).resolve()),
               "spec_sha256": hash_file(spec_path),
               "candidates": [{"path": str(p), "sha256": hash_file(p)} for p in paths],
               "reviewer_vision_executed": False, "review_result": "PENDING", "prompt_sha256": hash_file(out_dir / "comparison-prompt.md")}
    write_json(out_dir / "comparison-receipt.json", receipt)
    return {"status": receipt["status"], "comparison_prompt": str(p), "receipt": str(out_dir / "comparison-receipt.json")}
