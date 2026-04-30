# `src/vantage_v5/services/corrections.py`

Applies narrow saved-item negative corrections for concepts, memories, and artifacts.

## Purpose

- Validate correction source, action, and scope.
- Suppress saved items without deleting files.
- Update writable durable or experiment records in place.
- Write same-id tombstones into a writable user or experiment layer when hiding lower-priority records.
- Keep canonical records and built-in/protocol records immutable from this correction path.

## Key Objects

- `SavedItemCorrectionService`: main service for applying a correction against the active durable/runtime stores.
- `CorrectionResult`: normalized response payload for the API route.
- `CorrectionRejected`: typed validation error for unsupported sources, actions, scopes, protocols, and built-ins.

## Notes

- Supported actions are `mark_incorrect` and `forget`; both produce `status: suppressed`.
- Supported sources are `concept`, `memory`, and `artifact`.
- Supported scopes are `current`, `durable`, and `experiment`.
- Canonical items are hidden by same-id tombstones with `suppresses_canonical: true`; canonical files are never modified.
- The response includes `effect: suppressed`, `visibility: hidden`, and `hard_deleted: false` so clients do not mistake the correction for deletion, freshness scoring, or confidence scoring.
