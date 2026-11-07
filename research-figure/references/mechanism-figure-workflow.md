# Mechanism figure production SOP

**Default: understand → design the complete image → generate → inspect → targeted edit → deliver.** Image-model composition is the primary creative path. Code-drawn skeletons, asset assembly and vector reconstruction are explicit alternatives, not mandatory intermediate stages.

## Source and visual brief

Read the relevant paper/code/user explanation and preserve the actual modules, branches, arrows and dependency relationships in FigureSpec. Keep unknown facts pending. The source contract is not a mandate to put every source fact on the canvas. Most mechanism figures need only a few exact labels and no equations. Never invent formulas, dimensions, empirical improvements or observations.

Choose one independent scientific question per image. Inspect relevant local design references, then state a concise visual story: what enters, what changes, what interacts, what leaves, and why the innovative operation differs. Give the innovation more visual space than routine preprocessing. Use purposeful glyphs, token/feature representations and spatial relationships; avoid a row of verbose boxes, poster headings or decorative complexity. Keep long explanation in the caption.

Reference images have explicit roles: composition, style, current candidate, or source evidence. Style references do not provide scientific facts. Preserve the scientific topology when adapting a reference. Connection lanes and panel proportions are design constraints, not a requirement to position every object with code.

## Default image-model route

1. **Generate the complete composition.** Use the actual host image tool first, or an authorized configured image2-api/provider. The host LLM writes and reviews the prompt; the image model draws the full figure. Do not limit it to icons by default. A small candidate set is optional and budget-bound, not an unlimited search.
2. **Inspect actual images.** Compare source topology, arrow endpoints, repeated symbols, spelling, label density, hierarchy, whitespace and readability at the intended printed size. High visual quality does not establish scientific correctness. Record specific observed defects rather than restating prompt intentions.
3. **Edit the selected candidate.** For a local defect, send the selected image as the primary input and specify what changes, what must remain, and how the repair will be checked. Use additional references and a supported mask when useful. Never overwrite the selected original. An edit request cannot guarantee unrelated pixels remain identical: inspect every new result.
4. **Finish when gates pass.** Stop at the requested format after source and visual review. A good PNG does not need conversion to SVG merely because SVG is available. Preserve the source contract, original/submitted prompt, candidates, references, repair instructions and generation metadata outside the public Skill.

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

## Optional code/vector path

Use host-authored SVG when the user explicitly asks for SVG or exact object editability. The host writes SVG code directly, then validates XML and renders the saved file for inspection. No image-API SVG call is needed. Keep editable text and semantic groups where feasible; avoid raster wrappers presented as native vectors. TikZ remains available for an explicitly suitable deliverable, not because the topic sounds mathematical.

When a native reconstruction or mixed-data composition is requested, retain the established discipline: inventory assets, reserve connection lanes, build panels with unique IDs, merge using explicit transforms, preserve real pixels, and inspect the final composition and export. Do not rerender an outdated specification over manual edits.

Real plots use source data and deterministic rendering. Optical/SAR images, predictions and measured heatmaps remain actual source assets. These boundaries do not force the surrounding mechanism illustration into a code-only style.

## Delivery

Default image delivery: the actual final image, a preview as needed, source/prompt/receipt records and a short unresolved-issues statement. SVG, native PPTX, draw.io and vector PDF are additional deliverables only when requested and actually verified. A flattened slide or wrapped PNG must be labelled accordingly. A prompt, dry-run, prepared job or `HOST_ACTION_REQUIRED` response is not a generated figure.
