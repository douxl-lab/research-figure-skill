# PaperBanana: proactive delegated execution

Load for every new scientific mechanism/architecture image, even when the user says only “用 research-figure 画机制图”. This is RFS's delegated design stage, not a second top-level task. The source snapshot is recorded in `assets/capabilities.json`.

## Native host first

A compatible checkout exposes `skill/native_host.py`; it coordinates existing host reasoning, vision and image tools without reading an external provider key. The runner still needs Python 3.10+ and PaperBanana's exchange requirements (`jsonschema`, Pillow). Do not run with Python optimization (`-O`). The host must inspect the actual installed tool schema; upstream tool names/arguments are hints, not permission to invent unsupported calls.

`workflow.py run` performs `prepare` and `next`. Continue from that returned task:

```bash
python "$PAPERBANANA_ROOT/skill/native_host.py" next --job /project/figures/F01/native-job
python "$PAPERBANANA_ROOT/skill/native_host.py" record --job /project/figures/F01/native-job --stage Retriever --artifact /project/retriever.json --task-id ACTUAL_TASK_ID
```

Use the actual returned task/tool ID, or the upstream-supported `tool-managed-not-reported` when the platform exposes none. Never invent an ID. In fixed order:

| Stage | Required actual work | Successful stage JSON |
| --- | --- | --- |
| Retriever | Inspect the supplied science and selected CVPR visual references | `status: succeeded`, `observations`, `source_paths` |
| Planner | Plan a composition preserving nodes, arrows, labels and evidence | `status: succeeded`, `design_description` |
| Stylist | Prepare exact visual instructions; keep source evidence immutable | `status: succeeded`, `prompt`, `design_description`; optional bound reference paths |
| Visualizer | Call the real host image tool; preserve its returned image bytes | Record the actual PNG and prompt hash returned by `next` |
| Critic | Open the generated image and compare science, legibility and design | `status: succeeded`, `image_sha256`, `verdict: accept|revise`, `observed_scientific_fidelity`, `aesthetics`, `issues` |

```bash
python "$PAPERBANANA_ROOT/skill/native_host.py" record --job /project/figures/F01/native-job --stage Visualizer --artifact /project/generated.png --task-id ACTUAL_IMAGE_CALL_ID --prompt-sha256 HASH_FROM_NEXT
python "$PAPERBANANA_ROOT/skill/native_host.py" verify --job /project/figures/F01/native-job
```

Run `next` after each recorded stage; do not synthesize receipts in advance. If the host does not expose exact prompt submission, do not misrepresent a locally planned prompt hash as provider-verified submission. Native receipts are local attestations, not platform signatures. A native job is **not** a provider exchange bundle; do not pass it to `verify-bundle`, `vector-handoff` or canonical `reconstruction-package --bundle` without an actual compatible export. Native-to-editable handoff remains explicitly pending until its source/image contract is supported by the selected builder.

For repairs, preserve the original bytes, bounded target IDs and protected science, use the engine's `repair` operation, and execute Visualizer/Critic again. Do not start another outer five-stage chain.

## Authorized provider route

Use `workflow.py run --mode paperbanana-provider --allow-external ...` only with valid task/service-specific disclosure and cost authorization. Existing RFS `bridge.py` verifies the Exchange v1 descriptor before `skill/exchange.py run`. Keep its schema/hash checks; do not bypass a failed handshake by sending prose. A timeout may have incurred cost: do not automatically retry or switch providers.

## Self-contained host fallback

When no compatible checkout exists but the host image tool is real, the bundled workflow still supplies the five stage responsibilities above. Perform them in the host (sequential roles are acceptable; do not claim independent subagents unless actually used), keep the exact FigureSpec and real image bytes, and record stage completion in the project output. Label execution **bundled-host-workflow**, with `upstream_runtime_executed: false`; do not fabricate native-host `verify` output or an Exchange bundle. This is an independently authored fallback based on the five-stage responsibility split, not a claim that copied instructions installed PaperBanana.

If image generation or review cannot execute, report the blocker or pending stage. Prompt-only is a valid final deliverable only when the user requested a prompt. Host/system safety and image-tool constraints always take precedence.
