# `src/vantage_v5/storage/overlay.py`

Read-through overlay helpers for combining higher-priority user/session records with lower-priority canonical defaults.

## Purpose

- Preserve a stable precedence rule: experiment records override durable user records, and durable user records override canonical defaults.
- Let canonical concepts, protocols, memories, and artifacts be visible to every profile without copying those files into each user's private store.
- Allow personal overrides to use the same record id as a canonical default while hiding the lower-priority default from merged lists.
- Provide a simple suppression hook through hidden/suppressed records for future "hide this default" behavior.

## Key Objects

- `overlay_records()`: first-wins merge over record lists keyed by `(source, id)`, skipping suppression records.
- `ConceptOverlayStore`: read-only facade exposing `list_concepts()` and `get()` across ordered concept stores.
- `MemoryOverlayStore`: read-only facade exposing `list_memories()` and `get()` across ordered memory stores.
- `ArtifactOverlayStore`: read-only facade exposing `list_artifacts()` and `get()` across ordered artifact stores.

## Notes

- Overlay stores intentionally do not write. All user changes should go through the active writable store so canonical files remain immutable shipped defaults.
