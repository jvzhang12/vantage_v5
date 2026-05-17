# `tests/test_attention.py`

Unit tests for the Attention + Navigator selection service.

## Purpose

- Lock in query-frame parsing, deterministic resource indexing, ranking, selection fallback, and explicit Navigator surface selection behavior.
- Prove that temporal phrases such as "last Tuesday" can retrieve the right work product.
- Prove that visible artifacts take priority as the user's current working view.

## Coverage

- `QueryFrame` parsing for reopen intent, whiteboard domain, temporal references, and worked-on relations.
- Ranking of saved artifacts by temporal metadata.
- Explicit `scope`, `durability`, and `is_canonical` metadata on attention candidates and selected attention resources.
- Priority of visible calendar/task artifacts over older saved context.
- Regression coverage for polluted study-plan artifacts, where broad material lookup should choose the full `Midterm Study Plan` over derivative first-action snapshots but explicit first-action queries preserve the derivative primary.
- Navigator-selection normalization accepts both resource ids and compact candidate ids, prefers the source artifact over a same-title opened Whiteboard copy only for saved/open-material lookup turns, and preserves explicit opened-copy selections outside those lookup turns.
- Operational indexing for calendar day/week and task focus resources.
- Deterministic Attention fallback selects high-signal resources when the model is unavailable without treating `suggested_surface` metadata as a UI-open directive.
- Surface-selection regression coverage where only explicit Navigator `surface_to_open` opens a surface; saved/open-material lookup phrases can still prefer the source artifact as selected context, but the UI-open intent is now supplied by Navigator/control-panel fallback rather than Attention.
- Hard surface intents such as chat-only and close-visible-surface are not overwritten by explicit Navigator-selected attention surfaces.
