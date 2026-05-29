# Vantage Pseudocode Canon

> Status: Current source of truth
> Note: This is design-intent guidance, not proof that the current implementation already matches every step. Use it to evaluate future code changes against the intended product and architecture logic.

## Purpose

This directory describes Vantage as intended system logic before implementation details.

Use it when a change touches:

- chat turn flow
- Attention, Recall, or Working Memory
- Whiteboard and Vantage surfaces
- durable writes, proposals, drafts, or TurnPlan authority
- public-safe context and trace projection
- deterministic fallback boundaries

The canonical vocabulary remains in [../glossary.md](../glossary.md). The implementation architecture map remains [../architecture-overview.md](../architecture-overview.md). Compatibility surfaces remain cataloged in [../compatibility-ledger.md](../compatibility-ledger.md).

## Read Order

1. [00-north-star.md](00-north-star.md)
2. [01-core-principles.md](01-core-principles.md)
3. [02-information-model.md](02-information-model.md)
4. [03-turn-lifecycle.md](03-turn-lifecycle.md)
5. [04-attention-recall-working-memory.md](04-attention-recall-working-memory.md)
6. [05-write-authority.md](05-write-authority.md)
7. [06-surfaces-and-whiteboard.md](06-surfaces-and-whiteboard.md)
8. [07-agent-readable-context.md](07-agent-readable-context.md)
9. [08-failure-modes.md](08-failure-modes.md)

## Contract

This canon is current design intent.

It does not:

- change runtime behavior
- authorize API payload changes
- authorize storage path changes
- authorize test deletion
- prove current code conforms
- supersede the compatibility ledger for retained aliases and old names

When code and this canon differ, do not silently "fix" the difference in an unrelated slice. Record the mismatch, check the compatibility ledger and test taxonomy, then plan a behavior-preserving cleanup or an explicit product change.
