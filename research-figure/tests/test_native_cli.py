"""Exercise actual RFS CLI entrypoints, including the canonical v1 regression."""
from __future__ import annotations

import html
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

def attr(value):
    return html.attr(str(value), quote=True)


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "rfs.py"
V1_EXAMPLE = ROOT / "assets" / "figure-spec-v1-example.json"
LEGACY_EXAMPLE = ROOT / "assets" / "spec-architecture.json"
sys.path.insert(0, str(ROOT / "scripts"))


class CLIRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)

    def invoke(self, *args):
        proc = subprocess.run([sys.executable, str(CLI), *map(str, args)],
                              capture_output=True, text=True, timeout=35)
        try:
            response = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"CLI output not JSON: rc={proc.returncode}, stdout={proc.stdout!r}, stderr={proc.stderr!r}")
        return proc.returncode, response

    def test_canonical_validate_cli_returns_success(self):
        status, report = self.invoke("validate", "--spec", V1_EXAMPLE)
        self.assertEqual(status, 0, report)
        self.assertTrue(report["valid"])
        self.assertEqual(report["schema_version"], "1.0.0")
        self.assertEqual(report["scientific_review"], "PENDING")

    def test_legacy_validate_cli_is_still_supported(self):
        status, report = self.invoke("validate", "--spec", LEGACY_EXAMPLE)
        self.assertEqual(status, 0, report)
        self.assertTrue(report["valid"])

    def test_invalid_canonical_cli_reports_failure(self):
        source = json.loads(V1_EXAMPLE.read_text(encoding="utf-8"))
        source["nodes"][0]["id"] = "unknown changed id"
        path = self.output / "invalid.json"
        path.write_text(json.dumps(source), encoding="utf-8")
        status, result = self.invoke("validate", "--spec", path)
        self.assertEqual(status, 2, result)
        self.assertEqual(result["status"], "ERROR")

    def test_native_drawio_cli_validates_tagged_topology(self):
        spec = json.loads(V1_EXAMPLE.read_text(encoding="utf-8"))
        parts = ['<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>']
        for node in spec["nodes"]:
            parts.append(f'<mxCell id="rfs-node:{attr(node["id"])}" '
                         f'value="{attr(node["label"])}" vertex="1" parent="1"/>')
        for edge in spec["edges"]:
            parts.append(f'<mxCell id="rfs-edge:{attr(edge["id"])}" edge="1" '
                         f'source="rfs-node:{attr(edge["source"])}" target="rfs-node:{attr(edge["target"])}" '
                         f'style="endArrow={"classic" if edge.get("directed") else "none"};" parent="1"/>')
            if edge.get("label"):
                parts.append(f'<mxCell id="label-{attr(edge["id"])}" value="{attr(edge["label"])}" vertex="1" parent="1"/>')
        for group in spec.get("groups", []):
            parts.append(f'<mxCell id="group-{attr(group["id"])}" value="{attr(group["label"])}" vertex="1" parent="1"/>')
        for label in spec.get("labels", []):
            parts.append(f'<mxCell id="label-{attr(label["id"])}" value="{attr(label["text"])}" vertex="1" parent="1"/>')
        path = self.output / "tagged.drawio"
        path.write_text("".join(parts) + "</root></mxGraphModel>", encoding="utf-8")
        code, report = self.invoke("native-audit", "--spec", V1_EXAMPLE, "--native-file", path)
        self.assertEqual(code, 0, report)
        self.assertEqual(report["structure_check"], "PASS")
        self.assertEqual(report["target_render"], "NOT_RUN")
        self.assertIn("PENDING", report["status"])

    def test_legacy_package_audit_does_not_use_canonical_dispatch(self):
        from core import load_and_validate
        from reconstruction import create_reconstruction_package
        spec, report = load_and_validate(str(LEGACY_EXAMPLE))
        self.assertTrue(report["valid"])
        ref = self.output / "reference.png"
        Image.new("RGB", (160, 90), "white").save(ref)
        notes = self.output / "observed-notes.md"
        notes.write_text(
            "Layout: left-to-right pipeline with four regions and breathing room. "
            "Objects: labeled native rectangular modules with readable exact names. "
            "Connectors: directed arrows following one spine between the modules. "
            "Color: blue outlines on white with sufficient contrast and consistent text alignment.",
            encoding="utf-8")
        pkg = self.output / "legacy-handoff"
        create_reconstruction_package(spec, LEGACY_EXAMPLE, reference=ref, notes=notes,
                                      out=pkg, backend="paper-fig", approved=True)
        code, receipt = self.invoke("audit-package", "--package", pkg)
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["integrity"], "PASS")
        self.assertEqual(receipt["native_editability"], "PENDING")


if __name__ == "__main__":
    unittest.main()
