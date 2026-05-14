# `tests/test_response_mode.py`

Focused unit tests for response-mode message finalization.

## Purpose

- Verify assistant messages no longer receive the legacy best-guess text preface.
- Preserve the backend best-guess/intuitive metadata contract while keeping the visible answer text clean.

## Coverage

- Best-guess responses return their original answer text without prepending `This is new to me, but my best guess is:`.
- Legacy prefaces already present in a model or fallback answer are stripped defensively, including the punctuated variant seen in earlier UI copy.
- Grounded answers without the legacy preface remain unchanged.
