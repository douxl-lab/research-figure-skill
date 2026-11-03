# Core capability map

This is an operating map, not a list of links that the user must activate manually.

| Scientific deliverable | Load and use automatically | What must remain separate |
| --- | --- | --- |
| New mechanism or architecture image | CVPR-Figure reference guide + PaperBanana delegation | Source accuracy is not inferred from an attractive candidate |
| Diagram with actual optical/SAR imagery | Preserve actual crops; use the same visual-design chain around them | Never synthesize observations, prediction maps or scores |
| Exact requested TikZ/math vector | Existing TikZ workflow/renderer | No forced PaperBanana call; no unverified formula |
| CSV, training curve or ablation | Existing validated Matplotlib adapter | No generated numeric chart |
| Approved image to editable PPTX/draw.io | Reconstruction guide; installed paper-fig/native specialist, or reviewed CVPR spec when suitable | PNG-in-PPTX is not native editability; preserve approved design |
| CVPR-Figure editable-vector output | Explicit reviewed CVPR YAML + render + validate | CVPR YAML and FigureSpec v1 are different contracts |
| Audit or small edit | Audit/edit existing artifact | Do not rerun concept design unnecessarily |

Read `assets/capabilities.json` for source repositories, exact reviewed revisions, runtime entrypoints and licensing boundaries. Sivia is optional, not a bundled default. Its rights must be reviewed before commercial work or redistribution. Existing `references/integrations.md` describes the low-level integrations; the default Agent-facing delegation order is defined by `references/orchestration.md`.

## Deliverable record

Keep a project-local workflow record with the selected modules, actual runtime paths/versions, actual calls, actual image files, references used, skipped modules and reasons. Preserve `PENDING`, `BLOCKED`, `HOST_ACTION_REQUIRED`, and partial/failed states. Report neither successful backend execution from a plan nor publication quality from unit tests. Do not store credentials, live research or generated work in the public Skill repository.
