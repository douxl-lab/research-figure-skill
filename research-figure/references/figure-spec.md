# FigureSpec — scientific contract (v0.1 schema, RFS runtime v0.3)

`assets/figure-spec.schema.json` describes the **FigureSpec JSON document**. Runtime version (`0.3.0`) and schema version (`0.1.0`) are different version axes; the schema keeps its legacy version for compatibility while adding optional design/generation fields. Run `python scripts/rfs.py validate --spec /PATH/spec.json`.

## Required fields

- `schema_version`: `0.1.0` for all bundled examples.
- `figure_id`, `type`, `title`, `scientific_claim` and `evidence` array.
- `type`: `architecture`, `quantitative`, `editable_reconstruction`, `evidence_panel`.
- `evidence`: each `id` + `kind=method|code|data|reference|hypothesis` + `status=verified|pending|illustrative`, optionally an existing local `path` and SHA256.
- `architecture`: `diagram.nodes[]` with stable `id`, exact `label`, `evidence_refs`; `diagram.edges[]` with `source`, `target`, optional `label`, `feedback`, `evidence_refs`.
- `quantitative`: `plot.kind=bar|line|scatter`, actual `plot.data_file`, `plot.x`, `plot.y`, optionally grouping `plot.series`, axis labels. Data CSV must exist.

A `verified` label in the spec is the preparer's assertion, **not** proof a visual claim was independently checked. Missing source files or wrong hashes are errors; unsupported scientific relations stay `pending`. Synthetic examples require `style.demo=true` to produce a conspicuous disclaimer on generated demonstration data figures.

## Optional creative design additions

```json
{
  "generation": {"intent": "creative", "archetype": "overview"},
  "design": {
    "reading_path": "left_to_right",
    "visual_priority": "Visually highlight the novel module without hiding prerequisites",
    "layout_notes": ["Main flow is clear before local detail is read"],
    "connector_notes": ["Avoid routes through unrelated blocks and labels"],
    "text_notes": ["Use exact case-sensitive scientific terminology"],
    "asset_notes": ["Empirical evidence must use genuine source pixels"],
    "avoid": ["Decorative icon clutter", "Invented experimental results"]
  }
}
```

`generation.intent` defaults to `creative` for **architecture**, so accurate scientific topology and generative composition coexist. Set `exact` only when explicitly requesting simple structure-first native output. `generation.archetype`: `overview`, `architecture`, `mechanism`.

## FigureSpec preparation guidance

Read actual code/method/result files. For every module, create one stable ID and evidence reference; distinguish legitimate training/inference paths and feedback loops. Don't guess equations, modality inputs, confidence values or performance. If reference image suggests a topology differing from source code, record discrepancy. Numeric errors, missing required columns, missing series/category pairs, nonfinite values and unintended repeats must fail, not be plotted as zero/averaged without explanation.

## Files in the bundle

- `assets/spec-architecture.json`: tentative MRLQ-EF creative FigureSpec for testing (NOT validated implementation).
- `assets/spec-architecture-exact.json`: same source as a direct SVG test (NOT publication-grade styling).
- `assets/spec-plot-demo.json` and `assets/demo-synthetic-ablation.csv`: synthetic data for software tests ONLY.
- `assets/design-notes-template.md`: template to fill from an actually viewed chosen image, not from imagined geometry.

Store your live project specifications beside your paper code or experimental artifacts, never inside the installed Skill directory.
