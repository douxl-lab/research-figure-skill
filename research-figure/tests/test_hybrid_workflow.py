"""Offline core-hybrid routing and real layout composition fixtures, not model QA."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import workflow

DIAGRAM = {"schema_version": "1.0.0", "kind": "diagram"}


def caps():
    return {
        "design": {"root": str(ROOT / "kernels/design"),
                   "files": {"skill/native_host.py": True, "skill/exchange.py": True}},
        "layout": {"root": str(ROOT / "kernels/layout"),
                   "files": {"scripts/render.py": True, "scripts/validate.py": True}},
    }


class HybridRoutingTests(unittest.TestCase):
    def test_registry_retains_two_core_workflows_and_image_first_default(self):
        data = json.loads((ROOT / "assets/capabilities.json").read_text())
        self.assertEqual(data["mechanism_default"]["strategy"], "complete-image-first")
        self.assertIn("hybrid-assembly", data["core_production_workflows"])
        self.assertEqual(next(m for m in data["modules"] if m["id"] == "hybrid-assembly")["tier"], "core")

    def test_image_first_default_is_unchanged(self):
        self.assertEqual(workflow.make_plan(DIAGRAM, caps(), host_image_tool="fixture-tool")["mode"], "design-native")

    def test_explicit_hybrid_overrides_image_first(self):
        plan = workflow.make_plan(DIAGRAM, caps(), mode="hybrid-assembly", host_image_tool="fixture-tool")
        self.assertEqual(plan["mode"], "hybrid-assembly")
        self.assertEqual(plan["status"], "HOST_ACTION_REQUIRED")
        self.assertFalse(plan["blockers"])
        self.assertIn("references/design-core.md", plan["references"])
        self.assertIn("references/mechanism-figure-workflow.md", plan["references"])

    def test_no_generator_blocks_instead_of_using_plain_code(self):
        plan = workflow.make_plan(DIAGRAM, caps(), mode="hybrid-assembly")
        self.assertEqual(plan["mode"], "hybrid-assembly")
        self.assertEqual(plan["status"], "BLOCKED")

    def test_generic_external_permission_is_not_a_usable_asset_runtime(self):
        plan = workflow.make_plan(DIAGRAM, caps(), mode="hybrid-assembly", allow_external=True)
        self.assertEqual(plan["status"], "BLOCKED")

    def test_configured_image2_needs_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "SKILL.md").write_text("# Synthetic local-runtime fixture\n")
            for name in ("generate_image.py", "edit_image.py"):
                (root / "scripts" / name).write_text("# Not executed\n")
            self.assertEqual(workflow.make_plan(DIAGRAM, caps(), mode="hybrid-assembly", image2_root=root)["status"], "BLOCKED")
            plan = workflow.make_plan(DIAGRAM, caps(), mode="hybrid-assembly", image2_root=root, allow_external=True)
            self.assertEqual(plan["status"], "HOST_ACTION_REQUIRED")

    def test_legacy_contract_is_not_silently_converted(self):
        plan = workflow.make_plan({"type": "architecture"}, caps(), mode="hybrid-assembly", host_image_tool="fixture-tool")
        self.assertEqual(plan["status"], "BLOCKED")

    def test_measured_plots_never_use_hybrid_generation(self):
        with self.assertRaises(ValueError):
            workflow.make_plan({"schema_version": "1.0.0", "kind": "plot"}, caps(), mode="hybrid-assembly", host_image_tool="fixture-tool")
        plan = workflow.make_plan({**DIAGRAM, "datasets": [{"id": "measured"}]}, caps(), mode="hybrid-assembly", host_image_tool="fixture-tool")
        self.assertEqual(plan["status"], "BLOCKED")

    def test_hybrid_content_kind_is_not_production_mode(self):
        spec = {"schema_version": "1.0.0", "kind": "hybrid"}
        self.assertEqual(workflow.make_plan(spec, caps(), host_image_tool="fixture-tool")["mode"], "source-preserving-handoff")
        with self.assertRaises(ValueError):
            workflow.make_plan(spec, caps(), mode="hybrid-assembly", host_image_tool="fixture-tool")

    def test_dry_run_does_not_bypass_hybrid_capability_checks(self):
        plan = workflow.make_plan(DIAGRAM, caps(), mode="hybrid-assembly", host_image_tool="fixture-tool", dry_run=True)
        self.assertEqual(plan["status"], "BLOCKED")

    def test_preparation_snapshots_source_but_does_not_fake_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "job"
            spec = ROOT / "assets/figure-spec-v1-example.json"
            original = spec.read_bytes()
            plan = workflow.make_plan(json.loads(original), caps(), mode="hybrid-assembly", host_image_tool="fixture-tool")
            result = workflow.execute(plan, spec, out)
            self.assertEqual(result["status"], "HOST_ACTION_REQUIRED")
            self.assertEqual(result["next_task"]["id"], "scaffold")
            job = json.loads(Path(result["job"]).read_text())
            self.assertEqual(job["source_contract"]["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual((out / "figure-spec.json").read_bytes(), original)
            self.assertEqual([stage["id"] for stage in job["stages"]], ["scaffold", "assets", "composition", "review"])
            self.assertEqual(job["stages"][1]["depends_on"], ["scaffold"])
            self.assertTrue(all(s["status"] == "PENDING" and not s["artifacts"] for s in job["stages"]))
            self.assertFalse(job["generation_executed"])
            self.assertFalse(job["rendering_executed"])
            self.assertEqual(job["asset_backend"]["kind"], "host")
            self.assertEqual(job["scientific_review"], "PENDING")
            self.assertFalse(list(out.glob("*.png")))
            self.assertFalse(list(out.glob("*.svg")))
            with self.assertRaises(ValueError):
                workflow.execute(plan, spec, out)

    def test_fixture_requests_cover_chinese_and_english(self):
        cases = json.loads((ROOT / "tests/agent_matching_cases.json").read_text())["cases"]
        matches = [c for c in cases if c["expected_route"] == "hybrid-assembly"]
        self.assertEqual({c["lang"] for c in matches}, {"zh", "en"})
        self.assertTrue(all(c["activate"] for c in matches))


class RealLayoutCompositionFixture(unittest.TestCase):
    def test_scaffold_slot_accepts_raster_asset_without_changing_labels_or_edges(self):
        """Exercise the existing bundled renderer, with an explicitly synthetic asset."""
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            layout = {
                "figure": {"id": "synthetic-hybrid-fixture", "width": "double", "font": "helvetica"},
                "layout": "row", "gap": 24,
                "panels": [{"id": "fixture", "body": [{"row": {"gap": 24, "body": [
                    {"id": "input", "text": "Input features", "role": "input"},
                    {"id": "encoder", "text": "Encoder", "role": "encoder"},
                    {"id": "embedding", "text": "Embedding", "role": "output"}
                ]}}, {"id": "art", "shape": "image", "w": 50, "h": 30, "fit": "contain"}]}],
                "edges": [{"from": "input", "to": "encoder"}, {"from": "encoder", "to": "embedding"}],
                "caption": "Synthetic software fixture; not a research result.",
            }
            renderer = ROOT / "kernels/layout/scripts/render.py"

            def render(name, spec):
                path = base / (name + ".json")
                path.write_text(json.dumps(spec))
                done = subprocess.run([sys.executable, str(renderer), str(path), "-o", str(base / name), "-f", "svg", "--json"],
                                      text=True, capture_output=True, timeout=30, check=False)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                return ET.fromstring((base / (name + ".svg")).read_bytes())

            scaffold = render("scaffold", layout)
            original = copy.deepcopy(layout)
            Image.new("RGBA", (100, 60), (110, 120, 140, 180)).save(base / "synthetic-asset.png")
            composed = copy.deepcopy(layout)
            composed["panels"][0]["body"][1]["src"] = "synthetic-asset.png"
            final = render("composed", composed)
            self.assertEqual(layout, original)
            self.assertEqual(scaffold.get("viewBox"), final.get("viewBox"))
            ns = "{http://www.w3.org/2000/svg}"
            self.assertEqual(len(list(scaffold.iter(ns + "image"))), 0)
            self.assertEqual(len(list(final.iter(ns + "image"))), 1)
            picture = next(final.iter(ns + "image"))
            self.assertTrue(picture.get("{http://www.w3.org/1999/xlink}href", "").startswith("data:image/png;base64,"))
            for label in ("Input features", "Encoder", "Embedding"):
                self.assertIn(label, "".join(final.itertext()))
            # Directed connectors are separate vector paths and must not move.
            arrows = lambda svg: [(e.get("d"), e.get("marker-end")) for e in svg.iter(ns + "path") if e.get("marker-end")]
            self.assertTrue(arrows(scaffold))
            self.assertEqual(arrows(scaffold), arrows(final))


if __name__ == "__main__":
    unittest.main()
