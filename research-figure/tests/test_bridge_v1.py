"""Canonical cross-repository FigureSpec v1 checks (no paid provider traffic)."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import bridge

SUPPORTED = (ROOT / "protocol" / "contract.py").exists()


def fixture(kind="diagram"):
    source = "Inputs feed an Encoder, which produces Embeddings."
    evidence = [{"source_id": "input", "quote": source}]
    science = {"schema_version": "1.0.0", "figure_id": "minimal-v1", "kind": "diagram",
       "nodes": [{"id": "inputs", "label": "Inputs", "kind": "input", "evidence": evidence},
                 {"id": "encoder", "label": "Encoder", "kind": "module", "evidence": evidence},
                 {"id": "embeddings", "label": "Embeddings", "kind": "output", "evidence": evidence}],
       "edges": [{"id": "edge1", "source": "inputs", "target": "encoder", "kind": "data_flow", "directed": True, "evidence": evidence},
                 {"id": "edge2", "source": "encoder", "target": "embeddings", "kind": "data_flow", "directed": True, "evidence": evidence}],
       "groups": [], "labels": [], "datasets": [],
       "sources": [{"id": "input", "kind": "user_text", "content": source,
                    "sha256": hashlib.sha256(source.encode()).hexdigest()}],
       "constraints": {"locked": True, "required_labels": ["Inputs", "Encoder", "Embeddings"],
                       "layout": [], "visual": [], "negative": []},
       "design": {"layout": "Left to right with no crossings", "composition": "One principal flow",
                  "palette": ["#2F6B9A", "#FFFFFF"], "typography": "Legible sans serif", "candidate_variation": ""},
       "provenance": {"origin": "user_supplied", "scientific_verification": "unverified", "external_consumer_verified": False}}
    if kind == "plot":
        data = {"columns": ["method", "accuracy"], "rows": [["Baseline", 0.61], ["Proposed", 0.78]]}
        raw = json.dumps(data, separators=(",", ":"))
        sha = hashlib.sha256(raw.encode()).hexdigest()
        table = {"id": "data", "name": "Synthetic fixture", "source_id": "input",
                 **data, "encoding": {"x": "method", "y": "accuracy", "chart_type": "bar"},
                 "sha256": hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        science.update(kind="plot", nodes=[], edges=[], sources=[{"id": "input", "kind": "user_data", "content": raw, "sha256": sha}],
                       datasets=[table], constraints={**science["constraints"], "required_labels": []})
    return science


@unittest.skipUnless(SUPPORTED, "Canonical provider protocol files are installed by release packaging")
class CanonicalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.contract, self.interop, _ = bridge._api()
        self.spec = fixture()
        self.spec_path = self.base / "input.figure-spec.json"
        self.spec_path.write_text(json.dumps(self.spec), encoding="utf-8")

    def test_immutable_topology_and_strict_schema(self):
        self.contract.validate_figure_spec(self.spec)
        wrong = copy.deepcopy(self.spec)
        wrong["edges"][0]["target"] = "not-a-real-node"
        with self.assertRaises(ValueError):
            self.contract.validate_figure_spec(wrong)

    def test_draft_outputs_prompt_not_claimed_generated_image(self):
        result = bridge.compile_draft(self.spec, self.base / "draft")
        self.assertEqual(result["status"], "PROMPT_READY_NOT_RENDERED")
        self.assertIn("Encoder", Path(result["prompt"]).read_text())
        self.assertFalse((self.base / "draft" / "image.png").exists())

    def test_canonical_request_preserves_full_source_and_science(self):
        request = self.interop.prepare_request(self.spec_path, self.base / "request")
        envelope, spec = self.interop.validate_request(request)
        self.assertEqual(spec, self.spec)
        self.assertEqual(envelope["scientific_fingerprint"], self.contract.scientific_fingerprint(self.spec))
        self.assertIn("--rfs-file", self.interop.request_argv(request))

    def test_authorization_precedes_external_generation(self):
        with self.assertRaisesRegex(ValueError, "allow-external"):
            bridge.generate(self.spec_path, self.base / "gen", allow_external=False)
        self.assertFalse((self.base / "gen").exists())

    def test_numerical_plot_uses_exact_dataset(self):
        spec = fixture("plot")
        result = bridge.render_plot_v1(spec, self.base / "plot")
        self.assertEqual(result["status"], "DATA_PLOTTED_SCIENCE_REVIEW_PENDING")
        receipt = json.loads(Path(result["manifest"]).read_text())
        self.assertEqual(receipt["row_count"], 2)
        self.assertEqual(json.loads((self.base / "plot" / "figure-spec.json").read_text())["datasets"][0]["rows"], spec["datasets"][0]["rows"])
        self.assertTrue((self.base / "plot" / "figure.svg").exists())
        self.assertTrue((self.base / "plot" / "plot-reproduce.py").is_file())

    def test_reject_invented_statistical_aggregation(self):
        spec = fixture("plot")
        spec["datasets"][0]["rows"].append(["Proposed", 0.9])
        with self.assertRaises(ValueError):
            bridge.render_plot_v1(spec, self.base / "plot")

    def test_canonical_dispatch(self):
        self.assertTrue(bridge.is_canonical(self.spec_path))
        self.assertEqual(bridge.explain_route(self.spec)["engine"], "prompt-only")
        self.assertEqual(bridge.explain_route(self.spec, allow_external=True)["engine"], "paperbanana")
        self.assertEqual(bridge.explain_route(fixture("plot"))["engine"], "plot-matplotlib")


@unittest.skipUnless(SUPPORTED and bool(os.environ.get("PAPERBANANA_ROOT")), "Real producer checkout required for cross-repository tests")
class LiveCodeOfflineConsumerIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.spec = fixture()
        self.spec_path = self.base / "spec.json"
        self.spec_path.write_text(json.dumps(self.spec), encoding="utf-8")

    def test_real_provider_descriptor_matches(self):
        self.assertEqual(bridge._check_peer()["status"], "COMPATIBLE")

    def test_real_provider_validates_consumer_request(self):
        _, interop, _ = bridge._api()
        p = interop.prepare_request(self.spec_path, self.base / "request")
        root, python = bridge._peer()
        result = subprocess.run([python, str(root / "skill" / "exchange.py"), "validate-request", "--request", str(p)],
                                cwd=root, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "VALID_REQUEST_NOT_EXECUTED")
        (p.parent / "source.txt").write_text("TAMPERED", encoding="utf-8")
        fail = subprocess.run([python, str(root / "skill" / "exchange.py"), "validate-request", "--request", str(p)],
                              cwd=root, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(fail.returncode, 0)

    def _real_producer_fixture(self) -> Path:
        root, python = bridge._peer()
        bundle = self.base / "producer_bundle"
        code = '''import sys, json, io, base64, hashlib
from pathlib import Path
from PIL import Image
from rfs.contract import canonical_json, sha256_text, validate_figure_spec
from rfs.artifacts import export_bundle
spec = validate_figure_spec(json.loads(Path(sys.argv[1]).read_text()))
raw = io.BytesIO()
Image.new("RGBA", (20, 20), (10, 20, 30, 128)).save(raw, "PNG")
key = "target_diagram_desc0"
record = {"candidate_id": "0", "stage": "design", "provider": "fixture", "model": "no-paid-model",
          "prompt": "synthetic test", "design_description": "Left to right nodes, gray background, precise connector and typography.",
          "figure_spec": spec, "figure_spec_sha256": sha256_text(canonical_json(spec)),
          "image_base64": base64.b64encode(raw.getvalue()).decode(), "image_mime": "image/png"}
data = {"candidate_id": "0", "status": "succeeded", "eval_image_field": key+"_base64_jpg",
        "rfs_artifacts": {key:record}, "review_status":"not_requested"}
export_bundle(data, sys.argv[2])
'''
        r = subprocess.run([python, "-c", code, str(self.spec_path), str(bundle)], cwd=root, capture_output=True, text=True, timeout=25)
        self.assertEqual(r.returncode, 0, r.stderr)
        return bundle

    def test_actual_paperbanana_exporter_verifies_in_rfs(self):
        bundle = self._real_producer_fixture()
        report = bridge.audit_bundle(self.spec_path, bundle)
        self.assertEqual(report["integrity"], "PASS")
        self.assertEqual(report["scientific_review"], "PENDING")
        image = bundle / "image.png"
        image.write_bytes(image.read_bytes() + b"tampered")
        with self.assertRaises(ValueError):
            bridge.audit_bundle(self.spec_path, bundle)

    def test_three_source_native_handoff_is_explicitly_pending(self):
        bundle = self._real_producer_fixture()
        notes = self.base / "observed.md"
        notes.write_text("Layout: left to right. Object inventory: 3 native shapes, exact labels. "
                         "Connector: input to encoder, encoder to embeddings. Color: dark blue and white. "
                         "Observed from the source test image; physical target display still pending.", encoding="utf-8")
        receipt = bridge.prepare_editable(self.spec_path, bundle, notes, self.base / "handoff", approved=True)
        self.assertEqual(receipt["status"], "READY_NOT_EXECUTED")
        self.assertFalse((self.base / "handoff" / "figure.pptx").exists())
        self.assertEqual(bridge.audit_handoff(self.base / "handoff")["render_verification"], "PENDING")
        (self.base / "handoff" / "observed-design-notes.md").write_text("TAMPERED")
        with self.assertRaises(ValueError):
            bridge.audit_handoff(self.base / "handoff")


if __name__ == "__main__":
    unittest.main()