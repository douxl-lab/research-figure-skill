# Agent matching and delegated backend selection

The **only portable auto-discovery signals** are `SKILL.md` frontmatter `name` and `description`. The body and this file load **after** activation, so do not place essential trigger conditions only here. `agents/openai.yaml` is optional host/UI metadata, not an alternative Agent Skills specification.

## User intent precedes domain keywords

Use RFS when an actual **scientific figure artifact or figure audit** is requested. Positive intents include a figure-ready model overview, remote-sensing architecture/mechanism schematic, measured-data ablation plot, truthful empirical-image panel, academic figure visual design prompt, candidate comparison/refinement, or editable scientific figure reconstruction. A request may be in English or Chinese.

Do **not** activate solely because a message mentions `科研`, `paper`, `model`, `TikZ`, `Matplotlib`, `PDF` or `PPTX`. If the output is purely a technical explanation, writing/translation, ML hyperparameter help, regular presentation, poster, commercial chart, software unit test, or ordinary LaTeX typesetting, another assistant/tool should handle it.

## Competing Skill precedence (avoid duplicate loops)

1. **RFS-level goal wins:** When the user wants an entire scientific-figure workflow, provenance, multi-backend selection, scientific consistency check, or final figure QA, select `research-figure`. RFS may delegate *one* generation pass to PaperBanana if installed and authorized.
2. **Explicit engine-only request wins:** When the user asks to use `$paperbanana` or PaperBanana **alone** for image generation, a verified candidate bundle, or `vector-handoff` without RFS routing, select `paperbanana`. The user may still opt into RFS acceptance as a separate requested operation.
3. **Explicit other-specialist request wins:** A `$paper-fig`-only reconstruction or ordinary PPT slide task should not start RFS/PaperBanana orchestration unnecessarily.
4. **No requested figure output:** Neither research figure Skill should trigger. A question *about* TikZ or PaperBanana is not a rendering job.
5. **Mixed or ambiguous output:** Identify the concrete user deliverable first. If scientific rendering and unrelated tasks are both requested, route only the scientific-figure part to RFS; do not claim permissions or completed artifacts from another app.

## Inside RFS: route after activation

- Publication-quality creative architecture/mechanism composition → **A**, prompt-only if no authorized callable image provider; PaperBanana if installed/authorized.
- Explicit `TikZ`, source-generating TeX, deterministic formula/timing vector drawing → **T**, canonical v1 diagram only.
- Actual numerical measurements, ablation, training or benchmark CSV → **C**, no synthesizing unknown numbers.
- An approved scientific figure requiring **native editable** PPTX/draw.io → approved-reference three-source reconstruction via a real builder; avoid rerunning image generation.
- An already generated figure needing scientific, visual or native audit → review real bytes/semantics; audit results are not new figures.
- Optical/SAR empirical samples → preserve original image pixels.

Consult [routing](routing.md), [TikZ workflow](tikz-workflow.md) and [canonical exchange](canonical-exchange.md) only for applicable modes.

## Evaluation and claims

`tests/agent_matching_cases.json` contains positive/negative/near-miss **expected labels**, while `tests/skill_selection_pairs.json` distinguishes RFS vs PaperBanana vs neither. The Python selection-contract tests check sample consistency and **real deterministic CLI routing** (prompt-only/TikZ/source plot). They do **not** run an LLM with automatic discovery.

To measure live precision/recall, expose **both installed canonical Skills** to the same host agent, run the labelled prompts without manually naming a skill unless the case requires it, record actual activations and workflow outcomes, then inspect false positives, false negatives and collisions. Do not report a fixture pass count as actual model matching accuracy. Keep scenarios periodically updated with ambiguous bilingual requests and competing installed Skills.
