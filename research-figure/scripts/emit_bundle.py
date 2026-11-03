#!/usr/bin/env python3
"""Assemble verified, provenance-bound local image artifacts into an RFS v1 bundle.

This is an independent producer adapter, not proof of upstream pipeline execution.
Byte integrity, scientific review, visual review and user approval remain separate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from bridge import _api


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def emit(source: Path, candidate: int, output: Path | None = None, *, metadata: Path | None = None) -> dict:
    contract, interop, _ = _api()
    if type(candidate) is not int or candidate < 1:
        raise ValueError('candidate must be a positive integer')
    source = interop.ordinary_path(source)
    spec_path = source / 'figure-spec.json'
    spec = interop.load_spec(spec_path)
    if spec['kind'] != 'diagram':
        raise ValueError('Only an actual diagram image can enter this reconstruction bundle')
    paths = {'figure_spec': spec_path, 'prompt': source / 'prompt.txt', 'design': source / 'design-intent.md'}
    payloads = {role: interop.read_bytes(path) for role, path in paths.items()}
    if metadata is None:
        possibilities = [source / 'candidates/generation-metadata.json', source / 'generation-metadata.json']
        found = [p for p in possibilities if p.is_file()]
        if len(found) != 1:
            raise ValueError('Require exactly one generation metadata file, or explicit --metadata')
        metadata = found[0]
    metadata = interop.ordinary_path(metadata)
    meta_raw = interop.read_bytes(metadata)
    meta = json.loads(meta_raw.decode('utf-8'))
    if not isinstance(meta, dict):
        raise ValueError('Generation metadata must be an object')
    for name in ('provider', 'model'):
        if not isinstance(meta.get(name), str) or not meta[name].strip():
            raise ValueError('Metadata must contain actual provider and configured model identity')
    if meta.get('prompt_sha256') != digest(payloads['prompt']):
        raise ValueError('Submitted prompt binding missing or changed')
    if meta.get('figure_spec_sha256') != digest(payloads['figure_spec']):
        raise ValueError('Generation FigureSpec bytes changed or were not bound')
    fingerprint = contract.scientific_fingerprint(spec)
    if meta.get('scientific_fingerprint') != fingerprint:
        raise ValueError('Scientific source fingerprint changed')
    records = meta.get('candidates')
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise ValueError('Candidate provenance is missing')
    chosen = [r for r in records if r.get('index') == candidate and r.get('status') == 'succeeded']
    if len(chosen) != 1:
        raise ValueError('Chosen candidate must have exactly one successful provenance record')
    rec = chosen[0]
    if not isinstance(rec.get('file'), str) or not rec['file']:
        raise ValueError('Candidate file path is missing')
    relative = Path(rec['file'])
    image = interop.ordinary_path(metadata.parent / relative)
    if source not in image.parents:
        raise ValueError('Candidate must remain inside the selected job')
    raw = interop.read_bytes(image, 64 * 1024 * 1024)
    if digest(raw) != rec.get('sha256') or len(raw) != rec.get('bytes'):
        raise ValueError('Candidate bytes changed or provenance is incomplete')
    from generate_from_prompt import image_info
    ext, mime, width, height = image_info(raw)
    if rec.get('mime') != mime or rec.get('width') != width or rec.get('height') != height:
        raise ValueError('Candidate image metadata does not match its actual bytes')
    payloads.update(image=raw, generation_metadata=meta_raw)
    names = {'figure_spec':'figure-spec.json', 'prompt':'prompt.txt', 'design':'design-intent.md',
             'image':'image' + ext, 'generation_metadata':'generation-metadata.json'}
    mimes = {'figure_spec':'application/json', 'prompt':'text/plain', 'design':'text/markdown',
             'image':mime, 'generation_metadata':'application/json'}
    manifest = {'schema_version':'1.0.0', 'candidate_id':f'rfs-local-{candidate}', 'status':'succeeded',
       'stage':'design', 'provider':meta['provider'], 'model':meta['model'], 'description_key':f'candidate-{candidate}',
       'options':{k:meta[k] for k in ('size','quality','requested_candidates') if k in meta},
       'provenance':{'scientific_verification':spec['provenance']['scientific_verification'],
          'external_consumer_verified':False, 'editable_reconstruction_verified':False, 'image_bytes_preserved':True,
          'generation':{'pipeline':meta.get('pipeline','host-single-shot'), 'generated_at':meta.get('generated_at'),
                        'visual_review':meta.get('visual_review','PENDING'), 'model_source':meta.get('model_source','recorded_by_host'),
                        'compiler_metadata':{'prompt_sha256':digest(payloads['prompt'])}}},
       'scientific_fingerprint':fingerprint, 'review':[], 'review_status':'pending-user-approval', 'error':None,
       'files':{role:{'path':names[role], 'mime':mimes[role], 'sha256':digest(data), 'bytes':len(data)} for role,data in payloads.items()}}
    out = interop.ordinary_path(output or source / 'bundle')
    package = {names[role]:data for role,data in payloads.items()}
    package['manifest.json'] = interop.json_bytes(manifest)
    folder = interop.write_new_folder(out, package)
    try:
        interop.verify_result(folder, spec)
    except Exception:
        shutil.rmtree(folder)  # Only the newly created bundle, never source artifacts.
        raise
    return {'status':'BUNDLE_EMITTED_UNREVIEWED', 'bundle':str(folder), 'scientific_fingerprint':fingerprint,
            'scientific_review':'PENDING', 'user_approval':'PENDING', 'native_editability':'NOT_EXECUTED'}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dir', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=int)
    p.add_argument('--out', type=Path)
    p.add_argument('--metadata', type=Path)
    a = p.parse_args()
    try:
        print(json.dumps(emit(a.dir,a.candidate,a.out,metadata=a.metadata),indent=2))
        return 0
    except (ValueError,OSError,ImportError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
