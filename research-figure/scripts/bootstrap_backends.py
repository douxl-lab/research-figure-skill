#!/usr/bin/env python3
"""Materialize pinned public engines; never run their code or install packages."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(entry: dict, destination: Path, *, allow_network: bool = False) -> dict:
    if not allow_network:
        raise ValueError("Backend download requires explicit --allow-network")
    revision = entry["revision"]
    repository = entry["repository"]
    directory = entry["directory"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Use an exact 40-character commit, never a floating branch")
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Only pinned public GitHub repositories are supported")
    if directory not in {"PaperBanana", "CVPR-Figure"}:
        raise ValueError("Unknown backend directory")
    destination = destination.expanduser().resolve()
    target = destination / directory
    if target.exists():
        raise ValueError(f"Refusing to overwrite existing checkout: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    # Fresh, temporary checkout; no user Git templates/hooks/filters are used.
    with tempfile.TemporaryDirectory(prefix=".rfs-fetch-", dir=destination) as temporary:
        staging = Path(temporary) / "repo"
        empty = Path(temporary) / "empty"
        empty.mkdir()
        base = ["git", "-c", f"core.hooksPath={empty}", "-c", f"init.templateDir={empty}"]
        def git(*args: str) -> str:
            p = subprocess.run(base + list(args), env=env, text=True, capture_output=True, timeout=180, check=False)
            if p.returncode:
                raise ValueError("Pinned checkout failed; check network/Git access. No backend code was run")
            return p.stdout.strip()
        git("init", str(staging))
        git("-C", str(staging), "remote", "add", "origin", repository + ".git")
        git("-C", str(staging), "fetch", "--depth", "1", "origin", revision)
        if git("-C", str(staging), "rev-parse", "FETCH_HEAD") != revision:
            raise ValueError("Fetched revision mismatch")
        git("-C", str(staging), "checkout", "--detach", revision)
        if not (staging / "LICENSE").is_file():
            raise ValueError("Upstream LICENSE missing; do not redistribute an unreviewed snapshot")
        if not all((staging / path).is_file() for path in entry["entrypoints"]):
            raise ValueError("Pinned checkout is missing expected entrypoints")
        if target.exists():
            raise ValueError("Destination appeared during download; refusing replacement")
        staging.rename(target)
    return {"id": entry["id"], "path": str(target), "revision": revision,
            "status": "SOURCE_INSTALLED_RUNTIME_NOT_VERIFIED"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend", choices=("paperbanana", "cvpr-figure", "all"), default="all")
    p.add_argument("--destination", required=True, type=Path)
    p.add_argument("--allow-network", action="store_true")
    args = p.parse_args()
    completed = []
    try:
        catalog = json.loads((ROOT / "assets/capabilities.json").read_text(encoding="utf-8"))
        for entry in catalog["modules"]:
            if entry["id"] in {"paperbanana", "cvpr-figure"} and args.backend in {"all", entry["id"]}:
                completed.append(install(entry, args.destination, allow_network=args.allow_network))
        print(json.dumps({"installed": completed, "next": "Review upstream runtime requirements; no package installation or provider authorization was performed"}, indent=2))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "FAILED_OR_PARTIAL", "installed": completed, "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
