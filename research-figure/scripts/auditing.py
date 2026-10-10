"""Conservative structural checks for actual artifact bytes.

No image-model, research-semantics, or target-application rendering judgement is
pretended by this library.
"""
from __future__ import annotations

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from core import hash_file, resolve_source

SVG_NS = "{http://www.w3.org/2000/svg}"
P_NS = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def verdict(state: str, message: str, **data: object) -> dict:
    return {"status": state, "details": message, **data}


def audit_file(spec: dict, spec_path: str | Path, artifact_path: str | Path) -> dict:
    source = Path(spec_path).expanduser().resolve()
    artifact = Path(artifact_path).expanduser().resolve()
    checks = {
        "source_integrity": verdict("PENDING", "Source validity not fully established"),
        "semantic_structure": verdict("PENDING", "No verified semantic structure assessment"),
        "numeric_integrity": verdict("PENDING", "Numeric claims not independently verified"),
        "native_editability": verdict("PENDING", "Editability not verified by native application"),
        "publication_visual_review": verdict("PENDING", "Actual target-size render not manually reviewed"),
        "scientific_interpretation": verdict("PENDING", "Requires checking real paper, code and data")
    }
    if not artifact.is_file() or artifact.stat().st_size <= 0:
        checks["artifact_exists"] = verdict("FAIL", f"Missing or empty artifact: {artifact}")
        return _report(spec, artifact, checks)
    checks["artifact_exists"] = verdict("PASS", f"Artifact exists; {artifact.stat().st_size} bytes")
    _source_check(spec, source, checks)
    ext = artifact.suffix.lower()
    if ext == ".svg":
        _audit_svg(spec, artifact, checks)
    elif ext == ".pptx":
        _audit_pptx(spec, artifact, checks)
    elif ext == ".png":
        if artifact.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            checks["artifact_format"] = verdict("FAIL", "Invalid PNG header")
        else:
            checks["artifact_format"] = verdict("PASS", "PNG header present")
            if spec.get("delivery", {}).get("editable"):
                checks["native_editability"] = verdict("FAIL", "Raster PNG alone is not an editable vector/native project")
    elif ext == ".pdf":
        if artifact.read_bytes()[:5] != b"%PDF-":
            checks["artifact_format"] = verdict("FAIL", "Invalid PDF header")
        else:
            checks["artifact_format"] = verdict("PASS", "PDF signature present; internal objects not evaluated")
    else:
        checks["artifact_format"] = verdict("PENDING", f"No deterministic verifier for extension {ext}")
    requested = set(spec.get("delivery", {}).get("formats", []))
    if requested and ext.lstrip(".") not in requested:
        checks["delivery_format"] = verdict(
            "PENDING", "Artifact is an intermediate format, not a requested final delivery format",
            current_format=ext.lstrip("."), requested_formats=sorted(requested)
        )
    elif requested:
        checks["delivery_format"] = verdict("PASS", "Artifact extension is one requested output; other requested outputs must be reviewed separately")
    _manifest_check(spec, source, artifact, checks)
    return _report(spec, artifact, checks)


def _source_check(spec: dict, spec_path: Path, checks: dict) -> None:
    ev = spec.get("evidence", [])
    if not ev:
        return
    missing = []
    pending = []
    found = 0
    for e in ev:
        if not e.get("path"):
            pending.append(e.get("id", "unknown"))
            continue
        path = resolve_source(spec_path, e["path"])
        if not path.is_file():
            missing.append(str(path))
        elif e.get("sha256") and hash_file(path).lower() != str(e["sha256"]).lower():
            missing.append(f"SHA256 mismatch: {path}")
        else:
            found += 1
    if missing:
        checks["source_integrity"] = verdict("FAIL", "Source files missing or mismatched", missing=missing)
    elif pending:
        checks["source_integrity"] = verdict("PENDING", "Some ledger entries lack local source files", pending=pending, source_files_found=found)
    else:
        checks["source_integrity"] = verdict("PASS", "Linked files exist; provided checksums match", source_files_found=found)


