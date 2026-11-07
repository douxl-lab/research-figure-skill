"""Offline image2 CLI-contract fixtures, NOT live API or visual-quality tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import image2_adapter as adapter
import workflow
from emit_bundle import emit

# This synthetic CLI accepts the reviewed public flags; it makes no network call.
FAKE_CLI = r'''
import argparse, json, os
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser()
for name in ('prompt-file','base-url','endpoint','model','model-family','size','quality','background','output-format','count','batch-mode','max-retries','timeout','prompt-profile','prompt-lint','output-dir'):
    p.add_argument('--'+name, required=True)
p.add_argument('--image',action='append',default=[])
p.add_argument('--mask')
p.add_argument('--dry-run',action='store_true')
p.add_argument('--json',action='store_true')
a=p.parse_args()
assert os.environ['IMAGE_API_PROVIDERS']==''
assert os.environ['IMAGE_API_MAX_RETRIES']=='0'
assert os.environ['IMAGE_API_CLEAN_INTERMEDIATES']=='0'
assert os.environ['IMAGE_API_EXTRA_HEADERS']=='{}'
assert a.max_retries=='0'
out=Path(a.output_dir);out.mkdir()
text=Path(a.prompt_file).read_text().strip()
payload={k:getattr(a,k) for k in ('model','size','quality','background','output_format')}
payload.update(prompt=text,n=1)
operation='edit' if a.image else 'generate'
config={'max_retries':0,'edit_endpoint' if a.image else 'generation_endpoint':a.endpoint}
(out/'request.json').write_text(json.dumps({'operation':operation,'config':config,'requests':[payload for _ in range(int(a.count))]}))
images=[]
if not a.dry_run:
    for n in range(int(a.count)):
        f=out/f'image-{n}.png'
        Image.new('RGBA',(32,20),(255,255,255,0 if a.background=='transparent' else 255)).save(f)
        images.append(str(f))
print(json.dumps({'ok':True,'dry_run':a.dry_run,'images':images}))
'''


def caps():
    return {"design":{"root":str(ROOT/'kernels/design'),"files":{"skill/native_host.py":True,"skill/exchange.py":True}},
            "layout":{"root":str(ROOT/'kernels/layout'),"files":{"scripts/render.py":True,"scripts/validate.py":True}}}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.runtime=self.root/'image2-api';(self.runtime/'scripts').mkdir(parents=True)
        (self.runtime/'SKILL.md').write_text('# Synthetic CLI contract fixture\n')
        for f in ('generate_image.py','edit_image.py'):
            (self.runtime/'scripts'/f).write_text(FAKE_CLI)
        self.spec=self.root/'spec.json';self.spec.write_bytes((ROOT/'assets/figure-spec-v1-example.json').read_bytes())
        self.prompt=self.root/'brief.txt';self.prompt.write_text('  Complete mechanism figure. Exact labels only.\n')
        self.config=self.root/'service.json';self.config.write_text(json.dumps({
            'provider':'synthetic-fixture','model':'fixture-model','base_url':'https://example.invalid/v1','api_key_env':'RFS_FIXTURE_TOKEN'}))
        self.env=patch.dict(os.environ,{'RFS_FIXTURE_TOKEN':'fixture-only'});self.env.start();self.addCleanup(self.env.stop)

    def args(self, **overrides):
        a=adapter.parser().parse_args(['--spec',str(self.spec),'--prompt',str(self.prompt),
             '--config',str(self.config),'--image2-root',str(self.runtime),'--out',str(self.root/'job'),'--dry-run'])
        for key,value in overrides.items():setattr(a,key,value)
        return a

    def metadata(self,result):
        return json.loads(Path(result['metadata']).read_text())

    def test_default_is_png_not_svg(self):
        a=self.args();self.assertEqual(a.output_format,'png');self.assertEqual(a.candidates,1)

    def test_dry_run_needs_no_key_and_has_no_candidates(self):
        with patch.dict(os.environ,{'RFS_FIXTURE_TOKEN':''}):r=adapter.execute(self.args())
        self.assertEqual(r['status'],'DRY_RUN_VALID_NOT_GENERATED');self.assertEqual(r['candidate_count'],0)
        m=self.metadata(r);self.assertEqual(m['prompt_submission'],'PLANNED_ONLY')
        self.assertEqual(m['scientific_review'],'PENDING')

    def test_live_call_requires_permission_before_execution(self):
        with self.assertRaisesRegex(ValueError,'authorization'):adapter.execute(self.args(dry_run=False))
        self.assertFalse((self.root/'job').exists())

    def test_live_call_requires_explicit_key(self):
        with patch.dict(os.environ,{'RFS_FIXTURE_TOKEN':''}):
            with self.assertRaisesRegex(ValueError,'credential'):adapter.execute(self.args(dry_run=False,allow_external=True))

    def test_synthetic_generation_preserves_both_prompt_hashes_and_bundle(self):
        r=adapter.execute(self.args(dry_run=False,allow_external=True,candidates=2))
        self.assertEqual(r['status'],'GENERATED_UNREVIEWED');self.assertEqual(r['candidate_count'],2)
        m=self.metadata(r);self.assertNotEqual(m['source_prompt_sha256'],m['prompt_sha256'])
        self.assertEqual((self.root/'job/prompt-source.txt').read_bytes(),self.prompt.read_bytes())
        self.assertEqual((self.root/'job/prompt.txt').read_text(),self.prompt.read_text().strip())
        self.assertEqual(emit(self.root/'job',1)['status'],'BUNDLE_EMITTED_UNREVIEWED')

    def test_reference_and_mask_are_snapshotted_without_mutating_original(self):
        image=self.root/'ref.png';mask=self.root/'mask.png'
        Image.new('RGB',(40,30)).save(image);Image.new('RGBA',(40,30),(0,0,0,0)).save(mask)
        original=image.read_bytes();r=adapter.execute(self.args(image=[image],mask=mask))
        self.assertEqual(r['operation'],'edit');self.assertEqual(image.read_bytes(),original)
        records=self.metadata(r)['reference_inputs']
        self.assertEqual([x['role'] for x in records],['primary','mask'])
        self.assertEqual((self.root/'job/reference-1.png').read_bytes(),original)

    def test_mask_without_image_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'mask requires'):adapter.execute(self.args(mask=self.root/'absent'))

    def test_mask_dimensions_are_checked_before_execution(self):
        image=self.root/'ref.png';mask=self.root/'mask.png'
        Image.new('RGB',(40,30)).save(image);Image.new('RGBA',(20,30)).save(mask)
        with self.assertRaisesRegex(ValueError,'dimensions'):adapter.execute(self.args(image=[image],mask=mask))

    def test_opaque_mask_is_rejected(self):
        image=self.root/'ref.png';mask=self.root/'mask.png'
        Image.new('RGB',(40,30)).save(image);Image.new('RGBA',(40,30),(0,0,0,255)).save(mask)
        with self.assertRaisesRegex(ValueError,'transparent editable'):adapter.execute(self.args(image=[image],mask=mask))

    def test_transparency_observation_is_recorded(self):
        r=adapter.execute(self.args(dry_run=False,allow_external=True,background='transparent'))
        self.assertTrue(self.metadata(r)['candidates'][0]['has_transparent_pixels'])

    def test_source_data_never_uses_image_model(self):
        for kind in ('plot','hybrid'):
            data=json.loads(self.spec.read_text());data['kind']=kind;self.spec.write_text(json.dumps(data))
            with self.assertRaises(ValueError):adapter.execute(self.args())

    def test_no_silent_svg_output(self):
        with self.assertRaisesRegex(ValueError,'host LLM'):adapter.execute(self.args(output_format='svg'))

    def test_transparent_jpeg_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'PNG or WebP'):adapter.execute(self.args(background='transparent',output_format='jpeg'))

    def test_existing_output_is_never_overwritten(self):
        (self.root/'job').mkdir();(self.root/'job/keep').write_text('preserve')
        with self.assertRaisesRegex(ValueError,'Output exists'):adapter.execute(self.args())
        self.assertEqual((self.root/'job/keep').read_text(),'preserve')

    def test_output_cannot_be_inside_runtime(self):
        with self.assertRaisesRegex(ValueError,'outside'):adapter.execute(self.args(out=self.runtime/'new-job'))

    def test_missing_backend_blocks_without_generation(self):
        (self.runtime/'scripts/generate_image.py').unlink()
        with self.assertRaises(ValueError):adapter.execute(self.args())

    def test_provider_error_is_sanitized_and_not_retried(self):
        secret='private-response-text'
        def fail(*a,**k):return SimpleNamespace(returncode=1,stdout=secret,stderr=secret)
        with patch.object(adapter.subprocess,'run',side_effect=fail) as run:
            r=adapter.execute(self.args(dry_run=False,allow_external=True))
        self.assertEqual(run.call_count,1);self.assertEqual(r['status'],'FAILED_OR_UNKNOWN')
        self.assertNotIn(secret,Path(r['metadata']).read_text())

    def test_timeout_is_unknown_not_success(self):
        with patch.object(adapter.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixture',1)) as run:
            r=adapter.execute(self.args(dry_run=False,allow_external=True))
        self.assertEqual(run.call_count,1);self.assertEqual(r['status'],'FAILED_OR_UNKNOWN')

    def test_bad_json_cannot_be_success(self):
        r=adapter.execute(self.args(),runner=lambda *a,**k:SimpleNamespace(returncode=0,stdout='not-json'))
        self.assertEqual(r['status'],'DRY_RUN_FAILED')

    def test_request_tampering_cannot_be_success(self):
        def mutate(command,**kwargs):
            result=subprocess.run(command,**kwargs)
            p=self.root/'job/provider-run/request.json';j=json.loads(p.read_text());j['requests'][0]['model']='changed';p.write_text(json.dumps(j))
            return result
        self.assertEqual(adapter.execute(self.args(),runner=mutate)['status'],'DRY_RUN_FAILED')

    def test_returned_image_cannot_escape_run(self):
        def mutate(command,**kwargs):
            result=subprocess.run(command,**kwargs);j=json.loads(result.stdout);j['images']=[str(self.prompt)];result.stdout=json.dumps(j);return result
        r=adapter.execute(self.args(dry_run=False,allow_external=True),runner=mutate)
        self.assertEqual(r['status'],'FAILED_OR_UNKNOWN')

    def test_service_chain_and_implicit_credentials_are_disabled(self):
        with patch.dict(os.environ,{'IMAGE_API_PROVIDERS':'hidden','OPENAI_API_KEY':'other','IMAGE_API_EXTRA_HEADERS':'secret'}):
            env=adapter.child_environment(json.loads(self.config.read_text()),'explicit')
        self.assertEqual(env['IMAGE_API_KEY'],'explicit');self.assertEqual(env['IMAGE_API_PROVIDERS'],'')
        self.assertEqual(env['OPENAI_API_KEY'],'');self.assertEqual(env['IMAGE_API_EXTRA_HEADERS'],'{}')

    def test_workflow_selects_image2_only_when_configured_and_authorized(self):
        spec={'schema_version':'1.0.0','kind':'diagram'}
        p=workflow.make_plan(spec,caps(),image2_root=self.runtime,allow_external=True)
        self.assertEqual(p['mode'],'image2-api');self.assertEqual(p['status'],'PLANNED_NOT_EXECUTED')
        p=workflow.make_plan(spec,caps(),image2_root=self.runtime,host_image_tool='real',allow_external=True)
        self.assertEqual(p['mode'],'design-native')

    def test_workflow_dry_run_does_not_require_external_authorization(self):
        p=workflow.make_plan({'schema_version':'1.0.0','kind':'diagram'},caps(),mode='image2-api',image2_root=self.runtime,dry_run=True)
        self.assertFalse(p['blockers'])
        r=workflow.execute(p,self.spec,self.root/'workflow-job',image2_config=self.config,prompt=self.prompt,candidates=1)
        self.assertEqual(r['status'],'DRY_RUN_VALID_NOT_GENERATED')

    def test_dry_run_cannot_accidentally_execute_other_backend(self):
        p=workflow.make_plan({'schema_version':'1.0.0','kind':'diagram'},caps(),host_image_tool='real',dry_run=True)
        self.assertEqual(p['status'],'BLOCKED')

    def test_svg_handoff_needs_no_image_api(self):
        p=workflow.make_plan({'schema_version':'1.0.0','kind':'diagram'},caps(),mode='llm-svg')
        self.assertEqual(p['status'],'HOST_ACTION_REQUIRED')
        r=workflow.execute(p,self.spec,self.root/'svg-job')
        self.assertEqual(r['status'],'HOST_ACTION_REQUIRED');self.assertFalse((self.root/'svg-job/figure.svg').exists())

    def test_invalid_explicit_runtime_does_not_silently_fallback(self):
        p=workflow.make_plan({'schema_version':'1.0.0','kind':'diagram'},caps(),image2_root=self.root/'absent',allow_external=True)
        self.assertEqual(p['status'],'BLOCKED')


if __name__=='__main__':unittest.main()
