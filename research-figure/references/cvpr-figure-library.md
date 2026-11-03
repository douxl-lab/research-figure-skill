# CVPR-Figure reference library and vector backend

Source: https://github.com/ChizkiyahuOhayon/CVPR-Figure . The exact reviewed revision and MIT license identifier are in `assets/capabilities.json`. Use as a recurring reference source, not an official CVPR standard or a guarantee of acceptance. This guide is independently authored; upstream templates/code retain their original license when installed.

## Mandatory reference selection for mechanism figures

Choose the closest archetype before design. Inspect its actual template/gallery when the checkout is available; otherwise this index is a structural suggestion, not a claim to have viewed that gallery.

| Need | Upstream template |
| --- | --- |
| Input → architecture → actual output | `templates/framework-with-io.yaml` |
| Optical/SAR or other parallel streams | `templates/dual-branch.yaml` |
| Label Query / Cross-Attention | `templates/attention-tokens.yaml` |
| Routing/gating with a focused contribution | `templates/gated-module.yaml` |
| Evidence/uncertainty or another detailed mechanism | `templates/module-detail.yaml` |
| Teacher/student distillation | `templates/teacher-student.yaml` |
| Frozen backbone and trainable modules | `templates/trainable-frozen.yaml` |
| Before/after or paradigm comparison | `templates/teaser-comparison.yaml` |

Reuse spatial hierarchy, visual grammar, semantic colors and primitive shapes. Replace all scientific content with verified project facts. Do not import another paper's output image as our result. Do not auto-delete a scientific node to fit a column; any abstraction must preserve the stated mechanism and be explained.

Read the relevant upstream `references/house-style.md`, `references/spec-language.md` and `references/anti-ai-checklist.md` only when needed. Treat upstream preferences (Office palette, fonts, font sizes or anti-AI rules) as **local style defaults**, not universal journal requirements. They do not override our source contract, user/venue requirements, PaperBanana route or TikZ availability. In particular, do not import an upstream top-level prohibition on image models into the RFS orchestrator.

## Optional executable vector path

CVPR-Figure accepts its own YAML spec. Never send canonical FigureSpec JSON directly to it and claim semantic interoperability. Create and review the YAML against the unchanged FigureSpec before invoking:

```bash
python /installed/research-figure/scripts/workflow.py run --spec /project/figure-spec.json --mode cvpr-figure --cvpr-spec /project/cvpr-layout.yaml --out /project/figures/F01-vector
```

The adapter requests native SVG/PPTX/VSDX and runs the upstream validator, then checks that all requested files exist and are nonempty. It does not establish scientific fidelity, rendered appearance or native object quality. For PDF/PNG conversion, use the installed upstream converter workflow and audit the actual export; external converters are separate dependencies. For hand-edited PPTX, run upstream `audit_pptx.py`, export, and audit the PDF; do not overwrite edits by rerendering an older YAML.

CVPR-Figure and PaperBanana can serve different stages of one job. They are not mutually exclusive names that the user must choose between. Only run the vector backend when the output requires it; consulting the reference library does not require executing every renderer.
