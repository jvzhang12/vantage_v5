# `tests/test_repo_hygiene.py`

Regression test for the repo-structure hygiene checker.

## Purpose

- Run `scripts/check_repo_hygiene.py` inside the repo root.
- Fail fast if mirrored source summaries or codebase guide files drift out of sync.

## Why It Matters

- This gives the documentation contract a real test boundary instead of relying on memory.
