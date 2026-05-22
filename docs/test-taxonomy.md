# Test Taxonomy And Retirement Plan

> Status: Current source of truth
> Note: This is a docs-only classification of tests and retirement candidates. It does not authorize deleting tests, source code, aliases, fallbacks, storage paths, or behavior.

Date: 2026-05-21

## 1. Executive Summary

The focused test set mostly protects current product behavior, but several files deliberately mix current contracts with compatibility aliases, fallback/safety guardrails, and transitional architecture seams. The safest cleanup path is not immediate deletion. It is to label the tests by role, retire the smallest compatibility assertions only after consumers are reviewed, and keep fallback tests until structured Navigator/TurnPlan/model paths prove they own the same behavior.

Highest-signal map:

- `tests/test_turn_plan.py`, `tests/test_context_engine.py`, `tests/test_draft_artifact_lifecycle.py`, `tests/test_search.py`, and most React reducer/visibility tests are current product contract.
- `tests/test_turn_payloads.py`, parts of `tests/test_server.py`, and parts of React normalizer/state tests preserve public alias and old payload contracts.
- `tests/test_attention.py`, `tests/test_navigator.py`, `tests/test_artifact_actions.py`, and fallback sections in `tests/test_server.py` protect fallback/safety guardrails.
- `tests/test_context_handoff.py` is an active transitional-seam suite for the Attention/Recall generation cutover.
- `tests/test_response_mode.py` is the clearest historical-regression/compatibility cleanup candidate.

## 2. Taxonomy Legend

| Classification | Meaning | Retirement posture |
|---|---|---|
| Current product contract | Protects desired current behavior, safety, security, serving, storage isolation, or UI semantics. | Do not retire without a product behavior change. |
| Compatibility alias / old payload contract | Preserves public fields, request aliases, old naming, or old payload bridges. | Retire only after consumer review and explicit API/client migration. |
| Fallback / safety guardrail | Protects provider-failure behavior, deterministic repair, conservative blocking, or no-write safety. | Retire only after the structured primary path covers the case and traces prove fallback is no longer relied on. |
| Transitional architecture seam | Protects a bridge between old and new architecture while parity or ownership is still settling. | Retire after target architecture owns the behavior and diagnostics are no longer needed. |
| Historical regression | Protects against a known past bug or retired behavior resurfacing. | Usually first retirement candidate after proving the old input/output shape cannot reappear. |
| Unclear / needs owner review | The test protects behavior whose product role is not obviously current. | Assign owner/reason before changing. |

## 3. Current Product Contract Tests

| Test file / group | Evidence | What it protects | Notes |
|---|---|---|---|
| `tests/test_turn_plan.py` core authority suites | `chat_only`, `surface_authority`, `artifact_write_authority`, `memory_write_authority`, `concept_write_authority`, `protocol_write_authority`, `operational_proposal_authority` tests | TurnPlan write/no-write, draft/offer, artifact, memory, concept, protocol, close/preserve/open-only, and calendar/task proposal authority. | Current behavior. Some assertions mention legacy compatibility, but the suite is primarily the authority contract. |
| `tests/test_server.py` security/deployment/static/PWA/auth sections | Basic Auth, cross-origin mutation, generated React shell, missing-build 503, Dockerfile build, PWA public assets, user OpenAI key scoping | Public deployment and app safety contracts. | Current product/security contract. |
| `tests/test_server.py` calendar/task proposal and accept/reject sections | Calendar/task lookup, proposal, confirmation, accept/reject, global configured write rejection | Proposal-only operational mutation safety and user-scoped writes. | Current contract; deterministic fallback source labels are fallback subcases. |
| `tests/test_surface_invocation.py` | Chat-only, Whiteboard draft, calendar/task/code surfaces, close/preserve, visible artifact Q&A | Deterministic surface policy after structured Navigator/control-panel facts. | Current contract, but raw close/preserve tests are guardrail-flavored. |
| `tests/test_context_engine.py` | Hidden workspace redaction, pending whiteboard carry/drop/force | Safe prepared-turn context and Whiteboard carry semantics. | Current deep-module contract. |
| `tests/test_draft_artifact_lifecycle.py` | Save/publish/promote/reopen flows, experiment/canonical provenance | Draft/Artifact lifecycle service behavior. | Current contract, despite implementation `workspace` naming. |
| `tests/test_search.py` | Concept/memory/artifact/vault/Memory Trace ranking, scope/provenance, recall rationale | Retrieval relevance and bounded mixed-source ranking. | Current retrieval contract. |
| React `App.test.tsx`, `appReducer.test.ts`, `inspectionModel.test.ts`, `visibleArtifacts.test.ts` | Working Memory view, prompt sanitization, surface state, pinned context, visible context serialization | React state, inspection, and visible-context behavior. | Current frontend contract. |
| `src/vantage_v5/webapp_react/src/entrypoints.test.ts` | Vite root/build output and React mount path | React-only frontend/generated-build contract. | Current deployment/frontend contract. |

