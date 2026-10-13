**Canonical routing:** FigureSpec Exchange v1 diagrams default to PaperBanana when explicitly authorized and protocol-paired, otherwise to prompt-only. The new **explicit** `--engine tikz` route builds local, source-preserving vector diagrams without any model/API call. It does not automatically replace creative diagrams or attempt to reproduce a PaperBanana image pixel for pixel. Canonical v1 numerical plots always use the original data; hybrids remain split. Do not route a canonical complex diagram to legacy SVG automatically. See [TikZ workflow](tikz-workflow.md) and [canonical-exchange](canonical-exchange.md). Below: legacy v0.1 routing detail.

# FigureRouter: A/C 双主路线，B 按需使用

## Decision precedence

1. If actual experimental values, axes or error bars are involved, use **C / `plot-matplotlib`** from source data. Do not use an image generator for numeric artwork. Unknown measurements remain missing.
2. If the user provides an approved reference and asks for editable files, skip generative creation. Use the **three-source reconstruction package** and a native builder.
3. For research method diagrams, model architecture and overviews, default to **A / creative** with a binding exact node/edge contract. Accurate science does **not** imply `generation.intent=exact`; this flag means the user specifically wants a structure-first, simple native diagram.
4. Only when explicitly requested or scientifically suited, use **B / native SVG**. Complex topologies, aesthetic refinement, long edge crossings and node crowding are warnings that deterministic layout may look poor.
5. For measured imagery panels, preserve original input pixels. Any synthetic asset must remain clearly separated from empirical evidence.

## CLI routing states

| Condition | CLI `route` | Consequence |
|---|---|---|
| Creative overview; no authorized configured PaperBanana | `prompt-only` | Generate provider-adapted prompt + design brief; *host must actually generate image* |
| Creative overview; user authorized model submission; configured PaperBanana ready | `paperbanana` | Run upstream 5-agent generator, preserve candidate PNGs, later review |
| `generation.intent=exact` or explicit `--engine native-svg` | `native-svg` | Structural draft; if creative was requested report degraded visual goal |
| `type=quantitative` | `plot-matplotlib` | Source CSV only; measured-data verification separate |
| `type=editable_reconstruction` / `evidence_panel` | `handoff` | No pretend local PPTX engine |

## Do not confuse these roles

- A **creative draft** chooses composition. FigureSpec governs scientific correctness. The image is a *visual reference*, not evidence that arrows/text are correct.
- **Candidate review** checks science and visual grammar. PaperBanana may already have a Critic; reuse its internal candidate iteration, do not wrap it with a duplicate planner/critic swarm. RFS's independent final FigureGuard audits *different* properties (evidence and native file) and is not redundant.
- **Native reconstruction** reproduces selected composition with FigureSpec and written details; native backend does not get permission to reimagine the design.

## External permissions and fallback

- Before exporting unpublished methods to an external provider, confirm user permission for the specific service, material and potential cost. Presence of an API key or `--allow-external` does not itself constitute consent.
- If a provider is unavailable, prefer a **prompt-ready** handoff to another capable host image tool over a low-quality SVG replacement; fail clearly when no host can actually create the user-requested image.
- If a specific backend was requested and it is unavailable, report `NOT_EXECUTED` / `PENDING`. Do not silently switch backends or formats.

## Decision summary

```
SCIENTIFIC SOURCES -> FigureSpec
  -> numeric facts?        -> C: code plots -> source provenance & publication audit
  -> selected reference?   -> three-source editable reconstruction -> actual native render audit
  -> complex method?       -> A: adapt prompt -> generative image candidates -> design lock
  -> simple exact layout?  -> B: native structural drawing, if explicitly chosen
```