# `src/vantage_v5/services/surface_invocation.py`

Deterministic policy layer for deciding which Vantage surface should be summoned for a chat turn.

## Purpose

- Reframe Vantage around automatic context/application invocation instead of optional panels.
- Classify turns into surface intents such as `durable_artifact`, `schedule_lookup`, `schedule_planning`, `task_focus`, `code_artifact`, or `chat_only`.
- Return a public `surface_invocation` payload with the primary surface, supporting surfaces, write behavior, confidence, and product-facing reason.
- Override old timid whiteboard routing for durable work products so emails, essays, plans, code, outlines, proposals, and similar outputs draft directly into the whiteboard unless the user explicitly asks for chat-only or offer mode.

## Key Classes / Functions

- `InvokedSurface`: one selected surface with `kind`, `role`, `reason`, and `status`.
- `SurfaceInvocation`: the full policy result, including `intent`, `primary_surface`, `supporting_surfaces`, `write_behavior`, `reason`, `confidence`, optional `whiteboard_mode`, and helper `resolved_whiteboard_mode()`.
- `build_surface_invocation()`: deterministic classifier used by `TurnOrchestrator` after Navigator interpretation and before chat/Scenario Lab execution.

## Surface Rules

- Chat-only requests stay in chat when the user explicitly asks for that.
- Visible artifact/Whiteboard follow-up questions about the current item, including pronoun-only summarize/explain/key-points prompts, stay in chat and keep the current view unless the user explicitly asks to draft, edit, write, create, save, open a whiteboard, or publish.
- Current-material questions that mention an item such as `this study plan` stay chat-first even when the item is selected but not yet visible; the noun `study plan` alone no longer implies a draft.
- Schedule lookup requests summon `calendar_day`.
- Schedule planning requests summon `calendar_day` with `task_focus` and `whiteboard` support.
- Task/deadline/focus requests summon `task_focus`.
- Code implementation requests summon `code_artifact` with `whiteboard` support.
- Durable work-product requests summon `whiteboard` and request direct `draft` mode only when explicit draft/write/create-style language is present.

## Notable Behavior

- The policy does not fetch calendar/task data yet; it produces the contract the UI and future providers can render from.
- Explicit composer modes still win: `chat`, `offer`, and `draft` are respected.
- Scenario Lab remains the owner for branch/comparison artifacts, so the surface policy marks that path as handled elsewhere.
