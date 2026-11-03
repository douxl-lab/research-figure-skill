#!/usr/bin/env python3
"""Run the real embedded coordinators/renderers offline with synthetic fixtures.

This checks executable integration and native objects, not AI generation or
scientific correctness. No credentials, downloads or provider calls are used.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from kernels import discover
from workflow import make_plan, execute
ROOT=Path(__file__).resolve().parents[1]
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}


def smoke(out: Path) -> dict:
    spec=ROOT/'assets/figure-spec-v1-example.json'
    data=json.loads(spec.read_text())
    caps=discover(environ={})
    native=execute(make_plan(data,caps,host_image_tool='synthetic-test-declaration-not-a-model-call'),spec,out/'native')
    if native['status']!='HOST_ACTION_REQUIRED':
        raise ValueError('Native preparation must not claim generation')
    layout=execute(make_plan(data,caps,mode='layout'),spec,out/'layout',layout_spec=ROOT/'assets/demo-synthetic-layout.yaml')
    pptx=out/'layout/figure.pptx'
    with zipfile.ZipFile(pptx) as z:
        slide=ET.fromstring(z.read('ppt/slides/slide1.xml'))
        if any('/fonts/' in n.lower() for n in z.namelist()):
            raise ValueError('Unexpected embedded fonts')
    texts=[n.text for n in slide.findall('.//a:t',NS)]
    if not all(label in texts for label in ('Input features','Encoder','Embedding')):
        raise ValueError('Missing native text')
    connectors=slide.findall('.//p:cxnSp',NS)
    if len(connectors)!=2 or any(c.find('.//a:stCxn',NS) is None or c.find('.//a:endCxn',NS) is None for c in connectors):
        raise ValueError('Expected two glued native connectors')
    if slide.findall('.//p:pic',NS):
        raise ValueError('Synthetic native fixture must not be flattened to an image')
    if layout['audit'].get('counts',{}).get('error')!=0:
        raise ValueError('Layout validator errors')
    result={'status':'OFFLINE_SMOKE_PASSED','source':'synthetic fixtures only',
            'native_coordinator':'prepared actual job; no host image call',
            'layout_outputs':['svg','pptx','vsdx'], 'native_connectors':len(connectors),
            'native_labels':texts, 'visual_review':'PENDING', 'live_image_generation':'NOT_EXECUTED'}
    (out/'smoke-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:
        if a.out:
            a.out.mkdir(parents=True,exist_ok=False)
            result=smoke(a.out)
        else:
            with tempfile.TemporaryDirectory(prefix='rfs-smoke-') as d:
                result=smoke(Path(d))
        print(json.dumps(result,indent=2))
        return 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'status':'FAILED','reason':str(exc)}))
        return 2


if __name__=='__main__': raise SystemExit(main())
