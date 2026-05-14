from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any

import yaml


ACCOUNT_PASSWORD_ITERATIONS = 310_000
DEFAULT_DEMO_PASSWORD = "vantage-demo-eden"
ACCOUNT_KEY = "eden"
USERNAME = "eden"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> None:
    root = repo_root()
    today = date.today()
    user_root = root / "users" / ACCOUNT_KEY
    ensure_demo_account(root)
    ensure_user_dirs(user_root)

    calendar_payload = demo_calendar(today)
    tasks_payload = demo_tasks(today)
    write_json(user_root / "state" / "calendar" / "events.json", calendar_payload)
    write_json(user_root / "state" / "tasks" / "tasks.json", tasks_payload)

    write_demo_records(user_root, today)
    write_demo_workspace(user_root, today)
    manifest = write_manifest(user_root, today, calendar_payload, tasks_payload)
    write_demo_document(root, today, manifest)

    print(f"Seeded Eden demo account at {user_root}")
    print(f"Demo guide: {root / 'docs' / 'demo' / 'eden-demo-account.md'}")


def ensure_demo_account(root: Path) -> None:
    path = root / "state" / "accounts.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"version": 1, "accounts": {}}
    accounts = payload.setdefault("accounts", {})
    if ACCOUNT_KEY not in accounts:
        accounts[ACCOUNT_KEY] = {
            "username": USERNAME,
            "created_at": datetime.now(tz=UTC).isoformat(),
            "password": make_password_record(DEFAULT_DEMO_PASSWORD),
            "demo_seeded": True,
        }
    write_json(path, payload)


def make_password_record(password: str) -> dict[str, Any]:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        ACCOUNT_PASSWORD_ITERATIONS,
    ).hex()
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": ACCOUNT_PASSWORD_ITERATIONS,
        "salt": salt,
        "hash": password_hash,
    }


def ensure_user_dirs(user_root: Path) -> None:
    for folder in [
        "artifacts",
        "concepts",
        "memories",
        "memory_trace",
        "state/calendar",
        "state/tasks",
        "traces",
        "workspaces",
    ]:
        (user_root / folder).mkdir(parents=True, exist_ok=True)


def demo_calendar(today: date) -> dict[str, Any]:
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    return {
        "calendars": [
            {"id": "school", "title": "School"},
            {"id": "vantage", "title": "Vantage"},
            {"id": "personal", "title": "Personal"},
        ],
        "events": [
            event("morning-reset", "Morning reset + inbox triage", today, time(8, 30), time(9, 0), "personal", "Apartment", "Clear inbox, skim deadlines, pick one must-win outcome."),
            event("linear-algebra-session", "Linear Algebra problem session", today, time(9, 30), time(10, 15), "school", "Library study room B", "Work through practice set before office hours."),
            event("advisor-check-in", "Advisor check-in", today, time(11, 0), time(11, 30), "school", "Zoom", "Discuss midterm prep and project pacing."),
            event("data-structures-lecture", "Data Structures II", today, time(14, 0), time(15, 15), "school", "Building 3, Room 204", "CS 210 lecture: graph traversal review."),
            event("office-hours", "Office Hours with Jordan Lee", today, time(16, 30), time(17, 0), "school", "Zoom", "Ask about Homework 2 edge cases."),
            event("midterm-review-group", "Midterm review group", today, time(19, 0), time(20, 30), "school", "North Library", "Active recall on graph algorithms and runtime analysis."),
            event("vantage-demo-rehearsal", "Vantage demo rehearsal", tomorrow, time(10, 0), time(10, 45), "vantage", "Desk", "Practice Today surface, whiteboard drafting, and Vantage receipt flow."),
            event("morgan-feedback-call", "Morgan feedback call", tomorrow, time(13, 30), time(14, 0), "vantage", "Zoom", "Show the chat-first flow and ask for feedback."),
            event("algorithms-lab", "Algorithms lab", day_after, time(10, 0), time(11, 30), "school", "Lab 2", "Graph implementation drills."),
        ],
    }


def event(
    event_id: str,
    title: str,
    event_date: date,
    start: time,
    end: time,
    calendar_id: str,
    location: str,
    description: str,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "calendar_id": calendar_id,
        "title": title,
        "start": datetime.combine(event_date, start).isoformat(),
        "end": datetime.combine(event_date, end).isoformat(),
        "location": location,
        "description": description,
    }


