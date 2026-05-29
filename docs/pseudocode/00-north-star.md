# 00. North Star

> Status: Current source of truth
> Note: This is intended product logic. Current implementation may differ in transitional seams documented by the architecture overview, compatibility ledger, and stale-code inventory.

## Product Intent

Vantage should feel like a normal high-quality chat model while quietly maintaining useful, bounded, inspectable memory.

The user should not feel the architecture first. They should feel:

- a natural chat partner
- a collaborative Whiteboard when drafting helps
- a Vantage inspection surface when they want to see context and saved outcomes
- conservative write behavior
- memory that helps without replaying the whole past

## Core Loop

```text
on user_turn(message):
    understand the user's goal semantically
    gather only relevant bounded context
    answer naturally in chat unless a surface or write is explicitly appropriate
    propose or draft instead of mutating when confirmation is required
    save durable state only through approved authority
    record Memory Trace for future recall
    expose safe, compact receipts to the user
```

## North Star Rules

Ordinary chat stays ordinary:

```text
if user_turn is simple Q&A:
    answer in chat
    include relevant bounded context if selected
    avoid forcing Whiteboard, Vantage, or Library workflows
```

Work products use the right surface:

```text
if user asks for a substantial draft and Whiteboard would help:
    offer or open Whiteboard according to explicitness and current state
    keep the draft pending until accepted or saved
else:
    answer in chat
```

Memory helps but stays bounded:

```text
candidate_context = search(Memory Trace + Library + relevant surfaces)
selected_context = LLM_vet(candidate_context, message)
working_memory = bounded(current message + recent chat + selected_context + intentional surface context)
```

Writes require authority:

```text
if proposed_action mutates durable state:
    require explicit user intent or confirmation-gated proposal
    validate with TurnPlan/write authority
    execute only through the existing write path
```

## Product Distinctions

Keep these distinctions visible in every design and implementation review:

| Distinction | North Star |
|---|---|
| Chat vs Whiteboard | Chat is default conversation; Whiteboard is collaborative drafting. |
| Whiteboard vs Library | Whiteboard is active work; Library is saved durable material. |
| Concepts vs memories vs artifacts | Concepts are timeless reasoning knowledge; memories are continuity facts; artifacts are concrete outputs. |
| Attention vs Recall vs Working Memory | Attention selects broad turn resources; Recall is memory grounding over selected resources; Working Memory is the full bounded model input. |
| Draft vs proposal vs durable write | Drafts and proposals are pending; durable writes persist only after authority. |
| Explicit intent vs inferred convenience | Explicit user commands outrank convenience guesses. |
| LLM reasoning vs deterministic code | LLMs interpret semantic intent; deterministic code validates, bounds, projects, and executes. |

## Anti-Goals

Do not make Vantage into:

- a control panel that interrupts normal chat
- a transcript replay system
- a deterministic keyword router disguised as intelligence
- an always-on whiteboard
- a single generic memory bucket
- an automatic write engine
- a public payload that exposes raw internal trace bodies
