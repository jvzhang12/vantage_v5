# `src/vantage_v5/services/context_budget.py`

Builds the turn-level Context Budget receipt used by Inspect.

Responsibilities:

- summarize whether the user request, Recall, protocol guidance, whiteboard, recent chat, prior draft, pinned context, and Memory Trace contributed to a turn
- expose readable included / excluded rows without token accounting
- keep protocol counts separate from factual memory counts while still showing that protocol guidance shaped the task

This module is presentation-oriented DTO assembly. It does not perform retrieval, token counting, or storage mutation.
