# Stale Code Inventory

> Status: Current source of truth
> Note: This guide inventories code that may be active-but-transitional, compatibility-retained, fallback-only, unclear, or ready for future retirement review. It is not deletion authorization and does not change runtime behavior. For public aliases and retained compatibility fields, see [compatibility-ledger.md](compatibility-ledger.md). For test role classification, see [test-taxonomy.md](test-taxonomy.md). For runtime files, generated assets, local worktrees, and untracked docs, see [stale-artifact-inventory.md](stale-artifact-inventory.md).

Date: 2026-05-21

## Executive Summary

The current quick reference/search pass did not prove that any tracked source module is cleanly dead. Most entropy is not abandoned code; it is active compatibility code, transitional seams, fallback/safety code, and tests that intentionally preserve old behavior while Vantage is moving toward cleaner Attention/Recall, TurnPlan, React, and Working Memory contracts.

The highest-value cleanup is therefore:

1. Label each compatibility or fallback path by role.
2. Identify its consumers and tests.
3. Define the condition under which it can be retired.
4. Remove or archive it only in small reviewed slices with behavior-preservation proof.

Code searches should exclude reproducible build output such as `src/vantage_v5/webapp/generated/**`; generated bundles are not source truth.

## Classification Legend

| Classification | Meaning | Deletion posture |
|---|---|---|
| Current product path | Active implementation of current product behavior. | Do not retire. |
| Compatibility-retained | Older public field, storage name, request alias, or behavior kept for clients/tests/data. | Retire only after consumer review and migration. |
| Transitional architecture seam | Active bridge between old and new architecture. | Retire after the target architecture owns the behavior and parity evidence is no longer needed. |
| Fallback/safety guardrail | Deterministic or local path that handles provider failure, malformed model output, validation, or conservative repair. | Keep narrow, labeled, and observable; retire only after structured model/control-plane paths are proven. |
| Dormant or unclear capability | Code appears reachable, but its current product role is weak or not recently exercised. | Mark for owner review before changing. |
| Test-only compatibility contract | Test preserves old payload or fallback behavior rather than primary product behavior. | Taxonomize before deleting or rewriting. |
| Already retired/deleted | Previously stale source removed from the active tree. | Do not resurrect unless explicitly planned. |

## Confirmed Active Core

These areas were checked because they can look stale from names alone. They should not be treated as dead code.

| Area | Classification | Evidence | Notes |
|---|---|---|---|
| React frontend under `src/vantage_v5/webapp_react/` | Current product path | FastAPI serves the generated React build; legacy static fallback was removed. | Do not recreate old `src/vantage_v5/webapp/*.mjs` helpers. |
| `src/vantage_v5/services/turn_plan.py` | Current product path plus compatibility projection | TurnPlan authority gates writes, draft authority, proposals, and public compatibility annotations. | Large file, but not stale; consolidation can continue only through behavior-preserving slices. |
| `src/vantage_v5/services/turn_orchestrator.py` | Current product path | Coordinates chat turns, Navigator, TurnPlan execution policy, ChatService, local actions, Scenario Lab, and final payloads. | Central flow, not deletion candidate. |
| `src/vantage_v5/services/public_context_projection.py` | Current product path | Centralizes public-safe Memory Trace and prompt-derived ID projection. | New safety layer; keep it as the shared projection point rather than scattering sanitizers. |
| `src/vantage_v5/services/context_handoff.py` | Transitional architecture seam | Builds Attention/Recall handoff and adapts recalled context into generation candidates. | Active bridge while `ChatService.search_context()` still owns retrieval/vetting. |
| `src/vantage_v5/services/context_budget.py` | Current product path | Referenced by payload shaping, normalizers, and tests. | Name may sound auxiliary, but it is part of bounded public context behavior. |
| `src/vantage_v5/services/visible_artifacts.py` | Current product path | Referenced by context engine, Navigator, meta decisions, and tests. | Needed for visible-surface scope discipline. |
| `src/vantage_v5/services/executor.py` | Current product path | Executes approved graph actions and is used by ChatService, protocol/draft flows, server, and tests. | Some action variants need review, but the module is active. |
| `src/vantage_v5/services/scenario_lab.py` | Current product path | Navigator can route Scenario Lab turns; tests and payloads preserve branch/comparison behavior. | Contains legacy lineage compatibility, but Scenario Lab itself is not stale. |

