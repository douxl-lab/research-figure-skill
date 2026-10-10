"""FigureSpec parsing and conservative, standard-library-only validation.

All evidence and scientific interpretation remain pending unless substantiated.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
HERE = Path(__file__).resolve().parent.parent
ASSETS = HERE / "assets"
ALLOWED_TYPES = {"architecture", "quantitative", "editable_reconstruction", "evidence_panel"}
ALLOWED_EVIDENCE_STATES = {"verified", "pending", "illustrative"}
ALLOWED_EVIDENCE_KINDS = {"method", "code", "data", "reference", "hypothesis"}
_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class RFSValidationError(ValueError):
    """User-facing input, dependency, or semantic validation failure."""


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RFSValidationError(f"Could not read valid JSON from {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise RFSValidationError("FigureSpec root must be a JSON object")
    return data


def hash_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_source(spec_path: str | Path, raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path(spec_path).expanduser().resolve().parent / p
    return p.resolve()


def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def load_style(spec: dict[str, Any]) -> dict[str, Any]:
    theme = spec.get("style", {}).get("theme", "academic-clean")
    if not isinstance(theme, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", theme):
        raise RFSValidationError("style.theme must be a safe lowercase kebab-case identifier")
    path = ASSETS / f"style-{theme}.json"
    if not path.is_file():
        raise RFSValidationError(f"Unsupported style theme {theme!r}; add a matching assets/style-*.json preset")
    theme_data = read_json(path)
    required = ("background", "text", "secondary_text", "stroke", "node_fill", "node_border", "accent_fill", "accent_border", "highlight", "palette")
    if not all(k in theme_data for k in required) or not isinstance(theme_data["palette"], list) or not theme_data["palette"]:
        raise RFSValidationError(f"Style preset is incomplete: {path}")
    return theme_data


def diagram_layers(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """Longest-path topological layering; feedback edges excluded explicitly."""
    ids = [n["id"] for n in nodes]
    parents = {name: 0 for name in ids}
    neighbors: dict[str, list[str]] = {name: [] for name in ids}
    for e in edges:
        if e.get("feedback"):
            continue
        src, dst = e["source"], e["target"]
        neighbors[src].append(dst)
        parents[dst] += 1
    queue = [i for i in ids if parents[i] == 0]
    depths = {i: 0 for i in ids}
    processed = 0
    while queue:
        node = queue.pop(0)
        processed += 1
        for nxt in neighbors[node]:
            depths[nxt] = max(depths[nxt], depths[node] + 1)
            parents[nxt] -= 1
            if parents[nxt] == 0:
                queue.append(nxt)
    if processed != len(ids):
        raise RFSValidationError("Directed cycle found. Mark intended backward/feedback edges with feedback=true")
    return depths


def read_plot_rows(spec: dict[str, Any], spec_path: str | Path) -> list[dict[str, Any]]:
    cfg = spec["plot"]
    path = resolve_source(spec_path, cfg["data_file"])
    if not path.is_file():
        raise RFSValidationError(f"Plot CSV does not exist: {path}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            expected = [cfg["x"], cfg["y"]]
            if cfg.get("series"):
                expected.append(cfg["series"])
            fields = reader.fieldnames or []
            missing = [col for col in expected if col not in fields]
            if missing:
                raise RFSValidationError(f"CSV missing columns {missing}; found {fields}")
            data = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise RFSValidationError(f"Could not parse CSV: {exc}") from exc
    if not data:
        raise RFSValidationError("Plot CSV is empty")
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    for row_no, row in enumerate(data, start=2):
        x_raw = (row.get(cfg["x"]) or "").strip()
        y_raw = (row.get(cfg["y"]) or "").strip()
        series = ((row.get(cfg.get("series")) or "").strip() if cfg.get("series") else "single")
        if not x_raw or not series:
            raise RFSValidationError(f"CSV row {row_no}: x or series is blank")
        try:
            y = float(y_raw)
            if not math.isfinite(y):
                raise ValueError("non-finite y")
        except (TypeError, ValueError) as exc:
            raise RFSValidationError(f"CSV row {row_no}: invalid finite numerical y={y_raw!r}") from exc
        if cfg["kind"] in ("line", "scatter"):
            try:
                x = float(x_raw)
                if not math.isfinite(x):
                    raise ValueError("non-finite x")
            except (TypeError, ValueError) as exc:
                raise RFSValidationError(f"CSV row {row_no}: x must be a finite number for {cfg['kind']}") from exc
            x_key = str(x)
        else:
            x = x_raw
            x_key = x_raw
        # Scatter plots can legitimately have repeated x coordinates.
        if cfg["kind"] != "scatter":
            pair = (series, x_key)
            if pair in seen:
                raise RFSValidationError(f"CSV row {row_no}: repeated x={x_raw!r} in series={series!r}; aggregate explicitly upstream")
            seen.add(pair)
        rows.append({"x": x, "y": y, "series": series})
    if cfg["kind"] == "bar":
        categories = sorted({str(r["x"]) for r in rows})
        groups = sorted({r["series"] for r in rows})
        # Missing values in bar groups are not silently treated as zero.
        missing_pairs = [(g, x) for g in groups for x in categories
                         if (g, x) not in {(r["series"], str(r["x"])) for r in rows}]
        if missing_pairs:
            raise RFSValidationError(f"Incomplete grouped bar grid (not imputed): {missing_pairs[:8]}")
    return rows


def validate_spec(spec: dict[str, Any], spec_path: str | Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    spec_file = Path(spec_path).expanduser().resolve()
    for field in ("schema_version", "figure_id", "type", "title", "scientific_claim"):
        if not _nonempty_str(spec.get(field)):
            errors.append(f"Missing nonempty field: {field}")
    if spec.get("schema_version") != VERSION:
        errors.append(f"Unsupported schema_version; required {VERSION}")
    if spec.get("type") not in ALLOWED_TYPES:
        errors.append(f"Unknown type: {spec.get('type')!r}")
    if not _ID.fullmatch(str(spec.get("figure_id", ""))):
        errors.append("figure_id must contain only letters, numbers, underscore and hyphen")
    evidence = spec.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")
        evidence = []
    evidence_ids: set[str] = set()
    verified_count = 0
    for i, e in enumerate(evidence):
        if not isinstance(e, dict):
            errors.append(f"evidence[{i}] must be an object")
            continue
        evid = e.get("id")
        if not _nonempty_str(evid) or evid in evidence_ids:
            errors.append(f"evidence[{i}] requires unique nonempty id")
        else:
            evidence_ids.add(evid)
        if e.get("status") not in ALLOWED_EVIDENCE_STATES:
            errors.append(f"evidence[{i}] has invalid status")
        if e.get("kind") not in ALLOWED_EVIDENCE_KINDS:
            errors.append(f"evidence[{i}] has invalid kind")
        if e.get("status") == "verified":
            verified_count += 1
            if not e.get("path"):
                warnings.append(f"evidence[{i}]: manually marked verified without a linked local source")
        if e.get("path"):
            source_path = resolve_source(spec_file, str(e["path"]))
            if not source_path.is_file():
                errors.append(f"evidence[{i}] source missing: {source_path}")
            elif e.get("sha256"):
                digest = hash_file(source_path)
                if digest.lower() != str(e["sha256"]).lower():
                    errors.append(f"evidence[{i}] source SHA256 mismatch: {source_path}")
        elif e.get("sha256"):
            errors.append(f"evidence[{i}] sha256 requires path")
    if not evidence:
        warnings.append("No evidence ledger: scientific interpretation must remain pending")
    if verified_count == 0:
        warnings.append("No manually verified evidence; scientific interpretation remains PENDING")
    style = spec.get("style", {})
    if not isinstance(style, dict):
        errors.append("style must be an object")
        style = {}
    if isinstance(style, dict):
        try:
            load_style(spec)
        except RFSValidationError as exc:
            errors.append(str(exc))
    if style.get("demo") is not True and any(e.get("status") == "illustrative" for e in evidence if isinstance(e, dict)):
        errors.append("Illustrative evidence requires style.demo=true for visible watermarking")
    generation = spec.get("generation", {})
    if not isinstance(generation, dict):
        errors.append("generation must be an object")
        generation = {}
    if generation.get("intent", "creative") not in {"exact", "creative"}:
        errors.append("generation.intent must be exact or creative")
    if spec.get("type") != "architecture" and generation.get("intent") == "creative":
        errors.append("generation.intent=creative is only supported for architecture diagrams")
    if generation.get("archetype", "overview") not in {"overview", "architecture", "mechanism"}:
        errors.append("generation.archetype must be overview, architecture or mechanism")
    design = spec.get("design", {})
    if not isinstance(design, dict):
        errors.append("design must be an object")
    else:
        for key in ("visual_priority",):
            if key in design and not _nonempty_str(design[key]):
                errors.append(f"design.{key} must be nonempty text")
        if design.get("reading_path", "left_to_right") not in {"left_to_right", "top_to_bottom", "radial", "hierarchical"}:
            errors.append("design.reading_path must be left_to_right, top_to_bottom, radial, or hierarchical")
        for key in ("layout_notes", "text_notes", "connector_notes", "asset_notes", "avoid"):
            values = design.get(key, [])
            if not isinstance(values, list) or len(values) > 32 or any(not _nonempty_str(x) for x in values):
                errors.append(f"design.{key} must be a list of up to 32 nonempty text entries")
    target = spec.get("target", {})
    if not isinstance(target, dict):
        errors.append("target must be an object")
        target = {}
    for field, minimum, maximum in (("width_px", 500, 8000), ("height_px", 300, 8000)):
        if field in target and (type(target[field]) is not int or not minimum <= target[field] <= maximum):
            errors.append(f"target.{field} must be an integer in [{minimum},{maximum}]")
    if "publication_width_mm" in target:
        v = target["publication_width_mm"]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
            errors.append("target.publication_width_mm must be a positive finite number")
    type_name = spec.get("type")
    if type_name == "architecture":
        diagram = spec.get("diagram")
        if not isinstance(diagram, dict):
            errors.append("architecture requires diagram object")
        else:
            nodes, edges = diagram.get("nodes"), diagram.get("edges")
            if not isinstance(nodes, list) or not nodes:
                errors.append("architecture requires nonempty diagram.nodes")
                nodes = []
            if not isinstance(edges, list):
                errors.append("architecture requires diagram.edges array")
                edges = []
            names: set[str] = set()
            for i, n in enumerate(nodes):
                if not isinstance(n, dict):
                    errors.append(f"node[{i}] must be an object")
                    continue
                name = n.get("id")
                if not _nonempty_str(name) or name in names or not _ID.fullmatch(str(name)):
                    errors.append(f"node[{i}] invalid or duplicate id")
                else:
                    names.add(name)
                if not _nonempty_str(n.get("label")):
                    errors.append(f"node[{i}] missing label")
                if "emphasis" in n and type(n["emphasis"]) is not bool:
                    errors.append(f"node[{i}].emphasis must be a boolean")
                _validate_refs(n, f"node[{i}]", evidence_ids, errors, warnings)
            for i, e in enumerate(edges):
                if not isinstance(e, dict):
                    errors.append(f"edge[{i}] must be an object")
                    continue
                if e.get("source") not in names or e.get("target") not in names:
                    errors.append(f"edge[{i}] references missing source/target node")
                if "feedback" in e and type(e["feedback"]) is not bool:
                    errors.append(f"edge[{i}].feedback must be a boolean")
                _validate_refs(e, f"edge[{i}]", evidence_ids, errors, warnings)
            if not errors:
                try:
                    diagram_layers(nodes, edges)
                except RFSValidationError as exc:
                    errors.append(str(exc))
            if len(nodes) > 16:
                warnings.append("Native SVG renderer is deliberately simple; >16 nodes need manual layout review")
    if type_name == "quantitative":
        plot = spec.get("plot")
        if not isinstance(plot, dict):
            errors.append("quantitative requires plot object")
        else:
            for key in ("data_file", "x", "y"):
                if not _nonempty_str(plot.get(key)):
                    errors.append(f"plot.{key} is required")
            if plot.get("kind") not in {"bar", "line", "scatter"}:
                errors.append("plot.kind must be bar, line, or scatter")
            if not errors:
                try:
                    read_plot_rows(spec, spec_file)
                except RFSValidationError as exc:
                    errors.append(str(exc))
            data_path = plot.get("data_file")
            if isinstance(data_path, str) and not any(e.get("path") and resolve_source(spec_file, e["path"]) == resolve_source(spec_file, data_path) for e in evidence if isinstance(e, dict)):
                warnings.append("CSV plot source lacks a matching evidence ledger path")
    if type_name in {"evidence_panel", "editable_reconstruction"}:
        warnings.append("This figure type requires a host-side editable/image assembly backend; CLI can generate a handoff only")
    delivery = spec.get("delivery", {})
    if not isinstance(delivery, dict):
        errors.append("delivery must be an object")
    else:
        formats = delivery.get("formats", [])
        valid_formats = {"svg", "pdf", "png", "pptx", "drawio"}
        if not isinstance(formats, list) or any(not isinstance(f, str) or f not in valid_formats for f in formats):
            errors.append("delivery.formats must be an array of supported formats")
        elif len(formats) != len(set(formats)):
            errors.append("delivery.formats must not contain duplicates")
        if "editable" in delivery and type(delivery["editable"]) is not bool:
            errors.append("delivery.editable must be a boolean")
        if isinstance(formats, list) and ("pptx" in formats or "drawio" in formats):
            warnings.append("Native PPTX/draw.io requested: host-side editable creation is a separate step")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "scientific_interpretation": "PENDING", "schema_version": VERSION}


def _validate_refs(obj: dict, name: str, evidence_ids: set[str], errors: list[str], warnings: list[str]) -> None:
    refs = obj.get("evidence_refs", [])
    if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
        errors.append(f"{name}.evidence_refs must be a string array")
        return
    for ref in refs:
        if ref not in evidence_ids:
            errors.append(f"{name} references missing evidence id={ref}")
    if not refs:
        warnings.append(f"{name} has no explicit evidence reference")


def load_and_validate(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = read_json(path)
    report = validate_spec(spec, path)
    return spec, report


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
