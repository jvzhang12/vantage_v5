# `src/vantage_v5/services/record_cards.py`

Presentation boundary for UI-facing record cards.

## Purpose

- Keep `server.py`, Chat, and Scenario Lab from owning duplicated record-card serialization rules.
- Preserve stable payload shapes for concepts, protocols, memories, artifacts, vault notes, lineage fields, scenario metadata, and grouped memory responses.
- Keep lifecycle-specific artifact fields delegated to `draft_artifact_lifecycle.py` while centralizing the broader card DTO shape here.

## Key Functions

- `lineage_payload()`: returns the thin UI lineage view over raw `comes_from`, including `derived_from_id`, `revision_parent_id`, and `lineage_kind`.
- `serialize_concept_card()`: serializes concept records, including protocol metadata when the concept type is `protocol`.
- `serialize_built_in_protocol_card()`: serializes built-in protocol definitions using the same protocol card shape as persisted protocol records.
- `serialize_saved_note_card()`: serializes memory and artifact records, including artifact lifecycle fields and Scenario Lab scenario metadata for artifacts.
- `serialize_vault_note_card()`: serializes read-only vault/reference notes.
- `memory_payload()`: groups saved and reference notes with count metadata for `/api/memory`-style responses.
- `scenario_payload()` and `saved_record_scenario_metadata()`: normalize the nested Scenario Lab metadata visible on saved artifact cards and workspace payloads.

## Notable Behavior

- Artifact lifecycle enrichment is intentionally delegated to `artifact_lifecycle_card_fields()` so the lifecycle module remains the owner of `artifact_origin` / `artifact_lifecycle` card semantics.
- Scenario metadata is cleaned before exposure so empty strings, empty lists, and empty nested objects do not leak into UI cards.
- Protocol cards expose `kind="protocol"`, `memory_role="protocol"`, and a nested `protocol` object while keeping the same base concept-card shape. The nested object now distinguishes built-in, canonical, built-in-override, and canonical-override protocol states for Inspect.
- Canonical/default records receive Vantage-default source labels while user and experiment records keep their existing saved/experiment labels.
- This module is a presentation layer only; it does not mutate storage or decide whether records should be recalled, saved, reopened, or promoted.
