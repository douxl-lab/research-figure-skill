"""Offline semantic and real-compiler acceptance for the optional TikZ v1 renderer."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from tikz_renderer import audit_tikz, escape_text, make_tex, render_tikz, safe_formula


def fixture():
    source = "输入 跨模态注意力 标签查询 输出"
    evidence = [{"source_id": "user", "quote": source}]
    return {
        "schema_version": "1.0.0", "figure_id": "tikz-v1-test", "kind": "diagram",
        "nodes": [
            {"id": "input", "label": "输入", "kind": "input", "evidence": evidence},
            {"id": "attention", "label": "跨模态注意力", "kind": "block", "formula": r"Q=\mathrm{softmax}(X W_q)", "evidence": evidence},
            {"id": "label", "label": "标签查询", "kind": "block", "evidence": evidence},
            {"id": "output", "label": "输出", "kind": "output", "evidence": evidence}],
        "edges": [
            {"id": "e1", "source": "input", "target": "attention", "kind": "flow", "directed": True, "evidence": evidence},
            {"id": "e2", "source": "attention", "target": "label", "kind": "flow", "directed": True, "evidence": evidence},
            {"id": "e3", "source": "label", "target": "output", "kind": "flow", "directed": True, "evidence": evidence}],
        "groups": [{"id": "mechanism", "label": "关键模块", "node_ids": ["attention", "label"], "evidence": evidence}],
        "labels": [{"id": "annotation", "text": "公式与结构", "target_ids": ["attention"], "evidence": evidence}],
        "datasets": [],
        "sources": [{"id": "user", "kind": "user_text", "content": source, "sha256": hashlib.sha256(source.encode()).hexdigest()}],
        "constraints": {"locked": True, "required_labels": ["输入", "跨模态注意力", "标签查询", "输出"],
                        "layout": [], "visual": [], "negative": []},
        "design": {"layout": "Left to right", "composition": "Pipeline",
                   "palette": ["#2F6B9A", "#E9A23B", "#7363A8"], "typography": "Chinese labels and math", "candidate_variation": ""},
        "provenance": {"origin": "user_supplied", "scientific_verification": "unverified", "external_consumer_verified": False},
    }


class TikzRendererTests(unittest.TestCase):
    def test_escaping_and_formula_macro_allowlist(self):
        self.assertIn(r"\&", escape_text("A&B_1%"))
        self.assertEqual(safe_formula(r"\frac{1}{2} + \alpha"), r"\frac{1}{2} + \alpha")
        for payload in (r"\input{secret}", r"\write18{bad}", r"\catcode{bad}", "a$evil"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                safe_formula(payload)

    def test_source_node_edge_group_and_math_preserved(self):
        tex, warnings = make_tex(fixture())
        self.assertIn("跨模态注意力", tex)
        self.assertIn(r"\mathrm{softmax}", tex)
        self.assertEqual(tex.count(r"\draw["), 3)
        self.assertIn("关键模块", tex)
        self.assertFalse(warnings)

    def test_unsafe_formula_fails_before_any_output(self):
        spec = fixture()
        spec["nodes"][1]["formula"] = r"\input{private-file}"
        with self.assertRaises(ValueError):
            make_tex(spec)

    def test_explicit_tikz_routing_does_not_change_creative_default(self):
        import bridge
        spec = fixture()
        self.assertEqual(bridge.explain_route(spec)["engine"], "prompt-only")
        self.assertEqual(bridge.explain_route(spec, engine="tikz")["engine"], "tikz")
        broken = copy.deepcopy(spec)
        broken["kind"] = "plot"
        with self.assertRaises(ValueError):
            bridge.explain_route(broken, engine="tikz")

    def test_cli_route_selects_tikz_without_invoking_compiler(self):
        spec = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "rfs.py"),
                                     "route", "--spec", str(path), "--engine", "tikz"],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["plan"]["engine"], "tikz")

    @unittest.skipUnless(shutil.which("xelatex") and shutil.which("pdftocairo"),
                         "Real TeX and Poppler toolchain required for vector compiler acceptance")
    def test_compiled_outputs_and_integrity_tamper_detection(self):
        spec = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "rendered"
            result = render_tikz(spec, target)
            self.assertEqual(result["engine"], "tikz")
            self.assertEqual(audit_tikz(spec, target)["integrity"], "PASS")
            self.assertTrue((target / "figure.pdf").read_bytes().startswith(b"%PDF"))
            self.assertIn(b"<svg", (target / "figure.svg").read_bytes()[:1000])
            self.assertTrue((target / "figure.png").read_bytes().startswith(b"\x89PNG"))
            self.assertEqual(json.loads((target / "figure-spec.json").read_text()), spec)
            self.assertFalse((target / "figure.log").exists())
            with self.assertRaises(ValueError):
                render_tikz(spec, target)
            with (target / "figure.tex").open("a", encoding="utf-8") as file:
                file.write("% tampered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                audit_tikz(spec, target)


if __name__ == "__main__":
    unittest.main()
