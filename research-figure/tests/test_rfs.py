"""Offline regression tests for the self-contained orchestration layer."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from auditing import audit_file
from core import RFSValidationError, load_and_validate, read_plot_rows, validate_spec
from diagram import render_diagram
from external import create_handoff


ARCH = ROOT / "assets" / "spec-architecture.json"
EXACT = ROOT / "assets" / "spec-architecture-exact.json"
PLOT = ROOT / "assets" / "spec-plot-demo.json"
CLI = ROOT / "scripts" / "rfs.py"


class RFSOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_example_specs_validate(self):
        for src in (ARCH, PLOT):
            spec, result = load_and_validate(src)
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["scientific_interpretation"], "PENDING")

    def test_nodes_edges_and_label_are_exact_svg(self):
        spec, report = load_and_validate(ARCH)
        artifact = self.out / "figure.svg"
        render_diagram(spec, artifact)
        audit = audit_file(spec, ARCH, artifact)
        self.assertEqual(audit["checks"]["semantic_structure"]["status"], "PASS")
        self.assertEqual(audit["checks"]["native_editability"]["status"], "PASS")
        self.assertEqual(audit["checks"]["scientific_interpretation"]["status"], "PENDING")
        self.assertIn("DRAFT", artifact.read_text(encoding="utf-8"))

    def test_wrong_svg_label_fails_semantic_audit(self):
        spec, _ = load_and_validate(ARCH)
        artifact = self.out / "figure.svg"
        render_diagram(spec, artifact)
        content = artifact.read_text(encoding="utf-8")
        artifact.write_text(content.replace("Multimodal", "WrongModule", 1), encoding="utf-8")
        report = audit_file(spec, ARCH, artifact)
        self.assertEqual(report["checks"]["semantic_structure"]["status"], "FAIL")

    def test_unknown_edge_rejected(self):
        spec, _ = load_and_validate(ARCH)
        modified = copy.deepcopy(spec)
        modified["diagram"]["edges"][0]["target"] = "missing"
        self.assertFalse(validate_spec(modified, ARCH)["valid"])

    def test_undocumented_cycle_rejected(self):
        spec, _ = load_and_validate(ARCH)
        modified = copy.deepcopy(spec)
        modified["diagram"]["edges"].append({"source": "fusion", "target": "encoders"})
        self.assertFalse(validate_spec(modified, ARCH)["valid"])
        modified["diagram"]["edges"][-1]["feedback"] = True
        self.assertTrue(validate_spec(modified, ARCH)["valid"])

    def test_illustrative_evidence_requires_watermark(self):
        spec, _ = load_and_validate(PLOT)
        modified = copy.deepcopy(spec)
        modified["style"]["demo"] = False
        result = validate_spec(modified, PLOT)
        self.assertFalse(result["valid"])

    def test_numeric_csv_source_and_no_implicit_average(self):
        spec, _ = load_and_validate(PLOT)
        rows = read_plot_rows(spec, PLOT)
        self.assertEqual(len(rows), 6)
        bad_csv = self.out / "x.csv"
        bad_csv.write_text("Configuration,Group,ToyScore\nA,G,1\nA,G,2\n", encoding="utf-8")
        local = self.out / "bad.json"
        modified = copy.deepcopy(spec)
        modified["plot"]["data_file"] = "x.csv"
        modified["evidence"][0]["path"] = "x.csv"
        local.write_text(json.dumps(modified), encoding="utf-8")
        self.assertFalse(validate_spec(modified, local)["valid"])

    def test_handoff_is_not_pptx(self):
        spec, _ = load_and_validate(ARCH)
        result = create_handoff(spec, ARCH, self.out, "paper-fig")
        self.assertEqual(result["status"], "NOT_EXECUTED")
        self.assertTrue((self.out / "handoff.md").exists())
        self.assertFalse(list(self.out.glob("*.pptx")))

    def test_invalid_theme_is_not_silently_ignored(self):
        spec, _ = load_and_validate(ARCH)
        modified = copy.deepcopy(spec)
        modified["style"]["theme"] = "unavailable-theme"
        report = validate_spec(modified, ARCH)
        self.assertFalse(report["valid"])
        self.assertIn("Unsupported style theme", " ".join(report["errors"]))

    def test_pptx_flattened_bitmap_is_not_editable(self):
        import zipfile
        spec, _ = load_and_validate(ARCH)
        pptx = self.out / "flattened.pptx"
        xml = ("<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' "
               "xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'>"
               "<p:cSld><p:spTree><p:pic/></p:spTree></p:cSld></p:sld>")
        with zipfile.ZipFile(pptx, "w") as z:
            z.writestr("ppt/slides/slide1.xml", xml)
        report = audit_file(spec, ARCH, pptx)
        self.assertEqual(report["checks"]["native_editability"]["status"], "FAIL")

    def test_manifest_detects_tampered_artifact(self):
        path = self.out / "tamper"
        proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(ARCH),
                               "--out", str(path), "--engine", "native-svg"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0)
        artifact = path / "figure.svg"
        artifact.write_text(artifact.read_text(encoding="utf-8").replace("Encoders", "EncodersX"), encoding="utf-8")
        report = audit_file(load_and_validate(ARCH)[0], ARCH, artifact)
        self.assertEqual(report["checks"]["manifest_integrity"]["status"], "FAIL")
        self.assertEqual(report["overall"], "FAIL")

    def test_cli_run_and_audit(self):
        path = self.out / "render"
        proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(EXACT),
                               "--out", str(path), "--engine", "native-svg"],
                              text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "ARTIFACT_CREATED")
        artifact = path / "figure.svg"
        aud = subprocess.run([sys.executable, str(CLI), "audit", "--spec", str(EXACT),
                              "--artifact", str(artifact)], text=True, capture_output=True)
        self.assertEqual(aud.returncode, 0, aud.stderr + aud.stdout)
        self.assertEqual(json.loads(aud.stdout)["checks"]["semantic_structure"], "PASS")

    def test_paperbanana_not_called_without_authorization(self):
        proc = subprocess.run([sys.executable, str(CLI), "route", "--spec", str(ARCH),
                               "--engine", "paperbanana"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("allow-external", proc.stdout)

    def test_matplotlib_demo_plot_if_installed(self):
        try:
            import matplotlib  # noqa
        except ImportError:
            self.skipTest("matplotlib not installed")
        path = self.out / "plot"
        proc = subprocess.run([sys.executable, str(CLI), "run", "--spec", str(PLOT),
                               "--out", str(path)], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertTrue((path / "figure.svg").is_file())
        self.assertTrue((path / "figure.png").is_file())
        self.assertTrue((path / "figure.pdf").is_file())
        result = audit_file(load_and_validate(PLOT)[0], PLOT, path / "figure.svg")
        self.assertEqual(result["checks"]["numeric_integrity"]["status"], "PASS")
        self.assertEqual(result["overall"], "PENDING")


if __name__ == "__main__":
    unittest.main(verbosity=2)
