# `src/vantage_v5/services/product_scope.py`

Shared helpers for turning backend record locations into product-facing scope metadata.

## Purpose

- Produce compact `scope`, `durability`, and `is_canonical` values for search, recall, attention, and selected-record payloads.
- Keep canonical and experiment detection rooted in explicit path containment rather than folder-name or profile-name string guesses.
- Provide small helpers for virtual product scopes such as built-in protocols, live operational resources, and visible transient UI artifacts.

## Key Functions / Classes

- `ProductScope`: immutable DTO with `to_payload()` for API-facing metadata.
- `product_scope_for_record()`: classifies Markdown records and vault notes using optional canonical/experiment roots plus a conservative fallback scope.
- `builtin_product_scope()`, `operational_product_scope()`, and `transient_product_scope()`: produce scope metadata for non-file-backed candidates.

## Notable Behavior

- Vault notes are `reference` / `read_only`.
- Experiment records are `experiment` / `temporary`.
- Canonical records are `canonical` / `durable` with `is_canonical=true`.
- Memory Trace records can expose their stored `trace_scope` even when a root is not available.
