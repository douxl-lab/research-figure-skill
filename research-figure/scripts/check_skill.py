#!/usr/bin/env python3
"""Offline Agent Skills metadata preflight (NOT the official skills-ref validator).

Use `skills-ref validate <skill-dir>` in addition when the official checker is
available. This script checks the visible open specification and package links.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ALLOWED = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _header(raw: str) -> dict:
    if not raw.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter (---)")
    before, marker, rest = raw[4:].partition("\n---\n")
    if not marker or not rest.strip():
        raise ValueError("SKILL.md must have a closing frontmatter separator and instructions")
    try:
        import yaml  # type: ignore
    except ImportError:
        # Best-effort fallback for the restricted frontmatter shape shipped with
        # this skill. It deliberately does not claim complete YAML validation.
        match_name = re.search(r"(?m)^name:\s*([^\n]+)$", before)
        match_description = re.search(r"(?ms)^description:\s*>-\s*\n((?:[ ]{2,}[^\n]*\n?)*)", before)
        match_license = re.search(r"(?m)^license:\s*([^\n]+)$", before)
        match_compat = re.search(r"(?m)^compatibility:\s*([^\n]+)$", before)
        match_version = re.search(r'(?m)^[ ]{2}version:\s*["\']?([^"\'\n]+)', before)
        match_category = re.search(r'(?m)^[ ]{2}category:\s*["\']?([^"\'\n]+)', before)
        if not match_name or not match_description:
            raise ValueError("Cannot parse name and folded description without PyYAML; install PyYAML or use skills-ref")
        desc = " ".join(line.strip() for line in match_description.group(1).splitlines() if line.strip())
        result = {"name": match_name.group(1).strip(), "description": desc}
        if match_license:
            result["license"] = match_license.group(1).strip()
        if match_compat:
            result["compatibility"] = match_compat.group(1).strip()
        if match_version or match_category:
            result["metadata"] = {}
            if match_version: result["metadata"]["version"] = match_version.group(1).strip()
            if match_category: result["metadata"]["category"] = match_category.group(1).strip()
        return result
    try:
        meta = yaml.safe_load(before)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML frontmatter: {e}") from e
    if not isinstance(meta, dict):
        raise ValueError("Frontmatter must be a YAML mapping")
    return meta


def check(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    p = root / "SKILL.md"
    if not p.is_file():
        return {"valid": False, "errors": ["SKILL.md missing"], "warnings": []}
    contents = p.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore  # noqa: F401
    except ImportError:
        warnings.append("PyYAML unavailable: limited frontmatter fallback; use official skills-ref to validate full YAML")
    try:
        meta = _header(contents)
    except ValueError as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": []}
    unknown = set(meta) - ALLOWED
    if unknown:
        errors.append(f"Unsupported frontmatter fields: {sorted(unknown)}")
    name = meta.get("name")
    if not isinstance(name, str) or len(name) > 64 or not NAME_RE.fullmatch(name):
        errors.append("name must be lowercase kebab-case (max 64 chars)")
    elif name != root.name:
        errors.append(f"name {name!r} must match directory {root.name!r}")
    desc = meta.get("description")
    if not isinstance(desc, str) or not 1 <= len(desc) <= 1024:
        errors.append("description must be 1..1024 characters")
    else:
        required_signals = ["scientific", "figure", "method", "plot", "editable"]
        if not all(s in desc.lower() for s in required_signals):
            warnings.append("Description may miss key scientific-figure selection cues")
        if "do not use" not in desc.lower():
            warnings.append("Description lacks negative selection boundary")
    compat = meta.get("compatibility")
    if compat is not None and (not isinstance(compat, str) or not 1 <= len(compat) <= 500):
        errors.append("compatibility must be a string 1..500 characters")
    mm = meta.get("metadata")
    if mm is not None and (not isinstance(mm, dict) or not all(isinstance(k, str) and isinstance(v, str) for k,v in mm.items())):
        errors.append("metadata must be a string-to-string YAML mapping")
    if len(contents.splitlines()) > 500:
        warnings.append("SKILL.md exceeds recommended 500 lines")
    for rel in sorted(set(re.findall(r"\]\(((?:references|scripts|assets)/[^)#]+)(?:#[^)]*)?\)", contents))):
        if not (root / rel).is_file():
            errors.append(f"Broken local relative link in SKILL.md: {rel}")
    # Codex extension is optional, not part of core Agent Skills spec.
    agent = root / "agents" / "openai.yaml"
    if agent.is_file():
        try:
            import yaml
            ext = yaml.safe_load(agent.read_text(encoding="utf-8"))
        except ImportError:
            # Minimal optional extension check when PyYAML is unavailable.
            ext_raw = agent.read_text(encoding="utf-8")
            pairs = dict(re.findall(r'(?m)^[ ]{2}(display_name|short_description|default_prompt):\s*"([^"\n]*)"', ext_raw))
            ext = {"interface": pairs}
        except Exception as exc:
            errors.append(f"agents/openai.yaml could not be parsed: {exc}")
        else:
            face = ext.get("interface", {}) if isinstance(ext, dict) else {}
            if not isinstance(face, dict):
                errors.append("agents/openai.yaml interface must be mapping")
            else:
                short = face.get("short_description")
                if not isinstance(short, str) or not 25 <= len(short) <= 64:
                    errors.append("agents/openai.yaml short_description should be 25..64 characters")
                if not isinstance(face.get("display_name"), str) or not face["display_name"].strip():
                    errors.append("agents/openai.yaml missing display_name")
                prompt = face.get("default_prompt", "")
                if prompt and (not isinstance(prompt, str) or "$research-figure" not in prompt):
                    errors.append("default_prompt must explicitly name $research-figure")
    else:
        warnings.append("Optional Codex agents/openai.yaml not provided")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "official_validator": "not executed; run skills-ref validate explicitly if available"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Agent Skills metadata and reference checker")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()
    result = check(Path(args.root).expanduser().resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["valid"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
