# Vantage V5: Current Implementation vs Canonical Documentation

## Purpose

This note compares the current `vantage-v5` repository to the canonical Vantage documentation in Nexus.

It is not a replacement for canon. It is a reality check:

- what the repository clearly implements now
- what it partially implements
- what still reads more like future-state architecture than present behavior
- where the repository has introduced newer product direction that older canon does not describe cleanly

## Canon Sources Compared

The comparison below is grounded mainly against:

- `03_Product/Vantage V5 — Current Product Vision.md`
- `03_Product/Vantage Simplification Rules.md`
- `03_Product/Workspace View Design — Chat View and Active Workspace View.md`
- `04_Architecture/Architecture Spec.md`
- `04_Architecture/Workspace Runtime Lifetime Rule — One Active Workspace Until Topic Change.md`

## Bottom Line

The repository has moved decisively toward the newer V5 product thesis:

- chat-first
- bounded retrieval
- inspectable working memory
- explicit separation between concepts, memories, artifacts, and the whiteboard
- optional internal inspection through `Vantage`
- optional drafting through an on-demand whiteboard

The repository has not yet moved all the way into the stricter canonical architecture described in older architecture notes.

The largest mismatch is semantic:

- in the current repo, the `whiteboard` / workspace is primarily a collaborative Markdown draft surface
- in the stricter architecture canon, the `active workspace` is a bounded internal reasoning container populated from focused concepts

That distinction matters because several downstream canonical claims depend on it:

- one active workspace until topic change
- familiarity-first retrieval into a focused workspace
- warm cache behavior
- full artifact assembly outside the workspace

Today, the repository is more faithful to the V5 product canon than to the full architecture canon.

## Status Legend

- `Aligned`: current repo behavior matches the canonical expectation closely
- `Partial`: the repo captures part of the idea, but not the full canonical form
- `Diverged`: the repo intentionally behaves differently from the stricter canon
- `Repo-led`: the repo has introduced a meaningful product direction not clearly captured by the cited canon

## Comparison Table

| Theme | Canonical expectation | Current repo reality | Status |
| --- | --- | --- | --- |
| Chat-first experience | Vantage should feel like a normal high-quality LLM chat product. | The repo is explicitly chat-first in the README and UI behavior. | Aligned |
| Concepts vs memories vs artifacts | Durable reasoning knowledge, retained continuity, and concrete outputs should remain distinct. | Separate Markdown-backed stores and distinct UI/library roles are central to the implementation. | Aligned |
| Bounded retrieval | The model should never receive the full graph or full vault. | Chat-time retrieval stays bounded and mixed across concepts, memories, artifacts, and vault notes, then an LLM vets the final subset. | Aligned |
| Inspectable working memory | The user should be able to inspect what influenced the answer. | `Working Memory`, `Learned`, and library inspection are explicit product surfaces. | Aligned |
| Experiment isolation | Temporary notes should remain session-local unless promoted. | Experiment sessions use separate stores and traces, with durable stores treated as references. | Aligned |
| Shared workspace / whiteboard | V5 product canon expects an optional collaborative Markdown workspace. | The current repo implements this directly and now treats the whiteboard as an on-demand drafting surface. | Aligned |
| Meaning of "workspace" | Architecture canon defines the active workspace as a bounded reasoning container of focused concepts. | The repo's workspace is primarily a user-facing draft document, not an internal concept-loaded runtime container. | Diverged |
| One active workspace until topic change | Workspace continuity should depend on concept overlap across turns. | Active workspace state is a persisted selected document id, not a concept-overlap continuity mechanism. | Diverged |
| Familiarity-first retrieval | Retrieval should use semantic candidate generation, reranking, continuity, hierarchy, and graph structure. | Search is currently token-overlap plus lightweight source weighting, followed by LLM vetting. | Partial |
| Warm cache | Recently relevant concepts should remain easier to reactivate through a warm retrieval layer. | No explicit warm-cache layer is implemented in the current runtime. | Diverged |
| Full artifact assembly | The full user-facing artifact should be assembled separately from the bounded workspace. | The whiteboard currently acts as the main draft/artifact surface; there is no separate graph-assembled full artifact layer. | Partial |
| Linked revisions | Meaningful revisions should create linked descendants instead of destructive overwrite. | Revision lineage exists in storage/executor support, but the primary meta path does not currently expose revision creation as a standard outcome. | Partial |
| Read-only library vs writable memory | Nexus/library material should stay visibly distinct from writable Vantage memory. | Reference notes remain separate from saved notes and concept/memory/artifact stores. | Aligned |
| Simplified user-facing ontology | The user should mainly experience chat, optional workspace, and optional inspection, not graph machinery. | The current UI direction strongly favors chat-first with a deliberate `Vantage` inspection mode. | Aligned |
| Scenario Lab | Not a central part of the cited canonical docs. | The repo now treats Scenario Lab as a distinct reasoning mode for comparative what-if work. | Repo-led |

