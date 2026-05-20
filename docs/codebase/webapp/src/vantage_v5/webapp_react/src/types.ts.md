# `src/vantage_v5/webapp_react/src/types.ts`

Shared TypeScript types for the React frontend.

## Purpose

- Define typed app state, normalized turn payloads, surfaces, auth, account-creation-code status, workspace, receipt/provenance models, and the Working Memory view DTOs.

## Coverage

- Surface kinds, app views, health/workspace payloads, chat history, source refs, surface invocation, additive surface actions, answer basis, response mode, recall items, workspace updates, context budget, activity, semantic frame/policy, write/action payloads, Working Memory role/resource/execution summaries, and reducer state.
- Reducer state now keeps compatibility fields while also naming separate frontend domains for visible surfaces, active whiteboard editor content, selected resource metadata, pinned context, and included request context.
