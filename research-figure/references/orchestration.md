# Integrated orchestration contract

## Persistent project decision — 2026-11-03

`research-figure` is the installed Skill ID; `research-figure-skill` is the repository. One invocation owns the whole scientific-figure task. The user must not have to name PaperBanana, CVPR-Figure, TikZ or paper-fig again. Select capabilities from the deliverable, not from whether the user supplied backend keywords. This is a versioned project policy, not a claim about chat memory.

CVPR-Figure is a long-term **reference/template/component/audit library** and optional vector renderer. Do not copy another paper's mechanism or evidence. PaperBanana owns visual design and its five stages. TikZ owns explicit precise vector/math work. Matplotlib owns measured plots. Native builders own requested editable reconstructions. Preserve actual scientific sources, real pixels and the distinction between implemented, unverified and proposed mechanisms.

## Mandatory flow

1. Read the source and validate the unchanged FigureSpec. New jobs use v1. Unknown science stays pending; no invented formula, experiment, image or output.
2. Read `assets/capabilities.json` and the relevant bundled guides. For a new mechanism/architecture figure, **always** consult `references/cvpr-figure-library.md` and `references/paperbanana-delegation.md`, without waiting for explicit backend names. Record the selected visual archetype and why it fits.
3. Observe actual host tools; do not infer tool access from an API key, a Skill name or a directory. Run `scripts/workflow.py doctor`, then `plan`. `--host-image-tool` must name a genuinely exposed image-generation tool, not an invented capability. File presence is discovery only.
4. Execute the selected route. For a compatible PaperBanana checkout plus host image tool, select native-host automatically. An explicit provider selection with task/service/cost authorization takes precedence; otherwise native host takes precedence over provider use. A legacy spec is not silently converted to canonical v1.
5. If the PaperBanana runtime is absent but a host image tool exists, execute the bundled five-stage host guide. Label it `bundled-host-workflow`, **not** an upstream runtime invocation. If no generator is available, record `BLOCKED`; do not end successfully with only a prompt or silently replace a creative figure with boxes.
6. Run only one Retriever/Planner/Stylist/Visualizer/Critic chain. Approved-reference editing bypasses new concept generation. Source-data plots bypass all generative stages. Explicit TikZ remains local. Native editing/reconstruction requires the actual approved image, exact science and observed design notes.
7. Review actual image bytes and exported files. Preserve execution state separately from scientific/visual review and native editability. A host tool that ends the turn may prevent same-turn Critic execution: mark review pending rather than fabricate it.

## Commands

Use absolute paths from the installed Skill; the user's current directory is not the Skill directory.

```bash
python /installed/research-figure/scripts/workflow.py doctor
python /installed/research-figure/scripts/workflow.py plan --spec /project/figure-spec.json --host-image-tool ACTUAL_HOST_IMAGE_TOOL
python /installed/research-figure/scripts/workflow.py run --spec /project/figure-spec.json --host-image-tool ACTUAL_HOST_IMAGE_TOOL --out /project/figures/F01
```

`run` initializes a PaperBanana native job and returns its first task. **The host must then execute all returned stages; this command alone does not generate an image.** Provider/plot/TikZ routes delegate to the existing validated `rfs.py` adapters. Keep `rfs.py` as the backwards-compatible low-level CLI; its `auto` does not discover host tools. Use `workflow.py` as the Agent-facing entrypoint.

The explicit `--mode` values include `paperbanana-native`, `paperbanana-provider`, `cvpr-figure`, `tikz`, `plot-matplotlib` and `prompt-only`. Use `--allow-external` only when the actual service/data/cost authorization exists. Never ask users to reauthorize an already applicable permission merely because the backend name was omitted; never generalize permission across services or data.

## Complete package versus runtime dependencies

The RFS package contains the workflow, capability registry, adapters, source contract, safety/QA rules and tests. External engines remain versioned dependencies, not competing top-level instruction sets. `scripts/bootstrap_backends.py` can materialize the two pinned open-source engine checkouts into a user-selected directory, with their original licenses. It does not install Python packages, run their code, acquire credentials, or grant network/provider permission. Discovery supports `--backend-dir`, `PAPERBANANA_ROOT`, `CVPR_FIGURE_ROOT`, bundled `backends/`, and sibling checkouts. Outputs never belong in the installed Skill.

ChatGPT/Codex still needs to load this updated package. A GitHub commit does not update a previously installed copy. `allow_implicit_invocation: true` helps host selection; it is not a dependency installer or a guarantee of automatic nested-Skill loading. Do not invent a portable `dependencies.skills` mechanism. Bundled relative guides make orchestration independent of nested-Skill discovery.

Official format background (checked 2026-11-03): https://agentskills.io/specification and https://learn.chatgpt.com/docs/build-skills . Test actual host invocation separately from deterministic routing tests.
