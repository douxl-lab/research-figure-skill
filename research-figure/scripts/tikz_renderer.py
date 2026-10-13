"""Deterministic, source-preserving TikZ backend for canonical FigureSpec v1.

This local renderer does NOT run a scientific reviewer or PaperBanana's agents.
Only validated semantic nodes, labels and edges enter the generated TeX.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict, deque
from pathlib import Path

MAX_NODES = 64
MAX_EDGES = 160
SAFE_MATH = frozenset("frac sqrt sum prod int lim text mathrm mathit mathbf mathbb mathcal boldsymbol operatorname left right cdot times to rightarrow leftarrow leftrightarrow le leq ge geq neq approx sim in notin subset subseteq max min argmax argmin log exp sin cos tan alpha beta gamma delta theta lambda mu nu xi pi rho sigma tau phi psi omega Gamma Delta Theta Lambda Sigma Phi Omega partial nabla forall exists cup cap land lor neg overline hat tilde bar underbrace overbrace infinity infty pm mp dots ldots cdots vert Vert mid".split())
TEX_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def escape_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 400:
        raise ValueError("TikZ requires a nonempty label of at most 400 characters")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise ValueError("TikZ label contains control characters")
    return "".join(TEX_SPECIAL.get(ch, ch) for ch in value.replace("\n", " ").replace("\t", " "))


def safe_formula(value: str) -> str:
    """Allow a limited LaTeX math vocabulary; reject arbitrary TeX execution."""
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError("Formula is empty or exceeds TikZ math safety limit")
    if any(ord(ch) < 32 for ch in value) or "$" in value or "%" in value or "#" in value or "~" in value:
        raise ValueError("Formula has unsupported TeX characters")
    commands = re.findall(r"\\([A-Za-z@]+|.)", value)
    if any(command not in SAFE_MATH and command not in ("{", "}", "_", "^", " ", ",", ";", ":", "!", "|", "\\") for command in commands):
        raise ValueError("Formula includes unsupported LaTeX macro; no raw TeX is executed")
    # Only math syntax, Unicode letters, brackets and a whitelisted command vocabulary.
    if re.search(r"(?<!\\)[&]", value) or re.search(r"\\(?:begin|end|input|include|write|def|catcode|csname)", value):
        raise ValueError("Unsupported TeX control syntax")
    if value.count("{") != value.count("}"):
        raise ValueError("Unbalanced formula braces")
    return value


def layout(spec: dict) -> tuple[dict[str, tuple[float, float]], list[str]]:
    nodes = spec["nodes"]
    names = [node["id"] for node in nodes]
    if not 1 <= len(names) <= MAX_NODES or len(spec["edges"]) > MAX_EDGES:
        raise ValueError("TikZ backend supports 1-64 nodes and at most 160 edges")
    indegree = {name: 0 for name in names}
    next_nodes: dict[str, list[str]] = defaultdict(list)
    for edge in spec["edges"]:
        if edge["directed"] and edge["source"] != edge["target"]:
            next_nodes[edge["source"]].append(edge["target"])
            indegree[edge["target"]] += 1
    queue = deque(name for name in names if not indegree[name])
    rank = {name: 0 for name in names}
    visited = set()
    while queue:
        source = queue.popleft()
        visited.add(source)
        for dest in next_nodes[source]:
            rank[dest] = max(rank[dest], rank[source] + 1)
            indegree[dest] -= 1
            if indegree[dest] == 0:
                queue.append(dest)
    warnings = []
    if len(visited) != len(names):
        warnings.append("Directed cycles detected; remaining nodes use a stable fallback column. Review arrow routing.")
        remaining_col = max(rank[x] for x in visited) + 1 if visited else 0
        for name in names:
            if name not in visited:
                rank[name] = remaining_col
    # A long chain creates a wide diagram; cap size rather than silently drop nodes.
    if max(rank.values()) >= 13:
        warnings.append("Wide graph (14+ layers): inspect publication-size legibility")
    columns: dict[int, list[str]] = defaultdict(list)
    for name in names:
        columns[rank[name]].append(name)
    xy = {}
    for col, members in columns.items():
        for row, name in enumerate(members):
            xy[name] = (col * 4.7, (len(members) - 1 - 2 * row) * 1.35)
    return xy, warnings


def make_tex(spec: dict) -> tuple[str, list[str]]:
    if spec.get("schema_version") != "1.0.0" or spec.get("kind") != "diagram":
        raise ValueError("TikZ supports canonical FigureSpec v1 diagrams only")
    xy, warnings = layout(spec)
    names = {node["id"]: f"n{i}" for i, node in enumerate(spec["nodes"])}
    captions = defaultdict(list)
    for label in spec["labels"]:
        if not label["target_ids"]:
            raise ValueError(f"Label {label['id']} has no target; cannot safely position")
        for target in label["target_ids"]:
            captions[target].append(escape_text(label["text"]))
    raw_palette = spec["design"]["palette"]
    palette = [c[1:].upper() for c in raw_palette[:4]]
    if not palette or any(not re.fullmatch(r"[0-9A-F]{6}", c) for c in palette):
        raise ValueError("TikZ palette must contain #RRGGBB colors")
    while len(palette) < 3:
        palette.append(palette[0])
    lines = [
        r"\documentclass[tikz,border=10pt]{standalone}",
        r"\usepackage{fontspec}",
        r"\usepackage{amsmath,amssymb}",
        r"\usepackage{tikz}",
        r"\usetikzlibrary{arrows.meta,positioning,fit,backgrounds}",
        r"\IfFontExistsTF{Noto Sans CJK SC}{\setmainfont{Noto Sans CJK SC}}{\setmainfont{TeX Gyre Heros}}",
        *[rf"\definecolor{{rfs{i}}}{{HTML}}{{{color}}}" for i, color in enumerate(palette[:3])],
        r"\pgfdeclarelayer{rfsbackground}", r"\pgfsetlayers{rfsbackground,main}",
        r"\tikzset{rfsnode/.style={draw=rfs0!75!black,fill=rfs0!7,rounded corners=3pt,line width=.75pt,align=center,text width=3.0cm,inner sep=7pt,minimum height=1.1cm,font=\small},rfselabel/.style={font=\scriptsize,fill=white,inner sep=2pt,text=black}}",
        r"\begin{document}", r"\begin{tikzpicture}[>=Stealth,line join=round]",
    ]
    for node in spec["nodes"]:
        x, y = xy[node["id"]]
        color = sum(map(ord, node["kind"])) % 3
        label = escape_text(node["label"])
        if node.get("formula"):
            label += r"\\[3pt]{\footnotesize $" + safe_formula(node["formula"]) + r"$}"
        lines.append(rf"\node[rfsnode,draw=rfs{color}!75!black,fill=rfs{color}!7] ({names[node['id']]}) at ({x:.2f},{y:.2f}) {{{label}}};")
    for i, group in enumerate(spec["groups"]):
        members = "".join(f"({names[name]})" for name in group["node_ids"])
        name = f"g{i}"
        title = escape_text(group["label"])
        lines.append(r"\begin{pgfonlayer}{rfsbackground}")
        lines.append(rf"\node[draw=rfs1!65,dashed,fill=rfs1!3,rounded corners=6pt,fit={members},inner sep=12pt] ({name}) {{}};")
        lines.append(r"\end{pgfonlayer}")
        lines.append(rf"\node[font=\scriptsize,anchor=south west,text=rfs1!65!black] at ({name}.north west) {{{title}}};")
        for text in captions.pop(group["id"], []):
            lines.append(rf"\node[font=\scriptsize,anchor=north west] at ({name}.south west) {{{text}}};")
    for edge in spec["edges"]:
        source, target = names[edge["source"]], names[edge["target"]]
        sx, _ = xy[edge["source"]]
        tx, _ = xy[edge["target"]]
        arrow = "-{Stealth[length=2.3mm]}" if edge["directed"] else "-"
        label = " | ".join([*([escape_text(edge["label"])] if edge.get("label") else []), *captions.pop(edge["id"], [])])
        midway = rf" node[midway,rfselabel] {{{label}}}" if label else ""
        if source == target:
            path = f"({source}) to[out=55,in=125,looseness=7]"
            lines.append(rf"\draw[{arrow},line width=.65pt,draw=rfs0!80!black] {path}{midway} ({target});")
        elif tx > sx:
            bend = "" if tx - sx < 5 else "rounded corners=3pt,"
            lines.append(rf"\draw[{arrow},{bend}line width=.65pt,draw=rfs0!80!black] ({source}.east) --{midway} ({target}.west);")
        else:
            lines.append(rf"\draw[{arrow},line width=.65pt,draw=rfs2!85!black,dashed] ({source}.north) to[out=75,in=105] {midway} ({target}.north);")
    for node_id, texts in list(captions.items()):
        if node_id not in names:
            raise ValueError(f"Unmapped label target: {node_id}")
        for offset, text in enumerate(texts):
            lines.append(rf"\node[font=\scriptsize,anchor=north] at ([yshift={-5 - offset * 10}pt]{names[node_id]}.south) {{{text}}};")
    lines.extend([r"\end{tikzpicture}", r"\end{document}", ""])
    return "\n".join(lines), warnings


def _run(args: list[str], cwd: Path, timeout: int, env: dict | None = None) -> None:
    try:
        completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                                   timeout=timeout, check=False, env=env)
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"TikZ tool timed out: {Path(args[0]).name}") from exc
    if completed.returncode != 0:
        raise ValueError(f"TikZ tool failed: {Path(args[0]).name}: {(completed.stdout + completed.stderr)[-1800:]}")


def render_tikz(spec: dict, output: str | Path, *, timeout: int = 45) -> dict:
    """Produce .tex, vector PDF/SVG and raster preview; publish atomically."""
    from protocol import contract  # imported inside RFS installed package
    validated = contract.validate_figure_spec(spec)
    tex, warnings = make_tex(validated)
    if shutil.which("xelatex") is None:
        raise ValueError("TikZ backend requires XeLaTeX (xelatex)")
    if shutil.which("pdftocairo") is None:
        raise ValueError("TikZ backend requires pdftocairo for SVG and PNG previews")
    destination = Path(output).expanduser().resolve()
    if destination.exists():
        raise ValueError("TikZ output directory already exists; choose a fresh path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rfs-tikz-", dir=destination.parent) as temp:
        directory = Path(temp)
        (directory / "figure.tex").write_text(tex, encoding="utf-8")
        env = os.environ.copy()
        env.update({"openin_any": "p", "openout_any": "p", "HOME": str(directory), "TEXMFOUTPUT": str(directory)})
        _run(["xelatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "figure.tex"], directory, timeout, env)
        _run(["pdftocairo", "-svg", "figure.pdf", "figure.svg"], directory, timeout)
        _run(["pdftocairo", "-f", "1", "-l", "1", "-singlefile", "-r", "200", "-png", "figure.pdf", "figure"], directory, timeout)
        (directory / "figure-spec.json").write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        deliverables = ["figure.tex", "figure.pdf", "figure.svg", "figure.png", "figure-spec.json"]
        if not all((directory / name).is_file() and (directory / name).stat().st_size > 0 for name in deliverables):
            raise ValueError("TikZ renderer did not produce all required artifacts")
        hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in deliverables}
        manifest = {"format": "rfs-tikz/1.0", "status": "ARTIFACT_CREATED_SCIENCE_REVIEW_PENDING",
                    "engine": "tikz", "figure_id": validated["figure_id"],
                    "scientific_fingerprint": contract.scientific_fingerprint(validated),
                    "sha256": hashes, "warnings": warnings,
                    "verification": {"compilation": "PASS", "scientific_correctness": "PENDING", "layout_qa": "PENDING", "powerpoint_editability": "NOT_CLAIMED"}}
        (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Do not expose TeX aux/log files; keep only the requested outputs and receipts.
        for item in directory.iterdir():
            if item.name not in set(deliverables + ["manifest.json"]):
                item.unlink()
        directory.rename(destination)
    return {"status": manifest["status"], "engine": "tikz", "manifest": str(destination / "manifest.json"),
            "artifacts": [str(destination / name) for name in deliverables[:4]],
            "warnings": warnings, "scientific_interpretation": "PENDING"}


def audit_tikz(spec: dict, directory: str | Path) -> dict:
    """Check output bytes and bound scientific fingerprint; not visual correctness."""
    from protocol import contract
    validated = contract.validate_figure_spec(spec)
    folder = Path(directory).expanduser().resolve()
    data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if data.get("format") != "rfs-tikz/1.0" or data.get("scientific_fingerprint") != contract.scientific_fingerprint(validated):
        raise ValueError("TikZ manifest or scientific fingerprint mismatch")
    required = {"figure.tex", "figure.pdf", "figure.svg", "figure.png", "figure-spec.json"}
    if not isinstance(data.get("sha256"), dict) or set(data["sha256"]) != required:
        raise ValueError("TikZ manifest has an incomplete artifact inventory")
    for filename, expected in data["sha256"].items():
        if filename not in required:
            raise ValueError("Unexpected TikZ manifest filename")
        if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"TikZ artifact hash mismatch: {filename}")
    if json.loads((folder / "figure-spec.json").read_text(encoding="utf-8")) != validated:
        raise ValueError("TikZ figure science differs from supplied FigureSpec")
    return {"integrity": "PASS", "scientific_review": "PENDING", "visual_review": "PENDING"}
