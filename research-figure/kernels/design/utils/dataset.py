"""Secure, lazy materialization of the current Parquet PaperBananaBench layout.

No network on import, retrieval=none, offline or existing complete cache.
Research inputs belong in an external work directory, never inside Skill source.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Callable

REPO_ID = "dwzhu/PaperBananaBench"
MAX_REFERENCES = 20000
MAX_IMAGES_BYTES = 768 * 1024 * 1024


def default_work_dir() -> Path:
    """Stable per-user cache that is independent of the installed Skill tree."""
    configured = os.environ.get("RFS_DESIGN_WORK_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))).expanduser()
            / "research-figure" / "design").resolve()


def _safe_image_path(raw: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw or ":" in raw or any(ord(c) < 32 for c in raw):
        raise ValueError("Unsafe reference image path")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or "." in p.parts or p.parts[0] != "images" or len(p.parts) < 2:
        raise ValueError("Reference image must stay under images/")
    if any(s.startswith(".") for s in p.parts) or p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Unsafe reference image extension")
    return p


def _record(row: dict, task: str) -> dict:
    image_name = str(row["path_to_gt_image"])
    _safe_image_path(image_name)
    if task == "diagram":
        return {
            "id": row["id"], "content": row["content"], "visual_intent": row["visual_intent"],
            "path_to_gt_image": image_name, "category": row["category"],
            "additional_info": {
                "file_name": row.get("source_pdf", ""),
                "file_path": "pdfs/" + str(row.get("source_pdf", "")),
                "diagram_page_num": row.get("diagram_page_num"),
                "method_section_title": row.get("method_section_title", ""),
                "width": row.get("width"), "height": row.get("height"),
                "rounded_ratio": row.get("rounded_ratio"),
            }, "split": row.get("split"),
        }
    raw_content = row["content"]
    return {
        "id": row["id"], "content": json.loads(raw_content) if isinstance(raw_content, str) else raw_content,
        "visual_intent": row["visual_intent"], "path_to_gt_image": image_name,
        "original_category": row.get("original_category"),
        "additional_info": {"gt_code": row.get("gt_code", ""), "width": float(row["width"]),
                            "height": float(row["height"]), "rounded_ratio": row.get("rounded_ratio")},
        "difficulty": row.get("difficulty"), "category": row["category"],
    }


def _usable(path: Path, retrieval_setting: str) -> bool:
    if path.is_symlink():
        raise ValueError("Refusing symlinked reference cache")
    reference = path / ("agent_selected_12.json" if retrieval_setting == "manual" else "ref.json")
    if not reference.is_file() or not (path / "images").is_dir():
        return False
    try:
        rows = json.loads(reference.read_text(encoding="utf-8"))
        return isinstance(rows, list) and len(rows) > 0 and all(
            isinstance(row, dict) and "path_to_gt_image" in row and
            (path / _safe_image_path(row["path_to_gt_image"])).is_file()
            for row in rows
        )
    except (ValueError, KeyError, OSError, TypeError):
        return False


def ensure_dataset(task_name: str, *, work_dir: Path, retrieval_setting: str = "auto",
                   policy: str = "auto", offline: bool = False,
                   downloader: Callable | None = None,
                   reader: Callable | None = None, revision: str | None = None) -> bool:
    """Materialize Parquet references atomically; injectable IO for offline tests.

    Incomplete directories are replaced only after a fully validated staging tree
    has been prepared. External failures are redacted and do not leak URLs/keys.
    """
    if task_name not in ("diagram", "plot"):
        raise ValueError("Dataset task must be diagram or plot")
    if policy not in ("auto", "never", "download"):
        raise ValueError("Unknown dataset download policy")
    if retrieval_setting not in ("auto", "random", "manual", "none"):
        raise ValueError("Unknown retrieval setting")
    if retrieval_setting == "none":
        return False
    base = Path(work_dir).expanduser().resolve() / "data" / "PaperBananaBench"
    task_dir = base / task_name
    if _usable(task_dir, retrieval_setting):
        return True
    if retrieval_setting == "manual":
        # The public dataset does not contain user-selected reference IDs.
        return False
    if offline or policy == "never":
        return False
    try:
        if downloader is None:
            from huggingface_hub import hf_hub_download
            downloader = hf_hub_download
        if reader is None:
            import pyarrow.parquet as pq
            reader = lambda path: pq.read_table(path).to_pylist()
        base.mkdir(parents=True, exist_ok=True)
        if base.is_symlink() or task_dir.is_symlink():
            raise ValueError("Symlinked reference directory is not allowed")
        staging = Path(tempfile.mkdtemp(prefix=".rfs-ref-", dir=base))
        try:
            image_total = 0
            for split in ("ref", "test"):
                filename = f"data/{task_name}/{split}-00000-of-00001.parquet"
                source = downloader(REPO_ID, filename, repo_type="dataset", revision=revision)
                rows = reader(source)
                if not isinstance(rows, list) or not 0 < len(rows) <= MAX_REFERENCES:
                    raise ValueError("Unexpected reference split size")
                records = []
                for row in rows:
                    record = _record(row, task_name)
                    raw_image = row.get("image") or {}
                    raw = raw_image.get("bytes") if isinstance(raw_image, dict) else None
                    if not isinstance(raw, bytes) or not raw:
                        raise ValueError("Dataset row is missing image bytes")
                    image_total += len(raw)
                    if image_total > MAX_IMAGES_BYTES:
                        raise ValueError("Reference dataset exceeds configured limit")
                    output = staging / _safe_image_path(record["path_to_gt_image"])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    if output.exists() and output.read_bytes() != raw:
                        raise ValueError("Conflicting dataset image paths")
                    output.write_bytes(raw)
                    records.append(record)
                (staging / f"{split}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if not _usable(staging, "auto"):
                raise ValueError("Staged reference dataset is incomplete")
            backup = base / (staging.name + "-old")
            moved = False
            if task_dir.exists():
                task_dir.rename(backup)
                moved = True
            try:
                staging.rename(task_dir)
            except BaseException:
                if moved:
                    backup.rename(task_dir)
                raise
            if moved:
                shutil.rmtree(backup)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    except Exception as exc:
        if policy == "download":
            raise RuntimeError(f"Reference dataset preparation failed ({type(exc).__name__}); check dependency/cache policy") from None
        return False
    return _usable(task_dir, retrieval_setting)
