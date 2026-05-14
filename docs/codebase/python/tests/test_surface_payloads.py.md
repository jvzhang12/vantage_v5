# `tests/test_surface_payloads.py`

Tests for operational surface payload creation.

## Purpose

- Verify date resolution from ISO dates embedded in user messages.
- Verify focus suggestions pair prioritized tasks with open calendar blocks.
- Verify schedule/calendar plus task invocations create a composite `today_briefing`.
- Verify non-operational invocations do not create UI surface payloads.

## Coverage

- `resolve_surface_date()`.
- `build_focus_suggestions()`.
- `SurfacePayloadBuilder.build_for_turn()`.
