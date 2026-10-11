"""Offline native-object and optional target-render QA for scientific figure handoffs.

The object audit never executes embedded code. Optional LibreOffice rendering
is explicit, requires a trusted local document and is NOT a security sandbox.
An integrity PASS is not a scientific or visual-fidelity PASS.
"""
from __future__ import annotations

import base64
import html
import io
import os
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path
from typing import Any

MAX_ARTIFACT = 45 * 1024 * 1024
MAX_XML = 8 * 1024 * 1024
MAX_TOTAL_XML = 48 * 1024 * 1024
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


class NativeAuditError(ValueError):
    """Unsafe, unsupported or inconsistent native figure source."""


def _regular(path: str | Path, *, limit: int = MAX_ARTIFACT) -> Path:
    target = Path(path).expanduser().absolute()
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise NativeAuditError("Native audit refuses symlinked paths")
    if not target.is_file() or not stat.S_ISREG(target.stat().st_mode):
        raise NativeAuditError("Native artifact must be an existing regular file")
    if target.stat().st_size > limit:
        raise NativeAuditError("Native artifact exceeds size limit")
    return target


def _xml(data: bytes) -> ET.Element:
    if len(data) > MAX_XML or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise NativeAuditError("XML exceeds limit or declares entities")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise NativeAuditError("Malformed native XML") from exc


def _labels(spec: dict) -> list[str]:
    labels = [n["label"] for n in spec.get("nodes", [])]
    labels += [g["label"] for g in spec.get("groups", [])]
    labels += [label["text"] for label in spec.get("labels", [])]
    labels += [edge["label"] for edge in spec.get("edges", []) if edge.get("label")]
    labels += spec.get("constraints", {}).get("required_labels", [])
    return list(dict.fromkeys(labels))


def _text(value: str) -> str:
    # Only normalize whitespace; exact labels, case, numbers and formulas remain locked.
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", value)).split())


def _native_pptx(path: Path) -> dict:
    shapes, connectors, pictures, names, text, shape_ids, edges, node_labels = [], [], 0, [], [], {}, {}, {}
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(e.file_size for e in entries) > MAX_TOTAL_XML * 4:
                raise NativeAuditError("PPTX archive exceeds member/uncompressed size bounds")
            slides = sorted((n for n in entries if re.fullmatch(r"ppt/slides/slide\d+\.xml", n.filename)),
                            key=lambda n: int(re.search(r"slide(\d+)\.xml", n.filename).group(1)))
            if len(slides) != 1:
                raise NativeAuditError("A research figure must be reconstructed on exactly one slide")
            if slides[0].file_size > MAX_XML:
                raise NativeAuditError("Slide XML is too large")
            root = _xml(archive.read(slides[0]))
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise NativeAuditError("Invalid or unsupported PPTX archive") from exc
    for shape in root.iter(P + "sp"):
        cnv = shape.find("./" + P + "nvSpPr/" + P + "cNvPr")
        label = "".join((v.text or "") for v in shape.iter(A + "t"))
        text.append(_text(label))
        if cnv is not None:
            sid, name = cnv.get("id"), cnv.get("name", "")
            names.append(name)
            if name.startswith("rfs-node:"):
                node_id = name[len("rfs-node:"):]
                shape_ids[sid] = node_id
                node_labels[node_id] = _text(label)
        shapes.append({"text": _text(label), "name": cnv.get("name", "") if cnv is not None else ""})
    for connection in root.iter(P + "cxnSp"):
        cnv = connection.find("./" + P + "nvCxnSpPr/" + P + "cNvPr")
        nv = connection.find("./" + P + "nvCxnSpPr/" + P + "cNvCxnSpPr")
        first = nv.find(A + "stCxn") if nv is not None else None
        last = nv.find(A + "endCxn") if nv is not None else None
        # DrawingML a:headEnd is the BEGINNING of the path; a:tailEnd is its END.
        # Checking only for an arrowhead would accept reversed scientific flow.
        arrow = any(item.get("type", "none") != "none" for item in connection.iter(A + "tailEnd"))
        reverse_arrow = any(item.get("type", "none") != "none" for item in connection.iter(A + "headEnd"))
        name = cnv.get("name", "") if cnv is not None else ""
        record = {"name": name, "start": first.get("id") if first is not None else None,
                  "end": last.get("id") if last is not None else None,
                  "arrow": arrow, "reverse_arrow": reverse_arrow}
        connectors.append(record)
        if name.startswith("rfs-edge:"):
            edges[name[len("rfs-edge:"):]] = record
    pictures = len(list(root.iter(P + "pic")))
    return {"format": "pptx", "native_shapes": len(shapes), "native_connectors": len(connectors),
            "raster_pictures": pictures, "native_text": list(filter(None, text)),
            "node_shape_ids": shape_ids, "node_labels": node_labels,
            "edge_records": edges, "source_labels": names}