## Retirement And Archiving Candidates

These are the main code entropy candidates. "Candidate" here means "needs an explicit retirement condition," not "safe to delete now."

| Candidate | Classification | Evidence | Why it exists | Risk if removed now | Retirement condition | Suggested slice | Priority |
|---|---|---|---|---|---|---|---|
| `legacy_*` fields in `src/vantage_v5/services/response_mode.py` | Compatibility-retained | `legacy_grounding_mode`, `legacy_context_sources`, and related tests. | Keeps older grounding/Working Memory payload consumers working while canonical response-mode fields settle. | Public payload regression and UI/test breakage. | React and any external clients consume only canonical `response_mode` fields; tests are reclassified and migrated. | Response-mode compatibility retirement audit. | P1 |
| Top-level `working_memory`, `created_record`, selected-record aliases, and `workspace_update.type` in `turn_payloads.py` | Compatibility-retained | Compatibility ledger and many server/turn-payload tests. | Maintains old public response shape while current concepts are `working_memory_view`, `learned`, pinned context, and Whiteboard lifecycle metadata. | Public `/api/chat` shape break; possible hidden client breakage. | Explicit API migration or proof that only canonical fields are consumed. | Public payload alias inventory and removal-condition review. | P1 |
| `ChatService.search_context()` in `chat.py` and `search.py` | Transitional architecture seam | Chat still uses bounded retrieval/vetting; handoff generation consumes adapted recall; parity traces compare both paths. | Preserves behavior while Attention/Recall handoff becomes the generation context model. | Retrieval/generation regressions; loss of parity diagnostics. | Attention/Recall owns retrieval/vetting or search becomes a private helper behind the handoff. | Attention/Recall retrieval ownership cutover plan. | P1 |
| `legacy_vetted_memory` adapter and parity fields in `context_handoff.py` / `chat.py` | Transitional architecture seam | `legacy_vetted_memory_ids`, omitted legacy ids, generation parity diagnostics. | Proves handoff generation matches legacy search/vetting before deleting old pathways. | Silent context loss during generation cutover. | Parity is stable across smokes and tests, and legacy ids are no longer needed for diagnostics. | Handoff parity retirement slice. | P1 |
| Deterministic Navigator/control-panel fallback in `navigator.py` and `turn_orchestrator.py` | Fallback/safety guardrail | `apply_control_panel_open_intent_fallback`, fallback decisions, tests in `test_navigator.py`. | Keeps routing conservative when model output is unavailable/invalid and handles narrow open/preserve/remember repair. | Loss of safe provider-failure behavior or reintroduction of broad raw-text routing if replaced poorly. | Structured Navigator/control-plane outputs cover the cases reliably; fallback remains only provider-failure/no-op or is removed with smoke proof. | Navigator fallback taxonomy and narrowing. | P1 |
| Deterministic Attention selection fallback in `attention.py` | Fallback/safety guardrail | Fallback selected highest-signal candidates when Navigator selection is absent/invalid; tested in `test_attention.py`. | Prevents empty or unstable Attention output from breaking the turn. | Working Memory context gaps and worse recovery when model selection fails. | Navigator/Attention selection has reliable structured outputs and fallback is no longer hit in expected smokes. | Attention fallback observability and retirement criteria. | P2 |
| Deterministic artifact mutation compiler fallback and due-date repair in `artifact_mutation_compiler.py` / `artifact_actions.py` | Fallback/safety guardrail | `compiler.source="deterministic_fallback"`, raw-message fallback, due-date repair tests. | Repairs narrow proposal cases while keeping calendar/task mutation confirmation-gated. | Calendar/task proposal regressions, especially around explicit phrasing and timezone/date handling. | Model-normalized structured actions reliably include required fields; fallback hit rate and source labels prove it is not primary routing. | Proposal compiler fallback reduction. | P1 |
| Chat provider fallback drafts/offers in `chat.py` | Fallback/safety guardrail | `_fallback_reply`, `_fallback_workspace_draft`, `_fallback_email_draft`, `_fallback_essay_draft`. | Keeps the app responsive when no model provider is available and supports local dev/test. | Offline/dev behavior and draft authority tests may fail; fallback could also create overconfident product behavior if narrowed incorrectly. | Decide whether local fallback should remain a supported offline mode or become test-only. | Provider-fallback product policy review. | P2 |
| `meta.py` semantic write decision path and `_fallback_decide` | Transitional architecture seam | ChatService still calls meta decisions for graph actions; TurnPlan gates final authority. | Older semantic write interpreter remains part of the write path beneath TurnPlan authority. | Memory/concept/artifact write regressions and loss of conservative fallback behavior. | TurnPlan/control-plane structured write intent fully replaces local/meta decisioning, or meta is reduced to formatting/persistence prep. | Meta write interpreter consolidation. | P1 |
| `semantic_frame.py`, `semantic_policy.py`, and `local_semantic_actions.py` | Transitional architecture seam | Used by orchestrator/local actions and tests to suppress or allow local semantic side effects. | Read-model/policy layer from earlier TurnPlan migration. | Regressions in hard no-write, draft denial, or local semantic write blocking. | TurnPlan execution policy owns the relevant checks with equivalent tests. | Semantic policy consolidation into TurnPlanExecutionPolicy. | P2 |
| `create_revision` action path across `meta.py`, `executor.py`, `turn_plan.py`, and stores | Dormant or unclear capability | Present in allowed action sets and storage APIs; less visible in current product flows. | Supports concept revision lineage. | May break concept revision if still desired; unclear current UX. | Product owner decides whether concept revision is current, hidden, or retired; tests/smokes cover chosen path. | Concept revision role review. | P2 |
| Legacy Scenario Lab comparison recovery in `storage/artifacts.py` | Compatibility-retained | `_looks_like_legacy_comparison_artifact` and recovery from `comes_from`; covered by server tests. | Lets old comparison artifacts behave as Scenario Lab comparison hubs. | Old saved comparisons lose metadata/continuity. | Old artifacts are migrated once, or compatibility support is explicitly declared no longer needed. | Scenario Lab lineage migration/retirement review. | P2 |
| `record_cards.py` lineage heuristics for revision/provenance | Compatibility-retained | Infers revision parent from `comes_from` and `--vN` ids. | Bridges older record lineage into newer write-review/card payloads. | Saved-review UI may lose useful lineage context. | Stable canonical lineage metadata exists for all created records. | Record lineage schema cleanup. | P3 |
| CamelCase request parsing aliases in `server.py` | Compatibility-retained | Compatibility ledger notes JS-style request keys. | Supports React/external callers that send camelCase. | Request-shape regressions. | Versioned API or confirmed clients use snake_case only. | Request alias retirement review. | P3 |
| Local static generated asset handling in server tests | Current product path, not stale | Generated React serving contract and missing-build 503 tests. | Ensures old static fallback does not return. | Removing it could reintroduce frontend deployment regressions. | None; keep as current deployment contract. | No cleanup beyond docs. | P3 |

