# Comparable Systems

As of April 19, 2026, these are the most relevant external interaction models for Vantage.

The useful comparison is not “which product has the most features.”

The useful comparison is:

- how they keep chat usable
- how they surface drafting or project work
- how they separate context, memory, and work product
- how much internal machinery they expose by default

## Comparative Matrix

| Product | Core UI pattern | What stays in main chat | What moves to secondary surfaces | Intuition vs clutter | What Vantage should borrow or avoid |
| --- | --- | --- | --- | --- | --- |
| ChatGPT Canvas + Projects | Chat plus explicit collaborative work surface, with projects as context containers | ordinary back-and-forth, quick asks, lightweight edits | canvas drafting, project files, project instructions, project memory | intuitive because the draft is visibly “the work”; can get busy when project context grows | borrow the explicit move from chat to draft surface; avoid making every project input feel equally important |
| Claude Artifacts + Projects | Chat plus dedicated artifact window, with projects as scoped knowledge spaces | prompts, iteration, conversational steering | self-contained work product, project knowledge, project instructions, project memory summaries | very intuitive for “build this thing” flows; clutter rises when artifacts, projects, and memory all compete | borrow the “significant, self-contained work object” rule; avoid blurring artifacts into memory |
| NotebookLM | source-first notebook with separate source, chat, and studio regions | questions, grounded conversation, lightweight steering | sources, notes, derived outputs like guides or audio/video overviews | very legible because the notebook is clearly about these materials; less good as a general assistant shell | borrow the source-bound mental model and strong citation story; avoid making every Vantage turn feel like a research notebook |
| Perplexity Spaces | topic container around threads, files, instructions, and collaborators | question/answer threads and follow-ups | files, shared space context, custom instructions, connectors, collaboration settings | intuitive as a topic hub; clutter risk rises when too many modes share one shell | borrow explicit topic containers and pinning; avoid overloading one surface with too many modes |
| LangSmith / LangGraph Studio | operator-console trace and debugging environment | test prompts and thread playback | execution graph, traces, datasets, node details, prompt editing | powerful but inherently heavy for non-operators | use as an anti-pattern reference for default chat UX; keep this style out of Vantage's main surface |
| Cline checkpoints | action-heavy chat with restore points and diff/recovery tools | task conversation | compare, restore, checkpoint history | useful when an agent makes risky changes; too much history chrome would overwhelm normal users | borrow rollback thinking for memory/work trace design; avoid turning ordinary Vantage turns into checkpoint management |

## Cross-Product Patterns

### 1. Chat Stays Clean

The strongest products keep the main chat surface focused on:

- the transcript
- the composer
- a small amount of status or evidence

They do not force every user to live in a dashboard.

### 2. Work Product Gets Its Own Surface

The drafting surface is not treated as just another assistant message.

Instead it becomes:

- a canvas
- an artifact
- a notebook studio output
- a project document

This gives the user one obvious answer to:

`Where is the thing we are making?`

### 3. Context Containers Work Best When They Are Scoped

Projects, notebooks, and spaces all work because the user can tell:

- what belongs to this container
- what carries across turns
- what is shared
- what is not

The weak version of this pattern is ambient context that “might matter somehow.”

### 4. Transparency Is Secondary, Not Primary

These products generally keep source proof, citations, memory, or trace details behind:

- a source panel
- a project panel
- an inspection surface
- a trace or observability tool

They do not dump all internals into the default answer flow.

## Strong Takeaways For Vantage

- Keep `Chat` as the lightest surface.
- Make `Whiteboard` the explicit home for the thing being drafted.
- Keep `Vantage` as the inspection home for why the answer happened.
- Keep `Library` separate from both `Whiteboard` and `Working Memory`.
- Make carry-forward context legible and scoped.
- Let the user inspect deeper layers, but only on demand.

## What Vantage Should Avoid

- Collapsing memory, sources, work products, and inspection into one generic panel.
- Making the user infer whether they are editing, inspecting, or persisting something.
- Opening deep trace detail before the user understands the answer-level outcome.
- Letting internal terminology dominate the first impression of the UI.

## References

- [OpenAI Academy: Canvas](https://academy.openai.com/en/public/clubs/work-users-ynjqu/resources/canvas)
- [OpenAI Help: Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt)
- [Claude Help: What are artifacts and how do I use them?](https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them)
- [Claude Help: How can I create and manage projects?](https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects)
- [Claude blog: Artifacts are now generally available](https://claude.com/blog/artifacts)
- [Google blog: NotebookLM goes global with Slides support and better ways to fact-check](https://blog.google/innovation-and-ai/products/notebooklm-goes-global-support-for-websites-slides-fact-check/)
- [Google blog: NotebookLM new design with Source, Chat, and Studio regions](https://blog.google/intl/id-id/company-news/technology/notebooklm-kini-dengan-tampilan-baru-dan-audio-interaktif/)
- [Perplexity Help: What are Spaces?](https://www.perplexity.ai/help-center/en/articles/10352961-spaces)
- [LangChain docs: Observability in Studio](https://docs.langchain.com/langsmith/observability-studio)
- [Cline docs: Checkpoints](https://docs.cline.bot/core-workflows/checkpoints)
