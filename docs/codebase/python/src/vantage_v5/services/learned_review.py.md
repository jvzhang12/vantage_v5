# `src/vantage_v5/services/learned_review.py`

Shared backend helper for read-only review metadata on records saved by a turn.

## Purpose

- Keep normal chat, Scenario Lab, local semantic actions, and saved-note card serializers on the same `write_review` DTO.
- Preserve the existing `learned`, `created_record`, `why_learned`, `scope`, `durability`, and `correction_affordance` compatibility fields while giving the UI one canonical review object to read.
- Make Saved for Later inspectable without adding direct mutation APIs before storage, search, trace, experiment, and privacy semantics are defined.

## Key Functions

- `build_write_review()`: builds the additive review DTO for a saved record, including reason, scope, durability, record identity, allowed review actions, and unsupported direct-mutation metadata.
- `ensure_write_review()`: mutates an already-built record payload in place only when it is missing `write_review`.

## Notable Behavior

- The review model is intentionally read-only. It exposes actions such as opening or revising in the whiteboard and pinning for the next turn, but it marks direct mutation as unsupported.
- `write_review` does not replace the public `learned` field; it sits inside learned/saved records as a more explicit receipt for what was saved and how the user can review it.
- Experiment-scoped records get temporary durability through the same DTO, so UI copy can distinguish session-local saved outcomes from durable Library writes.
