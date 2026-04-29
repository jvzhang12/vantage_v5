# `tests/test_record_cards.py`

Focused unit tests for the record-card presentation boundary.

## Purpose

- Verify UI-facing record card serialization independently from the HTTP server routes.
- Lock down compatibility for artifact lifecycle fields, Scenario Lab metadata, protocol cards, saved-note grouping, and scenario metadata cleanup.

## Coverage

- Saved artifact cards preserve `artifact_origin`, `artifact_lifecycle`, `scenario_kind`, nested `scenario`, and lineage fields.
- Persisted protocol cards expose protocol metadata, variables, scope, built-in/canonical state, and override state.
- Built-in protocol cards and grouped memory payloads keep their existing API shapes.
- Memory cards do not accidentally receive artifact-only lifecycle fields.
- Scenario payload cleanup removes empty nested values while preserving useful comparison metadata.
