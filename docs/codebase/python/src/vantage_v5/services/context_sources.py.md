# `src/vantage_v5/services/context_sources.py`

Context-source resolver for pinned context, whiteboard provenance summaries, and Navigator continuity context.

## Purpose

- Keep saved-record, vault-note, Memory Trace, and recent-whiteboard summary assembly out of `server.py`.
- Provide the app-specific lookup callbacks that `ContextEngineHooks` needs through one deeper collaborator.
- Build compact, metadata-first summaries for the Navigator without exposing hidden whiteboard body content.

## Key Classes

- `ContextSourceResolver`: resolves `pinned_context_summary`, `whiteboard_source_summary`, and `navigator_continuity_context` from the active runtime, durable stores, and vault store.

## Notable Behavior

- Looks in active runtime stores first, then ordered reference stores, which can include durable user records plus lower-priority canonical defaults.
- Labels saved-record summaries through `product_scope.py`, using configured canonical root and active experiment root containment so similarly named user/profile path segments do not affect scope.
- Falls back to vault-note summaries for pinned reference notes, marking them as read-only reference scope.
- Whiteboard source summaries now include additive source provenance fields (`source_scope`, `source_durability`, `source_is_canonical`, and nested `source_provenance`) so continuity/debug traces can explain when the current editable whiteboard originated from canonical or reference material.
- Reconstructs a short continuity frame from the latest Memory Trace, unique reopenable recalled records, the current whiteboard, and up to three recent whiteboards.
- Marks protocol records as non-reopenable in whiteboard continuity, because protocols are instructional guidance objects rather than work products to draft from.
- Preserves Scenario Lab comparison metadata through the shared `record_cards.py` helpers.