def demo_tasks(today: date) -> dict[str, Any]:
    return {
        "tasks": [
            task("homework-2", "Finish Homework 2 edge cases", today, "high", "Data Structures II", 90, "Must finish before office hours."),
            task("homework-3", "Draft Homework 3 solution outline", today + timedelta(days=1), "high", "Data Structures II", 75, "Make a clean outline before implementation."),
            task("midterm-review", "Midterm Review: graph algorithms", today + timedelta(days=1), "high", "Midterm", 120, "Active recall, sample problems, then one-page mistake log."),
            task("demo-script", "Practice Vantage demo script", today, "medium", "Vantage", 35, "Show calendar, tasks, whiteboard draft, and Vantage receipt."),
            task("email-morgan", "Send Morgan prototype feedback email", today, "medium", "Vantage", 20, "Use the saved email draft artifact as starting point."),
            task("read-graphs", "Read graph algorithms chapter", None, "low", "Midterm", 60, "Can defer if homework runs long."),
            task("laundry", "Laundry and room reset", None, "low", "Personal", 30, "Nice to have, not a must-win item."),
            {**task("old-lab", "Submit completed lab reflection", today - timedelta(days=1), "medium", "School", 20, "Completed demo hidden from focus."), "status": "done"},
        ],
    }


def task(
    task_id: str,
    title: str,
    due_date: date | None,
    priority: str,
    project: str,
    duration_minutes: int,
    notes: str,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "due_date": due_date.isoformat() if due_date else None,
        "status": "open",
        "priority": priority,
        "project": project,
        "duration_minutes": duration_minutes,
        "notes": notes,
    }


def write_demo_records(user_root: Path, today: date) -> None:
    write_record(
        user_root / "memories" / "eden-prefers-concise-warm-email-drafts.md",
        {
            "id": "eden-prefers-concise-warm-email-drafts",
            "title": "Eden Prefers Concise Warm Email Drafts",
            "type": "memory",
            "card": "Eden likes emails that are concise, warm, specific, and easy for the recipient to say no to.",
            "created_at": today.isoformat(),
            "updated_at": today.isoformat(),
            "links_to": ["email-drafting-protocol"],
            "comes_from": [],
            "status": "active",
        },
        "When drafting emails for Eden, keep the tone warm and human while staying direct. Include a clear ask, a low-pressure opt-out, and sign as Eden unless another signature is requested.",
    )
    write_record(
        user_root / "memories" / "eden-current-academic-focus.md",
        {
            "id": "eden-current-academic-focus",
            "title": "Eden Current Academic Focus",
            "type": "memory",
            "card": "Eden is balancing Data Structures II homework with midterm prep and benefits from concrete time blocks.",
            "created_at": today.isoformat(),
            "updated_at": today.isoformat(),
            "links_to": [],
            "comes_from": [],
            "status": "active",
        },
        "Eden's current school priority is finishing Homework 2, outlining Homework 3, and preparing for a Data Structures midterm focused on graph algorithms and runtime analysis.",
    )
    write_record(
        user_root / "memories" / "eden-vantage-demo-goals.md",
        {
            "id": "eden-vantage-demo-goals",
            "title": "Eden Vantage Demo Goals",
            "type": "memory",
            "card": "The demo should show Vantage as a chat-first context manager that summons the right surface when needed.",
            "created_at": today.isoformat(),
            "updated_at": today.isoformat(),
            "links_to": ["vantage-demo-script"],
            "comes_from": [],
            "status": "active",
        },
        "For demos, emphasize the flow: ask naturally, Vantage pulls calendar/tasks/whiteboard into view, the answer stays concise, and the Vantage receipt explains what context was used and why.",
    )
    write_record(
        user_root / "concepts" / "daily-planning-protocol.md",
        {
            "id": "daily-planning-protocol",
            "title": "Daily Planning Protocol",
            "type": "protocol",
            "card": "Plan the day by honoring hard commitments, selecting must-win tasks, then fitting focus blocks into open calendar windows.",
            "created_at": today.isoformat(),
            "updated_at": today.isoformat(),
            "links_to": [],
            "comes_from": [],
            "status": "active",
            "protocol_kind": "daily_planning",
            "variables": {
                "hard_commitments": "Calendar events and unavailable blocks.",
                "must_win_tasks": "High-priority tasks due today or tomorrow.",
                "energy": "Prefer deep work before late-afternoon commitments when possible.",
            },
            "applies_to": ["planning the day", "study planning", "time blocking"],
            "modifiable": True,
        },
        "\n".join(
            [
                "## Protocol",
                "",
                "1. Read the calendar first and identify hard commitments.",
                "2. Pull tasks into must do today, good next, can defer, and unscheduled groups.",
                "3. Put deep work into the longest open blocks before meetings when possible.",
                "4. End with a fallback plan: the smallest set of tasks that would still make the day a win.",
            ]
        ),
    )
    write_record(
        user_root / "concepts" / "vantage-demo-script.md",
        {
            "id": "vantage-demo-script",
            "title": "Vantage Demo Script",
            "type": "concept",
            "card": "A short demo arc for showing Vantage's chat-first surface invocation and latest-turn receipt.",
            "created_at": today.isoformat(),
            "updated_at": today.isoformat(),
            "links_to": ["eden-vantage-demo-goals"],
            "comes_from": [],
            "status": "active",
        },
        "Start with the empty chat. Ask what the day looks like. Show the Today surface. Ask when to study. Show calendar plus tasks. Ask for an email draft. Show the whiteboard. Click Vantage to explain the latest answer.",
    )
    write_artifacts(user_root, today)


