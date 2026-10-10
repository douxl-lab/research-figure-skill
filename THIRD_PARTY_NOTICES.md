# Third-party projects and license boundaries

This skill is an original orchestration package. The only intentionally vendored upstream code is the separately Apache-licensed PaperBanana FigureSpec v1 protocol identified below. It does not bundle third-party models, paid SDKs, fonts, scientific image datasets, Sivia or paper-fig runtime assets.

- **PaperBanana** — https://github.com/dwzhu-pku/PaperBanana — repository reports Apache-2.0; its `skill/SKILL.md` separately advertises MIT-0. Recheck relevant file-specific rights at integration time. External model provider API terms also apply.
- **Orchestra-Research / academic-plotting** — https://github.com/Orchestra-Research/AI-Research-SKILLs/tree/main/20-ml-paper-writing/academic-plotting — Skill lists MIT. The present plotting script is independently written and uses normal Matplotlib APIs.
- **Sivia** — https://github.com/exsinger-hub/Sivia — license for current Sivia-authored material is `LicenseRef-Sivia-NonCommercial-1.0` (effective 2026-09-20). Personal learning and non-commercial academic research are permitted; commercial use requires separate written authorization. The package does not copy or redistribute Sivia-specific content.
- **Editable-Design / paper-fig** — https://github.com/yejy53/Editable-Design/tree/main/skills/paper-fig — repo's own code is Apache-2.0, but `skills/paper-fig/NOTICE.md` explains that some inherited helper scripts have third-party copyrights and are not relicensed by the repository. `@oai/artifact-tool` is external and is not bundled.

Generated artifacts incorporating third-party figures, imagery, datasets, fonts, or templates remain subject to their licenses. The fact that a user can access a repository does not authorize copying it into a new public Skill. Source repositories and their licenses can change; verify again before redistribution or commercial release.

## Vendored canonical FigureSpec v1 protocol

`research-figure/protocol/contract.py`, `interop.py`, `prompt_compiler.py`, both canonical JSON schemas, and `research-figure/protocol/LICENSE-APACHE-2.0` are preserved from [douxl-lab/PaperBanana](https://github.com/douxl-lab/PaperBanana), originally based on PaperBanana / PaperVizAgent. This component remains licensed under Apache License 2.0 and is **not** relicensed as MIT by this repository. Any modifications will be explicitly attributed in the source files. See the copy of the upstream license under `protocol/`.