## 4. Compatibility Alias Tests

| Test file / group | Evidence | Alias or old contract | Retirement condition |
|---|---|---|---|
| `tests/test_turn_payloads.py` chat/scenario body alias cases | `preserves_chat_payload_aliases`, `preserves_scenario_payload_aliases`, malformed `created_record` alias tests | `working_memory`, `created_record`, selected/pinned aliases, `workspace_update.type`, graph-action aliases. | Retire after React and any external clients consume only canonical fields, with an API-versioned migration if public shape changes. |
| `tests/test_server.py` API compatibility cases | CamelCase visible workspace payload test; public payload alias assertions; selected-record/pinned-context payload checks | camelCase request fields, workspace naming, selected-record aliases. | Retire after request and response compatibility consumers are reviewed. |
| React reducer/normalizer behavior around compatibility props | `appReducer.test.ts` uses compatible `view`, workspace, selected resource, pinned context, visible surfaces | Compatibility props while reducer keeps clearer domains. | Retire after components no longer receive old-compatible props and public payload aliases are gone. |
| Scenario Lab legacy lineage server tests | `legacy_comparison_lineage`, legacy comparison artifact recovery, branch metadata recovery | Old `comes_from` and body-derived comparison metadata. | Retire after old comparison artifacts are migrated or declared unsupported. |
| `tests/test_response_mode.py` preface-stripping cases | Strips legacy best-guess preface variants | Old visible answer copy cleanup. | First candidate after model/fallback outputs can no longer include the old preface. |

## 5. Fallback / Safety Tests

| Test file / group | Evidence | Guardrail protected | Retirement condition |
|---|---|---|---|
| `tests/test_navigator.py` fallback cases | canonical fallback decision, open intent fallback, memory intent fallback, preserve fallback | Provider/invalid-output recovery and compact suppressed-action metadata. | Structured Navigator/control-panel output reliably covers the cases; fallback hit traces show it is not needed outside provider failure. |
| `tests/test_attention.py` fallback and surface-selection guard cases | ranked-candidate fallback, legacy surface override, hard chat/close/preserve guard tests | Conservative Attention selection and prevention of accidental UI-open/draft behavior. | Navigator/Attention structured selection fully owns selection and open intent. |
| `tests/test_artifact_actions.py` compiler fallback cases | `compiler.source="deterministic_fallback"`, raw-message task/calendar repair, due-date recovery | Narrow calendar/task proposal repair and visible fallback provenance. | Model-normalized candidates reliably include all required fields, including dates/titles. |
| `tests/test_server.py` provider/model failure sections | chat reply failure fallback, vetting failure fallback, Scenario Lab failure payload, whiteboard accept provider failure | Product-safe completion when model calls fail. | Product decision that offline/provider fallback is no longer supported, or fallback reduced to explicit error-only behavior. |
| `tests/test_server.py` hard no-write blocks | Open-only, close, preserve, hard no-write, malformed proposal, empty candidate tests | Prevents unsafe writes, misleading receipts, and accidental persistence. | Current safety contract; do not retire unless authority model changes intentionally. |
| `tests/test_server.py` public payload sanitization | Memory Trace public payload, generation handoff sanitization, selected Attention Memory Trace sanitization | Prevents raw prompts, trace bodies, and prompt-derived ids from public/model-input leaks. | Current safety contract; not a retirement target. |

## 6. Transitional-Seam Tests

| Test file / group | Evidence | Seam protected | Retirement condition |
|---|---|---|---|
| `tests/test_context_handoff.py` | Handoff roles, role projection, Working Memory view, generation adapter, Memory Trace sanitization, non-Memory-Trace `turn-*` slug preservation | Attention/Recall context handoff while legacy retrieval/search remains in play. | Retire parity/adapter-only tests after handoff owns retrieval/generation without legacy comparison. Keep public-safety tests. |
| `tests/test_server.py` handoff/trace parity sections | generation handoff context, generation_context parity, role projection, working_memory_view trace alignment | Server integration of handoff and legacy search diagnostics. | Retire parity diagnostics after stable smokes and removal of legacy comparison path. |
| `tests/test_turn_payloads.py` assembler/deep-module boundary tests | LocalTurnBodyParts, Chat/Scenario body parts, final response trace payloads | Payload assembly migration out of route-level code. | Keep while assembler is a stable boundary; only retire old alias assertions. |
| `tests/test_server.py` semantic policy/local action sections | local save/publish/experiment status, semantic policy clarifications | Transitional deterministic semantic policy beneath Navigator/TurnPlan. | Retire when TurnPlan/control-panel fully owns those decisions. |
| `tests/test_server.py` meta/write-interpreter sections | meta fallback, create concept/revision, explicit revision upgrade, near-duplicate suppression | Older graph-conditioned write interpreter gated by TurnPlan. | Retire or split after write-intent ownership is consolidated. |

