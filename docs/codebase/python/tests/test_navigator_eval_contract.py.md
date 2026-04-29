# `tests/test_navigator_eval_contract.py`

Offline contract tests for the Navigator eval harness.

## Purpose

- Verify the eval case file stays a small product-behavior contract rather than a brittle mirror of the full Navigator payload.
- Test summary extraction and scoring without calling OpenAI.

## Coverage

- Loads `evals/navigator_cases.jsonl` and checks that required high-signal cases are present.
- Asserts expected summaries contain only `route`, `draft_surface`, `protocols`, and `preserve_context`.
- Verifies `summarize_navigation_decision()` deduplicates protocol actions and maps whiteboard modes into behavior summaries.
- Verifies Scenario Lab summaries ignore advisory whiteboard mode and report no draft surface.
- Verifies eval failures stay compact and focused on mismatched behavior fields.
- Verifies result aggregation and invalid expected-summary rejection.
