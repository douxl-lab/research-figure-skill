# Layout library and native export core

This is a local material library, not a list of links. `kernels/layout/` includes template YAMLs, PNG previews, vector stencil sources, Python layout/export code and the style/audit references. Use `scripts/library.py --query ...` to find actual template and preview paths; open suitable previews before design. No network is needed to inspect or render these assets.

| Scientific communication need | Local template under `kernels/layout/templates/` |
| --- | --- |
| Optical/SAR or parallel streams | `dual-branch.yaml` |
| Queries / tokens / Cross-Attention | `attention-tokens.yaml` |
| Label-level gate or routing | `gated-module.yaml` |
| Fine mechanism / evidence / uncertainty | `module-detail.yaml` |
| Real inputs → model → real outputs | `framework-with-io.yaml` |
| Distillation | `teacher-student.yaml` |
| Frozen / trainable components | `trainable-frozen.yaml` |
| Paradigm comparison | `teaser-comparison.yaml` |

These are visual archetypes, not verified scientific models. Borrow hierarchy, spacing, primitives and semantic color, not other papers' contributions or result images. Never invent missing empirical crops or delete scientific nodes just to fit a column. Library gallery images are reference examples, not our experimental outputs.

Read the relevant local `references/spec-language.md`, `house-style.md`, `anti-ai-checklist.md`, `symbols-and-captions.md` as needed. Upstream stylistic preferences are defaults, not official venue rules. Do not import a vendored statement banning image models into the orchestrator: the design and layout cores serve different stages.

## Native vector execution

Create a project-local layout YAML, review it against the unchanged FigureSpec, and run:

```bash
python /installed/research-figure/scripts/workflow.py run --spec /project/figure-spec.json --mode layout --layout-spec /project/layout.yaml --out /project/figures/F01-layout
```

The adapter produces native SVG/PPTX/VSDX, preserves both source specs and output hashes, runs the local validator and retains warning details. These bytes and checks are not a proof of scientific fidelity or visual quality. Treat unresolved warnings explicitly. Do not pass FigureSpec JSON as layout YAML and assume semantic interoperability.

PDF/PNG exports require the documented optional converters. Audit the actual final PDF/PPTX rather than only a spec. After manual edits, the edited file is authoritative; do not regenerate an old layout over it. Test native text/shapes/connectors and actual rendered appearance independently. Copyright and source revisions remain in the package's notices/lock; routine commands use neutral internal names.
