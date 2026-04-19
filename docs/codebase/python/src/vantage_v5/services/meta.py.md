# `src/vantage_v5/services/meta.py`

Decides whether a chat turn should create durable graph state, and if so, what kind of record to write. It turns a user/assistant exchange plus nearby context into a `MetaDecision` that stays concept-forward for stable, generalizable turns while preserving `dont_save` and pending-whiteboard guardrails.

## Purpose

- Classify the current turn as `no_op`, `create_concept`, `create_memory`, or `promote_workspace_to_artifact`.
- Prefer concept creation for stable, generalizable novelty when the turn is durable enough to matter.
- Link nearby related concepts through `links_to` instead of suppressing every related concept write.
- Prefer no write when the intent is ambiguous or blocked by guardrails.
- Build lightweight titles, cards, bodies, and links for downstream stores.

## Core Data Flow

- `MetaService.decide()` checks `memory_mode` first and immediately suppresses writes when the user disabled memory saving.
- `MetaService.decide()` also checks for pending whiteboard offers or drafts and blocks all durable writes on those turns, even if the user combines drafting language with explicit remember/save/promote language in the same message.
- If an OpenAI client is available, `_openai_decide()` sends the turn, workspace excerpt, history, and vetted items to the model and parses a JSON decision. The model prompt asks for concept-forward behavior on stable/generalizable turns, and the method now applies a small deterministic backstop so near-duplicate concepts are suppressed and related vetted concepts are preserved in `links_to` even if the model omits them.
- If the model call fails or no API key is configured, `_fallback_decide()` applies deterministic phrase matching and simple heuristics that stay concept-forward for explanatory turns, while still blocking near-exact duplicates.
- The returned `MetaDecision` is later consumed by the executor to actually write concepts, memories, or artifacts.

## Key Classes / Functions

- `MetaDecision`: dataclass describing the proposed graph action and optional fields like title, card, body, target concept, and links.
- `MetaService`: orchestrates model-backed and fallback decisioning.
- `_openai_decide()`: prepares the payload, constrains the allowed actions, and parses the JSON response.
- `_fallback_decide()`: handles explicit user phrases such as “save as concept,” “promote workspace,” and “remember this,” then otherwise applies concept-forward heuristics for reusable knowledge turns.
- `_related_concept_links()`: filters vetted concepts down to the subset that actually overlaps with the current turn before adding them as `links_to`.
- `_validated_link_targets()`: limits model-returned `links_to` values to vetted concept ids so the write path cannot introduce arbitrary concept references.
- `_is_pending_whiteboard_update()`: enforces the non-durable whiteboard guardrail before either meta path runs.
- `_title_from_message()`: shortens and title-cases user text for record titles.
- `_sentence_card_from_text()`: extracts a compact first sentence for cards.
- `_body_from_turn()`: stores the source exchange as Markdown sections.

## Notable Edge Cases

- `memory_mode == "dont_save"` always returns `no_op`, even if the turn looks save-worthy.
- Pending whiteboard offers or drafts also return `no_op`; explicit save/remember wording on the same turn does not override that boundary, which keeps ask-first whiteboard collaboration from turning into an accidental graph write based on wrapper text or stale workspace state.
- The OpenAI path is wrapped in a broad `try/except`, so any API or parsing failure silently falls back to deterministic logic.
- The concept-forward direction lives in the policy prompt and repo documentation, with the fallback path adding only lightweight duplicate checks and durable-turn heuristics.
- Similar vetted concepts are allowed to remain as `links_to` context for new concepts; only near-duplicate restatements are suppressed.
- Explicit fallback memory phrases now win even when saved notes were already retrieved, which keeps direct user save requests from being suppressed by retrieval noise.
- Fallback concept and memory writes reuse the same title/card/body shaping helpers, which means the saved record may reflect either the user message or assistant reply depending on available text.
- `links_to` is normalized to an empty list in `to_dict()` so downstream code does not have to handle `None`.
