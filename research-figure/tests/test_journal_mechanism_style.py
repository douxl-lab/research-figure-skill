"""Public Agent Skill safeguards for the learned paper-figure style."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class JournalMechanismStyleTests(unittest.TestCase):
    def test_installable_skill_exposes_style_standard(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/journal-mechanism-style.md", skill)
        self.assertIn("One independent scientific question", skill)
        self.assertIn("multi-label uncertainty equations", skill)

    def test_prompt_and_root_readme_link_standard(self):
        prompt = (ROOT / "references/prompt-system.md").read_text(encoding="utf-8")
        readme = (ROOT.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("journal-mechanism-style.md", prompt)
        self.assertIn("journal-mechanism-style.md", readme)
        self.assertIn("captionless/titleless", prompt)

    def test_style_standard_distinguishes_single_and_multipart(self):
        guide = (ROOT / "references/journal-mechanism-style.md").read_text(encoding="utf-8")
        self.assertIn("standalone", guide)
        self.assertIn("three independently captioned images", guide)
        self.assertIn("Dirichlet", guide)
        self.assertIn("Nature Communications", guide)
        self.assertIn("CVPR 2024", guide)
        from sys import path
        path.insert(0, str(ROOT / "scripts"))
        from check_repository import public_path, scan_content
        rel = "research-figure/references/journal-mechanism-style.md"
        self.assertTrue(public_path(rel))
        self.assertEqual(scan_content(rel, guide.encode("utf-8")), [])

if __name__ == "__main__":
    unittest.main()
