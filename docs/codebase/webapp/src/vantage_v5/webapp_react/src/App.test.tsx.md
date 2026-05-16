# `src/vantage_v5/webapp_react/src/App.test.tsx`

Focused React rendering coverage for the top-level Vantage app shell.

## Purpose

- Verify that cross-surface chat behavior remains visible in the mounted UI, not just in reducer state.
- Guard the mobile whiteboard/chat visibility contract for normal assistant replies.

## Coverage

- Opens a selected saved artifact into the Whiteboard, then sends a normal follow-up turn while the Whiteboard remains active.
- Asserts the latest assistant answer is rendered and the Whiteboard content remains open, preserving chat-first visibility without creating or replacing a surface.
