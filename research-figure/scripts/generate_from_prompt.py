#!/usr/bin/env python3
"""Explicit, host-orchestrated single-shot image adapter. No implicit credentials/config.

Requires an evidence-bound diagram, an explicit service config and authorization.
Outputs preserve exact prompt/image bytes and a portable provenance sidecar.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import hashlib
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE = 64 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_config(path: Path) -> dict:
    # Configuration is task-local. Never scan an installed kernel for secrets.
    if path.suffix.lower() in {'.yaml', '.yml'}:
        import yaml
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
    else:
        value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Provider configuration must be an object')
    for field in ('provider', 'model', 'base_url', 'api_key_env'):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError('Provider config requires provider/model/base_url/api_key_env')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value['api_key_env']):
        raise ValueError('Invalid credential environment variable name')
    url = urlsplit(value['base_url'])
    local_http = url.scheme == 'http' and url.hostname in {'localhost', '127.0.0.1', '::1'}
    if url.scheme != 'https' and not (local_http and value.get('allow_http_loopback') is True):
        raise ValueError('Require HTTPS or an explicitly configured loopback service')
    if not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Endpoint must not contain embedded credentials/query/fragment')
    hosts = value.get('image_hosts', [])
    if not isinstance(hosts, list) or not all(isinstance(h, str) and h and ':' not in h for h in hosts):
        raise ValueError('image_hosts must be an exact hostname allowlist')
    return value


def image_info(raw: bytes) -> tuple[str, str, int, int]:
    from PIL import Image
    if not raw or len(raw) > MAX_IMAGE:
        raise ValueError('Empty or oversized image response')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in {'PNG', 'JPEG', 'WEBP'} or im.width * im.height > 64_000_000:
                raise ValueError('Unsupported image format or pixel count')
            result = ({'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp'}[im.format], Image.MIME[im.format], im.width, im.height)
            im.verify()
            return result
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid image bytes') from exc


async def render(client, model: str, prompt: str, size: str, quality: str, image_hosts: list[str]) -> tuple[bytes, str | None]:
    response = await client.images.generate(model=model, prompt=prompt, n=1, size=size, quality=quality)
    if not response.data:
        raise ValueError('Provider returned no image')
    item = response.data[0]
    if getattr(item, 'b64_json', None):
        # Bound the encoded representation before allocating decoded bytes.
        if len(item.b64_json) > MAX_IMAGE * 4 // 3 + 8:
            raise ValueError('Oversized encoded image')
        raw = base64.b64decode(item.b64_json, validate=True)
    else:
        url = urlsplit(getattr(item, 'url', '') or '')
        if url.scheme != 'https' or url.hostname not in image_hosts or url.username or url.password:
            raise ValueError('Image URL host not explicitly allowed; request base64 or configure image_hosts')
        import httpx
        async with httpx.AsyncClient(timeout=120, follow_redirects=False) as http:
            async with http.stream('GET', url.geturl()) as r:
                r.raise_for_status()
                chunks, total = [], 0
                async for part in r.aiter_bytes():
                    total += len(part)
                    if total > MAX_IMAGE:
                        raise ValueError('Oversized downloaded image')
                    chunks.append(part)
                raw = b''.join(chunks)
    return raw, getattr(response, 'model', None)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prompt', required=True, type=Path)
    p.add_argument('--spec', type=Path, help='Defaults to figure-spec.json next to the prompt')
    p.add_argument('--config', required=True, type=Path, help='Explicit project-local JSON/YAML config, not an installed-kernel config')
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--candidates', type=int, default=1)
    p.add_argument('--size', default='1536x1024')
    p.add_argument('--quality', default='high', choices=['low', 'medium', 'high', 'xhigh', 'max', 'auto', 'standard'])
    p.add_argument('--model', help='Explicit override of configured model')
    p.add_argument('--allow-external', action='store_true')
    return p


async def execute(args, *, client_factory=None) -> dict:
    if not args.allow_external:
        raise ValueError('External image calls require --allow-external after service/data/cost authorization')
    if not 1 <= args.candidates <= 8:
        raise ValueError('candidates must be 1..8')
    from bridge import _api
    contract, interop, _ = _api()
    prompt_path = interop.ordinary_path(args.prompt)
    prompt_raw = interop.read_bytes(prompt_path)
    prompt = prompt_raw.decode('utf-8')  # Exact bytes, including whitespace.
    if not prompt.strip():
        raise ValueError('Empty prompt')
    spec_path = interop.ordinary_path(args.spec or prompt_path.parent / 'figure-spec.json')
    spec_raw = interop.read_bytes(spec_path)
    spec = interop.load_spec(spec_path)
    if spec['kind'] != 'diagram':
        raise ValueError('Measured plots/hybrid evidence must not use an image generator')
    config = load_config(args.config)
    key = os.environ.get(config['api_key_env'], '')
    if not key:
        raise ValueError('Configured credential environment variable is empty')
    model = args.model or config['model']
    out = interop.ordinary_path(args.out)
    if ROOT == out or ROOT in out.parents:
        raise ValueError('Output must be outside the installed Skill')
    if out.exists():
        raise ValueError('Output exists; use a fresh job directory, never overwrite candidates')
    if client_factory is None:
        from openai import AsyncOpenAI
        client_factory = AsyncOpenAI
    meta = {'format': 'rfs-image-generation/1.0', 'pipeline': 'host-single-shot',
            'provider': config['provider'], 'model': model, 'model_source': 'requested_configuration',
            'endpoint_host': urlsplit(config['base_url']).hostname,
            'prompt_sha256': sha(prompt_raw), 'figure_spec_sha256': sha(spec_raw),
            'scientific_fingerprint': contract.scientific_fingerprint(spec),
            'size': args.size, 'quality': args.quality, 'requested_candidates': args.candidates,
            'generated_at': datetime.now(timezone.utc).isoformat(), 'candidates': [],
            'scientific_review': 'PENDING', 'visual_review': 'PENDING', 'status': 'IN_PROGRESS'}
    out.mkdir(parents=True, exist_ok=False)
    sidecar = out / 'generation-metadata.json'
    def save():
        sidecar.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    save()
    try:
        async with client_factory(api_key=key, base_url=config['base_url'], timeout=600, max_retries=0) as client:
            for index in range(1, args.candidates + 1):
                try:
                    raw, observed = await render(client, model, prompt, args.size, args.quality, config.get('image_hosts', []))
                    ext, mime, width, height = image_info(raw)
                    name = f'candidate-{index}{ext}'
                    (out / name).write_bytes(raw)
                    meta['candidates'].append({'index': index, 'file': name, 'sha256': sha(raw),
                        'mime': mime, 'bytes': len(raw), 'width': width, 'height': height,
                        'response_model': observed, 'status': 'succeeded'})
                    save()
                except Exception as exc:
                    # Never print provider error text, URLs, prompt or credentials.
                    meta['candidates'].append({'index': index, 'status': 'failed_or_unknown', 'error_type': type(exc).__name__})
                    break  # No automatic retry after a possibly billable request.
    except Exception as exc:
        meta['error_type'] = type(exc).__name__
    count = sum(c['status'] == 'succeeded' for c in meta['candidates'])
    meta['status'] = 'GENERATED_UNREVIEWED' if count == args.candidates else 'FAILED_OR_PARTIAL'
    save()
    return {'status': meta['status'], 'candidate_count': count, 'requested_candidates': args.candidates, 'metadata': str(sidecar)}


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        result = asyncio.run(execute(args))
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'GENERATED_UNREVIEWED' else 1
    except (ValueError, OSError, ImportError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