def _audit_svg(spec: dict, artifact: Path, checks: dict) -> None:
    try:
        root = ET.parse(artifact).getroot()
    except ET.ParseError as exc:
        checks["artifact_format"] = verdict("FAIL", f"Malformed SVG XML: {exc}")
        return
    if root.tag != SVG_NS + "svg":
        checks["artifact_format"] = verdict("FAIL", "Not an SVG root node")
        return
    checks["artifact_format"] = verdict("PASS", "Well-formed SVG XML")
    if spec.get("type") == "architecture":
        expected_nodes = {n["id"]: n["label"] for n in spec["diagram"]["nodes"]}
        expected_edges = {f'{e["source"]}__{e["target"]}__{i}' for i, e in enumerate(spec["diagram"]["edges"])}
        actual_groups = {g.get("data-rfs-node-id"): g for g in root.iter() if g.get("data-rfs-node-id")}
        actual_edges = {g.get("data-rfs-edge-id") for g in root.iter() if g.get("data-rfs-edge-id")}
        bad_labels = []
        for name, wanted in expected_nodes.items():
            g = actual_groups.get(name)
            if g is None:
                bad_labels.append(name)
                continue
            actual = "\n".join((t.text or "") for t in g.iter() if t.tag == SVG_NS + "tspan")
            if actual != wanted:
                bad_labels.append(name)
        if set(actual_groups) != set(expected_nodes) or actual_edges != expected_edges or bad_labels:
            checks["semantic_structure"] = verdict("FAIL", "SVG node/edge IDs or labels do not match FigureSpec",
                                                    missing_or_bad_labels=bad_labels,
                                                    expected_node_count=len(expected_nodes), actual_node_count=len(actual_groups),
                                                    expected_edge_count=len(expected_edges), actual_edge_count=len(actual_edges))
        else:
            checks["semantic_structure"] = verdict("PASS", "SVG contains the exact contract node/edge IDs and labels; scientific truth remains pending",
                                                    node_count=len(actual_groups), edge_count=len(actual_edges))
            checks["native_editability"] = verdict("PASS", "Node labels are SVG text/tspans and connectors are native SVG paths (not editable PPTX)")
    elif spec.get("type") == "quantitative":
        labels = [t.text for t in root.iter() if t.tag == SVG_NS + "text"]
        if labels:
            checks["native_editability"] = verdict("PASS", "SVG contains native text; check plotting provenance in manifest")
        else:
            checks["native_editability"] = verdict("PENDING", "No native SVG text found")


def _audit_pptx(spec: dict, artifact: Path, checks: dict) -> None:
    try:
        with zipfile.ZipFile(artifact) as z:
            slide_names = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml") and "/_rels/" not in n]
            if not slide_names:
                checks["artifact_format"] = verdict("FAIL", "PPTX contains no slide XML")
                return
            shape_count = picture_count = text_count = 0
            for name in slide_names:
                root = ET.fromstring(z.read(name))
                shape_count += len(list(root.iter(P_NS + "sp"))) + len(list(root.iter(P_NS + "cxnSp")))
                picture_count += len(list(root.iter(P_NS + "pic")))
                text_count += len([t for t in root.iter(A_NS + "t") if t.text and t.text.strip()])
    except (zipfile.BadZipFile, ET.ParseError, OSError) as exc:
        checks["artifact_format"] = verdict("FAIL", f"Invalid PPTX structure: {exc}")
        return
    checks["artifact_format"] = verdict("PASS", "PPTX slide XML is parseable", slide_count=len(slide_names),
                                        shapes=shape_count, images=picture_count, text_runs=text_count)
    if spec.get("delivery", {}).get("editable") and shape_count == 0 and picture_count > 0:
        checks["native_editability"] = verdict("FAIL", "PPTX contains pictures but no native shapes or connectors; possible flattened figure")
    else:
        checks["native_editability"] = verdict("PENDING", "Native-object inventory exists but object-level editability and target rendering need application checks",
                                               shapes=shape_count, images=picture_count, text_runs=text_count)


def _manifest_check(spec: dict, spec_path: Path, artifact: Path, checks: dict) -> None:
    p = artifact.parent / "manifest.json"
    if not p.is_file():
        return
    try:
        manifest = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        checks["manifest_integrity"] = verdict("FAIL", "Invalid manifest.json")
        return
    if manifest.get("spec_sha256") != hash_file(spec_path):
        checks["manifest_integrity"] = verdict("FAIL", "Source FigureSpec SHA256 changed since generation")
        return
    rec = manifest.get("artifact_sha256", {})
    if rec.get(artifact.name) != hash_file(artifact):
        checks["manifest_integrity"] = verdict("FAIL", "Artifact bytes do not match recorded hash")
        return
    checks["manifest_integrity"] = verdict("PASS", "Spec and artifact SHA256 match generation receipt")
    if spec.get("type") == "quantitative":
        csv_ref = manifest.get("result", {}).get("source_csv")
        csv_digest = manifest.get("result", {}).get("source_sha256")
        if csv_ref and csv_digest and Path(csv_ref).is_file() and hash_file(csv_ref) == csv_digest:
            checks["numeric_integrity"] = verdict("PASS", "Plot source CSV matches deterministic generation receipt; validity of experimental measurements not established")
        else:
            checks["numeric_integrity"] = verdict("FAIL", "Plot source CSV missing or differs from generation receipt")


def _report(spec: dict, artifact: Path, checks: dict) -> dict:
    states = {entry["status"] for entry in checks.values()}
    overall = "FAIL" if "FAIL" in states else "PENDING" if "PENDING" in states else "PASS"
    return {"figure_id": spec.get("figure_id"), "artifact": str(artifact),
            "overall": overall, "checks": checks,
            "notice": "Structural checks are not a substitute for scientific or actual publication-render inspection"}
