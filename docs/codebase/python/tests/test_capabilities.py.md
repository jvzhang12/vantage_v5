# `tests/test_capabilities.py`

Tests the Vantage app capability manifest.

## Purpose

- Ensure calendar, tasks, and whiteboard register as first-class Vantage capabilities.
- Verify that resources, tools, renderer metadata, write behavior, and receipt metadata stay stable.
- Protect the user-scoped write model from accidentally treating global provider files as writable.

## Coverage

- Capability payload versioning and app ids.
- Calendar/task tool availability and JSON contracts.
- Read-only versus writable provider status.
- Manifest fields that `/api/chat`, the mutation compiler, and Vantage receipt depend on.

