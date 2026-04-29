# `tests/test_whiteboard_routing.py`

Focused unit tests for the deep whiteboard routing service.

## Purpose

- Verify `WhiteboardRoutingEngine` independently from `/api/chat`, server bootstrap wiring, and full turn orchestration.
- Lock down the existing whiteboard routing precedence while the routing rules move behind a service boundary.
- Keep coverage narrow to whiteboard-specific heuristics rather than introducing broad deterministic intent classification.

## Coverage

- Requested `offer` and `draft` modes are preserved.
- Requested `chat` wins even when the message explicitly asks for whiteboard drafting.
- Explicit whiteboard draft/open requests upgrade Navigator chat decisions to `draft`.
- Current whiteboard edit/revision requests upgrade Navigator chat decisions to `draft` when workspace content exists.
- Navigator `whiteboard_mode` values `chat`, `offer`, `draft`, and `auto` are honored when no deterministic override applies.
- Unknown or missing Navigator whiteboard modes fall back to `auto`.
- Explicit whiteboard draft phrase detection recognizes direct open/draft requests, including `fresh whiteboard` phrasing, and rejects ordinary mentions.
