# Canonical RFS / PaperBanana exchange v1

The contract for new research figures is defined by `protocol/contract.py`, `protocol/schemas/figure-spec-v1.schema.json` and `protocol/schemas/manifest-v1.schema.json`. Those files are mirrored unmodified from the paired PaperBanana Fork. Both sides expose the protocol descriptor and must match version, schema and validator fingerprints; use fail-closed negotiation. Schema v0.1 input is supported only by the legacy CLI path and is not accepted as a canonical request.

RFS route A: original scientific sources → canonical v1 FigureSpec → PaperBanana request with original source and strict checksum → five agents → verified response bundle (image, exact selected-stage prompt, design text, canonical scientific structure) → actual-image inspection and observed notes → optional editable native builder. Never treat the planned design description alone as observed visual quality. If the image or scientific topology changes, require re-review.

RFS route C: preserve a single entire verified v1 dataset for the deterministic Matplotlib backend, refuse implicit aggregations, unknown columns, unsupported plot types, and invented uncertainty. Split hybrid representations instead of allowing an image model to draw empirical charts.

Offline request creation, prompt compilation, source verification and bundle inspection do not trigger paid model calls. External provider generation requires `--allow-external`; check user rights to unpublished material and possible fees before using it. A timeout is not evidence that a provider did not charge for generation.

Bundle acceptance compares actual bytes and exact original scientific fingerprint. Both providers may create an attractive but scientifically incorrect figure, so visual/semantic QA remains PENDING until independently verified. An accepted bundle is not an editable PPTX/draw.io file.