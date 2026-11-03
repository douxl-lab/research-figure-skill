"""Smoke-test the OpenAI-compatible image relay configured for PaperBanana.

Reads the repo-local .env (OPENAI_API_KEY) and configs/model_config.yaml
(provider_settings.openai.base_url, defaults.image_gen_model_name), generates
one small image, and verifies the response with Pillow. Use this to check the
image2-api relay health without touching the full multi-agent pipeline.

Usage (from repo root):
    .venv/Scripts/python.exe scripts/image2api_smoke.py [--size 1024x1024] [--quality low]
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import sys
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


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="low", choices=["low", "medium", "high"])
    args = parser.parse_args()

    load_env(REPO / ".env")
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("MISSING OPENAI_API_KEY in", REPO / ".env")
        return 2

    cfg = yaml.safe_load((REPO / "configs/model_config.yaml").read_text(encoding="utf-8"))
    model = cfg["defaults"]["image_gen_model_name"]
    base_url = cfg["provider_settings"]["openai"]["base_url"]
    print(f"model={model}  base={base_url.split('//')[-1].split('/')[0]}  size={args.size} quality={args.quality}")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=300, max_retries=0)
    resp = await client.images.generate(
        model=model, prompt="A minimal flat teal circle centered on a white background, no text.",
        n=1, size=args.size, quality=args.quality)
    b64 = resp.data[0].b64_json if resp.data else None
    url = getattr(resp.data[0], "url", None) if resp.data else None
    if b64:
        raw = base64.b64decode(b64)
    elif url:
        import httpx
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as http:
            r = await http.get(url)
            r.raise_for_status()
            raw = r.content
    else:
        print("FAIL: empty response (no b64_json, no url)")
        return 1

    import io
    from PIL import Image
    im = Image.open(io.BytesIO(raw))
    out = REPO / "outputs" / "image2api-smoke.png"
    out.parent.mkdir(exist_ok=True)
    im.save(out)
    print(f"OK: {im.size[0]}x{im.size[1]} {im.mode} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