## Tests Preserving Old Or Transitional Behavior

| Test area | Classification | Evidence | Role | Suggested action |
|---|---|---|---|---|
| `tests/test_turn_payloads.py` compatibility cases | Test-only compatibility contract | `working_memory`, `created_record`, `workspace_update`, selected-record assertions. | Protects public payload aliases. | Add comments or names that distinguish canonical product behavior from compatibility aliases before any retirement. |
| `tests/test_server.py` response-shape and fallback sections | Test-only compatibility contract plus product contracts | Large set of `legacy_*`, `fallback`, Scenario Lab lineage, pending Whiteboard, and selected-record cases. | Mixed current behavior and compatibility preservation. | Introduce a test taxonomy or section labels: product contract, compatibility alias, fallback/safety, historical regression. |
| `tests/test_response_mode.py` legacy best-guess preface stripping | Compatibility-retained | Tests old preface normalization. | Defensive cleanup for old model/output shapes. | Keep until old responses cannot occur, then retire or reduce to a single sanitizer test. |
| `tests/test_artifact_actions.py` deterministic compiler fallback cases | Fallback/safety guardrail | Explicit raw-message fallback and due-date repair tests. | Ensures fallback is labeled and narrow. | Keep while fallback exists; add hit-rate/trace review before narrowing. |
| `tests/test_attention.py` fallback/legacy surface selection cases | Fallback/safety guardrail | Attention fallback and legacy surface override tests. | Protects conservative context selection. | Keep until structured Attention/Navigator selection proves equivalent. |
| `tests/test_navigator.py` control-panel fallback cases | Fallback/safety guardrail | Tests fallback open/remember/preserve behavior. | Protects provider-failure and invalid-response behavior. | Rename/label as fallback-specific if future Navigator output becomes primary. |
| Scenario Lab legacy lineage tests in `tests/test_server.py` | Compatibility-retained | Legacy comparison artifact recovery and selected-record payload preservation. | Protects old saved comparison artifacts. | Tie to a migration decision for old Scenario Lab artifacts. |

