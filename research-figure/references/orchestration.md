# Unified kernel orchestration

## Public workflow contract

`research-figure` is the only ordinary Skill entry. Internal capabilities are `design`, `image-generation`, `hybrid-assembly`, `layout`, `vector`, `plot`, `reconstruction` and `audit`. Complete-image generation and hybrid assembly are both core production workflows; only the former is the default. Users should describe the figure, not list implementation brands. The design/layout code, local template specs, gallery and export/audit scripts are installed with the Skill. Original project names remain in provenance, licenses and deprecated compatibility aliases; renaming our interface is not claiming authorship of upstream code.

## Task flow

A new creative mechanism/architecture request automatically reads `design-core.md` and `layout-library.md`, inspects source/code, selects local references and executes the available design route. The fixed five stages run once. In image-first mode, the Visualizer produces the complete mechanism figure. In hybrid-assembly mode, the host codes and inspects the scaffold first, the Visualizer produces scoped assets, and code composes them into that scaffold. Reuse the design sequence rather than adding another competing planner. Formula-free visual explanations are normal; minimal labels, meaningful glyphs and clear flow outrank code-native editability. Host reasoning can perform the text stages; the actual image tool must perform the Visualizer stage. Explicit measured plots and TikZ bypass generation. An approved-reference reconstruction or small correction bypasses new concept design.

`workflow.py` resolves bundled kernels by default. Explicit `RFS_DESIGN_ROOT` / `RFS_LAYOUT_ROOT` override them; invalid overrides fail rather than silently using another runtime. Old `PAPERBANANA_ROOT` / `CVPR_FIGURE_ROOT` and old mode flags remain migration aliases. Hosts report actual tools; script discovery cannot prove a model is installed or an API is authorized.

Default mode order: native design with available host image tool → labelled host workflow if the local coordinator is unavailable → explicitly configured and authorized `image2-api` installation → authorized provider design. Both image routes are generative, not SVG assembly. `image2-api` is an optional external runtime, not part of the bundled kernels. Explicit `llm-svg` delegates SVG code authoring to the host without an image API; it is never an automatic fallback. Explicit authorized provider choice wins. No generator means `BLOCKED`, not a completed prompt or unannounced box diagram. Existing task/service authorization need not be requested again; keys alone never establish it. No automatic retry after a potentially billable failure.

## Core hybrid assembly dispatch

Explicit `--mode hybrid-assembly` overrides the image-first default. The host should select it for natural-language requests such as “先用代码搭骨架，再让模型补素材” or an agreed need for fixed labels/connections and reusable artwork; no backend brand or formula requirement is necessary. It requires canonical `kind: diagram` and an actual host image tool or an explicitly configured, authorized image2-api installation for its asset stage. Missing capabilities block the route instead of silently changing strategy. FigureSpec `kind: hybrid` retains its existing source-preserving handoff; it is not this production-mode selector.

`run` validates and snapshots the source, then writes `hybrid-job.json` with scaffold, assets, composition and review tasks, all pending. Continue those tasks with actual host code/image tools and the existing layout renderer when appropriate. The preparation result is `HOST_ACTION_REQUIRED`, never a rendered scaffold or generated figure. Model generation is limited to the asset stage; code owns global topology, exact labels and final composition. Full instructions are in the core hybrid section of the production SOP.

## Completion

`run` returning `HOST_ACTION_REQUIRED` means the host must continue the coordinator. Native receipts are local attestations, not signatures; prompt intent is not evidence of exact provider submission when a tool hides its prompt. Real image bytes and science remain separately reviewed. A host tool may end the turn; later review is then pending, never fabricated.

The local single-shot route, bound bundle emitter and complete-image production SOP remain available. They are not a machine-specific override of the portable default. Unknown native editor availability or licensing stays a blocker. A partially rasterized presentation is labelled partial editability, not fully editable.

Read `upstream-maintenance.md` for dependency updates. Installation includes code/assets, not model credentials, SDKs, system converters or proprietary editors. A metadata setting such as implicit invocation helps selection; it does not guarantee host behavior. Offline dispatch tests are not a live host invocation benchmark.

## image2-api execution boundary

`workflow.py plan --mode image2-api --image2-root /installed/image2-api --spec /project/F01.json --dry-run` plans offline. For `run`, also supply `--image2-config`, reviewed `--prompt` and a fresh `--out`. Use `--allow-external` instead of `--dry-run` only under applicable service/data/cost authorization. `--dry-run` is rejected for other modes so it cannot accidentally trigger another backend. Full generation/edit controls are exposed by `image2_adapter.py`; references, masks and output preferences are described in `local-image-pipeline.md`.

`llm-svg` returns `HOST_ACTION_REQUIRED`. The host must actually author the source, render and inspect the result before claiming completion. An API raster wrapped in SVG is not an editable vector reconstruction.