def _drawio_model(diagram: ET.Element) -> ET.Element:
    model = diagram.find("mxGraphModel")
    if model is not None:
        return model
    packed = (diagram.text or "").strip()
    if not packed or len(packed) > MAX_XML * 2:
        raise NativeAuditError("draw.io diagram has no supported model data")
    try:
        encoded = base64.b64decode(packed, validate=True)
        decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
        unpacked = decompressor.decompress(encoded, MAX_XML + 1)
        if len(unpacked) > MAX_XML or decompressor.unconsumed_tail or not decompressor.eof:
            raise NativeAuditError("Compressed draw.io XML exceeds bound")
        document = urllib.parse.unquote_to_bytes(unpacked)
        return _xml(document)
    except (ValueError, zlib.error, UnicodeError) as exc:
        raise NativeAuditError("Cannot decode compressed draw.io diagram") from exc


def _native_drawio(path: Path) -> dict:
    root = _xml(path.read_bytes())
    if root.tag == "mxGraphModel":
        model = root
    elif root.tag == "mxfile":
        diagrams = root.findall("diagram")
        if len(diagrams) != 1:
            raise NativeAuditError("A research figure must have exactly one draw.io page")
        model = _drawio_model(diagrams[0])
    else:
        raise NativeAuditError("Unsupported draw.io XML root")
    if model.tag != "mxGraphModel":
        raise NativeAuditError("Missing draw.io mxGraphModel")
    shapes, connections, pictures, names, ids, edges, node_labels = [], [], 0, [], {}, {}, {}
    for cell in model.iter("mxCell"):
        cid = cell.get("id", "")
        if cell.get("vertex") == "1":
            label = _text(cell.get("value", ""))
            shapes.append(label)
            names.append(cid)
            if cid.startswith("rfs-node:"):
                node_id = cid[len("rfs-node:"):]
                ids[cid] = node_id
                node_labels[node_id] = label
            style = cell.get("style", "")
            if "shape=image" in style or "image=data:" in style or style.startswith("image;"):
                pictures += 1
        if cell.get("edge") == "1":
            end_arrow = re.search(r"(?:^|;)endArrow=([^;]+)", cell.get("style", ""))
            arrow = end_arrow is not None and end_arrow.group(1) not in {"none", "0"}
            start_arrow = re.search(r"(?:^|;)startArrow=([^;]+)", cell.get("style", ""))
            reverse_arrow = start_arrow is not None and start_arrow.group(1) not in {"none", "0"}
            record = {"name": cid, "start": cell.get("source"), "end": cell.get("target"),
                      "arrow": arrow, "reverse_arrow": reverse_arrow}
            connections.append(record)
            if cid.startswith("rfs-edge:"):
                edges[cid[len("rfs-edge:"):]] = record
    return {"format": "drawio", "native_shapes": len(shapes), "native_connectors": len(connections),
            "raster_pictures": pictures, "native_text": list(filter(None, shapes)),
            "node_shape_ids": ids, "node_labels": node_labels,
            "edge_records": edges, "source_labels": names}


