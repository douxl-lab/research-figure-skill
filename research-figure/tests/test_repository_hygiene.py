"""Repository publication invariants, independent of external credentials."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_repository import check_paths, public_path, scan_content


class RepositoryPrivacyTests(unittest.TestCase):
    def test_public_runtime_skill_components_are_allowed(self):
        for path in (
            "README.md", "research-figure/SKILL.md", "research-figure/LICENSE", "THIRD_PARTY_NOTICES.md",
            "research-figure/references/routing.md", "research-figure/agents/openai.yaml", "research-figure/scripts/rfs.py",
            "research-figure/assets/prompts/model-registry.json", "research-figure/assets/demo-synthetic-ablation.csv", "research-figure/tests/test_rfs.py",
            ".github/workflows/ci.yml", ".gitignore",
        ):
            with self.subTest(path=path):
                self.assertTrue(public_path(path))

    def test_internal_docs_and_editor_profiles_never_publish(self):
        for path in (
            "docs/internal-review.md", "internal/notes.md", "plans/roadmap.md",
            ".vscode/settings.json", ".cursor/mcp.json", ".claude/config.json",
            ".codex/config.json", "research-figure/assets/private/data.json",
            "research-figure/assets/generated/figure.png", "research-figure/assets/.env", "research-figure/assets/.env.test",
            "notes.md", "secret.yaml", "credentials.json", "output/plot.pdf",
            "research-figure/tests/private.key", "research-figure/assets/user-data.csv.zip", "research-figure/assets/private-experiment.csv", "PACKAGE_MANIFEST.json",
        ):
            with self.subTest(path=path):
                self.assertFalse(public_path(path))

    def test_high_confidence_credentials_are_redacted_from_diagnostics(self):
        tokens = [
            b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----\nMII=\n",
            b"GITHUB_TOKEN=github_pat_" + b"x" * 40,
            b"MY_KEY=sk-proj-" + b"a" * 40,
            b"GOOGLE_KEY=AIza" + b"a" * 35,
            b"AWS_ACCESS_KEY_ID=AKIA" + b"B" * 16,
        ]
        for token in tokens:
            problems = scan_content("foo.txt", token)
            self.assertTrue(problems)
            self.assertNotIn(token.decode("ascii"), " ".join(problems))

    def test_clean_public_skill_files_pass(self):
        issues = check_paths(REPO_ROOT, ["research-figure/SKILL.md", "README.md", "research-figure/scripts/rfs.py"])
        self.assertEqual(issues, [])

    def test_gitignore_protects_private_folders_and_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/".gitignore").write_text((REPO_ROOT/".gitignore").read_text())
            subprocess.run(["git", "init", "-q", str(p)], check=True, stdout=subprocess.PIPE)
            for path in (".vscode/settings.json", ".cursor/mcp.json", ".env", ".env.local",
                         "docs/private.md", "outputs/raster.png", "local.model_config.yaml",
                         "cache/prompt.log", "service-account.json", "secret.pem", "final-figure.png", "experiment.csv"):
                r=subprocess.run(["git", "-C", str(p), "check-ignore", "-q", path],check=False)
                with self.subTest(path=path):
                    self.assertEqual(r.returncode,0)
            for path in ("SKILL.md", "README.md", "references/routing.md", "agents/openai.yaml"):
                r=subprocess.run(["git", "-C", str(p), "check-ignore", "-q", path],check=False)
                with self.subTest(path=path):
                    self.assertEqual(r.returncode,1)


if __name__ == "__main__":
    unittest.main()
