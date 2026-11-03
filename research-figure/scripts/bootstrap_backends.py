#!/usr/bin/env python3
"""Legacy source installer; embedded kernels are now the default.

Use upstreams.py check/pull to update embedded kernels. This compatibility command
only materializes optional separate source checkouts; it installs no dependencies.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from upstreams import read_lock
ROOT = Path(__file__).resolve().parents[1]


def install(entry: dict, destination: Path, *, allow_network: bool = False) -> dict:
    if not allow_network:
        raise ValueError("Source download requires explicit --allow-network")
    revision, repository = entry["revision"], entry["repository"]
    directory = entry["directory"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected pinned public HTTPS GitHub source")
    if directory not in {"design", "layout", "PaperBanana", "CVPR-Figure"}:
        raise ValueError("Unknown source directory")
    destination = destination.expanduser().resolve()
    target = destination / directory
    if target.exists():
        raise ValueError("Refusing to overwrite an existing checkout")
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    with tempfile.TemporaryDirectory(prefix=".rfs-fetch-", dir=destination) as temporary:
        stage = Path(temporary) / "source"
        empty = Path(temporary) / "empty"
        empty.mkdir()
        base = ["git", "-c", f"core.hooksPath={empty}", "-c", f"init.templateDir={empty}"]
        def git(*args):
            p = subprocess.run(base + list(args), env=env, capture_output=True, text=True, timeout=180)
            if p.returncode:
                raise ValueError("Pinned source checkout failed; no source code was executed")
            return p.stdout.strip()
        git("init", str(stage))
        git("-C", str(stage), "fetch", "--depth", "1", repository + ".git", revision)
        if git("-C", str(stage), "rev-parse", "FETCH_HEAD") != revision:
            raise ValueError("Fetched revision mismatch")
        git("-C", str(stage), "checkout", "--detach", revision)
        if not (stage / "LICENSE").is_file():
            raise ValueError("Missing license")
        stage.rename(target)
    return {"path": str(target), "revision": revision, "status": "SOURCE_INSTALLED_RUNTIME_NOT_VERIFIED"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend", choices=["design", "layout", "paperbanana", "cvpr-figure", "all"], default="all")
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--allow-network", action="store_true")
    a = p.parse_args()
    selected = {"paperbanana":"design", "cvpr-figure":"layout"}.get(a.backend, a.backend)
    results = []
    try:
        for name, entry in read_lock(ROOT)["kernels"].items():
            if selected in {"all", name}:
                results.append(install(dict(entry, directory=name), a.destination, allow_network=a.allow_network))
        print(json.dumps({"installed":results, "notice":"Embedded kernels already ship; use upstreams.py for their updates"}, indent=2))
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"BLOCKED_OR_PARTIAL", "completed":results, "error":str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
