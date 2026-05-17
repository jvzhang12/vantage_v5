# `src/vantage_v5/services/surface_invocation.py`

Deterministic policy layer for deciding which Vantage surface should be summoned for a chat turn.

## Purpose

- Reframe Vantage around automatic context/application invocation instead of optional panels.
- Classify turns into surface intents such as `durable_artifact`, `schedule_lookup`, `schedule_planning`, `task_focus`, `code_artifact`, or `chat_only`.
- Return a public `surface_invocation` payload with the primary surface, supporting surfaces, write behavior, confidence, and product-facing reason.
- Return a structured `surface_action` when Navigator/control-panel supplies a validated close-surface action so the UI can hide the visible surface without deleting saved data.
- Treat structured Navigator/control-panel preserve-surface actions as authoritative no-op surface intent before raw text classifiers run.
- Override old timid whiteboard routing for durable work products so emails, essays, plans, code, outlines, proposals, and similar outputs draft directly into the whiteboard unless the user explicitly asks for chat-only or offer mode.

## Key Classes / Functions

- `InvokedSurface`: one selected surface with `kind`, `role`, `reason`, and `status`.
- `SurfaceInvocation`: the full policy result, including `intent`, `primary_surface`, `supporting_surfaces`, `write_behavior`, `reason`, `confidence`, optional `whiteboard_mode`, and helper `resolved_whiteboard_mode()`.
- `SurfaceInvocation` can also carry an additive `surface_action` dictionary for client-applied surface state changes such as closing a visible Whiteboard or calendar surface.
- `build_surface_invocation()`: deterministic classifier used by `TurnOrchestrator` after Navigator interpretation and before chat/Scenario Lab execution.

## Surface Rules

- Chat-only requests stay in chat when the user explicitly asks for that.
- Visible artifact/Whiteboard follow-up questions about the current item, including pronoun-only summarize/explain/key-points prompts, stay in chat and keep the current view unless the user explicitly asks to draft, edit, write, create, save, open a whiteboard, or publish.
- Structured Navigator/control-panel `close_surface` actions over a visible Whiteboard, artifact, Today/calendar, or task surface produce `intent="close_visible_surface"` with `write_behavior="none"` and a `close_visible_surface` action. Raw close/hide/remove wording alone stays chat/no-op unless the Navigator supplied that structured action.
- Structured Navigator/control-panel `preserve_surface` actions produce `intent="preserve_visible_surface"` with `write_behavior="none"`, no `surface_action`, and no downstream calendar/task/whiteboard classification from the same raw text.
- Current-material questions that mention an item such as `this study plan` stay chat-first even when the item is selected but not yet visible; the noun `study plan` alone no longer implies a draft.
- Schedule lookup requests summon `calendar_day`.
- Schedule planning requests summon `calendar_day` with `task_focus` and `whiteboard` support.
- Task/deadline/focus requests summon `task_focus`.
- Code implementation requests summon `code_artifact` with `whiteboard` support.
- Durable work-product requests summon `whiteboard` and request direct `draft` mode only when explicit draft/write/create-style language is present.

## Notable Behavior

- The policy does not fetch calendar/task data yet; it produces the contract the UI and future providers can render from.
- Explicit composer modes still win: `chat`, `offer`, and `draft` are respected.
- Close-surface handling is intentionally validation-only: it maps trusted structured targets such as `whiteboard`, `artifact`, `today`, `calendar`, `task_focus`, or `current` to currently visible surfaces and never deletes saved data.
- Scenario Lab remains the owner for branch/comparison artifacts, so the surface policy marks that path as handled elsewhere.
