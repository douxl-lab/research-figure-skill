#!/usr/bin/env python3
"""Fail closed on accidentally tracked private state and high-confidence secrets.

This complements .gitignore: already tracked or force-added files are STILL
submitted to GitHub. Do not claim a regex scan proves that content is harmless.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT_PUBLIC = frozenset({
    ".gitignore", ".gitattributes", "README.md", "SKILL.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "requirements-plot.txt",
})
SOURCE_DIRS = frozenset({"assets", "agents", "references", "scripts", "tests"})
PRIVATE_SEGMENTS = frozenset({
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".vscode", ".idea", ".cursor", ".claude", ".codex", ".agents",
    ".continue", ".windsurf", ".roo", ".fleet", ".zed",
    "docs", "documents", "internal", "private", "notes", "drafts", "plans",
    "work", "workspace", "tmp", "temp", "cache", "data", "datasets",
    "checkpoints", "runs", "results", "outputs", "output", "artifacts",
    "generated", "figures", "logs", "screenshots", "notebooks", "reviews",
})
BAD_EXTENSIONS = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".p8", ".jks", ".keystore",
    ".db", ".sqlite", ".sqlite3", ".ipynb", ".pdf", ".docx",
    ".xlsx", ".pptx", ".zip", ".tar", ".tgz", ".rar", ".7z",
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".tiff", ".tif",
})
SENSITIVE_NAME = re.compile(
    r"(?i)(?:^|[._-])(?:secret|secrets|credential|credentials|api[-_]?key|"
    r"private[-_]?key|service[-_]?account|password|access[-_]?token|"
    r"refresh[-_]?token)(?:[._-]|$)"
)
HIGH_CONFIDENCE = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "OpenAI-like token": re.compile(r"\bsk-(?:proj-|live-|test-|org-)?[A-Za-z0-9_-]{32,}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{24,})\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{25,}\b"),
}
MAX_SOURCE_FILE = 2 * 1024 * 1024


def public_path(path: str) -> bool:
    """Allow public Skill runtime/docs/tests, reject local data/docs/dev profiles."""
    if not isinstance(path, str) or not path or "\\" in path:
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        return False
    parts = pure.parts
    if any(segment.lower() in PRIVATE_SEGMENTS for segment in parts):
        return False
    if any(segment.startswith(".") for segment in parts[1:]):
        return False
    name = parts[-1]
    if name.startswith(".env") or name.endswith(".env") or ".local." in name or SENSITIVE_NAME.search(name):
        return False
    if pure.suffix.lower() in BAD_EXTENSIONS:
        return False
    if path in ROOT_PUBLIC:
        return True
    if parts[0] == ".github":
        return len(parts) == 3 and parts[1] == "workflows" and pure.suffix in {".yml", ".yaml"}
    if parts[0] != "research-figure":
        return False
    sub = parts[1:]
    if len(sub) == 1:
        return sub[0] in {"SKILL.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "requirements-plot.txt"}
    if len(sub) < 2:
        return False
    if sub[0] == "assets" and pure.suffix.lower() == ".csv":
        return sub[-1].startswith("demo-synthetic-")
    return sub[0] in SOURCE_DIRS and pure.suffix.lower() in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".csv"}


def scan_content(path: str, payload: bytes) -> list[str]:
    if len(payload) > MAX_SOURCE_FILE:
        return [f"{path}: source file exceeds {MAX_SOURCE_FILE} bytes"]
    try:
        content = payload.decode("utf-8")
    except UnicodeDecodeError:
        return [f"{path}: non-UTF-8/binary file not allowed without explicit review"]
    if "\x00" in content:
        return [f"{path}: contains NUL bytes"]
    issues = []
    for label, pattern in HIGH_CONFIDENCE.items():
        if pattern.search(content):
            issues.append(f"{path}: possible {label} (value never printed)")
    return issues


def check_paths(root: Path, paths: list[str]) -> list[str]:
    failures: list[str] = []
    for rel in sorted(set(paths)):
        if not public_path(rel):
            failures.append(f"{rel}: forbidden tracked path or file extension")
            continue
        path = root / rel
        if path.is_symlink() or not path.is_file():
            failures.append(f"{rel}: symlink or missing tracked file")
            continue
        failures.extend(scan_content(rel, path.read_bytes()))
    return failures


def git_tracked(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode:
        raise RuntimeError("Git tracked-files check requires a valid git repository")
    return [p.decode("utf-8") for p in proc.stdout.split(b"\0") if p]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Git-tracked RFS files for confidential state and token patterns")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--tracked", action="store_true", help="Scan exactly the files recorded in the Git index")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        files = git_tracked(root) if args.tracked else [str(p.relative_to(root)) for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts and not any(seg in PRIVATE_SEGMENTS for seg in p.relative_to(root).parts)]
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    problems = check_paths(root, files)
    if problems:
        for problem in problems:
            print("BLOCK: " + problem, file=sys.stderr)
        return 1
    print(f"Repository hygiene PASS: checked {len(files)} public source files; no high-confidence secret signatures found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
