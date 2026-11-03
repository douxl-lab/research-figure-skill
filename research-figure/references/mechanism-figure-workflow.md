# Mechanism figure production SOP

Portable production discipline: assets first, connection lanes before drawing, native structure plus justified raster content, and inspection of final saved files.

## Eight steps

1. **Specify.** For an existing reference, inspect it and record panel bounds, object inventory, text, raster slots and acceptance criteria. For a new mechanism, read the actual paper/code/formulas and validate FigureSpec. Science outranks a reference image when they conflict; mark unresolved conflicts pending instead of inventing a compromise.
2. **Prepare assets.** Code-render purely mathematical illustrations when appropriate. Generated imagery may be illustrative placeholders only, labelled as such. Real optical/SAR crops, prediction maps and empirical plots come from their actual sources. For reconstruction crops, convert displayed coordinates to source-image coordinates, then inspect a contact sheet. Preserve aspect ratio and source rights.
3. **Reserve lanes.** Allocate horizontal/vertical corridors before drawing arrows. Distinguish parallel edges with spacing appropriate to the final printed size. Pass explicit lane/bounds constraints to collaborators; shortest-path drawing is not sufficient.
4. **Build panels.** Use a real available subagent/editor when appropriate, or one sequential producer when not. Generate repeated objects programmatically. Prefer structured XML editing to regex substitutions; ensure unique IDs, valid parents, referenced endpoints and native labels. A supplied layout cannot silently alter source semantics.
5. **Merge and embed.** Merge panels with collision-free IDs and explicit coordinate transforms. Embed legitimate raster content in planned slots without stretching. Validate the final merged file, not only intermediate panels; do not silently delete dangling scientific edges.
6. **Self-audit.** Check text/subscripts/tensor labels, line corridors, crossings through opaque objects, label overlap, raster inventory, object counts and z-order. Run structural checks, render a preview and inspect that actual preview. Record defects and limitations.
7. **Independent inspection.** Use an actually available separate reviewer with the source, final file, acceptance criteria and known differences. Report when no independent review ran. On Windows, use UTF-8 task files/console settings where needed; never hard-code a particular reviewer CLI into the portable workflow. Failed inspection returns to repair and full final-file validation.
8. **User approval and delivery.** Deliver the requested native source, publication export, preview, known differences and unresolved placeholder list. User approval concerns the specific candidate, not all future versions. Do not mark it approved in advance.

## Format decisions

| Target | Approach | Required qualification |
| --- | --- | --- |
| Preview PNG | Render the saved authoritative source | A preview is not native editability |
| SVG/PDF | Layout/TikZ/editor vector export | Check actual printed text, symbols, arrows and embedded pixel resolution |
| PPTX | Native layout writer or available native reconstruction backend | Inspect text, shapes and connectors; a rasterized edge remains raster |
| draw.io | Available native builder/editor | Validate XML and inspect final render, not only coordinate tables |

After manual edits, keep one authoritative source; never rerender an outdated spec over it. HTML-to-PPTX or alternative routes may be used only with a real available tool and disclosed editability limitations. Cross-export consistency and source/image/bundle hash binding are release gates where the required converters exist, not claims based on a planned command.
