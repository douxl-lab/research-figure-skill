"""Deterministic orchestration tests, NOT a live model/host invocation benchmark."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import workflow
import bootstrap_backends

DIAGRAM = {"schema_version": "1.0.0", "kind": "diagram"}
PLOT = {"schema_version": "1.0.0", "kind": "plot"}


def capabilities(native=False, provider=False, cvpr=False):
    return {
        "design": {"root": None, "files": {"skill/native_host.py": native, "skill/exchange.py": provider}},
        "layout": {"root": None, "files": {"scripts/render.py": cvpr, "scripts/validate.py": cvpr}},
    }


class RoutingTests(unittest.TestCase):
    def test_unnamed_diagram_selects_native_paperbanana(self):
        p = workflow.make_plan(DIAGRAM, capabilities(native=True), host_image_tool="actual-image-tool")
        self.assertEqual(p["mode"], "design-native")
        self.assertIn("references/layout-library.md", p["references"])
        self.assertIn("references/design-core.md", p["references"])
        self.assertEqual(p["status"], "PLANNED_NOT_EXECUTED")

    def test_native_preferred_over_provider_in_auto(self):
        p = workflow.make_plan(DIAGRAM, capabilities(True, True), host_image_tool="actual", allow_external=True)
        self.assertEqual(p["mode"], "design-native")

    def test_explicit_authorized_provider_overrides_native(self):
        p = workflow.make_plan(DIAGRAM, capabilities(True, True), mode="design-provider", host_image_tool="actual", allow_external=True)
        self.assertEqual(p["mode"], "design-provider")
        self.assertFalse(p["blockers"])

    def test_host_fallback_is_not_claimed_as_upstream_runtime(self):
        p = workflow.make_plan(DIAGRAM, capabilities(), host_image_tool="actual")
        self.assertEqual(p["mode"], "bundled-host-workflow")

    def test_no_host_no_authorization_blocks_even_with_provider_files(self):
        p = workflow.make_plan(DIAGRAM, capabilities(provider=True))
        self.assertEqual(p["status"], "BLOCKED")
        self.assertNotEqual(p["mode"], "prompt-only")

    def test_authorized_provider_is_automatic_without_backend_name(self):
        p = workflow.make_plan(DIAGRAM, capabilities(provider=True), allow_external=True)
        self.assertEqual(p["mode"], "design-provider")

    def test_explicit_provider_cannot_bypass_permission(self):
        p = workflow.make_plan(DIAGRAM, capabilities(provider=True), mode="design-provider")
        self.assertEqual(p["status"], "BLOCKED")

    def test_explicit_exact_legacy_intent_is_preserved(self):
        spec = {"type": "architecture", "generation": {"intent": "exact"}}
        p = workflow.make_plan(spec, capabilities(True, True), host_image_tool="actual", allow_external=True)
        self.assertEqual(p["mode"], "native-svg")
        self.assertNotIn("references/design-core.md", p["references"])
        self.assertEqual(workflow.make_plan(DIAGRAM, capabilities(), mode="native-svg")["status"], "BLOCKED")

    def test_data_never_uses_generator(self):
        p = workflow.make_plan(PLOT, capabilities(True, True), host_image_tool="actual", allow_external=True)
        self.assertEqual(p["mode"], "plot-matplotlib")
        with self.assertRaises(ValueError):
            workflow.make_plan(PLOT, capabilities(True, True), mode="design-native")

    def test_explicit_tikz_does_not_force_paperbanana(self):
        p = workflow.make_plan(DIAGRAM, capabilities(), mode="tikz", host_image_tool="actual")
        self.assertEqual(p["mode"], "tikz")
        self.assertNotIn("references/design-core.md", p["references"])

    def test_explicit_prompt_remains_supported(self):
        self.assertEqual(workflow.make_plan(DIAGRAM, capabilities(), mode="prompt-only")["mode"], "prompt-only")

    def test_native_requires_real_host_declaration(self):
        p = workflow.make_plan(DIAGRAM, capabilities(native=True), mode="design-native")
        self.assertEqual(p["status"], "BLOCKED")

    def test_legacy_is_not_silently_converted_to_v1(self):
        p = workflow.make_plan({"type": "architecture"}, capabilities(native=True), mode="design-native", host_image_tool="actual")
        self.assertEqual(p["status"], "BLOCKED")

    def test_hybrid_and_reconstruction_do_not_regenerate(self):
        for spec in ({"schema_version": "1.0.0", "kind": "hybrid"}, {"type": "editable_reconstruction"}, {"type": "evidence_panel"}):
            p = workflow.make_plan(spec, capabilities(True, True), host_image_tool="actual")
            self.assertEqual(p["mode"], "source-preserving-handoff")

    def test_bad_kind_and_mode_are_rejected(self):
        for spec, mode in (({}, "auto"), (DIAGRAM, "invented")):
            with self.assertRaises(ValueError):
                workflow.make_plan(spec, capabilities(), mode=mode)

    def test_cvpr_needs_real_renderer_and_validator(self):
        self.assertEqual(workflow.make_plan(DIAGRAM, capabilities(), mode="layout")["status"], "BLOCKED")
        self.assertFalse(workflow.make_plan(DIAGRAM, capabilities(cvpr=True), mode="layout")["blockers"])


class FilesAndExecutionTests(unittest.TestCase):
    def test_discovery_no_network_and_invalid_explicit_root_no_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skill"
            (root / "kernels/design/skill").mkdir(parents=True)
            (root / "kernels/design/skill/native_host.py").write_text("# fixture\n")
            found = workflow.discover(root=root, environ={})
            self.assertTrue(found["design"]["files"]["skill/native_host.py"])
            self.assertFalse(found["design"]["runtime_verified"])
            override = workflow.discover(root=root, environ={"PAPERBANANA_ROOT": str(Path(tmp) / "missing")})
            self.assertIsNone(override["design"]["root"])

    def test_backend_dir_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            (parent / "layout/scripts").mkdir(parents=True)
            for name in ("render.py", "validate.py"):
                (parent / "layout/scripts" / name).write_text("# fixture\n")
            self.assertTrue(all(workflow.discover(root=parent / "unrelated", backend_dir=parent, environ={})["layout"]["files"].values()))

    def _fixture(self, base):
        root = base / "installed"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts/rfs.py").write_text('import json,sys\nprint(json.dumps({"valid": True} if sys.argv[1] == "validate" else {"status": "FIXTURE_BACKEND_RETURNED"}))\n')
        spec = base / "spec.json"
        spec.write_text(json.dumps(DIAGRAM))
        return root, spec

    def test_real_subprocess_native_preparation_is_not_image_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, spec = self._fixture(base)
            pb = base / "design"
            (pb / "skill").mkdir(parents=True)
            (pb / "skill/native_host.py").write_text('import json,sys\nprint(json.dumps({"status": "FIXTURE_PREPARED"} if sys.argv[1] == "prepare" else {"stage": "Retriever"}))\n')
            caps = capabilities(native=True)
            caps["design"]["root"] = str(pb)
            plan = workflow.make_plan(DIAGRAM, caps, host_image_tool="actual")
            with patch.dict(workflow.os.environ, {"PAPERBANANA_PYTHON": sys.executable}):
                result = workflow.execute(plan, spec, base / "job", root=root)
            self.assertEqual(result["status"], "HOST_ACTION_REQUIRED")
            self.assertEqual(result["next_task"]["stage"], "Retriever")
            self.assertTrue((base / "job/workflow-result.json").is_file())
            self.assertFalse(list((base / "job").rglob("*.png")))

    def test_fallback_has_real_trace_but_no_upstream_runtime_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, spec = self._fixture(base)
            plan = workflow.make_plan(DIAGRAM, capabilities(), host_image_tool="actual")
            result = workflow.execute(plan, spec, base / "job", root=root)
            self.assertEqual(result["mode"], "bundled-host-workflow")
            self.assertEqual(result["status"], "HOST_ACTION_REQUIRED")

    def test_existing_output_and_installed_directory_are_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, spec = self._fixture(base)
            plan = workflow.make_plan(DIAGRAM, capabilities(), mode="tikz")
            for out in (root / "outputs", base):
                with self.assertRaises(ValueError):
                    workflow.execute(plan, spec, out, root=root)

    def test_cvpr_requires_separate_reviewed_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, spec = self._fixture(base)
            plan = workflow.make_plan(DIAGRAM, capabilities(cvpr=True), mode="layout")
            with self.assertRaises(ValueError):
                workflow.execute(plan, spec, base / "out", root=root)
            self.assertFalse((base / "out").exists())

    def test_failed_backend_produces_failure_trace_without_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, spec = self._fixture(base)
            (root / "scripts/rfs.py").write_text('import json,sys\nprint(json.dumps({"valid": True}))\nsys.exit(0 if sys.argv[1] == "validate" else 9)\n')
            plan = workflow.make_plan(DIAGRAM, capabilities(), mode="tikz")
            with self.assertRaises(ValueError):
                workflow.execute(plan, spec, base / "out", root=root)
            result = json.loads((base / "out/workflow-result.json").read_text())
            self.assertEqual(result["status"], "FAILED_OR_UNKNOWN")

    def test_malformed_validator_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, spec = self._fixture(base)
            (root / "scripts/rfs.py").write_text('print("not json")\n')
            with self.assertRaises(ValueError):
                workflow.execute(workflow.make_plan(DIAGRAM, capabilities(), mode="tikz"), spec, base / "out", root=root)
            self.assertFalse((base / "out").exists())

    def test_plan_cli_does_not_create_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = base / "spec.json"
            spec.write_text(json.dumps(DIAGRAM))
            p = subprocess.run([sys.executable, str(ROOT / "scripts/workflow.py"), "plan", "--spec", str(spec), "--mode", "prompt-only"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["mode"], "prompt-only")
            self.assertEqual(list(base.iterdir()), [spec])

    def test_pinned_registry_and_bootstrap_requires_consent(self):
        catalog = json.loads((ROOT / "assets/upstreams.lock.json").read_text())
        for name, raw in catalog["kernels"].items():
            entry = dict(raw, directory=name)
            if "revision" in entry:
                self.assertRegex(entry["revision"], r"^[0-9a-f]{40}$")
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(ValueError):
                        bootstrap_backends.install(entry, Path(tmp) / "new")
                    self.assertFalse((Path(tmp) / "new").exists())

    def test_bootstrap_rejects_floating_and_overwrite(self):
        catalog = json.loads((ROOT / "assets/upstreams.lock.json").read_text())
        entry = dict(catalog["kernels"]["design"], directory="design")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                bootstrap_backends.install(dict(entry, revision="main"), Path(tmp), allow_network=True)
            (Path(tmp) / entry["directory"]).mkdir()
            with self.assertRaises(ValueError):
                bootstrap_backends.install(entry, Path(tmp), allow_network=True)

    def test_installed_peer_prepares_real_native_job_without_image_generation(self):
        peer = ROOT / "kernels/design"
        source = ROOT / "assets/figure-spec-v1-example.json"
        if not peer or not (Path(peer) / "skill/native_host.py").is_file() or not source.is_file():
            self.skipTest("Real PaperBanana peer/sample unavailable; subprocess fixtures are tested separately")
        caps = workflow.discover(root=ROOT)
        plan = workflow.make_plan(json.loads(source.read_text()), caps, host_image_tool="test-host-declaration-no-image-call")
        with tempfile.TemporaryDirectory() as tmp:
            result = workflow.execute(plan, source, Path(tmp) / "job", root=ROOT)
            self.assertEqual(result["status"], "HOST_ACTION_REQUIRED")
            self.assertTrue(result["next_task"])
            self.assertTrue((Path(result["job"])).is_dir())

    def test_entrypoint_loads_modules_without_backend_keywords(self):
        text = (ROOT / "SKILL.md").read_text()
        for resource in ("references/design-core.md", "references/layout-library.md", "scripts/workflow.py"):
            self.assertIn(resource, text)
        self.assertIn("allow_implicit_invocation: true", (ROOT / "agents/openai.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
