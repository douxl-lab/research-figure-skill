"""Deterministic source-CSV-to-Matplotlib publication graphics.

No statistical aggregation, imputation, synthetic uncertainty, or inferred
significance is performed.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from core import RFSValidationError, hash_file, load_style, read_plot_rows, resolve_source


def render_plot(spec: dict, spec_path: str | Path, out_dir: str | Path) -> dict:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise RFSValidationError("Quantitative chart requires Matplotlib: python -m pip install matplotlib") from exc
    if spec.get("type") != "quantitative":
        raise RFSValidationError("Matplotlib renderer only supports quantitative type")
    rows = read_plot_rows(spec, spec_path)
    cfg = spec["plot"]
    style = load_style(spec)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["series"]].append(row)
    categories = list(dict.fromkeys(str(r["x"]) for r in rows))
    nseries = len(grouped)
    palette = style["palette"]
    wpx = spec.get("target", {}).get("width_px", 1400)
    hpx = spec.get("target", {}).get("height_px", 850)
    figsize = (max(5.4, min(11.0, wpx / 150)), max(3.3, min(7.0, hpx / 155)))
    plt.rcParams.update({
        "svg.fonttype": "none", "pdf.fonttype": 42,
        "font.family": "DejaVu Sans", "axes.spines.top": False,
        "axes.spines.right": False, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 8, "savefig.dpi": 300
    })
    fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    kind = cfg["kind"]
    if kind == "bar":
        xpos = np.arange(len(categories), dtype=float)
        group_width = 0.76
        width = group_width / max(1, nseries)
        for idx, (group, rr) in enumerate(grouped.items()):
            values = {str(r["x"]): r["y"] for r in rr}
            ys = [values[cat] for cat in categories]
            offset = (idx - (nseries - 1)/2) * width
            ax.bar(xpos + offset, ys, width*0.90,
                   label=group if nseries > 1 else None,
                   color=palette[idx % len(palette)], linewidth=0.3,
                   edgecolor="#FFFFFF", hatch=("", "//", "xx", "..", "\\\\")[idx % 5])
        ax.set_xticks(xpos, categories)
        # Baseline 0; never visually truncate bars to amplify small differences.
        lo, hi = ax.get_ylim()
        ax.set_ylim(min(0.0, lo), max(0.0, hi))
    elif kind in {"line", "scatter"}:
        symbols = ("o", "s", "^", "D", "v", "P", "X")
        for idx, (group, rr) in enumerate(grouped.items()):
            rr = sorted(rr, key=lambda r: r["x"]) if kind == "line" else rr
            xx = [r["x"] for r in rr]
            yy = [r["y"] for r in rr]
            color = palette[idx % len(palette)]
            if kind == "line":
                ax.plot(xx, yy, marker=symbols[idx % len(symbols)], markersize=5,
                        linewidth=1.8, color=color, label=group if nseries > 1 else None)
            else:
                ax.scatter(xx, yy, marker=symbols[idx % len(symbols)], color=color,
                           s=32, label=group if nseries > 1 else None)
    ax.set_xlabel(cfg.get("x_label") or cfg["x"])
    ax.set_ylabel(cfg.get("y_label") or cfg["y"])
    ax.set_title(spec["title"], fontsize=12, pad=12)
    ax.grid(axis="y", alpha=0.16, zorder=0)
    if nseries > 1:
        ax.legend(frameon=False)
    if spec.get("style", {}).get("demo"):
        fig.text(0.5, 0.5, "DEMO / SYNTHETIC DATA — NOT REAL RESULTS",
                 ha="center", va="center", rotation=18, fontsize=17,
                 weight="bold", color="#AC3C2B", alpha=0.27,
                 transform=fig.transFigure)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    filenames = []
    for ext in ("svg", "pdf", "png"):
        dest = out / f"figure.{ext}"
        fig.savefig(dest, format=ext, dpi=300, facecolor="white")
        filenames.append(str(dest.resolve()))
    plt.close(fig)
    data_file = resolve_source(spec_path, cfg["data_file"])
    return {"engine": "plot-matplotlib", "artifacts": filenames,
            "source_csv": str(data_file), "source_sha256": hash_file(data_file),
            "matplotlib_version": matplotlib.__version__,
            "row_count": len(rows), "series_count": nseries,
            "known_limitations": ["No implicit statistics / error bars / uncertainty", "Publication-size visual inspection required"]}
