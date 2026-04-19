# `tests/test_search.py`

This test file covers the ranking and retrieval behavior of `ConceptSearchService`. It checks that searches prefer concept records that match the user query, that memory search can combine saved memories, artifacts, and vault notes into one result set, and that reasoning-oriented queries surface the most relevant concept notes for planning, root-cause analysis, counterfactual thinking, debate, and mechanism-focused reasoning.

The newer coverage also verifies that:

- zero-signal records are dropped instead of surviving on source bonus alone,
- memory records can outrank artifacts on tied lexical matches because source weighting stays deterministic,
- `links_to`, `comes_from`, and path-like signals can move an otherwise generic record to the front,
- mixed-source result sets can differ from the raw score ordering when the repeat-penalty shaping prevents one source bucket from monopolizing the shortlist,
- and the scorer still behaves predictably across the current concept, memory, artifact, and vault-note record types.

That matters because search is one of the main ways the system decides what context to surface. These tests protect the relevance layer: they verify that the service is not only returning results, but returning the right kinds of results in a useful order, which directly affects downstream chat quality and retrieval trustworthiness.
