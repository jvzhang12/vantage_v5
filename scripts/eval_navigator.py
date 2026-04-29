from __future__ import annotations

import argparse
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vantage_v5.services.navigator_eval import evaluate_navigation_summary
from vantage_v5.services.navigator_eval import load_navigator_eval_cases
from vantage_v5.services.navigator_eval import NavigatorEvalCase
from vantage_v5.services.navigator_eval import results_payload
from vantage_v5.services.navigator_eval import summarize_navigation_decision
from vantage_v5.storage.workspaces import WorkspaceDocument


DEFAULT_CASES_PATH = REPO_ROOT / "evals" / "navigator_cases.jsonl"


def main() -> int:
    args = _parse_args()
    cases = load_navigator_eval_cases(args.cases)
    if not args.live:
        print(f"Loaded {len(cases)} Navigator eval case(s). Use --live to call the model.")
        return 0

    from vantage_v5.config import AppConfig
    from vantage_v5.services.navigator import NavigatorService

    config = AppConfig.from_env()
    if not config.openai_api_key:
        print("OPENAI_API_KEY is required for --live Navigator evals.", file=sys.stderr)
        return 2

    navigator = NavigatorService(model=args.model or config.model, openai_api_key=config.openai_api_key)
    results = []
    for case in cases:
        decision = navigator.route_turn(
            user_message=case.message,
            history=case.history,
            workspace=_workspace_from_case(case),
            requested_whiteboard_mode=case.requested_whiteboard_mode,
            pinned_context_id=case.pinned_context_id,
            pinned_context=case.pinned_context,
            pending_workspace_update=case.pending_workspace_update,
            continuity_context=case.continuity_context,
        )
        summary = summarize_navigation_decision(decision)
        results.append(
            evaluate_navigation_summary(
                case,
                summary,
                raw_decision=decision.to_dict(),
            )
        )

    payload = results_payload(results)
    _print_report(payload)
    if args.write_report:
        report_path = _write_report(payload, output_dir=args.output_dir)
        print(f"Wrote report: {report_path}")
    return 0 if payload["failed"] == 0 else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Navigator behavior-summary evals.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="Path to the navigator JSONL case file.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the configured OpenAI model. Without this, the script only validates cases.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override for live evals. Defaults to VANTAGE_V5_MODEL.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write a JSON report under eval_runs/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "eval_runs",
        help="Directory for --write-report output.",
    )
    return parser.parse_args()


def _workspace_from_case(case: NavigatorEvalCase) -> WorkspaceDocument:
    workspace = case.workspace
    workspace_id = str(workspace.get("workspace_id") or "eval-whiteboard")
    title = str(workspace.get("title") or "Eval Whiteboard")
    content = str(workspace.get("content") or "")
    scenario_metadata = workspace.get("scenario_metadata")
    return WorkspaceDocument(
        workspace_id=workspace_id,
        title=title,
        content=content,
        path=Path(f"{workspace_id}.md"),
        scenario_metadata=scenario_metadata if isinstance(scenario_metadata, dict) else None,
    )


def _print_report(payload: dict[str, Any]) -> None:
    print(f"Navigator evals: {payload['passed']} passed, {payload['failed']} failed")
    for result in payload["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status} {result['case_id']}: {result['actual']}")
        for failure in result["failures"]:
            print(f"  - {failure}")


def _write_report(payload: dict[str, Any], *, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"navigator-eval-{timestamp}.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    raise SystemExit(main())
