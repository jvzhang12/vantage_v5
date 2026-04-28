# `src/vantage_v5/services/search.py`

Implements keyword-style scoring across concepts, recent memory-trace records, saved records, and vault notes. It produces ranked `CandidateMemory` objects that later get filtered by vetting and fed into chat and meta reasoning.

## Purpose

- Tokenize free-text queries into normalized search terms.
- Rank records by overlap across title, card, body, path, linked lineage, and broader searchable text.
- Give extra weight to exact phrase matches in titles, cards, paths, links, and lineage when the current record structure supports those signals.
- Merge results from multiple record sources while preferring more durable or curated items and applying a light source-repeat penalty so one bucket does not dominate mixed result sets.
- Keep recent memory-trace retrieval as its own candidate bucket rather than folding it into the Library stores.

## Core Data Flow

- `tokenize()` extracts alphanumeric tokens, removes stopwords when possible, and expands some aliases and word forms.
- `ConceptSearchService.search()` and `search_context()` score record pools and return the top matches.
- `search_memory()` and `search_context()` merge separately scored groups, then re-shape the shortlist with a source-repeat penalty so mixed-source sets stay balanced.
- `search_context()` now accepts `memory_trace_records` plus optional current-whiteboard and preserved-context hints so recent-history continuity can compete with concepts, saved notes, and reference notes during retrieval without turning selected context into a hard side channel.
- Each match becomes a `CandidateMemory`, which preserves the original record content and metadata for later stages.
- `CandidateMemory.reason` stays the machine/debug scoring string, while `CandidateMemory.why_recalled` carries the shorter user-facing recall rationale that chat can expose separately in turn payloads.
- `memory_trace` is intentionally a separate source with its own bonus and priority, so recent-history recall does not masquerade as a concept or saved note.
- Memory Trace records now contribute structured frontmatter metadata as a separate ranking signal, so trace scope and grounding metadata can outrank transcript-body-only matches when recent history is the better continuity source. The scorer also applies bounded Memory Trace bonuses for recency, same-whiteboard continuity, visible-whiteboard agreement, and preserved-context matches when those hints are available.

## Key Classes / Functions

- `SearchableRecord`: protocol describing the fields the scorer needs.
- `CandidateMemory`: normalized search result with score, debug `reason`, user-facing `why_recalled`, source, trust, body, optional path, and optional protocol metadata. `to_dict()` preserves `why_recalled` plus canonical `recall_reason`, protocol editor metadata, and additive taxonomy fields (`kind`, `memory_role`, `recall_status`, `source_tier`) for candidate payloads, while `to_recall_dict()` emits the product-safe recalled view without the raw debug scoring string.
- `ConceptSearchService`: search façade for concept-only, memory-only, or mixed context queries.
- `_search_records()`: applies weighted overlap scoring, phrase boosts, and filters out zero-score items.
- `_token_variants()`: handles simple stemming and alias expansion.
- `_source_bonus()` and `_source_priority()`: bias ranking toward concepts first, then recent/durable saved context, then vault notes.
- `_shape_merged_candidates()`: balances merged rankings so repeated sources do not monopolize the top of the result set.

## Notable Edge Cases

- If tokenization would otherwise return only stopwords, `tokenize()` falls back to the raw token set so the query is not empty.
- Matching is intentionally approximate, with boosts for literal phrase matches in the searchable text, title, card, path, links, lineage, and Memory Trace metadata where available.
- Record body and searchable text are truncated before tokenization, which keeps scoring bounded and avoids overweighting huge documents.
- Items with no lexical or phrase signal are dropped before source bias is applied, so low-signal records do not reach vetting just because they came from a favored bucket.
- Memory Trace bonuses are intentionally small and metadata-driven; they tune recent-history continuity without making traces outrank stronger concept or saved-note matches by default.
- `CandidateConcept` is just an alias of `CandidateMemory`, which keeps older type names compatible without duplicating logic.
