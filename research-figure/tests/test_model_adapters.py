"""V0.3.1 offline model matching and provider safety regression.

These do NOT make external API calls, nor do they claim model image quality.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from core import RFSValidationError, load_and_validate
from model_catalog import catalog, choose_model, load_registry
from prompting import build_prompt, save_prompt_pack
from external import paperbanana_status, call_paperbanana

ARCH = ROOT / "assets" / "spec-architecture.json"
CLI = ROOT / "scripts" / "rfs.py"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082")


class CurrentModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.spec, _ = load_and_validate(ARCH)

    def tearDown(self):
        self.temp.cleanup()

    def test_latest_verified_catalog(self):
        data, path = load_registry()
        self.assertEqual("2026-10-09", data["verified_at"])
        self.assertTrue(path.is_file())
        self.assertGreaterEqual(len(data["sources"]), 4)
        ids = {x["id"] for x in data["models"]}
        self.assertTrue({"gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gemini-nano-banana-2.1", "gemini-3-pro-image"} <= ids)

    def test_google_balanced_and_quality(self):
        self.assertEqual("gemini-nano-banana-2.1", choose_model(provider="gemini")["id"])
        self.assertEqual("gemini-3-pro-image", choose_model(provider="gemini", priority="quality")["id"])

    def test_openai_speed_and_refinement(self):
        self.assertEqual("gpt-image-2.5-flare", choose_model(provider="openai", priority="speed")["id"])
        self.assertEqual("gpt-image-2.5-sunburst", choose_model(provider="openai", priority="precise_edit", stage="refine")["id"])

    def test_unknown_and_cross_provider_rejected(self):
        with self.assertRaisesRegex(RFSValidationError, "not in registry"):
            choose_model(model="imaginary-model-2027")
        with self.assertRaisesRegex(RFSValidationError, "belongs to"):
            choose_model(model="gpt-image-2.5-flare", provider="gemini")

    def test_model_specific_prompts_keep_exact_science(self):
        candidates = {}
        for model in ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gemini-nano-banana-2.1", "gemini-3-pro-image"):
            txt = build_prompt(self.spec, profile="generic", model=model)
            self.assertIn("router -> fusion", txt)
            self.assertIn(model, txt)
            self.assertIn("No fabricated numerical results", txt)
            self.assertIn("offline candidate only", txt)
            candidates[model] = txt
        self.assertEqual(len(set(candidates.values())), 4)

    def test_refine_receipt_includes_model_and_reference(self):
        ref = self.root / "ref.png"
        ref.write_bytes(PNG)
        result = save_prompt_pack(self.spec, ARCH, self.root / "out", profile="generic",
                    model="gpt-image-2.5-sunburst", stage="refine", reference=str(ref),
                    change="Fix only the outgoing connector", region="Router")
        self.assertEqual("PROMPT_READY_NOT_RENDERED", result["status"])
        self.assertEqual("gpt-image-2.5-sunburst", result["model_id"])
        plan = json.loads(Path(result["model_call_plan"]).read_text())
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual("ADVISORY_NOT_SUBMITTED", plan["status"])
        self.assertFalse(plan["provider_api_call_performed"])
        self.assertFalse(plan["provider_access_verified"])
        self.assertIn("Attach actual reference", plan["input_requirements"])
        self.assertEqual("gpt-image-2.5-sunburst", receipt["model_id"])
        self.assertIn("model-call-plan.json", receipt["hashes"])

    def test_future_registry_extension_needs_no_code_changes(self):
        registry, _ = load_registry()
        custom = copy.deepcopy(registry)
        extra = copy.deepcopy(custom["models"][0])
        extra["id"] = "future-image-model-example"
        extra["draft_guidance"] = ["Future extra model design directive for this example."]
        custom["models"].append(extra)
        custom["default_candidates"]["balanced"]["openai"] = extra["id"]
        custom["verified_at"] = "2026-10-10"
        path = self.root / "custom-registry.json"
        path.write_text(json.dumps(custom))
        selection = choose_model(provider="openai", priority="balanced", registry=path)
        self.assertEqual(extra["id"], selection["id"])
        prompt = build_prompt(self.spec, profile="generic", model="auto", provider="openai", registry=path)
        self.assertIn("Future extra model design directive", prompt)

    def test_malformed_registry_rejected(self):
        reg, _ = load_registry()
        reg["models"].append(copy.deepcopy(reg["models"][0]))
        path = self.root / "bad.json"
        path.write_text(json.dumps(reg))
        with self.assertRaisesRegex(RFSValidationError, "Duplicate"):
            load_registry(path)

    def test_model_cli_listing_and_prompt(self):
        proc = subprocess.run([sys.executable, str(CLI), "models", "--provider", "openai", "--priority", "precise_edit"],
                              text=True, capture_output=True)
        self.assertEqual(0, proc.returncode, proc.stderr + proc.stdout)
        self.assertEqual("gpt-image-2.5-sunburst", json.loads(proc.stdout)["recommended_candidate"])
        pr = subprocess.run([sys.executable, str(CLI), "prompt", "--spec", str(ARCH), "--model", "auto",
                             "--provider", "gemini", "--out", str(self.root / "prompt")], text=True, capture_output=True)
        self.assertEqual(0, pr.returncode, pr.stderr + pr.stdout)
        self.assertEqual("gemini-nano-banana-2.1", json.loads(pr.stdout)["model_id"])

    def test_run_prompt_only_passes_model_id(self):
        proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(ARCH), "--model", "auto",
                              "--provider", "openai", "--out", str(self.root / "r")], text=True, capture_output=True)
        self.assertEqual(0, proc.returncode, proc.stderr + proc.stdout)
        content = json.loads(proc.stdout)
        self.assertEqual("PROMPT_READY_NOT_RENDERED", content["status"])
        self.assertEqual("gpt-image-2.5-flare", content["prompt_pack"]["model_id"])

    def test_numeric_data_never_uses_image_model(self):
        plot = ROOT / "assets" / "spec-plot-demo.json"
        proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(plot), "--model", "auto",
                              "--out", str(self.root / "bad")], text=True, capture_output=True)
        self.assertEqual(2, proc.returncode)
        self.assertIn("direct prompt compilation only", proc.stdout)

    def test_paperbanana_retired_preview_preflight(self):
        pb = self.root / "pb"
        (pb / "skill").mkdir(parents=True)
        (pb / "configs").mkdir(parents=True)
        (pb / "skill" / "run.py").write_text("print('should not run')\n")
        (pb / "configs" / "model_config.template.yaml").write_text('defaults:\n  image_gen_model_name: "gemini-3.1-flash-image-preview"\n')
        with patch.dict(os.environ, {"PAPERBANANA_ROOT": str(pb), "GOOGLE_API_KEY": "dummy-placeholder"}):
            status = paperbanana_status()
            self.assertTrue(status["ready"])
            self.assertIn("shut down", status["image_model_warning"])
            with self.assertRaisesRegex(RFSValidationError, "shut down"):
                call_paperbanana(self.spec, self.root / "pb_out", allow_external=True)
            self.assertFalse((self.root / "pb_out" / "paperbanana-method.txt").exists())


if __name__ == "__main__":
    unittest.main()