## Test Evidence Crosswalk

Use [test-taxonomy.md](test-taxonomy.md) for the reviewer-facing classification. This crosswalk ties each major stale-code or compatibility candidate above to concrete test evidence.

| Candidate | Test evidence | Test classification | Retirement signal |
|---|---|---|---|
| `legacy_*` fields in `response_mode.py` | `tests/test_response_mode.py`, response-mode sections in `tests/test_turn_payloads.py` and `tests/test_server.py` | Compatibility alias / historical regression | Canonical `response_mode` fields fully replace legacy fields and visible preface sanitizer is no longer needed beyond one regression. |
| Top-level `working_memory`, `created_record`, selected-record aliases, `workspace_update.type` | `tests/test_turn_payloads.py`, compatibility sections in `tests/test_server.py`, React `appReducer.test.ts`/normalizer-adjacent state tests | Compatibility alias / old payload contract | React and external clients consume only `working_memory_view`, `learned`, pinned-context fields, and canonical Whiteboard status/lifecycle metadata. |
| `ChatService.search_context()` | `tests/test_search.py`, `tests/test_context_handoff.py`, handoff/generation sections in `tests/test_server.py` | Transitional architecture seam | Attention/Recall handoff owns retrieval/generation context without legacy parity diagnostics. |
| Legacy handoff parity fields | `tests/test_context_handoff.py`, generation parity sections in `tests/test_server.py` | Transitional architecture seam | Parity is stable across smokes and legacy search ids are no longer needed for diagnostics. |
| Navigator/control-panel fallback | `tests/test_navigator.py`, surface/open/preserve server sections | Fallback / safety guardrail | Structured Navigator output reliably supplies actions; fallback traces show only provider-failure use. |
| Attention deterministic fallback and surface guards | `tests/test_attention.py`, selected attention server regressions | Fallback / safety guardrail | Structured Attention/Navigator selection covers resource selection and open intent without fallback hits. |
| Artifact mutation compiler fallback | `tests/test_artifact_actions.py`, calendar/task server proposal tests | Fallback / safety guardrail | Model-normalized actions reliably preserve required titles, dates, statuses, and confirmation gates. |
| Chat provider fallback drafts/offers | Provider-failure sections in `tests/test_server.py`, whiteboard accept fallback tests | Fallback / safety guardrail | Product decision says provider failure should error instead of draft locally, or fallback remains explicitly dev/offline-only. |
| Meta write interpreter and `_fallback_decide` | Meta/concept/revision sections in `tests/test_server.py`, TurnPlan write-authority tests | Transitional architecture seam / unclear owner review | TurnPlan/control-panel structured write intent fully owns semantic write authority. |
| `semantic_frame.py`, `semantic_policy.py`, `local_semantic_actions.py` | Semantic policy sections in `tests/test_server.py`, TurnPlan no-write/write-projection tests | Transitional architecture seam | TurnPlan execution policy owns local save/publish/experiment/write decisions with equivalent receipts. |
| `create_revision` path | Concept revision tests in `tests/test_server.py`, concept-write authority tests in `tests/test_turn_plan.py` | Unclear / needs owner review | Product owner decides revision is current hidden capability, future UX, or retired code. |
| Legacy Scenario Lab comparison recovery | Scenario Lab lineage tests in `tests/test_server.py`, lifecycle/card enrichment tests | Compatibility alias / historical regression | Old comparison artifacts are migrated or declared unsupported. |
| Record-card lineage heuristics | `tests/test_record_cards.py`, lifecycle/card enrichment tests, server saved-item/open tests | Compatibility alias / historical regression | Canonical lineage metadata exists for new and migrated records. |
| CamelCase request aliases | CamelCase workspace payload case in `tests/test_server.py`, React request-shaping tests | Compatibility alias / old request contract | Versioned API or confirmed clients use snake_case only. |
| Generated React serving tests | Static/PWA/server tests and `src/vantage_v5/webapp_react/src/entrypoints.test.ts` | Current product contract / historical regression guard | Keep while React/generated is the serving contract; only consolidate duplicate assertions. |

