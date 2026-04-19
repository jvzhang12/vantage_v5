# Vantage V5 Milestone 3

## Goal

Complete the first demoable V5 memory loop:

- graph-conditioned meta call after chat
- strict executor for graph actions
- concept creation and revision primitives
- explicit workspace promotion into concept memory
- concept inspection and open-into-workspace flow

This milestone is where V5 stops being only a chat shell with retrieval and becomes a usable concept-memory product.

## In Scope

- meta call with a compact structured action schema
- executor layer that validates and applies graph actions
- active workspace state persistence
- concept creation as Markdown files
- revision file creation for concept updates
- workspace promotion to concept
- opening a concept into the shared workspace
- UI notices for memory writes and graph actions
- traces that include meta output and executed actions

## Out of Scope

- full graph visualization
- advanced link editing UI
- archive UI
- embeddings pipeline
- multi-user collaboration
- automatic concept splitting
- large-scale ontology design

## Success Criteria

Milestone 3 is successful if:

1. the assistant still behaves like a normal chat assistant
2. only vetted concepts enter the assistant context window
3. a meta call runs after each turn
4. the executor can safely create Markdown concepts when memory actions are selected
5. the user can explicitly promote a workspace document into a concept
6. the user can inspect a concept and open it into the shared workspace
7. the UI makes saved memory and graph updates visible without being noisy
8. the product is demoable end to end in local mode

## Deliverables

- meta call service
- graph action executor
- active workspace state store
- concept open and promotion API routes
- richer chat payloads with meta and graph-action data
- memory-aware frontend controls and notices
- tests covering open, promote, and remember flows

## Notes

Milestone 3 is the first point where the README contract is materially present in the running app.

After this point, the main remaining work is polish, stronger OpenAI prompting, and deeper memory behaviors rather than basic product shape.