def write_artifacts(user_root: Path, today: date) -> None:
    artifacts = [
        (
            "email-draft-to-morgan-product-feedback",
            "Email Draft to Morgan: Product Feedback",
            "Warm email asking Morgan for feedback on the Vantage prototype demo.",
            "# Email Draft to Morgan: Product Feedback\n\nHi Morgan,\n\nI hope your week is going well. I’m putting together a short Vantage demo and would really value your feedback on whether the flow feels intuitive.\n\nWould you be open to a 20-minute walkthrough tomorrow or early next week? Totally okay if now is not a good time.\n\nBest,\nEden",
        ),
        (
            "email-draft-to-professor-kim-extension-request",
            "Email Draft to Professor Kim: Extension Request",
            "Concise draft asking for a one-day homework extension if needed.",
            "# Email Draft to Professor Kim: Extension Request\n\nHi Professor Kim,\n\nI’m working through the final edge cases on Homework 2 and wanted to ask whether a one-day extension would be possible. I’m still planning to attend office hours and make as much progress as I can today.\n\nIf extensions aren’t available, I understand and will submit what I have by the deadline.\n\nBest,\nEden",
        ),
        (
            "midterm-study-plan",
            "Midterm Study Plan",
            "Study plan for graph algorithms, runtime analysis, and active recall.",
            "# Midterm Study Plan\n\n## Focus Areas\n\n- Graph traversal: BFS, DFS, edge cases, and implementation details.\n- Runtime analysis: explain time and space complexity out loud.\n- Practice: two timed problems, then a mistake log.\n\n## Plan\n\n1. Review lecture notes for 25 minutes.\n2. Solve one graph traversal problem without notes.\n3. Compare against solution and write down mistakes.\n4. Repeat with a runtime-analysis problem.\n5. End with a five-minute recall summary.",
        ),
        (
            "vantage-demo-one-page-brief",
            "Vantage Demo One-Page Brief",
            "One-page narrative for showing Vantage as a chat-first context manager.",
            "# Vantage Demo One-Page Brief\n\nVantage is a chat-first context manager. The user asks naturally, and Vantage summons the right surface only when the request implies an operational domain or durable artifact.\n\n## Demo Beats\n\n- Day planning opens calendar and task context.\n- Email drafting opens a whiteboard artifact.\n- The Vantage receipt explains intent, context used, surfaces opened, and write safety.\n\n## Takeaway\n\nThe product should feel calm until context needs to come into focus.",
        ),
    ]
    for record_id, title, card, body in artifacts:
        write_record(
            user_root / "artifacts" / f"{record_id}.md",
            {
                "id": record_id,
                "title": title,
                "type": "artifact",
                "card": card,
                "created_at": today.isoformat(),
                "updated_at": today.isoformat(),
                "links_to": ["eden-vantage-demo-goals"],
                "comes_from": ["vantage-demo-day-plan"],
                "status": "active",
                "artifact_origin": "demo_seed",
                "artifact_lifecycle": "whiteboard_snapshot",
            },
            body,
        )


