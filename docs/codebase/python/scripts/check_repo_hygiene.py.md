# `scripts/check_repo_hygiene.py`

Small structural hygiene checker for the repository.

## Purpose

- Verify the codebase map guides exist.
- Verify each relevant source/test file has a mirrored summary.
- Detect orphaned summaries whose source file no longer exists.

## Scope

- Python source, tests, and scripts
- Legacy webapp source, React/TypeScript webapp source, and browser-facing tests
- Generated frontend bundles under `src/vantage_v5/webapp/generated/` are ignored because they are build outputs.

## Usage

```bash
python3 scripts/check_repo_hygiene.py
```

The script exits non-zero when mirrored documentation has drifted from the codebase shape.
