# 07. Agent-Readable Context

> Status: Current source of truth
> Note: This file is for future Codex/LLM agents deciding whether implementation matches product intent.

## How Agents Should Use This Canon

```text
before editing behavior:
    read README.md
    read docs/README.md
    read glossary and semantic rules
    read this pseudocode canon section relevant to the change
    read compatibility ledger and stale-code inventory for noisy seams
    read mirrored codebase summaries for touched files
    then read source
```
This order keeps implementation entropy from becoming product truth by accident.

## Evaluation Pattern

```text
function evaluate_code_against_canon(change):
    identify intended product rule
    identify current implementation seam
    identify compatibility consumers and tests
    decide whether change is:
        behavior-preserving cleanup
        compatibility retirement
        intentional behavior change
        docs-only clarification
    choose tests and smokes accordingly
```

Do not treat a mismatch as automatic permission to rewrite code. Some mismatches are retained compatibility.

## Context Receipts

Safe agent-readable receipts should answer:

- What context was actually in scope?
- Which role did it play?
- Which surface or write action was authorized?
- Which fallback, if any, supplied a decision?
- What was saved, proposed, or left pending?

```text
receipt:
    context_sources: bounded safe list
    role_projection: answer_context / recall_context / protocol_guidance / surface / pinned
    authority: safe allow/deny/proposed/no-write summary
    fallback_source: absent or explicit
```

Receipts should not expose hidden chain-of-thought, raw prompts, full Memory Trace bodies, or prompt-derived trace ids.

## Documentation Priority

When docs conflict, use this order unless a task says otherwise:

1. `README.md` and `docs/README.md`
2. `docs/glossary.md`
3. `docs/semantic-rules.md`
4. `docs/working-memory-and-trace-model.md`
5. `docs/pseudocode/`
6. `docs/architecture-overview.md`
7. `docs/compatibility-ledger.md`
8. `docs/stale-code-inventory.md` and `docs/test-taxonomy.md`
9. mirrored codebase summaries
10. historical/archive docs

The order is not a license to ignore implementation. It is a guide for resolving intent before editing.

## When To Update This Canon

Update this canon when:

- intended system logic changes
- a compatibility seam becomes permanent product shape
- a current principle is proven wrong by product direction
- a new surface or write authority class is added

Do not update it merely because current code is messy. Current-code drift belongs in architecture docs, stale-code inventory, or implementation plans.

## Agent Checklist

```text
before finalizing a change:
    check no raw Memory Trace leaks to public payload/model input
    check deterministic fallback remains narrow and labeled
    check visible/open/selected/pinned/in-scope remain distinct
    check writes are authority-gated
    check experiment mode stays isolated
    check compatibility aliases were not removed accidentally
    check docs and mirrored summaries match touched source/tests
```
