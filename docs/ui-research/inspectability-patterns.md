# Inspectability Patterns

This document focuses on how AI products make reasoning, sources, memory, and system actions inspectable without making the product feel like an operator console.

For Vantage, this matters because the product already has strong internal distinctions:

- `Working Memory`
- `Recall`
- `Memory Trace`
- `Whiteboard`
- `Library`
- `Learned`
- `Reasoning Path`

The problem is not missing concepts.

The problem is choosing which of those concepts belong in:

- default chat
- guided inspection
- deep debugging

## Taxonomy

### Evidence

Small proof objects that answer:

`Why should I trust this answer?`

Typical forms:

- inline citations
- source chips
- “used 2 recalled items”
- “grounded by whiteboard”

Best placement:

- default chat
- turn summary headers

### Context

A compact explanation of what was in scope for the answer.

Typical forms:

- recall badges
- whiteboard / recent chat / pinned context chips
- a short “this answer used recall + whiteboard” disclosure

Best placement:

- default chat in compact form
- expanded in `Vantage`

### Trace

A staged explanation of how the system moved from request to answer.

Typical forms:

- request
- route
- considered context
- selected recall
- working-memory scope
- outcome

Best placement:

- secondary inspection surface

### Draft State

A clear representation of the active work product and its lifecycle.

Typical forms:

- transient draft
- saved whiteboard
- promoted artifact
- pending whiteboard offer

Best placement:

- whiteboard surface
- compact chat invite when relevant

### Checkpoints And Recovery

A way to recover from bad agent actions without losing context.

Typical forms:

- compare
- restore
- version history
- task checkpoints

Best placement:

- action-heavy tools
- advanced drafting or coding flows

These should not dominate ordinary chat.

### Durable Change Log

A minimal answer to:

`What changed because of this turn?`

Typical forms:

- learned item
- created memory
- saved artifact
- trace recorded

Best placement:

- `Vantage`
- turn review

## Default Chat vs Secondary Inspection

### Default Chat Should Show

- the answer
- a compact grounding/evidence signal
- at most one active drafting invitation
- very small status cues when something was learned or saved

### Secondary Inspection Should Show

- the full `Reasoning Path`
- `Recall`
- `Memory Trace`
- working-memory scope
- candidate context
- library inspection
- durable writes

### Deep Debugging Should Stay Even Further Back

- raw prompts
- token-level reasoning
- full candidate pools by default
- tool plumbing
- execution internals not meaningful to normal users

## Common Failure Modes

- Showing every internal concept in the main answer frame.
- Treating “open for inspection” as if it also means “in scope for generation.”
- Merging `Recall`, `Working Memory`, and `Memory Trace` into one blob.
- Leading with candidate search detail before the answer-level outcome is clear.
- Spreading the same drafting decision across chat, whiteboard, notices, and inspection panels at once.

## Recommended Mapping For Vantage

| Vantage concept | Best default exposure | Best expanded exposure |
| --- | --- | --- |
| `Whiteboard` | chat invite or draft-ready cue | full drafting surface |
| `Working Memory` | one compact grounding label | scope table inside `Vantage` |
| `Recall` | count chip only | inspectable selected items |
| `Memory Trace` | usually hidden | recent-history contribution and trace record |
| `Reasoning Path` | hidden by default | staged inspection rail |
| `Learned` | compact “Learned 1 item” chip | explicit saved items section |
| `Library` | usually hidden | full search, inspect, pin, open flows |

## Implications

- `Vantage` should feel like guided inspection, not permanent exposure of internals.
- `Working Memory` should explain scope, not try to be the entire top-level page title for the turn.
- `Reasoning Path` should start from user-meaningful stages and keep deeper candidate detail behind expansion.
- `Memory Trace` should remain inspectable, but secondary.
- The UI should prefer one honest compact cue in chat over five explanatory subpanels.

## References

- [Google blog: NotebookLM source grounding and inline citations](https://blog.google/innovation-and-ai/products/notebooklm-goes-global-support-for-websites-slides-fact-check/)
- [Google blog: NotebookLM Source / Chat / Studio layout](https://blog.google/intl/id-id/company-news/technology/notebooklm-kini-dengan-tampilan-baru-dan-audio-interaktif/)
- [Perplexity Help: What are Spaces?](https://www.perplexity.ai/help-center/en/articles/10352961-spaces)
- [OpenAI Help: Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt)
- [OpenAI Academy: Canvas](https://academy.openai.com/en/public/clubs/work-users-ynjqu/resources/canvas)
- [Claude Help: What are artifacts and how do I use them?](https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them)
- [LangChain docs: Observability in Studio](https://docs.langchain.com/langsmith/observability-studio)
- [Cline docs: Checkpoints](https://docs.cline.bot/core-workflows/checkpoints)
