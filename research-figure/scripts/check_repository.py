#!/usr/bin/env python3
"""Fail closed on accidentally tracked private state and high-confidence secrets.

This complements .gitignore: already tracked or force-added files are STILL
submitted to GitHub. Do not claim a regex scan proves that content is harmless.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

ROOT_PUBLIC = frozenset({
    ".gitignore", ".gitattributes", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
})
SOURCE_DIRS = frozenset({"assets", "agents", "references", "scripts", "tests", "protocol"})
PRIVATE_SEGMENTS = frozenset({
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".vscode", ".idea", ".cursor", ".claude", ".codex", ".agents",
    ".continue", ".windsurf", ".roo", ".fleet", ".zed", ".kiro", ".trae",
    ".aider", ".gemini", ".opencode", ".openclaw", ".pi", ".kimi",
    ".ssh", ".aws", ".azure", ".config", ".kube", ".gnupg",
    ".project-state", ".task-state", ".scratch", ".sync-state",
    "docs", "documents", "internal", "private", "notes", "drafts", "plans",
    "reports", "reviews", "sessions", "transcripts", "manuscripts", "research",
    "work", "workspace", "tmp", "temp", "cache", "data", "datasets", "papers",
    "checkpoints", "runs", "results", "outputs", "output", "artifacts",
    "generated", "figures", "logs", "screenshots", "notebooks", "scratch",
    "jobs", "native-jobs", "native_runtime", "attachments", "deliverables",
    "node_modules", "site-packages", "build", "dist", "release",
})
PRIVATE_NAMES = frozenset({
    "agents.md", "claude.md", "gemini.md", "todo.md", "plan.md", "roadmap.md",
    "dev_notes.md", "status.md", "task_plan.md", "findings.md", "progress.md",
    "package_manifest.json", "context.json", "request.json", "repair.json",
    "prompt.txt", "generation-metadata.json", "workflow-plan.json",
    "workflow-result.json", "mcp.json", "mcp.yaml", "model_config.yaml",
    "image-provider.json", "image-provider.yaml", "provider.json", "provider.yaml",
    "config.json", "settings.json",
})
PRIVATE_SUFFIXES = (".receipt.json", ".output.json", ".local", ".env", ".bak", ".tmp", ".swp")
DOCUMENT_EXTENSIONS = frozenset({".md", ".mdx", ".rst", ".adoc", ".org", ".txt"})
BAD_EXTENSIONS = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".p8", ".jks", ".keystore",
    ".db", ".sqlite", ".sqlite3", ".ipynb", ".pdf", ".docx",
    ".xlsx", ".pptx", ".zip", ".tar", ".tgz", ".rar", ".7z",
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".tiff", ".tif",
    ".ttf", ".otf", ".woff", ".woff2", ".eot", ".pfb", ".pfm",
    ".har", ".pcap", ".pcapng", ".jsonl", ".log", ".ipynb",
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
PUBLIC_DOCUMENTS = frozenset({
    'README.md',
    'THIRD_PARTY_NOTICES.md',
    'research-figure/SKILL.md',
    'research-figure/THIRD_PARTY_NOTICES.md',
    'research-figure/assets/design-notes-template.md',
    'research-figure/references/agent-matching.md',
    'research-figure/references/canonical-exchange.md',
    'research-figure/references/core-capabilities.md',
    'research-figure/references/cvpr-figure-library.md',
    'research-figure/references/design-core.md',
    'research-figure/references/figure-spec.md',
    'research-figure/references/integrations.md',
    'research-figure/references/journal-mechanism-style.md',
    'research-figure/references/layout-library.md',
    'research-figure/references/local-image-pipeline.md',
    'research-figure/references/mechanism-figure-workflow.md',
    'research-figure/references/model-routing.md',
    'research-figure/references/orchestration.md',
    'research-figure/references/paperbanana-delegation.md',
    'research-figure/references/prompt-system.md',
    'research-figure/references/quality-gates.md',
    'research-figure/references/recipes.md',
    'research-figure/references/reconstruction.md',
    'research-figure/references/routing.md',
    'research-figure/references/style-spec.md',
    'research-figure/references/tikz-quality-standards.md',
    'research-figure/references/tikz-workflow.md',
    'research-figure/references/trigger-regression.md',
    'research-figure/references/upstream-maintenance.md',
    'research-figure/references/zcode-local-pipeline.md',
    'research-figure/requirements-exchange.txt',
    'research-figure/requirements-native-qa.txt',
    'research-figure/requirements-plot.txt',
})

HIGH_CONFIDENCE["credential-bearing URL"] = re.compile(r"https?://[^\s/:'\"]+:[^\s/@'\"]+@")
HIGH_CONFIDENCE["literal bearer credential"] = re.compile(r"(?i)\bBearer[ \t]+[A-Za-z0-9_./+=-]{24,}")
LITERAL_SECRET = re.compile(
    r"(?im)^[ \t]*[\"']?(?:[A-Z0-9]+[_-])*(?:api[_-]?key|secret[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|password|passwd|token)[\"']?"
    r"[ \t]*[:=][ \t]*[\"']([A-Za-z0-9_+/=.-]{20,})[\"']"
)

UNQUOTED_SECRET = re.compile(
    r"(?im)^[ \t]*(?:[A-Z0-9]+[_-])*(?:api[_-]?key|secret[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|password|passwd|token)"
    r"[ \t]*[:=][ \t]*([A-Za-z0-9_+/=-]{20,})[ \t]*(?:\#.*)?$"
)

MAX_SOURCE_FILE = 2 * 1024 * 1024
MAX_INDEX_BLOB = 8 * 1024 * 1024


def vendor_inventory(root: Path, lock_payload: bytes | None = None) -> dict:
    """Validate a lock from disk or the index without trusting unstaged edits."""
    from upstreams import read_lock
    if lock_payload is None:
        skill = root / "research-figure"
        if not (skill / "assets/upstreams.lock.json").exists():
            return {}
        data = read_lock(skill)
    else:
        # Reuse the same strict upstream validator for staged bytes. This temporary
        # lock is never committed or executed and no downloaded code is imported.
        with tempfile.TemporaryDirectory(prefix="rfs-index-lock-") as temp:
            skill = Path(temp)
            (skill / "assets").mkdir()
            (skill / "assets/upstreams.lock.json").write_bytes(lock_payload)
            data = read_lock(skill)
    return {"research-figure/" + item["destination"] + "/" + rel: record
            for item in data["kernels"].values() for rel, record in item["files"].items()}


def safe_public_location(path: str) -> bool:
    """Common path policy applies even to provenance-locked vendor files."""
    if not isinstance(path, str) or not path or "\\" in path or ":" in path:
        return False
    if any(ord(c) < 32 for c in path):
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute() or pure.as_posix() != path or ".." in pure.parts or not pure.parts:
        return False
    if any(part.lower() in PRIVATE_SEGMENTS for part in pure.parts):
        return False
    if any(part.startswith(".") for part in pure.parts[1:]):
        return False
    name = pure.name.lower()
    if name in PRIVATE_NAMES or name.startswith(".env") or ".local." in name:
        return False
    return not (name.endswith(PRIVATE_SUFFIXES) or SENSITIVE_NAME.search(name))


def public_path(path: str) -> bool:
    """Allow only runtime sources, reviewed public documents, and the CI entry."""
    if not safe_public_location(path):
        return False
    pure = PurePosixPath(path)
    parts, suffix = pure.parts, pure.suffix.lower()
    if suffix in BAD_EXTENSIONS:
        return False
    if suffix in DOCUMENT_EXTENSIONS and path not in PUBLIC_DOCUMENTS:
        return False
    if path in ROOT_PUBLIC:
        return True
    if parts[0] == ".github":
        return path == ".github/workflows/ci.yml"
    if parts[0] != "research-figure" or len(parts) < 2:
        return False
    sub = parts[1:]
    if len(sub) == 1:
        return path in PUBLIC_DOCUMENTS or sub[0] == "LICENSE"
    if path == "research-figure/protocol/LICENSE-APACHE-2.0":
        return True
    if sub[0] == "agents":
        return path == "research-figure/agents/openai.yaml"
    if suffix == ".csv":
        return path == "research-figure/assets/demo-synthetic-ablation.csv"
    return sub[0] in SOURCE_DIRS and suffix in {".py", ".md", ".txt", ".json", ".yaml", ".yml"}


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
    patterns = [LITERAL_SECRET]
    if Path(path).suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".env"}:
        patterns.append(UNQUOTED_SECRET)
    matches = (match for pattern in patterns for match in pattern.finditer(content))
    for match in matches:
        value = match.group(1).lower()
        if not value.startswith(("your_", "your-", "example_", "placeholder", "replace_me", "replace-me")):
            issues.append(f"{path}: possible literal credential assignment (value never printed)")
            break
    return issues


def check_paths(root: Path, paths: list[str]) -> list[str]:
    failures: list[str] = []
    try:
        locked = vendor_inventory(root)
    except (ValueError, OSError) as exc:
        return ["Invalid vendor lock: " + str(exc)]
    for rel in sorted(set(paths)):
        if rel in locked:
            if not safe_public_location(rel):
                failures.append(f"{rel}: private state cannot be allowed by a vendor lock")
                continue
            path = root / rel
            if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root) or not path.is_file():
                failures.append(f"{rel}: symlink or missing locked source")
                continue
            raw = path.read_bytes()
            expected = locked[rel]
            if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
                failures.append(f"{rel}: upstream inventory mismatch")
            elif path.suffix.lower() in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".svg"} or path.name in {"LICENSE", "NOTICE"}:
                failures.extend(scan_content(rel, raw))
            continue
        if not public_path(rel):
            failures.append(f"{rel}: forbidden tracked path or file extension")
            continue
        path = root / rel
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root) or not path.is_file():
            failures.append(f"{rel}: symlink or missing tracked file")
            continue
        failures.extend(scan_content(rel, path.read_bytes()))
    return failures


def check_tracked_inventory(root: Path, paths: list[str]) -> list[str]:
    """A working directory may hide ignored required files; the Git index may not."""
    try:
        missing = sorted(set(vendor_inventory(root)) - set(paths))
    except (ValueError, OSError) as exc:
        return ["Invalid vendor lock: " + str(exc)]
    return [f"{rel}: locked source is not tracked by Git" for rel in missing]


def git_tracked(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode:
        raise RuntimeError("Git tracked-files check requires a valid git repository")
    return [p.decode("utf-8") for p in proc.stdout.split(b"\0") if p]



def read_git_index(root: Path) -> tuple[dict[str, bytes], list[str]]:
    """Read real stage-0 blobs, not current worktree versions; bounded and redacted."""
    listing = subprocess.run(["git", "-C", str(root), "ls-files", "--stage", "-z"],
                             capture_output=True, check=False)
    if listing.returncode:
        raise RuntimeError("Index scan requires a valid Git repository")
    files: dict[str, bytes] = {}
    issues: list[str] = []
    with subprocess.Popen(["git", "-C", str(root), "cat-file", "--batch"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as proc:
        try:
            for row in listing.stdout.split(b"\0"):
                if not row:
                    continue
                info, raw_name = row.split(b"\t", 1)
                mode, oid, stage = info.split()
                name = raw_name.decode("utf-8")
                if stage != b"0" or mode not in {b"100644", b"100755"}:
                    issues.append(f"{name}: unresolved entry, symlink or submodule cannot publish")
                    continue
                proc.stdin.write(oid + b"\n")
                proc.stdin.flush()
                header = proc.stdout.readline().split()
                if len(header) != 3 or header[:2] != [oid, b"blob"]:
                    raise RuntimeError("Cannot read staged source blob")
                size = int(header[2])
                if size > MAX_INDEX_BLOB:
                    raise RuntimeError("Staged blob exceeds publication size bound")
                raw = proc.stdout.read(size)
                if len(raw) != size or proc.stdout.read(1) != b"\n":
                    raise RuntimeError("Incomplete staged blob")
                files[name] = raw
        finally:
            proc.kill()
    return files, issues


def check_git_index(root: Path) -> list[str]:
    """Secrets staged earlier remain detectable after cleaning the worktree."""
    files, issues = read_git_index(root)
    lock_name = "research-figure/assets/upstreams.lock.json"
    try:
        locked = vendor_inventory(root, files[lock_name]) if lock_name in files else {}
    except (ValueError, OSError):
        return issues + ["Invalid staged vendor lock (details suppressed)"]
    for rel, raw in files.items():
        if rel in locked:
            record = locked[rel]
            if not safe_public_location(rel):
                issues.append(f"{rel}: forbidden staged vendor path")
            elif len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                issues.append(f"{rel}: staged upstream inventory mismatch")
            elif Path(rel).suffix.lower() in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".svg"} or Path(rel).name in {"LICENSE", "NOTICE"}:
                issues.extend(scan_content(rel, raw))
        elif not public_path(rel):
            issues.append(f"{rel}: forbidden staged path or file extension")
        else:
            issues.extend(scan_content(rel, raw))
    for rel in sorted(set(locked) - set(files)):
        issues.append(f"{rel}: locked source is not tracked by Git")
    return issues

def main() -> int:
    parser = argparse.ArgumentParser(description="Check Git-tracked RFS files for confidential state and token patterns")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--tracked", action="store_true", help="Scan staged blob bytes AND tracked worktree files; never rely on .gitignore alone")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        files = git_tracked(root) if args.tracked else [str(p.relative_to(root)) for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts and not any(seg in PRIVATE_SEGMENTS for seg in p.relative_to(root).parts)]
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    problems = check_paths(root, files)
    if args.tracked:
        try:
            problems.extend(check_git_index(root))
        except (RuntimeError, OSError, ValueError):
            problems.append("Git index scan could not finish; publication blocked")
    if problems:
        for problem in sorted(set(problems)):
            print("BLOCK: " + problem, file=sys.stderr)
        return 1
    scope = "Git index + worktree" if args.tracked else "worktree"
    print(f"Repository hygiene PASS: checked {len(files)} public source files ({scope}); no configured secret signatures found; not a guarantee of absence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())