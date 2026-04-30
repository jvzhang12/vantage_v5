# System Improvements Assessment

## Purpose

This note compiles read-only assessment findings from backend, frontend, and product-semantics passes over the current repo.

It evaluates whether the current improvement ideas fit `vantage-v5` as it exists today, and where they should plug into the system.

## Summary

The suggestions mostly fit the current repository.

The strongest pattern is:

`Improve Vantage by making context provenance, guidance, and saved turn outcomes clearer without adding new top-level surfaces.`

The repo now has much of the substrate:

- `response_mode` for grounding / best-guess disclosure
- `answer_basis` for turn-level basis badges and separated evidence / guidance buckets
- `turn_interpretation` for Navigator route and control-panel decisions
- `Recall` and candidate context payloads
- `Working Memory` inspection
- `Learned` / `Saved for Later` surfaces
- protocol records and built-in protocol guidance
- Memory Trace records
- Reasoning Path / Inspect UI

Most improvements should refine those existing surfaces rather than create a second explanation system.

## High-Confidence Recommendations

### 1. Answer-Basis Badges

Status: implemented as a turn payload and frontend badge/review model.

It is a thin user-facing layer over existing `response_mode`, recalled item metadata, recent chat / whiteboard context, and protocol guidance.

Recommended badge set:

- `Intuitive Answer`: the answer came from general learned capability rather than a specific recalled Vantage context object.
- `Memory-Backed`: recalled non-protocol Library or Memory Trace items supported the answer.
- `Protocol-Guided`: a reusable protocol shaped the answer.
- `Whiteboard-Grounded`: active or pending whiteboard content supported the answer.
- `Mixed Context`: multiple meaningful context sources supported the answer.

Important distinction:

`Protocol-Guided` should be treated as guidance, not factual evidence.

Protocols are recipes for how to perform a task. They should not inflate the user's confidence that the answer was factually grounded in memory.

Draft taxonomy:

| Label | Trigger | Counts as factual grounding? | Shown in chat? | Shown in Inspect? |
| --- | --- | --- | --- | --- |
| `Intuitive Answer` | The answer was generated from general learned capability, without a specific recalled Library record, Memory Trace item, whiteboard, pinned item, or pending-draft context materially supporting it. This is the normal LLM-style response path: useful pattern-based judgment without an explicit remembered source to point at. | No | Yes, as the compact answer-basis badge. | Yes, with copy explaining that the answer came from general model intuition rather than supplied Vantage context. |
| `Memory-Backed` | One or more recalled non-protocol Library or Memory Trace records supported the answer. | Yes | Yes, as the compact answer-basis badge. | Yes, with the supporting recalled records listed separately from protocol guidance. |
| `Protocol-Guided` | A reusable protocol shaped the task behavior, format, variables, or procedure. | No | Yes, when protocol guidance is the main differentiator. | Yes, with the applied protocol shown as task guidance rather than evidence. |
| `Whiteboard-Grounded` | Active whiteboard, pending whiteboard offer, or reopened draft content materially supported the answer. | Yes, when the draft content supplies task facts or source material. | Yes, as the compact answer-basis badge. | Yes, with whiteboard scope shown separately from recalled Library records. |
| `Mixed Context` | More than one meaningful context source supported or shaped the answer, such as memory plus protocol, whiteboard plus memory, or pinned context plus protocol. | Depends on included sources; protocol guidance alone does not make the factual grounding stronger. | Yes, as the compact answer-basis badge. | Yes, with each contributing source bucket separated so guidance, evidence, and draft context do not collapse together. |

Definition note:

`Intuitive Answer` should not mean random, unsupported, or mystical. It means Vantage is answering the way humans often speak from intuition: drawing on general learned understanding without recalling a specific source, memory, draft, or protocol that can be cited as the basis for the answer.

### 2. Unified "Why This Answer" Surface

This already exists in pieces through Inspect, Reasoning Path, Context in Scope, Pulled In, Memory Trace, and Saved for Later.

The answer-basis and Saved for Later slices improve the turn receipt, but the whole Inspect consolidation is not done. The remaining improvement should unify these pieces into a clearer turn receipt:

