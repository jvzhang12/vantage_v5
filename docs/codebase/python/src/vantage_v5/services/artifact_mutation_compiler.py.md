# `src/vantage_v5/services/artifact_mutation_compiler.py`

Second-step artifact mutation compiler for Vantage app actions.

## Purpose

- Convert the assistant's natural-language semantic action into the existing `ArtifactAction` JSON contract.
- Keep the main response model conversational while a separate compiler step produces validated calendar/task mutations.
- Preserve the proposal-only boundary: compiler output can propose actions, but deterministic executors commit only after the user clicks Apply.

## Core Data Flow

- `ArtifactMutationCompiler.compile_for_turn()` receives the user message, assistant semantic action text, and current visible artifacts.
- It decides whether compilation is relevant by looking for mutation language, operational visible artifacts, or artifact-related app capability cues.
- When an OpenAI-backed compiler is available, it receives a compact prompt containing the current artifact context and the relevant app JSON interfaces.
- If provider output is unavailable or invalid, the compiler falls back to the deterministic `ArtifactActionPlanner`.
- Returned actions are annotated with compiler metadata so the Vantage receipt can explain whether the action came from the compiler, deterministic fallback, or validation repair.

## Important Boundaries

- This module does not mutate calendar or task files directly.
- It delegates validation and persistence to `artifact_actions.py`.
- Visible artifacts are treated as the current working view and are the primary targeting source for edits like replacing or moving a calendar event.
- Global read-only providers remain non-writable because capability and executor checks happen after compilation.

