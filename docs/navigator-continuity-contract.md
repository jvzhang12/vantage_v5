# Navigator Continuity Contract

## Purpose

This note documents the implemented V1 continuity payload for the navigator LLM and the small set of follow-on extensions that may still come later.

It exists because the repository previously had a real product seam:

- the navigator can see recent chat text
- the navigator can see the current whiteboard excerpt
- the navigator can see pinned context and pending whiteboard update state
- and the navigator previously did **not** receive a small structured continuity frame for recently active whiteboards and last-turn referenced saved items

That gap makes deictic follow-ups such as:

- `pull that up on the whiteboard`
- `go back to the other email`
- `continue the first draft`
- `open the earlier one`

harder than they should be.

The goal is to fix that without flooding the navigator with too much context or turning the interpreter into a brittle deterministic rules engine.

## Current Repository Truth

Today the navigator payload in [src/vantage_v5/services/navigator.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/navigator.py) already includes:

- `user_message`
- `recent_chat`
- current whiteboard metadata and content excerpt
- `requested_whiteboard_mode`
- canonical pinned-context id and summary
- pending whiteboard update context

That is enough for:

- ordinary chat vs Scenario Lab routing
- whiteboard offer vs draft hints
- pinned-context continuity
- many current-draft follow-ups

The repository now also includes a small structured `continuity_context` built server-side in [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py) and passed into the navigator interpreter.

That continuity frame currently provides:

- `current_whiteboard`
- `recent_whiteboards`
- `last_turn_referenced_record`
- `last_turn_recall`

The practical remaining gap is narrower:

- `last_turn_referenced_record` is now written as an explicit internal Memory Trace fact for new turns, but older traces still fall back to preserved-context or unique-recall reconstruction
- whiteboard source linkage is opportunistic when the workspace id also resolves as a saved record id
- navigator outputs still stop at `mode` and `whiteboard_mode` rather than exposing richer explicit reopen targets

So the repository now has a bounded continuity frame for reopen-style interpretation, with the strongest previous-turn record handoff written at trace time instead of reconstructed only at read time. It still has room to become less heuristic around whiteboard/source linkage and reopen-target outputs over time.

## Design Goal

Give the navigator a **small metadata-first continuity frame**.

The navigator should have enough structured context to interpret `this`, `that`, `the other one`, `the earlier draft`, and similar follow-ups fluidly.

It should **not** receive a large dump of recent whiteboards or full content for many drafts.

## Implemented V1 Continuity Frame

The navigator now receives:

- `current_whiteboard`
- `recent_whiteboards`: last `3` by default
- `last_turn_referenced_record`: `0` or `1`
- `last_turn_recall`: top `3` max
- `pending_whiteboard_update` when present

This is intentionally small.

The point is to help the navigator answer:

`What is the user probably referring to right now?`

not:

`Here is a large workspace history dump; infer everything from scratch.`

## Canonical Payload Shape

```json
{
  "current_whiteboard": {
    "workspace_id": "draft-email-to-jerry",
    "title": "Draft Email to Jerry",
    "status": "dirty",
    "source_record_id": "email-to-jerry",
    "source_record_title": "Draft Email to Jerry",
    "content_excerpt": "Hi Jerry, I hope your day is going well..."
  },
  "recent_whiteboards": [
    {
      "workspace_id": "predicting-behavior-email",
      "title": "Email Draft: Insights on Predicting Behavior and the Importance of Representation",
      "source_record_id": "email-insights-on-predicting-behavior",
      "source_record_title": "Email Draft: Insights on Predicting Behavior and the Importance of Representation",
      "last_active_at": "2026-04-21T12:34:56Z",
      "kind": "reopened_artifact"
    }
  ],
  "last_turn_referenced_record": {
    "record_id": "email-insights-on-predicting-behavior",
    "title": "Email Draft: Insights on Predicting Behavior and the Importance of Representation",
    "source": "artifact",
    "reopenable_in_whiteboard": true
  },
  "last_turn_recall": [
    {
      "record_id": "email-insights-on-predicting-behavior",
      "title": "Email Draft: Insights on Predicting Behavior and the Importance of Representation",
      "source": "artifact"
    }
  ],
  "pending_whiteboard_update": {
    "status": "offered",
    "summary": "I can draft the email in the whiteboard."
  }
}
```

