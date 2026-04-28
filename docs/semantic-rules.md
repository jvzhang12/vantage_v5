# Vantage V5 Semantic Rules

## Purpose

This note turns the glossary into implementation-facing rules.

Use it when changing:

- UI behavior
- payload semantics
- retrieval scope
- whiteboard behavior
- continuity rules
- grounding disclosures

Read this after [glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md).

## Core Rule

The system should stay chat-first while making context, drafting, and durable learning inspectable.

That means:

- ordinary chat should feel natural
- Whiteboard should stay collaborative rather than mandatory
- Memory Trace should capture recent searchable history automatically
- Working Memory should stay bounded and only include what the model actually sees
- Recall should stay the narrower retrieved subset that feeds Working Memory, with legacy `working_memory` retained only as a compatibility alias
- durable writes should stay conservative
- Workspace should be treated as a deprecated implementation term rather than the future product noun
- broad user-intent interpretation should live in the Navigator control panel, with deterministic code validating and executing structured actions

## Rule 1: Open Is Inspect-Only By Default

Opening an item means the user is viewing it.

Opening an item does **not** automatically mean:

- it enters Working Memory
- it becomes pinned
- it stays active next turn

Implementation checklist:

- opening a library item should default to inspection behavior
- opening a scenario artifact should not silently pin it
- opening a whiteboard branch should not automatically broaden current-turn context beyond the active whiteboard rules

## Rule 2: Pinning Is The Explicit Carry-Forward Mechanism

If context should stay active across turns, it should be pinned explicitly.

Implementation checklist:

- pinning should persist until the user clears it
- pinning should be stronger than simple selection or inspection
- UI copy should not blur `open` and `pinned`

## Rule 3: Visible Is Not The Same As In Scope

Something can be visible to the user without influencing the current answer.

Implementation checklist:

- Vantage inspection should not automatically broaden Working Memory
- an opened library item can remain out of scope
- a hidden whiteboard should not silently ground normal chat

## Rule 4: Working Memory Means Actual Model Access

Working Memory is the bounded in-scope context the LLM actually has access to for the current response.

That includes the current user message and any other in-scope sources that genuinely contribute to generation.

`Recall` is the retrieval step or recalled subset pulled into Working Memory after retrieval and vetting.

`Memory Trace` is the automatically captured recent-history layer that the system can search when deciding what is relevant now.

Implementation checklist:

- if something influenced the answer, it should be representable in the in-scope context model for the turn: the current `user_message`, recent chat, whiteboard, pending whiteboard, selected continuity context, `Memory Trace`, or a truthful mixed-context combination
- if concepts, memories, artifacts, reference notes, or recent trace items were pulled into the turn, describe them as `Recall`
- the top-level `recall` field is the recall-shaped subset produced by retrieval and vetting, and legacy `working_memory` is only an alias for that subset; do not treat either as the entire product concept of Working Memory
- if something is not in scope, it should not be described as grounding the answer
- the UI should make the full in-scope generation context legible, while keeping the narrower recalled subset explicit

## Rule 5: Whiteboard Is A Separate Surface That Can Enter Working Memory

The whiteboard is not the same thing as Working Memory.

It is a separate collaborative surface that may contribute to Working Memory when it is in scope.

Implementation checklist:

- keep the whiteboard visually separate from Working Memory and Library views
- do not describe all whiteboard content as recalled memory
- when the whiteboard is in scope, treat it as active current-turn context rather than a saved-note retrieval event
- keep the current whiteboard distinct from its trace history, which belongs to Memory Trace

## Rule 6: Whiteboard Content Should Count Only When Intentionally In Scope

Whiteboard content should influence the answer only when product semantics say it should.

It should normally count when:

- the whiteboard is open and active
- the whiteboard is explicitly pinned
- the user explicitly refers to the current draft
- the user explicitly asks to draft or continue in the whiteboard

It should normally not count when:

- the whiteboard exists but is hidden and not referenced
- the user is inspecting Vantage or the Library without referring to the draft
- a stale pending whiteboard offer is no longer relevant

Implementation checklist:

- keep `workspace_scope` authoritative
- keep whiteboard carry-over narrow and intentional
- do not let passive visibility heuristics silently inject whiteboard content

## Rule 7: Explicit Whiteboard Requests Should Skip Redundant Confirmation

If the user explicitly asks to open the whiteboard or draft there, the system should move into drafting behavior directly.

Implementation checklist:

- `open whiteboard`
- `draft this in whiteboard`
- `put that on the whiteboard`

These should not trigger an extra invitation step unless there is a genuine ambiguity the user needs to resolve.

## Rule 8: Follow-Up Drafting Should Prefer Continuation Over Restart

If there is an active draft and the user is clearly continuing it, the system should continue the current whiteboard rather than reoffering or starting over.

Implementation checklist:

- `revise that`
- `update the email`
- `add my name`
- `change the tone`

These should usually target the active whiteboard draft when one exists and is in scope.

