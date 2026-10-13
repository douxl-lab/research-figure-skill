# TikZ journal-quality checklist (visual review; not an automated PASS)

Use this checklist **after** the actual .tex has been compiled to PDF and PNG.

1. **Scientific exactness:** every node, connection direction, displayed formula, group and annotation is traceable to FigureSpec v1 and the checked method/code. Missing, inferred or contradictory science is a FAIL.
2. **Layout:** assess reading order, grouping, edge intersections, text-on-arrow collisions, consistent spacing, consistent corner/line styles, and empty space. A deterministic rank-based layout is just a starting point. For complicated cyclic/high-density networks, manually refine the source or select route A and reconstruct.
3. **Typography:** CJK, English and math fonts must be legible at publication size. No tofu glyphs, overflowing formulas, text clipping, superscript misplacement or excessive font-size hierarchy.
4. **Colors:** use a restrained journal palette, with meaningful distinctions and grayscale robustness. Style changes cannot alter scientific semantics. Avoid big in-image titles, decorative banners or gratuitous panel letters in standalone figures.
5. **Deliverables:** check .tex compiles, PDF/SVG contain vector geometry, PNG was actually rendered from the PDF, artifacts have hashes and the spec fingerprint matches. A reproducible .tex is editable code, not native PPTX shapes.
6. **Review receipt:** record compilation, source_integrity, scientific_review, visual_review, format_compatibility separately. Only checked dimensions may be marked PASS; never infer science PASS from compiler success.

Test with (i) a compact Chinese + English pipeline with groups, (ii) formulas and time-dependent transitions, and (iii) a larger graph exhibiting long edges and cycles. The current renderer supports 64 nodes and 160 edges maximum; beyond this it errors instead of silently dropping content. Complex chemistry glyphs and photorealistic appliances belong to specialized engines or composite visual assets, not a basic TikZ flow template.