## Field Semantics

### `current_whiteboard`

This is the currently active whiteboard surface.

It should include:

- id
- title
- continuity status such as dirty/saved
- source-record linkage when the whiteboard came from a saved item
- content excerpt only when appropriate for routing

It answers:

`Are we already in the middle of an active draft?`

### `recent_whiteboards`

This is a small shortlist of recently active whiteboards.

Default:

- `3` items

Possible later expansion:

- `5` if product evidence shows it is needed

Each item should be metadata-first:

- `workspace_id`
- `title`
- `last_active_at`
- `kind`
- source-record linkage when available
- optional short excerpt

It answers:

`If the user says "the other draft," what nearby whiteboards are even plausible?`

### `last_turn_referenced_record`

This is the strongest explicit saved-item reference from the previous turn when one exists.

This is more precise than plain recent chat text.

It answers:

`What concrete durable item did the assistant most recently surface or talk about as an object?`

This field should be absent when confidence is low.

### `last_turn_recall`

This is the top recalled saved-item shortlist from the previous turn.

Default:

- max `3`

This should be metadata only, not full bodies.

It answers:

`What did the system just pull up that the user might be referring back to?`

### `pending_whiteboard_update`

This remains the explicit handoff for offer/draft continuity and should stay separate from recent-whiteboard history.

It answers:

`Is there a still-open invitation or pending draft proposal that should outrank older continuity?`

## Ranking Principles

The navigator should reason with a simple continuity priority:

1. active pending whiteboard flow
2. current whiteboard when the user is clearly continuing it
3. last explicitly referenced saved record
4. last-turn recalled items
5. recent whiteboards

This priority keeps the system from overfitting to older drafts when the current draft is obviously the intended target.

## Future Navigator Outcomes

The current repository still only exposes:

- `mode`
- `whiteboard_mode`
- pinned-context preservation hints

The next-step semantic model should eventually let the navigator distinguish:

- `keep_in_chat`
- `draft_new_whiteboard`
- `continue_current_whiteboard`
- `reopen_recalled_record`
- `reopen_recent_whiteboard`

That does **not** mean the navigator should execute those actions directly.

The correct split is:

- navigator decides intent and target
- deterministic execution performs the open/replace/apply safely

## Safety And Boundedness

This continuity frame should stay narrow.

Do **not** send:

- full content for many recent whiteboards
- long transcript slices just because they are recent
- a large list like `10` by default

Why:

- too much context will make the navigator noisier
- routing quality will drift downward if every continuity call becomes a mini retrieval problem
- the product should remain fluid and semantic, not overloaded

Recommended boundedness rule:

- `recent_whiteboards`: `3` default
- `last_turn_recall`: `3` max
- `last_turn_referenced_record`: singular when high confidence
- full content only for the current in-scope whiteboard, not the whole recent list

## Relationship To Existing Canon

This proposal stays aligned with the repository’s current semantic rules:

- `Whiteboard` remains a separate collaborative surface
- `Working Memory` remains the actual in-scope generation context
- `Recall` remains the narrower vetted recalled subset
- `Pinned Context` remains the explicit carry-forward mechanism
- `Memory Trace` remains recent searchable history, not a raw replay bucket

This contract is specifically for **navigator continuity interpretation**, not for broadening Working Memory automatically.

## Implementation Notes

The initial implementation deliberately followed this order:

1. add a small continuity view-model builder on the server side
2. thread that view-model into `NavigatorService.route_turn()`
3. keep the current route schema stable first

That is now done. A later pass can still:

4. extend navigator outputs with explicit reopen target semantics
5. keep execution deterministic for replace/keep/open safety

This phased approach avoids mixing:

- payload canon migration
- whiteboard continuity semantics
- execution-path changes

into one risky step.

## Near-Term Product Benefit

This should improve turns like:

- `pull that up on the whiteboard`
- `open the other email`
- `continue the previous draft`
- `go back to the first itinerary`

without forcing the user to remember ids, titles, or internal system state.

That is a meaningful product improvement because it makes Vantage feel more like a coherent working environment and less like a chat app with hidden file state.