def write_demo_workspace(user_root: Path, today: date) -> None:
    workspace_id = "vantage-demo-day-plan"
    write_record(
        user_root / "workspaces" / f"{workspace_id}.md",
        {
            "id": workspace_id,
            "title": "Vantage Demo Day Plan",
            "type": "workspace",
            "card": "Visible whiteboard seed for demoing a day plan, task priorities, and artifact drafting.",
            "created_at": today.isoformat(),
            "updated_at": today.isoformat(),
            "links_to": ["daily-planning-protocol"],
            "comes_from": [],
            "status": "active",
        },
        "# Vantage Demo Day Plan\n\nUse this workspace if you want to show the whiteboard as a durable artifact surface.\n\n## Must Win\n\n- Finish Homework 2 edge cases.\n- Draft Homework 3 outline.\n- Complete a focused midterm review block.\n- Practice the Vantage demo story.\n\n## Demo Arc\n\n1. Ask: “What does my day look like?”\n2. Ask: “When should I study for the midterm?”\n3. Ask: “Draft the Morgan feedback email.”\n4. Click Vantage to show why the answer was generated that way.",
    )
    write_json(
        user_root / "state" / "active_workspace.json",
        {
            "active_workspace_id": workspace_id,
            "active_workspace_path": f"workspaces/{workspace_id}.md",
            "status": "active",
        },
    )


def write_manifest(user_root: Path, today: date, calendar_payload: dict[str, Any], tasks_payload: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "account": USERNAME,
        "seeded_at": datetime.now(tz=UTC).isoformat(),
        "today": today.isoformat(),
        "calendar_event_count": len(calendar_payload["events"]),
        "task_count": len(tasks_payload["tasks"]),
        "paths": {
            "calendar": "users/eden/state/calendar/events.json",
            "tasks": "users/eden/state/tasks/tasks.json",
            "memories": "users/eden/memories/",
            "concepts": "users/eden/concepts/",
            "artifacts": "users/eden/artifacts/",
            "workspace": "users/eden/workspaces/vantage-demo-day-plan.md",
        },
    }
    write_json(user_root / "state" / "demo_manifest.json", manifest)
    return manifest


def write_demo_document(root: Path, today: date, manifest: dict[str, Any]) -> None:
    path = root / "docs" / "demo" / "eden-demo-account.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Eden Demo Account

Seeded by `scripts/seed_eden_demo.py` on {manifest["seeded_at"]}.

## Account

- Username: `eden`
- Password: existing local password is preserved. If the account did not already exist when the seed script was run, it was created with `vantage-demo-eden`.
- Demo date anchor: `{today.isoformat()}`

## Operational Data

- Calendar: `{manifest["paths"]["calendar"]}` with {manifest["calendar_event_count"]} events across school, Vantage, and personal calendars.
- Tasks: `{manifest["paths"]["tasks"]}` with {manifest["task_count"]} tasks, including one completed task hidden from focus.
- Active whiteboard: `{manifest["paths"]["workspace"]}`

## Memories And Context

- `users/eden/memories/eden-prefers-concise-warm-email-drafts.md`
- `users/eden/memories/eden-current-academic-focus.md`
- `users/eden/memories/eden-vantage-demo-goals.md`
- `users/eden/concepts/daily-planning-protocol.md`
- `users/eden/concepts/vantage-demo-script.md`

## Demo Artifacts

- `users/eden/artifacts/email-draft-to-morgan-product-feedback.md`
- `users/eden/artifacts/email-draft-to-professor-kim-extension-request.md`
- `users/eden/artifacts/midterm-study-plan.md`
- `users/eden/artifacts/vantage-demo-one-page-brief.md`

## Suggested Demo Prompts

1. `What does my day look like?`
2. `When should I study for the midterm today?`
3. `Show my to-do list and what I should focus on.`
4. `Draft a warm concise email to Morgan asking for feedback on the Vantage demo.`
5. `Make a study plan for the midterm and put it on the whiteboard.`
6. Click `Vantage` after any answer to show the latest-turn receipt: intent, grounding, context used, surfaces opened, and read/write state.

## What This Demonstrates

- Chat-first default UI.
- Automatic Today surface invocation from day/schedule questions.
- Calendar plus task focus surfaces from planning requests.
- Whiteboard artifact behavior for durable drafts and plans.
- Memory/protocol recall for email and daily planning.
- The Vantage receipt explaining why the latest answer used particular context and surfaces.
"""
    path.write_text(text, encoding="utf-8")


def write_record(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
    path.write_text(f"---\n{frontmatter_text}\n---\n\n{body.strip()}\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
