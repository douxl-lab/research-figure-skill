# Embedded kernel maintenance

## Two independent updates

`git pull --ff-only` in the RFS repository gets our released code **and the committed kernel assets**. Installing the complete `research-figure/` directory carries them with it; no submodule initialization or second checkout is required.

Maintainers update copied upstream sources through `scripts/upstreams.py`. This is a selective Git-fetch/pull mechanism, not a raw `git pull` inside `kernels/`. It preserves exact upstream bytes, reviewable revisions and per-file SHA-256/size records while our wrappers retain neutral names and custom policy. Sources are declared in `assets/upstreams.lock.json`; upstream URLs, authors and license texts are not removed.

```bash
# Offline: verify every copied source/material file against the lock
python research-figure/scripts/upstreams.py verify

# Explicit network: inspect the upstream branch, without changing our tree
python research-figure/scripts/upstreams.py check --kernel layout --allow-network

# Apply a clean update after inspection; no git commit/push is performed
python research-figure/scripts/upstreams.py pull --kernel layout --allow-network
# Reproducible update to a chosen commit:
python research-figure/scripts/upstreams.py pull --kernel design --ref FULL_COMMIT_SHA --allow-network

# Re-run gates, review the diff, commit and push in the parent RFS repository
python research-figure/scripts/check_skill.py
python research-figure/scripts/check_repository.py --root . --tracked
python -m unittest discover -s research-figure/tests -v
```

Use `--source /path/to/local/git/mirror --kernel design|layout` for an explicit offline mirror. It reads Git objects without executing source code. `--bootstrap` is only for initially empty kernel directories and defaults to the locked revision, not a floating branch. New releases are fully materialized, so ordinary users do not need it.

## Conflict and rollback policy

Before applying, compare the entire installed snapshot with its recorded hashes. A changed, deleted, extra or symlinked source file **blocks** replacement; do not discard local modifications. Keep customization in `scripts/` or `references/` wrappers. Review local diffs and move intentional customizations into wrappers before updating pristine snapshots. There is no force-overwrite flag.

Updates stage files on the same filesystem, acquire an exclusive transaction lock, recheck source inventory/lock and swap one kernel atomically. A write failure restores the prior directory. Symlinks, path traversal, case collisions, oversized payloads, font files and embedded fonts in Office archives are rejected. License changes block application until explicitly reviewed with `--accept-license-change`; a new upstream version is not automatically trusted. No provider request or dependency installation is performed.

A multi-kernel operation is sequential: if the second fails, the first may already be updated and is reported in `completed`. Inspect that result; do not assume all-or-nothing across both kernels. Run tests before committing. A committed rollback uses `git revert <update-commit>`; an uncommitted rollback requires reviewing/backing up local changes before intentionally restoring the kernel directory and its matching lock together. Do not restore just the lock or just the files.

The narrow public-source allowlist covers only locked upstream materials. It does not allow research outputs, credentials, arbitrary new images or font redistribution in this repository. `build_package.py` verifies the actual package inventory before creating an installable ZIP.
