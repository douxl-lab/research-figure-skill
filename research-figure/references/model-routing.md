# Image model selection and maintenance (2026-10-09 registry snapshot)

**Objective:** make Route A prompts model-aware without overfitting the scientific truth to a model. The user's FigureSpec always controls exact modules, labels, and directed connections. The selected reference image and approved written design notes control the eventual editable reconstruction. Do not apply this registry to quantitative plots.

## Model roles — curated suggestions, not rankings

| Task priority | OpenAI candidate | Google candidate |
|---|---|---|
| Fast multiple candidates | `gpt-image-2.5-flare` | `gemini-nano-banana-2.1` |
| Balanced creation | `gpt-image-2.5-flare` | `gemini-nano-banana-2.1` |
| Complex academic overview | `gpt-image-2.5-sunburst` | `gemini-3-pro-image` |
| Precise local edit | `gpt-image-2.5-sunburst` | `gemini-3-pro-image` |

These are practical **starting candidates** based on published model descriptions, *not* tested scientific diagram benchmarks. A newer or more expensive model does not automatically produce more correct diagrams. Evaluate exact node/edge reproduction, legible text, rerender consistency, and editing locality on actual RFS cases.

## How selection works

1. Check accessible image model/provider in the actual host. The CLI cannot authenticate or discover entitlement.
2. For an architecture figure, choose `--model <exact-id>` when known, or `--model auto --provider openai|gemini --priority speed|balanced|quality|precise_edit`. Omitting `--model` preserves the legacy broad `--profile` behavior.
3. Compile six-layer prompt + model-specific guidance. Inspect `model-call-plan.json` for *parameter hints* and `prompt-receipt.json` for selected model and registry SHA256. **Neither is a live API request.**
4. Submit the prompt and real image(s) to the host/provider only with user authorization for unpublished text. Validate supported size/quality/thinking/reference-image arguments from current official docs; never pass unverified fields merely because they exist in the local JSON.
5. Save actual observed model ID, API/provider, model snapshot where known, prompt, settings and generated image. Compare/refine; re-open the output to check science against FigureSpec.
6. When making PPTX/draw.io, use visual reference + FigureSpec + observed written guidance; model-specific prompt content is a source artifact, not proof of editability.

## Commands

```bash
python scripts/rfs.py models --provider gemini --priority quality
python scripts/rfs.py models --provider openai --priority precise_edit --stage refine
python scripts/rfs.py prompt --spec /PROJECT/F01.json --model auto --provider gemini --priority balanced --out /PROJECT/F01/draft
python scripts/rfs.py prompt --spec /PROJECT/F01.json --model gpt-image-2.5-sunburst --stage refine \
  --reference /PROJECT/F01/approved.png --region Router --change 'Untangle outgoing connector only' --out /PROJECT/F01/refine
```

## Updating to future models without rewriting code

`assets/prompts/model-registry.json` is data. Copy it to your own project directory; update `verified_at`, the model entry/capabilities, `default_candidates`, and official source URLs. Then pass `--model-registry /PROJECT/registry.json`. The new ID can immediately be used as long as it declares an existing `prompt_profile` (`gemini`, `gpt-image`, or `generic`). Implement and test a new profile only when a new model needs materially different prompting. Do not introduce a new model ID based solely on an unverified blog post.

Model releases are **not** automatically downloaded or polled. Built-in recommendations are dated snapshots. Host operators should check the vendor docs before each major model upgrade or production use. Avoid silently switching `latest` aliases during scientific reproduction; prefer resolved model IDs and, when available, fixed versions.

## PaperBanana compatibility boundary

PaperBanana is a separate executor with its own provider SDK, model router and model defaults. `--model` only selects RFS **direct image prompt compilation**. `--paperbanana-image-model <id>` is an **explicit upstream override** for `rfs.py run --engine paperbanana --allow-external` and may fail if the installed PaperBanana version/provider lacks support. RFS reports known retired preview IDs before issuing any paid calls; update or test the upstream environment before relying on it. Never claim that a new model works in PaperBanana without a real upstream integration test.

## Official references checked on October 9, 2026

- OpenAI image models and endpoints: https://developers.openai.com/api/docs/guides/image-generation
- OpenAI model/parameter API: https://developers.openai.com/api/reference/resources/images/methods/generate
- Google Nano Banana 2.1: https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1
- Google Pro Image: https://ai.google.dev/gemini-api/docs/models/gemini-3-pro-image
- Google image generation details: https://ai.google.dev/gemini-api/docs/image-generation
- Google deprecations: https://ai.google.dev/gemini-api/docs/deprecations
