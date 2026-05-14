# `tests/test_tasks.py`

Tests for the read-only local task provider and focus grouping.

## Purpose

- Verify due, overdue, high-priority, near-term, deferrable, and unscheduled task grouping.
- Verify the JSON-backed provider filters closed tasks and serializes focus payloads.
- Verify missing task files return empty read-only payloads instead of failing.

## Coverage

- Pure `group_tasks_for_focus()` ordering.
- `LocalTaskProvider.focus()` happy path.
- Missing-file empty state.
