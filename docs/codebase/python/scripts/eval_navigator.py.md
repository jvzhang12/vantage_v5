# `scripts/eval_navigator.py`

Opt-in command-line runner for Navigator behavior evals.

## Purpose

- Validate the JSONL Navigator case file without calling OpenAI by default.
- When run with `--live`, call the configured Navigator model and compare each response against the compact behavior summary contract.

## Usage

```bash
python3 scripts/eval_navigator.py
python3 scripts/eval_navigator.py --live
python3 scripts/eval_navigator.py --live --write-report
```

## Behavior

- Loads cases from `evals/navigator_cases.jsonl` unless `--cases` is provided.
- Uses `AppConfig.from_env()` for `OPENAI_API_KEY` and `VANTAGE_V5_MODEL` during live runs, but imports that config lazily so offline case validation does not require app runtime dependencies.
- Reduces each raw `NavigationDecision` to `{route, draft_surface, protocols, preserve_context}` before scoring.
- Can write JSON reports under `eval_runs/` with both compact summaries and raw decisions for debugging.
