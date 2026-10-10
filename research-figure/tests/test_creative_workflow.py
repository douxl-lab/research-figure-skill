"""Contract tests for A/C primary routing, prompt specialization and three-source reconstruction."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from core import RFSValidationError, load_and_validate, validate_spec
from prompting import build_prompt, save_prompt_pack, save_comparison, design_brief
from reconstruction import create_reconstruction_package, audit_reconstruction_package
from rfs import route

ARCH = ROOT / "assets" / "spec-architecture.json"
PLOT = ROOT / "assets" / "spec-plot-demo.json"
CLI = ROOT / "scripts" / "rfs.py"

# Different tiny PNG test fixtures for hash identity; not scientific figures.
TEST_PNG_A = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082")
TEST_PNG_B = TEST_PNG_A + b"distinct-test-suffix"

class CreativeFirstTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.spec, _ = load_and_validate(ARCH)
        self.img1 = self.out / "candidate_a.png"
        self.img2 = self.out / "candidate_b.png"
        self.img1.write_bytes(TEST_PNG_A)
        self.img2.write_bytes(TEST_PNG_B)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_creative_when_generation_intent_omitted(self):
        spec = copy.deepcopy(self.spec)
        spec["generation"] = {}
        self.assertEqual("prompt-only", route(spec)["engine"])

    def test_exact_uses_native_svg_when_explicit(self):
        spec = copy.deepcopy(self.spec)
        spec["generation"] = {"intent": "exact"}
        self.assertEqual("native-svg", route(spec)["engine"])

    def test_force_svg_on_creative_discloses_visual_degradation(self):
        self.assertTrue(route(self.spec, "native-svg")["degraded"])

    def test_numeric_cannot_be_image_generator(self):
        spec,_ = load_and_validate(PLOT)
        self.assertEqual("plot-matplotlib", route(spec)["engine"])
        with self.assertRaisesRegex(RFSValidationError, "Measured"):
            route(spec, engine="paperbanana", allow_external=True)

    def test_spec_invalid_design_is_rejected(self):
        spec=copy.deepcopy(self.spec)
        spec["design"]["reading_path"] = "teleport"
        self.assertFalse(validate_spec(spec, ARCH)["valid"])
        spec["design"]["reading_path"] = "left_to_right"
        spec["design"]["avoid"] = [1]
        self.assertFalse(validate_spec(spec, ARCH)["valid"])

    def test_custom_profile_key_can_be_added_without_changing_cli_parser(self):
        cmd=subprocess.run([sys.executable, str(CLI), "prompt", "--spec", str(ARCH),
            "--profile", "nonexistent-profile", "--out", str(self.out/"future")],
            capture_output=True,text=True)
        self.assertEqual(2,cmd.returncode)
        self.assertIn("Unknown profile",cmd.stdout)
        self.assertNotIn("invalid choice",cmd.stdout)

    def test_model_profiles_have_science_and_same_nodes(self):
        prompts = [build_prompt(self.spec, profile=profile) for profile in ("generic", "gemini", "gpt-image")]
        self.assertEqual(len(set(prompts)), 3)
        for p in prompts:
            self.assertIn("encoders", p)
            self.assertIn("labelquery", p)
            self.assertIn("router -> fusion", p)
            self.assertIn("No fabricated numerical results", p)
            self.assertIn("layout", p.lower())
            self.assertIn("exact", p.lower())

    def test_refine_requires_real_reference_and_local_change(self):
        with self.assertRaisesRegex(RFSValidationError, "Refinement requires"):
            build_prompt(self.spec, profile="gemini", stage="refine", change="Fix one arrow")
        text = build_prompt(self.spec, profile="gemini", stage="refine", reference=str(self.img1),
                            change="Uncross the arrow between label-query and router", region="Router region")
        self.assertIn("Preserve all unaffected regions", text)
        self.assertIn("candidate_a.png", text)
        self.assertIn("Router region", text)

    def test_prompt_pack_receipt_explicitly_unrendered(self):
        out=self.out / "prompt"
        result=save_prompt_pack(self.spec, ARCH, out, profile="gpt-image")
        self.assertEqual("PROMPT_READY_NOT_RENDERED", result["status"])
        receipt=json.loads((out / "prompt-receipt.json").read_text())
        self.assertFalse(receipt["render_verified"])
        self.assertEqual("NOT_EXECUTED", receipt["provider_execution"])
        with self.assertRaisesRegex(RFSValidationError, "exists"):
            save_prompt_pack(self.spec, ARCH, out, profile="gpt-image")

    def test_fake_candidate_image_bytes_rejected(self):
        bad=self.out / "bad.png"
        bad.write_bytes(b"not a real image" * 20)
        with self.assertRaisesRegex(RFSValidationError, "plausible image"):
            save_comparison(self.spec, ARCH, [str(self.img1),str(bad)], self.out / "bad-cmp")

    def test_candidate_compare_requires_distinct_images(self):
        with self.assertRaisesRegex(RFSValidationError, "distinct"):
            save_comparison(self.spec, ARCH, [str(self.img1),str(self.img1)], self.out / "compare")
        result=save_comparison(self.spec, ARCH, [str(self.img1),str(self.img2)], self.out / "compare")
        self.assertEqual("REVIEW_PROMPT_READY_NOT_EXECUTED", result["status"])
        self.assertIn("topology", (self.out/"compare"/"comparison-prompt.md").read_text().lower())

    def test_compiler_brief_cannot_masquerade_as_image_anchored_notes(self):
        src=self.out / "pre-image.md"
        src.write_text(design_brief(self.spec),encoding="utf-8")
        with self.assertRaisesRegex(RFSValidationError,"pre-image design brief"):
            create_reconstruction_package(self.spec, ARCH, reference=self.img1,
                                          notes=src, out=self.out/"reject")
        with self.assertRaisesRegex(RFSValidationError,"unfilled template"):
            create_reconstruction_package(self.spec, ARCH, reference=self.img1,
                notes=ROOT/"assets"/"design-notes-template.md", out=self.out/"reject2")

    def test_reconstruction_requires_text_notes_and_reference(self):
        notes=self.out/"notes.md"
        notes.write_text("Layout: main left-to-right route. Typography: native text. Arrows: attach to semantic nodes. Preserve the approved group arrangement.")
        result=create_reconstruction_package(self.spec, ARCH, reference=self.img1, notes=notes,
                                             out=self.out / "pack", backend="paper-fig", approved=True)
        self.assertEqual("READY_FOR_BACKEND_HANDOFF_NOT_EXECUTED", result["status"])
        p=self.out/"pack"
        self.assertIn("three", (p / "handoff.md").read_text().lower())
        self.assertTrue((p / "reference" / "approved.png").exists())
        a=audit_reconstruction_package(p)
        self.assertEqual("PASS",a["integrity"])
        self.assertEqual("PENDING",a["native_editability"])
        (p / "design-notes.md").write_text("modified")
        b=audit_reconstruction_package(p)
        self.assertEqual("FAIL",b["integrity"])
        self.assertIn("design-notes.md",b["mismatched_files"])

    def test_package_without_approval_is_not_locked(self):
        notes=self.out/"notes.md"
        notes.write_text("Layout: horizontal regions; important arrows avoid labels. Style: clean academic, precise text, no fabricated measurements.")
        res=create_reconstruction_package(self.spec, ARCH, reference=self.img1, notes=notes, out=self.out/"p")
        self.assertFalse(res["approved_by_user"])
        data=json.loads((self.out / "p" / "reconstruction-manifest.json").read_text())
        self.assertFalse(data["design_lock"])

    def test_cli_auto_creative_does_not_silently_generate_svg(self):
        cp=subprocess.run([sys.executable,str(CLI),"run","--spec",str(ARCH),"--out",str(self.out/"run")],capture_output=True,text=True)
        self.assertEqual(0,cp.returncode,cp.stderr+cp.stdout)
        data=json.loads(cp.stdout)
        self.assertEqual("PROMPT_READY_NOT_RENDERED",data["status"])
        self.assertFalse((self.out/"run"/"figure.svg").exists())

if __name__ == "__main__":
    unittest.main()
