#!/usr/bin/env python3
"""RFS design coordinator. Executes no image tool and obtains no provider key."""
from __future__ import annotations
import argparse
import subprocess
import sys
from kernels import locate, python_for_design


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kernel', choices=['design'])
    p.add_argument('command', choices=['prepare', 'next', 'record', 'verify', 'repair'])
    args, rest = p.parse_known_args()
    root = locate(args.kernel)
    if not root or not (root / 'skill/native_host.py').is_file():
        p.error('Embedded design kernel missing; install the complete research-figure directory')
    # Arguments remain a list: no shell or interpolated commands.
    try:
        done = subprocess.run([python_for_design(), str(root / 'skill/native_host.py'), args.command, *rest],
                              cwd=root, timeout=90, check=False)
        return done.returncode
    except (OSError, subprocess.TimeoutExpired):
        print('Design coordinator could not complete; inspect job state before retrying', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