## Already Retired Or Not Source

| Path / area | Classification | Current state | Note |
|---|---|---|---|
| `src/vantage_v5/webapp/index.html`, `app.js`, `styles.css`, legacy `.mjs` helpers, and vendor files | Already retired/deleted | Removed from tracked source. | Do not restore a legacy static fallback; React/generated is the product frontend path. |
| Legacy Node tests for removed static helpers | Already retired/deleted | Removed with the legacy modules. | Active frontend behavior is covered by React/Vitest and server route tests. |
| `src/vantage_v5/webapp/generated/**` | Generated output, not source | Ignored build output produced by `npm run build`. | Exclude it from stale-code searches. |
| `.venv/`, `node_modules/`, `.pytest_cache/`, `build/`, `tmp/`, `eval_runs/` | Local tooling output | Ignored or local state. | Covered by [stale-artifact-inventory.md](stale-artifact-inventory.md). |

## Search Hygiene

Useful read-only searches:

```bash
rg -n "legacy_|compatibility|fallback|transitional|deprecated|retire|unused|TODO|FIXME" src/vantage_v5 tests -g '!src/vantage_v5/webapp/generated/**'
rg -n "working_memory|workspace_update|created_record|selected_record|legacy_" src/vantage_v5 tests docs -g '!src/vantage_v5/webapp/generated/**'
rg -n "search_context\\(|create_revision|_fallback|_looks_like_legacy" src/vantage_v5 tests -g '!src/vantage_v5/webapp/generated/**'
```

Do not treat a low import count as deletion proof. Vantage uses FastAPI route registration, pytest fixtures, store/runtime construction, and public payload contracts that can make code reachable without obvious static references. Confirm candidate removals with tests, API/browser smokes when behavior-facing, and review of the compatibility ledger.

## Recommended Cleanup Slices

1. **Response-mode compatibility narrowing**: use [test-taxonomy.md](test-taxonomy.md) to reduce duplicate legacy preface regressions and review `legacy_*` response-mode fields.
2. **Public payload alias consumer review**: list consumers and removal conditions for `working_memory`, `created_record`, `workspace_update.type`, selected-record aliases, and camelCase request aliases.
3. **Fallback hit observability**: make sure every deterministic fallback that can affect a response has an explicit trace/source field and is easy to smoke for.
4. **Attention/Recall retrieval ownership plan**: decide when `ChatService.search_context()` becomes private, diagnostic-only, or retired.
5. **Meta/semantic policy consolidation**: review whether `meta.py`, `semantic_policy.py`, and local semantic actions can shrink now that TurnPlan execution policy exists.
6. **Scenario Lab legacy lineage migration**: decide whether to migrate old comparison artifacts and remove `_looks_like_legacy_comparison_artifact` recovery later.
7. **Concept revision role review**: decide whether `create_revision` is a current hidden capability, a future UX, or stale code to archive.
8. **Provider fallback product policy**: decide whether local fallback draft generation is a supported offline behavior or test/dev-only scaffolding.

## Open Questions

- Which compatibility aliases have consumers outside the React app and tests?
- Should deterministic fallbacks be measured in traces before any narrowing attempt?
- Is concept revision part of the current product model, or should it be archived until a clear UX exists?
- Should Scenario Lab old comparison artifacts be migrated into canonical metadata once, then drop legacy recovery?
- Is `ChatService.search_context()` the permanent retrieval/vetting implementation behind Attention/Recall, or a transitional path to retire?
- Should codebase summaries explicitly mark compatibility/fallback modules so fresh agents do not mistake them for dead code?
