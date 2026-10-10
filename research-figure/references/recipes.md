# Recipe precedence

For new figures, prefer canonical v1: `assets/figure-spec-v1-example.json` or `assets/figure-plot-v1-example.json`; see [canonical-exchange](canonical-exchange.md). The commands below are for the **legacy 0.1.0 format**, retained for existing user projects only.

# Recipes — runnable commands and honest outputs

Assume `RFS=/ABS/PATH/research-figure` and a real project folder `WORK=/ABS/PROJECT/figures/F01`. Run `python "$RFS/scripts/rfs.py" doctor` once; it reports installed (not necessarily executable) optional dependencies without exposing credentials.

## A: architecture creative design

```bash
python "$RFS/scripts/rfs.py" validate --spec "$WORK/F01.json"
python "$RFS/scripts/rfs.py" route --spec "$WORK/F01.json"
python "$RFS/scripts/rfs.py" prompt --spec "$WORK/F01.json" --model auto --provider gemini --priority balanced --out "$WORK/draft"
```

Open `draft/figure-prompt.md`; use it with the **actual** available image generator (host image tool) and attach the FigureSpec context as needed. Save genuine candidate files. `PROMPT_READY_NOT_RENDERED` is not a generated figure. For an authorized installed PaperBanana:

```bash
# Requires PAPERBANANA_ROOT + configured model credentials and explicit user permission
python "$RFS/scripts/rfs.py" run --spec "$WORK/F01.json" --engine paperbanana --allow-external --out "$WORK/generation"
```

Compare 2–8 existing candidate images (attach them to host vision reviewer):

```bash
python "$RFS/scripts/rfs.py" compare --spec "$WORK/F01.json" --images "$WORK/a.png" "$WORK/b.png" --out "$WORK/selection"
```

Make one scoped correction (host image-edit model must receive `chosen.png` bytes):

```bash
python "$RFS/scripts/rfs.py" prompt --spec "$WORK/F01.json" --stage refine --model gpt-image-2.5-sunburst \
  --reference "$WORK/chosen.png" --region "router subfigure" \
  --change "Fix the crossing outgoing arrow; preserve the rest of the image" --out "$WORK/refine"
```

## A -> optional native editable reconstruction

After **looking at** the real chosen image, create `$WORK/design-notes.md` from `assets/design-notes-template.md` with observed positions, fonts, object IDs/lanes and raster/native types. For an explicit approval:

```bash
python "$RFS/scripts/rfs.py" reconstruction-package --spec "$WORK/F01.json" \
  --reference "$WORK/chosen.png" --design-notes "$WORK/design-notes.md" \
  --approved --backend paper-fig --out "$WORK/reconstruction"
python "$RFS/scripts/rfs.py" audit-package --package "$WORK/reconstruction"
```

The installed native builder (paper-fig / Sivia / draw.io) must actually build and render the PPTX/draw.io. No `reconstruction-package` command produces a native file. If approval has not occurred, omit `--approved` and keep the candidate unlocked.

## C: empirical values -> plotting code

```bash
python "$RFS/scripts/rfs.py" run --spec "$RFS/assets/spec-plot-demo.json" --out /tmp/rfs-synthetic-demo
python "$RFS/scripts/rfs.py" audit --spec "$RFS/assets/spec-plot-demo.json" --artifact /tmp/rfs-synthetic-demo/figure.svg
```

Bundled example data is **synthetic and not research**. For a real paper, create a new FigureSpec and point `plot.data_file`/`evidence.path` at the actual CSV; store versions/seeds/extraction script outside the Skill. Install optional plots dependency via `python -m pip install -r "$RFS/requirements-plot.txt"` when permitted.

## B: explicitly simple structure-first SVG

```bash
python "$RFS/scripts/rfs.py" run --spec "$RFS/assets/spec-architecture-exact.json" \
  --engine native-svg --out /tmp/rfs-exact-draft
```

This produces a simple native SVG structural **draft**, not an aesthetic reference for complex scientific overviews. For architecture `generation.intent=creative`, forcing `native-svg` records a degraded creative goal.

## Offline project checks

```bash
python "$RFS/scripts/check_skill.py"
python -m unittest discover -s "$RFS/tests" -v
# Additional independent format check when installed:
skills-ref validate "$RFS"
```