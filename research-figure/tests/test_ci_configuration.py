"""Workflow packaging guards; YAML parsing augments the always-on shape checks."""
from pathlib import Path
import unittest
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research-figure/scripts'))
from check_repository import check_tracked_inventory, git_tracked


class CIConfigurationTests(unittest.TestCase):
    def test_ci_steps_are_separate_and_ship_embedded_sources(self):
        workflow = ROOT / '.github/workflows/ci.yml'
        if not workflow.is_file():
            self.skipTest('Installable Skill intentionally omits repository GitHub workflows')
        source = workflow.read_text(encoding='utf-8')
        self.assertNotIn('scripts      - name:', source)
        self.assertIn('\n      - name: Exercise real embedded kernels offline\n', source)
        self.assertNotIn('repository: douxl-lab/PaperBanana', source)
        self.assertIn('research-figure/kernels/design', source)
        self.assertIn('scripts/upstreams.py verify', source)
        try:
            import yaml
        except ImportError:
            return  # Structural guards above do not require a new dependency.
        document = yaml.safe_load(source)
        steps = document['jobs']['audit']['steps']
        self.assertTrue(any(s.get('name') == 'Exercise real embedded kernels offline' for s in steps))
        self.assertTrue(any(s.get('name') == 'Build complete installable package' for s in steps))
        for step in steps:
            self.assertNotEqual('uses' in step, 'run' in step, step)


    def test_inventory_guard_rejects_ignored_source(self):
        rel = 'research-figure/kernels/design/agents/__init__.py'
        with patch('check_repository.vendor_inventory', return_value={rel: {}}):
            failures = check_tracked_inventory(ROOT, [])
        self.assertEqual(len(failures), 1)
        self.assertIn('not tracked by Git', failures[0])

    def test_inventory_guard_accepts_complete_source(self):
        rel = 'research-figure/kernels/layout/scripts/cvprfig/_metrics.py'
        with patch('check_repository.vendor_inventory', return_value={rel: {}}):
            self.assertEqual(check_tracked_inventory(ROOT, [rel]), [])

    def test_actual_index_has_every_locked_file(self):
        if not (ROOT / '.git').exists():
            self.skipTest('Installed package has no Git index')
        self.assertEqual(check_tracked_inventory(ROOT, git_tracked(ROOT)), [])


if __name__ == '__main__':
    unittest.main()
