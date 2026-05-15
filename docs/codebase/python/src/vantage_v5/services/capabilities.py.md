# `src/vantage_v5/services/capabilities.py`

Defines Vantage's app capability manifest for operational artifacts.

## Purpose

- Describe first-class app capabilities such as calendar, tasks, and whiteboard.
- Publish resource kinds, tools, invocation policy, write behavior, visible-context serialization, renderer metadata, and receipt events in one product-facing contract.
- Give model calls and the mutation compiler a stable JSON interface for how Vantage expects artifact work to be shaped.

## Core Data Flow

- Capability builders inspect the active calendar/task providers and current workspace state.
- Read-only global files and user-scoped local stores are represented differently so the UI and compiler know whether writes can be proposed.
- Calendar and task mutation tools expose JSON contracts for the second-step compiler while preserving Apply-confirmation semantics.
- The server attaches the manifest to `/api/chat` payloads and safe system state so the frontend and Vantage receipt can explain available tools.

## Important Boundaries

- Capabilities are descriptive; they do not execute writes.
- Calendar and task writes still flow through `ArtifactAction` proposals and deterministic executors.
- The manifest is intentionally MCP-like, but remains a local Vantage contract rather than an external MCP server.

