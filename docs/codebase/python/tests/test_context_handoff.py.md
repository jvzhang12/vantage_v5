# `tests/test_context_handoff.py`

Focused unit tests for the internal Attention/Recall context handoff.

## Purpose

- Verify that `AttentionRecallContextHandoff` groups selected, visible, recalled, protocol, pinned, and surface-open resources into compact roles.
- Verify that the compatibility Attention/Recall role projection and public Working Memory view can be built from the same handoff source.
- Verify that the handoff-to-generation adapter preserves ordinary recalled candidates while sanitizing Memory Trace candidates before response generation.
- Guard against leaking full resource bodies, raw prompts, or chain-of-thought fields through the handoff/view payloads.

## Coverage

- Selected Attention resources appear in `answer_context`; explicit open targets appear in `surface_to_open`.
- Legacy Recall records appear in `recall_context`, and protocol records also appear in `protocol_guidance`.
- Pinned context appears in `pinned_or_continuity_context`.
- Handoff comparison records selected-vs-recall overlap and gaps.
- Working Memory view construction remains bounded and keeps write execution summaries separate from resource bodies.
- Memory Trace resources with raw prompt/assistant-derived fields are sanitized across handoff, role projection, and Working Memory view payloads.
- Prompt-derived Memory Trace storage ids are replaced by safe public aliases, role references/comparison ids resolve to those aliases, and `working_memory_view.turn.trace_id` does not expose raw Memory Trace record ids.
- Handoff-derived generation memory keeps concept bodies available but replaces Memory Trace ids with safe aliases and strips raw trace bodies.
- Selected Attention Memory Trace resources are sanitized before generation while selected non-Memory-Trace resources remain behavior-compatible.
- Synthetic surface-open placeholders preserve the open-target role without claiming they were sent to the response LLM.