When the user is clearly referring to a different recently surfaced saved draft rather than the current whiteboard, the system should prefer reopening that saved item over silently continuing the wrong draft.

Implementation checklist:

- the navigator should eventually receive a small continuity frame rather than only free-text recent chat
- that frame should stay metadata-first and should be small by default
- the strongest recent saved-item reference should outrank generic recent-whiteboard recency
- do not dump a long recent-whiteboard history into every navigator call
- when ambiguity remains meaningful, ask or present a small explicit choice rather than guessing

## Rule 9: Pending Drafts And Offers Are Non-Durable Until Applied Or Saved

Whiteboard offers and draft proposals should remain pending and inspectable until the user accepts, applies, or saves them.

Implementation checklist:

- do not silently write pending drafts to disk
- do not silently replace unrelated unsaved work
- preserve non-destructive fork-or-replace behavior when a new draft conflicts with an existing unsaved draft

## Rule 10: Learned Means Durable Change, Not Internal Reasoning

`Learned` should report what changed durably because of the turn.

Implementation checklist:

- concepts, memories, or artifacts created after the turn belong in `Learned`
- transient interpretation or retrieval reasoning does not belong in `Learned`
- do not overstate learning when the system only considered something without saving it

## Rule 11: Grounding Disclosures Must Stay Truthful

The system should distinguish between:

- grounded by Working Memory
- grounded by the whiteboard
- grounded by recent chat
- grounded by pending whiteboard continuity
- mixed context
- best guess

Implementation checklist:

- use `Best Guess` only when there is no relevant grounded context
- do not imply recalled-memory grounding when only the current user message, recent chat, or whiteboard context supported the answer
- do not imply trace-backed Recall when the turn did not actually recall memory-trace items
- do not label the broader Working Memory bundle as if it were only the narrower `working_memory` field
- do not treat `Recall` as the whole of `Working Memory`
- keep Scenario Lab on the same disclosure contract so a comparison grounded by whiteboard or recent chat is not mislabeled as a best guess
- keep frontend evidence tied to backend payload truth

## Rule 12: Durable Types Must Stay Distinct

The saved roles should remain clear:

- `Concepts` for timeless reasoning knowledge
- `Memories` for retained continuity facts
- `Artifacts` for concrete work products

Implementation checklist:

- do not collapse all saved things into one generic memory bucket
- do not treat every saved whiteboard as a concept
- do not treat every durable write as equivalent for UI labeling

## Rule 13: Scenario Lab Is A Distinct Reasoning Mode

Scenario Lab should remain separate from ordinary chat and from ordinary whiteboard drafting.

Implementation checklist:

- comparative what-if work should remain navigator-routed
- Scenario Lab outputs should behave like durable branch outputs plus a comparison artifact
- follow-up questions on a comparison artifact should prefer continuity over rerunning the whole flow

## Rule 14: Experiment Mode Must Preserve Temporary Boundaries

Experiment mode is a sandbox.

Implementation checklist:

- temporary notes should remain session-local unless promoted
- experiment inspection should not blur temporary and durable state
- UI copy should stay clear about what is temporary and what is durable

## Rule 15: Protocols Are Guidance, Not Evidence

Protocols describe how Vantage should perform a recurring class of work.

They can enter Working Memory through protocol interpretation or Navigator `apply_protocol` actions, including cases where semantic search would not naturally retrieve the right reasoning lens.

Implementation checklist:

- treat protocol items as task recipes, output-shape guidance, or user preferences
- do not cite a protocol as a factual source claim
- keep protocol activation LLM-directed through the protocol interpreter or Navigator control panel
- let deterministic code validate supported protocol kinds and merge candidates safely

## Rule 16: The Control Panel Is The Intent Seam

The target architecture is LLM-directed interpretation followed by deterministic execution.

Implementation checklist:

- the Navigator should choose product actions such as `apply_protocol`, `draft_whiteboard`, `open_scenario_lab`, `save_whiteboard`, or `ask_clarification`
- deterministic code should validate targets, enforce safety, and persist data
- avoid adding new broad raw-text intent classifiers when the Navigator can return a structured action
- existing deterministic helpers should be treated as transitional guardrails or safety policy, not as the long-term intent layer

## Quick Checklist For New Changes

Before shipping a behavior change, check:

- Does this change broaden Working Memory accidentally?
- Does this confuse `open`, `pinned`, or `in scope`?
- Does this blur Whiteboard, Memory Trace, Recall, or Working Memory?
- Does this make the whiteboard feel mandatory instead of collaborative?
- Does this overclaim what grounded the answer?
- Does this blur concepts, memories, and artifacts?
- Does this make Vantage feel like an operator console instead of guided inspection?
- Does this break experiment isolation?
- Does this add raw-text intent sorting where a Navigator control-panel action should exist?
- Does this treat protocol guidance as factual evidence?

If the answer to any of these is yes, the change likely needs another pass.
