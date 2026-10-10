# Prompt Compiler: 专业化科研生图系统

**Purpose:** image-generation models are visual design engines; their raster outputs must never be mistaken for editable scientific objects or new experimental evidence.

## The six-layer compiler contract

`rfs.py prompt` compiles the FigureSpec into one *model-adapted* prompt, with these mandatory parts:

1. **Figure Intent + Evidence**: reader takeaway, tentative/verified source status, figure archetype.
2. **Scientific Structure**: exact labels, stable node IDs, directed edges, permitted feedback and proof references. Never add scientific modules or data.
3. **Spatial Composition**: chosen reading spine, hierarchy, grouped regions, arrow corridors, anti-crossing and figure size.
4. **Academic Visual Grammar**: paper-compatible typography, constrained palette, novelty emphasis, grayscale/column-width clarity.
5. **Exact Text & Reconstruction Awareness**: literal spelling; clean separation of image art versus objects to be natively retyped.
6. **Negative Constraints & Output**: no fake results, misspellings, extra arrows, unrelated icons, occlusion, dashboards, figure title. Output is a **design preview**, not native PPTX.

For current dated model IDs and separate parameters, read [model routing](model-routing.md) and `assets/prompts/model-registry.json`. `rfs.py models` lists candidate models but cannot confirm account access. `--model auto --provider gemini --priority balanced` compiles a Gemini Nano Banana 2.1 prompt as of 2026-10-09; override with an exact model ID and keep the registry receipt. Prompts return `model-call-plan.json`, which is **advisory only**, not an executable API request.

Provider-level fallback profiles live in `assets/prompts/model-profiles.json`: `gemini`, `gpt-image`, `generic`. Their differences are *workflow heuristics* to be A/B-tested in the actual target model environment, not guarantees that any provider renders perfect technical text. No API credentials or provider SDKs are bundled. Profiles can be revised without changing source truth.

## Three prompt phases (do not blend them)

**Draft:** science -> full figure concept. Compile for the currently available generator:

```bash
python scripts/rfs.py prompt --spec /PROJECT/F01.json --model auto --provider gemini --priority balanced --out /PROJECT/F01/draft
```

This writes `figure-prompt.md` and `design-brief.md` plus a source-hash receipt. A host with an actual image tool should submit the prompt and then *inspect the real image*, not merely declare success from a tool call.

**Compare:** pass 2–8 *existing, distinct* images, review legible labels, node/edge coverage, readers' first interpretation, crossings, occlusion and publication-width legibility:

```bash
python scripts/rfs.py compare --spec /PROJECT/F01.json --images /PROJECT/F01/a.png /PROJECT/F01/b.png --out /PROJECT/F01/review
```

The generated `comparison-prompt.md` is *only instructions*. The host must attach/view the actual images and record findings; no image contents are analyzed by the local CLI.

**Refine:** do not resubmit the full draft as if it were a redesign. Pass reference image and one localized fix; keep all other regions fixed:

```bash
python scripts/rfs.py prompt --spec /PROJECT/F01.json --model gpt-image-2.5-sunburst --stage refine \
  --reference /PROJECT/F01/chosen.png --region "Router + outgoing edge" \
  --change "Remove the crossing; preserve module order and all labels" --out /PROJECT/F01/refine
```

For image-edit tools the host **must attach the image bytes**, not merely put its path in text. Any requested topology change must be reconciled against sources before editing.

## Fit to PaperBanana without double planning

PaperBanana's own five agents already plan, style, visualize and critique. Canonical v1 requests pass the *full unchanged FigureSpec*, verified protocol descriptor and original source, not a lossy text summary. The `rfs.py run --engine paperbanana --allow-external` adapter feeds it a compact scientific and design-intent brief instead of spawning another outer Planner/Stylist/Critic sequence. The standalone model profiles are most relevant to *direct host image generation* or explicitly selected model-specific work.

## Candidate -> approved design

A high-quality image is a visual reference. After selection, inspect it and author detailed **image-anchored** notes using `assets/design-notes-template.md`; the compiler's pre-image design brief is a starting point, **not a substitute for observed image details**. An approved composition does not make fabricated numbers or false arrow relationships acceptable. Continue to [reconstruction](reconstruction.md).