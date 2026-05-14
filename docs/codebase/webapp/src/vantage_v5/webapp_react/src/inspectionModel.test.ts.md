# `src/vantage_v5/webapp_react/src/inspectionModel.test.ts`

Vitest coverage for the Vantage inspection adapter.

## Purpose

- Verify that latest-turn provenance becomes the expected “Why this answer?” receipt.
- Guard against showing excluded context as used context.

## Coverage

- Calendar/task Today Briefing receipt mapping.
- Summary columns, opened surface decisions, canonical decision path labels, and read-only/no-write audit state.
- Current-request-only fallback when no backend provenance selected additional context.
