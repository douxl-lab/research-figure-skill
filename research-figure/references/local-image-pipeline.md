# Image-model-first local pipeline

The host LLM reads the source, writes the visual brief, selects references and reviews actual results. The image model generates the **complete mechanism figure** and performs targeted edits. PNG is the normal deliverable. SVG is an explicit host-code task, not a default paid image-API format.

A real exposed host image tool remains the preferred route. The optional bridge below uses the separately installed [image2-api](https://github.com/techdou/image2-api) CLI; this runtime is not bundled, automatically installed or automatically updated. The reviewed CLI contract is commit `d4cdbc64bc77c395a4aa5c8928f116a4722f038d`. A compatible newer installation may work, but the bridge records its entry-script hash and checks request/output contracts; that is not full runtime attestation or proof of live service access.

## Responsibilities

RFS owns source fidelity, mechanism-focused prompting, candidate review, edit instructions and publication checks. image2-api owns the configured image request and response handling. Do not launch a second Retriever/Planner/Stylist loop or replace RFS's rules with another Skill's top-level policy. The service can be an authorized official API or a user-configured compatible relay. A provider model alias is not independently verified model identity.

Use the current local image2-api installation and its dependencies in the same Python interpreter. No network or model call is needed to author prompts or plan a job. The adapter deliberately uses a project-local explicit service config rather than searching other installed Skills for credentials.

## Project configuration

Store this **outside both repositories and installed Skills**; replace the placeholders and set the named environment variable in the execution environment:

```json
{
  "provider": "YOUR_AUTHORIZED_SERVICE",
  "base_url": "https://YOUR_SERVICE_HOST/v1",
  "model": "YOUR_AVAILABLE_IMAGE_MODEL",
  "model_family": "auto",
  "api_key_env": "RFS_IMAGE_API_KEY"
}
```

The base is an API prefix, not `/images/generations` or `/images/edits`. Use image2-api's corresponding model family for a relay alias. No hard-coded model upgrade is performed. Credentials are never CLI arguments or metadata fields. HTTPS is required; an explicitly configured loopback HTTP service also needs `allow_http_loopback: true`.

The adapter freezes provider/model/endpoints, disables image2-api's configured provider chain, sets retries to zero and preserves intermediate records. It does not call `doctor --probe`, discover a key in `.env`, switch providers or automatically rerun a timed-out paid call. Installed service settings do not by themselves authorize disclosure of a private manuscript. Existing applicable task/service authorization need not be requested again.

The image2 runtime still owns HTTP transport, downloads and its dependencies; its current implementation can follow redirects. The adapter's endpoint validation is not an egress sandbox. Use a trusted, reviewed runtime and service; do not equate an entry-script hash with full dependency integrity.

## Generate a complete figure

Prepare canonical FigureSpec v1 and a reviewed UTF-8 visual prompt using `prompt-system.md`. Keep the prompt visual and concise: the scientific point, invariant topology, exact label whitelist, meaningful glyphs, composition and explicit constraints. Do not manufacture equations for a formula-free mechanism.

```bash
RFS=/installed/research-figure
IMAGE2=/installed/image2-api

# Offline validation. No key or permission to spend is needed.
python "$RFS/scripts/image2_adapter.py" \
  --spec /project/F01.json --prompt /project/F01-prompt.txt \
  --image2-root "$IMAGE2" --config /project/image-provider.json \
  --size 1536x1024 --out /project/figures/F01-check --dry-run

# Real generation, only with applicable service/data/cost authorization.
# Use a NEW output directory, not the dry-run directory.
python "$RFS/scripts/image2_adapter.py" \
  --spec /project/F01.json --prompt /project/F01-prompt.txt \
  --image2-root "$IMAGE2" --config /project/image-provider.json \
  --size 1536x1024 --candidates 2 --out /project/figures/F01-v1 --allow-external
```

Choose size/aspect ratio for the actual composition and provider, not a compulsory square canvas. The default is `size=auto`, `quality=high`, one PNG. Provider capabilities still apply. PNG/WebP support requesting transparency, but the bridge checks actual alpha pixels and records a warning when the result is opaque. Do not erase white pixels indiscriminately: they may be meaningful objects.

The unified workflow also supports `--mode image2-api --image2-root ... --image2-config ... --prompt ...`. `plan` never invokes the runtime; `run --dry-run` validates the external request without generating. Real `run` needs `--allow-external`. The direct adapter exposes the full image-edit and format controls.

## Reference-guided generation and local edits

When references are needed, image2-api's image-edit endpoint receives the images. For a repair, the **first `--image` is the selected candidate**; additional images supply explicitly described references. A reference image is not itself a segmentation mask.

```bash
python "$RFS/scripts/image2_adapter.py" \
  --spec /project/F01.json --prompt /project/F01-edit.txt \
  --image2-root "$IMAGE2" --config /project/image-provider.json \
  --image /project/figures/F01-v1/candidate-1.png \
  --mask /project/F01-edit-mask.png \
  --out /project/figures/F01-v2 --allow-external
```

Omit `--mask` for an unmasked edit. A mask is a PNG with alpha, the same dimensions as the first image, and transparent pixels in the editable area. The actual service must support masks. Use **change / preserve / acceptance check** in the prompt; inspect the entire result because a localized request is not a pixel-preservation guarantee. Every run snapshots input images and preserves the previous candidate.

## Records and completion

The job preserves `figure-spec.json`, `prompt-source.txt`, actual request prompt `prompt.txt`, `design-intent.md`, reference snapshots, candidates, provider-local request records and `generation-metadata.json`. Some runtimes normalize surrounding whitespace: the adapter accepts only identity or outer-whitespace trimming, records both hashes, and rejects unexpected rewriting. Do not claim an undisclosed internal provider prompt rewrite is observable.

`DRY_RUN_VALID_NOT_GENERATED` is offline validation only. `GENERATED_UNREVIEWED` means the returned bytes were inspected for format/size, not that science or visual design has passed. `FAILED_OR_UNKNOWN` preserves local records; inspect before any manual retry. Missing or mismatched output files cannot become successful provenance.

For an optional later reconstruction, the source-bound records can enter the existing bundle emitter:

```bash
python "$RFS/scripts/emit_bundle.py" --dir /project/figures/F01-v1 --candidate 1
```

A bundle is not approval. Observe the selected image before writing design notes. Native reconstruction requires actual approval of that image and verification of real editable objects/exported results; it is not the default next step after PNG generation.

## Existing direct adapter compatibility

`generate_from_prompt.py` and the `image2api_smoke.py` compatibility entry remain available for the older single-shot SDK route. They use the same explicit project-local service/data/cost boundary, require real source/prompt/config/output arguments, and never run silently from `doctor`. The new `image2_adapter.py` adds reference-image edits via the separate image2-api runtime; it does not rename the old adapter or pretend it already used this dependency.
