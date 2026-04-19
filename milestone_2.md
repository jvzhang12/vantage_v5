# Vantage V5 Milestone 2

## Goal

Add the first real memory path to V5:

- search candidate concepts from the graph
- vet which concepts are relevant to the current turn
- send only those vetted concepts into assistant context

This milestone implements the bounded concept-retrieval layer without yet adding novelty detection or concept creation.

## In Scope

- concept search over Markdown concepts
- candidate ranking
- vetting selection of up to 5 relevant concepts
- chat call receives vetted concepts plus recent chat and workspace
- UI shows which concepts were relevant for the current turn
- traces record candidates and vetted concepts

## Out of Scope

- novelty detection
- meta call
- concept creation
- workspace promotion
- revision logic
- graph writes

## Success Criteria

Milestone 2 is successful if:

1. the system can retrieve concept candidates for a user turn
2. a vetting step selects a bounded relevant subset
3. the assistant receives only those vetted concepts
4. the UI can show the concepts used for the turn
5. the app still works in fallback mode without OpenAI