def audit_native(spec: dict[str, Any], artifact: str | Path) -> dict:
    """Audit structural editability of a native source; never claim visual PASS."""
    if spec.get("schema_version") != "1.0.0":
        raise NativeAuditError("Native audit needs the canonical FigureSpec v1")
    path = _regular(artifact)
    kind = path.suffix.lower()
    if kind not in {".pptx", ".drawio", ".xml"}:
        raise NativeAuditError("Only PPTX and draw.io XML native files are supported")
    record = _native_pptx(path) if kind == ".pptx" else _native_drawio(path)
    expected_nodes = spec.get("nodes", [])
    expected_edges = spec.get("edges", [])
    available = set(record["native_text"])
    missing = [label for label in _labels(spec) if _text(label) not in available]
    failed = []
    if missing:
        failed.append("Native editable labels are missing or not exact")
    if record["native_shapes"] < len(expected_nodes):
        failed.append("Fewer native objects than scientific nodes")
    if record["native_connectors"] < len(expected_edges):
        failed.append("Fewer native connectors than scientific edges")
    if record["raster_pictures"] and record["native_shapes"] <= record["raster_pictures"]:
        failed.append("Native figure appears flattened or dominated by pictures")
    tagged_shapes = set(record["node_shape_ids"].values())
    for node in expected_nodes:
        if node["id"] in record["node_labels"] and record["node_labels"][node["id"]] != _text(node["label"]):
            failed.append("Tagged node label mismatch: " + node["id"])
    expected_ids = {node["id"] for node in expected_nodes}
    extra_shapes = tagged_shapes - expected_ids
    if extra_shapes:
        failed.append("Native source contains invalid scientific node tags")
    tagged_edges = record["edge_records"]
    required_edge_ids = {edge["id"] for edge in expected_edges}
    if set(tagged_edges) - required_edge_ids:
        failed.append("Native source contains unexpected scientific edge tags")
    for edge in expected_edges:
        if edge["id"] not in tagged_edges:
            continue
        actual = tagged_edges[edge["id"]]
        source = record["node_shape_ids"].get(actual["start"])
        target = record["node_shape_ids"].get(actual["end"])
        if source != edge["source"] or target != edge["target"]:
            failed.append("Tagged connector endpoint mismatch: " + edge["id"])
        if edge.get("directed"):
            if not actual["arrow"] or actual["reverse_arrow"]:
                failed.append("Tagged connector arrow direction is wrong or ambiguous: " + edge["id"])
        elif actual["arrow"] or actual["reverse_arrow"]:
            failed.append("Tagged undirected connector has unexpected arrowhead: " + edge["id"])
    tagged_coverage = (tagged_shapes == expected_ids and set(tagged_edges) == required_edge_ids)
    structural = "FAIL" if failed else "PASS" if tagged_coverage else "PENDING_UNTAGGED_OBJECTS"
    report = {"format": record["format"], "artifact": str(path),
              "native_shape_count": record["native_shapes"],
              "native_connector_count": record["native_connectors"],
              "raster_picture_count": record["raster_pictures"],
              "scientific_node_count": len(expected_nodes), "scientific_edge_count": len(expected_edges),
              "missing_native_labels": missing, "structure_check": structural,
              "object_tags_complete": tagged_coverage,
              "failures": failed, "native_source_editable_elements": bool(record["native_shapes"]),
              "target_render": "NOT_RUN", "reference_comparison": "PENDING",
              "scientific_semantics": "PENDING_HUMAN_REVIEW",
              "status": "FAIL" if failed else "STRUCTURE_CHECK_PASSED_VISUAL_REVIEW_PENDING" if tagged_coverage else "PENDING_OBJECT_MAPPING_AND_VISUAL_REVIEW"}
    return report


def render_pptx(path: str | Path, *, save_png: str | Path | None = None, timeout: int = 90) -> bytes:
    """Render saved PPTX through LibreOffice, then PyMuPDF. Requires trusted input.

    Running a desktop importer on malicious documents is NOT sandboxing. This
    operation is opt-in; use disposable environments for untrusted sources.
    """
    native = _regular(path)
    if native.suffix.lower() != ".pptx":
        raise NativeAuditError("Automatic native rendering currently supports PPTX only")
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        raise NativeAuditError("LibreOffice is unavailable; target rendering remains pending")
    try:
        import fitz
    except ImportError as exc:
        raise NativeAuditError("Install PyMuPDF to inspect native PPTX render output") from exc
    with tempfile.TemporaryDirectory(prefix="rfs-native-qa-") as tmp:
        working = Path(tmp)
        copy = working / "source.pptx"
        shutil.copyfile(native, copy)
        command = [executable, "-env:UserInstallation=" + (working / "lo-profile").as_uri(),
                   "--headless", "--convert-to", "pdf", "--outdir", str(working), str(copy)]
        try:
            res = subprocess.run(command, cwd=working, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise NativeAuditError("LibreOffice target rendering timed out") from exc
        pdf = working / "source.pdf"
        if res.returncode or not pdf.is_file():
            raise NativeAuditError("LibreOffice could not render saved PPTX")
        with fitz.open(pdf) as doc:
            if len(doc) != 1:
                raise NativeAuditError("Native figure must render to one page")
            image = doc[0].get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            raw = image.tobytes("png")
        if save_png is not None:
            output = Path(save_png).expanduser().absolute()
            if output.exists():
                raise NativeAuditError("Refusing to overwrite existing native render")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(raw)
        return raw


def compare_reference(reference: str | Path, rendered_png: bytes) -> dict:
    """Diagnostic pixel difference only; never certifies semantic/visual quality."""
    from PIL import Image, ImageChops, ImageOps, ImageStat
    ref = _regular(reference)
    try:
        with Image.open(ref) as source:
            source.load()
            desired = ImageOps.pad(source.convert("RGB"), (512, 288), color="white")
        with Image.open(io.BytesIO(rendered_png)) as target:
            target.load()
            observed = ImageOps.pad(target.convert("RGB"), (512, 288), color="white")
    except (OSError, ValueError) as exc:
        raise NativeAuditError("Cannot decode comparison images") from exc
    difference = ImageStat.Stat(ImageChops.difference(desired, observed)).mean
    score = round(sum(difference) / (3 * 255), 5)
    return {"normalized_mean_absolute_pixel_difference": score,
            "interpretation": "DIAGNOSTIC_ONLY_NOT_HIGH_FIDELITY_PROOF",
            "alignment": "Images letterboxed to 512x288; font/render differences can affect this score"}
