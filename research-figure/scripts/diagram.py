"""Dependency-free deterministic diagram renderer (SVG text and paths stay editable)."""
from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path

from core import RFSValidationError, diagram_layers, load_style


def _txt(s: object) -> str:
    return escape(str(s), quote=False)


def _attr(s: object) -> str:
    return escape(str(s), quote=True)


def render_diagram(spec: dict, output_path: str | Path) -> dict:
    if spec.get("type") != "architecture":
        raise RFSValidationError("Native SVG diagram renderer only supports architecture type")
    nodes = spec["diagram"]["nodes"]
    edges = spec["diagram"]["edges"]
    levels = diagram_layers(nodes, edges)
    groups: dict[int, list[dict]] = defaultdict(list)
    for node in nodes:
        groups[levels[node["id"]]].append(node)
    w = int(spec.get("target", {}).get("width_px", 1560))
    h = int(spec.get("target", {}).get("height_px", 760))
    style = load_style(spec)
    num_layers = max(1, max(levels.values(), default=0) + 1)
    margin_x = 78
    margin_top = 155
    margin_bottom = 140
    card_h = 104
    if num_layers > 1:
        card_w = min(246, max(140, int((w - margin_x * 2 - (num_layers - 1) * 70) / num_layers)))
        step_x = (w - 2 * margin_x - card_w) / (num_layers - 1)
    else:
        card_w = min(290, w - 2 * margin_x)
        step_x = 0
    positions: dict[str, tuple[float, float]] = {}
    drawable_h = max(120, h - margin_top - margin_bottom)
    for col in range(num_layers):
        group = groups.get(col, [])
        for row_idx, node in enumerate(group):
            x = margin_x + col * step_x
            cy = margin_top + (row_idx + 1) * drawable_h / (len(group) + 1)
            positions[node["id"]] = (x, cy - card_h / 2)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">',
        '<title>' + _txt(spec["title"]) + '</title>',
        '<desc>Exact nodes and directed links from FigureSpec; draft science must be reviewed separately.</desc>',
        f'<rect width="100%" height="100%" fill="{style["background"]}"/>',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth">',
        f'<path d="M 0 1 L 8 4.5 L 0 8 Z" fill="{style["stroke"]}"/></marker></defs>',
        f'<text x="{w/2:.1f}" y="70" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="28" font-weight="700" fill="{style["text"]}">{_txt(spec["title"])}</text>',
    ]
    # Draw edges before cards so nodes remain visually on top.
    edge_count = 0
    for i, e in enumerate(edges):
        src_x, src_y = positions[e["source"]]
        dst_x, dst_y = positions[e["target"]]
        src_cy = src_y + card_h / 2
        dst_cy = dst_y + card_h / 2
        eid = f'{e["source"]}__{e["target"]}__{i}'
        feedback = bool(e.get("feedback"))
        if feedback:
            bottom = h - 102 - (i % 3) * 15
            x1, x2 = src_x + card_w / 2, dst_x + card_w / 2
            d = f'M {x1:.1f} {src_y+card_h:.1f} L {x1:.1f} {bottom:.1f} L {x2:.1f} {bottom:.1f} L {x2:.1f} {dst_y+card_h+2:.1f}'
        else:
            x1, x2 = src_x + card_w, dst_x
            if x2 - x1 > 35:
                xm = (x1 + x2) / 2
                d = f'M {x1:.1f} {src_cy:.1f} L {xm:.1f} {src_cy:.1f} L {xm:.1f} {dst_cy:.1f} L {x2-4:.1f} {dst_cy:.1f}'
            else:
                # Same-layer or long-distance edges are deliberately routed with
                # a dogleg; publication fit remains subject to visual review.
                lane = min(src_y, dst_y) - 20 - (i % 4) * 14
                d = f'M {x1:.1f} {src_cy:.1f} L {x1+16:.1f} {src_cy:.1f} L {x1+16:.1f} {lane:.1f} L {x2-18:.1f} {lane:.1f} L {x2-18:.1f} {dst_cy:.1f} L {x2-4:.1f} {dst_cy:.1f}'
        dash = ' stroke-dasharray="7 5"' if feedback else ''
        out.append(f'<path data-rfs-edge-id="{_attr(eid)}" d="{d}" fill="none" '
                   f'stroke="{style["stroke"]}" stroke-width="2.5" marker-end="url(#arrow)"{dash}/>')
        if e.get("label"):
            mx = (src_x + dst_x + card_w) / 2
            my = min(src_cy, dst_cy) - 13 if not feedback else h-116
            out.append(f'<text x="{mx:.1f}" y="{my:.1f}" text-anchor="middle" '
                       f'font-size="14" font-family="DejaVu Sans, Arial, sans-serif" '
                       f'fill="{style["secondary_text"]}">{_txt(e["label"])}</text>')
        edge_count += 1
    for node in nodes:
        x, y = positions[node["id"]]
        accent = bool(node.get("emphasis"))
        fill = style["accent_fill"] if accent else style["node_fill"]
        border = style["accent_border"] if accent else style["node_border"]
        out.append(f'<g data-rfs-node-id="{_attr(node["id"])}">')
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{card_w:.1f}" height="{card_h}" '
                   f'rx="14" ry="14" fill="{fill}" stroke="{border}" stroke-width="2"/>')
        label_lines = str(node["label"]).split("\n")
        line_h = 24
        y0 = y + card_h/2 - (len(label_lines)-1) * line_h/2 + 7
        out.append(f'<text x="{x+card_w/2:.1f}" y="{y0:.1f}" text-anchor="middle" '
                   f'font-family="DejaVu Sans, Arial, sans-serif" font-size="19" font-weight="600" fill="{style["text"]}">')
        for li, line in enumerate(label_lines):
            dy = "0" if li == 0 else str(line_h)
            out.append(f'<tspan x="{x+card_w/2:.1f}" dy="{dy}">{_txt(line)}</tspan>')
        out.append('</text></g>')
    evidences = spec.get("evidence", [])
    if spec.get("style", {}).get("demo"):
        note = "DEMO / ILLUSTRATIVE FIGURE — NOT RESEARCH EVIDENCE"
    elif any(e.get("status") != "verified" for e in evidences) or not evidences:
        note = "DRAFT — SCIENTIFIC STRUCTURE PENDING REVIEW"
    else:
        note = "SCIENTIFIC INTERPRETATION REQUIRES SOURCE REVIEW"
    out.append(f'<text x="{w/2:.1f}" y="{h-39}" text-anchor="middle" font-size="15" '
               f'font-family="DejaVu Sans, Arial, sans-serif" fill="{style["highlight"]}">{_txt(note)}</text>')
    out.append('</svg>')
    result_path = Path(output_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text('\n'.join(out)+'\n', encoding='utf-8')
    return {"engine": "native-svg", "artifacts": [str(result_path.resolve())],
            "diagram_nodes": len(nodes), "diagram_edges": edge_count,
            "known_limitations": ["Layout is heuristic; inspect at target publication size", "Scientific interpretation requires manual review"]}
