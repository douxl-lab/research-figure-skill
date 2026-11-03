# Portable host-local image pipeline

Integrated from contributor PR #1. Host reasoning owns source reading, FigureSpec, prompt review and actual-image critique. An explicitly selected image service renders candidates. This replaces the old machine-specific paths/default relay without losing the local workflow.

1. Read the complete relevant source; produce canonical v1 FigureSpec.
2. Validate with `rfs.py validate --spec ...`.
3. Compile an explicit `prompt-only` draft; preserve `figure-spec.json`, `prompt.txt`, `design-intent.md`.
4. Review labels, formulas, references and layout. The exact prompt file bytes used for generation are then recorded, including whitespace.
5. With service/data/cost authorization, use the single-shot adapter below. It does not inspect `.env` or installed-kernel configs, auto-pick a relay from a key, or automatically retry a failed billable call.
6. Inspect the actual saved candidates. Use an independent reviewer when available; never invent a reviewer or equate visual review with scientific validation.
7. Emit a source-bound bundle. Changed prompt/spec/image bytes or missing producer metadata block emission.
8. Write observed design notes from the actual selected image; no prompt-intent text masquerading as image observations.
9. After the user approves that specific reference, produce the native reconstruction handoff and inspect the actual native/exported outputs.

Example project-local service config (replace placeholders; this is not a credential or account guarantee):

```json
{"provider":"YOUR_SERVICE_NAME","model":"YOUR_AVAILABLE_IMAGE_MODEL","base_url":"https://YOUR_SERVICE_HOST/v1","api_key_env":"RFS_IMAGE_API_KEY","image_hosts":[]}
```

`image_hosts` is an explicit allowlist only for providers returning HTTPS image URLs; base64 needs no host entry. Redirects are not followed. An HTTP loopback endpoint additionally requires `allow_http_loopback: true`. Keys live in the explicitly named environment variable; never in committed source, job metadata or prompt text. Model identity is recorded as requested configuration unless the service actually reports a model.

```bash
python /installed/research-figure/scripts/generate_from_prompt.py --prompt /project/job/prompt.txt --spec /project/job/figure-spec.json --config /project/image-provider.json --out /project/job/candidates --candidates 2 --allow-external
python /installed/research-figure/scripts/emit_bundle.py --dir /project/job --candidate 1
python /installed/research-figure/scripts/rfs.py reconstruction-package --spec /project/job/figure-spec.json --bundle /project/job/bundle --design-notes /project/job/observed-design-notes.md --approved --backend paper-fig --out /project/job/native-handoff
```

Pass `--approved` only for an actual approval. By default the metadata sidecar is in `candidates/`, exactly where the generator writes it; one historical root-level sidecar is supported if unambiguous and fully bound. `--metadata` resolves ambiguity explicitly. No output directory is overwritten. Metadata and candidates remain archived even after partial failure; partial generation returns failure, not blanket success.

`image2api_smoke.py` is retained as a compatibility entry to the same guarded adapter. It requires the same explicit source/config/output/authorization arguments and performs a real potentially paid call; `doctor` never calls it silently.
