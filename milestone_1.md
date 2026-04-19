# Vantage V5 Milestone 1

## Goal

Build the first usable V5 surface:

- simple chat UI
- shared collaborative Markdown workspace
- concept file schema and local filesystem layout

This milestone should establish the product foundation without yet implementing the full retrieval, vetting, or meta-call pipeline.

## Why This Is First

V5 is chat-first.

The first thing that must feel good is:
- talking to the assistant
- seeing a normal chat transcript
- collaboratively working in a shared Markdown workspace

Before memory logic becomes sophisticated, the core interaction should already feel natural and useful.

## In Scope

### 1. Chat UI
Build a minimal local web UI with:
- chat transcript
- message composer
- assistant responses
- loading and error states

The chat should feel like talking to a normal LLM.

### 2. Shared Workspace UI
Build a shared Markdown workspace pane where:
- the current workspace document is visible
- the user can edit it
- the assistant can propose edits
- workspace content can be referenced during chat

For Milestone 1, only one workspace document needs to be active in the UI at a time.

### 3. Local Filesystem Structure
Create the initial V5 local filesystem structure:

- `concepts/`
- `workspaces/`
- `state/`
- `traces/`
- `prompts/`

These directories do not need full functionality yet, but they should exist and be wired into the app structure.

### 4. Concept Schema
Lock in the initial concept Markdown schema:

- `id`
- `title`
- `type`
- `card`
- `created_at`
- `updated_at`
- `links_to`
- `comes_from`
- `status`

This milestone should include at least a few seed concept files that follow this schema.

### 5. Workspace Document Model
Establish the shared workspace document format as Markdown files stored in `workspaces/`.

For Milestone 1:
- one sample workspace document should exist
- the app should be able to load it
- the app should be able to edit/save it locally

### 6. Local App Skeleton
Establish the initial app boundary:
- local web app
- local backend
- local file-backed storage

The app should run end-to-end locally.

## Out of Scope

Milestone 1 should not yet include:
- concept search
- vetting LLM call
- top-5 concept selection
- graph-conditioned meta call
- automatic novelty detection
- automatic concept creation from chat
- workspace promotion into concepts
- archive/delete policy implementation
- embedding pipeline
- graph visualization

These belong to later milestones.

## Success Criteria

Milestone 1 is successful if:

1. the user can open a local V5 app
2. the user can chat naturally with the assistant
3. the user can view and edit a shared Markdown workspace
4. the assistant can reference the workspace during chat
5. the app has the agreed local folder structure
6. concept files exist in the agreed Markdown schema
7. the whole thing works locally without the memory architecture getting in the way

## Deliverables

### Product Deliverables
- basic chat interface
- shared workspace pane
- sample seeded concepts
- sample seeded workspace document

### Technical Deliverables
- local file-backed app structure
- concept Markdown schema
- workspace Markdown schema
- backend/frontend plumbing for chat and workspace load/save

## Recommended Build Order

1. scaffold the local app
2. create the directory structure
3. implement the chat view
4. implement the shared workspace pane
5. load/save a Markdown workspace file
6. create seed concept files in the agreed schema
7. ensure the assistant can receive workspace content in chat context
8. add basic traces for chat and workspace actions

## Notes

Milestone 1 is intentionally not the memory system.

It is the product foundation that later memory features will plug into.

If this milestone succeeds, V5 should already feel like:
- a normal LLM chat app
- with a collaborative Markdown workspace
- and a visible path toward durable concept memory
