# Style contract and consistent paper-wide visual language

RFS has shared style presets under `assets/style-academic-clean.json` and `assets/style-remote-sensing.json`. Each paper can select one in `style.theme`; do not arbitrarily recolor unrelated figures after a reference is approved.

The prompt system governs visual grammar: semantic palette by module role, clear primary spine, credible science-first illustrations, restrained shape vocabulary, readable type hierarchy, no accidental dashboard/card grid, intentional whitespace, and legibility at final physical publication width. **Colors alone do not define a distinctive paper figure**; structural composition matters more.

For numeric figures, the Matplotlib executor owns axes, units and data; ensure the selected palette remains readable when printed in grayscale. Do not create fictitious intervals or rescale metrics misleadingly. For multi-panel empirical imagery, keep original pixels and use native captions and callout shapes.

After image selection, copy actual style details into the image-anchored design notes; never infer exact shape positions or font properties from a text-only FigureSpec. Native reconstruction must preserve the approved candidate's composition as far as scientifically valid and technically feasible.