- answer basis badge
- grounding sources
- recalled items
- protocol guidance
- whiteboard / recent chat scope
- learned or saved items
- actions taken

This should live in `Vantage` / Inspect, not as a heavy default chat panel.

### 3. Memory Write Review

Status: a read-only review slice is implemented, and the backend saved-item correction route now supports narrow negative correction.

The API field remains `learned`; the UI may call the same turn-created/saved items `Saved for Later`. That label is product copy, not a payload rename. It means a turn-created/saved item exists in `learned`; it does not mean the item is verified, correct, fresh, or high confidence.

The right next step is still not approval before every write. That would make chat feel heavy.

Implemented first pass:

- show what was saved
- explain why it was saved
- expose durability / scope
- keep direct correction affordances read-only or guidance-only where backend mutation is not explicit

This keeps learning inspectable without interrupting normal chat.

Correction semantics decision:

- `POST /api/records/{source}/{record_id}/corrections` is the backend correction seam.
- Supported actions are `mark_incorrect` and `forget`.
- Both actions are hide/suppress semantics: they remove the saved item from Library lists, recall, and saved-item search through a hidden/suppressed writable record or status update.
- These actions are not hard deletes; the underlying saved file or lower-priority record remains on disk.
- Correction responses should expose a `correction` object with the corrected `source`, `record_id`, `action`, requested/effective scope, hidden-record scope, correction status, reason when supplied, and whether the correction suppresses canonical material.
- Correction payloads should not add freshness or confidence fields.
- Direct correction UI controls remain deferred until the product flow is explicit; the current visible review loop still favors whiteboard revision and pinning.

Deferred:

- direct content edit, durable hard delete, and scope mutation such as `make_temporary`
- freshness/confidence labels or scoring
- broader privacy/retention behavior beyond hide/suppress suppression semantics

### 4. Context Budget View

Status: implemented as a human-readable Inspect receipt.

The backend now emits a `context_budget` DTO for each turn, and Inspect renders it inside Context in Scope.

Implemented shape inside Inspect:

- user request: included
- Recall: N items
- protocols: N applied
- whiteboard: included / excluded
- recent chat: included / excluded
- pinned context: preserved / not preserved
- pending whiteboard: included / excluded

The receipt intentionally avoids exact token counts. It is a scope receipt, not a provider-token console.

### 5. Protocol Library UX

Protocols are real in the backend and should become more legible.

Good UX direction:

- list built-in and custom protocols
- show when each protocol applies
- show what behavior it changes
- allow inline editing where already supported
- surface `Protocol-Guided` on turns where one applied

Inspect Protocols is backed by `GET /api/protocols?include_builtins=true`, which returns persisted protocols plus missing built-in defaults in one deduped catalog. Source labels should stay simple: `Built-in`, `Custom override`, and `Custom`. The underlying flags (`is_builtin`, `is_canonical`, `overrides_builtin`, `overrides_canonical`) carry the exact backend provenance without making the UI sound like protocols are factual evidence.

Risk:

Do not make protocols look like factual evidence, saved drafts, or ordinary concepts. They are task guidance.

### 6. Recall Failure UX

The current implementation keeps the backend `best_guess` response mode while using `Intuitive Answer` as the softer answer-basis label.

The product copy should keep making this clear:

- no relevant Vantage memory was used
- the answer came from general model understanding
- user can save, correct, or pin context if useful

The meaning should remain precise:

`The answer came from general learned capability rather than a specific recalled Vantage context object.`

## Ideas That Need Care

### Concept Key / Value Terminology

Decision: `concept key/value` is accepted only as an advanced design metaphor, not as product UI, API, or schema vocabulary.

The metaphor can be useful in design discussion:

- current user turn / retrieval intent = query
- concept title, card, metadata, and links = routing signals
- concept body / full saved content = content that may enter Working Memory

The canonical repo vocabulary remains:

- `title`
- `card`
- `body`
- `links`
- `links_to`

and the code/tests rely heavily on `card`.

Guardrails:

