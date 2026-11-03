# Internal capability map

| ID | Responsibility | Implementation |
| --- | --- | --- |
| design | One source-grounded five-stage visual-design chain | Bundled `kernels/design`, host tools or authorized provider |
| layout | Local reference/template/gallery search; native vector export and file audits | Bundled `kernels/layout` |
| vector | Explicit precise mathematical/vector work | RFS TikZ adapter; separate system compiler |
| plot | Real measured data and reproducible plots | RFS Matplotlib adapter; separate library dependency |
| reconstruction | Approved-reference native editing | Bundled handoff/QA; selected external editor when needed |
| audit | Sources, hashes, scientific/visual review and actual native objects | RFS checks plus bundled layout auditors |

`assets/capabilities.json` is the module registry. `assets/upstreams.lock.json` identifies provenance, licenses and pinned file bytes for copied upstream components. No runtime requires another Skill to be discovered by its author's name. External image models and native editors are not falsely advertised as embedded.
