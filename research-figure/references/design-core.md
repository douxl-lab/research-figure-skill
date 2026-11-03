# Design core

The code is bundled in `kernels/design/`. Use `scripts/kernel.py design` rather than asking the user to invoke a separate named Skill. Sources/rights/revisions are in `THIRD_PARTY_NOTICES.md` and `assets/upstreams.lock.json`. Do not edit the upstream snapshot in place; adapt it through RFS scripts.

## Native execution

Dependencies: Python 3.10+, jsonschema and Pillow. `workflow.py run` prepares a fresh canonical v1 job and returns the first task. Continue:

```bash
python /installed/research-figure/scripts/kernel.py design next --job /project/job/native-job
python /installed/research-figure/scripts/kernel.py design record --job /project/job/native-job --stage Retriever --artifact /project/retrieval.json --task-id ACTUAL_TASK_ID
```

Five stages, once:

| Stage | Actual work | Required successful JSON |
| --- | --- | --- |
| Retriever | Inspect science plus local reference templates/previews | `status: succeeded`, `observations`, `source_paths` |
| Planner | Lay out exact nodes, arrows, labels and evidence | `status: succeeded`, `design_description` |
| Stylist | Prepare visual instructions and bound references | `status: succeeded`, `prompt`, `design_description`; optional `referenced_image_paths` |
| Visualizer | Invoke the real available image tool | Record actual PNG bytes, actual tool ID and coordinator prompt hash |
| Critic | Open actual generated image and inspect it | `status: succeeded`, `image_sha256`, `verdict: accept|revise`, `observed_scientific_fidelity`, `aesthetics`, `issues` |

Use the actual tool/task ID; `tool-managed-not-reported` is allowed only when the platform does not expose one. Call `next` after each recorded stage. A tool hint from the coordinator must be adapted to the actual host schema; never invent unsupported image-tool parameters or substitute a synthetic fixture. If exact prompt submission cannot be observed, do not claim a planned hash proves it. Respect host restrictions on reference images and final responses.

```bash
python /installed/research-figure/scripts/kernel.py design record --job /project/job/native-job --stage Visualizer --artifact /project/real-image.png --task-id ACTUAL_IMAGE_CALL_ID --prompt-sha256 HASH_FROM_NEXT
python /installed/research-figure/scripts/kernel.py design verify --job /project/job/native-job
```

`ACCEPTED` is the recorded critic verdict, not scientific truth or publication acceptance. `REVISION_REQUIRED` is not completion. Repairs preserve original image bytes and protect unaffected science; use the coordinator's bounded `repair`, then rerun Visualizer/Critic only. Do not use Python `-O`: upstream validation explicitly rejects it.

## Provider and single-shot modes

`workflow.py run --mode design-provider --allow-external` invokes the embedded Exchange boundary and five-stage provider engine only with actual authorization and its separately installed SDK requirements. Protocol checks precede calls; retrieval/dataset downloads are disabled in the canonical request. No credentials belong inside a bundled kernel.

For host-led text stages with a configured image relay, use `local-image-pipeline.md`. This performs one image call per requested candidate and exports provenance-bound results; it does not impersonate the full provider pipeline. Native coordinator jobs are not automatically provider Exchange bundles. Keep either representation's integrity semantics explicit when handing off to a native editor.

## Selectively adapted original upstream improvements

The embedded CLI supports `--figure-size` (passed through to the configured provider's image-size tier) and `--work-dir` (an external work/cache location). The reference preparation path now supports the original dataset's Parquet layout and writes an atomic per-task `data/PaperBananaBench/` tree **outside this Skill**. This is an **optional runtime path**, not an automatic download on native-host `prepare` or when `--retrieval-setting none` / `--offline` is selected. The Parquet path requires `huggingface_hub` and `pyarrow` when used. Dataset images are visual references, not the user's empirical data. The complete original upstream has not been wholesale merged; provenance and the selected topics are in the upstream lock.
