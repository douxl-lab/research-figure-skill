#!/usr/bin/env python
"""emit_bundle.py — ZCode 本机生图链的 bundle 发射器（RFS canonical v1）.

把 ZCode 编排流程的既有产物（figure-spec.json / 选中 candidate PNG / prompt.txt /
design-intent.md / generation-metadata.json）组装成 PaperBanana Exchange v1 协议的
合法 result bundle，并当场用 interop.verify_result 自验。产出目录可直接传给
`rfs.py reconstruction-package --bundle`。

所有 payload 均为流程真实产物，本脚本只生成协议回执（manifest.json）——这是
producer 侧的合法 emit，不是仿造。

用法（在 ~/.agents/skills/research-figure/scripts 下）:
  python emit_bundle.py --dir <产物目录> --candidate 2 [--out <bundle目录>]
  产物目录须含: figure-spec.json, prompt.txt, design-intent.md,
                candidates/candidate-<N>.png, generation-metadata.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import _api  # noqa: E402

contract, interop, _ = _api()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble a canonical v1 result bundle from ZCode pipeline artifacts")
    ap.add_argument("--dir", required=True, help="ZCode 流程产物目录")
    ap.add_argument("--candidate", type=int, required=True, help="选中的 candidate 编号（经第 6 步视觉评审后）")
    ap.add_argument("--out", help="bundle 输出目录（默认 <dir>/bundle）")
    args = ap.parse_args()

    src = Path(args.dir).expanduser().resolve()
    spec_path = src / "figure-spec.json"
    prompt_path = src / "prompt.txt"
    design_path = src / "design-intent.md"
    image_path = src / "candidates" / f"candidate-{args.candidate}.png"
    meta_path = src / "generation-metadata.json"
    for p in (spec_path, prompt_path, design_path, image_path, meta_path):
        if not p.is_file():
            print(f"FAIL: missing artifact {p}")
            return 1

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != "1.0.0":
        print("FAIL: figure-spec.json is not canonical v1 (schema_version != 1.0.0)")
        return 1

    # Provenance honesty (pi review 2026-11-01): metadata is REQUIRED and its
    # provider/model fields are used verbatim — no default fabrications.
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not meta.get("provider") or not meta.get("model"):
        print("FAIL: generation-metadata.json must contain real provider and model fields")
        return 1

    out = Path(args.out).expanduser().resolve() if args.out else src / "bundle"
    if out.exists():
        print(f"FAIL: {out} already exists; remove it or pass --out")
        return 1
    (out / "candidates").mkdir(parents=True)
    files = {
        "figure-spec.json": spec_path,
        "prompt.txt": prompt_path,
        "design-intent.md": design_path,
        "candidates/candidate-%d.png" % args.candidate: image_path,
    }
    entries = {}
    for rel, origin in files.items():
        shutil.copyfile(origin, out / rel)
        raw = (out / rel).read_bytes()
        mime = "image/png" if rel.endswith(".png") else (
            "application/json" if rel.endswith(".json") else (
                "text/markdown" if rel.endswith(".md") else "text/plain"))
        entries["figure_spec" if rel == "figure-spec.json" else
                "image" if rel.endswith(".png") else
                "prompt" if rel == "prompt.txt" else "design"] = {
            "path": rel, "sha256": _sha(raw), "bytes": len(raw), "mime": mime}

    manifest = {
        "schema_version": "1.0.0",
        "candidate_id": "zcode-candidate-%d" % args.candidate,
        "status": "succeeded",
        "stage": "final",
        "provider": meta["provider"],
        "model": meta["model"],
        "description_key": "candidate-%d" % args.candidate,
        "options": {k: meta.get(k) for k in ("size", "quality", "candidates") if meta.get(k)},
        "provenance": {
            "scientific_verification": spec["provenance"]["scientific_verification"],
            "external_consumer_verified": False,
            "editable_reconstruction_verified": False,
            "image_bytes_preserved": True,
            "generation": {
                "pipeline": meta.get("pipeline", "zcode-local"),
                "generated_at": meta.get("generated_at"),
                "candidates_requested": meta.get("candidates"),
                "visual_review": meta.get("visual_review",
                    "not performed (bundle emitted before visual review)"),
            },
        },
        "scientific_fingerprint": contract.scientific_fingerprint(spec),
        "review": [],
        "review_status": "pending-user-approval",
        "error": None,
        "files": entries,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 协议自验：不过就整体失败，绝不交付半成品 bundle
    try:
        _, actual, _ = interop.verify_result(out, spec)
        assert actual is not None and actual["kind"] == "diagram"
    except Exception as exc:
        print(f"FAIL: bundle rejected by protocol verify_result: {exc}")
        shutil.rmtree(out)
        return 1

    print(json.dumps({"status": "emitted", "bundle": str(out),
                      "fingerprint": manifest["scientific_fingerprint"],
                      "next": "rfs.py reconstruction-package --spec <spec> --bundle %s --design-notes <notes.md> --out <pkg>" % out},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
