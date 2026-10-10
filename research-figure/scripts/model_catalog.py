"""Validated, overridable offline registry for image-model-aware RFS prompts.

Registry selection is advisory: does not make network requests, check account access,
or certify a model's performance on scientific diagrams.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from core import ASSETS, RFSValidationError, hash_file, read_json

DEFAULT_REGISTRY = ASSETS / "prompts" / "model-registry.json"
PROVIDERS = {"any", "openai", "gemini"}
PRIORITIES = {"speed", "balanced", "quality", "precise_edit"}
STAGES = {"draft", "refine"}
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")


def load_registry(path: str | Path | None = None) -> tuple[dict, Path]:
    p = Path(path).expanduser().resolve() if path else DEFAULT_REGISTRY.resolve()
    try:
        data = read_json(p)
    except (OSError, ValueError) as exc:
        raise RFSValidationError(f"Cannot load model registry: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != "rfs-model-registry/1":
        raise RFSValidationError("Model registry must use schema rfs-model-registry/1")
    if not isinstance(data.get("verified_at"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["verified_at"]):
        raise RFSValidationError("Model registry needs a verified_at YYYY-MM-DD")
    rows = data.get("models")
    if not isinstance(rows, list) or not rows:
        raise RFSValidationError("Model registry has no models")
    ids = set()
    for x in rows:
        if not isinstance(x, dict) or not isinstance(x.get("id"), str) or not MODEL_ID_RE.fullmatch(x["id"]):
            raise RFSValidationError("Model entry has invalid ID")
        if x["id"] in ids:
            raise RFSValidationError(f"Duplicate model {x['id']}")
        ids.add(x["id"])
        if x.get("provider") not in (PROVIDERS - {"any"}) or x.get("prompt_profile") not in {"gemini", "gpt-image", "generic"}:
            raise RFSValidationError(f"Invalid provider/profile for {x['id']}")
        if not isinstance(x.get("stages"), list) or not x["stages"] or not set(x["stages"]) <= STAGES:
            raise RFSValidationError(f"Invalid supported stages for {x['id']}")
        for field in ("draft_guidance", "refinement_guidance"):
            if not isinstance(x.get(field), list) or not all(isinstance(z, str) for z in x[field]):
                raise RFSValidationError(f"Invalid {field} for {x['id']}")
    defaults = data.get("default_candidates", {})
    if not isinstance(defaults, dict):
        raise RFSValidationError("Invalid default_candidates mapping")
    for priority in PRIORITIES:
        entry = defaults.get(priority)
        if not isinstance(entry, dict) or not PROVIDERS <= set(entry):
            raise RFSValidationError(f"Missing default candidates for {priority}")
        for provider, mid in entry.items():
            if mid not in ids:
                raise RFSValidationError(f"Unknown default model {mid}")
            actual = next(x for x in rows if x["id"] == mid)
            if provider != "any" and actual["provider"] != provider:
                raise RFSValidationError(f"Provider mismatch for {mid}")
    return data, p


def choose_model(*, model: str = "auto", provider: str = "any", priority: str = "balanced",
                 stage: str = "draft", registry: str | Path | None = None) -> dict[str, Any]:
    if provider not in PROVIDERS or priority not in PRIORITIES or stage not in STAGES:
        raise RFSValidationError("Bad model selection provider/priority/stage")
    data, path = load_registry(registry)
    model_id = (data["default_candidates"][priority][provider] if model == "auto" else model)
    found = next((r for r in data["models"] if r["id"] == model_id), None)
    if found is None:
        raise RFSValidationError(f"Model {model_id!r} not in registry; update local JSON registry or select a listed model")
    if provider != "any" and found["provider"] != provider:
        raise RFSValidationError(f"Model {model_id} belongs to {found['provider']}, not {provider}")
    if stage not in found["stages"]:
        raise RFSValidationError(f"Model {model_id} does not support registry stage {stage}")
    result = copy.deepcopy(found)
    result.update({
        "selection": "curated_offline_default" if model == "auto" else "user_selected",
        "priority": priority,
        "registry_verified_at": data["verified_at"],
        "registry_path": str(path),
        "registry_sha256": hash_file(path),
        "access_verified": False,
        "api_called": False,
    })
    return result


def catalog(*, provider: str = "any", priority: str = "balanced", stage: str = "draft",
            registry: str | Path | None = None) -> dict:
    data, path = load_registry(registry)
    selection = choose_model(provider=provider, priority=priority, stage=stage, registry=path)
    listed = [{"id": x["id"], "provider": x["provider"], "lifecycle": x["lifecycle"],
               "best_for": x.get("best_for", [])} for x in data["models"]
              if (provider in ("any", x["provider"])) and stage in x["stages"]]
    return {"registry_verified_at": data["verified_at"], "registry_sha256": hash_file(path),
            "recommended_candidate": selection["id"], "priority": priority, "provider": provider,
            "stage": stage, "models": listed, "status": "CURATED_OFFLINE_ONLY_NOT_LIVE_AVAILABILITY",
            "note": data.get("offline_disclaimer")}
