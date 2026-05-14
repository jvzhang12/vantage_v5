# `src/vantage_v5/webapp_react/src/normalizers.ts`

React TypeScript DTO normalizers.

## Purpose

- Convert existing backend snake_case and legacy aliases into stable React-facing objects.
- Preserve API compatibility while the frontend migrates away from vanilla `.mjs` helpers.

## Coverage

- Turn payloads, answer basis, response mode, recall/learned items, surface invocation, surface payloads, source refs, workspace updates, context budget, activity, semantic policy/frame, visible artifacts, and write/action records.
- Maps legacy `Best Guess` labels to the product-facing `Intuitive Answer` label.
