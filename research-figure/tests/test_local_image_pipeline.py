"""Synthetic API responses only. No model traffic, credits or scientific results."""
from __future__ import annotations
import asyncio
import base64
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import generate_from_prompt as gen
from emit_bundle import emit
import bridge


def png():
    b=io.BytesIO(); Image.new('RGB',(16,16)).save(b,format='PNG'); return b.getvalue()


class FakeClient:
    def __init__(self, *, fail_after=None, **kwargs):
        self.options=kwargs; self.calls=[]; self.images=self; self.fail_after=fail_after
    async def __aenter__(self): return self
    async def __aexit__(self,*_): return False
    async def generate(self,**kwargs):
        self.calls.append(kwargs)
        if self.fail_after is not None and len(self.calls)>self.fail_after:
            raise RuntimeError('PRIVATE PROVIDER TEXT MUST NOT BE LOGGED')
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(png()).decode())],model='synthetic-observed-model')


class LocalPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.spec=self.base/'figure-spec.json'; self.spec.write_bytes((ROOT/'assets/figure-spec-v1-example.json').read_bytes())
        self.prompt=self.base/'prompt.txt'; self.prompt.write_text('  SYNTHETIC FIXTURE ONLY\n',encoding='utf-8')
        (self.base/'design-intent.md').write_text('Synthetic test intent, not an inspected real figure.\n')
        self.config=self.base/'service.json'; self.config.write_text(json.dumps({'provider':'synthetic-provider','model':'synthetic-model','base_url':'https://example.invalid/v1','api_key_env':'RFS_TEST_VALUE'}))
        self.args=gen.parser().parse_args(['--prompt',str(self.prompt),'--out',str(self.base/'candidates'),'--config',str(self.config),'--allow-external'])
        self.client=FakeClient()

    def generate(self,client=None):
        with patch.dict(os.environ,{'RFS_TEST_VALUE':'synthetic-not-a-real-key'}):
            return asyncio.run(gen.execute(self.args,client_factory=lambda **kw: self.capture(kw,client or self.client)))

    def capture(self,opts,client):
        client.options=opts; return client

    def test_generator_emitter_and_protocol_complete_chain(self):
        result=self.generate()
        self.assertEqual(result['status'],'GENERATED_UNREVIEWED')
        self.assertEqual(self.client.options['max_retries'],0)
        self.assertEqual(self.client.calls[0]['prompt'],'  SYNTHETIC FIXTURE ONLY\n')
        bundle=emit(self.base,1)
        m,_,_=bridge._api()[1].verify_result(self.base/'bundle',json.loads(self.spec.read_text()))
        self.assertEqual(m['provider'],'synthetic-provider')
        self.assertEqual(m['model'],'synthetic-model')
        self.assertEqual(m['review_status'],'pending-user-approval')
        self.assertFalse(m['provenance']['editable_reconstruction_verified'])
        self.assertEqual((self.base/'bundle/image.png').read_bytes(),png())
        self.assertTrue((self.base/'bundle/generation-metadata.json').is_file())
        self.assertEqual(bundle['status'],'BUNDLE_EMITTED_UNREVIEWED')

    def test_no_authorization_means_no_output_or_calls(self):
        self.args.allow_external=False
        with self.assertRaises(ValueError): self.generate()
        self.assertFalse(self.args.out.exists()); self.assertFalse(self.client.calls)

    def test_real_data_plot_refused_before_api_call(self):
        self.spec.write_bytes((ROOT/'assets/figure-plot-v1-example.json').read_bytes())
        with self.assertRaises(ValueError): self.generate()
        self.assertFalse(self.client.calls)

    def test_failure_is_partial_and_error_text_redacted(self):
        self.args.candidates=3; fake=FakeClient(fail_after=1)
        result=self.generate(fake)
        self.assertEqual(result['status'],'FAILED_OR_PARTIAL')
        self.assertEqual(len(fake.calls),2)
        self.assertNotIn('PRIVATE PROVIDER',Path(result['metadata']).read_text())
        self.assertEqual(result['candidate_count'],1)

    def test_candidate_and_prompt_tampering_rejected(self):
        self.generate()
        self.prompt.write_text('modified')
        with self.assertRaisesRegex(ValueError,'prompt'): emit(self.base,1)
        self.prompt.write_text('  SYNTHETIC FIXTURE ONLY\n')
        (self.base/'candidates/candidate-1.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'bytes changed'): emit(self.base,1)

    def test_science_binding_rejects_even_visual_only_spec_change(self):
        self.generate()
        doc=json.loads(self.spec.read_text()); doc['design']['layout']='changed layout'
        self.spec.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'FigureSpec bytes'): emit(self.base,1)

    def test_missing_provider_and_ambiguous_sidecars_rejected(self):
        self.generate()
        path=self.base/'candidates/generation-metadata.json'; meta=json.loads(path.read_text())
        meta.pop('provider'); path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,'provider'): emit(self.base,1)
        (self.base/'generation-metadata.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'exactly one'): emit(self.base,1)

    def test_existing_directory_never_overwritten(self):
        self.args.out.mkdir()
        with self.assertRaisesRegex(ValueError,'Output exists'): self.generate()
        self.assertFalse(self.client.calls)

    def test_config_credentials_and_unsafe_http_refused(self):
        original=json.loads(self.config.read_text())
        for bad in ['http://remote.invalid/v1','https://user:secret@example.invalid','https://example.invalid?key=not-real']:
            self.config.write_text(json.dumps(dict(original,base_url=bad)))
            with self.assertRaises(ValueError): gen.load_config(self.config)
        self.config.write_text(json.dumps(dict(original,base_url='http://127.0.0.1:8123/v1',allow_http_loopback=True)))
        self.assertEqual(gen.load_config(self.config)['provider'],'synthetic-provider')

    def test_non_image_response_rejected(self):
        with self.assertRaises(ValueError): gen.image_info(b'<html>not an image</html>')

    def test_candidate_bound_and_metadata_type_rejections(self):
        self.args.candidates=0
        with self.assertRaises(ValueError): self.generate()
        with self.assertRaises(ValueError): emit(self.base,0)


if __name__=='__main__': unittest.main()