## What The Repo Clearly Optimizes For Now

The current implementation is optimized around a practical V5 interpretation:

1. Keep ordinary chat natural.
2. Keep retrieval bounded and inspectable.
3. Keep durable memory conservative.
4. Let the whiteboard handle real drafting work.
5. Let `Vantage` handle inspection, not routine interaction.
6. Use LLM interpretation for routing and continuity judgments, with deterministic code enforcing payloads and persistence.

This is a coherent direction. It is not random drift.

## Where The Architecture Canon Still Exceeds The Implementation

The following ideas still read as future-state architecture rather than current repo behavior:

- a true focused concept workspace distinct from the whiteboard
- concept-overlap-based workspace continuity
- a warm retrieval cache
- familiarity-first reranking beyond lexical search plus vetting
- graph-assembled full artifacts separate from the draft surface
- revision-first mutation flows as a routine durable behavior

Those ideas may still be valuable. They are just not the best description of the codebase today.

## Recommended Source-Of-Truth Policy

For current implementation work, use the following order:

1. `README.md` for implemented repo behavior and product expectations
2. `03_Product/Vantage V5 — Current Product Vision.md` for current product direction
3. `03_Product/Vantage Simplification Rules.md` for design restraint and UX principles
4. older architecture notes as future-state guidance unless the repo explicitly implements them

## Recommendation

To reduce future confusion, the project should keep one of these stances explicit:

### Option A: Treat the stricter architecture docs as roadmap

Keep the older architecture canon, but label it more explicitly as not-yet-implemented in V5.

### Option B: Split "whiteboard" from "internal focused workspace" in canon

Update the canonical docs so they distinguish:

- `whiteboard`: user-facing full draft / artifact surface
- `working memory` or `focused reasoning set`: bounded internal context

This would make the current repo direction feel much more canonical rather than like drift.

### Option C: Recommit to the stricter architecture with milestones

If warm cache, familiarity-first retrieval, concept-populated workspace formation, and full artifact assembly remain non-negotiable, the project should restate them as explicit upcoming milestones rather than leaving them implied as if they already exist.

## Repo Evidence

The comparison above is grounded in the current implementation, especially:

- `README.md`
- `src/vantage_v5/server.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/search.py`
- `src/vantage_v5/services/navigator.py`
- `src/vantage_v5/services/meta.py`
- `src/vantage_v5/services/executor.py`
- `src/vantage_v5/storage/workspaces.py`
- `src/vantage_v5/storage/state.py`

## Practical Summary

The repo has not become less Vantage-like.

It has become a more practical, product-shaped Vantage:

- closer to the simplified V5 user experience
- more inspectable in the right places
- more explicit about bounded memory and whiteboard collaboration
- less faithful, for now, to the heavier concept-workspace architecture described in the older canon

That is the current implementation truth.
