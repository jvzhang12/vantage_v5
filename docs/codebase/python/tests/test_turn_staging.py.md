# `tests/test_turn_staging.py`

Focused unit tests for backend turn staging contracts.

## Purpose

- Verify staging contracts are public-safe and bound retry attempts.
- Verify progress sanitization removes hidden/provider/schema/debug/reasoning data.
- Verify parsed-output audit behavior for accepted, retryable, and terminal results.

## Coverage

- `TurnStage.to_payload()` preserves the public stage contract while stripping hidden keys from dict contracts.
- `StageProgressEvent` and public payload sanitizers keep user-visible progress free of provider/debug/schema/reasoning leakage.
- `audit_stage_output()` accepts valid draft whiteboard output.
- Missing offer/draft workspace updates return retryable audit results before the attempt budget is exhausted.
- Contract failures become terminal once `max_attempts` is reached.
- Recursive sanitization drops hidden keys from nested dictionaries and lists.
