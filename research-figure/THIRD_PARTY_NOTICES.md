# Third-party provenance and licensing

RFS-owned orchestration, adapters and documentation remain under the root MIT
license. Neutral internal names identify responsibilities; they do **not** replace
upstream attribution or claim sole authorship of the bundled source.

## Embedded design kernel — Apache-2.0

`kernels/design/` contains a selected, unmodified source snapshot from
https://github.com/douxl-lab/PaperBanana at
`1937a4a6701a76cd01724d359797bb14e2a93e17`, based on
https://github.com/dwzhu-pku/PaperBanana (PaperBanana / PaperVizAgent).
The original `kernels/design/LICENSE` and source copyright notices are retained.
The snapshot includes the host coordinator, provider entrypoints, five-stage
agents, prompts, protocol, configuration templates and style guides. Benchmark
corpora, model weights, website assets, credentials and fonts are not included.
External SDK/model-service dependencies and terms remain separate.

## Embedded layout kernel and library — MIT

`kernels/layout/` contains a selected, unmodified source snapshot from
https://github.com/ChizkiyahuOhayon/CVPR-Figure at
`8adb0d6b881ed0c8643657ccd1b2f43258d4a3d1`. Its original MIT license and copyright
notice are in `kernels/layout/LICENSE`. Included are source renderers/auditors,
16 YAML templates, editable stencils, 19 gallery previews, example specs and
necessary reference/style documents. Gallery images are **design references**,
not our scientific observations or predictions. A repository's license does not
supply additional rights to a paper, logo, dataset or other separately owned
material depicted or referenced within it. Respect file-specific notices and
independent source rights before reuse in a publication.

## Existing canonical protocol — Apache-2.0

`protocol/contract.py`, `interop.py`, `prompt_compiler.py` and the schemas are
previously integrated code from the maintained design upstream. Their Apache-2.0
license is preserved in `protocol/LICENSE-APACHE-2.0`; they are not relicensed as
MIT. This consumer copy and the embedded producer copy are checked for protocol
compatibility. Adaptation code lives outside the preserved source snapshots.

## Optional, not redistributed

The independently authored Matplotlib adapter draws inspiration from
Orchestra-Research/AI-Research-SKILLs academic-plotting; no third-party numeric
results are copied. Sivia-specific material is not bundled and may require a
noncommercial/commercial license check. Editable-Design / paper-fig and its
third-party runtime helpers are not bundled; their notices and runtime terms must
be checked when actually selected. No proprietary fonts or SDK binaries ship here.

## Updates and audit trail

`assets/upstreams.lock.json` is the authoritative, machine-readable revision and
per-file SHA-256 inventory. The revisions above describe the v0.8.0 initial
snapshot; after an update, the lock is authoritative and this notice must be
reviewed. Updates preserve source notices and refuse unreviewed LICENSE changes.
Use the upstream maintenance guide and inspect the commit diff before release.
