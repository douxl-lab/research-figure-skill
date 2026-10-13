# Route T — local, source-preserving TikZ/PGF renderer

## Scope and activation

- **Opt in** with --engine tikz for a canonical FigureSpec Exchange v1 diagram. Flowcharts, algorithmic dependency diagrams, math-labeled architectures and timing diagrams are suitable.
- Leave the default creative route A (PaperBanana or prompt-only) intact. Real-valued experiment plots remain route C; mixed diagram+data work is split, never drawn from invented values.
- RFS is the authority for scientific nodes, directed/undirected edges, groups, labels, evidence and unchanged source data. TikZ is a renderer, not a second scientific editor or generative Critic. The protocol hash and scientific fingerprint are unchanged across this addition.
- High-density drawings require human layout QA; the deterministic rank-based layout is not a replacement for a top-tier illustration designer. It does not interpret arbitrary natural-language layout constraints.

## Dependencies and CLI

Requires Python 3.10+, XeLaTeX (TikZ/PGF, standalone, fontspec, amsmath/amssymb), pdftocairo (Poppler) and a suitable CJK font if Chinese labels are expected. On macOS these are generally supplied by a TeX Live/MacTeX installation plus Poppler; verify executables with command -v. If only TeX is available, install Poppler rather than treating an incomplete SVG/PNG export as success.

~~~bash
FIG=research-figure/assets/figure-spec-v1-example.json
python research-figure/scripts/rfs.py validate --spec "$FIG"
python research-figure/scripts/rfs.py route --spec "$FIG" --engine tikz
python research-figure/scripts/rfs.py run --spec "$FIG" --engine tikz --out /project/figures/F01-tikz
python research-figure/scripts/rfs.py audit --spec "$FIG" --artifact /project/figures/F01-tikz
~~~

Choose a fresh output directory for each candidate; avoid clobbering prior versions. The renderer writes .tex, PDF, SVG, PNG, a complete same-science FigureSpec and a manifest with SHA-256 hashes and scientific fingerprint. No image model or external API is called.

## Source ownership, scientific guarantees and security

1. Validate the whole FigureSpec v1 via the existing contract, including checksums, evidence quotes and node/edge references, **before** rendering. Labels are TeX-escaped; formula markup must use the restricted math-macro allowlist. Unsupported macros are refused rather than silently edited.
2. Compile a generated template with xelatex -no-shell-escape -halt-on-error in a fresh temporary directory. Restrict TeX openin/openout variables and impose a process timeout. These controls reduce risk but **do not constitute an OS sandbox**; untrusted workloads still require container/process isolation and resource limits.
3. Verify that all outputs exist and are nonempty before publishing. Hash files; the audit command checks each artifact byte stream and its FigureSpec against the canonical scientific fingerprint. A compilation PASS is **not** a scientifically validated topology, a pixel-perfect PaperBanana reconstruction, or an object-editable PPTX.
4. Keep all project outputs, source texts and figures outside the installed read-only Skill directory. Never commit unpublished scientific data, model credentials or project-generated illustrations to the public repository.

## Publication QA (required after compilation)

- View the actual PDF/PNG and inspect arrow direction, node coverage, formula correctness, labels, group boundaries, overlap and line intersections against the source and FigureSpec. Crossings must be individually reviewed.
- Review at actual single-column and double-column paper widths, not only a zoomed-in browser image. Check CJK/Latin font consistency, accents in grayscale, readable labels, bounded margins and no clipping.
- Confirm PDF/SVG remain vector geometry. pdfimages -list figure.pdf can reveal embedded raster elements, but zero embedded images alone does not establish visual correctness. SVG converted via Poppler may contain glyph outlines; the .tex source is the authoritative editable form.
- Record independent statuses for compilation, scientific review, publication-size visual review and native PPTX editability. No object-level PPTX is produced here.

## Optional PaperBanana visual-reference handoff

PaperBanana's authenticated vector-handoff CLI verifies an actual successful candidate bundle and exports reference.png, design.md, complete figure-spec.json and an integrity receipt. Use this **as visual design guidance** while rebuilding the semantics with TikZ:

~~~bash
python /PATH/PaperBanana/skill/exchange.py vector-handoff \
  --spec /project/F01.json --bundle /project/paperbanana/candidate \
  --out /project/vector-reference
python /PATH/research-figure/scripts/rfs.py run \
  --spec /project/vector-reference/figure-spec.json --engine tikz \
  --out /project/figures/F01-tikz
~~~

The reference handoff is not a TeX file and does not automatically duplicate the reference geometry. Inspect and compare the two renders explicitly; avoid changing scientific data to match visual pixels.
