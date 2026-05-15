# `tests/test_artifact_json_interface.py`

Tests the artifact JSON interface used by the second-step mutation compiler.

## Purpose

- Verify that calendar/task capability contracts expose the JSON shapes the model compiler needs.
- Ensure writable and read-only provider states are represented truthfully.
- Keep mutation-facing contracts stable as Vantage adds more first-class app capabilities.

## Coverage

- Calendar and task tool schemas include supported operations, payload fields, and commit boundaries.
- The contracts describe proposal-only behavior rather than direct mutation.
- Capability payloads remain product-facing and compact enough to send alongside relevant model calls.

