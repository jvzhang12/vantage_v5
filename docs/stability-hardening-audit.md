# Stability Hardening Audit

This note is the current stabilization map after the deep-module refactor.

The goal is to keep the new module shape while protecting the canonical Vantage product contract:

- chat stays primary
- Whiteboard is an opt-in drafting surface
- Vantage is the inspection surface
- Working Memory is bounded, truthful model context
- Recall is the narrower retrieved subset
- protocols are task guidance, not factual evidence or draft targets
- Navigator control-panel interpretation is the main intent seam
- deterministic code validates and executes structured decisions

## Canonical Contracts That Survived

- `/api/chat` still runs through `TurnOrchestrator`, with context preparation, Navigator routing, protocol resolution, local semantic actions, Chat or Scenario Lab execution, and final payload assembly separated by module boundaries.
- `ContextEngine` / `ContextSupport` keep hidden whiteboard content out of the model unless the turn intentionally scopes it in.
- `turn_payloads.py` owns the public response shape, compatibility aliases, safe system state, activity, turn interpretation, and workspace-scope disclosure.
- `ProtocolEngine` can inject protocol guidance into Working Memory through Navigator `apply_protocol` actions or protocol interpretation, which is the right answer for non-obvious reasoning lenses that semantic search would miss.
- `DraftArtifactLifecycle` owns save/publish/reopen behavior, keeping artifacts, snapshots, promoted work, and Scenario Lab outputs distinct.
- `record_cards.py` owns UI-facing DTOs for concepts, protocols, memories, artifacts, reference notes, and grouped counts.

## Loose Threads To Stabilize Next

1. Navigator work-product routing

   The ask-first whiteboard path depends on the Navigator choosing `whiteboard_mode="offer"` for concrete work products. The second response-normalization call can make model output parseable, but it cannot recover a whiteboard offer if routing stayed in plain chat. Add an evaluation fixture for email, itinerary, plan, checklist, and code-draft prompts that expects Navigator `offer` unless the user explicitly asks for chat-only output.

2. Control-panel migration

   Some deterministic raw-text helpers remain as transitional guardrails in semantic frame/policy, whiteboard carry, meta fallback, vetting follow-up heuristics, and the frontend deictic reopen path. These should migrate behind Navigator control-panel actions over time. Until then, keep them narrow, tested, and described as guardrails rather than product intent sources.

3. Protocol lifecycle boundaries

   Protocols should be editable in Inspect and usable as guidance in Working Memory. They should not reopen as whiteboard drafts, appear as factual evidence, or be updated from one-off work-product requests. This is now partly locked by tests, but protocol UI affordances and learned-item correction affordances should remain part of regression testing.

4. Grounding truth

   The UI must keep distinguishing Recall, recent chat, whiteboard, pending whiteboard, pinned context, and mixed context. Any future payload reshaping should add tests before changing labels, because this is where product drift becomes user-visible.

5. Runtime artifact noise

   Manual app runs create many untracked Markdown files under `artifacts/`, `concepts/`, `memories/`, `workspaces/`, and `tmp/`. For stabilization work, separate test fixtures from local demo state before committing so runtime state does not obscure source diffs.

## Hardening Checklist

Before merging behavioral changes:

- Run `python3 scripts/check_repo_hygiene.py`.
- Run `git diff --check`.
- Run focused tests for the touched module boundary.
- Run full Python and Node suites before a push.
- Check whether the change broadens Working Memory, blurs Whiteboard vs Vantage, or treats protocols as evidence.
- Check whether a new raw-text classifier should instead be a Navigator control-panel action.
- Check whether the UI explanation remains truthful to backend payload facts.

## Current Priority

The next hardening pass is now scaffolded through `evals/navigator_cases.jsonl`,
`src/vantage_v5/services/navigator_eval.py`, `scripts/eval_navigator.py`, and
`tests/test_navigator_eval_contract.py`.

It should focus on Navigator contract evaluation and routing reliability:

1. Build a small deterministic evaluation harness around representative `NavigationDecision` outputs.
2. Add fixtures for concrete work products, chat-only requests, explicit whiteboard requests, active-draft revisions, Scenario Lab comparisons, and pinned-context follow-ups.
3. Tighten the Navigator prompt/schema only where fixtures show drift.
4. Keep deterministic fallback behavior narrow and visible in tests.
