#!/usr/bin/env python3
"""Compatibility entry for an EXPLICIT image-provider smoke test.

Use the same source-bound prompt/config/output/authorization flags as generation.
No baked-in model, endpoint, filesystem path or hidden paid request is used.
"""
from generate_from_prompt import main

if __name__ == '__main__':
    raise SystemExit(main())
