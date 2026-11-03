"""Generate one or more candidate figures from a prompt file.

This is the ZCode-orchestrated single-shot image entry for PaperBanana: the
text side (planning, prompt review, visual critique) is done by the host
agent, and this script only renders. Reads the repo-local .env
(OPENAI_API_KEY) and configs/model_config.yaml (relay base_url + default
model), writes PNG candidates plus a metadata sidecar for provenance.

Usage (repo root):
    .venv/Scripts/python.exe scripts/generate_from_prompt.py --prompt path/prompt.txt --out dir [--candidates 2] [--size 1536x1024] [--quality high] [--model ID]

Prompt is read from --prompt (a text file, e.g. RFS prompt.txt); the first
non-empty line block is used verbatim.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

import os
REPO = Path(os.environ.get("PAPERBANANA_ROOT", r"E:\skills\PaperBanana")).expanduser().resolve()
sys.path.insert(0, str(REPO))

import yaml  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402


def load_env(path: Path) -> None:
    if not path.exists():
        return
    import os
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip())


async def render(client: AsyncOpenAI, model: str, prompt: str, size: str, quality: str) -> bytes:
    resp = await client.images.generate(model=model, prompt=prompt, n=1, size=size, quality=quality)
    if not resp.data:
        raise RuntimeError("empty response")
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    url = getattr(item, "url", None)
    if not url:
        raise RuntimeError("response has neither b64_json nor url")
    import httpx
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as http:
        r = await http.get(url)
        r.raise_for_status()
        return r.content


async def main() -> int:
    ap = argparse.ArgumentParser(description="Single-shot figure generation from a prompt file")
    ap.add_argument("--prompt", required=True, help="Path to a prompt text file (e.g. RFS prompt.txt)")
    ap.add_argument("--out", required=True, help="Output directory for candidates + metadata")
    ap.add_argument("--candidates", type=int, default=1)
    ap.add_argument("--size", default="1536x1024")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    load_env(REPO / ".env")
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("MISSING OPENAI_API_KEY in", REPO / ".env")
        return 2
    prompt = Path(args.prompt).expanduser().resolve().read_text(encoding="utf-8").strip()
    if not prompt:
        print("FAIL: prompt file is empty")
        return 2

    cfg = yaml.safe_load((REPO / "configs/model_config.yaml").read_text(encoding="utf-8"))
    model = args.model or cfg["defaults"]["image_gen_model_name"]
    base_url = cfg["provider_settings"]["openai"]["base_url"]
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    first = sorted(out.glob("candidate-*.png"))
    if first and not args.overwrite:
        print(f"FAIL: {out} already has candidates; use --overwrite")
        return 2

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=600, max_retries=1)
    meta = {"model": model, "size": args.size, "quality": args.quality,
            "prompt_file": str(Path(args.prompt).resolve()),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "relay": base_url.split("//")[-1].split("/")[0],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "candidates": []}
    ok = 0
    for idx in range(args.candidates):
        try:
            raw = await render(client, model, prompt, args.size, args.quality)
        except Exception as exc:  # keep provenance of failures too
            meta["candidates"].append({"index": idx + 1, "error": str(exc)[:300]})
            print(f"candidate {idx + 1}: FAIL {str(exc)[:120]}")
            continue
        path = out / f"candidate-{idx + 1}.png"
        path.write_bytes(raw)
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(raw))
        meta["candidates"].append({"index": idx + 1, "file": str(path),
                                   "bytes": len(raw), "width": im.size[0], "height": im.size[1]})
        ok += 1
        print(f"candidate {idx + 1}: OK {im.size[0]}x{im.size[1]} -> {path}")

    (out / "generation-metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(("DONE" if ok else "FAILED") + f": {ok}/{args.candidates} candidates; metadata -> {out / 'generation-metadata.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
