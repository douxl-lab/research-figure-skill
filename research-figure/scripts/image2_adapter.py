#!/usr/bin/env python3
"""Source-bound, raster-first bridge to a separately installed image2-api CLI.

No provider discovery, implicit payment, automatic retries or vector fallback.
The external CLI is a trusted local dependency, not bundled or auto-updated.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bridge import _api
from generate_from_prompt import image_info, load_config, sha

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_REVISION = "d4cdbc64bc77c395a4aa5c8928f116a4722f038d"
RASTER_FORMATS = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}


def child_environment(config: dict, key: str) -> dict[str, str]:
    """Freeze every known image2 provider setting; installed .env cannot override it."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("IMAGE_API_", "OPENAI_"))}
    base = config["base_url"].rstrip("/")
    env.update({
        "IMAGE_API_KEY": key, "OPENAI_API_KEY": "",
        "IMAGE_API_BASE_URL": base, "IMAGE_API_MODEL": config["model"],
        "IMAGE_API_MODEL_FAMILY": config.get("model_family", "auto"),
        "IMAGE_API_GENERATIONS_URL": base + "/images/generations",
        "IMAGE_API_EDITS_URL": base + "/images/edits",
        "IMAGE_API_PROVIDERS": "", "IMAGE_API_FALLBACK_STATUS": "",
        "IMAGE_API_MAX_RETRIES": "0", "IMAGE_API_VERIFY_SSL": "true",
        "IMAGE_API_EXTRA_HEADERS": "{}", "IMAGE_API_CLEAN_INTERMEDIATES": "0",
        "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
    })
    return env


def backend_script(root: Path, operation: str) -> Path:
    _, interop, _ = _api()
    root = interop.ordinary_path(root).resolve()
    script = root / "scripts" / ("edit_image.py" if operation == "edit" else "generate_image.py")
    interop.read_bytes(script)
    interop.read_bytes(root / "SKILL.md")
    return script


def check_options(args) -> None:
    if args.output_format not in RASTER_FORMATS:
        raise ValueError("Use raster output here; requested SVG is authored by the host LLM, not this image API")
    if type(args.candidates) is not int or not 1 <= args.candidates <= 8:
        raise ValueError("candidates must be 1..8")
    if not 1 <= args.timeout <= 900:
        raise ValueError("timeout must be 1..900 seconds per candidate")
    if len(args.image) > 16 or (args.mask and not args.image):
        raise ValueError("At most 16 reference images; a mask requires a primary image")
    if args.background == "transparent" and args.output_format == "jpeg":
        raise ValueError("Transparent output requires PNG or WebP")
    if not args.dry_run and not args.allow_external:
        raise ValueError("Live calls require --allow-external after service/data/cost authorization")