## 7. Historical Regression Tests

| Test file / group | Evidence | Past behavior guarded | First retirement signal |
|---|---|---|---|
| `tests/test_response_mode.py` legacy best-guess preface stripping | `strips_legacy_preface*` | Old visible copy prepended a best-guess sentence into assistant text. | No provider/fallback path can emit that preface; one sanitizer test may be enough. |
| `src/vantage_v5/webapp_react/src/entrypoints.test.ts` legacy entrypoint assertion | Ensures React mount uses `/src/main.tsx`, not `/static/app.js` or `/static/styles.css` | Legacy static frontend reintroduction. | Keep as long as generated-build contract is important; maybe fold into one build-contract test later. |
| Scenario Lab legacy artifact recovery | server tests recover old comparison metadata | Old comparison artifacts without canonical metadata. | Migration or explicit unsupported-old-artifact decision. |
| `workspace_update.type` backfill/carry tests | Pending offer `type` recovers canonical `status` | Old pending whiteboard payload shape. | React/client no longer sends old `type`-only pending offers. |

## 8. Unclear / Owner-Review Tests

| Test file / group | Why unclear | Owner-review question |
|---|---|---|
| Concept revision tests in `tests/test_server.py` and `tests/test_turn_plan.py` | `create_revision` is present and tested, but current UX ownership is less visible than memory/artifact/protocol writes. | Is concept revision a current hidden capability, future UX, or retire/archive candidate? |
| Meta fallback concept creation tests | The meta path remains active beneath TurnPlan gates, but the long-term owner may become control-panel/TurnPlan. | Should meta remain a semantic write interpreter or shrink to persistence prep? |
| Provider fallback draft-generation tests | Local/dev fallback is useful, but product support level is unclear. | Is deterministic draft fallback a supported offline feature or only test/dev scaffolding? |
| Legacy Scenario Lab lineage tests | Useful for old artifacts, but may be permanent drag. | Will old comparison artifacts be migrated once, or should compatibility remain indefinite? |
| Response-mode `legacy_*` internals outside visible preface tests | Some legacy fields may be public-compatibility, some pure internal bridge. | Which clients consume them, and can canonical response-mode fields replace them? |

## 9. First Retirement Candidates

These are the first candidates because they are narrow, mostly compatibility/history, and unlikely to alter current product behavior if handled with focused tests and smoke review.

1. `tests/test_response_mode.py` duplicate legacy preface variants: keep one sanitizer regression or retire the variants after proving no model/fallback path emits the old copy.
2. `workspace_update.type` backfill assertions: retire only after React and pending-offer clients rely on canonical `status` and no old type-only payloads are accepted.
3. `created_record` single-item alias assertions: retire after `learned`/record cards are the only consumer path and external API clients are reviewed.
4. Scenario Lab legacy `comes_from` recovery tests: retire after migrating old comparison artifacts or deciding old artifact compatibility is no longer needed.
5. Parity-only generation-context diagnostics: retire after Attention/Recall handoff owns the generation/retrieval context path and smokes show stable parity.

## 10. Recommended Next Code Slices

1. **Response-mode compatibility narrowing**: inventory `legacy_*` response-mode fields and reduce preface sanitizer coverage to the minimum needed regression.
2. **Public payload alias consumer review**: inspect React normalizers, API smokes, and any external clients for `working_memory`, `created_record`, selected-record aliases, and `workspace_update.type`.
3. **Attention/Recall ownership decision**: decide whether `ChatService.search_context()` remains the private retrieval/vetting helper or becomes removable after handoff cutover.
4. **Fallback observability pass**: ensure Navigator, Attention, artifact-action compiler, provider fallback, and meta fallback all expose clear source/trace labels before any narrowing.
5. **Scenario Lab legacy migration plan**: decide whether to migrate old comparison artifact metadata and then retire body/`comes_from` recovery paths.