- preserve `card`, `body`, and `links` / `links_to` as schema and internal terms
- do not introduce `concept key/value` in product UI, API, or schema fields
- do not imply literal transformer attention
- do not start a repo-wide rename from this metaphor
- preserve compatibility if aliases are later introduced

### Memory Confidence / Freshness

Freshness and confidence are useful, but easy to overstate.

Current implementation decision: freshness/confidence labels remain deferred until the correction UI flow and semantics are product-tested. The current freshness-related pass adds only a narrow noisy-write guard for obvious test/probe/freshness-marker prompts so they do not become durable concepts. It is not a freshness model, confidence model, source-verification system, or correction workflow.

Separate these concepts:

- retrieval match strength
- source recency
- user-confirmed status
- durable vs temporary scope
- answer uncertainty

Do not imply factual certainty just because a record is fresh or highly matched.

### Session Modes

Experiment mode and durable mode are already real.

The product improvement should make write scope clear without adding another navigation maze.

Recommended emphasis:

- `Durable`: writes can affect the long-term Library.
- `Experiment`: writes stay session-local unless promoted.
- `Drafting`: whiteboard is active.
- `Scenario Lab`: branch comparison mode is active.

## Main Risks

- Duplicating explanation surfaces instead of simplifying the current Inspect hierarchy.
- Treating protocols as factual sources instead of guidance.
- Collapsing `Recall` into `Working Memory`.
- Making memory review interrupt normal chat.
- Turning concept key/value into confusing ML jargon for ordinary users.
- Adding confidence/freshness labels before correction paths exist.
- Making answer-basis badges sound like claims about the model's hidden reasoning rather than claims about whether supplied Vantage context shaped the answer.

## Recommended Implementation Order

1. Complete: add an `answer_basis` payload derived from existing `response_mode`, recalled items, protocol actions, and context sources.
2. Complete: update frontend badge copy to use the answer-basis mapping without adding a new top-level surface.
3. Complete: separate protocol guidance from factual grounding in payload and UI.
4. Complete first pass: improve `Saved for Later` / `Learned` into a read-only memory write review surface.
5. Backend route implemented: `mark_incorrect` and `forget` are saved-item hide/suppress corrections; direct edit, hard delete, make-temporary, freshness, confidence, and direct UI controls stay deferred.
6. Complete: add Context Budget inside Inspect.
7. Complete: build a more visible Protocols guidance subview inside Inspect.
8. Complete docs-only decision: accept concept key/value only as an advanced design metaphor, preserving `card`, `body`, and `links` / `links_to` as canonical terms.
9. Deferred: add freshness/confidence labels once the correction UI flow and semantics are product-tested.

## Concrete Checklist Additions

- [x] Define `answer_basis` backend DTO.
- [x] Map `response_mode.kind == "best_guess"` to `Intuitive Answer`.
- [x] Map recalled non-protocol items to `Memory-Backed`.
- [x] Map applied protocol guidance to `Protocol-Guided`.
- [x] Map whiteboard context sources to `Whiteboard-Grounded`.
- [x] Map multiple sources to `Mixed Context`.
- [x] Ensure protocols do not count as factual memory evidence.
- [x] Add tests for answer-basis mapping.
- [x] Add frontend tests for badge rendering.
- [x] Improve Saved for Later with read-only review affordances.
- [x] Implement backend saved-item correction semantics for `mark_incorrect` and `forget` as hide/suppress actions, not hard deletes.
- [ ] Add broader Saved for Later mutation actions such as direct edit, hard delete, or make temporary.
- [x] Add Context Budget to Inspect.
- [x] Draft and implement a small Protocols guidance UX inside Inspect.
- [x] Record concept key/value as an advanced design metaphor only, not UI/API/schema vocabulary.
- [x] Add a narrow guard for obvious test/probe/freshness-marker prompts so they do not become durable concepts.
- [ ] Add Saved for Later freshness/confidence labels only after the correction UI flow and semantics are product-tested.

## Bottom Line

The suggestions make sense because they push Vantage toward its strongest identity:

`A chat-first thinking system that tells the user what context shaped an answer and what it learned afterward.`

The implementation should stay conservative: refine existing response mode, Inspect, Learned, Protocol, and Reasoning Path surfaces before adding new architecture.
