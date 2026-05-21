# `src/vantage_v5/webapp_react/src/normalizers.ts`

React TypeScript DTO normalizers.

## Purpose

- Convert existing backend snake_case and legacy aliases into stable React-facing objects.
- Preserve API compatibility in the React-only frontend while normalizing older payload aliases that originated before the vanilla helper modules were retired.

## Coverage

- Turn payloads, answer basis, response mode, recall/learned items, surface invocation, close/hide surface actions, surface payloads, source refs, workspace updates, context budget, activity, semantic policy/frame, visible artifacts, write/action records, and the bounded `working_memory_view` contract.
- Working Memory normalization accepts snake_case/camelCase aliases, keeps compact role/resource/provenance/execution fields, and intentionally ignores full resource `content`/`body` fields so the Vantage UI remains product-safe.
- Maps legacy `Best Guess` labels to the product-facing `Intuitive Answer` label.
