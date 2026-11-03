# Embedded kernel maintenance

## Original upstream versus our maintained integration

**`check` now uses the original author's `original_upstream` by default** when that field exists. It compares the actual original source commit against `original_revision` in the lock, instead of reporting changes against our fork as if they were upstream changes. `installed_diff` is separately reported to show why an unmodified copy would be unsafe. For the design kernel, the authoritative original is `dwzhu-pku/PaperBanana`; our maintained fork is `douxl-lab/PaperBanana`.

The design kernel is **fork-protected**: upstream lacks our canonical FigureSpec protocol, `skill/native_host.py`, Exchange and privacy restrictions. Consequently a direct `pull --kernel design` of the raw original (the default source) intentionally **fails closed**. The supported three-step process is original discovery → adaptation and tests in our maintained fork → explicitly pull the tested maintained fork commit into RFS. This avoids falsely claiming that a fork-derived snapshot contains exactly the pristine original commit.

The lock records three distinct revisions: `original_revision` is the original common-ancestor baseline, `original_head_reviewed` is the latest original HEAD inspected (not fully merged), and `revision` is the exact maintained fork commit whose bytes are bundled. `adapted_upstream_topics` lists selected incorporated changes. A checked original HEAD is not itself an installed upgrade.

```bash
# No changes: compare original author's main to the pinned original baseline.
python research-figure/scripts/upstreams.py check --kernel design --allow-network

# Safe, separate step AFTER reviewing and committing adapted changes in our fork:
python research-figure/scripts/upstreams.py check --kernel design --source-role maintained --allow-network
python research-figure/scripts/upstreams.py pull --kernel design --source-role maintained --ref FULL_FORK_COMMIT_SHA --allow-network
python research-figure/scripts/upstreams.py verify

# Equivalent offline evaluation against a trusted original/fork Git mirror:
python research-figure/scripts/upstreams.py check --kernel design --source /outside/original-checkout
python research-figure/scripts/upstreams.py pull --kernel design --source-role maintained --source /outside/maintained-fork --ref FULL_FORK_COMMIT_SHA

# Layout remains un-forked and can be checked/pulled from its recorded repository.
python research-figure/scripts/upstreams.py check --kernel layout --allow-network
python research-figure/scripts/upstreams.py pull --kernel layout --allow-network
```

`git pull --ff-only` in the RFS repository gets the already released code **and all committed kernel assets**. The complete `research-figure/` installation does not require a second clone/submodule. The update helper only reads Git objects and stages reviewable files; no downloaded Python is executed and no provider calls, dependency installs, commits or pushes occur automatically.

For exact reproduction use `--ref FULL_COMMIT_SHA`. `--bootstrap` is strictly for an initially empty kernel and defaults to the locked maintained snapshot. Keep outputs, reference datasets, credentials and logs outside the installed Skill. Current design CLI materializes Hugging Face Parquet references in the user cache or the explicitly supplied `--work-dir`, not the public repository.

After any accepted update, check the **entire** newly resolved dependency graph, scientific provenance, static audits and offline smoke tests, then review Git diff/CI before committing. Tests never prove live paid-model execution or scientific fidelity.

## Conflict and rollback policy

Before applying, compare the entire installed snapshot with its recorded hashes. A changed, deleted, extra or symlinked source file **blocks** replacement; do not discard local modifications. Keep customization in `scripts/` or `references/` wrappers. Review local diffs and move intentional customizations into wrappers before updating pristine snapshots. There is no force-overwrite flag.

Updates stage files on the same filesystem, acquire an exclusive transaction lock, recheck source inventory/lock and swap one kernel atomically. A write failure restores the prior directory. Symlinks, path traversal, case collisions, oversized payloads, font files and embedded fonts in Office archives are rejected. License changes block application until explicitly reviewed with `--accept-license-change`; a new upstream version is not automatically trusted. No provider request or dependency installation is performed.

A multi-kernel operation is sequential: if the second fails, the first may already be updated and is reported in `completed`. Inspect that result; do not assume all-or-nothing across both kernels. Run tests before committing. A committed rollback uses `git revert <update-commit>`; an uncommitted rollback requires reviewing/backing up local changes before intentionally restoring the kernel directory and its matching lock together. Do not restore just the lock or just the files.

The narrow public-source allowlist covers only locked upstream materials. It does not allow research outputs, credentials, arbitrary new images or font redistribution in this repository. `build_package.py` verifies the actual package inventory before creating an installable ZIP.
