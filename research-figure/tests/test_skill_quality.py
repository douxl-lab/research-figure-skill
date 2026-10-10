"""Agent Skills packaging and dispatch-behavior contracts.

The trigger corpus is a manual host-evaluation fixture: these tests do not call
an LLM and cannot claim real model-level matching precision or recall.
"""
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
from core import load_and_validate, validate_spec  # noqa: E402
from rfs import route  # noqa: E402
from check_skill import check  # noqa: E402
from external import create_handoff  # noqa: E402

ARCH = ROOT / "assets" / "spec-architecture.json"
EXACT = ROOT / "assets" / "spec-architecture-exact.json"
CLI = ROOT / "scripts" / "rfs.py"


class AgentSkillContractTests(unittest.TestCase):
    def test_local_agent_skills_spec_and_codex_metadata(self):
        report = check(ROOT)
        self.assertTrue(report["valid"], report)
        self.assertTrue(all("PyYAML unavailable" in item for item in report["warnings"]))

    def test_matching_fixture_shape_and_boundary_coverage(self):
        fixture = json.loads((ROOT / "tests" / "agent_matching_cases.json").read_text(encoding="utf-8"))
        cases = fixture["cases"]
        self.assertGreaterEqual(sum(c["activate"] for c in cases), 10)
        self.assertGreaterEqual(sum(not c["activate"] for c in cases), 10)
        self.assertEqual(len(cases), len({c["id"] for c in cases}))
        self.assertTrue(any("$paper-fig" in c["prompt"] and not c["activate"] for c in cases))
        self.assertTrue(all(isinstance(c["prompt"], str) and c["prompt"].strip() and
                            isinstance(c["activate"], bool) and c["expected_route"] for c in cases))

    @patch("rfs.paperbanana_status", return_value={"ready": True})
    def test_exact_mode_is_not_overridden_by_available_ai(self, status):
        spec, report = load_and_validate(EXACT)
        self.assertTrue(report["valid"])
        outcome = route(spec, "auto", allow_external=True)
        self.assertEqual("native-svg", outcome["engine"])
        status.assert_not_called()

    @patch("rfs.paperbanana_status", return_value={"ready": True})
    def test_creative_mode_uses_external_only_when_authorized(self, status):
        spec, _ = load_and_validate(ARCH)
        spec["generation"] = {"intent": "creative"}
        with_auth = route(spec, "auto", allow_external=True)
        self.assertEqual("paperbanana", with_auth["engine"])
        self.assertFalse(with_auth["degraded"])
        without_auth = route(spec, "auto", allow_external=False)
        self.assertEqual("prompt-only", without_auth["engine"])
        self.assertFalse(without_auth["degraded"])

    def test_unrelated_engine_cannot_override_editable_reconstruction(self):
        spec, _ = load_and_validate(ARCH)
        spec["type"] = "editable_reconstruction"
        with self.assertRaisesRegex(ValueError, "handoff"):
            route(spec, "paperbanana", True)

    def test_invalid_generation_intent_is_rejected(self):
        spec, _ = load_and_validate(ARCH)
        spec["generation"] = {"intent": "unbounded"}
        report = validate_spec(spec, ARCH)
        self.assertFalse(report["valid"])
        self.assertIn("generation.intent", " ".join(report["errors"]))

    def test_pptx_only_target_is_partial_not_misreported_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_spec = Path(tmp) / "arch.json"
            spec, _ = load_and_validate(ARCH)
            spec["delivery"] = {"editable": True, "formats": ["pptx"]}
            local_spec.write_text(json.dumps(spec), encoding="utf-8")
            out = Path(tmp) / "out"
            proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(local_spec),
                                   "--out", str(out)], text=True, capture_output=True, cwd=tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertEqual("PROMPT_READY_NOT_RENDERED", payload["status"])
            self.assertEqual(["pptx"], payload["pending_formats"])
            self.assertFalse((out / "figure.svg").is_file())
            self.assertTrue((out / "creative-prompts" / "figure-prompt.md").is_file())

    def test_handoff_contains_versioned_figure_spec_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec, _ = load_and_validate(ARCH)
            created = create_handoff(spec, ARCH, Path(tmp), "paper-fig")
            self.assertEqual("NOT_EXECUTED", created["status"])
            self.assertEqual(spec, json.loads(Path(created["spec_snapshot"]).read_text(encoding="utf-8")))
            self.assertIn("No PPTX", created["warning"])

    def test_execute_cli_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(CLI), "route", "--spec", str(ARCH)],
                                  text=True, capture_output=True, cwd=tmp)
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            self.assertEqual("prompt-only", json.loads(proc.stdout)["plan"]["engine"])

    def test_old_paperbanana_candidates_block_accidental_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rfs-output"
            out.mkdir()
            (out / "paperbanana_7.png").write_bytes(b"stale candidate")
            proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(ARCH),
                                   "--out", str(out)], text=True, capture_output=True)
            self.assertEqual(2, proc.returncode)
            self.assertIn("Output exists", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
