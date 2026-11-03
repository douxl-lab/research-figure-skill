"""Publication boundaries and real Git-index regressions; synthetic secrets only."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import check_repository as guard


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)


def put(root: Path, name: str, raw: bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


class PublicationPolicyTests(unittest.TestCase):
    def test_document_allowlist_is_exact(self):
        for name in guard.PUBLIC_DOCUMENTS:
            self.assertTrue(guard.public_path(name), name)
        for name in ('research-figure/references/meeting-notes.md',
                     'research-figure/tests/validation-report.md',
                     'research-figure/assets/experiment.txt', 'PLAN.md',
                     'research-figure/SKILL.mdx'):
            self.assertFalse(guard.public_path(name), name)

    def test_internal_state_is_blocked_at_every_depth(self):
        for name in ('reports/a.md', 'reviews/a.py', 'sessions/a.json', '.kiro/config.json',
                     'manuscripts/paper.md', 'jobs/spec.json', 'mcp.json', 'context.json',
                     'run.receipt.json', 'draft.output.json', 'notes/recipe.py',
                     '.opencode/settings.json', '.vscode/settings.json', 'model_config.yaml'):
            for prefix in ('', 'research-figure/assets/', 'research-figure/tests/'):
                self.assertFalse(guard.public_path(prefix + name), prefix + name)

    def test_paths_are_canonical_and_portable(self):
        for name in ('', '.', './README.md', 'research-figure//scripts/a.py',
                     'research-figure/../README.md', '/README.md',
                     'research-figure/scripts/a.py\n', 'C:/file.py',
                     'research-figure\\scripts\\a.py'):
            self.assertFalse(guard.public_path(name), repr(name))

    def test_font_and_capture_payloads_are_not_sources(self):
        for suffix in ('.ttf', '.otf', '.woff2', '.har', '.pcap', '.jsonl'):
            self.assertFalse(guard.public_path('research-figure/assets/fixture' + suffix))

    def test_literal_secret_and_auth_url_detection_is_redacted(self):
        secret = 'synthetic-only-' + 'A7' * 16
        samples = ['API_KEY = "' + secret + '"',
                   '  "access_token": "' + secret + '",',
                   'Authorization: ' + 'Bearer ' + secret,
                   'endpoint = "' + 'https://' + 'user:' + secret + '@example.invalid"']
        for sample in samples:
            issues = guard.scan_content('fixture.py', sample.encode())
            self.assertTrue(issues)
            self.assertNotIn(secret, ' '.join(issues))

    def test_unquoted_config_secret_is_redacted(self):
        value = 'synthetic-only-' + 'A7' * 16
        for name in ('config.yaml', 'README.md'):
            issues = guard.scan_content(name, ('API_KEY: ' + value + '\n').encode())
            self.assertTrue(issues)
            self.assertNotIn(value, ' '.join(issues))

    def test_environment_lookup_and_placeholder_are_not_secrets(self):
        for source in ('API_KEY = os.environ.get("SERVICE_KEY")',
                       '"api_key_env": "RFS_IMAGE_API_KEY"',
                       'API_KEY = "YOUR_REVIEWED_PLACEHOLDER_ONLY"'):
            self.assertEqual(guard.scan_content('fixture.py', source.encode()), [])

    def test_gitignore_covers_nested_private_items(self):
        if not (REPO / '.gitignore').is_file():
            self.skipTest('Installed Skill does not ship repository ignore rules')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, 'init', '-q')
            put(root, '.gitignore', (REPO / '.gitignore').read_bytes())
            private = ['research-figure/reports/a.md', 'research-figure/tests/.vscode/settings.json',
                       'research-figure/assets/.env.prod', 'research-figure/references/private-plan.md',
                       'research-figure/tests/TODO.md', 'research-figure/assets/context.json',
                       'research-figure/assets/job.receipt.json', 'research-figure/tests/.codex/config.toml',
                       'research-figure/kernels/design/configs/model_config.yaml',
                       'research-figure/kernels/layout/assets/gallery/new-unreviewed.png',
                       'development-state.json', 'notes.txt', '.github/private/status.json']
            for name in private:
                result = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', name])
                self.assertEqual(result.returncode, 0, name)

    def test_gitignore_preserves_every_reviewed_runtime_file(self):
        if not (REPO / '.gitignore').is_file():
            self.skipTest('Installed Skill does not ship repository ignore rules')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, 'init', '-q')
            put(root, '.gitignore', (REPO / '.gitignore').read_bytes())
            names = sorted(set(guard.PUBLIC_DOCUMENTS) | set(guard.vendor_inventory(REPO)) |
                           {'research-figure/scripts/__init__.py', 'research-figure/agents/openai.yaml'})
            result = subprocess.run(['git', '-C', str(root), 'check-ignore', '--stdin'],
                                    input='\n'.join(names)+'\n', text=True, capture_output=True)
            self.assertEqual(result.stdout, '', result.stdout)

    def test_symlink_ancestor_cannot_publish_first_party_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'research-figure').mkdir()
            target = root / 'other'
            target.mkdir()
            (target / 'public.py').write_text('# fixture\n')
            try:
                (root / 'research-figure/scripts').symlink_to(target, target_is_directory=True)
            except OSError:
                self.skipTest('Symlink creation not permitted')
            issues = guard.check_paths(root, ['research-figure/scripts/public.py'])
            self.assertTrue(any('symlink' in s for s in issues))

    def test_vendor_lock_cannot_whitelist_private_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = 'research-figure/kernels/design/private/state.json'
            raw = b'{"synthetic": true}'
            put(root, name, raw)
            inventory = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}
            with patch.object(guard, 'vendor_inventory', return_value=inventory):
                self.assertTrue(guard.check_paths(root, [name]))


class StagedBlobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, 'init', '-q')

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_staged_file_passes(self):
        put(self.root, 'README.md', b'# Public usage\n')
        git(self.root, 'add', 'README.md')
        self.assertEqual(guard.check_git_index(self.root), [])

    def test_staged_secret_detected_after_worktree_cleaned(self):
        value = b'sk-proj-' + b'Z' * 40  # Synthetic; never a usable credential.
        path = put(self.root, 'README.md', value)
        git(self.root, 'add', 'README.md')
        path.write_bytes(b'# Clean worktree\n')
        self.assertEqual(guard.check_paths(self.root, ['README.md']), [])
        issues = guard.check_git_index(self.root)
        self.assertTrue(issues)
        self.assertNotIn(value.decode(), ' '.join(issues))

    def test_staged_private_file_detected_after_worktree_deleted(self):
        path = put(self.root, 'docs/private.md', b'Synthetic local note')
        git(self.root, 'add', 'docs/private.md')
        path.unlink()
        self.assertTrue(any('forbidden staged path' in s for s in guard.check_git_index(self.root)))

    def test_unstaged_lock_fix_cannot_hide_invalid_staged_lock(self):
        name = 'research-figure/assets/upstreams.lock.json'
        path = put(self.root, name, b'{"format":"invalid"}')
        git(self.root, 'add', name)
        path.write_bytes((ROOT / 'assets/upstreams.lock.json').read_bytes())
        self.assertIn('Invalid staged vendor lock', ' '.join(guard.check_git_index(self.root)))

    def test_staged_oversize_is_fail_closed(self):
        put(self.root, 'README.md', b'x' * 100)
        git(self.root, 'add', 'README.md')
        with patch.object(guard, 'MAX_INDEX_BLOB', 40):
            with self.assertRaisesRegex(RuntimeError, 'size bound'):
                guard.read_git_index(self.root)

    def test_staged_symlink_is_rejected(self):
        target = put(self.root, 'local-source', b'Synthetic')
        try:
            (self.root / 'README.md').symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation not permitted')
        git(self.root, 'add', 'README.md')
        self.assertTrue(any('symlink' in s for s in guard.check_git_index(self.root)))

    def test_non_repository_fails_closed(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(RuntimeError):
                guard.read_git_index(Path(empty))


if __name__ == '__main__':
    unittest.main()
