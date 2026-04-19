# `src/vantage_v5/services/response_mode.py`

Shared backend helper for building truthful `response_mode` payloads.

## Purpose

- Keep normal chat and Scenario Lab on the same grounding-mode contract.
- Turn the actual context inputs for a turn into a canonical coarse/fine payload:
  - coarse `kind` such as `grounded` or `best_guess`
  - canonical `grounding_mode` values such as `recall`, `whiteboard`, `recent_chat`, `pending_whiteboard`, or `mixed_context`
  - canonical `recall_count` plus canonical `context_sources` / `grounding_sources`, with `working_memory_count`, `legacy_grounding_mode`, and legacy source lists kept as compatibility aliases for older `working_memory` clients

## Key Function

- `build_response_mode_payload()`

## Notable Behavior

- Uses `Best Guess` only when there is no grounded context at all.
- Distinguishes recalled `Recall` context from whiteboard-only, recent-chat-only, prior-whiteboard, and mixed-context grounding.
- Emits product-facing labels and notes such as `Recall`, `Prior Whiteboard`, `Recall + Recent Chat`, and `No grounded context supported this answer.` while preserving legacy grounding/source aliases for `working_memory`-shaped clients.
- `finalize_assistant_message()` only adds the visible best-guess preface for ordinary ungrounded chat; whiteboard offer/draft replies suppress that preface so a deliberate collaboration flow does not read like a guess.
- Lets Scenario Lab reuse the same truthful response-mode semantics as normal chat instead of maintaining a second coarser contract.
