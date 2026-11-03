#!/usr/bin/env python3
"""Search and inspect the embedded RFS template/gallery library offline."""
from __future__ import annotations
import argparse
import json
from kernels import locate

TAGS = {
 'dual-branch': 'multimodal optical SAR 双分支 多模态 光学 雷达',
 'attention-tokens': 'query token cross attention 标签 注意力',
 'gated-module': 'router dynamic gate 可靠性 门控 动态路由',
 'module-detail': 'mechanism uncertainty evidence 机制细节 不确定性 证据',
 'framework-with-io': 'input output framework 总览 输入 输出',
 'teacher-student': 'distillation teacher student 蒸馏 教师 学生',
 'trainable-frozen': 'frozen trainable backbone 冻结 可训练',
 'teaser-comparison': 'comparison paradigm teaser 对比 范式',
}


def entries(query: str = '') -> list[dict]:
    root = locate('layout')
    if root is None:
        raise ValueError('Embedded layout library missing')
    result = []
    words = query.lower().split()
    for path in sorted((root / 'templates').glob('*.yaml')):
        name = path.stem
        tags = TAGS.get(name, name.replace('-', ' '))
        if words and not all(w in (name + ' ' + tags).lower() for w in words):
            continue
        image = root / 'assets/gallery' / (name + '.png')
        result.append({'id': name, 'tags': tags, 'template': str(path),
                       'preview': str(image) if image.is_file() else None,
                       'usage': 'Reference design only; source science must be supplied and checked'})
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--query', default='')
    a = p.parse_args()
    try:
        print(json.dumps({'templates': entries(a.query)}, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
