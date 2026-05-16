# `tests/test_attention.py`

Unit tests for the Attention + Navigator selection service.

## Purpose

- Lock in query-frame parsing, deterministic resource indexing, ranking, selection fallback, and surface selection behavior.
- Prove that temporal phrases such as "last Tuesday" can retrieve the right work product.
- Prove that visible artifacts take priority as the user's current working view.

## Coverage

- `QueryFrame` parsing for reopen intent, whiteboard domain, temporal references, and worked-on relations.
- Ranking of saved artifacts by temporal metadata.
- Explicit `scope`, `durability`, and `is_canonical` metadata on attention candidates and selected attention resources.
- Priority of visible calendar/task artifacts over older saved context.
- Regression coverage for polluted study-plan artifacts, where broad material lookup should choose the full `Midterm Study Plan` over derivative first-action snapshots but explicit first-action queries can still choose the derivative.
- Navigator-selection normalization accepts both resource ids and compact candidate ids, and prefers the source artifact over a same-title opened Whiteboard copy when both are selected.
- Operational indexing for calendar day/week and task focus resources.
- Deterministic Navigator fallback that opens the appropriate surface when the model is unavailable.
- Surface-selection regression coverage where an already-visible Today resource can be selected first while a saved artifact selected second still produces a Whiteboard `open_only` directive.
