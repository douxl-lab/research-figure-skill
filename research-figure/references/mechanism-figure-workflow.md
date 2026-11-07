# Mechanism figure production SOP

**Two core workflows, one default.** Image-first defaults to understand → design the complete image → generate → inspect → targeted edit → deliver. Hybrid assembly is equally maintained: code scaffold → scoped model-generated assets → code composition → inspect → targeted repair. It is a core capability, not a fallback or deprecated feature. Select by the user’s request or agreed task constraints; do not force either strategy onto every figure.

## Source and visual brief

Read the relevant paper/code/user explanation and preserve the actual modules, branches, arrows and dependency relationships in FigureSpec. Keep unknown facts pending. The source contract is not a mandate to put every source fact on the canvas. Most mechanism figures need only a few exact labels and no equations. Never invent formulas, dimensions, empirical improvements or observations.

Choose one independent scientific question per image. Inspect relevant local design references, then state a concise visual story: what enters, what changes, what interacts, what leaves, and why the innovative operation differs. Give the innovation more visual space than routine preprocessing. Use purposeful glyphs, token/feature representations and spatial relationships; avoid a row of verbose boxes, poster headings or decorative complexity. Keep long explanation in the caption.

Reference images have explicit roles: composition, style, current candidate, or source evidence. Style references do not provide scientific facts. Preserve the scientific topology when adapting a reference. Connection lanes and panel proportions are design constraints, not a requirement to position every object with code.

## Default image-model route

1. **Generate the complete composition.** Use the actual host image tool first, or an authorized configured image2-api/provider. The host LLM writes and reviews the prompt; the image model draws the full figure. Do not limit it to icons by default. A small candidate set is optional and budget-bound, not an unlimited search.
2. **Inspect actual images.** Compare source topology, arrow endpoints, repeated symbols, spelling, label density, hierarchy, whitespace and readability at the intended printed size. High visual quality does not establish scientific correctness. Record specific observed defects rather than restating prompt intentions.
3. **Edit the selected candidate.** For a local defect, send the selected image as the primary input and specify what changes, what must remain, and how the repair will be checked. Use additional references and a supported mask when useful. Never overwrite the selected original. An edit request cannot guarantee unrelated pixels remain identical: inspect every new result.
4. **Finish when gates pass.** Stop at the requested format after source and visual review. A good PNG does not need conversion to SVG merely because SVG is available. Preserve the source contract, original/submitted prompt, candidates, references, repair instructions and generation metadata outside the public Skill.

## Core hybrid assembly workflow

Use `workflow.py run --mode hybrid-assembly --spec /project/F01.json --host-image-tool ACTUAL_AVAILABLE_TOOL --out /project/F01-hybrid`. The coordinator snapshots the scientific source and writes `hybrid-job.json` with pending host tasks. It **does not** render a scaffold, invoke an image model, compose a figure or approve it during preparation. A configured external asset route instead requires `--image2-root` and applicable `--allow-external`; retain the service/configuration boundary in `local-image-pipeline.md`. Do not invent a usable backend from a key or package name.

1. **Code the scaffold first.** Use host-authored SVG/Python composition or the bundled layout renderer. Lock node/group IDs, exact labels, ports, arrow endpoints, panel geometry, typography and connection corridors against FigureSpec. Reserve named asset slots with bounding boxes, aspect ratio, padding and clipping rules. Render and inspect the scaffold before generating assets. Placeholders are allowed here but not in the final deliverable. A scientific contract and a layout YAML are different inputs; review their correspondence.
2. **Generate scoped assets.** Each request describes one slot’s scientific role, visual shape, viewpoint, palette, scale and background. Share one style specification across assets. Keep global labels, connections and captions in code; do not ask the generator to redraw the entire figure. A local glyph may depict an internal interaction when grounded in the source. Record actual image bytes, prompt/receipt, provenance, target slot and SHA-256 in an asset ledger; verify requested alpha transparency. No synthetic remote-sensing observations, predictions or measured heatmaps.
3. **Compose deterministically.** Insert accepted assets into the locked slots, preserve their aspect ratio and keep labels/arrows on separate layers above imagery. Protect connection lanes and avoid clipping useful detail. Reuse code/scaffold and unaffected assets when replacing one asset. Do not send the entire scaffold to image-to-image generation and call the result a structure-preserving composition: that is a different strategy and may change topology.
4. **Review the saved composition.** Check every scientific edge and label, cross-asset style consistency, whitespace, overlap, printed-size readability and any requested transparency. Rerender the actual exported file after repair. Preserve the scaffold source, asset ledger and bytes, composition code, final image and review notes. A slot placeholder or unexecuted task means incomplete, not success.

The layout kernel already supports `shape: image` with an explicit `w`, `h`, and optional `src` relative to the layout file. Missing `src` creates a visible scaffold placeholder; filling `src` must not alter the locked slot dimensions. Use its existing renderer and validator rather than implementing a competing layout engine. A standalone SVG is not mandatory: Python raster composition is also valid. A composition SVG may legitimately contain raster assets; call it **mixed vector/raster**, not fully vector or fully editable. Real-data panels remain source-preserving even inside a hybrid composition.

`hybrid-assembly` is a production strategy for `kind: diagram`. Do **not** change a diagram to FigureSpec `kind: hybrid` to select it: that kind already denotes mixed scientific content with its own source-preserving route.

## Quality gates

| Gate | Check |
| --- | --- |
| Science | Correct modules, branches, directed edges and innovation; no invented empirical content |
| Communication | The mechanism is visible without paragraphs of explanation; labels identify rather than narrate |
| Design | Clear hierarchy, intentional glyphs, balanced density, purposeful color and sufficient arrow spacing |
| Publication | Readability at actual column width, correct aspect ratio and sufficient actual pixel dimensions |
| Transparency | When requested, inspect the alpha channel and edges; white or checkerboard pixels are not transparency |
| Iteration | Preserve accepted structure, version candidates and inspect the final saved bytes |

DPI metadata alone does not add image detail. A PDF containing the PNG is still raster content. Report limitations instead of claiming native vectors or acceptance by a venue. Use an independent reviewer only when actually available; otherwise disclose that review was not independent. Approval refers to the specific image, not future variants.

## Standalone vector and reconstruction paths

Use host-authored SVG when the user explicitly asks for SVG or exact object editability. The host writes SVG code directly, then validates XML and renders the saved file for inspection. No image-API SVG call is needed. Keep editable text and semantic groups where feasible; avoid raster wrappers presented as native vectors. TikZ remains available for an explicitly suitable deliverable, not because the topic sounds mathematical.

When a native reconstruction or mixed-data composition is requested, retain the established discipline: inventory assets, reserve connection lanes, build panels with unique IDs, merge using explicit transforms, preserve real pixels, and inspect the final composition and export. Do not rerender an outdated specification over manual edits.

Real plots use source data and deterministic rendering. Optical/SAR images, predictions and measured heatmaps remain actual source assets. These boundaries do not force the surrounding mechanism illustration into a code-only style.

## Delivery

Default image delivery: the actual final image, a preview as needed, source/prompt/receipt records and a short unresolved-issues statement. SVG, native PPTX, draw.io and vector PDF are additional deliverables only when requested and actually verified. A flattened slide or wrapped PNG must be labelled accordingly. A prompt, dry-run, prepared job or `HOST_ACTION_REQUIRED` response is not a generated figure.
