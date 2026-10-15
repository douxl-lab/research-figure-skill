"""Offline discovery-contract checks; not an LLM invocation benchmark.

Natural-language route labels are adjudicated fixtures, not model predictions.
Real CLI routing is tested separately from the metadata/corpus shape.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import bridge
from check_skill import _header, check

CORPUS = ROOT / "tests" / "agent_matching_cases.json"
PAIRS = ROOT / "tests" / "skill_selection_pairs.json"
EXAMPLE = ROOT / "assets" / "figure-spec-v1-example.json"
PLOT = ROOT / "assets" / "figure-plot-v1-example.json"
CLI = ROOT / "scripts" / "rfs.py"


class SkillSelectionContract(unittest.TestCase):
    def test_public_skill_metadata_is_discriminating_and_valid(self):
        report = check(ROOT)
        self.assertTrue(report["valid"], report)
        meta = _header((ROOT / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(meta["name"], "research-figure")
        desc = meta["description"].lower()
        for term in ("scientific", "method", "plot", "editable", "do not use", "tikz"):
            self.assertIn(term, desc)
        self.assertLess(len(desc), 800, "Keep startup selection metadata selective")
        self.assertNotIn("general image generation", desc)
        ui = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$research-figure", ui)
        self.assertIn("scientific", ui)

    def test_missing_pyyaml_fallback_still_validates_ui_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "research-figure"
            (skill / "agents").mkdir(parents=True)
            shutil.copyfile(ROOT / "SKILL.md", skill / "SKILL.md")
            (skill / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Research Figure"\n'
                '  short_description: "bad"\n'
                '  default_prompt: "Use $research-figure for a paper figure."\n',
                encoding="utf-8",
            )
            with patch.dict(sys.modules, {"yaml": None}):
                report = check(skill)
            self.assertIn("short_description should be 25..64",
                          " ".join(report["errors"]))

    def test_positive_negative_and_near_miss_cases(self):
        cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), len({c["id"] for c in cases}))
        self.assertGreaterEqual(sum(case["activate"] for case in cases), 20)
        self.assertGreaterEqual(sum(not case["activate"] for case in cases), 20)
        self.assertTrue(any(case["activate"] and case["expected_route"] == "tikz" for case in cases))
        self.assertTrue(any(case["activate"] and case["expected_route"] == "plot-matplotlib" for case in cases))
        self.assertTrue(any(not case["activate"] and "$paperbanana" in case["prompt"] for case in cases))
        self.assertTrue(any(not case["activate"] and "TikZ" in case["prompt"] for case in cases))
        self.assertTrue(all(isinstance(case["prompt"], str) and len(case["prompt"]) >= 10
                            and type(case["activate"]) is bool and
                            isinstance(case["expected_route"], str) and case["lang"] in {"zh", "en"}
                            for case in cases))

    def test_paired_skill_intents_are_exclusive(self):
        catalog = json.loads(PAIRS.read_text(encoding="utf-8"))
        self.assertEqual(catalog["skills"], ["research-figure", "paperbanana"])
        cases = catalog["cases"]
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        counts = {kind: sum(case["intended_skill"] == kind for case in cases)
                  for kind in ("research-figure", "paperbanana", "none")}
        self.assertGreaterEqual(counts["research-figure"], 8)
        self.assertGreaterEqual(counts["paperbanana"], 5)
        self.assertGreaterEqual(counts["none"], 8)
        self.assertTrue(all(case["prompt"].strip() and case["category"] and case["lang"] in ("en", "zh")
                            and case["intended_skill"] in counts for case in cases))
        # These are human-labelled pairs: a matching host evaluation is still required
        # before claiming accuracy, precision or recall.

    def test_canonical_backend_dispatch_matches_explicit_user_intent(self):
        diagram = bridge._api()[1].load_spec(EXAMPLE)
        source_plot = bridge._api()[1].load_spec(PLOT)
        self.assertEqual(bridge.explain_route(diagram)["engine"], "prompt-only")
        self.assertEqual(bridge.explain_route(diagram, allow_external=True)["engine"], "paperbanana")
        self.assertEqual(bridge.explain_route(diagram, engine="tikz")["engine"], "tikz")
        self.assertFalse(bridge.explain_route(diagram, engine="tikz")["requires_external"])
        self.assertEqual(bridge.explain_route(source_plot)["engine"], "plot-matplotlib")
        with self.assertRaises(ValueError):
            bridge.explain_route(source_plot, engine="tikz")
        with self.assertRaises(ValueError):
            bridge.explain_route(diagram, engine="native-svg")

    def test_live_cli_route_does_not_execute_a_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for source, opts, engine in [
                (EXAMPLE, [], "prompt-only"),
                (EXAMPLE, ["--engine", "tikz"], "tikz"),
                (PLOT, [], "plot-matplotlib")
            ]:
                result = subprocess.run([sys.executable, str(CLI), "route", "--spec", str(source), *opts],
                                        cwd=path, text=True, capture_output=True, timeout=25)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["plan"]["engine"], engine)
            self.assertEqual(list(path.iterdir()), [], "Routing must have no generation side effects")


if __name__ == "__main__":
    unittest.main()
