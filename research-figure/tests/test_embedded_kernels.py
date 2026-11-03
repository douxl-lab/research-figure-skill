"""Embedded source/update/package contracts; all images are synthetic test fixtures."""
from __future__ import annotations
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import kernels
import upstreams as u
import workflow
from check_repository import check_paths
from build_package import build


class EmbeddedTests(unittest.TestCase):
    def test_embedded_sources_assets_and_licenses_verify(self):
        lock=u.read_lock(ROOT)
        self.assertEqual(set(lock['kernels']), {'design','layout'})
        for entry in lock['kernels'].values():
            self.assertEqual(u.verify_entry(ROOT,entry)['status'],'VERIFIED')
        self.assertEqual(len(list((ROOT/'kernels/layout/templates').glob('*.yaml'))),16)
        self.assertEqual(len(list((ROOT/'kernels/layout/assets/gallery').glob('*.png'))),19)
        self.assertFalse(list((ROOT/'kernels').rglob('SKILL.md')))

    def test_default_no_external_checkout_or_credentials(self):
        found=kernels.discover(environ={})
        self.assertTrue(all(v['embedded'] for v in found.values()))
        self.assertFalse(any(v['runtime_verified'] for v in found.values()))
        spec=json.loads((ROOT/'assets/figure-spec-v1-example.json').read_text())
        p=workflow.make_plan(spec,found,host_image_tool='test-declaration')
        self.assertEqual(p['mode'],'design-native')
        self.assertEqual(workflow.make_plan(spec,found)['status'],'BLOCKED')

    def test_legacy_mode_and_env_aliases(self):
        found=kernels.discover(environ={})
        spec={'schema_version':'1.0.0','kind':'diagram'}
        for old,new in [('paperbanana-native','design-native'),('paperbanana-provider','design-provider'),('cvpr-figure','layout')]:
            p=workflow.make_plan(spec,found,mode=old,allow_external=True,host_image_tool='test')
            self.assertEqual(p['mode'],new)
        self.assertEqual(kernels.locate('design',environ={'PAPERBANANA_ROOT':str(ROOT/'kernels/design')}),ROOT/'kernels/design')
        self.assertIsNone(kernels.locate('design',environ={'RFS_DESIGN_ROOT':'/definitely-missing-rfs-kernel'}))

    def test_narrow_source_whitelist_rejects_extra_and_changed(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); root=base/'research-figure'
            (root/'assets').mkdir(parents=True)
            (root/'assets/upstreams.lock.json').write_bytes((ROOT/'assets/upstreams.lock.json').read_bytes())
            rel='research-figure/kernels/layout/assets/gallery/attention-tokens.png'
            dest=base/rel; dest.parent.mkdir(parents=True)
            dest.write_bytes((ROOT.parent/rel).read_bytes())
            self.assertEqual(check_paths(base,[rel]),[])
            dest.write_bytes(b'tampered')
            self.assertTrue(check_paths(base,[rel]))
            self.assertTrue(check_paths(base,['research-figure/kernels/layout/new-private.png']))

    def test_package_complete_reproducible_and_offline_copy_usable(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            a=build(base/'a.zip'); b=build(base/'b.zip')
            self.assertEqual(a['sha256'],b['sha256'])
            import zipfile
            with zipfile.ZipFile(a['path']) as z:
                self.assertTrue(any(n.endswith('attention-tokens.png') for n in z.namelist()))
                self.assertFalse(any(Path(n).suffix.lower() in u.FONT_EXT for n in z.namelist()))
                z.extractall(base/'install')
            installed=base/'install/research-figure'
            self.assertEqual(u.verify_entry(installed,u.read_lock(installed)['kernels']['design'])['status'],'VERIFIED')
            with patch.dict(os.environ,{},clear=True):
                self.assertEqual(kernels.locate('layout',root=installed),installed/'kernels/layout')
            p=subprocess.run([sys.executable,str(installed/'scripts/library.py'),'--query','attention'],capture_output=True,text=True,timeout=30,
                env={k:v for k,v in os.environ.items() if not k.startswith(('PAPERBANANA_','CVPR_FIGURE_','RFS_DESIGN_','RFS_LAYOUT_'))})
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('attention-tokens',p.stdout)


class PullTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name); self.source=self.base/'upstream'; self.root=self.base/'research-figure'
        self.source.mkdir(); (self.root/'assets').mkdir(parents=True)
        self.run_git('init','-q','-b','main')
        self.run_git('config','user.name','RFS fixture')
        self.run_git('config','user.email','fixture@example.invalid')
        (self.source/'LICENSE').write_text('Synthetic test license\n')
        (self.source/'core.py').write_text('raise RuntimeError("SOURCE MUST NEVER EXECUTE")\n')
        self.rev=self.commit()
        entry={'destination':'kernels/design','repository':'https://github.com/example/fixture','revision':self.rev,
            'branch':'main','license':'fixture','license_sha256':u.digest((self.source/'LICENSE').read_bytes()),
            'include':['LICENSE','*.py'],'files':{}}
        (self.root/u.LOCK).write_text(json.dumps({'format':'rfs-upstreams/1.0','kernels':{'design':entry}}))
        u.sync(self.root,'design',action='pull',source=self.source,bootstrap=True)

    def run_git(self,*args):
        p=subprocess.run(['git',*args],cwd=self.source,capture_output=True,text=True,check=True)
        return p.stdout.strip()

    def commit(self):
        self.run_git('add','-A'); self.run_git('commit','-qm','synthetic fixture')
        return self.run_git('rev-parse','HEAD')

    def test_check_is_read_only_and_pull_records_added_changed_removed(self):
        lock_before=(self.root/u.LOCK).read_bytes()
        (self.source/'core.py').unlink(); (self.source/'new.py').write_text('NEW_FIXTURE = True\n')
        rev=self.commit()
        check=u.sync(self.root,'design',source=self.source)
        self.assertIn('new.py',check['diff']['added']); self.assertIn('core.py',check['diff']['removed'])
        self.assertEqual((self.root/u.LOCK).read_bytes(),lock_before)
        result=u.sync(self.root,'design',action='pull',source=self.source)
        self.assertEqual(result['status'],'UPDATED_UNTESTED')
        self.assertEqual(u.read_lock(self.root)['kernels']['design']['revision'],rev)
        self.assertFalse((self.root/'kernels/design/core.py').exists())
        self.assertEqual(u.sync(self.root,'design',action='pull',source=self.source)['status'],'UP_TO_DATE')

    def test_dirty_source_or_extra_file_never_overwritten(self):
        target=self.root/'kernels/design/core.py'
        target.write_text('local modification')
        with self.assertRaisesRegex(ValueError,'conflict'):
            u.sync(self.root,'design',action='pull',source=self.source)
        self.assertEqual(target.read_text(),'local modification')
        target.write_bytes((self.source/'core.py').read_bytes())
        (target.parent/'extra.py').write_text('private')
        with self.assertRaisesRegex(ValueError,'conflict'):
            u.sync(self.root,'design',source=self.source)

    def test_license_change_needs_explicit_review(self):
        (self.source/'LICENSE').write_text('Changed test license\n'); self.commit()
        self.assertTrue(u.sync(self.root,'design',source=self.source)['license_changed'])
        with self.assertRaisesRegex(ValueError,'license changed'):
            u.sync(self.root,'design',action='pull',source=self.source)
        u.sync(self.root,'design',action='pull',source=self.source,accept_license_change=True)
        self.assertEqual((self.root/'kernels/design/LICENSE').read_text(),'Changed test license\n')

    def test_original_upstream_is_default_and_protected_fork_is_not_overwritten(self):
        # The exact reference baseline is the first synthetic revision.
        lock_path = self.root / u.LOCK
        lock = json.loads(lock_path.read_text())
        entry = lock['kernels']['design']
        entry.update(original_upstream='https://github.com/original/fixture',
                     original_revision=self.rev, fork_protected=True)
        lock_path.write_text(json.dumps(lock))
        (self.source / 'core.py').write_text('UPSTREAM_ONLY_FIX = True\n')
        new_revision = self.commit()
        read_only_before = lock_path.read_bytes()
        inspected = u.sync(self.root, 'design', action='check', source=self.source)
        self.assertEqual(inspected['source_role'], 'original')
        self.assertEqual(inspected['source_repository'], 'https://github.com/original/fixture')
        self.assertEqual(inspected['from_revision'], self.rev)
        self.assertEqual(inspected['to_revision'], new_revision)
        self.assertEqual(inspected['diff']['changed'], ['core.py'])
        self.assertEqual(lock_path.read_bytes(), read_only_before)
        with self.assertRaisesRegex(ValueError, 'protected fork-only'):
            u.sync(self.root, 'design', action='pull', source=self.source)
        self.assertEqual((self.root / 'kernels/design/core.py').read_text(),
                         'raise RuntimeError("SOURCE MUST NEVER EXECUTE")\n')
        adapted = u.sync(self.root, 'design', action='pull', source=self.source,
                         source_role='maintained')
        self.assertEqual(adapted['status'], 'UPDATED_UNTESTED')
        self.assertEqual(adapted['source_role'], 'maintained')

    def test_original_upstream_contract_requires_provenance(self):
        lock_path=self.root/u.LOCK
        lock=json.loads(lock_path.read_text())
        lock['kernels']['design']['original_upstream']='https://github.com/original/fixture'
        lock_path.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, 'original_revision'):
            u.read_lock(self.root)

    def test_network_is_opt_in(self):
        with self.assertRaisesRegex(ValueError,'allow-network'):
            u.sync(self.root,'design')

    def test_atomic_rollback_when_lock_replace_fails(self):
        before=(self.root/u.LOCK).read_bytes(); old=(self.root/'kernels/design/core.py').read_bytes()
        (self.source/'core.py').write_text('NEW = True\n'); self.commit()
        with patch('upstreams.os.replace',side_effect=OSError('synthetic disk error')):
            with self.assertRaises(OSError):
                u.sync(self.root,'design',action='pull',source=self.source)
        self.assertEqual((self.root/u.LOCK).read_bytes(),before)
        self.assertEqual((self.root/'kernels/design/core.py').read_bytes(),old)
        self.assertFalse((self.root/'kernels/.upstream-sync.lock').exists())

    def test_concurrent_transaction_blocks_without_overwrite(self):
        (self.source/'core.py').write_text('NEW = 2\n'); self.commit()
        mutex=self.root/'kernels/.upstream-sync.lock'; mutex.touch()
        with self.assertRaises(FileExistsError):
            u.sync(self.root,'design',action='pull',source=self.source)
        self.assertTrue(mutex.exists())

    def test_upstream_symlink_and_font_rejected(self):
        if hasattr(os,'symlink'):
            (self.source/'bad.py').symlink_to('core.py'); self.commit()
            with self.assertRaisesRegex(ValueError,'Symlink'):
                u.sync(self.root,'design',source=self.source)
        self.assertFalse(u.permitted('font.ttf'))
        self.assertFalse(u.permitted('private/.env'))
        self.assertFalse(u.permitted('../escape.py'))
        self.assertFalse(u.permitted('SKILL.md'))

    def test_kernel_parent_symlink_is_rejected(self):
        if not hasattr(os,'symlink'): self.skipTest('symlink unavailable')
        (self.root/'kernels').rename(self.base/'moved-kernels')
        (self.root/'kernels').symlink_to(self.base/'moved-kernels',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlinks'):
            u.read_lock(self.root)


if __name__=='__main__': unittest.main()
