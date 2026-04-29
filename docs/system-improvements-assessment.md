# System Improvements Assessment

## Purpose

This note compiles read-only assessment findings from backend, frontend, and product-semantics passes over the current repo.

It evaluates whether the current improvement ideas fit `vantage-v5` as it exists today, and where they should plug into the system.

## Summary

The suggestions mostly fit the current repository.

The strongest pattern is:

`Improve Vantage by making context provenance, guidance, and durable learning clearer without adding new top-level surfaces.`

The repo already has much of the substrate:

- `response_mode` for grounding / best-guess disclosure
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

This is the best near-term product improvement.

It should be a thin user-facing layer over existing `response_mode`, recalled item metadata, and protocol guidance.

Recommended badge set:

- `Intuitive Answer`: no grounded Vantage context supported the answer.
- `Memory-Backed`: recalled non-protocol Library or Memory Trace items supported the answer.
- `Protocol-Guided`: a reusable protocol shaped the answer.
- `Whiteboard-Grounded`: active or pending whiteboard content supported the answer.
- `Mixed Context`: multiple meaningful context sources supported the answer.

Important distinction:

`Protocol-Guided` should be treated as guidance, not factual evidence.

Protocols are recipes for how to perform a task. They should not inflate the user's confidence that the answer was factually grounded in memory.

### 2. Unified "Why This Answer" Surface

This already exists in pieces through Inspect, Reasoning Path, Context in Scope, Pulled In, Memory Trace, and Saved for Later.

The improvement should unify those pieces into a clearer turn receipt:

- answer basis badge
- grounding sources
- recalled items
- protocol guidance
- whiteboard / recent chat scope
- learned or saved items
- actions taken

This should live in `Vantage` / Inspect, not as a heavy default chat panel.

### 3. Memory Write Review

The repo already has post-turn `Learned` / `Saved for Later` behavior.

The right next step is not approval before every write. That would make chat feel heavy.

Better direction:

- show what was saved
- explain why it was saved
- expose durability / scope
- add correction actions over time
- support delete / forget / revise / mark wrong once backend actions exist

This keeps learning inspectable without interrupting normal chat.

### 4. Context Budget View

This fits if it is human-readable, not token-console-like.

Recommended shape inside Inspect:

- user request: included
- Recall: N items
- protocols: N applied
- whiteboard: included / excluded
- recent chat: included / excluded
- pinned context: preserved / not preserved
- pending whiteboard: included / excluded

Avoid exact token counts until the backend can provide them reliably.

### 5. Protocol Library UX

Protocols are real in the backend and should become more legible.

Good UX direction:

- list built-in and custom protocols
- show when each protocol applies
- show what behavior it changes
- allow inline editing where already supported
- surface `Protocol-Guided` on turns where one applied

Risk:

Do not make protocols look like factual evidence, saved drafts, or ordinary concepts. They are task guidance.

### 6. Recall Failure UX

The current `Best Guess` behavior is already close.

The improvement is clearer product copy:

- no relevant Vantage memory was used
- the answer came from general model understanding
- user can save, correct, or pin context if useful

The product may use `Intuitive Answer` as the softer badge label, but its meaning should remain precise:

`No grounded Vantage context supported this answer.`

## Ideas That Need Care

### Concept Key / Value Terminology

The attention-inspired model is useful as an internal design metaphor:

- current user turn / retrieval intent = query
- concept key = compact routing representation
- concept value = full stored content brought into context

But the repo already uses:

- `title`
- `card`
- `body`
- `links`

and the code/tests rely heavily on `card`.

Recommendation:

- keep `card` internally for now
- use `concept key/value` experimentally in design docs or advanced Inspect copy
- avoid a repo-wide rename until the language has proven itself
- preserve compatibility if aliases are later introduced

### Memory Confidence / Freshness

Freshness and confidence are useful, but easy to overstate.

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
- Making answer-basis badges sound like claims about the model's hidden reasoning rather than claims about supplied Vantage context.

## Recommended Implementation Order

1. Add an `answer_basis` payload derived from existing `response_mode`, recalled items, protocol actions, and context sources.
2. Update frontend badge copy to use the answer-basis mapping without adding a new surface.
3. Separate protocol guidance from factual grounding in payload and UI.
4. Improve `Saved for Later` / `Learned` into the memory write review surface.
5. Add correction actions for saved items and bad recall.
6. Add Context Budget inside Inspect.
7. Build a more visible Protocol Library / protocol Inspect subview.
8. Experiment with concept key/value terminology in docs or advanced metadata only.
9. Add freshness/confidence labels once correction paths and semantics are clear.

## Concrete Checklist Additions

- [ ] Define `answer_basis` backend DTO.
- [ ] Map `response_mode.kind == "best_guess"` to `Intuitive Answer`.
- [ ] Map recalled non-protocol items to `Memory-Backed`.
- [ ] Map applied protocol guidance to `Protocol-Guided`.
- [ ] Map whiteboard context sources to `Whiteboard-Grounded`.
- [ ] Map multiple sources to `Mixed Context`.
- [ ] Ensure protocols do not count as factual memory evidence.
- [ ] Add tests for answer-basis mapping.
- [ ] Add frontend tests for badge rendering.
- [ ] Improve Saved for Later with review/correction affordances.
- [ ] Add Context Budget to Inspect.
- [ ] Draft a small protocol-library UX plan.
- [ ] Keep concept key/value terminology exploratory until validated.

## Bottom Line

The suggestions make sense because they push Vantage toward its strongest identity:

`A chat-first thinking system that tells the user what context shaped an answer and what it learned afterward.`

The implementation should stay conservative: refine existing response mode, Inspect, Learned, Protocol, and Reasoning Path surfaces before adding new architecture.