def execute(args, *, runner=None) -> dict:
    check_options(args)
    contract, interop, _ = _api()
    spec_path = interop.ordinary_path(args.spec)
    spec_raw = interop.read_bytes(spec_path)
    spec = interop.load_spec(spec_path)
    if spec["kind"] != "diagram" or spec.get("datasets"):
        raise ValueError("Only mechanism diagrams use generation; measurements and real evidence remain source-preserving")
    prompt_raw = interop.read_bytes(args.prompt, 128_000)
    prompt_text = prompt_raw.decode("utf-8")
    if not prompt_text.strip() or len(prompt_text) > 32_000:
        raise ValueError("Prompt must contain 1..32000 characters")
    config = load_config(args.config)
    # A project config names a service, not a request to discover one in .env.
    base = config["base_url"].rstrip("/")
    if base.endswith(("/images/generations", "/images/edits")):
        raise ValueError("base_url must be the API base, not an image endpoint")
    if not isinstance(config.get("model_family", "auto"), str):
        raise ValueError("model_family must be a string")
    key = os.environ.get(config["api_key_env"], "").strip()
    if not args.dry_run and not key:
        raise ValueError("The explicitly configured credential environment variable is empty")
    operation = "edit" if args.image else "generate"
    runtime = interop.ordinary_path(args.image2_root).resolve()
    script = backend_script(runtime, operation)
    out = interop.ordinary_path(args.out).resolve()
    if any(out == forbidden or forbidden in out.parents for forbidden in (ROOT, runtime)):
        raise ValueError("Output must be outside both installed Skills")
    if out.exists():
        raise ValueError("Output exists; preserve prior figures and use a fresh directory")
    inputs = []
    for index, path in enumerate(args.image, 1):
        raw = interop.read_bytes(path, 64 * 1024 * 1024)
        ext, mime, width, height = image_info(raw)
        inputs.append((f"reference-{index}{ext}", raw,
                       {"role": "primary" if index == 1 else "reference", "sha256": sha(raw),
                        "mime": mime, "width": width, "height": height}))
    if args.mask:
        from PIL import Image
        raw = interop.read_bytes(args.mask, 64 * 1024 * 1024)
        ext, mime, width, height = image_info(raw)
        with Image.open(io.BytesIO(raw)) as im:
            if mime != "image/png" or "A" not in im.getbands():
                raise ValueError("A mask must be a PNG with an alpha channel")
            if im.getchannel("A").getextrema()[0] == 255:
                raise ValueError("A mask must contain transparent editable pixels")
        first = inputs[0][2]
        if (width, height) != (first["width"], first["height"]):
            raise ValueError("Mask dimensions must match the primary image")
        inputs.append(("mask.png", raw, {"role": "mask", "sha256": sha(raw),
                                       "mime": mime, "width": width, "height": height}))
    out.mkdir(parents=True, exist_ok=False)
    (out / "figure-spec.json").write_bytes(spec_raw)
    (out / "prompt-source.txt").write_bytes(prompt_raw)
    (out / "prompt.txt").write_bytes(prompt_raw)
    (out / "design-intent.md").write_text(
        "# Design intent (not image observations)\n\n" +
        json.dumps(spec.get("design", {}), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, raw, _ in inputs:
        (out / name).write_bytes(raw)
    run_dir = out / "provider-run"
    endpoint = base + ("/images/edits" if operation == "edit" else "/images/generations")
    command = [sys.executable, str(script), "--prompt-file", str(out / "prompt-source.txt"),
               "--base-url", base, "--endpoint", endpoint, "--model", config["model"],
               "--model-family", config.get("model_family", "auto"),
               "--size", args.size, "--quality", args.quality,
               "--background", args.background, "--output-format", args.output_format,
               "--count", str(args.candidates), "--batch-mode", "sequential",
               "--max-retries", "0", "--timeout", str(args.timeout),
               "--prompt-profile", "edit" if operation == "edit" else "academic-diagram",
               "--prompt-lint", "warn", "--output-dir", str(run_dir), "--json"]
    for name, _, record in inputs:
        command += ["--mask" if record["role"] == "mask" else "--image", str(out / name)]
    if args.dry_run:
        command.append("--dry-run")
    metadata = {
        "format": "rfs-image-generation/1.0", "pipeline": "image2-api-cli",
        "operation": operation, "provider": config["provider"], "model": config["model"],
        "model_source": "requested_configuration", "endpoint_host": urlsplit(base).hostname,
        "figure_spec_sha256": sha(spec_raw), "scientific_fingerprint": contract.scientific_fingerprint(spec),
        "source_prompt_sha256": sha(prompt_raw), "prompt_sha256": None,
        "prompt_submission": "NOT_CONFIRMED", "size": args.size, "quality": args.quality,
        "background": args.background, "output_format": args.output_format,
        "requested_candidates": args.candidates, "candidates": [],
        "reference_inputs": [{"file": name, **record} for name, _, record in inputs],
        "adapter_reference_revision": REFERENCE_REVISION,
        "runtime_entry_sha256": sha(script.read_bytes()),
        "runtime_compatibility": "CLI_CONTRACT_NOT_A_FULL_RUNTIME_ATTESTATION",
        "created_at": datetime.now(timezone.utc).isoformat(), "generated_at": None,
        "scientific_review": "PENDING", "visual_review": "PENDING",
        "status": "DRY_RUN_IN_PROGRESS" if args.dry_run else "IN_PROGRESS",
    }
    sidecar = out / "generation-metadata.json"

    def save() -> None:
        sidecar.write_bytes(interop.json_bytes(metadata))

    save()
    runner = runner or subprocess.run
    try:
        done = runner(command, cwd=out, env=child_environment(config, key or "placeholder-dry-run"),
                      text=True, capture_output=True, check=False,
                      timeout=args.timeout * args.candidates + 30)
        if done.returncode:
            raise ValueError("External CLI failed; no automatic retry")
        response = json.loads(done.stdout)
        if not isinstance(response, dict) or response.get("ok") is not True:
            raise ValueError("External CLI did not confirm a successful result")
        if response.get("dry_run", False) is not args.dry_run:
            raise ValueError("Dry-run/live response mismatch")
        request = interop.read_object(run_dir / "request.json")
        payloads = request.get("requests", [])
        if not isinstance(payloads, list) or len(payloads) != args.candidates:
            raise ValueError("Request candidate count mismatch")
        submitted = payloads[0].get("prompt") if isinstance(payloads[0], dict) else None
        if submitted not in (prompt_text, prompt_text.strip()):
            raise ValueError("Unexpected prompt rewriting; inspect the local request")
        for payload in payloads:
            if not isinstance(payload, dict) or any(payload.get(k) != v for k, v in {
                "prompt": submitted, "model": config["model"], "n": 1,
                "output_format": args.output_format, "size": args.size,
                "quality": args.quality, "background": args.background,
            }.items()):
                raise ValueError("Actual request differs from the authorized plan")
        actual_config = request.get("config", {})
        field = "edit_endpoint" if operation == "edit" else "generation_endpoint"
        if (not isinstance(actual_config, dict) or actual_config.get(field) != endpoint
                or actual_config.get("max_retries") != 0 or actual_config.get("chain")):
            raise ValueError("Actual service/retry configuration differs from the plan")
        submitted_raw = submitted.encode("utf-8")
        (out / "prompt.txt").write_bytes(submitted_raw)
        metadata["prompt_sha256"] = sha(submitted_raw)
        metadata["prompt_submission"] = "PLANNED_ONLY" if args.dry_run else "RECORDED_BY_IMAGE2_REQUEST"
        metadata["request_sha256"] = sha(interop.read_bytes(run_dir / "request.json"))
        if args.dry_run:
            metadata["status"] = "DRY_RUN_VALID_NOT_GENERATED"
        else:
            paths = response.get("images")
            if (not isinstance(paths, list) or len(paths) != args.candidates
                    or not all(isinstance(p, str) for p in paths)):
                raise ValueError("Unexpected image count; inspect preserved provider outputs")
            seen = set()
            for index, filename in enumerate(paths, 1):
                image = interop.ordinary_path(filename)
                # image2-api returns absolute output paths; reject relative or escaped paths.
                if not Path(filename).is_absolute() or run_dir not in image.resolve().parents or image in seen:
                    raise ValueError("Returned image escaped the run or duplicated another candidate")
                seen.add(image)
                raw = interop.read_bytes(image, 64 * 1024 * 1024)
                ext, mime, width, height = image_info(raw)
                if mime != RASTER_FORMATS[args.output_format]:
                    raise ValueError("Output format does not match actual image bytes")
                from PIL import Image
                with Image.open(io.BytesIO(raw)) as im:
                    has_alpha = "A" in im.getbands() or "transparency" in im.info
                    transparent = has_alpha and im.convert("RGBA").getchannel("A").getextrema()[0] < 255
                name = f"candidate-{index}{ext}"
                (out / name).write_bytes(raw)
                metadata["candidates"].append({"index": index, "file": name, "sha256": sha(raw),
                    "bytes": len(raw), "mime": mime, "width": width, "height": height,
                    "has_alpha": has_alpha, "has_transparent_pixels": bool(transparent), "status": "succeeded"})
            metadata["status"] = "GENERATED_UNREVIEWED"
            metadata["generated_at"] = datetime.now(timezone.utc).isoformat()
            if args.background == "transparent" and not all(c["has_transparent_pixels"] for c in metadata["candidates"]):
                metadata["warnings"] = ["Requested transparency was not observed in every candidate; repair before delivery"]
    except Exception as exc:
        # Provider stdout/stderr/errors can contain prompts, URLs and credentials.
        metadata["status"] = "DRY_RUN_FAILED" if args.dry_run else "FAILED_OR_UNKNOWN"
        metadata["error_type"] = type(exc).__name__
        metadata["instruction"] = "Inspect preserved local outputs before any retry; do not infer completion"
    save()
    return {"status": metadata["status"], "operation": operation,
            "candidate_count": len(metadata["candidates"]), "metadata": str(sidecar),
            "scientific_review": "PENDING", "visual_review": "PENDING"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("spec", "prompt", "config", "image2-root", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--image", action="append", type=Path, default=[])
    p.add_argument("--mask", type=Path)
    p.add_argument("--size", default="auto")
    p.add_argument("--quality", choices=("low", "medium", "high", "xhigh", "max", "auto"), default="high")
    p.add_argument("--background", choices=("auto", "opaque", "transparent"), default="auto")
    p.add_argument("--output-format", choices=tuple(RASTER_FORMATS), default="png")
    p.add_argument("--candidates", type=int, default=1)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-external", action="store_true")
    return p


def main() -> int:
    try:
        result = execute(parser().parse_args())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"GENERATED_UNREVIEWED", "DRY_RUN_VALID_NOT_GENERATED"} else 1
    except (ValueError, OSError, ImportError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
