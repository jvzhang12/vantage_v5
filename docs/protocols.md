# Vantage Protocols

Protocols are reusable instructions for recurring classes of work. They sit between general concepts and one-off memories: a protocol describes how Vantage should perform a task type, which variables matter, and which user preferences should be carried forward.

## Current Slice

- Protocols are stored as Markdown-backed concept records with `type: protocol`.
- The first supported protocol kinds are `email`, `research_paper`, and `scenario_lab`.
- `ProtocolEngine` runs the LLM protocol interpreter to decide whether a turn updates a reusable protocol, recalls an existing protocol, both, or neither.
- Once that interpreter returns a structured decision, `ProtocolEngine` deterministically upserts one stable protocol record or attaches matching protocols to Recall.
- Matching requests such as "Draft an email..." can bring the relevant protocol into Recall before vetting, so the assistant can follow the user's stored variables and procedure.
- The Navigator control panel can also press `apply_protocol`, which lets deterministic code inject a selected protocol into working memory even when semantic search would not retrieve it naturally.
- `/api/protocols` exposes active protocol cards, and `include_builtins=true` also returns built-in protocols that do not yet have persisted overrides.
- `GET /api/protocols/{protocol_kind_or_id}` resolves a protocol by stable id or supported kind.
- `PUT /api/protocols/{protocol_kind}` updates a protocol from the Inspect editor. Editing a built-in protocol creates a persisted override in the active scope instead of mutating the built-in default.
- Experiment mode protocol edits are temporary because they write to the experiment concept store; durable mode edits write to the durable concept store.

## Email Protocol Example

An email protocol can carry variables such as:

- `recipient_name`: infer from the request unless ambiguous.
- `sender_name`: infer from saved preference when available.
- `signature`: the user's preferred sign-off name.
- `style`: tone preferences such as concise, warm, professional, or business.
- `format`: structural preferences such as greeting, body, close, and signature.

The assistant should treat turn-specific instructions as overrides, but otherwise follow the stored protocol whenever the interpreter decides the current work matches it.

## Scenario Lab Protocol

The built-in `scenario_lab` protocol is a reasoning recipe rather than a saved user preference. It asks Vantage to use first-principles, counterfactual, causal, tradeoff, and assumption-surfacing lenses when comparing branches. This covers the gap where a user asks about scenarios but the relevant reasoning concepts are not semantically close enough to the query to appear through ordinary retrieval.

When the Navigator selects `apply_protocol` with `protocol_kind: "scenario_lab"`, `ProtocolEngine` builds the protocol candidate that chat and Scenario Lab merge into working memory before vetting. The model should treat it as task guidance, not as a factual source claim.

## Product Direction

Protocols now appear as editable Inspect cards with summary, applies-to phrases, variables, and procedure body. The editor intentionally has no delete/reset flow yet; future work can add explicit reset-to-built-in and protocol history once the core editing contract has settled.
