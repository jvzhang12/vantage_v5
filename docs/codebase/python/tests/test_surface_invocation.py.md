# `tests/test_surface_invocation.py`

Focused unit tests for the deterministic surface invocation policy.

## Coverage

- Email drafting becomes a `durable_artifact` intent with `whiteboard` as the primary surface and `draft` as the requested whiteboard mode.
- Explicit chat-only phrasing prevents automatic whiteboard drafting.
- Today/day schedule lookups summon `calendar_day`.
- Schedule planning summons `calendar_day` with `task_focus` and `whiteboard` support.
- To-do/focus requests summon `task_focus`.
- Visible artifact/Whiteboard follow-up questions, including pronoun-only summarize/explain/key-points phrasing, stay in chat and force chat mode even if an upstream route suggested draft mode, while explicit "draft this in the whiteboard" requests still draft.
- Structured Navigator/control-panel close actions return a validated surface action for Whiteboard/artifact and Today/calendar surfaces, close actions without a visible surface return a safe no-op action, and raw close text without a Navigator action stays chat/no-op.
- Structured Navigator/control-panel preserve actions short-circuit raw calendar/task/whiteboard classification so keep/leave-open turns remain no-op surface preservation.
- Selected/current material questions such as "What should I do first from this study plan?" and "Can you summarize this study plan?" do not draft merely because the noun "study plan" appears.
- Code/implementation requests summon `code_artifact` with whiteboard support.
- Scenario Lab routes are recognized as already handled by the branch/comparison artifact path.

## Why It Matters

These tests lock in the Jarvis-style product rule: when the user asks for a durable object or operational domain, Vantage brings the right application surface into scope automatically instead of asking the user to manually pick a panel first.
