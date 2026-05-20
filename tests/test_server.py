from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path
import json
import re
import shutil

import pytest
from fastapi.testclient import TestClient

from vantage_v5.config import AppConfig
from vantage_v5.services.artifact_actions import ArtifactActionPlan
from vantage_v5.services.executor import GraphActionExecutor
from vantage_v5.services.meta import MetaDecision
from vantage_v5.services.meta import MetaService
from vantage_v5.services.model_client import MODEL_PROVIDER_CODEX_OAUTH
from vantage_v5.services.model_client import MODEL_PROVIDER_OPENAI
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
from vantage_v5.services.chat import ReplyVerification
from vantage_v5.services.chat import WorkspaceOffer
from vantage_v5.services.protocols import ProtocolInterpretation
from vantage_v5.services.protocols import build_protocol_write_from_interpretation
from vantage_v5.services.scenario_lab import ScenarioBranchPlan
from vantage_v5.services.scenario_lab import ScenarioComparisonPlan
from vantage_v5.services.scenario_lab import ScenarioPlan
from vantage_v5.services.search import CandidateMemory
from vantage_v5.services.semantic_policy import SemanticPolicyDecision
from vantage_v5.services.turn_payloads import ChatTurnBodyParts
from vantage_v5.server import create_app
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _test_repo(tmp_path: Path) -> Path:
    source = _repo_root()
    repo_root = tmp_path / "vantage-v5"
    repo_root.mkdir()
    for folder in ["canonical", "concepts", "memories", "memory_trace", "artifacts", "workspaces", "fixtures"]:
        ignore = shutil.ignore_patterns("launch-strategy*.md") if folder == "workspaces" else None
        shutil.copytree(source / folder, repo_root / folder, ignore=ignore)
    # Build a fresh state directory so tests never inherit a live experiment
    # session, active workspace, or trace files from manual local runs.
    (repo_root / "state").mkdir()
    (repo_root / "traces").mkdir()
    (repo_root / "state" / "index.json").write_text(
        json.dumps(
            {
                "concept_count": 3,
                "workspace_count": 1,
                "last_updated": "2026-04-06",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (repo_root / "state" / "active_workspace.json").write_text(
        json.dumps(
            {
                "active_workspace_id": "v5-milestone-1",
                "active_workspace_path": "workspaces/v5-milestone-1.md",
                "status": "active",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return repo_root


def _client(
    tmp_path: Path,
    *,
    openai_api_key: str | None = None,
    auth_username: str = "vantage",
    auth_password: str | None = None,
    auth_users: dict[str, str] | None = None,
    account_creation_code: str | None = None,
    host: str = "127.0.0.1",
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
    cookie_secure: bool = False,
    allow_unsafe_public_no_auth: bool = False,
    model_provider: str = MODEL_PROVIDER_OPENAI,
    model: str = "gpt-4.1",
    codex_auth_path: Path | None = None,
    codex_base_url: str | None = None,
    calendar_events_path: Path | None = None,
    tasks_path: Path | None = None,
) -> tuple[TestClient, Path]:
    repo_root = _test_repo(tmp_path)
    app = create_app(
        AppConfig(
            repo_root=repo_root,
            openai_api_key=openai_api_key,
            model=model,
            model_provider=model_provider,
            codex_auth_path=codex_auth_path,
            codex_base_url=codex_base_url,
            calendar_events_path=calendar_events_path,
            tasks_path=tasks_path,
            host=host,
            port=8005,
            active_workspace="v5-milestone-1",
            nexus_root=repo_root / "fixtures" / "nexus",
            nexus_include_paths=["allowed"],
            nexus_exclude_paths=["private"],
            auth_username=auth_username,
            auth_password=auth_password,
            auth_users=auth_users or {},
            account_creation_code=account_creation_code,
            allowed_hosts=allowed_hosts or [],
            allowed_origins=allowed_origins or [],
            cookie_secure=cookie_secure,
            allow_unsafe_public_no_auth=allow_unsafe_public_no_auth,
        )
    )
    return TestClient(app), repo_root


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _latest_trace_payload(repo_root: Path) -> dict[str, object]:
    trace_paths = sorted((repo_root / "traces").glob("chat-turn-*.json"))
    if not trace_paths:
        trace_paths = sorted((repo_root / "traces").glob("chat-final-response-*.json"))
    assert trace_paths
    return json.loads(trace_paths[-1].read_text(encoding="utf-8"))


def _today_calendar_artifact() -> dict[str, object]:
    return {
        "id": "today-2026-05-14",
        "kind": "today_briefing",
        "title": "Today",
        "summary": "1 scheduled event.",
        "content": "# Today\n- Advisor check-in | 11:00 AM - 11:30 AM",
        "data": {
            "date": "2026-05-14",
            "calendar": {
                "date": "2026-05-14",
                "events": [
                    {
                        "id": "advisor-check-in",
                        "calendar_id": "school",
                        "title": "Advisor check-in",
                        "start": "2026-05-14T11:00:00",
                        "end": "2026-05-14T11:30:00",
                    }
                ],
                "free_blocks": [],
            },
            "tasks": {"groups": {}, "summary": {}},
            "suggestions": [],
        },
    }


def _task_focus_artifact() -> dict[str, object]:
    return {
        "id": "tasks-2026-05-14",
        "kind": "task_focus",
        "title": "Today Focus",
        "summary": "1 open task.",
        "content": "# Today Focus\n- Finish Homework 2",
        "data": {
            "date": "2026-05-14",
            "tasks": {
                "date": "2026-05-14",
                "groups": {
                    "must_do_today": [
                        {
                            "id": "homework-2",
                            "title": "Finish Homework 2",
                            "due_date": "2026-05-14",
                            "status": "open",
                        }
                    ],
                    "good_next": [],
                    "can_defer": [],
                    "unscheduled": [],
                },
            },
        },
    }


def _fake_jwt(exp: int) -> str:
    def encode(payload: dict[str, object]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode({'exp': exp})}.signature"


def _write_codex_auth(path: Path, *, access_token: str = "codex-access-token") -> Path:
    path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": "codex-refresh-token",
                    "account_id": "account-id-for-tests",
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_calendar_events(path: Path, *, events: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "calendars": [{"id": "school", "title": "School"}],
                "events": events,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_tasks(path: Path, *, tasks: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
    return path


def _fallback_vet_for_tests(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
    vetted = candidates[:4]
    return vetted, {
        "selected_ids": [candidate.id for candidate in vetted],
        "none_relevant": not bool(vetted),
        "rationale": "Test vetting path selected the highest-ranked candidates.",
    }


def _no_relevant_matches_for_tests(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
    return [], {
        "selected_ids": [],
        "none_relevant": True,
        "rationale": "The short follow-up did not match retrieval candidates on its own.",
    }


def _raise_runtime_error_for_tests(*args, **kwargs):
    raise RuntimeError("insufficient_quota")


def _pending_offer_update() -> dict[str, str]:
    return {
        "type": "offer_whiteboard",
        "status": "offered",
        "summary": "Whiteboard ready for collaboratively drafting the thank-you email.",
        "origin_user_message": "Lets draft an email to Judy thanking her for the flowers she dropped off.",
        "origin_assistant_message": "Would you like to pull up a whiteboard so we can write the thank-you email there?",
    }


def _concept_candidate_for_tests(
    *,
    id: str,
    title: str,
    card: str,
    body: str = "",
) -> CandidateMemory:
    return CandidateMemory(
        id=id,
        title=title,
        type="concept",
        card=card,
        score=9.0,
        reason="Test concept match.",
        source="concept",
        trust="high",
        body=body,
    )


def _scenario_navigation(*, confidence: float = 0.92) -> NavigationDecision:
    return NavigationDecision(
        mode="scenario_lab",
        confidence=confidence,
        reason="The turn asks for structured comparison across alternatives.",
        comparison_question="What if we cut milestone 1 scope by 40%?",
        branch_count=3,
        branch_labels=["baseline", "reduced-scope", "fast-launch"],
    )


def _scenario_plan() -> ScenarioPlan:
    return ScenarioPlan(
        comparison_question="What if we cut milestone 1 scope by 40%?",
        shared_context_summary="The current milestone plan balances scope, retrieval quality, and delivery speed.",
        shared_assumptions=[
            "Milestone 1 still needs a coherent chat, workspace, and saved-note loop.",
            "The team wants a visible proof that Vantage is more than generic chat.",
        ],
        branches=[
            ScenarioBranchPlan(
                label="baseline",
                title="Baseline",
                preserved_assumptions=["Keep the current milestone scope intact."],
                changed_assumptions=["No scope reduction is applied."],
                first_order_effects=["Delivery remains broad but slower."],
                second_order_effects=["The demo feels more complete but carries execution risk."],
                risks=["More moving parts can blur the product story."],
                open_questions=["Which proof point matters most for the demo?"],
                confidence="medium",
            ),
            ScenarioBranchPlan(
                label="reduced-scope",
                title="Reduced Scope",
                preserved_assumptions=["Keep the shared workspace as the center of the experience."],
                changed_assumptions=["Cut milestone scope by roughly 40% to focus on Scenario Lab."],
                first_order_effects=["Implementation speed improves."],
                second_order_effects=["The product story becomes sharper and easier to demo."],
                risks=["Some secondary features may feel deferred."],
                open_questions=["Which features move out of milestone 1?"],
                confidence="high",
            ),
            ScenarioBranchPlan(
                label="fast-launch",
                title="Fast Launch",
                preserved_assumptions=["Keep bounded retrieval and saved outputs."],
                changed_assumptions=["Bias toward a fast public-facing proof point."],
                first_order_effects=["The team can show durable branching sooner."],
                second_order_effects=["Technical debt may shift into later polish work."],
                risks=["The UI may need a second pass after launch."],
                open_questions=["How polished does the first demo need to be?"],
                confidence="medium",
            ),
        ],
        comparison=ScenarioComparisonPlan(
            title="Milestone 1 Scenario Comparison",
            summary="Reduced Scope is the strongest first proof because it makes Scenario Lab legible without overloading the milestone.",
            tradeoffs=[
                "Baseline keeps breadth but dilutes the proof point.",
                "Reduced Scope sharpens the story while preserving the core loop.",
                "Fast Launch maximizes speed but increases polish risk.",
            ],
            recommendation="Ship the reduced-scope branch as the milestone centerpiece.",
            next_steps=[
                "Commit to Scenario Lab as the flagship capability.",
                "Defer lower-signal surface area until after the first durable demo.",
            ],
        ),
    )


def _generic_launch_navigation(*, confidence: float = 0.94) -> NavigationDecision:
    return NavigationDecision(
        mode="scenario_lab",
        confidence=confidence,
        reason="The user asked for a structured comparison across launch strategies.",
        comparison_question="Which launch strategy is best for a new software product?",
        branch_count=3,
        branch_labels=["conservative-rollout", "focused-mvp", "aggressive-launch"],
    )


def _generic_launch_plan() -> ScenarioPlan:
    return ScenarioPlan(
        comparison_question="Which launch strategy is best for a new software product?",
        shared_context_summary="A small team needs to balance speed, learning, and risk on a new launch.",
        shared_assumptions=[
            "Time and budget are limited.",
            "The team wants early user feedback without losing credibility.",
        ],
        branches=[
            ScenarioBranchPlan(
                label="conservative-rollout",
                title="Gradual, region- or segment-limited release with controlled feedback loops.",
                card="Lower risk of catastrophic failure.",
                preserved_assumptions=["The product should launch to real users."],
                changed_assumptions=["Release gradually to reduce blast radius."],
                first_order_effects=["Operational risk stays lower."],
                second_order_effects=["Learning is slower but steadier."],
                risks=["Momentum may stall if adoption looks too quiet."],
                open_questions=["Which early segment matters most?"],
                confidence="High for stability, low for fast gains.",
            ),
            ScenarioBranchPlan(
                label="focused-mvp",
                title="Limited-feature release aimed at a target user group for rapid validation.",
                card="Accelerated learning from a real user base.",
                preserved_assumptions=["The team still wants real-world validation."],
                changed_assumptions=["Launch a narrower product to a narrower audience."],
                first_order_effects=["Feedback arrives quickly."],
                second_order_effects=["Scope discipline becomes the main success factor."],
                risks=["The MVP could miss the wrong features."],
                open_questions=["Which user slice is most diagnostic?"],
                confidence="Moderate: balances risk and speed, but rests on the right MVP targeting.",
            ),
            ScenarioBranchPlan(
                label="aggressive-launch",
                title="Full-feature, large-scale market release aiming for maximum visibility and growth from day one.",
                card="Rapid user growth possible.",
                preserved_assumptions=["The team wants a visible market entry."],
                changed_assumptions=["Launch broadly from the start."],
                first_order_effects=["Growth ceiling is highest."],
                second_order_effects=["Reputational and operational pressure rises immediately."],
                risks=["A rough launch could damage trust early."],
                open_questions=["Can support and quality hold at launch scale?"],
                confidence="Moderate for high growth, low for risk containment.",
            ),
        ],
        comparison=ScenarioComparisonPlan(
            title="Launch Strategy: Comparative Analysis",
            summary="Each strategy trades speed, learning, and risk in a different way.",
            tradeoffs=[
                "Conservative rollout reduces exposure but can feel slow.",
                "Focused MVP learns fastest per unit of risk when scoped well.",
                "Aggressive launch maximizes visibility but carries the highest downside.",
            ],
            recommendation="Start with a focused MVP launch, then expand once the core path is validated.",
            next_steps=[
                "Define the narrowest real user segment worth serving first.",
                "Pick the few launch metrics that determine whether to expand.",
            ],
        ),
    )


def _outcome_biased_launch_plan() -> ScenarioPlan:
    plan = _generic_launch_plan()
    plan.comparison = ScenarioComparisonPlan(
        title="Focused MVP Is Best",
        summary=plan.comparison.summary,
        tradeoffs=plan.comparison.tradeoffs,
        recommendation=plan.comparison.recommendation,
        next_steps=plan.comparison.next_steps,
    )
    return plan


def _saved_note_ids(payload: dict[str, Any]) -> set[str]:
    return {str(item.get("id") or "") for item in payload.get("saved_notes", [])}


def _payload_has_key(value: Any, forbidden_key: str) -> bool:
    if isinstance(value, dict):
        return forbidden_key in value or any(_payload_has_key(item, forbidden_key) for item in value.values())
    if isinstance(value, list):
        return any(_payload_has_key(item, forbidden_key) for item in value)
    return False


def test_chat_search_and_concept_inspection(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    workspace = client.get("/api/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == "v5-milestone-1"

    memory = client.get("/api/memory")
    assert memory.status_code == 200
    memory_payload = memory.json()
    assert len(memory_payload["saved_notes"]) >= 1
    assert len(memory_payload["reference_notes"]) == 1
    assert memory_payload["counts"]["total"] >= 2

    concepts = client.get("/api/concepts")
    assert concepts.status_code == 200
    assert len(concepts.json()["concepts"]) >= 1

    search = client.get("/api/concepts/search", params={"query": "shared workspace"})
    assert search.status_code == 200
    assert any(item["id"] == "shared-workspace" for item in search.json()["concepts"])

    vault_notes = client.get("/api/vault-notes")
    assert vault_notes.status_code == 200
    assert len(vault_notes.json()["vault_notes"]) == 1
    assert vault_notes.json()["vault_notes"][0]["path"] == "allowed/project-doc.md"

    vault_search = client.get("/api/vault-notes/search", params={"query": "searchable library"})
    assert vault_search.status_code == 200
    assert len(vault_search.json()["vault_notes"]) == 1
    note_id = vault_search.json()["vault_notes"][0]["id"]

    memory_search = client.get("/api/memory/search", params={"query": "searchable library"})
    assert memory_search.status_code == 200
    memory_search_payload = memory_search.json()
    assert any(item["source"] == "vault_note" for item in memory_search_payload["results"])
    assert len(memory_search_payload["reference_notes"]) == 1

    concept = client.get("/api/concepts/shared-workspace")
    assert concept.status_code == 200
    assert "collaborative Markdown workspace" in concept.json()["body"]

    note = client.get(f"/api/vault-notes/{note_id}")
    assert note.status_code == 200
    assert note.json()["source"] == "vault_note"
    assert note.json()["path"] == "allowed/project-doc.md"

    memory_item = client.get(f"/api/memory/{note_id}")
    assert memory_item.status_code == 200
    assert memory_item.json()["kind"] == "reference_note"
    assert memory_item.json()["item"]["path"] == "allowed/project-doc.md"

    chat = client.post(
        "/api/chat",
        json={
            "message": "How should shared workspace, persistent memory, and the searchable Nexus library fit together?",
            "history": [],
        },
    )
    assert chat.status_code == 200
    payload = chat.json()
    assert "assistant_message" in payload
    assert isinstance(payload["memory"]["saved_notes"], list)
    assert len(payload["memory"]["reference_notes"]) >= 1
    assert "candidate_memory" in payload
    assert isinstance(payload["candidate_memory"]["saved_notes"], list)
    assert isinstance(payload["candidate_memory"]["reference_notes"], list)
    assert len(payload["concept_cards"]) >= 1
    assert "saved_notes" in payload
    assert len(payload["vault_notes"]) >= 1
    assert "candidate_concepts" in payload
    assert "candidate_saved_notes" in payload
    assert "candidate_vault_notes" in payload
    assert "candidate_memory_results" in payload
    assert "recall" in payload
    assert "working_memory" in payload
    assert "attention_recall_role_projection" not in payload
    assert payload["working_memory_view"]["schema"] == "working_memory_view.v1"
    assert payload["recall"] == payload["working_memory"]
    assert isinstance(payload["working_memory"], list)
    assert "response_mode" in payload
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "recall"
    assert payload["response_mode"]["legacy_grounding_mode"] == "working_memory"
    assert payload["response_mode"]["recall_count"] == len(payload["recall"])
    assert payload["response_mode"]["working_memory_count"] == len(payload["working_memory"])
    assert payload["response_mode"]["grounding_sources"] == ["recall"]
    assert payload["response_mode"]["context_sources"] == ["recall"]
    assert payload["response_mode"]["legacy_context_sources"] == ["working_memory"]
    assert payload["response_mode"]["label"] == "Recall"
    assert payload["learned"] == []
    assert payload["created_record"] is None
    assert payload["pinned_context"] is None
    assert payload["pinned_context_id"] is None
    assert payload["selected_record"] is None
    assert payload["selected_record_id"] is None
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "auto"
    assert payload["turn_interpretation"]["control_panel"]["actions"][0]["type"] == "respond"
    assert payload["turn_interpretation"]["control_panel"]["response_call"]["type"] == "chat_response"
    assert payload["semantic_frame"]["target_surface"] == "chat"
    assert payload["semantic_frame"]["task_type"] == "question_answering"
    assert payload["semantic_frame"]["user_goal"] == "Answer the user directly."
    assert payload["workspace"]["context_scope"] == "excluded"
    assert payload["system_state"]["mode"] == payload["mode"]
    assert payload["system_state"]["workspace"]["workspace_id"] == "v5-milestone-1"
    assert "content" not in payload["system_state"]["workspace"]
    assert payload["activity"]["kind"] == "chat"
    assert payload["activity"]["recall_count"] == len(payload["working_memory"])
    assert "vetting" in payload
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["graph_action"] is None
    ids = {concept["id"] for concept in payload["concept_cards"]}
    assert {"shared-workspace", "persistent-memory"} & ids
    assert any(note["source"] == "vault_note" for note in payload["vault_notes"])
    assert any(item["source"] == "concept" for item in payload["working_memory"])
    recalled_item = payload["working_memory"][0]
    assert {"kind", "memory_role", "recall_status", "source_tier"} <= set(recalled_item)
    assert recalled_item["recall_status"] == "recalled"
    final_response = _latest_trace_payload(repo_root)["final_response"]
    role_projection = final_response["attention_recall_role_projection"]
    assert role_projection["schema"] == "attention_recall_role_projection.v1"
    assert role_projection["roles"]["recall_context"]
    assert role_projection["comparison"]["recall_resource_ids"]
    assert not _payload_has_key(role_projection, "content")
    assert not _payload_has_key(role_projection, "body")
    assert all(len(item.get("excerpt") or "") <= 320 for item in role_projection["resources"])
    assert any(
        resource["kind"] == "concept" and "recall_context" in resource["roles"]
        for resource in role_projection["resources"]
    )
    working_memory_view = payload["working_memory_view"]
    assert final_response["working_memory_view"] == working_memory_view
    assert working_memory_view["roles"]["recall_context"]
    assert working_memory_view["execution_summary"]["writes"]["categories"] == ["none"]
    assert not _payload_has_key(working_memory_view, "content")
    assert not _payload_has_key(working_memory_view, "body")
    assert not _payload_has_key(working_memory_view, "raw_prompt")
    assert not _payload_has_key(working_memory_view, "chain_of_thought")
    assert all(len(item.get("excerpt") or "") <= 320 for item in working_memory_view["resources"])
    assert any(
        resource["kind"] == "concept" and "recall_context" in resource["roles"]
        for resource in working_memory_view["resources"]
    )


def test_calendar_day_endpoint_returns_read_only_day_payload(tmp_path: Path) -> None:
    calendar_events_path = _write_calendar_events(
        tmp_path / "calendar" / "events.json",
        events=[
            {
                "id": "homework",
                "calendar_id": "school",
                "title": "Homework block",
                "start": "2026-05-13T13:00:00",
                "end": "2026-05-13T14:00:00",
            },
            {
                "id": "midterm",
                "calendar_id": "school",
                "title": "Midterm study",
                "start": "2026-05-13T16:00:00",
                "end": "2026-05-13T17:30:00",
            },
        ],
    )
    client, _ = _client(tmp_path, calendar_events_path=calendar_events_path)

    response = client.get("/api/calendar/day", params={"date": "2026-05-13"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-05-13"
    assert payload["source"]["configured"] is True
    assert payload["source"]["read_only"] is True
    assert [event["id"] for event in payload["events"]] == ["homework", "midterm"]
    assert payload["summary"]["event_count"] == 2
    assert payload["summary"]["free_block_count"] == 3


def test_calendar_week_endpoint_returns_read_only_week_payload(tmp_path: Path) -> None:
    calendar_events_path = _write_calendar_events(
        tmp_path / "calendar" / "events.json",
        events=[
            {
                "id": "monday",
                "calendar_id": "school",
                "title": "Monday lab",
                "start": "2026-05-11T10:00:00",
                "end": "2026-05-11T11:00:00",
            },
            {
                "id": "wednesday",
                "calendar_id": "school",
                "title": "Wednesday lecture",
                "start": "2026-05-13T14:00:00",
                "end": "2026-05-13T15:00:00",
            },
            {
                "id": "next-week",
                "calendar_id": "school",
                "title": "Next week",
                "start": "2026-05-18T09:00:00",
                "end": "2026-05-18T10:00:00",
            },
        ],
    )
    client, _ = _client(tmp_path, calendar_events_path=calendar_events_path)

    response = client.get("/api/calendar/week", params={"date": "2026-05-13"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["start_date"] == "2026-05-11"
    assert payload["end_date"] == "2026-05-17"
    assert payload["source"]["configured"] is True
    assert payload["source"]["read_only"] is True
    assert payload["summary"]["day_count"] == 7
    assert payload["summary"]["event_count"] == 2
    assert [event["id"] for event in payload["days"][0]["events"]] == ["monday"]
    assert [event["id"] for event in payload["days"][2]["events"]] == ["wednesday"]


def test_calendar_day_endpoint_requires_auth_when_profiles_are_enabled(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, auth_users={"eden": "eden-password"})

    blocked = client.get("/api/calendar/day", params={"date": "2026-05-13"})
    assert blocked.status_code == 401

    login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})
    assert login.status_code == 200
    allowed = client.get("/api/calendar/day", params={"date": "2026-05-13"})
    assert allowed.status_code == 200
    allowed_week = client.get("/api/calendar/week", params={"date": "2026-05-13"})
    assert allowed_week.status_code == 200


def test_calendar_day_endpoint_rejects_unknown_date_phrase(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/api/calendar/day", params={"date": "next month"})

    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.json()["detail"]

    week_response = client.get("/api/calendar/week", params={"date": "next month"})
    assert week_response.status_code == 400
    assert "YYYY-MM-DD" in week_response.json()["detail"]


def test_task_focus_endpoint_returns_grouped_read_only_tasks(tmp_path: Path) -> None:
    tasks_path = _write_tasks(
        tmp_path / "tasks" / "tasks.json",
        tasks=[
            {"id": "homework-2", "title": "Homework 2", "due_date": "2026-05-13", "priority": "high"},
            {"id": "problem-set-3", "title": "Problem Set 3", "due_date": "2026-05-14", "priority": "normal"},
            {"id": "reading", "title": "Read graph algorithms", "priority": "low"},
            {"id": "done", "title": "Already done", "status": "completed"},
        ],
    )
    client, _ = _client(tmp_path, tasks_path=tasks_path)

    response = client.get("/api/tasks/focus", params={"date": "2026-05-13"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-05-13"
    assert payload["source"]["configured"] is True
    assert payload["source"]["read_only"] is True
    assert [task["id"] for task in payload["groups"]["must_do_today"]] == ["homework-2"]
    assert [task["id"] for task in payload["groups"]["good_next"]] == ["problem-set-3"]
    assert [task["id"] for task in payload["groups"]["can_defer"]] == ["reading"]
    assert payload["summary"]["task_count"] == 3


def test_task_focus_endpoint_requires_auth_when_profiles_are_enabled(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, auth_users={"eden": "eden-password"})

    blocked = client.get("/api/tasks/focus", params={"date": "2026-05-13"})
    assert blocked.status_code == 401

    login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})
    assert login.status_code == 200
    allowed = client.get("/api/tasks/focus", params={"date": "2026-05-13"})
    assert allowed.status_code == 200


def test_calendar_and_tasks_use_user_scoped_demo_files_when_profiles_are_enabled(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password", "sam": "sam-password"})
    _write_calendar_events(
        repo_root / "users" / "eden" / "state" / "calendar" / "events.json",
        events=[
            {
                "id": "eden-demo",
                "calendar_id": "school",
                "title": "Eden demo review",
                "start": "2026-05-13T10:00:00",
                "end": "2026-05-13T11:00:00",
            }
        ],
    )
    _write_tasks(
        repo_root / "users" / "eden" / "state" / "tasks" / "tasks.json",
        tasks=[{"id": "eden-homework", "title": "Eden homework", "due_date": "2026-05-13", "priority": "high"}],
    )

    eden_headers = _basic_auth_header("eden", "eden-password")
    sam_headers = _basic_auth_header("sam", "sam-password")

    eden_calendar = client.get("/api/calendar/day", params={"date": "2026-05-13"}, headers=eden_headers)
    sam_calendar = client.get("/api/calendar/day", params={"date": "2026-05-13"}, headers=sam_headers)
    eden_tasks = client.get("/api/tasks/focus", params={"date": "2026-05-13"}, headers=eden_headers)
    sam_tasks = client.get("/api/tasks/focus", params={"date": "2026-05-13"}, headers=sam_headers)

    assert eden_calendar.status_code == 200
    assert sam_calendar.status_code == 200
    assert eden_tasks.status_code == 200
    assert sam_tasks.status_code == 200
    assert eden_calendar.json()["summary"]["event_count"] == 1
    assert sam_calendar.json()["summary"]["event_count"] == 0
    assert eden_tasks.json()["summary"]["must_do_today_count"] == 1
    assert sam_tasks.json()["summary"]["task_count"] == 0


def test_chat_attaches_today_briefing_surface_for_day_planning(tmp_path: Path) -> None:
    calendar_events_path = _write_calendar_events(
        tmp_path / "calendar" / "events.json",
        events=[
            {
                "id": "lecture",
                "calendar_id": "school",
                "title": "Data Structures II",
                "start": "2026-05-13T14:00:00",
                "end": "2026-05-13T15:00:00",
            },
        ],
    )
    tasks_path = _write_tasks(
        tmp_path / "tasks" / "tasks.json",
        tasks=[
            {"id": "homework-2", "title": "Homework 2", "due_date": "2026-05-13", "priority": "high"},
            {"id": "midterm-review", "title": "Midterm Review", "priority": "high", "duration_minutes": 90},
        ],
    )
    client, repo_root = _client(tmp_path, calendar_events_path=calendar_events_path, tasks_path=tasks_path)

    response = client.post(
        "/api/chat",
        json={
            "message": "Tell me about what I have planned for today on 2026-05-13.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["primary_surface"] == "calendar_day"
    assert payload["active_surface_id"] == "today-2026-05-13"
    assert [surface["kind"] for surface in payload["surface_payloads"]] == ["today_briefing"]
    surface = payload["surface_payloads"][0]
    assert surface["data"]["calendar"]["summary"]["event_count"] == 1
    assert surface["data"]["tasks"]["summary"]["must_do_today_count"] == 2
    assert surface["data"]["suggestions"]

    trace_payload = _latest_trace_payload(repo_root)
    final_response = trace_payload["final_response"]
    assert final_response["user_message"] == "Tell me about what I have planned for today on 2026-05-13."
    assert final_response["active_surface_id"] == payload["active_surface_id"]
    assert final_response["surface_payloads"] == payload["surface_payloads"]
    assert final_response["surface_invocation"] == payload["surface_invocation"]
    assert final_response["turn_plan"]["ui_surface_action"]["surface"] == "calendar_day"
    assert final_response["turn_plan"]["execution"]["surface_payload_policy"] == "build_operational_payload"
    assert final_response["turn_plan"]["validation"]["status"] == "ok"


def test_chat_attaches_task_focus_surface_for_task_only_prompt(tmp_path: Path) -> None:
    tasks_path = _write_tasks(
        tmp_path / "tasks" / "tasks.json",
        tasks=[
            {"id": "problem-set-3", "title": "Problem Set 3", "due_date": "2026-05-14"},
        ],
    )
    client, _ = _client(tmp_path, tasks_path=tasks_path)

    response = client.post(
        "/api/chat",
        json={"message": "Show my to-do list and what I should focus on.", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_surface_id"].startswith("tasks-")
    assert [surface["kind"] for surface in payload["surface_payloads"]] == ["task_focus"]


def test_chat_attaches_task_focus_surface_for_priority_lookup(tmp_path: Path) -> None:
    tasks_path = _write_tasks(
        tmp_path / "tasks" / "tasks.json",
        tasks=[
            {"id": "midterm-review", "title": "Review graphs", "priority": "high"},
        ],
    )
    client, _ = _client(tmp_path, tasks_path=tasks_path)

    response = client.post(
        "/api/chat",
        json={"message": "Show my priorities.", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_surface_id"].startswith("tasks-")
    assert [surface["kind"] for surface in payload["surface_payloads"]] == ["task_focus"]


def test_chat_attaches_calendar_week_surface_for_week_prompt(tmp_path: Path) -> None:
    calendar_events_path = _write_calendar_events(
        tmp_path / "calendar" / "events.json",
        events=[
            {
                "id": "lab",
                "calendar_id": "school",
                "title": "Algorithms lab",
                "start": "2026-05-11T10:00:00",
                "end": "2026-05-11T11:00:00",
            },
        ],
    )
    client, _ = _client(tmp_path, calendar_events_path=calendar_events_path)

    response = client.post(
        "/api/chat",
        json={"message": "Show me my calendar for this week on 2026-05-13.", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["primary_surface"] == "calendar_week"
    assert payload["active_surface_id"] == "calendar-week-2026-05-11"
    assert [surface["kind"] for surface in payload["surface_payloads"]] == ["calendar_week"]
    assert payload["surface_payloads"][0]["data"]["calendar_week"]["summary"]["event_count"] == 1
    assert "opened your week calendar" in payload["assistant_message"]
    assert "Algorithms lab" in payload["assistant_message"]


def test_chat_payload_exposes_app_capability_manifest(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, auth_users={"eden": "eden-password"})

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={"message": "what is on my calendar today?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    manifest = payload["app_capabilities"]
    assert manifest["policy_version"] == "app-capability-v1"
    assert [app["id"] for app in manifest["apps"]] == ["calendar", "tasks", "whiteboard"]
    assert next(tool for tool in manifest["tools"] if tool["name"] == "calendar.create_event")["status"] == "available"
    assert payload["system_state"]["app_capabilities"]["policy_version"] == "app-capability-v1"
    assert "calendar.create_event" in payload["system_state"]["available_tools"]


def test_chat_payload_exposes_attention_selection_for_calendar_context(tmp_path: Path) -> None:
    calendar_events_path = _write_calendar_events(
        tmp_path / "calendar" / "events.json",
        events=[
            {
                "id": "midterm",
                "calendar_id": "school",
                "title": "Data Structures Midterm",
                "start": "2026-05-13T10:00:00",
                "end": "2026-05-13T11:30:00",
            }
        ],
    )
    client, _ = _client(tmp_path, calendar_events_path=calendar_events_path)

    response = client.post(
        "/api/chat",
        json={"message": "What is on my calendar today on 2026-05-13?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "calendar" in payload["query_frame"]["domains"]
    assert any(candidate["kind"] == "calendar_day" for candidate in payload["attention_candidates"])
    assert payload["navigator_selection"]["selected_ids"]
    assert payload["selected_attention_resources"][0]["kind"] == "calendar_day"
    assert "Data Structures Midterm" in payload["selected_attention_resources"][0]["content"]
    assert payload["system_state"]["navigator_selection"]["fallback"] is True


def test_chat_model_path_receives_visible_artifacts_from_current_view(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifacts = [
        {
            "id": "calendar-week-2026-05-11",
            "kind": "calendar_week",
            "title": "Week",
            "summary": "1 scheduled event this week.",
            "content": "# Calendar Week\n- Algorithms lab",
            "data": {
                "calendar_week": {
                    "start_date": "2026-05-11",
                    "end_date": "2026-05-17",
                }
            },
        }
    ]
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        captured["navigator_visible"] = kwargs["visible_artifacts"]
        captured["navigator_attention"] = kwargs["attention_candidates"]
        return NavigationDecision(
            mode="chat",
            confidence=0.93,
            reason="The visible calendar is relevant current-view context.",
            whiteboard_mode="chat",
        )

    def _interpret(self, **kwargs):
        captured["protocol_visible"] = kwargs["visible_artifacts"]
        return ProtocolInterpretation(rationale="No protocol action.")

    def _vet(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
        captured["vetting_visible"] = visible_artifacts
        return [], {
            "selected_ids": [],
            "none_relevant": True,
            "rationale": "Visible artifacts supplied current-view context.",
        }

    def _reply(self, **kwargs):
        captured["reply_visible"] = kwargs["visible_artifacts"]
        captured["reply_selected_attention"] = kwargs["selected_attention_resources"]
        captured["reply_app_capabilities"] = kwargs["app_capabilities"]
        return "I see the current week calendar with Algorithms lab."

    def _decide(self, **kwargs):
        captured["meta_visible"] = kwargs["visible_artifacts"]
        return MetaDecision(action="no_op", rationale="Visible context was read-only.")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.protocols.ProtocolInterpreter.interpret", _interpret)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _vet)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr("vantage_v5.services.meta.MetaService.decide", _decide)

    response = client.post(
        "/api/chat",
        json={
            "message": "What am I looking at this week?",
            "history": [],
            "whiteboard_mode": "chat",
            "visible_artifacts": visible_artifacts,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I see the current week calendar with Algorithms lab."
    assert payload["visible_artifacts"][0]["id"] == "calendar-week-2026-05-11"
    assert "Algorithms lab" in payload["visible_artifacts"][0]["content"]
    assert payload["attention_candidates"]
    assert payload["navigator_selection"]["fallback"] is True
    assert payload["selected_attention_resources"][0]["resource_id"] == "visible:calendar-week-2026-05-11"
    assert captured["navigator_attention"][0]["resource_id"] == "visible:calendar-week-2026-05-11"
    assert captured["reply_selected_attention"][0]["resource_id"] == "visible:calendar-week-2026-05-11"
    for key in ["navigator_visible", "protocol_visible", "vetting_visible", "reply_visible", "meta_visible"]:
        assert captured[key][0]["id"] == "calendar-week-2026-05-11"
        assert "Algorithms lab" in captured[key][0]["content"]
    assert captured["reply_app_capabilities"]["policy_version"] == "app-capability-v1"
    assert "calendar.read_week" in {tool["name"] for tool in captured["reply_app_capabilities"]["tools"]}
    final_response = _latest_trace_payload(repo_root)["final_response"]
    role_projection = final_response["attention_recall_role_projection"]
    visible_resource = next(
        resource
        for resource in role_projection["resources"]
        if resource["resource_id"] == "visible:calendar-week-2026-05-11"
    )
    assert visible_resource["flags"]["visible"] is True
    assert visible_resource["flags"]["selected"] is True
    assert "answer_context" in visible_resource["roles"]
    assert "current_visible_context" in visible_resource["origins"]
    assert "attention_selection" in visible_resource["origins"]
    working_memory_view = payload["working_memory_view"]
    assert final_response["working_memory_view"] == working_memory_view
    visible_working_memory_resource = next(
        resource
        for resource in working_memory_view["resources"]
        if resource["resource_id"] == "visible:calendar-week-2026-05-11"
    )
    assert visible_working_memory_resource["flags"]["visible"] is True
    assert visible_working_memory_resource["flags"]["selected"] is True
    assert "answer_context" in visible_working_memory_resource["roles"]
    assert len(visible_working_memory_resource.get("excerpt") or "") <= 320


@pytest.mark.parametrize(
    "message",
    [
        "What should I do first from this study plan?",
        "Can you summarize this study plan?",
        "Can you explain this study plan?",
        "What are the key points in this study plan?",
        "Summarize it.",
        "Explain the open artifact.",
    ],
)
def test_visible_whiteboard_follow_up_answers_in_chat_without_saving_derivative_artifact(
    tmp_path: Path,
    monkeypatch,
    message: str,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifacts = [
        {
            "id": "artifact:midterm-study-plan",
            "kind": "whiteboard",
            "title": "Midterm Study Plan",
            "summary": "Study plan for graph algorithms and priorities.",
            "content": (
                "# Midterm Study Plan\n\n"
                "## Focus Areas\n\n"
                "- Graph traversal: BFS, DFS, edge cases, and implementation details.\n"
                "- Runtime analysis: explain time and space complexity out loud.\n"
                "- Practice: two timed problems, then a mistake log.\n\n"
                "## Plan\n\n"
                "1. Review lecture notes for 25 minutes.\n"
                "2. Solve one graph traversal problem without notes.\n"
                "3. Compare against solution and write down mistakes.\n"
            ),
        }
    ]
    artifact_ids_before = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    concept_ids_before = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The model misread the visible study-plan follow-up as a whiteboard draft.",
            whiteboard_mode="draft",
        )

    def _reply(self, **kwargs):
        captured["whiteboard_mode"] = kwargs["whiteboard_mode"]
        captured["visible_artifacts"] = kwargs["visible_artifacts"]
        return "Start with one graph traversal problem without notes, then compare and log mistakes."

    def _unexpected_meta_write(self, **kwargs):
        raise AssertionError("Visible artifact Q&A should not ask meta to create durable graph records.")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr("vantage_v5.services.meta.MetaService.decide", _unexpected_meta_write)
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Visible artifact Q&A should not compile artifact actions.")
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": message,
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifacts[0]["content"],
            "visible_artifacts": visible_artifacts,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"].startswith("Start with one graph traversal problem")
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert payload["visible_artifacts"][0]["id"] == "artifact:midterm-study-plan"
    assert "Midterm Study Plan" in payload["visible_artifacts"][0]["content"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "chat"
    assert payload["surface_invocation"]["intent"] == "current_artifact_followup"
    assert payload["surface_invocation"]["primary_surface"] == "chat"
    assert payload["surface_invocation"]["write_behavior"] == "none"
    assert captured["whiteboard_mode"] == "chat"
    assert captured["visible_artifacts"][0]["id"] == "artifact:midterm-study-plan"
    artifact_ids_after = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    assert artifact_ids_after == artifact_ids_before
    assert not any(artifact_id.startswith("first-action-from-midterm-study-plan") for artifact_id in artifact_ids_after)
    concept_ids_after = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    assert concept_ids_after == concept_ids_before
    assert "active-study-cycle-for-algorithm-exam-preparation" not in concept_ids_after
    final_response = _latest_trace_payload(repo_root)["final_response"]
    turn_plan_execution = final_response["turn_plan"]["execution"]
    assert turn_plan_execution["suppress_auto_graph_writes"] is True
    assert turn_plan_execution["artifact_action_policy"] == "disabled"
    assert final_response["turn_plan"]["side_effect_policy"]["suppress_auto_graph_writes_reason"] == (
        "artifact_qna_chat_first"
    )
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_visible_whiteboard_follow_up_with_memory_intent_remember_is_not_suppressed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifacts = [
        {
            "id": "artifact:midterm-study-plan",
            "kind": "whiteboard",
            "title": "Midterm Study Plan",
            "summary": "Study plan for graph algorithms and priorities.",
            "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
        }
    ]
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Visible study plan follow-up.",
            whiteboard_mode="draft",
        )

    def _reply(self, **kwargs):
        return "Start with graph traversal practice."

    def _decide(self, **kwargs):
        captured["memory_mode"] = kwargs["memory_mode"]
        captured["visible_artifacts"] = kwargs["visible_artifacts"]
        return MetaDecision(
            action="create_memory",
            title="Study plan first step",
            card="Start with graph traversal practice.",
            body="The visible Midterm Study Plan says to start with graph traversal practice.",
            rationale="The user explicitly asked Vantage to remember this.",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr("vantage_v5.services.meta.MetaService.decide", _decide)
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        lambda self, **kwargs: ArtifactActionPlan(artifact_actions=[]),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Can you summarize this study plan? Remember the first step.",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifacts[0]["content"],
            "visible_artifacts": visible_artifacts,
            "memory_intent": "remember",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured["memory_mode"] == "remember"
    assert captured["visible_artifacts"][0]["id"] == "artifact:midterm-study-plan"
    assert payload["surface_invocation"]["intent"] == "current_artifact_followup"
    assert payload["created_record"]["source"] == "memory"
    assert payload["graph_action"]["type"] == "create_memory"
    assert (repo_root / "memories" / f"{payload['created_record']['id']}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["side_effect_policy"]["suppress_auto_graph_writes_reason"] is None
    assert final_response["turn_plan"]["execution"]["suppress_auto_graph_writes"] is False
    assert final_response["turn_plan"]["memory_write_authority"]["action"] == "memory_write"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is True
    assert final_response["turn_plan"]["memory_write_authority"]["authority"] == "memory_intent"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_close_visible_whiteboard_returns_close_action_without_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Study plan for graph algorithms and priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
    )
    visible_artifacts = [
        {
            "id": artifact.id,
            "kind": "whiteboard",
            "title": artifact.title,
            "summary": artifact.card,
            "content": artifact.body,
        }
    ]

    def _reply_should_not_run(self, **kwargs):
        raise AssertionError("Close visible surface should be handled before ChatService.reply().")

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "protocol_kind": None,
                        "target": "whiteboard",
                        "reason": "The user asked to close the visible whiteboard.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "close the whiteboard",
            "history": [],
            "workspace_id": artifact.id,
            "workspace_scope": "visible",
            "workspace_content": artifact.body,
            "visible_artifacts": visible_artifacts,
            "pinned_context_id": f"artifact:{artifact.id}",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Closed Midterm Study Plan from view."
    assert payload["surface_action"] == {
        "type": "close_visible_surface",
        "status": "requested",
        "target": "whiteboard",
        "target_id": artifact.id,
        "target_kind": "whiteboard",
        "title": "Midterm Study Plan",
        "reason": "The user asked to close the visible whiteboard.",
    }
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert payload["surface_payloads"] == []
    assert payload["pinned_context_id"] == f"artifact:{artifact.id}"
    assert (repo_root / "artifacts" / f"{artifact.id}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["ui_surface_action"]["mode"] == "close"
    assert final_response["turn_plan"]["ui_surface_action"]["surface"] == "whiteboard"
    assert final_response["turn_plan"]["execution"]["artifact_action_policy"] == "disabled"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_close_visible_today_returns_close_action_without_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    def _reply_should_not_run(self, **kwargs):
        raise AssertionError("Close visible surface should be handled before ChatService.reply().")

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "protocol_kind": None,
                        "target": "calendar",
                        "reason": "The user asked to close the visible calendar.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "close the calendar",
            "history": [],
            "visible_artifacts": [_today_calendar_artifact()],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Closed Today from view."
    assert payload["surface_action"]["target"] == "calendar"
    assert payload["surface_action"]["target_kind"] == "today_briefing"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["ui_surface_action"]["mode"] == "close"
    assert final_response["turn_plan"]["ui_surface_action"]["target_resource_kind"] == "today_briefing"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_close_visible_surface_with_no_surface_is_safe_noop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    def _reply_should_not_run(self, **kwargs):
        raise AssertionError("Close visible surface no-op should be handled before ChatService.reply().")

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "protocol_kind": None,
                        "target": "whiteboard",
                        "reason": "The user asked to close the visible whiteboard.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={"message": "close the whiteboard", "history": [], "visible_artifacts": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I don't see a visible surface to close."
    assert payload["surface_action"]["status"] == "no_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []


@pytest.mark.parametrize(
    "message",
    [
        "don't close the whiteboard",
        "do not close this artifact",
        "don't hide the study plan",
        "please don't remove today from view",
        "keep the whiteboard open",
        "leave the calendar open",
    ],
)
def test_chat_negated_close_text_without_control_action_does_not_close(
    tmp_path: Path,
    monkeypatch,
    message: str,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Study plan for graph algorithms and priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
    )
    visible_artifacts = [
        {
            "id": artifact.id,
            "kind": "whiteboard",
            "title": artifact.title,
            "summary": artifact.card,
            "content": artifact.body,
        }
    ]
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.84,
            reason="Navigator chose ordinary chat and did not press close_surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "respond",
                        "protocol_kind": None,
                        "reason": "The user did not ask to close the visible surface.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    def _reply(self, **kwargs):
        captured["visible_artifacts"] = kwargs["visible_artifacts"]
        return "Okay, I'll keep it open."

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        lambda self, **kwargs: ArtifactActionPlan(artifact_actions=[]),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="No write requested."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": message,
            "history": [],
            "workspace_id": artifact.id,
            "workspace_scope": "visible",
            "workspace_content": artifact.body,
            "visible_artifacts": visible_artifacts,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("surface_action") is None
    assert payload["surface_invocation"]["intent"] != "close_visible_surface"
    assert payload["surface_invocation"]["primary_surface"] == "chat"
    assert payload["surface_invocation"]["write_behavior"] != "open_only"
    assert payload["active_surface_id"] is None
    assert payload["surface_payloads"] == []
    navigator_selection = payload.get("navigator_selection")
    assert navigator_selection is None or navigator_selection.get("surface_to_open") is None
    control_actions = payload["turn_interpretation"]["control_panel"]["actions"]
    assert all(action["type"] != "open_whiteboard" for action in control_actions)
    assert all(action["type"] != "close_surface" for action in control_actions)
    assert any(action["type"] == "preserve_surface" for action in control_actions)
    assert payload["visible_artifacts"][0]["id"] == artifact.id
    assert captured["visible_artifacts"][0]["id"] == artifact.id
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert (repo_root / "artifacts" / f"{artifact.id}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["ui_surface_action"]["mode"] == "preserve"
    assert final_response["turn_plan"]["execution"]["artifact_action_policy"] == "disabled"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_preserve_calendar_open_does_not_foreground_calendar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    unrelated = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Vantage Demo One-Page Brief",
        card="A demo brief that should remain context only.",
        body="# Vantage Demo One-Page Brief\n\nThis should not replace the visible surface.",
    )
    visible_today = _today_calendar_artifact()
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.88,
            reason="Navigator interpreted a keep-open request for the visible calendar.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "protocol_kind": None,
                        "target": "calendar",
                        "reason": "The user asked to leave the visible calendar open.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
            attention_selection={
                "selected_ids": [f"artifact:{unrelated.id}"],
                "primary_resource_id": f"artifact:{unrelated.id}",
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": "whiteboard",
                "reason": "This artifact is unrelated context and must not open during preserve.",
                "confidence": 0.8,
            },
        )

    def _reply(self, **kwargs):
        captured["visible_artifacts"] = kwargs["visible_artifacts"]
        return "I'll leave it open."

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(AssertionError("Preserve turns should suppress graph writes.")),
    )
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        lambda self, **kwargs: (_ for _ in ()).throw(AssertionError("Preserve turns should skip artifact mutations.")),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "leave the calendar open",
            "history": [],
            "visible_artifacts": [visible_today],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("surface_action") is None
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["surface_invocation"]["primary_surface"] == "chat"
    assert payload["surface_invocation"]["write_behavior"] == "none"
    assert payload["navigator_selection"]["surface_to_open"] is None
    assert payload["active_surface_id"] is None
    assert payload["surface_payloads"] == []
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert payload["visible_artifacts"][0]["id"] == visible_today["id"]
    assert captured["visible_artifacts"][0]["id"] == visible_today["id"]
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["ui_surface_action"]["mode"] == "preserve"
    assert final_response["turn_plan"]["ui_surface_action"]["target_resource_kind"] == "calendar"
    assert final_response["turn_plan"]["execution"]["surface_payload_policy"] == "none"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_preserve_surface_blocks_local_semantic_artifact_publish(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
        "summary": "Study plan for graph algorithms and priorities.",
        "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
    }

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose preserve-visible-surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to keep the current whiteboard open.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.turn_orchestrator.decide_semantic_policy",
        lambda *args, **kwargs: SemanticPolicyDecision(
            action_type="artifact_publish",
            should_clarify=False,
            reason="Synthetic local publish policy for no-write regression coverage.",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I'll keep the whiteboard open.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Preserve turns should suppress generic graph writes.")
        ),
    )

    artifact_ids_before = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    memory_ids_before = {path.stem for path in (repo_root / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "leave the study plan open and publish this artifact",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifact["content"],
            "visible_artifacts": [visible_artifact],
            "memory_intent": "remember",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert {path.stem for path in (repo_root / "artifacts").glob("*.md")} == artifact_ids_before
    assert {path.stem for path in (repo_root / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["execution"]["local_semantic_write_policy"] == "disabled"
    assert final_response["turn_plan"]["artifact_write_authority"]["action"] == "artifact_publish"
    assert final_response["turn_plan"]["artifact_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["artifact_write_authority"]["denied_reason"] == "preserve_visible_surface"
    assert final_response["turn_plan"]["memory_write_authority"]["action"] == "memory_write"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["memory_write_authority"]["denied_reason"] == "preserve_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_preserve_surface_denied_save_receipt_does_not_claim_saved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
        "summary": "Study plan for graph algorithms and priorities.",
        "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
    }

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose preserve-visible-surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to keep the current whiteboard open.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.turn_orchestrator.decide_semantic_policy",
        lambda *args, **kwargs: SemanticPolicyDecision(
            action_type="artifact_save",
            should_clarify=False,
            reason="Synthetic local save policy for mixed preserve/save receipt coverage.",
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService.reply",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Denied mixed preserve/save turns should not ask chat to write the receipt.")
        ),
    )

    artifact_ids_before = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "keep the whiteboard open and save this whiteboard",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifact["content"],
            "visible_artifacts": [visible_artifact],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I kept the whiteboard open. I did not save it."
    assert "saved" not in payload["assistant_message"].lower()
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert {path.stem for path in (repo_root / "artifacts").glob("*.md")} == artifact_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["artifact_write_authority"]["action"] == "artifact_save"
    assert final_response["turn_plan"]["artifact_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["artifact_write_authority"]["denied_reason"] == "preserve_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_preserve_surface_blocks_whiteboard_draft_signal_without_claiming_draft(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
        "summary": "Study plan for graph algorithms and priorities.",
        "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
    }

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose preserve-visible-surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to keep the current whiteboard open.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    def _reply(self, **kwargs):
        return (
            "CHAT_RESPONSE: I drafted that in the whiteboard.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Blocked Draft\n\n"
            "This should never become a pending draft."
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Preserve turns should suppress automatic graph writes.")
        ),
    )

    artifact_ids_before = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "keep the whiteboard open and draft this in the whiteboard",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifact["content"],
            "visible_artifacts": [visible_artifact],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert "drafted" not in payload["assistant_message"].lower()
    assert "did not create" in payload["assistant_message"].lower()
    assert {path.stem for path in (repo_root / "artifacts").glob("*.md")} == artifact_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "preserve_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_save_whiteboard_accepts_camel_case_visible_workspace_payload(
    tmp_path: Path,
) -> None:
    client, repo_root = _client(tmp_path)
    content = "# API Visible Save Target\n\nThe live whiteboard buffer is the save target."
    artifact_path = repo_root / "artifacts" / "api-visible-save-target.md"
    artifact_path.unlink(missing_ok=True)

    response = client.post(
        "/api/chat",
        json={
            "message": "Save this whiteboard",
            "history": [],
            "workspaceId": "api-visible-save-target",
            "workspaceScope": "visible",
            "workspaceContent": content,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I saved API Visible Save Target as a whiteboard snapshot."
    assert payload["workspace"]["context_scope"] == "visible"
    assert payload["semantic_policy"]["action_type"] == "artifact_save"
    assert payload["semantic_policy"]["should_clarify"] is False
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["created_record"]["id"] == "api-visible-save-target"
    assert artifact_path.exists()
    assert "The live whiteboard buffer is the save target." in artifact_path.read_text(encoding="utf-8")


def test_preserve_surface_denied_concept_receipt_does_not_claim_learned(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    content = "# Midterm Study Plan\n\nPractice graph traversal first."

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose preserve-visible-surface plus concept intent.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to keep the current whiteboard open.",
                    },
                    {
                        "type": "learn",
                        "target": "concept",
                        "reason": "The user also asked to learn this as a concept.",
                    },
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService.reply",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Denied mixed preserve/concept turns should not ask chat to write the receipt.")
        ),
    )

    concept_ids_before = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "keep the whiteboard open and learn this as a concept: DFS uses a stack or recursion.",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": content,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I kept the whiteboard open. I did not learn it as a concept."
    assert "treat this as a concept" not in payload["assistant_message"].lower()
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert {path.stem for path in (repo_root / "concepts").glob("*.md")} == concept_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["concept_write_authority"]["action"] == "concept_write"
    assert final_response["turn_plan"]["concept_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["concept_write_authority"]["denied_reason"] == "preserve_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_close_visible_workspace_with_concept_intent_closes_and_denies_concept(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    content = "# Midterm Study Plan\n\nPractice graph traversal first."

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose close-visible-surface plus concept intent.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to close the current whiteboard.",
                    },
                    {
                        "type": "learn",
                        "target": "concept",
                        "reason": "The user also asked to learn this as a concept.",
                    },
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService.reply",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Close-visible-surface should return before ChatService.reply().")
        ),
    )

    concept_ids_before = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "close the whiteboard and learn this as a concept: topological sorting works on DAGs.",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": content,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Closed Midterm Study Plan from view. I did not learn it as a concept."
    assert payload["surface_action"]["type"] == "close_visible_surface"
    assert payload["surface_action"]["status"] == "requested"
    assert payload["surface_action"]["target_kind"] == "whiteboard"
    assert payload["surface_action"]["title"] == "Midterm Study Plan"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert {path.stem for path in (repo_root / "concepts").glob("*.md")} == concept_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["concept_write_authority"]["action"] == "concept_write"
    assert final_response["turn_plan"]["concept_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["concept_write_authority"]["denied_reason"] == "close_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_close_surface_blocks_local_semantic_artifact_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
        "summary": "Study plan for graph algorithms and priorities.",
        "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
    }

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose close-visible-surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to close the current whiteboard.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.turn_orchestrator.decide_semantic_policy",
        lambda *args, **kwargs: SemanticPolicyDecision(
            action_type="artifact_save",
            should_clarify=False,
            reason="Synthetic local save policy for no-write regression coverage.",
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService.reply",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Close-visible-surface should return before ChatService.reply().")
        ),
    )

    artifact_ids_before = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    memory_ids_before = {path.stem for path in (repo_root / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "close the whiteboard and save this whiteboard",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifact["content"],
            "visible_artifacts": [visible_artifact],
            "memory_intent": "remember",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_action"]["type"] == "close_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert {path.stem for path in (repo_root / "artifacts").glob("*.md")} == artifact_ids_before
    assert {path.stem for path in (repo_root / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["execution"]["local_semantic_write_policy"] == "disabled"
    assert final_response["turn_plan"]["artifact_write_authority"]["action"] == "artifact_save"
    assert final_response["turn_plan"]["artifact_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["artifact_write_authority"]["denied_reason"] == "close_visible_surface"
    assert final_response["turn_plan"]["memory_write_authority"]["action"] == "memory_write"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["memory_write_authority"]["denied_reason"] == "close_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_uses_explicit_navigator_surface_open_intent(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    def _route(self, **kwargs):
        assert any(
            candidate["resource_id"] == "task_focus:2026-05-14"
            for candidate in kwargs["attention_candidates"]
        )
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator selected task focus from the attention shortlist.",
            whiteboard_mode="chat",
            attention_selection={
                "selected_ids": ["task_focus:2026-05-14"],
                "primary_resource_id": "task_focus:2026-05-14",
                "supporting_resource_ids": [],
                "rejected_candidate_ids": ["calendar_day:2026-05-14"],
                "surface_to_open": "task_focus",
                "reason": "The user is asking what to focus on, so task focus is the primary working surface.",
                "confidence": 0.91,
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)

    response = client.post(
        "/api/chat",
        json={"message": "Plan my day around homework on 2026-05-14.", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["trigger"] == "attention_navigator"
    assert payload["surface_invocation"]["selection_authority"] == "attention_navigator"
    assert payload["surface_invocation"]["primary_surface"] == "task_focus"
    assert payload["active_surface_id"] == "tasks-2026-05-14"
    assert [surface["kind"] for surface in payload["surface_payloads"]] == ["task_focus"]
    assert payload["selected_attention_resources"][0]["resource_id"] == "task_focus:2026-05-14"


def test_chat_attention_open_directive_prefers_selected_artifact_over_visible_today(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Exam preparation material about graphs and study priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
    )
    visible_today = {
        "id": "today-2026-05-14",
        "kind": "today_briefing",
        "title": "Today",
        "summary": "Today is already visible.",
        "content": "# Today\n\nAlgorithms lab.",
        "data": {"date": "2026-05-14"},
    }
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        artifact_resource_id = f"artifact:{artifact.id}"
        assert any(candidate["resource_id"] == "visible:today-2026-05-14" for candidate in kwargs["attention_candidates"])
        assert any(candidate["resource_id"] == artifact_resource_id for candidate in kwargs["attention_candidates"])
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator selected the visible Today card plus the matching saved study plan.",
            whiteboard_mode="chat",
            attention_selection={
                "selected_ids": ["visible:today-2026-05-14", artifact_resource_id],
                "primary_resource_id": "visible:today-2026-05-14",
                "supporting_resource_ids": [artifact_resource_id],
                "rejected_candidate_ids": [],
                "reason": "Today is visible, and the saved Midterm Study Plan is the material the user asked to find.",
                "confidence": 0.91,
            },
        )

    def _reply(self, **kwargs):
        captured["whiteboard_mode"] = kwargs["whiteboard_mode"]
        captured["selected_attention_resources"] = kwargs["selected_attention_resources"]
        return "I found the Midterm Study Plan. It prioritizes graph traversals and proof review."

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)

    def _unexpected_meta_write(self, **kwargs):
        raise AssertionError("Open-only selected context should not run automatic graph writes.")

    monkeypatch.setattr("vantage_v5.services.meta.MetaService.decide", _unexpected_meta_write)

    response = client.post(
        "/api/chat",
        json={
            "message": "Show me the saved Midterm Study Plan",
            "history": [],
            "visible_artifacts": [visible_today],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["navigator_selection"]["primary_resource_id"] == f"artifact:{artifact.id}"
    assert payload["navigator_selection"]["surface_to_open"] == "whiteboard"
    assert any(
        action["type"] == "open_whiteboard"
        for action in payload["turn_interpretation"]["control_panel"]["actions"]
    )
    assert payload["surface_invocation"]["primary_surface"] == "whiteboard"
    assert payload["surface_invocation"]["write_behavior"] == "open_only"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "chat"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["active_surface_id"] is None
    assert payload["surface_payloads"] == []
    assert payload["selected_attention_resources"][0]["resource_id"] == f"artifact:{artifact.id}"
    assert payload["selected_attention_resources"][0]["suggested_surface"] == "whiteboard"
    assert "graph traversals" in payload["selected_attention_resources"][0]["content"]
    assert captured["whiteboard_mode"] == "chat"


def test_chat_attention_open_directive_prefers_source_artifact_over_opened_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    source_artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Study plan for graph algorithms, runtime analysis, and active recall.",
        body="# Midterm Study Plan\n\nPractice BFS, DFS, edge cases, and runtime analysis.",
    )
    opened_copy = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Drafted the detailed answer into the whiteboard for collaborative editing.",
        body="# Midterm Study Plan\n\nExpanded copy with graph traversal and study priorities.",
        comes_from=[source_artifact.id],
    )
    derivative = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="First Action from Midterm Study Plan",
        card="Drafted the detailed answer into the whiteboard for collaborative editing.",
        body="# First Action from Midterm Study Plan\n\nStart with BFS and DFS.",
        comes_from=[source_artifact.id],
    )
    visible_today = {
        "id": "today-2026-05-14",
        "kind": "today_briefing",
        "title": "Today",
        "summary": "Today is already visible.",
        "content": "# Today\n\nAlgorithms lab.",
        "data": {"date": "2026-05-14"},
    }
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        selected = [
            f"candidate-artifact:{opened_copy.id}",
            "candidate-visible:today-2026-05-14",
            f"candidate-artifact:{source_artifact.id}",
            f"candidate-artifact:{derivative.id}",
        ]
        for candidate_id in selected:
            assert any(candidate["id"] == candidate_id for candidate in kwargs["attention_candidates"])
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator selected the matching saved study-plan material.",
            whiteboard_mode="chat",
            attention_selection={
                "selected_ids": selected,
                "primary_resource_id": f"candidate-artifact:{opened_copy.id}",
                "supporting_resource_ids": selected[1:],
                "rejected_candidate_ids": [],
                "reason": "The saved Midterm Study Plan is the material the user asked to find.",
                "confidence": 0.91,
            },
        )

    def _reply(self, **kwargs):
        captured["whiteboard_mode"] = kwargs["whiteboard_mode"]
        captured["selected_attention_resources"] = kwargs["selected_attention_resources"]
        return "I found the Midterm Study Plan. It includes homework priorities and task focus for graphs."

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)

    def _unexpected_meta_write(self, **kwargs):
        raise AssertionError("Open-only source-artifact handoff should not run automatic graph writes.")

    monkeypatch.setattr("vantage_v5.services.meta.MetaService.decide", _unexpected_meta_write)

    response = client.post(
        "/api/chat",
        json={
            "message": "Can you find my exam preparation material about graphs and study priorities?",
            "history": [],
            "visible_artifacts": [visible_today],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["navigator_selection"]["primary_resource_id"] == f"artifact:{source_artifact.id}"
    assert payload["navigator_selection"]["surface_to_open"] == "whiteboard"
    assert any(
        action["type"] == "open_whiteboard"
        for action in payload["turn_interpretation"]["control_panel"]["actions"]
    )
    assert payload["surface_invocation"]["primary_surface"] == "whiteboard"
    assert payload["surface_invocation"]["write_behavior"] == "open_only"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "chat"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert payload["active_surface_id"] is None
    assert payload["surface_payloads"] == []
    assert payload["selected_attention_resources"][0]["resource_id"] == f"artifact:{source_artifact.id}"
    assert payload["selected_attention_resources"][0]["title"] == "Midterm Study Plan"
    assert "Practice BFS" in payload["selected_attention_resources"][0]["content"]
    assert captured["whiteboard_mode"] == "chat"

    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["request"]["message"] == "Can you find my exam preparation material about graphs and study priorities?"
    assert final_response["navigator_selection"] == payload["navigator_selection"]
    assert final_response["surface_invocation"] == payload["surface_invocation"]
    assert final_response["selected_attention_resources"] == payload["selected_attention_resources"]
    assert final_response["workspace_update"] is None
    assert final_response["graph_action"] is None
    assert final_response["created_record"] is None
    assert final_response["artifact_actions"] == []
    assert final_response["turn_plan"]["retrieval"]["primary_resource_id"] == f"artifact:{source_artifact.id}"
    assert final_response["turn_plan"]["ui_surface_action"]["mode"] == "open_only"
    assert final_response["turn_plan"]["execution"]["artifact_action_policy"] == "disabled"
    assert final_response["turn_plan"]["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "open_only_ui_handoff"
    assert final_response["turn_plan"]["validation"]["warnings"] == []
    role_projection = final_response["attention_recall_role_projection"]
    surface_roles = role_projection["roles"]["surface_to_open"]
    assert surface_roles[0]["resource_id"] == f"artifact:{source_artifact.id}"
    selected_resource = next(
        resource
        for resource in role_projection["resources"]
        if resource["resource_id"] == f"artifact:{source_artifact.id}"
    )
    assert {"answer_context", "surface_to_open"} <= set(selected_resource["roles"])
    assert selected_resource["flags"]["selected"] is True
    assert selected_resource["sent_to_response_llm"] is True
    assert len(selected_resource.get("excerpt") or "") <= 320
    working_memory_view = payload["working_memory_view"]
    assert final_response["working_memory_view"] == working_memory_view
    assert working_memory_view["roles"]["surface_to_open"][0]["resource_id"] == f"artifact:{source_artifact.id}"
    assert working_memory_view["execution_summary"]["surface"]["mode"] == "open_only"
    assert working_memory_view["execution_summary"]["surface"]["surface"] == "whiteboard"
    assert working_memory_view["execution_summary"]["writes"]["categories"] == ["open_only_no_write"]
    wm_selected_resource = next(
        resource
        for resource in working_memory_view["resources"]
        if resource["resource_id"] == f"artifact:{source_artifact.id}"
    )
    assert wm_selected_resource["influence"]["ui_surface_action"] is True
    assert len(wm_selected_resource.get("excerpt") or "") <= 320


def test_attention_open_only_forces_chat_execution_when_base_surface_is_draft(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Exam preparation material about graphs and study priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
    )
    captured: dict[str, object] = {}

    def _route(self, **kwargs):
        artifact_resource_id = f"artifact:{artifact.id}"
        assert any(candidate["resource_id"] == artifact_resource_id for candidate in kwargs["attention_candidates"])
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator selected the saved study plan while the base surface policy was drafty.",
            whiteboard_mode="draft",
            attention_selection={
                "selected_ids": [artifact_resource_id],
                "primary_resource_id": artifact_resource_id,
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": "whiteboard",
                "reason": "Open the selected study plan as the relevant material.",
                "confidence": 0.9,
            },
        )

    def _reply(self, **kwargs):
        captured["whiteboard_mode"] = kwargs["whiteboard_mode"]
        return (
            "CHAT_RESPONSE: I drafted it in the whiteboard.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Should Not Exist\n\n"
            "This draft must be blocked by open-only authority."
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)

    def _unexpected_meta_write(self, **kwargs):
        raise AssertionError("Open-only drafty-base handoff should not run automatic graph writes.")

    monkeypatch.setattr("vantage_v5.services.meta.MetaService.decide", _unexpected_meta_write)

    response = client.post(
        "/api/chat",
        json={
            "message": "Plan my day around studying with the Midterm Study Plan today.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["navigator_selection"]["surface_to_open"] == "whiteboard"
    assert payload["surface_invocation"]["primary_surface"] == "whiteboard"
    assert payload["surface_invocation"]["write_behavior"] == "open_only"
    assert payload["surface_invocation"]["whiteboard_mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "chat"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert captured["whiteboard_mode"] == "chat"
    assert "drafted" not in payload["assistant_message"].lower()
    assert "without creating" in payload["assistant_message"].lower()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "open_only_ui_handoff"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_open_only_blocks_local_semantic_artifact_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Exam preparation material about graphs and study priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
    )

    def _route(self, **kwargs):
        artifact_resource_id = f"artifact:{artifact.id}"
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator selected the saved study plan for a UI-only open.",
            whiteboard_mode="chat",
            attention_selection={
                "selected_ids": [artifact_resource_id],
                "primary_resource_id": artifact_resource_id,
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": "whiteboard",
                "reason": "Open the selected study plan as existing material.",
                "confidence": 0.9,
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.turn_orchestrator.decide_semantic_policy",
        lambda *args, **kwargs: SemanticPolicyDecision(
            action_type="artifact_save",
            should_clarify=False,
            reason="Synthetic local save policy for no-write regression coverage.",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService.reply",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Denied mixed open/save turns should not ask chat to write the receipt.")
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Open-only turns should suppress generic graph writes.")
        ),
    )

    artifact_ids_before = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "Show me the saved Midterm Study Plan and save this whiteboard.",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": "# Midterm Study Plan\n\nPractice graph traversal first.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I opened the selected material in the whiteboard. I did not save it."
    assert "saved" not in payload["assistant_message"].lower()
    assert payload["surface_invocation"]["write_behavior"] == "open_only"
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["artifact_actions"] == []
    assert {path.stem for path in (repo_root / "artifacts").glob("*.md")} == artifact_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["execution"]["local_semantic_write_policy"] == "disabled"
    assert final_response["turn_plan"]["artifact_write_authority"]["action"] == "artifact_save"
    assert final_response["turn_plan"]["artifact_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["artifact_write_authority"]["denied_reason"] == "open_only_ui_handoff"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_open_only_blocks_memory_write_intent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Exam preparation material about graphs and study priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
    )

    def _route(self, **kwargs):
        artifact_resource_id = f"artifact:{artifact.id}"
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator selected the saved study plan for a UI-only open.",
            whiteboard_mode="chat",
            attention_selection={
                "selected_ids": [artifact_resource_id],
                "primary_resource_id": artifact_resource_id,
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": "whiteboard",
                "reason": "Open the selected study plan as existing material.",
                "confidence": 0.9,
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "Opened the Midterm Study Plan without saving anything.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Open-only turns should not ask MetaService for memory writes.")
        ),
    )

    memory_ids_before = {path.stem for path in (repo_root / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "Show me the saved Midterm Study Plan and remember this.",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": "# Midterm Study Plan\n\nPractice graph traversal first.",
            "memory_intent": "remember",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["write_behavior"] == "open_only"
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert {path.stem for path in (repo_root / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["memory_write_authority"]["action"] == "memory_write"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["memory_write_authority"]["denied_reason"] == "open_only_ui_handoff"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_returns_proposed_calendar_action_without_mutating_user_file(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    calendar_events_path = _write_calendar_events(
        repo_root / "users" / "eden" / "state" / "calendar" / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "calendar_id": "school",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            }
        ],
    )

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "replace Advisor check-in with Grocery shopping",
            "history": [],
            "visible_artifacts": [_today_calendar_artifact()],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"][0]["status"] == "proposed"
    assert payload["artifact_actions"][0]["operation"] == "replace_event"
    assert payload["artifact_actions"][0]["payload"]["updates"] == {"title": "Grocery shopping"}
    assert payload["artifact_actions"][0]["compiler"]["pipeline"] == "semantic_then_json_contract"
    assert "calendar.json_interface" in payload["artifact_actions"][0]["compiler"]["contract_refs"]
    assert payload["surface_invocation"]["write_behavior"] == "proposal_only"
    assert payload["operational_proposal_authority"]["action"] == "operational_proposal"
    assert payload["operational_proposal_authority"]["allowed"] is True
    assert payload["operational_proposal_authority"]["authority"] == "artifact_mutation_compiler"
    assert payload["assistant_message"].startswith("Understood. I will")
    assert "after you confirm" in payload["assistant_message"]
    assert json.loads(calendar_events_path.read_text(encoding="utf-8"))["events"][0]["title"] == "Advisor check-in"
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["turn_plan"]["operational_proposal_authority"]["allowed"] is True
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["proposed_calendar_task_mutation"]
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_turn_plan_denies_malformed_calendar_proposal_candidate_before_persisting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    actions_dir = repo_root / "users" / "eden" / "state" / "artifact_actions"

    def _unsafe_candidate(self, **kwargs):
        return ArtifactActionPlan(
            artifact_actions=[
                {
                    "id": "artifact-action-unsafe",
                    "artifact_kind": "calendar",
                    "operation": "create_event",
                    "status": "ready",
                    "summary": "Create unsafe event.",
                    "payload": {
                        "title": "grocery shopping",
                        "start": "2026-05-14T11:00:00",
                        "end": "2026-05-14T11:30:00",
                    },
                    "requires_confirmation": False,
                }
            ]
        )

    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        _unsafe_candidate,
    )

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "I have grocery shopping at 11 2026-05-14",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"] == []
    assert payload["operational_proposal_authority"]["allowed"] is False
    assert payload["operational_proposal_authority"]["denied_reason"] == "operational_proposal_requires_proposed_status"
    assert not (actions_dir / "artifact-action-unsafe.json").exists()
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["turn_plan"]["operational_proposal_authority"]["allowed"] is False
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_accept_calendar_artifact_action_mutates_only_user_calendar_and_refreshes_surface(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password", "sam": "sam-password"})
    eden_calendar = _write_calendar_events(
        repo_root / "users" / "eden" / "state" / "calendar" / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "calendar_id": "school",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            }
        ],
    )
    sam_calendar = _write_calendar_events(
        repo_root / "users" / "sam" / "state" / "calendar" / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "calendar_id": "school",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            }
        ],
    )
    headers = _basic_auth_header("eden", "eden-password")
    proposed = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "replace Advisor check-in with Grocery shopping",
            "history": [],
            "visible_artifacts": [_today_calendar_artifact()],
        },
    ).json()["artifact_actions"][0]

    response = client.post(f"/api/artifact-actions/{proposed['id']}/accept", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"][0]["status"] == "accepted"
    assert payload["graph_action"]["type"] == "calendar_replace_event"
    assert payload["surface_payloads"][0]["kind"] == "today_briefing"
    assert payload["surface_payloads"][0]["data"]["calendar"]["events"][0]["title"] == "Grocery shopping"
    assert json.loads(eden_calendar.read_text(encoding="utf-8"))["events"][0]["title"] == "Grocery shopping"
    assert json.loads(sam_calendar.read_text(encoding="utf-8"))["events"][0]["title"] == "Advisor check-in"


def test_reject_calendar_artifact_action_leaves_calendar_unchanged(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    calendar_events_path = _write_calendar_events(
        repo_root / "users" / "eden" / "state" / "calendar" / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            }
        ],
    )
    headers = _basic_auth_header("eden", "eden-password")
    proposed = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "replace Advisor check-in with Grocery shopping",
            "history": [],
            "visible_artifacts": [_today_calendar_artifact()],
        },
    ).json()["artifact_actions"][0]

    response = client.post(f"/api/artifact-actions/{proposed['id']}/reject", headers=headers)

    assert response.status_code == 200
    assert response.json()["artifact_actions"][0]["status"] == "rejected"
    assert json.loads(calendar_events_path.read_text(encoding="utf-8"))["events"][0]["title"] == "Advisor check-in"


def test_calendar_artifact_action_rejects_global_configured_calendar_writes(tmp_path: Path) -> None:
    global_calendar = _write_calendar_events(
        tmp_path / "global-calendar" / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            }
        ],
    )
    client, _ = _client(tmp_path, auth_users={"eden": "eden-password"}, calendar_events_path=global_calendar)

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "replace Advisor check-in with Grocery shopping",
            "history": [],
            "visible_artifacts": [_today_calendar_artifact()],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"] == []
    assert "read-only" in payload["assistant_message"]
    assert json.loads(global_calendar.read_text(encoding="utf-8"))["events"][0]["title"] == "Advisor check-in"


def test_chat_capture_calendar_statement_proposes_event_and_opens_calendar(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    calendar_events_path = repo_root / "users" / "eden" / "state" / "calendar" / "events.json"

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "I have grocery shopping at 11 2026-05-14",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"][0]["artifact_kind"] == "calendar"
    assert payload["artifact_actions"][0]["operation"] == "create_event"
    assert payload["artifact_actions"][0]["payload"]["title"] == "grocery shopping"
    assert payload["surface_invocation"]["intent"] == "calendar_capture"
    assert payload["operational_proposal_authority"]["allowed"] is True
    assert payload["active_surface_id"] == "calendar-2026-05-14"
    assert payload["surface_payloads"][0]["kind"] == "calendar_day"
    assert "after you confirm" in payload["assistant_message"]
    assert not calendar_events_path.exists()
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["turn_plan"]["operational_proposal_authority"]["allowed"] is True
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_chat_calendar_event_called_prompt_proposes_event_and_opens_calendar(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    calendar_events_path = repo_root / "users" / "eden" / "state" / "calendar" / "events.json"

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "Add a calendar event tomorrow at 3 PM called Graph study review.",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    action = payload["artifact_actions"][0]
    assert action["artifact_kind"] == "calendar"
    assert action["operation"] == "create_event"
    assert action["status"] == "proposed"
    assert action["requires_confirmation"] is True
    assert action["compiler"]["source"] == "deterministic_fallback"
    assert action["payload"]["title"] == "Graph study review"
    assert action["payload"]["start"].endswith("T15:00:00")
    assert payload["surface_invocation"]["intent"] == "calendar_capture"
    assert payload["operational_proposal_authority"]["allowed"] is True
    assert "after you confirm" in payload["assistant_message"]
    assert (repo_root / "users" / "eden" / "state" / "artifact_actions" / f"{action['id']}.json").exists()
    assert not calendar_events_path.exists()
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["proposed_calendar_task_mutation"]
    assert final_response["turn_plan"]["operational_proposal_authority"]["allowed"] is True
    assert final_response["turn_plan"]["validation"]["warnings"] == []
    assert final_response["artifact_actions"][0]["compiler"]["source"] == "deterministic_fallback"


def test_chat_calendar_add_title_at_time_tomorrow_still_proposes_event(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    calendar_events_path = repo_root / "users" / "eden" / "state" / "calendar" / "events.json"

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "Add Graph study review at 3 PM tomorrow.",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    action = payload["artifact_actions"][0]
    assert action["artifact_kind"] == "calendar"
    assert action["operation"] == "create_event"
    assert action["status"] == "proposed"
    assert action["requires_confirmation"] is True
    assert action["payload"]["title"] == "Graph study review"
    assert action["payload"]["start"].endswith("T15:00:00")
    assert payload["operational_proposal_authority"]["allowed"] is True
    assert not calendar_events_path.exists()


def test_chat_calendar_lookup_remains_read_only_without_proposal(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "Show me my calendar tomorrow at 3 PM.",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"] == []
    assert payload["surface_invocation"]["intent"] == "schedule_lookup"
    assert payload["surface_invocation"]["write_behavior"] == "read_only"
    actions_dir = repo_root / "users" / "eden" / "state" / "artifact_actions"
    assert not list(actions_dir.glob("*.json"))


def test_hard_no_write_blocks_calendar_event_called_proposal(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"}, openai_api_key="test-key")
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
        "summary": "Study plan for graph algorithms and priorities.",
        "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
    }

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator chose preserve-visible-surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to keep the current whiteboard open.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I kept the whiteboard open.",
    )

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "keep the whiteboard open and add a calendar event tomorrow at 3 PM called Graph study review",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifact["content"],
            "visible_artifacts": [visible_artifact],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["artifact_actions"] == []
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    actions_dir = repo_root / "users" / "eden" / "state" / "artifact_actions"
    assert not list(actions_dir.glob("*.json"))


def test_accept_calendar_capture_creates_user_event_and_refreshes_calendar(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    headers = _basic_auth_header("eden", "eden-password")
    proposed = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "I have grocery shopping at 11 2026-05-14",
            "history": [],
            "visible_artifacts": [],
        },
    ).json()["artifact_actions"][0]

    response = client.post(f"/api/artifact-actions/{proposed['id']}/accept", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    events_path = repo_root / "users" / "eden" / "state" / "calendar" / "events.json"
    assert payload["artifact_actions"][0]["status"] == "accepted"
    assert payload["surface_payloads"][0]["kind"] == "calendar_day"
    assert payload["surface_payloads"][0]["data"]["calendar"]["events"][0]["title"] == "grocery shopping"
    assert json.loads(events_path.read_text(encoding="utf-8"))["events"][0]["title"] == "grocery shopping"


def test_chat_capture_task_statement_proposes_task_and_opens_task_focus(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    tasks_path = repo_root / "users" / "eden" / "state" / "tasks" / "tasks.json"

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "I need to finish homework 2 by 2026-05-14",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"][0]["artifact_kind"] == "task"
    assert payload["artifact_actions"][0]["operation"] == "create_task"
    assert payload["artifact_actions"][0]["payload"]["title"] == "finish homework 2"
    assert payload["surface_invocation"]["intent"] == "task_capture"
    assert payload["operational_proposal_authority"]["allowed"] is True
    assert payload["active_surface_id"] == "tasks-2026-05-14"
    assert payload["surface_payloads"][0]["kind"] == "task_focus"
    assert not tasks_path.exists()
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["turn_plan"]["operational_proposal_authority"]["allowed"] is True
    assert final_response["turn_plan"]["validation"]["warnings"] == []


@pytest.mark.parametrize(
    ("message", "normalized_command", "expected_due_date"),
    [
        (
            "Add a task to create slides tonight.",
            'Create a task titled "Create slides" with due_date 2026-05-19. Requires confirmation before applying',
            "2026-05-19",
        ),
        (
            "I need to create slides tomorrow.",
            'Create a task titled "Create slides" due tomorrow. Requires confirmation before applying',
            "2026-05-20",
        ),
    ],
)
def test_chat_task_create_slides_titles_are_clean_without_memory_write(
    tmp_path: Path,
    monkeypatch,
    message: str,
    normalized_command: str,
    expected_due_date: str,
) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    memory_ids_before = {path.stem for path in (repo_root / "users" / "eden" / "memories").glob("*.md")}

    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler._normalize_with_model",
        lambda self, **kwargs: normalized_command,
    )

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={"message": message, "history": [], "visible_artifacts": []},
    )

    assert response.status_code == 200
    payload = response.json()
    action = payload["artifact_actions"][0]
    assert action["artifact_kind"] == "task"
    assert action["operation"] == "create_task"
    assert action["payload"]["title"] == "Create slides"
    assert action["payload"]["due_date"] == expected_due_date
    assert "Requires confirmation" not in action["payload"]["title"]
    assert payload["workspace_update"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert {path.stem for path in (repo_root / "users" / "eden" / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["workspace_update"] is None
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["proposed_calendar_task_mutation"]
    working_memory_view = payload["working_memory_view"]
    assert final_response["working_memory_view"] == working_memory_view
    assert working_memory_view["execution_summary"]["writes"]["categories"] == [
        "proposed_calendar_task_mutation"
    ]
    assert working_memory_view["execution_summary"]["writes"]["proposal_count"] == 1
    assert working_memory_view["execution_summary"]["writes"]["artifact_action_count"] == 1
    assert not _payload_has_key(working_memory_view, "content")
    assert not _payload_has_key(working_memory_view, "body")


def test_task_proposal_suppresses_conflicting_whiteboard_offer(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"}, openai_api_key="test-key")
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I can capture that task.\n"
            "WHITEBOARD_OFFER: I can draft a small task plan in the whiteboard."
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler._normalize_with_model",
        lambda self, **kwargs: 'Create a task titled "Create slides". Requires confirmation before applying',
    )

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={"message": "I need to create slides tomorrow.", "history": [], "visible_artifacts": []},
    )

    assert response.status_code == 200
    payload = response.json()
    action = payload["artifact_actions"][0]
    assert action["artifact_kind"] == "task"
    assert action["operation"] == "create_task"
    assert action["payload"]["title"] == "Create slides"
    assert action["payload"]["due_date"] == "2026-05-20"
    assert payload["workspace_update"] is None
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["workspace_update"] is None
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["proposed_calendar_task_mutation"]


def test_task_proposal_preserves_explicit_whiteboard_offer_request(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"}, openai_api_key="test-key")
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I can capture that task.\n"
            "WHITEBOARD_OFFER: I can also sketch it in the whiteboard."
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler._normalize_with_model",
        lambda self, **kwargs: 'Create a task titled "Create slides". Requires confirmation before applying',
    )

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "Add a task to create slides tomorrow.",
            "history": [],
            "visible_artifacts": [],
            "whiteboard_mode": "offer",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    action = payload["artifact_actions"][0]
    assert action["artifact_kind"] == "task"
    assert action["operation"] == "create_task"
    assert action["payload"]["title"] == "Create slides"
    assert action["payload"]["due_date"] == "2026-05-20"
    assert payload["workspace_update"]["type"] == "offer_whiteboard"
    assert payload["workspace_update"]["status"] == "offered"
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["workspace_update"]["type"] == "offer_whiteboard"
    assert final_response["workspace_update"]["status"] == "offered"
    assert set(final_response["turn_plan"]["write_ledger"]["categories"]) == {
        "pending_whiteboard_offer",
        "proposed_calendar_task_mutation",
    }


def test_chat_remember_to_task_proposal_does_not_also_write_memory(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Navigator interpreted the leading remember verb as memory intent.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "remember",
                        "reason": "The user asked Vantage to remember information.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I can capture that.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="create_memory",
            title="Reminder: create slides tomorrow",
            card="Create slides tomorrow.",
            body="The user asked to create slides tomorrow.",
            rationale="Synthetic memory candidate for a reminder-shaped task command.",
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler._normalize_with_model",
        lambda self, **kwargs: 'Create a task titled "Create slides". Requires confirmation before applying',
    )

    memory_ids_before = {path.stem for path in (repo_root / "users" / "eden" / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={"message": "Remember to create slides tomorrow.", "history": [], "visible_artifacts": []},
    )

    assert response.status_code == 200
    payload = response.json()
    action = payload["artifact_actions"][0]
    assert action["artifact_kind"] == "task"
    assert action["operation"] == "create_task"
    assert action["payload"]["title"] == "Create slides"
    assert action["payload"]["due_date"] == "2026-05-20"
    assert payload["workspace_update"] is None
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_memory"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_memory_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert {path.stem for path in (repo_root / "users" / "eden" / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root / "users" / "eden")["final_response"]
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["proposed_calendar_task_mutation"]
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_accept_task_capture_creates_user_task_and_refreshes_task_focus(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password", "sam": "sam-password"})
    headers = _basic_auth_header("eden", "eden-password")
    proposed = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "I need to finish homework 2 by 2026-05-14",
            "history": [],
            "visible_artifacts": [],
        },
    ).json()["artifact_actions"][0]

    response = client.post(f"/api/artifact-actions/{proposed['id']}/accept", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    eden_tasks = repo_root / "users" / "eden" / "state" / "tasks" / "tasks.json"
    sam_tasks = repo_root / "users" / "sam" / "state" / "tasks" / "tasks.json"
    assert payload["artifact_actions"][0]["status"] == "accepted"
    assert payload["graph_action"]["type"] == "task_create_task"
    assert payload["surface_payloads"][0]["kind"] == "task_focus"
    assert payload["surface_payloads"][0]["data"]["tasks"]["groups"]["must_do_today"][0]["title"] == "finish homework 2"
    assert json.loads(eden_tasks.read_text(encoding="utf-8"))["tasks"][0]["title"] == "finish homework 2"
    assert not sam_tasks.exists()


def test_accept_visible_task_complete_action_mutates_user_task_and_refreshes_focus(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_users={"eden": "eden-password"})
    tasks_path = _write_tasks(
        repo_root / "users" / "eden" / "state" / "tasks" / "tasks.json",
        tasks=[
            {
                "id": "homework-2",
                "title": "Finish Homework 2",
                "due_date": "2026-05-14",
                "status": "open",
            }
        ],
    )
    headers = _basic_auth_header("eden", "eden-password")
    proposed = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "mark Homework 2 done",
            "history": [],
            "visible_artifacts": [_task_focus_artifact()],
        },
    ).json()["artifact_actions"][0]

    assert proposed["operation"] == "complete_task"
    assert json.loads(tasks_path.read_text(encoding="utf-8"))["tasks"][0]["status"] == "open"

    response = client.post(f"/api/artifact-actions/{proposed['id']}/accept", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"][0]["status"] == "accepted"
    assert payload["graph_action"]["type"] == "task_complete_task"
    assert payload["surface_payloads"][0]["kind"] == "task_focus"
    assert json.loads(tasks_path.read_text(encoding="utf-8"))["tasks"][0]["status"] == "completed"


def test_task_capture_rejects_global_configured_task_writes(tmp_path: Path) -> None:
    global_tasks = _write_tasks(tmp_path / "global-tasks" / "tasks.json", tasks=[])
    client, _ = _client(tmp_path, auth_users={"eden": "eden-password"}, tasks_path=global_tasks)

    response = client.post(
        "/api/chat",
        headers=_basic_auth_header("eden", "eden-password"),
        json={
            "message": "I need to finish homework 2 by 2026-05-14",
            "history": [],
            "visible_artifacts": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_actions"] == []
    assert "read-only" in payload["assistant_message"]
    assert json.loads(global_tasks.read_text(encoding="utf-8"))["tasks"] == []


def test_plain_why_question_stays_direct_chat(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post(
        "/api/chat",
        json={
            "message": "Why do transformers use attention? Keep it concise.",
            "history": [],
            "workspace_scope": "excluded",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] != "Which answer or context path would you like me to inspect?"
    assert payload["semantic_frame"]["target_surface"] == "chat"
    assert payload["semantic_frame"]["task_type"] == "question_answering"
    assert payload["semantic_policy"]["should_clarify"] is False


def test_basic_auth_protects_ui_and_api_when_configured(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path, auth_username="jordan", auth_password="secret-password")

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["auth_required"] is True
    assert health.json()["authenticated"] is False

    index = client.get("/")
    assert index.status_code == 200
    assert "<title>Vantage</title>" in index.text

    unauthenticated_workspace = client.get("/api/workspace")
    assert unauthenticated_workspace.status_code == 401
    assert unauthenticated_workspace.json()["detail"] == "Authentication required."
    assert "www-authenticate" not in unauthenticated_workspace.headers

    bad_credentials = client.get(
        "/api/workspace",
        headers=_basic_auth_header("jordan", "wrong-password"),
    )
    assert bad_credentials.status_code == 401

    workspace = client.get(
        "/api/workspace",
        headers=_basic_auth_header("jordan", "secret-password"),
    )
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == "v5-milestone-1"
    assert (repo_root / "users" / "jordan" / "workspaces" / "v5-milestone-1.md").exists()

    index = client.get("/", headers=_basic_auth_header("jordan", "secret-password"))
    assert index.status_code == 200
    assert "<title>Vantage</title>" in index.text


def test_public_bind_requires_auth_unless_explicitly_overridden(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="without authentication"):
        _client(tmp_path, host="0.0.0.0")

    unsafe_tmp_path = tmp_path / "unsafe-override"
    unsafe_tmp_path.mkdir()
    client, _ = _client(
        unsafe_tmp_path,
        host="0.0.0.0",
        allow_unsafe_public_no_auth=True,
    )
    assert client.get("/api/health").status_code == 200


def test_cross_origin_mutating_requests_are_blocked(tmp_path: Path) -> None:
    client, _ = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
        },
    )

    blocked = client.post(
        "/api/login",
        json={"username": "eden", "password": "eden-password"},
        headers={"Origin": "https://attacker.example"},
    )
    assert blocked.status_code == 403

    allowed = client.post(
        "/api/login",
        json={"username": "eden", "password": "eden-password"},
        headers={"Origin": "http://testserver"},
    )
    assert allowed.status_code == 200


def test_secure_cookie_setting_for_https_proxy_deployments(tmp_path: Path) -> None:
    client, _ = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
        },
        cookie_secure=True,
    )

    login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})

    assert login.status_code == 200
    assert "Secure" in login.headers.get("set-cookie", "")


def test_cookie_login_protects_user_scoped_routes(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
            "jordan": "jordan-password",
        },
    )

    bad_login = client.post("/api/login", json={"username": "eden", "password": "wrong-password"})
    assert bad_login.status_code == 401

    login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})
    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert login.json()["user"] == {"id": "eden"}
    assert "vantage_session" in login.headers.get("set-cookie", "")

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["authenticated"] is True
    assert health.json()["user"] == {"id": "eden"}
    protocol_path = repo_root / "users" / "eden" / "concepts" / "email-drafting-protocol.md"
    assert not protocol_path.exists()

    protocols = client.get("/api/protocols")
    assert protocols.status_code == 200
    protocols_by_id = {item["id"]: item for item in protocols.json()["protocols"]}
    assert protocols_by_id["email-drafting-protocol"]["scope"] == "canonical"
    assert protocols_by_id["email-drafting-protocol"]["protocol"]["protocol_kind"] == "email"

    update = client.post(
        "/api/workspace",
        json={
            "workspace_id": "v5-milestone-1",
            "content": "# Eden Cookie Draft\n\nThis belongs to Eden's login session.",
        },
    )
    assert update.status_code == 200
    assert "Eden Cookie Draft" in update.json()["content"]
    assert "Eden Cookie Draft" in (
        repo_root / "users" / "eden" / "workspaces" / "v5-milestone-1.md"
    ).read_text(encoding="utf-8")
    jordan_workspace_path = repo_root / "users" / "jordan" / "workspaces" / "v5-milestone-1.md"
    assert not jordan_workspace_path.exists() or "Eden Cookie Draft" not in jordan_workspace_path.read_text(encoding="utf-8")

    logout = client.post("/api/logout")
    assert logout.status_code == 200
    assert client.get("/api/workspace").status_code == 401


def test_create_account_hashes_password_and_creates_user_session(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
        },
    )
    password = "taylor-password"

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["account_creation_enabled"] is True
    assert health.json()["account_creation_code_required"] is False

    invalid = client.post("/api/accounts", json={"username": "no spaces", "password": password})
    assert invalid.status_code == 400

    duplicate_configured_user = client.post("/api/accounts", json={"username": "eden", "password": password})
    assert duplicate_configured_user.status_code == 409

    created = client.post("/api/accounts", json={"username": "Taylor_01", "password": password})
    assert created.status_code == 201
    assert created.json()["authenticated"] is True
    assert created.json()["created"] is True
    assert created.json()["user"] == {"id": "Taylor_01"}
    assert "vantage_session" in created.headers.get("set-cookie", "")

    account_path = repo_root / "state" / "accounts.json"
    assert account_path.exists()
    account_payload = json.loads(account_path.read_text(encoding="utf-8"))
    account = account_payload["accounts"]["taylor_01"]
    assert account["username"] == "Taylor_01"
    assert account["password"]["algorithm"] == "pbkdf2_sha256"
    assert password not in account_path.read_text(encoding="utf-8")
    assert (repo_root / "users" / "taylor_01" / "workspaces" / "v5-milestone-1.md").exists()
    calendar_path = repo_root / "users" / "taylor_01" / "state" / "calendar" / "events.json"
    assert calendar_path.exists()
    assert json.loads(calendar_path.read_text(encoding="utf-8")) == {
        "calendars": [{"id": "local", "title": "Calendar"}],
        "events": [],
    }
    assert not (repo_root / "users" / "taylor_01" / "concepts" / "email-drafting-protocol.md").exists()

    protocols = client.get("/api/protocols")
    assert protocols.status_code == 200
    protocols_by_id = {item["id"]: item for item in protocols.json()["protocols"]}
    assert protocols_by_id["email-drafting-protocol"]["scope"] == "canonical"

    duplicate_local_user = client.post("/api/accounts", json={"username": "taylor_01", "password": password})
    assert duplicate_local_user.status_code == 409

    logout = client.post("/api/logout")
    assert logout.status_code == 200

    bad_login = client.post("/api/login", json={"username": "Taylor_01", "password": "wrong-password"})
    assert bad_login.status_code == 401

    login = client.post("/api/login", json={"username": "Taylor_01", "password": password})
    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert login.json()["user"] == {"id": "Taylor_01"}

    workspace = client.get("/api/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == "v5-milestone-1"


def test_create_account_does_not_seed_profile_calendar_when_global_calendar_is_configured(tmp_path: Path) -> None:
    global_event = {
        "id": "advisor-check-in",
        "calendar_id": "school",
        "title": "Advisor check-in",
        "start": "2026-05-14T11:00:00",
        "end": "2026-05-14T11:30:00",
    }
    global_calendar_path = _write_calendar_events(
        tmp_path / "global-calendar" / "events.json",
        events=[global_event],
    )
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
        },
        calendar_events_path=global_calendar_path,
    )

    created = client.post("/api/accounts", json={"username": "Taylor_01", "password": "taylor-password"})
    assert created.status_code == 201

    profile_calendar_path = repo_root / "users" / "taylor_01" / "state" / "calendar" / "events.json"
    assert not profile_calendar_path.exists()
    assert json.loads(global_calendar_path.read_text(encoding="utf-8")) == {
        "calendars": [{"id": "school", "title": "School"}],
        "events": [global_event],
    }


def test_create_account_can_require_access_code(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
        },
        account_creation_code="join-vantage",
    )

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["account_creation_enabled"] is True
    assert health.json()["account_creation_code_required"] is True

    missing_code = client.post("/api/accounts", json={"username": "Taylor_01", "password": "taylor-password"})
    assert missing_code.status_code == 403

    wrong_code = client.post(
        "/api/accounts",
        json={"username": "Taylor_01", "password": "taylor-password", "access_code": "wrong-code"},
    )
    assert wrong_code.status_code == 403

    created = client.post(
        "/api/accounts",
        json={"username": "Taylor_01", "password": "taylor-password", "access_code": "join-vantage"},
    )
    assert created.status_code == 201
    assert created.json()["authenticated"] is True
    assert created.json()["account_creation_code_required"] is True
    assert (repo_root / "users" / "taylor_01" / "workspaces" / "v5-milestone-1.md").exists()


def test_create_account_is_disabled_when_auth_is_not_enabled(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["auth_required"] is False
    assert health.json()["account_creation_enabled"] is False

    created = client.post("/api/accounts", json={"username": "Taylor_01", "password": "taylor-password"})
    assert created.status_code == 404


def test_pwa_assets_are_served_with_safe_cache_headers(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert manifest.headers["cache-control"] == "no-cache"
    manifest_payload = manifest.json()
    assert manifest_payload["name"] == "Vantage v6"
    assert manifest_payload["display"] == "standalone"
    assert manifest_payload["start_url"] == "/"
    assert {icon["src"] for icon in manifest_payload["icons"]} == {
        "/icons/vantage-icon-192.png",
        "/icons/vantage-icon-512.png",
    }

    service_worker = client.get("/sw.js")
    assert service_worker.status_code == 200
    assert service_worker.headers["content-type"].startswith("text/javascript")
    assert service_worker.headers["cache-control"] == "no-cache"
    assert service_worker.headers["service-worker-allowed"] == "/"
    assert 'url.pathname.startsWith("/api/")' in service_worker.text

    icon = client.get("/icons/vantage-icon-192.png")
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/png")
    assert icon.headers["cache-control"] == "public, max-age=86400"
    assert icon.content.startswith(b"\x89PNG")


def test_pwa_assets_stay_public_when_auth_is_enabled(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, auth_users={"eden": "eden-password"})

    assert client.get("/manifest.webmanifest").status_code == 200
    assert client.get("/sw.js").status_code == 200
    assert client.get("/icons/apple-touch-icon.png").status_code == 200
    protected_workspace = client.get("/api/workspace")
    assert protected_workspace.status_code == 401
    assert protected_workspace.json()["detail"] == "Authentication required."


def test_user_openai_key_is_scoped_and_not_returned_or_persisted(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
            "jordan": "jordan-password",
        },
    )
    secret = "sk-test-eden-secret-1234"

    assert client.get("/api/openai-key").status_code == 401

    login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})
    assert login.status_code == 200

    initial_status = client.get("/api/openai-key")
    assert initial_status.status_code == 200
    assert initial_status.json()["openai_key"] == {
        "configured": False,
        "source": "none",
        "masked_key": "",
        "environment_configured": False,
    }

    save = client.put("/api/openai-key", json={"api_key": secret})
    assert save.status_code == 200
    assert save.json()["mode"] == "openai"
    assert save.json()["openai_key"]["source"] == "user"
    assert save.json()["openai_key"]["masked_key"] == "sk-t...1234"
    assert secret not in save.text

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "openai"
    assert health.json()["openai_key"]["source"] == "user"
    assert secret not in health.text

    logout = client.post("/api/logout")
    assert logout.status_code == 200
    jordan_login = client.post("/api/login", json={"username": "jordan", "password": "jordan-password"})
    assert jordan_login.status_code == 200
    jordan_status = client.get("/api/openai-key")
    assert jordan_status.status_code == 200
    assert jordan_status.json()["mode"] == "fallback"
    assert jordan_status.json()["openai_key"]["source"] == "none"

    client.post("/api/logout")
    eden_login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})
    assert eden_login.status_code == 200
    clear = client.delete("/api/openai-key")
    assert clear.status_code == 200
    assert clear.json()["mode"] == "fallback"
    assert clear.json()["openai_key"]["source"] == "none"

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            assert secret not in path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def test_user_openai_key_can_override_environment_key_and_clear_back_to_env(tmp_path: Path) -> None:
    client, _ = _client(
        tmp_path,
        openai_api_key="sk-env-fallback-5678",
        auth_users={"eden": "eden-password"},
    )

    login = client.post("/api/login", json={"username": "eden", "password": "eden-password"})
    assert login.status_code == 200

    env_status = client.get("/api/openai-key")
    assert env_status.status_code == 200
    assert env_status.json()["mode"] == "openai"
    assert env_status.json()["openai_key"]["source"] == "environment"
    assert env_status.json()["openai_key"]["masked_key"] == "sk-e...5678"

    user_status = client.put("/api/openai-key", json={"api_key": "sk-user-override-9012"})
    assert user_status.status_code == 200
    assert user_status.json()["openai_key"]["source"] == "user"
    assert user_status.json()["openai_key"]["masked_key"] == "sk-u...9012"

    restored = client.delete("/api/openai-key")
    assert restored.status_code == 200
    assert restored.json()["mode"] == "openai"
    assert restored.json()["openai_key"]["source"] == "environment"
    assert restored.json()["openai_key"]["masked_key"] == "sk-e...5678"


def test_health_reports_codex_oauth_model_auth_without_returning_token(tmp_path: Path) -> None:
    access_token = _fake_jwt(4_102_444_800)
    auth_path = _write_codex_auth(tmp_path / "codex-auth.json", access_token=access_token)
    client, _ = _client(
        tmp_path,
        model_provider=MODEL_PROVIDER_CODEX_OAUTH,
        model="gpt-5.5",
        codex_auth_path=auth_path,
    )

    health = client.get("/api/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["mode"] == "codex_oauth"
    assert payload["model"] == "gpt-5.5"
    assert payload["model_provider"] == "codex_oauth"
    assert payload["model_auth"]["configured"] is True
    assert payload["model_auth"]["provider"] == "codex_oauth"
    assert payload["model_auth"]["codex_oauth"]["source"] == "codex_cli"
    assert access_token not in health.text


def test_semantic_policy_saves_visible_whiteboard_without_chat_guessing(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    def _reply_should_not_run(self, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("Semantic save should be handled before ChatService.reply().")

    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "save this whiteboard",
            "history": [],
            "workspace_id": "semantic-save-draft",
            "workspace_scope": "visible",
            "workspace_content": "# Semantic Save Draft\n\nThis should become a saved whiteboard snapshot.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "local_action"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["requested_whiteboard_mode"] == "auto"
    assert payload["turn_interpretation"]["whiteboard_entry_mode"] == "started_fresh"
    assert payload["semantic_frame"]["task_type"] == "artifact_save"
    assert payload["semantic_policy"]["action_type"] == "artifact_save"
    assert payload["semantic_policy"]["should_clarify"] is False
    assert "saved" in payload["assistant_message"].lower()
    assert payload["surface_invocation"]["intent"] == "artifact_save"
    assert payload["surface_invocation"]["legacy_write_behavior"] == "none"
    assert payload["surface_invocation"]["write_behavior"] == "committed_write"
    assert payload["surface_invocation"]["write_intent"]["kind"] == "artifact_save"
    assert payload["surface_invocation"]["write_intent"]["authority"] == "semantic_policy"
    assert payload["surface_invocation"]["write_effects"][0]["category"] == "artifact_save_or_promotion"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["created_record"]["artifact_lifecycle"] == "whiteboard_snapshot"
    assert payload["created_record"]["write_review"]["write_reason"] == (
        "Saved as a whiteboard snapshot so the in-progress draft stays inspectable."
    )
    assert {action["kind"] for action in payload["created_record"]["write_review"]["allowed_actions"]} == {
        "open_in_whiteboard",
        "revise_in_whiteboard",
        "pin_for_next_turn",
    }
    assert payload["created_record"]["write_review"]["direct_mutation_supported"] is False
    assert (repo_root / "workspaces" / "semantic-save-draft.md").exists()
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    turn_plan = final_response["turn_plan"]
    assert turn_plan["write_projection"]["intended_write_kind"] == "artifact_save"
    assert turn_plan["write_projection"]["effect_agreement"] == "aligned"
    assert turn_plan["artifact_write_authority"]["action"] == "artifact_save"
    assert turn_plan["artifact_write_authority"]["allowed"] is True
    assert turn_plan["artifact_write_authority"]["denied_reason"] is None
    assert turn_plan["validation"]["warnings"] == []


def test_semantic_policy_clarifies_save_without_visible_target(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    def _reply_should_not_run(self, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("Ambiguous save should clarify before ChatService.reply().")

    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "save this",
            "history": [],
            "workspace_scope": "excluded",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "clarification"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["requested_whiteboard_mode"] == "auto"
    assert payload["semantic_policy"]["action_type"] == "artifact_save"
    assert payload["semantic_policy"]["should_clarify"] is True
    assert "What should I save" in payload["assistant_message"]
    assert payload["graph_action"] is None
    assert payload["created_record"] is None


def test_semantic_policy_publishes_visible_whiteboard_as_artifact(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    def _reply_should_not_run(self, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("Semantic publish should be handled before ChatService.reply().")

    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "publish this artifact",
            "history": [],
            "workspace_id": "semantic-publish-draft",
            "workspace_scope": "visible",
            "workspace_content": "# Semantic Publish Draft\n\nThis should become a promoted artifact.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "local_action"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["requested_whiteboard_mode"] == "auto"
    assert payload["turn_interpretation"]["whiteboard_entry_mode"] == "started_fresh"
    assert payload["semantic_frame"]["task_type"] == "artifact_publish"
    assert payload["semantic_policy"]["action_type"] == "artifact_publish"
    assert payload["semantic_policy"]["should_clarify"] is False
    assert "published" in payload["assistant_message"].lower()
    assert payload["surface_invocation"]["intent"] == "artifact_publish"
    assert payload["surface_invocation"]["legacy_write_behavior"] == "none"
    assert payload["surface_invocation"]["write_behavior"] == "committed_write"
    assert payload["surface_invocation"]["write_intent"]["kind"] == "artifact_publish"
    assert payload["surface_invocation"]["write_intent"]["authority"] == "semantic_policy"
    assert payload["surface_invocation"]["write_effects"][0]["category"] == "artifact_save_or_promotion"
    assert payload["graph_action"]["type"] == "promote_workspace_to_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["created_record"]["artifact_lifecycle"] == "promoted_artifact"
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    turn_plan = final_response["turn_plan"]
    assert turn_plan["write_projection"]["intended_write_kind"] == "artifact_publish"
    assert turn_plan["write_projection"]["effect_agreement"] == "aligned"
    assert turn_plan["artifact_write_authority"]["action"] == "artifact_publish"
    assert turn_plan["artifact_write_authority"]["allowed"] is True
    assert turn_plan["artifact_write_authority"]["denied_reason"] is None
    assert turn_plan["validation"]["warnings"] == []


def test_semantic_policy_answers_experiment_status_locally(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    started = client.post("/api/experiment/start", json={"seed_from_workspace": False})
    assert started.status_code == 200

    def _reply_should_not_run(self, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("Experiment status should be handled before ChatService.reply().")

    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply_should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "am I in experiment mode?",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "local_action"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["requested_whiteboard_mode"] == "auto"
    assert payload["semantic_frame"]["task_type"] == "experiment_management"
    assert payload["semantic_policy"]["action_type"] == "experiment_manage"
    assert payload["semantic_policy"]["should_clarify"] is False
    assert "Experiment mode is active" in payload["assistant_message"]
    assert payload["experiment"]["active"] is True


def test_navigator_control_panel_is_exposed_on_turn_interpretation(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.94,
            reason="The navigator chose the whiteboard control.",
            whiteboard_mode="draft",
            control_panel={
                "actions": [
                    {
                        "type": "draft_whiteboard",
                        "reason": "The user asked for a collaborative draft.",
                    },
                    {
                        "type": "respond",
                        "reason": "Explain that the draft is ready.",
                    },
                ],
                "working_memory_queries": ["active email drafting protocol"],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I drafted it in the whiteboard.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Draft\n\n"
            "A concise draft."
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Draft stays temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft this in the whiteboard",
            "history": [],
        },
    )

    assert response.status_code == 200
    control_panel = response.json()["turn_interpretation"]["control_panel"]
    assert [action["type"] for action in control_panel["actions"]] == ["draft_whiteboard", "respond"]
    assert control_panel["working_memory_queries"] == ["active email drafting protocol"]
    assert control_panel["response_call"]["after_working_memory"] is True


def test_apply_protocol_control_loads_built_in_scenario_protocol_for_chat(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Use the Scenario Lab protocol as reasoning guidance.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "apply_protocol",
                        "protocol_kind": "scenario_lab",
                        "reason": "The request needs scenario-style reasoning.",
                    },
                    {"type": "respond", "reason": "Answer after applying the protocol."},
                ],
                "working_memory_queries": ["scenario reasoning protocol"],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Help me think through possible launch paths.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    recalled = {item["id"]: item for item in payload["working_memory"]}
    assert "scenario-lab-protocol" in recalled
    assert recalled["scenario-lab-protocol"]["type"] == "protocol"
    assert recalled["scenario-lab-protocol"]["kind"] == "protocol"
    assert recalled["scenario-lab-protocol"]["memory_role"] == "protocol"
    assert recalled["scenario-lab-protocol"]["source_tier"] == "instruction"
    assert recalled["scenario-lab-protocol"]["protocol"]["protocol_kind"] == "scenario_lab"
    assert recalled["scenario-lab-protocol"]["protocol"]["is_builtin"] is True
    assert recalled["scenario-lab-protocol"]["protocol"]["modifiable"] is True
    assert "counterfactual reasoning" in recalled["scenario-lab-protocol"]["body"]


def test_protocol_apis_include_builtins_and_persist_builtin_override(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    protocols = client.get("/api/protocols", params={"include_builtins": "true"})
    assert protocols.status_code == 200
    by_id = {item["id"]: item for item in protocols.json()["protocols"]}
    assert "scenario-lab-protocol" in by_id
    assert by_id["scenario-lab-protocol"]["scope"] == "builtin"
    assert by_id["scenario-lab-protocol"]["source_label"] == "Built-in"
    assert by_id["scenario-lab-protocol"]["protocol"]["is_builtin"] is True
    assert by_id["scenario-lab-protocol"]["protocol"]["is_canonical"] is False
    assert by_id["scenario-lab-protocol"]["protocol"]["overrides_builtin"] is False
    assert by_id["scenario-lab-protocol"]["protocol"]["overrides_canonical"] is False

    fetched_by_kind = client.get("/api/protocols/scenario_lab")
    assert fetched_by_kind.status_code == 200
    assert fetched_by_kind.json()["id"] == "scenario-lab-protocol"
    assert fetched_by_kind.json()["scope"] == "builtin"
    assert fetched_by_kind.json()["source_label"] == "Built-in"
    assert fetched_by_kind.json()["protocol"]["overrides_canonical"] is False

    updated = client.put(
        "/api/protocols/scenario_lab",
        json={
            "card": "Custom Scenario Lab guidance for premium comparisons.",
            "variables": {"default_surface": "premium_scenario_lab"},
            "applies_to": ["scenario lab", "premium comparison"],
        },
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["id"] == "scenario-lab-protocol"
    assert updated_payload["scope"] == "durable"
    assert updated_payload["source_label"] == "Custom override"
    assert updated_payload["protocol"]["is_builtin"] is False
    assert updated_payload["protocol"]["is_canonical"] is False
    assert updated_payload["protocol"]["overrides_builtin"] is True
    assert updated_payload["protocol"]["overrides_canonical"] is False
    assert updated_payload["protocol"]["variables"]["default_surface"] == "premium_scenario_lab"
    assert updated_payload["card"] == "Custom Scenario Lab guidance for premium comparisons."
    assert (repo_root / "concepts" / "scenario-lab-protocol.md").exists()

    protocols_after = client.get("/api/protocols", params={"include_builtins": "true"})
    assert protocols_after.status_code == 200
    matches = [item for item in protocols_after.json()["protocols"] if item["id"] == "scenario-lab-protocol"]
    assert len(matches) == 1
    assert matches[0]["scope"] == "durable"
    assert matches[0]["source_label"] == "Custom override"


def test_canonical_protocols_are_read_through_and_user_overrides_are_private(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
            "jordan": "jordan-password",
        },
    )
    eden_headers = _basic_auth_header("eden", "eden-password")
    jordan_headers = _basic_auth_header("jordan", "jordan-password")

    protocols = client.get("/api/protocols", headers=eden_headers)
    assert protocols.status_code == 200
    by_id = {item["id"]: item for item in protocols.json()["protocols"]}
    assert by_id["email-drafting-protocol"]["scope"] == "canonical"
    assert by_id["email-drafting-protocol"]["source_label"] == "Built-in"
    assert by_id["email-drafting-protocol"]["protocol"]["is_builtin"] is False
    assert by_id["email-drafting-protocol"]["protocol"]["is_canonical"] is True
    assert by_id["email-drafting-protocol"]["protocol"]["overrides_builtin"] is False
    assert by_id["email-drafting-protocol"]["protocol"]["overrides_canonical"] is False
    assert not (repo_root / "users" / "eden" / "concepts" / "email-drafting-protocol.md").exists()

    updated = client.put(
        "/api/protocols/email",
        headers=eden_headers,
        json={
            "variables": {"signature": "Eden Vale"},
            "applies_to": ["email", "investor update"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["scope"] == "durable"
    assert updated.json()["source_label"] == "Custom override"
    assert updated.json()["protocol"]["is_canonical"] is False
    assert updated.json()["protocol"]["overrides_canonical"] is True
    assert updated.json()["protocol"]["variables"]["signature"] == "Eden Vale"
    assert (repo_root / "users" / "eden" / "concepts" / "email-drafting-protocol.md").exists()
    assert "Eden Vale" not in (repo_root / "canonical" / "concepts" / "email-drafting-protocol.md").read_text(encoding="utf-8")

    second_update = client.put(
        "/api/protocols/email",
        headers=eden_headers,
        json={
            "variables": {"signature": "Eden Vale", "default_close": "Thanks"},
        },
    )
    assert second_update.status_code == 200
    assert second_update.json()["source_label"] == "Custom override"
    assert second_update.json()["protocol"]["overrides_canonical"] is True

    eden_protocols = client.get("/api/protocols", headers=eden_headers)
    assert eden_protocols.status_code == 200
    eden_by_id = {item["id"]: item for item in eden_protocols.json()["protocols"]}
    assert eden_by_id["email-drafting-protocol"]["scope"] == "durable"
    assert eden_by_id["email-drafting-protocol"]["source_label"] == "Custom override"
    assert eden_by_id["email-drafting-protocol"]["protocol"]["variables"]["signature"] == "Eden Vale"

    eden_catalog = client.get("/api/protocols", params={"include_builtins": "true"}, headers=eden_headers)
    assert eden_catalog.status_code == 200
    eden_catalog_items = eden_catalog.json()["protocols"]
    assert len([item for item in eden_catalog_items if item["id"] == "email-drafting-protocol"]) == 1
    assert len([item for item in eden_catalog_items if item["id"] == "scenario-lab-protocol"]) == 1

    jordan_protocols = client.get("/api/protocols", headers=jordan_headers)
    assert jordan_protocols.status_code == 200
    jordan_by_id = {item["id"]: item for item in jordan_protocols.json()["protocols"]}
    assert jordan_by_id["email-drafting-protocol"]["scope"] == "canonical"
    assert jordan_by_id["email-drafting-protocol"]["source_label"] == "Built-in"
    assert jordan_by_id["email-drafting-protocol"]["protocol"]["variables"]["signature"] == ""

    jordan_catalog = client.get("/api/protocols", params={"include_builtins": "true"}, headers=jordan_headers)
    assert jordan_catalog.status_code == 200
    jordan_catalog_by_id = {item["id"]: item for item in jordan_catalog.json()["protocols"]}
    assert jordan_catalog_by_id["email-drafting-protocol"]["source_label"] == "Built-in"
    assert jordan_catalog_by_id["email-drafting-protocol"]["protocol"]["variables"]["signature"] == ""
    assert jordan_catalog_by_id["scenario-lab-protocol"]["source_label"] == "Built-in"


def test_profile_named_canonical_keeps_private_records_durable_and_defaults_read_through(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "canonical": "canonical-password",
        },
    )
    headers = _basic_auth_header("canonical", "canonical-password")

    workspace = client.get("/api/workspace", headers=headers)
    assert workspace.status_code == 200
    user_root = repo_root / "users" / "canonical"

    private_concept = ConceptStore(user_root / "concepts").create_concept(
        title="Canonical Profile Private Concept",
        card="Private concept for the canonical-named profile.",
        body="This concept belongs to the profile named canonical, not to the global canonical layer.",
    )
    private_protocol = ConceptStore(user_root / "concepts").upsert_protocol(
        protocol_id="canonical-profile-private-protocol",
        title="Canonical Profile Private Protocol",
        card="Private protocol for the canonical-named profile.",
        body="## Protocol\n\nUse this only for the canonical-named profile.",
        protocol_kind="scenario_lab",
        variables={},
        applies_to=["canonical profile private protocol"],
    )
    private_memory = MemoryStore(user_root / "memories").create_memory(
        title="Canonical Profile Private Memory",
        card="Private memory for the canonical-named profile.",
        body="This memory belongs to the profile named canonical.",
    )
    private_artifact = ArtifactStore(user_root / "artifacts").create_artifact(
        title="Canonical Profile Private Artifact",
        card="Private artifact for the canonical-named profile.",
        body="This artifact belongs to the profile named canonical.",
    )
    canonical_memory = MemoryStore(repo_root / "canonical" / "memories").create_memory(
        title="Shared Canonical Memory",
        card="Canonical memory visible to every profile.",
        body="This memory lives under the configured canonical root.",
    )
    canonical_artifact = ArtifactStore(repo_root / "canonical" / "artifacts").create_artifact(
        title="Shared Canonical Artifact",
        card="Canonical artifact visible to every profile.",
        body="This artifact lives under the configured canonical root.",
    )

    concepts = client.get("/api/concepts", headers=headers)
    assert concepts.status_code == 200
    concepts_by_id = {item["id"]: item for item in concepts.json()["concepts"]}
    assert concepts_by_id[private_concept.id]["scope"] == "durable"
    assert concepts_by_id[private_protocol.id]["scope"] == "durable"
    assert concepts_by_id[private_protocol.id]["protocol"]["is_canonical"] is False
    assert concepts_by_id["email-drafting-protocol"]["scope"] == "canonical"

    concept_detail = client.get(f"/api/concepts/{private_concept.id}", headers=headers)
    assert concept_detail.status_code == 200
    assert concept_detail.json()["scope"] == "durable"

    concept_search = client.get(
        "/api/concepts/search",
        params={"query": "canonical profile private concept"},
        headers=headers,
    )
    assert concept_search.status_code == 200
    assert any(item["id"] == private_concept.id for item in concept_search.json()["concepts"])
    searched_concept_detail = client.get(f"/api/concepts/{private_concept.id}", headers=headers)
    assert searched_concept_detail.json()["scope"] == "durable"

    memory = client.get("/api/memory", headers=headers)
    assert memory.status_code == 200
    saved_notes_by_id = {item["id"]: item for item in memory.json()["saved_notes"]}
    assert saved_notes_by_id[private_memory.id]["scope"] == "durable"
    assert saved_notes_by_id[private_artifact.id]["scope"] == "durable"
    assert saved_notes_by_id[canonical_memory.id]["scope"] == "canonical"
    assert saved_notes_by_id[canonical_artifact.id]["scope"] == "canonical"

    private_memory_detail = client.get(f"/api/memory/{private_memory.id}", headers=headers)
    assert private_memory_detail.status_code == 200
    assert private_memory_detail.json()["item"]["scope"] == "durable"
    private_artifact_detail = client.get(f"/api/memory/{private_artifact.id}", headers=headers)
    assert private_artifact_detail.status_code == 200
    assert private_artifact_detail.json()["item"]["scope"] == "durable"
    canonical_memory_detail = client.get(f"/api/memory/{canonical_memory.id}", headers=headers)
    assert canonical_memory_detail.status_code == 200
    assert canonical_memory_detail.json()["item"]["scope"] == "canonical"

    memory_search = client.get(
        "/api/memory/search",
        params={"query": "canonical profile private memory"},
        headers=headers,
    )
    assert memory_search.status_code == 200
    assert any(item["id"] == private_memory.id for item in memory_search.json()["saved_notes_results"])
    searched_memory_detail = client.get(f"/api/memory/{private_memory.id}", headers=headers)
    assert searched_memory_detail.json()["item"]["scope"] == "durable"

    protocols = client.get("/api/protocols", headers=headers)
    assert protocols.status_code == 200
    protocols_by_id = {item["id"]: item for item in protocols.json()["protocols"]}
    assert protocols_by_id["email-drafting-protocol"]["scope"] == "canonical"
    assert protocols_by_id["email-drafting-protocol"]["protocol"]["is_canonical"] is True
    assert protocols_by_id[private_protocol.id]["scope"] == "durable"
    assert protocols_by_id[private_protocol.id]["protocol"]["is_canonical"] is False
    assert not (user_root / "concepts" / "email-drafting-protocol.md").exists()
    assert not (user_root / "memories" / f"{canonical_memory.id}.md").exists()
    assert not (user_root / "artifacts" / f"{canonical_artifact.id}.md").exists()


def test_protocol_edit_in_experiment_writes_to_experiment_concepts(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    started = client.post("/api/experiment/start", json={"seed_from_workspace": False})
    assert started.status_code == 200
    session_id = started.json()["experiment"]["session_id"]
    session_root = repo_root / "state" / "experiments" / session_id

    updated = client.put(
        "/api/protocols/scenario_lab",
        json={
            "body": "## Protocol\n\nUse experiment-only Scenario Lab rules.",
            "variables": {"default_surface": "experiment_scenario_lab"},
        },
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["scope"] == "experiment"
    assert payload["protocol"]["variables"]["default_surface"] == "experiment_scenario_lab"
    assert (session_root / "concepts" / "scenario-lab-protocol.md").exists()
    assert not (repo_root / "concepts" / "scenario-lab-protocol.md").exists()

    fetched = client.get("/api/protocols/scenario-lab-protocol")
    assert fetched.status_code == 200
    assert fetched.json()["scope"] == "experiment"


def test_apply_protocol_control_reaches_scenario_lab_working_memory(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="scenario_lab",
            confidence=0.94,
            reason="The Navigator chose Scenario Lab with its protocol.",
            comparison_question="Which launch path should we choose?",
            branch_count=3,
            branch_labels=["focused", "conservative", "aggressive"],
            control_panel={
                "actions": [
                    {
                        "type": "apply_protocol",
                        "protocol_kind": "scenario_lab",
                        "reason": "Scenario Lab should use its reasoning protocol.",
                    },
                    {
                        "type": "open_scenario_lab",
                        "protocol_kind": None,
                        "reason": "The request asks for branches.",
                    },
                ],
                "working_memory_queries": ["scenario lab protocol"],
                "response_call": {"type": "scenario_lab", "after_working_memory": True},
            },
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario",
        lambda self, **kwargs: _scenario_plan(),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Compare three launch paths.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    recalled = {item["id"]: item for item in payload["working_memory"]}
    assert "scenario-lab-protocol" in recalled
    assert "first-principles" in recalled["scenario-lab-protocol"]["body"]
    assert "Navigator pressed apply_protocol" in recalled["scenario-lab-protocol"]["why_recalled"]
    assert recalled["scenario-lab-protocol"]["recall_reason"] == recalled["scenario-lab-protocol"]["why_recalled"]


def test_email_protocol_is_learned_and_recalled_for_matching_draft(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    def _interpret_protocol(self, **kwargs):
        if kwargs["message"].startswith("For emails"):
            return ProtocolInterpretation(
                protocol_write=build_protocol_write_from_interpretation(
                    protocol_kind="email",
                    variables={"signature": "Jordan Zhang", "style": ["concise", "business"]},
                    applies_to=["email", "business email"],
                    source_instruction=kwargs["message"],
                    existing_protocols=kwargs["existing_protocols"],
                ),
                recall_protocol_kinds=["email"],
                rationale="The user set reusable email drafting preferences.",
            )
        if kwargs["message"].startswith("Draft an email"):
            return ProtocolInterpretation(
                recall_protocol_kinds=["email"],
                rationale="The user is asking for an email draft, so the email protocol applies.",
            )
        return ProtocolInterpretation(rationale="No protocol action.")

    monkeypatch.setattr("vantage_v5.services.protocols.ProtocolInterpreter.interpret", _interpret_protocol)

    learned = client.post(
        "/api/chat",
        json={
            "message": "For emails, always sign drafts with Jordan Zhang and use a concise business tone.",
            "history": [],
        },
    )

    assert learned.status_code == 200
    learned_payload = learned.json()
    assert learned_payload["created_record"]["id"] == "email-drafting-protocol"
    assert learned_payload["created_record"]["type"] == "protocol"
    assert learned_payload["graph_action"]["type"] == "upsert_protocol"
    assert learned_payload["surface_invocation"]["intent"] == "protocol_write"
    assert learned_payload["surface_invocation"]["write_behavior"] == "committed_write"
    assert learned_payload["surface_invocation"].get("status") != "handled_by_memory_write"
    assert learned_payload["surface_invocation"].get("legacy_intent") != "memory_write"
    assert all(
        surface.get("status") not in {"handled_by_memory_write", "handled_by_concept_write"}
        for surface in learned_payload["surface_invocation"]["surfaces"]
    )
    assert learned_payload["surface_invocation"]["write_intent"]["kinds"] == ["protocol_write"]
    learned_trace = _latest_trace_payload(repo_root)["final_response"]
    assert learned_trace["turn_plan"]["write_ledger"]["categories"] == ["protocol_write"]
    assert learned_trace["turn_plan"]["write_projection"]["intended_write_kind"] == "protocol_write"
    assert learned_trace["turn_plan"]["write_projection"]["intended_write_kinds"] == ["protocol_write"]
    assert learned_trace["turn_plan"]["write_projection"]["effect_agreement"] == "aligned"
    assert learned_trace["turn_plan"]["protocol_write_authority"]["allowed"] is True

    protocols = client.get("/api/protocols")
    assert protocols.status_code == 200
    protocol_payload = protocols.json()["protocols"][0]
    assert protocol_payload["id"] == "email-drafting-protocol"
    assert protocol_payload["kind"] == "protocol"
    assert protocol_payload["source_label"] == "Custom"
    assert protocol_payload["protocol"]["is_builtin"] is False
    assert protocol_payload["protocol"]["is_canonical"] is False
    assert protocol_payload["protocol"]["overrides_builtin"] is False
    assert protocol_payload["protocol"]["overrides_canonical"] is False
    assert protocol_payload["protocol"]["variables"]["signature"] == "Jordan Zhang"

    draft = client.post(
        "/api/chat",
        json={
            "message": "Draft an email to Amy thanking her for the flowers.",
            "history": [],
        },
    )

    assert draft.status_code == 200
    draft_payload = draft.json()
    recalled = {item["id"]: item for item in draft_payload["working_memory"]}
    assert "email-drafting-protocol" in recalled
    assert recalled["email-drafting-protocol"]["type"] == "protocol"
    assert "Jordan Zhang" in recalled["email-drafting-protocol"]["body"]
    draft_trace = _latest_trace_payload(repo_root)["final_response"]
    role_projection = draft_trace["attention_recall_role_projection"]
    protocol_resources = [
        resource
        for resource in role_projection["resources"]
        if resource["resource_id"] == "email-drafting-protocol"
    ]
    assert protocol_resources
    assert {"recall_context", "protocol_guidance"} <= set(protocol_resources[0]["roles"])
    assert "protocol_guidance" in protocol_resources[0]["origins"]
    assert role_projection["roles"]["protocol_guidance"][0]["resource_id"] == "email-drafting-protocol"
    working_memory_view = draft_payload["working_memory_view"]
    assert draft_trace["working_memory_view"]["roles"]["protocol_guidance"]
    assert working_memory_view["roles"]["protocol_guidance"][0]["resource_id"] == "email-drafting-protocol"
    protocol_working_memory_resources = [
        resource
        for resource in working_memory_view["resources"]
        if resource["resource_id"] == "email-drafting-protocol"
    ]
    assert protocol_working_memory_resources
    assert {"recall_context", "protocol_guidance"} <= set(protocol_working_memory_resources[0]["roles"])
    assert len(protocol_working_memory_resources[0].get("excerpt") or "") <= 320
    assert (repo_root / "concepts" / "email-drafting-protocol.md").exists()


def test_visible_artifact_qna_does_not_suppress_protocol_update(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifacts = [
        {
            "id": "artifact:midterm-study-plan",
            "kind": "whiteboard",
            "title": "Midterm Study Plan",
            "summary": "Study plan for graph algorithms and priorities.",
            "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
        }
    ]

    def _interpret_protocol(self, **kwargs):
        return ProtocolInterpretation(
            protocol_write=build_protocol_write_from_interpretation(
                protocol_kind="email",
                variables={"signature": "Jordan Zhang"},
                applies_to=["email"],
                source_instruction=kwargs["message"],
                existing_protocols=kwargs["existing_protocols"],
            ),
            recall_protocol_kinds=["email"],
            rationale="The user set a reusable email signature.",
        )

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Visible study plan follow-up plus reusable protocol update.",
            whiteboard_mode="chat",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.protocols.ProtocolInterpreter.interpret", _interpret_protocol)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "Use graph traversal first. I also updated the email signature protocol.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Protocol updates should skip the generic meta write path.")
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        lambda self, **kwargs: ArtifactActionPlan(artifact_actions=[]),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": (
                "For emails, always sign drafts with Jordan Zhang. "
                "Can you summarize this study plan?"
            ),
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifacts[0]["content"],
            "visible_artifacts": visible_artifacts,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["intent"] == "current_artifact_followup"
    assert payload["created_record"]["id"] == "email-drafting-protocol"
    assert payload["created_record"]["type"] == "protocol"
    assert payload["graph_action"]["type"] == "upsert_protocol"
    assert (repo_root / "concepts" / "email-drafting-protocol.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["side_effect_policy"]["suppress_auto_graph_writes_reason"] is None
    assert final_response["turn_plan"]["execution"]["suppress_auto_graph_writes"] is False
    assert final_response["turn_plan"]["protocol_write_authority"]["action"] == "protocol_write"
    assert final_response["turn_plan"]["protocol_write_authority"]["allowed"] is True
    assert final_response["protocol_write_authority"]["allowed"] is True
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["protocol_write"]
    assert final_response["turn_plan"]["write_projection"]["intended_write_kind"] == "protocol_write"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_hard_no_write_blocks_protocol_update_candidate(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    visible_artifacts = [
        {
            "id": "artifact:midterm-study-plan",
            "kind": "whiteboard",
            "title": "Midterm Study Plan",
            "summary": "Study plan for graph algorithms and priorities.",
            "content": "# Midterm Study Plan\n\nPractice graph traversal first.",
        }
    ]

    def _interpret_protocol(self, **kwargs):
        return ProtocolInterpretation(
            protocol_write=build_protocol_write_from_interpretation(
                protocol_kind="email",
                variables={"signature": "Jordan Zhang"},
                applies_to=["email"],
                source_instruction=kwargs["message"],
                existing_protocols=kwargs["existing_protocols"],
            ),
            recall_protocol_kinds=["email"],
            rationale="The user set a reusable email signature.",
        )

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Preserve the visible whiteboard.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to keep the whiteboard open.",
                    },
                    {"type": "respond", "reason": "Acknowledge the preserve request."},
                ],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.protocols.ProtocolInterpreter.interpret", _interpret_protocol)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I kept the whiteboard open. I did not update the email protocol.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Hard no-write protocol turns should skip generic graph writes.")
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.artifact_mutation_compiler.ArtifactMutationCompiler.compile_for_turn",
        lambda self, **kwargs: ArtifactActionPlan(artifact_actions=[]),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "keep the whiteboard open and always sign emails with Jordan Zhang",
            "history": [],
            "workspace_id": "midterm-study-plan",
            "workspace_scope": "visible",
            "workspace_content": visible_artifacts[0]["content"],
            "visible_artifacts": visible_artifacts,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I kept the current view unchanged. I did not update the protocol."
    assert payload["surface_invocation"]["intent"] == "preserve_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert not (repo_root / "concepts" / "email-drafting-protocol.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["protocol_write_authority"]["action"] == "protocol_write"
    assert final_response["turn_plan"]["protocol_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["protocol_write_authority"]["denied_reason"] == "preserve_visible_surface"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_close_surface_with_protocol_update_intent_closes_without_protocol_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact = ArtifactStore(repo_root / "artifacts").create_artifact(
        title="Midterm Study Plan",
        card="Study plan for graph algorithms and priorities.",
        body="# Midterm Study Plan\n\nPrioritize graph traversals.",
    )
    visible_artifacts = [
        {
            "id": artifact.id,
            "kind": "whiteboard",
            "title": artifact.title,
            "summary": artifact.card,
            "content": artifact.body,
        }
    ]

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "target": "whiteboard",
                        "reason": "The user asked to close the visible whiteboard.",
                    },
                    {"type": "respond", "reason": "Acknowledge the close action."},
                ],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService.reply",
        lambda self, **kwargs: (_ for _ in ()).throw(
            AssertionError("Close visible surface should be handled before protocol writes.")
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "close the whiteboard and always sign emails with Morgan Lee",
            "history": [],
            "workspace_id": artifact.id,
            "workspace_scope": "visible",
            "workspace_content": artifact.body,
            "visible_artifacts": visible_artifacts,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_action"]["type"] == "close_visible_surface"
    assert payload["workspace_update"] is None
    assert payload["created_record"] is None
    assert payload["graph_action"] is None
    assert payload["artifact_actions"] == []
    assert not (repo_root / "concepts" / "email-drafting-protocol.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["ui_surface_action"]["mode"] == "close"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_email_protocol_updates_existing_record_in_place(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    def _interpret_protocol(self, **kwargs):
        if kwargs["message"].startswith("For emails"):
            return ProtocolInterpretation(
                protocol_write=build_protocol_write_from_interpretation(
                    protocol_kind="email",
                    variables={"signature": "Jordan Zhang"},
                    applies_to=["email"],
                    source_instruction=kwargs["message"],
                    existing_protocols=kwargs["existing_protocols"],
                ),
                recall_protocol_kinds=["email"],
                rationale="The user set a reusable email signature.",
            )
        if kwargs["message"].startswith("Change my email signature"):
            return ProtocolInterpretation(
                protocol_write=build_protocol_write_from_interpretation(
                    protocol_kind="email",
                    variables={"signature": "Dr. Jordan Zhang"},
                    applies_to=["email"],
                    source_instruction=kwargs["message"],
                    existing_protocols=kwargs["existing_protocols"],
                ),
                recall_protocol_kinds=["email"],
                rationale="The user changed a reusable email signature.",
            )
        return ProtocolInterpretation(rationale="No protocol action.")

    monkeypatch.setattr("vantage_v5.services.protocols.ProtocolInterpreter.interpret", _interpret_protocol)

    first = client.post(
        "/api/chat",
        json={
            "message": "For emails, always sign drafts with Jordan Zhang.",
            "history": [],
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/chat",
        json={
            "message": "Change my email signature to Dr. Jordan Zhang.",
            "history": [],
        },
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["created_record"]["id"] == "email-drafting-protocol"
    assert payload["graph_action"]["type"] == "upsert_protocol"

    protocol_files = list((repo_root / "concepts").glob("email-drafting-protocol*.md"))
    assert [path.name for path in protocol_files] == ["email-drafting-protocol.md"]
    protocol = ConceptStore(repo_root / "concepts").get("email-drafting-protocol")
    assert protocol.metadata["variables"]["signature"] == "Dr. Jordan Zhang"
    assert "Dr. Jordan Zhang" in protocol.body


def test_open_saved_item_rejects_protocol_records(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)
    ConceptStore(repo_root / "concepts").upsert_protocol(
        protocol_id="email-drafting-protocol",
        title="Email Drafting Protocol",
        card="Reusable email drafting guidance.",
        body="Use this for drafting emails.",
        protocol_kind="email",
        variables={},
        applies_to=["email"],
    )

    response = client.post(
        "/api/concepts/open",
        json={"record_id": "email-drafting-protocol"},
    )

    assert response.status_code == 400
    assert "cannot be reopened as whiteboard drafts" in response.json()["detail"]


def test_protocol_learning_requires_interpreter_decision(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)
    protocol_path = repo_root / "concepts" / "email-drafting-protocol.md"
    protocol_path.unlink(missing_ok=True)

    response = client.post(
        "/api/chat",
        json={
            "message": "For emails, always sign drafts with Jordan Zhang.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert not protocol_path.exists()


def test_multi_user_auth_isolates_markdown_storage(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
            "jordan": "jordan-password",
        },
    )

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["multi_user"] is True
    assert health.json()["user"] is None

    unauthenticated_workspace = client.get("/api/workspace")
    assert unauthenticated_workspace.status_code == 401
    assert unauthenticated_workspace.json()["detail"] == "Authentication required."
    assert "www-authenticate" not in unauthenticated_workspace.headers

    eden_auth = _basic_auth_header("eden", "eden-password")
    jordan_auth = _basic_auth_header("jordan", "jordan-password")
    bad_cross_auth = _basic_auth_header("eden", "jordan-password")

    assert client.get("/api/workspace", headers=bad_cross_auth).status_code == 401

    eden_health = client.get("/api/health", headers=eden_auth)
    assert eden_health.status_code == 200
    assert eden_health.json()["user"] == {"id": "eden"}

    eden_update = client.post(
        "/api/workspace",
        headers=eden_auth,
        json={
            "workspace_id": "v5-milestone-1",
            "content": "# Eden Private Draft\n\nOnly Eden should see this.",
        },
    )
    assert eden_update.status_code == 200
    assert "Only Eden" in eden_update.json()["content"]

    eden_workspace = client.get("/api/workspace", headers=eden_auth)
    assert eden_workspace.status_code == 200
    assert "Only Eden" in eden_workspace.json()["content"]

    jordan_workspace = client.get("/api/workspace", headers=jordan_auth)
    assert jordan_workspace.status_code == 200
    assert "Only Eden" not in jordan_workspace.json()["content"]
    assert jordan_workspace.json()["workspace_id"] == "v5-milestone-1"

    eden_memory = client.get("/api/memory", headers=eden_auth)
    jordan_memory = client.get("/api/memory", headers=jordan_auth)
    assert eden_memory.status_code == 200
    assert jordan_memory.status_code == 200
    assert eden_memory.json()["counts"]["saved_notes"] == 1
    assert jordan_memory.json()["counts"]["saved_notes"] == 0

    eden_workspace_path = repo_root / "users" / "eden" / "workspaces" / "v5-milestone-1.md"
    jordan_workspace_path = repo_root / "users" / "jordan" / "workspaces" / "v5-milestone-1.md"
    assert "Only Eden" in eden_workspace_path.read_text(encoding="utf-8")
    assert "Only Eden" not in jordan_workspace_path.read_text(encoding="utf-8")


def test_chat_can_route_into_scenario_lab_and_open_branch(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["assistant_message"].startswith(
        "Recommendation: Ship the reduced-scope branch as the milestone centerpiece"
    )
    assert "Why: Reduced Scope is the strongest first proof" in payload["assistant_message"]
    assert "Tradeoffs: Baseline keeps breadth but dilutes the proof point;" in payload["assistant_message"]
    assert "Saved the full Scenario Lab comparison with 3 branches: Baseline, Reduced Scope, Fast Launch." in payload["assistant_message"]
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "recall"
    assert payload["response_mode"]["legacy_grounding_mode"] == "working_memory"
    assert payload["response_mode"]["grounding_sources"] == ["recall"]
    assert payload["response_mode"]["context_sources"] == ["recall"]
    assert payload["response_mode"]["legacy_context_sources"] == ["working_memory"]
    assert payload["response_mode"]["recall_count"] == len(payload["recall"])
    assert payload["response_mode"]["working_memory_count"] == len(payload["working_memory"])
    assert payload["response_mode"]["label"] == "Recall"
    assert payload["turn_interpretation"]["mode"] == "scenario_lab"
    assert payload["turn_interpretation"]["reason"] == "The turn asks for structured comparison across alternatives."
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] is None
    assert payload["semantic_frame"]["target_surface"] == "scenario_lab"
    assert payload["semantic_frame"]["task_type"] == "scenario_comparison"
    assert payload["semantic_frame"]["user_goal"] == "Compare alternatives and make the tradeoffs explicit."
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["graph_action"] is None
    assert payload["created_record"]["source"] == "artifact"
    assert payload["created_record"]["type"] == "scenario_comparison"
    assert payload["created_record"]["scenario_kind"] == "comparison"
    assert payload["created_record"]["scope"] == "durable"
    assert payload["learned"] == [payload["created_record"]]
    assert payload["pinned_context"] is None
    assert payload["pinned_context_id"] is None
    assert payload["selected_record"] is None
    assert payload["selected_record_id"] is None
    assert payload["scenario_lab"]["comparison_artifact"]["id"] == payload["created_record"]["id"]
    assert payload["scenario_lab"]["comparison_artifact"]["scenario_kind"] == "comparison"
    assert payload["scenario_lab"]["comparison_artifact"]["artifact_origin"] == "scenario_lab"
    assert payload["scenario_lab"]["comparison_artifact"]["artifact_lifecycle"] == "comparison_hub"
    assert payload["scenario_lab"]["comparison_question"] == "What if we cut milestone 1 scope by 40%?"
    assert len(payload["scenario_lab"]["branches"]) == 3
    assert len(payload["recall"]) >= 1

    artifact_id = payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{artifact_id}.md").exists()

    expected_branch_index = [
        {
            "workspace_id": branch["workspace_id"],
            "title": branch["title"],
            "label": branch["label"],
            "summary": branch["summary"],
        }
        for branch in payload["scenario_lab"]["branches"]
    ]
    branch_ids = [branch["workspace_id"] for branch in payload["scenario_lab"]["branches"]]
    assert branch_ids == [
        "v5-milestone-1--baseline",
        "v5-milestone-1--reduced-scope",
        "v5-milestone-1--fast-launch",
    ]
    assert payload["created_record"]["base_workspace_id"] == "v5-milestone-1"
    assert payload["created_record"]["branch_workspace_ids"] == branch_ids
    assert payload["created_record"]["branch_index"] == expected_branch_index
    assert payload["created_record"]["artifact_origin"] == "scenario_lab"
    assert payload["created_record"]["artifact_lifecycle"] == "comparison_hub"
    assert payload["created_record"]["scenario_namespace_id"] == "v5-milestone-1"
    assert payload["created_record"]["namespace_mode"] == "anchored"
    assert payload["scenario_lab"]["comparison_artifact"]["branch_workspace_ids"] == branch_ids
    assert payload["scenario_lab"]["comparison_artifact"]["branch_index"] == expected_branch_index
    for branch_id in branch_ids:
        branch_path = repo_root / "workspaces" / f"{branch_id}.md"
        assert branch_path.exists()
        assert "Status: Counterfactual Branch" in branch_path.read_text(encoding="utf-8")
    for branch in payload["scenario_lab"]["branches"]:
        assert branch["scenario_kind"] == "branch"
        assert branch["base_workspace_id"] == "v5-milestone-1"
        assert branch["comparison_question"] == "What if we cut milestone 1 scope by 40%?"
        assert branch["comparison_artifact_id"] == artifact_id
        assert branch["scenario_namespace_id"] == "v5-milestone-1"
        assert branch["namespace_mode"] == "anchored"

    opened = client.post("/api/workspace/open", json={"workspace_id": branch_ids[1]})
    assert opened.status_code == 200
    opened_payload = opened.json()
    assert opened_payload["workspace_id"] == "v5-milestone-1--reduced-scope"
    assert opened_payload["scope"] == "durable"
    assert opened_payload["scenario_kind"] == "branch"
    assert opened_payload["scenario"] == {
        "scenario_kind": "branch",
        "base_workspace_id": "v5-milestone-1",
        "comparison_question": "What if we cut milestone 1 scope by 40%?",
        "branch_label": "reduced-scope",
        "comparison_artifact_id": artifact_id,
        "scenario_namespace_id": "v5-milestone-1",
        "namespace_mode": "anchored",
    }
    assert "# Reduced Scope" in opened_payload["content"]

    artifact_item = client.get(f"/api/memory/{artifact_id}")
    assert artifact_item.status_code == 200
    artifact_payload = artifact_item.json()["item"]
    assert artifact_payload["scenario_kind"] == "comparison"
    assert artifact_payload["scenario"] == {
        "scenario_kind": "comparison",
        "base_workspace_id": "v5-milestone-1",
        "comparison_question": "What if we cut milestone 1 scope by 40%?",
        "comparison_artifact_id": artifact_id,
        "branch_workspace_ids": branch_ids,
        "branch_index": expected_branch_index,
        "scenario_namespace_id": "v5-milestone-1",
        "namespace_mode": "anchored",
    }

    active_workspace = client.get("/api/workspace")
    assert active_workspace.status_code == 200
    active_workspace_payload = active_workspace.json()
    assert active_workspace_payload["workspace_id"] == "v5-milestone-1--reduced-scope"
    assert active_workspace_payload["scenario"] == opened_payload["scenario"]


def test_scenario_lab_can_be_recent_chat_grounded_without_best_guess_preface(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [
                {
                    "user_message": "Compare our launch options.",
                    "assistant_message": "Here are the main options and tradeoffs.",
                }
            ],
            "workspace_scope": "excluded",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["working_memory"] == []
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "recent_chat"
    assert payload["response_mode"]["label"] == "Recent Chat"
    assert payload["response_mode"]["context_sources"] == ["recent_chat"]
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_scenario_lab_uses_neutralized_title_in_saved_comparison_body(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _generic_launch_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario",
        lambda self, **kwargs: _outcome_biased_launch_plan(),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Compare three launch strategies for a new product.",
            "history": [],
            "workspace_id": "thanksgiving-holiday",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    artifact_id = payload["created_record"]["id"]
    artifact_body = (repo_root / "artifacts" / f"{artifact_id}.md").read_text(encoding="utf-8")

    assert payload["created_record"]["title"] == "Launch Strategy Comparison"
    assert "\n# Launch Strategy Comparison\n" in artifact_body
    assert "\n# Focused MVP Is Best\n" not in artifact_body


def test_scenario_lab_can_be_whiteboard_grounded_without_best_guess_preface(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [],
            "workspace_scope": "visible",
            "workspace_content": "# Draft Plan\n\nCurrent milestone assumptions live here.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["working_memory"] == []
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "whiteboard"
    assert payload["response_mode"]["label"] == "Whiteboard"
    assert payload["response_mode"]["context_sources"] == ["whiteboard"]
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_scenario_lab_mixed_context_is_grounded_without_best_guess(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [
                {
                    "user_message": "Let's talk through the milestone 1 plan.",
                    "assistant_message": "Absolutely, we can compare the tradeoffs.",
                }
            ],
            "workspace_scope": "visible",
            "workspace_content": "# Milestone 1\n\nThe current whiteboard draft is still in play.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["grounding_sources"] == ["whiteboard", "recent_chat"]
    assert payload["response_mode"]["context_sources"] == ["whiteboard", "recent_chat"]
    assert payload["response_mode"]["working_memory_count"] == 0
    assert "Best Guess" not in payload["response_mode"]["label"]


def test_scenario_lab_without_grounded_context_remains_explicit_best_guess(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [],
            "workspace_scope": "excluded",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["response_mode"]["kind"] == "best_guess"
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["grounding_sources"] == []
    assert payload["response_mode"]["context_sources"] == []
    assert payload["response_mode"]["label"] == "Best Guess"
    assert payload["response_mode"]["note"] == "No grounded context supported this answer."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_scenario_lab_can_be_pending_whiteboard_grounded_without_best_guess_preface(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _build_scenario(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return _scenario_plan()

    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", _build_scenario)

    response = client.post(
        "/api/chat",
        json={
            "message": "yes, compare those launch strategies",
            "history": [],
            "workspace_scope": "excluded",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["working_memory"] == []
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "pending_whiteboard"
    assert payload["response_mode"]["label"] == "Prior Whiteboard"
    assert payload["response_mode"]["context_sources"] == ["pending_whiteboard"]
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_scenario_lab_mixed_context_note_mentions_pending_whiteboard_truthfully(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "open the whiteboard for the milestone 1 scope comparison",
            "history": [],
            "workspace_scope": "excluded",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["grounding_sources"] == ["recall", "pending_whiteboard"]
    assert payload["response_mode"]["context_sources"] == ["recall", "pending_whiteboard"]
    assert payload["response_mode"]["legacy_context_sources"] == ["working_memory", "pending_whiteboard"]
    assert payload["response_mode"]["label"] == "Recall + Prior Whiteboard"
    assert payload["response_mode"]["note"] == "Supported by Recall and the prior whiteboard."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_low_confidence_navigation_stays_in_normal_chat(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: _scenario_navigation(confidence=0.33),
    )

    def _should_not_run(*args, **kwargs):
        raise AssertionError("Scenario Lab should not run for a low-confidence navigation decision.")

    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService.run", _should_not_run)

    response = client.post(
        "/api/chat",
        json={
            "message": "Can you think through alternative launch options?",
            "history": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback"
    assert "scenario_lab" not in payload
    assert not (repo_root / "workspaces" / "v5-milestone-1--baseline.md").exists()


def test_chat_openai_reply_failure_falls_back_to_deterministic_response(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _raise_runtime_error_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Fallback chat should still complete after reply failure."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What color should the launch button be?",
            "history": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback"
    assert "could not complete the model-backed answer" in payload["assistant_message"]
    assert "Fallback mode" not in payload["assistant_message"]
    assert "Relevant memory trace" not in payload["assistant_message"]


def test_chat_reply_failure_still_drafts_fresh_whiteboard_request(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _raise_runtime_error_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Fallback whiteboard drafts should stay temporary until the user saves them.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Open a fresh whiteboard essay titled Why Design Partners Make AI Products Better.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "draft",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback"
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["title"] == "Why Design Partners Make Ai Products Better"
    assert payload["workspace_update"]["content"].startswith("# Why Design Partners Make Ai Products Better")
    assert "Fallback mode" not in payload["assistant_message"]
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_chat_workspace_signal_failures_still_surface_as_server_errors(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", lambda self, **kwargs: "CHAT_RESPONSE: Draft ready.")

    def _boom(*args, **kwargs):
        raise RuntimeError("parse boom")

    monkeypatch.setattr("vantage_v5.services.chat._extract_workspace_signal", _boom)

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft an email for me.",
            "history": [],
        },
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Chat request failed unexpectedly."


def test_chat_openai_vetting_failure_falls_back_to_deterministic_selection(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService._openai_vet", _raise_runtime_error_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I used the fallback vetted context.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Fallback vetting should still allow a normal reply."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What do we already know about the milestone?",
            "history": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "openai"
    assert "Deterministic score threshold over merged memory search candidates." in payload["vetting"]["rationale"]
    assert payload["assistant_message"] == "I used the fallback vetted context."


def test_scenario_lab_failure_is_explicit_in_payload(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: _scenario_navigation(),
    )
    monkeypatch.setattr(
        "vantage_v5.services.scenario_lab.ScenarioLabService.run",
        lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("scenario lab boom")),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Fallback chat after Scenario Lab failure."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback"
    assert payload["scenario_lab"]["status"] == "failed"
    assert payload["turn_interpretation"]["mode"] == "scenario_lab"
    assert payload["scenario_lab"]["chat_turn_mode"] == "fallback"
    assert payload["scenario_lab"]["fallback_mode"] == "chat"
    assert payload["scenario_lab"]["navigation"]["mode"] == "scenario_lab"
    assert payload["scenario_lab"]["error"]["type"] == "RuntimeError"
    assert payload["scenario_lab"]["error"]["message"] == (
        "Scenario Lab could not complete this turn. The turn stayed in chat so you can retry or continue from here."
    )
    assert payload["scenario_lab_error"]["message"] == payload["scenario_lab"]["error"]["message"]
    assert "scenario lab boom" not in payload["scenario_lab_error"]["message"]
    assert payload["assistant_message"]


def test_generic_scenario_uses_detached_namespace_instead_of_workspace_id(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _generic_launch_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _generic_launch_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "We need to choose a launch strategy for a new software product.",
            "history": [],
            "workspace_id": "thanksgiving-holiday",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"

    artifact_id = payload["created_record"]["id"]
    branch_ids = [branch["workspace_id"] for branch in payload["scenario_lab"]["branches"]]
    expected_branch_index = [
        {
            "workspace_id": branch["workspace_id"],
            "title": branch["title"],
            "label": branch["label"],
            "summary": branch["summary"],
        }
        for branch in payload["scenario_lab"]["branches"]
    ]
    assert branch_ids == [
        "launch-strategy--conservative-rollout",
        "launch-strategy--focused-mvp",
        "launch-strategy--aggressive-launch",
    ]
    assert payload["created_record"]["scenario_namespace_id"] == "launch-strategy"
    assert payload["created_record"]["namespace_mode"] == "detached"
    assert payload["created_record"]["branch_workspace_ids"] == branch_ids
    assert payload["created_record"]["branch_index"] == expected_branch_index
    assert all(not branch_id.startswith("thanksgiving-holiday--") for branch_id in branch_ids)
    for branch_id in branch_ids:
        assert (repo_root / "workspaces" / f"{branch_id}.md").exists()
    for branch in payload["scenario_lab"]["branches"]:
        assert branch["scenario_kind"] == "branch"
        assert branch["base_workspace_id"] == "thanksgiving-holiday"
        assert branch["comparison_artifact_id"] == artifact_id
        assert branch["scenario_namespace_id"] == "launch-strategy"
        assert branch["namespace_mode"] == "detached"

    opened = client.post("/api/workspace/open", json={"workspace_id": branch_ids[0]})
    assert opened.status_code == 200
    opened_payload = opened.json()
    assert opened_payload["scenario_kind"] == "branch"
    assert opened_payload["scenario"]["scenario_namespace_id"] == "launch-strategy"
    assert opened_payload["scenario"]["namespace_mode"] == "detached"

    artifact_item = client.get(f"/api/memory/{artifact_id}")
    assert artifact_item.status_code == 200
    artifact_payload = artifact_item.json()["item"]
    assert artifact_payload["scenario_kind"] == "comparison"
    assert artifact_payload["scenario"]["branch_workspace_ids"] == branch_ids
    assert artifact_payload["scenario"]["branch_index"] == expected_branch_index
    assert artifact_payload["scenario"]["scenario_namespace_id"] == "launch-strategy"
    assert artifact_payload["scenario"]["namespace_mode"] == "detached"


def test_workspace_transform_helpers_keep_branch_scenario_metadata_for_chat(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    branch_workspace_id = "v5-milestone-1--reduced-scope"
    branch_content = (
        "# Reduced Scope\n\n"
        "## Scenario Metadata\n"
        "- scenario_kind: branch\n"
        "- base_workspace_id: v5-milestone-1\n"
        "- comparison_question: What if we cut milestone 1 scope by 40%?\n"
        "- branch_label: reduced-scope\n"
        "- comparison_artifact_id: milestone-1-scenario-comparison\n"
        "- scenario_namespace_id: v5-milestone-1\n"
        "- namespace_mode: anchored\n\n"
        "## Thesis\n"
        "Keep Scenario Lab as the centerpiece.\n"
    )
    (repo_root / "workspaces" / f"{branch_workspace_id}.md").write_text(branch_content, encoding="utf-8")

    route_call = {"count": 0}
    expected_scenario = {
        "scenario_kind": "branch",
        "base_workspace_id": "v5-milestone-1",
        "comparison_question": "What if we cut milestone 1 scope by 40%?",
        "branch_label": "reduced-scope",
        "comparison_artifact_id": "milestone-1-scenario-comparison",
        "scenario_namespace_id": "v5-milestone-1",
        "namespace_mode": "anchored",
    }

    def _route(self, **kwargs):
        route_call["count"] += 1
        workspace = kwargs["workspace"]
        assert workspace.workspace_id == branch_workspace_id
        assert workspace.scenario_metadata == expected_scenario
        if route_call["count"] == 1:
            assert workspace.content == ""
        else:
            assert "## Live Edit" in workspace.content
            assert workspace.scenario_metadata == expected_scenario
        return NavigationDecision(
            mode="chat",
            confidence=0.82,
            reason="Keep the turn in normal chat while preserving visible scenario metadata.",
            preserve_selected_record=None,
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "The branch metadata should stay available without forcing a rerun.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="No durable write needed for the branch metadata check."),
    )

    hidden = client.post(
        "/api/chat",
        json={
            "message": "Do not rerun anything yet.",
            "history": [],
            "workspace_id": branch_workspace_id,
            "workspace_scope": "excluded",
        },
    )
    assert hidden.status_code == 200
    hidden_payload = hidden.json()
    assert hidden_payload["workspace"]["scenario_kind"] == "branch"
    assert hidden_payload["workspace"]["scenario"] == expected_scenario
    assert hidden_payload["workspace"]["context_scope"] == "excluded"

    visible = client.post(
        "/api/chat",
        json={
            "message": "Add one note to the current branch draft.",
            "history": [],
            "workspace_id": branch_workspace_id,
            "workspace_scope": "visible",
            "workspace_content": f"{branch_content}\n## Live Edit\nAdd a sharper milestone proof point.\n",
        },
    )
    assert visible.status_code == 200
    visible_payload = visible.json()
    assert visible_payload["workspace"]["scenario_kind"] == "branch"
    assert visible_payload["workspace"]["scenario"] == expected_scenario
    assert visible_payload["workspace"]["context_scope"] == "visible"
    assert "## Live Edit" in (visible_payload["workspace"]["content"] or "")


def test_workspace_save_and_reopen_preserves_branch_identity_without_metadata_block(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    branch_workspace_id = "v5-milestone-1--reduced-scope"
    branch_content = (
        "# Reduced Scope\n\n"
        "## Scenario Metadata\n"
        "- scenario_kind: branch\n"
        "- base_workspace_id: v5-milestone-1\n"
        "- comparison_question: What if we cut milestone 1 scope by 40%?\n"
        "- branch_label: reduced-scope\n"
        "- comparison_artifact_id: milestone-1-scenario-comparison\n"
        "- scenario_namespace_id: v5-milestone-1\n"
        "- namespace_mode: anchored\n\n"
        "## Thesis\n"
        "Keep Scenario Lab as the centerpiece.\n"
    )
    (repo_root / "workspaces" / f"{branch_workspace_id}.md").write_text(branch_content, encoding="utf-8")

    expected_scenario = {
        "scenario_kind": "branch",
        "base_workspace_id": "v5-milestone-1",
        "comparison_question": "What if we cut milestone 1 scope by 40%?",
        "branch_label": "reduced-scope",
        "comparison_artifact_id": "milestone-1-scenario-comparison",
        "scenario_namespace_id": "v5-milestone-1",
        "namespace_mode": "anchored",
    }

    saved = client.post(
        "/api/workspace",
        json={
            "workspace_id": branch_workspace_id,
            "content": "# Reduced Scope\n\n## Thesis\nKeep Scenario Lab as the centerpiece, but tighten the milestone proof.\n",
        },
    )
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["workspace_id"] == branch_workspace_id
    assert saved_payload["scenario_kind"] == "branch"
    assert saved_payload["scenario"] == expected_scenario
    assert "## Scenario Metadata" in (saved_payload["content"] or "")

    reopened = client.post("/api/workspace/open", json={"workspace_id": branch_workspace_id})
    assert reopened.status_code == 200
    reopened_payload = reopened.json()
    assert reopened_payload["workspace_id"] == branch_workspace_id
    assert reopened_payload["scenario_kind"] == "branch"
    assert reopened_payload["scenario"] == expected_scenario
    assert "## Scenario Metadata" in (reopened_payload["content"] or "")


def test_workspace_open_missing_workspace_returns_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post("/api/workspace/open", json={"workspace_id": "missing-workspace"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace 'missing-workspace' was not found."


def test_follow_up_on_selected_scenario_artifact_stays_in_chat(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    call_count = {"route": 0}
    created_artifact_id = {"value": None}
    created_branch_ids = {"value": []}
    created_branch_index = {"value": []}

    def _route(self, **kwargs):
        call_count["route"] += 1
        if call_count["route"] == 1:
            return _generic_launch_navigation()
        selected_record = kwargs.get("selected_record")
        assert selected_record is not None
        assert selected_record["id"] == created_artifact_id["value"]
        assert selected_record["type"] == "scenario_comparison"
        assert selected_record["scenario_kind"] == "comparison"
        assert selected_record["is_scenario_comparison"] is True
        assert selected_record["scenario"] == {
            "scenario_kind": "comparison",
            "base_workspace_id": "thanksgiving-holiday",
            "comparison_question": "Which launch strategy is best for a new software product?",
            "comparison_artifact_id": created_artifact_id["value"],
            "branch_workspace_ids": created_branch_ids["value"],
            "branch_index": created_branch_index["value"],
            "scenario_namespace_id": "launch-strategy",
            "namespace_mode": "detached",
        }
        return NavigationDecision(
            mode="chat",
            confidence=0.97,
            reason="This is a follow-up on the selected scenario comparison artifact, so normal chat should answer from it.",
            preserve_selected_record=True,
            selected_record_reason="The selected scenario comparison artifact remains the continuity anchor.",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _generic_launch_plan())
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I recommend the focused MVP launch because it preserves speed and learning without taking on the aggressive launch downside.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Follow-up answer over a selected scenario artifact."),
    )

    initial = client.post(
        "/api/chat",
        json={
            "message": "A small team is preparing to launch a new software product with limited time and budget. Create three scenario branches: conservative rollout, focused MVP launch, and aggressive feature launch. Compare tradeoffs, risks, and next steps, then recommend one.",
            "history": [],
            "workspace_id": "thanksgiving-holiday",
        },
    )
    assert initial.status_code == 200
    initial_payload = initial.json()
    assert initial_payload["mode"] == "scenario_lab"
    created_artifact_id["value"] = initial_payload["created_record"]["id"]
    created_branch_ids["value"] = [branch["workspace_id"] for branch in initial_payload["scenario_lab"]["branches"]]
    created_branch_index["value"] = [
        {
            "workspace_id": branch["workspace_id"],
            "title": branch["title"],
            "label": branch["label"],
            "summary": branch["summary"],
        }
        for branch in initial_payload["scenario_lab"]["branches"]
    ]

    follow_up = client.post(
        "/api/chat",
        json={
            "message": "which one do you recommend?",
            "history": [
                {
                    "user_message": initial_payload["user_message"],
                    "assistant_message": initial_payload["assistant_message"],
                }
            ],
            "workspace_id": "thanksgiving-holiday",
            "selected_record_id": created_artifact_id["value"],
        },
    )
    assert follow_up.status_code == 200
    follow_up_payload = follow_up.json()
    assert follow_up_payload["mode"] == "openai"
    assert "scenario_lab" not in follow_up_payload
    assert "focused MVP launch" in follow_up_payload["assistant_message"]
    assert follow_up_payload["meta_action"]["action"] == "no_op"
    assert any(item["id"] == created_artifact_id["value"] for item in follow_up_payload["working_memory"])
    assert len(follow_up_payload["working_memory"]) <= 5
    assert follow_up_payload["selected_record"]["scenario_kind"] == "comparison"
    assert follow_up_payload["selected_record"]["scenario"]["branch_workspace_ids"] == created_branch_ids["value"]
    assert follow_up_payload["selected_record"]["scenario"]["branch_index"] == created_branch_index["value"]
    assert follow_up_payload["selected_record"]["scenario"]["comparison_artifact_id"] == created_artifact_id["value"]
    assert follow_up_payload["turn_interpretation"]["preserve_selected_record"] is True
    assert follow_up_payload["turn_interpretation"]["selected_record_reason"] == "The selected scenario comparison artifact remains the continuity anchor."


def test_scenario_lab_respects_navigator_selected_record_override(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    (repo_root / "artifacts" / "launch-comparison.md").write_text(
        (
            "---\n"
            "id: launch-comparison\n"
            "title: Launch Strategy Comparison\n"
            "type: scenario_comparison\n"
            "card: Comparison artifact for launch strategy branches.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Baseline versus constrained versus aggressive launch options.\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="scenario_lab",
            confidence=0.96,
            reason="Create a fresh scenario comparison rather than follow the selected artifact.",
            comparison_question="Compare three launch strategies for a new product.",
            branch_count=3,
            branch_labels=["baseline", "constrained", "aggressive"],
            preserve_selected_record=False,
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.search.ConceptSearchService.search_context",
        lambda self, **kwargs: [
            CandidateMemory(
                id="launch-heuristics",
                title="Launch Heuristics",
                type="concept",
                card="General launch-planning heuristics.",
                score=8.9,
                reason="Useful planning context for a new comparison.",
                source="concept",
                trust="high",
            )
        ],
    )
    monkeypatch.setattr(
        "vantage_v5.services.vetting.ConceptVettingService.vet",
        lambda self, *, message, candidates, continuity_hint=None, visible_artifacts=None: (
            candidates[:1],
            {
                "selected_ids": [candidate.id for candidate in candidates[:1]],
                "none_relevant": False,
                "rationale": "Selected the fresh planning context without reviving the old comparison artifact.",
            },
        ),
    )

    def _build_scenario(self, **kwargs):
        assert kwargs["selected_record"] is None
        return _generic_launch_plan()

    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", _build_scenario)

    response = client.post(
        "/api/chat",
        json={
            "message": "Compare three launch strategies for a new product.",
            "history": [
                {
                    "user_message": "Which one do you recommend?",
                    "assistant_message": "Focused MVP is best for the earlier comparison.",
                }
            ],
            "workspace_id": "thanksgiving-holiday",
            "selected_record_id": "launch-comparison",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert all(item["id"] != "launch-comparison" for item in payload["working_memory"])
    assert payload["turn_interpretation"]["preserve_selected_record"] is False


def test_scenario_lab_selected_record_payload_preserves_legacy_comparison_lineage(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    (repo_root / "artifacts" / "launch-comparison.md").write_text(
        (
            "---\n"
            "id: launch-comparison\n"
            "title: Launch Strategy Comparison\n"
            "type: scenario_comparison\n"
            "card: Comparison artifact for launch strategy branches.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from:\n"
            "  - thanksgiving-holiday\n"
            "  - launch-strategy--conservative-rollout\n"
            "  - launch-strategy--focused-mvp\n"
            "  - launch-strategy--aggressive-launch\n"
            "status: active\n"
            "---\n\n"
            "Baseline versus focused MVP versus aggressive launch options.\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="scenario_lab",
            confidence=0.98,
            reason="The user is continuing the selected comparison artifact inside Scenario Lab.",
            comparison_question="Compare three launch strategies for a new product.",
            branch_count=3,
            branch_labels=["conservative-rollout", "focused-mvp", "aggressive-launch"],
            preserve_selected_record=True,
            selected_record_reason="Keep the selected scenario comparison artifact in focus.",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    expected_scenario = {
        "scenario_kind": "comparison",
        "base_workspace_id": "thanksgiving-holiday",
        "comparison_artifact_id": "launch-comparison",
        "branch_workspace_ids": [
            "launch-strategy--conservative-rollout",
            "launch-strategy--focused-mvp",
            "launch-strategy--aggressive-launch",
        ],
        "scenario_namespace_id": "launch-strategy",
        "namespace_mode": "detached",
    }

    def _build_scenario(self, **kwargs):
        selected_payload = kwargs["selected_record_payload"]
        assert kwargs["selected_record"] is not None
        assert selected_payload is not None
        assert selected_payload["id"] == "launch-comparison"
        assert selected_payload["comes_from"] == [
            "thanksgiving-holiday",
            "launch-strategy--conservative-rollout",
            "launch-strategy--focused-mvp",
            "launch-strategy--aggressive-launch",
        ]
        assert selected_payload["lineage_kind"] == "provenance"
        assert selected_payload["derived_from_id"] == "thanksgiving-holiday"
        assert selected_payload["revision_parent_id"] is None
        assert selected_payload["scenario_kind"] == "comparison"
        assert selected_payload["scenario"] == expected_scenario
        assert selected_payload["base_workspace_id"] == "thanksgiving-holiday"
        assert selected_payload["branch_workspace_ids"] == expected_scenario["branch_workspace_ids"]
        assert selected_payload["scenario_namespace_id"] == "launch-strategy"
        assert selected_payload["namespace_mode"] == "detached"
        return _generic_launch_plan()

    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", _build_scenario)

    response = client.post(
        "/api/chat",
        json={
            "message": "Compare three launch strategies for a new product.",
            "history": [
                {
                    "user_message": "Which one do you recommend?",
                    "assistant_message": "Focused MVP is best for the earlier comparison.",
                }
            ],
            "workspace_id": "thanksgiving-holiday",
            "selected_record_id": "launch-comparison",
        },
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "scenario_lab"


def test_generic_legacy_comparison_artifact_recovers_scenario_metadata_from_body(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    (repo_root / "artifacts" / "legacy-launch-comparison.md").write_text(
        (
            "---\n"
            "id: legacy-launch-comparison\n"
            "title: Legacy Launch Comparison\n"
            "type: artifact\n"
            "card: Older comparison artifact before explicit scenario typing.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from:\n"
            "  - thanksgiving-holiday\n"
            "  - launch-strategy--conservative-rollout\n"
            "  - launch-strategy--focused-mvp\n"
            "  - launch-strategy--aggressive-launch\n"
            "status: active\n"
            "---\n\n"
            "# Legacy Launch Comparison\n\n"
            "Base Workspace: thanksgiving-holiday\n"
            "Question: Which launch approach should we choose?\n\n"
            "## Branches Compared\n"
            "- launch-strategy--conservative-rollout\n"
            "- launch-strategy--focused-mvp\n"
            "- launch-strategy--aggressive-launch\n\n"
            "## Recommendation\n"
            "Focused MVP is the best balance of learning and risk.\n"
        ),
        encoding="utf-8",
    )

    response = client.get("/api/memory/legacy-launch-comparison")

    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["type"] == "artifact"
    assert payload["scenario_kind"] == "comparison"
    assert payload["scenario"] == {
        "scenario_kind": "comparison",
        "base_workspace_id": "thanksgiving-holiday",
        "comparison_question": "Which launch approach should we choose?",
        "comparison_artifact_id": "legacy-launch-comparison",
        "branch_workspace_ids": [
            "launch-strategy--conservative-rollout",
            "launch-strategy--focused-mvp",
            "launch-strategy--aggressive-launch",
        ],
        "scenario_namespace_id": "launch-strategy",
        "namespace_mode": "detached",
    }


def test_comparison_artifact_frontmatter_branch_index_surfaces_without_body_index(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    (repo_root / "artifacts" / "frontmatter-launch-comparison.md").write_text(
        (
            "---\n"
            "id: frontmatter-launch-comparison\n"
            "title: Frontmatter Launch Comparison\n"
            "type: scenario_comparison\n"
            "card: Comparison artifact with branch index in frontmatter only.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from:\n"
            "  - thanksgiving-holiday\n"
            "  - launch-strategy--conservative-rollout\n"
            "  - launch-strategy--focused-mvp\n"
            "status: active\n"
            "scenario_kind: comparison\n"
            "base_workspace_id: thanksgiving-holiday\n"
            "comparison_question: Which launch approach should we choose?\n"
            "comparison_artifact_id: frontmatter-launch-comparison\n"
            "branch_workspace_ids:\n"
            "  - launch-strategy--conservative-rollout\n"
            "  - launch-strategy--focused-mvp\n"
            "branch_index:\n"
            "  - workspace_id: launch-strategy--conservative-rollout\n"
            "    title: Conservative Rollout\n"
            "    label: conservative-rollout\n"
            "    summary: Lower risk of catastrophic failure.\n"
            "  - workspace_id: launch-strategy--focused-mvp\n"
            "    title: Focused MVP\n"
            "    label: focused-mvp\n"
            "    summary: Accelerated learning from a real user base.\n"
            "scenario_namespace_id: launch-strategy\n"
            "namespace_mode: detached\n"
            "---\n\n"
            "# Frontmatter Launch Comparison\n\n"
            "Base Workspace: thanksgiving-holiday\n"
            "Question: Which launch approach should we choose?\n\n"
            "## Branches Compared\n"
            "- launch-strategy--conservative-rollout\n"
            "- launch-strategy--focused-mvp\n\n"
            "## Recommendation\n"
            "Focused MVP is the best balance of learning and risk.\n"
        ),
        encoding="utf-8",
    )

    response = client.get("/api/memory/frontmatter-launch-comparison")

    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["scenario_kind"] == "comparison"
    assert payload["scenario"]["branch_index"] == [
        {
            "workspace_id": "launch-strategy--conservative-rollout",
            "title": "Conservative Rollout",
            "label": "conservative-rollout",
            "summary": "Lower risk of catastrophic failure.",
        },
        {
            "workspace_id": "launch-strategy--focused-mvp",
            "title": "Focused MVP",
            "label": "focused-mvp",
            "summary": "Accelerated learning from a real user base.",
        },
    ]


def test_low_context_follow_up_keeps_selected_concept_in_turn_memory(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    (repo_root / "concepts" / "rules-of-hangman-game.md").write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Short follow-up should keep the selected concept in scope."),
    )

    follow_up = client.post(
        "/api/chat",
        json={
            "message": "a",
            "history": [
                {
                    "user_message": "let us play with these settings",
                    "assistant_message": "Great! We'll play Hangman with 6 max incorrect guesses.",
                }
            ],
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert follow_up.status_code == 200
    follow_up_payload = follow_up.json()
    assert follow_up_payload["mode"] == "fallback"
    assert any(item["id"] == "rules-of-hangman-game" for item in follow_up_payload["concept_cards"])
    assert "Relevant concepts:" not in follow_up_payload["assistant_message"]
    assert "local context" in follow_up_payload["assistant_message"]
    assert "rules-of-hangman-game" in follow_up_payload["vetting"]["selected_ids"]
    assert follow_up_payload["vetting"]["none_relevant"] is False
    assert follow_up_payload["response_mode"]["kind"] == "grounded"
    assert "continuity context" in follow_up_payload["vetting"]["rationale"].lower()


def test_best_guess_response_uses_metadata_without_legacy_preface(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="No durable learning for an ungrounded reply."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What color should the launch button be?",
            "history": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["kind"] == "best_guess"
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["label"] == "Best Guess"
    assert payload["working_memory"] == []
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")
    assert payload["learned"] == []


def test_fallback_turn_blocks_concept_without_structured_intent(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    concept_path = repo_root / "concepts" / "what-are-the-rules-of-reverse-brainstorming.md"

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    response = client.post(
        "/api/chat",
        json={
            "message": "What are the rules of reverse brainstorming?",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["kind"] == "best_guess"
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_concept_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert not concept_path.exists()


def test_fallback_turn_skips_freshness_marker_qa_without_openai_key(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    before_concepts = {path.name for path in (repo_root / "concepts").glob("*.md")}

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    response = client.post(
        "/api/chat",
        json={
            "message": (
                "What are the rules of reverse brainstorming? Include a freshness marker "
                "so I can tell this response is fresh."
            ),
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["rationale"] == (
        "This looked like a test/probe marker rather than reusable concept knowledge, "
        "so Vantage skipped automatic concept creation."
    )
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.name for path in (repo_root / "concepts").glob("*.md")} == before_concepts


def test_explicit_save_as_concept_with_freshness_marker_still_creates_concept(tmp_path: Path) -> None:
    repo_root = _test_repo(tmp_path)
    workspace_store = WorkspaceStore(repo_root / "workspaces")
    workspace = workspace_store.load("v5-milestone-1")
    concept_store = ConceptStore(repo_root / "concepts")
    executor = GraphActionExecutor(
        concept_store=concept_store,
        memory_store=MemoryStore(repo_root / "memories"),
        artifact_store=ArtifactStore(repo_root / "artifacts"),
        workspace_store=workspace_store,
        state_store=ActiveWorkspaceStateStore(repo_root / "state" / "active_workspace.json"),
    )
    service = MetaService(model="gpt-4.1", openai_api_key=None)

    decision = service.decide(
        user_message=(
            "Save as concept: A deployment canary marker is a temporary proof that a response "
            "is fresh, not cached."
        ),
        assistant_message="A deployment canary marker is only useful as a transient verification cue.",
        workspace=workspace,
        vetted_items=[],
        history=[],
        memory_mode="auto",
    )
    executed = executor.execute(decision, workspace=workspace)

    assert decision.action == "create_concept"
    assert executed is not None
    assert executed.action == "create_concept"
    assert executed.source == "concept"
    assert executed.record_id is not None
    assert (repo_root / "concepts" / f"{executed.record_id}.md").exists()


def test_include_word_without_freshness_marker_still_blocks_unstructured_concept(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    before_concepts = {path.name for path in (repo_root / "concepts").glob("*.md")}

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    response = client.post(
        "/api/chat",
        json={
            "message": "What are the rules of reverse brainstorming? Include the word persimmon.",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_concept_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.name for path in (repo_root / "concepts").glob("*.md")} == before_concepts


def test_smoke_test_topic_without_response_marker_still_blocks_unstructured_concept(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    before_concepts = {path.name for path in (repo_root / "concepts").glob("*.md")}

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    response = client.post(
        "/api/chat",
        json={
            "message": "What is a smoke test?",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_concept_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.name for path in (repo_root / "concepts").glob("*.md")} == before_concepts


def test_chat_turn_writes_memory_trace_and_can_recall_it_without_promoting_it(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    monkeypatch.setattr(MetaService, "decide", lambda self, **kwargs: MetaDecision(action="no_op", rationale="No durable write."))

    first = client.post(
        "/api/chat",
        json={
            "message": "Jerry likes warm, short check-in emails from Jordan.",
            "memory_intent": "dont_save",
        },
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["memory_trace_record"]["source"] == "memory_trace"
    assert first_payload["memory_trace_record"]["turn_mode"] == "chat"
    assert first_payload["memory_trace_record"]["workspace_scope"] == "excluded"
    assert first_payload["memory_trace_record"]["history_count"] == 0
    assert first_payload["memory_trace_record"]["recalled_ids"] == [
        item["id"] for item in first_payload["working_memory"]
    ]
    assert (repo_root / "memory_trace" / f"{first_payload['memory_trace_record']['id']}.md").exists()
    assert first_payload["learned"] == []

    second = client.post(
        "/api/chat",
        json={
            "message": "What do you remember about Jerry emails?",
            "history": [
                {"role": "user", "content": "Jerry likes warm, short check-in emails from Jordan."},
                {"role": "assistant", "content": first_payload["assistant_message"]},
            ],
            "memory_intent": "dont_save",
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert any(item["source"] == "memory_trace" for item in second_payload["candidate_memory_results"])
    assert any(item["source"] == "memory_trace" for item in second_payload["working_memory"])
    assert any(item["source"] == "memory_trace" for item in second_payload["trace_notes"])


def test_experiment_chat_writes_memory_trace_inside_experiment_scope(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    monkeypatch.setattr(MetaService, "decide", lambda self, **kwargs: MetaDecision(action="no_op", rationale="No durable write."))

    started = client.post("/api/experiment/start", json={})
    assert started.status_code == 200
    session_id = started.json()["experiment"]["session_id"]

    response = client.post(
        "/api/chat",
        json={
            "message": "Remember the current draft tone is playful.",
            "memory_intent": "dont_save",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["memory_trace_record"]["scope"] == "experiment"
    assert payload["memory_trace_record"]["trace_scope"] == "experiment"
    assert payload["memory_trace_record"]["turn_mode"] == "chat"
    experiment_trace_path = repo_root / "state" / "experiments" / session_id / "memory_trace" / f"{payload['memory_trace_record']['id']}.md"
    assert experiment_trace_path.exists()


def test_scenario_lab_turn_writes_memory_trace(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "Compare three rollout scenarios for milestone 1.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["memory_trace_record"]["source"] == "memory_trace"
    assert payload["memory_trace_record"]["turn_mode"] == "scenario_lab"
    assert payload["memory_trace_record"]["learned_count"] == 1
    assert (repo_root / "memory_trace" / f"{payload['memory_trace_record']['id']}.md").exists()


def test_fallback_turn_blocks_linked_concept_without_structured_intent(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    concept_path = repo_root / "concepts" / "what-are-the-rules-of-hangman.md"
    matching_concept = _concept_candidate_for_tests(
        id="rules-of-hangman-game",
        title="Rules of Hangman (game)",
        card="Basic rules and gameplay flow for Hangman, a classic word-guessing game.",
        body=(
            "Hangman is a word-guessing game involving at least two players. "
            "The guesser proposes letters one at a time and has a limited number of incorrect guesses."
        ),
    )

    def _vet(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
        return [matching_concept], {
            "selected_ids": [matching_concept.id],
            "none_relevant": False,
            "rationale": "Test vetting path selected the matching Hangman concept.",
        }

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _vet)

    response = client.post(
        "/api/chat",
        json={
            "message": "What are the rules of hangman?",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_concept_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert payload["vetting"]["selected_ids"] == [matching_concept.id]
    assert not concept_path.exists()


def test_fallback_turn_does_not_link_unstructured_concept_candidates(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)
    related_concept = _concept_candidate_for_tests(
        id="hangman-word-game",
        title="Hangman (Word Game)",
        card="A classic word-guessing game.",
        body="Players guess letters in a hidden word.",
    )
    unrelated_concept = _concept_candidate_for_tests(
        id="launch-strategy",
        title="Launch Strategy",
        card="A concept about product launches.",
        body="Tradeoffs for shipping software products.",
    )

    def _vet(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
        return [related_concept, unrelated_concept], {
            "selected_ids": [related_concept.id, unrelated_concept.id],
            "none_relevant": False,
            "rationale": "Test vetting path returned one related and one unrelated concept.",
        }

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _vet)

    response = client.post(
        "/api/chat",
        json={
            "message": "What are the rules of hangman?",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_concept_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []


def test_fallback_turn_can_create_revision_for_explicit_concept_update(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    concept_store = ConceptStore(repo_root / "concepts")
    concept_store.create_concept(
        title="Rules of Hangman (game)",
        card="Basic rules and gameplay flow for Hangman.",
        body="Players guess letters one at a time.",
    )
    matching_concept = _concept_candidate_for_tests(
        id="rules-of-hangman-game",
        title="Rules of Hangman (game)",
        card="Basic rules and gameplay flow for Hangman.",
        body="Players guess letters one at a time.",
    )

    def _vet(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
        return [matching_concept], {
            "selected_ids": [matching_concept.id],
            "none_relevant": False,
            "rationale": "Test vetting path selected the existing Hangman rules concept.",
        }

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _vet)

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The user explicitly asked to revise an existing concept.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {"type": "create_revision", "reason": "The user asked to revise this concept."},
                    {"type": "respond", "reason": "Confirm the concept revision."},
                ],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)

    response = client.post(
        "/api/chat",
        json={
            "message": "Revise this concept so it says players get 6 wrong guesses.",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "create_revision"
    assert payload["graph_action"]["type"] == "create_revision"
    assert payload["created_record"]["source"] == "concept"
    assert payload["created_record"]["lineage_kind"] == "revision"
    assert payload["created_record"]["revision_parent_id"] == "rules-of-hangman-game"
    assert payload["created_record"]["derived_from_id"] == "rules-of-hangman-game"
    created_record = client.get(f"/api/concepts/{payload['created_record']['id']}")
    assert created_record.status_code == 200
    created_payload = created_record.json()
    assert created_payload["lineage_kind"] == "revision"
    assert created_payload["revision_parent_id"] == "rules-of-hangman-game"
    assert created_payload["derived_from_id"] == "rules-of-hangman-game"


def test_meta_fallback_skips_near_duplicate_concept_title(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key=None)
    matching_concept = _concept_candidate_for_tests(
        id="what-are-the-rules-of-hangman",
        title="What Are The Rules Of Hangman",
        card="Here are the basic rules of Hangman.",
        body="A saved concept for Hangman rules.",
    )

    decision = service._fallback_decide(
        user_message="What are the rules of hangman?",
        assistant_message=(
            "Here are the basic rules of Hangman. One player chooses a word, "
            "the other guesses letters, and wrong guesses advance the drawing."
        ),
        workspace=workspace,
        vetted_items=[matching_concept],
        memory_mode="auto",
    )

    assert decision.action == "no_op"
    assert decision.links_to == [matching_concept.id]
    assert "near-duplicate concept already exists" in decision.rationale


def test_meta_fallback_explicit_revision_request_targets_single_vetted_concept(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key=None)
    matching_concept = _concept_candidate_for_tests(
        id="rules-of-hangman-game",
        title="Rules of Hangman (game)",
        card="Basic rules and gameplay flow for Hangman.",
        body="Players guess letters one at a time.",
    )

    decision = service._fallback_decide(
        user_message="Revise this concept so it says players get 6 wrong guesses.",
        assistant_message="I revised the rules to make the max incorrect guesses 6.",
        workspace=workspace,
        vetted_items=[matching_concept],
        memory_mode="auto",
    )

    assert decision.action == "create_revision"
    assert decision.target_concept_id == "rules-of-hangman-game"
    assert decision.links_to == []


def test_meta_openai_prompt_biases_toward_create_concept_and_links_related_concepts(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key="test-key")
    related_concept = _concept_candidate_for_tests(
        id="hangman-word-game",
        title="Hangman (Word Game)",
        card="A classic word-guessing game.",
        body="A durable concept about the core Hangman game.",
    )
    captured: dict[str, object] = {}

    class _FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "action": "create_concept",
                            "rationale": "This turn adds a distinct but related durable concept.",
                            "title": "Rules Of Hangman",
                            "card": "The basic rules of Hangman.",
                            "body": "A durable concept about Hangman rules.",
                            "target_concept_id": None,
                            "links_to": ["hangman-word-game"],
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service._openai_decide(
        user_message="What are the rules of hangman?",
        assistant_message=(
            "Here are the basic rules of Hangman. One player chooses a word, "
            "the other guesses letters, and wrong guesses advance the drawing."
        ),
        workspace=workspace,
        vetted_items=[related_concept],
        history=[],
        memory_mode="auto",
    )

    instructions = str(captured["instructions"])
    assert "Create_concept is the default durable action" in instructions
    assert "prefer create_concept with links_to pointing at the nearby concept neighborhood" in instructions
    assert "bias toward create_concept" in instructions
    assert "Choose no_op only when the turn is clearly transient" in instructions
    assert decision.action == "create_concept"
    assert decision.links_to == ["hangman-word-game"]


def test_meta_decide_skips_freshness_marker_before_openai_create_concept(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key="test-key")
    calls: list[dict[str, object]] = []

    class _FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "action": "create_concept",
                            "rationale": "The fake model would have created a concept.",
                            "title": "Rules Of Reverse Brainstorming",
                            "card": "The basic rules of reverse brainstorming.",
                            "body": "A durable concept about reverse brainstorming rules.",
                            "target_concept_id": None,
                            "links_to": [],
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service.decide(
        user_message=(
            "What are the rules of reverse brainstorming? Include a freshness marker "
            "so I can tell this response is fresh."
        ),
        assistant_message="Here are the basic rules of reverse brainstorming.",
        workspace=workspace,
        vetted_items=[],
        history=[],
        memory_mode="auto",
    )

    assert calls == []
    assert decision.action == "no_op"
    assert decision.rationale == (
        "This looked like a test/probe marker rather than reusable concept knowledge, "
        "so Vantage skipped automatic concept creation."
    )


def test_meta_openai_decide_supports_constrained_create_revision(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key="test-key")
    target_concept = _concept_candidate_for_tests(
        id="rules-of-hangman-game",
        title="Rules of Hangman (game)",
        card="Basic rules and gameplay flow for Hangman.",
        body="Players guess letters one at a time.",
    )
    related_concept = _concept_candidate_for_tests(
        id="hangman-word-game",
        title="Hangman (Word Game)",
        card="A classic word-guessing game.",
        body="A durable concept about the core Hangman game.",
    )
    captured: dict[str, object] = {}

    class _FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "action": "create_revision",
                            "rationale": "This turn deliberately updates the existing Hangman rules concept.",
                            "title": "Rules Of Hangman",
                            "card": "The updated rules of Hangman.",
                            "body": "A revised Hangman rules concept with max guesses set to 6.",
                            "target_concept_id": "rules-of-hangman-game",
                            "links_to": ["rules-of-hangman-game", "hangman-word-game"],
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service._openai_decide(
        user_message="Revise the concept about Hangman rules so it says players get 6 wrong guesses.",
        assistant_message="I revised the rules to make the max incorrect guesses 6.",
        workspace=workspace,
        vetted_items=[target_concept, related_concept],
        history=[],
        memory_mode="auto",
    )

    instructions = str(captured["instructions"])
    assert "Create_revision is a deliberate action" in instructions
    assert "Do not use create_revision for merely related knowledge" in instructions
    assert decision.action == "create_revision"
    assert decision.target_concept_id == "rules-of-hangman-game"
    assert decision.links_to == ["hangman-word-game"]


def test_meta_openai_decide_backfills_related_links_when_model_omits_them(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key="test-key")
    related_concept = _concept_candidate_for_tests(
        id="hangman-word-game",
        title="Hangman (Word Game)",
        card="A classic word-guessing game.",
        body="A durable concept about the core Hangman game.",
    )

    class _FakeResponses:
        def create(self, **kwargs):
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "action": "create_concept",
                            "rationale": "This turn adds a distinct but related durable concept.",
                            "title": "Rules Of Hangman",
                            "card": "The basic rules of Hangman.",
                            "body": "A durable concept about Hangman rules.",
                            "target_concept_id": None,
                            "links_to": [],
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service._openai_decide(
        user_message="What are the rules of hangman?",
        assistant_message="Here are the basic rules of Hangman.",
        workspace=workspace,
        vetted_items=[related_concept],
        history=[],
        memory_mode="auto",
    )

    assert decision.action == "create_concept"
    assert decision.links_to == ["hangman-word-game"]


def test_meta_openai_decide_upgrades_explicit_revision_request_instead_of_suppressing_duplicate(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key="test-key")
    duplicate_concept = _concept_candidate_for_tests(
        id="what-are-the-rules-of-hangman",
        title="What Are The Rules Of Hangman",
        card="Here are the basic rules of Hangman.",
        body="A saved concept for Hangman rules.",
    )

    class _FakeResponses:
        def create(self, **kwargs):
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "action": "create_concept",
                            "rationale": "This should be saved durably.",
                            "title": "What Are The Rules Of Hangman",
                            "card": "Here are the updated rules of Hangman.",
                            "body": "A revised version of the saved Hangman rules concept.",
                            "target_concept_id": None,
                            "links_to": [],
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service._openai_decide(
        user_message="Revise the concept about Hangman rules so it says players get 6 wrong guesses.",
        assistant_message="I revised the rules to make the max incorrect guesses 6.",
        workspace=workspace,
        vetted_items=[duplicate_concept],
        history=[],
        memory_mode="auto",
    )

    assert decision.action == "create_revision"
    assert decision.target_concept_id == "what-are-the-rules-of-hangman"


def test_meta_openai_decide_suppresses_near_duplicate_concept(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = MetaService(model="gpt-4.1", openai_api_key="test-key")
    duplicate_concept = _concept_candidate_for_tests(
        id="what-are-the-rules-of-hangman",
        title="What Are The Rules Of Hangman",
        card="Here are the basic rules of Hangman.",
        body="A saved concept for Hangman rules.",
    )

    class _FakeResponses:
        def create(self, **kwargs):
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "action": "create_concept",
                            "rationale": "This looks durable enough for a concept.",
                            "title": "What Are The Rules Of Hangman",
                            "card": "Here are the basic rules of Hangman.",
                            "body": "A second copy of the Hangman rules.",
                            "target_concept_id": None,
                            "links_to": [],
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service._openai_decide(
        user_message="What are the rules of hangman?",
        assistant_message="Here are the basic rules of Hangman.",
        workspace=workspace,
        vetted_items=[duplicate_concept],
        history=[],
        memory_mode="auto",
    )

    assert decision.action == "no_op"
    assert decision.links_to == ["what-are-the-rules-of-hangman"]
    assert "near-duplicate concept already exists" in decision.rationale


def test_whiteboard_only_context_is_grounded_without_best_guess_preface(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I used the whiteboard draft.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Whiteboard context should ground this turn."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What should we change next?",
            "history": [],
            "workspace_scope": "visible",
            "workspace_content": "# Draft\n\nThis is a live whiteboard draft.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "whiteboard"
    assert payload["response_mode"]["label"] == "Whiteboard"
    assert payload["assistant_message"] == "I used the whiteboard draft."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_recent_chat_only_context_is_grounded_without_best_guess_preface(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I used the recent chat context.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Recent chat context should ground this turn."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Can you continue from there?",
            "history": [
                {
                    "user_message": "Draft a launch checklist.",
                    "assistant_message": "Here is a draft launch checklist.",
                }
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "recent_chat"
    assert payload["response_mode"]["label"] == "Recent Chat"
    assert payload["assistant_message"] == "I used the recent chat context."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")


def test_whiteboard_accept_route_drafts_without_fabricated_user_message(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    pending_workspace_update = _pending_offer_update()

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        assert kwargs["message"] == pending_workspace_update["origin_user_message"]
        return (
            "CHAT_RESPONSE: I drafted the thank-you email into the whiteboard so we can refine it together.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Subject: Thank you for the flowers\n\n"
            "Hi Judy,\n\n"
            "Thank you so much for the beautiful flowers you dropped off. That was such a thoughtful surprise, and it really brightened my day.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Explicit acceptance should keep the whiteboard draft temporary until the user saves it.",
        ),
    )

    response = client.post(
        "/api/chat/whiteboard/accept",
        json={
            "workspace_id": "v5-milestone-1",
            "history": [
                {
                    "user_message": "Lets draft an email to Judy thanking her for the flowers she dropped off.",
                    "assistant_message": "Would you like to pull up a whiteboard so we can write the thank-you email there?",
                }
            ],
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I drafted the thank-you email into the whiteboard so we can refine it together."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["semantic_frame"]["target_surface"] == "whiteboard"
    assert payload["semantic_frame"]["follow_up_type"] == "acceptance"
    assert payload["semantic_frame"]["referenced_object"]["type"] == "whiteboard"
    assert "pending_whiteboard" in payload["response_mode"]["context_sources"]
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["created_record"]["artifact_origin"] == "whiteboard"
    assert payload["created_record"]["artifact_lifecycle"] == "whiteboard_snapshot"
    assert payload["workspace_update"]["artifact_snapshot_id"] == payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_whiteboard_accept_route_provider_failure_still_returns_draft(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")
    pending_workspace_update = _pending_offer_update()

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _raise_runtime_error_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Fallback whiteboard acceptance should still keep the draft temporary.",
        ),
    )

    response = client.post(
        "/api/chat/whiteboard/accept",
        json={
            "workspace_id": "v5-milestone-1",
            "history": [],
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback"
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["title"] == "Email Draft To Judy"
    assert "Hi Judy" in payload["workspace_update"]["content"]
    assert "Fallback mode" not in payload["assistant_message"]
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_whiteboard_accept_requires_origin_user_message(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post(
        "/api/chat/whiteboard/accept",
        json={
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": {
                "type": "offer_whiteboard",
                "status": "offered",
                "summary": "Whiteboard ready for collaboratively drafting the thank-you email.",
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "pending_workspace_update.origin_user_message is required."


def test_open_promote_and_remember_flow(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    opened = client.post("/api/concepts/open", json={"concept_id": "shared-workspace"})
    assert opened.status_code == 200
    opened_payload = opened.json()
    assert opened_payload["workspace_id"] == "shared-workspace"
    assert "# Shared Workspace" in opened_payload["content"]

    workspace = client.get("/api/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == "shared-workspace"

    promoted = client.post(
        "/api/concepts/promote",
        json={
            "workspace_id": "shared-workspace",
            "title": "Shared Workspace Snapshot",
            "content": "# Shared Workspace Snapshot\n\nThis is a promoted snapshot.",
        },
    )
    assert promoted.status_code == 200
    promoted_payload = promoted.json()
    promoted_artifact = promoted_payload["promoted_record"]
    assert promoted_artifact["id"].startswith("shared-workspace-snapshot")
    assert promoted_artifact["source"] == "artifact"
    assert promoted_artifact["artifact_origin"] == "whiteboard"
    assert promoted_artifact["artifact_lifecycle"] == "promoted_artifact"
    assert (repo_root / "artifacts" / f"{promoted_artifact['id']}.md").exists()

    chat = client.post(
        "/api/chat",
        json={
            "message": "Please remember this durable note about Thanksgiving dinner planning.",
            "history": [],
            "workspace_id": "shared-workspace",
            "memory_intent": "remember",
        },
    )
    assert chat.status_code == 200
    payload = chat.json()
    assert payload["meta_action"]["action"] == "create_memory"
    assert payload["graph_action"]["type"] == "create_memory"
    assert payload["graph_action"]["record_id"] == payload["created_record"]["id"]
    assert payload["graph_action"]["concept_id"] == payload["created_record"]["id"]
    assert payload["created_record"]["id"]
    assert payload["learned"] == [payload["created_record"]]
    assert payload["created_record"]["scope"] == "durable"
    assert payload["created_record"]["source"] == "memory"
    assert payload["created_record"]["write_review"]["record"]["source"] == "memory"
    assert payload["created_record"]["write_review"]["scope"] == "durable"
    assert payload["created_record"]["write_review"]["write_reason"] == (
        "Saved as memory because the user asked Vantage to remember it."
    )
    assert payload["created_record"]["write_review"]["mutation_supported"] is False
    assert (repo_root / "memories" / f"{payload['created_record']['id']}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["memory_write_authority"]["action"] == "memory_write"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is True
    assert final_response["turn_plan"]["memory_write_authority"]["authority"] == "memory_intent"
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["memory_write"]
    assert final_response["turn_plan"]["write_projection"]["effect_agreement"] == "aligned"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_memory_write_without_structured_authority_is_denied(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I'll keep that in mind for this answer.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="create_memory",
            title="Unstructured remember",
            card="This candidate should be denied by TurnPlan.",
            body="This should not be written without structured memory authority.",
            rationale="Synthetic memory candidate without structured authority.",
        ),
    )

    memory_ids_before = {path.stem for path in (repo_root / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "Keep that in mind for the answer.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_memory"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_memory_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.stem for path in (repo_root / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["memory_write_authority"]["action"] == "memory_write"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is False
    assert final_response["turn_plan"]["memory_write_authority"]["denied_reason"] == (
        "missing_structured_memory_write_intent"
    )
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_memory_write_with_empty_candidate_content_is_denied(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "Got it, I can use that in this answer.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="create_memory",
            rationale="Malformed memory candidate without persisted content fields.",
        ),
    )

    memory_ids_before = {path.stem for path in (repo_root / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "Remember this preference from the whiteboard.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": "# Raw Whiteboard\n\nThis text must not count as safe memory candidate content.",
            "memory_intent": "remember",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_memory"
    assert payload["meta_action"]["blocked_reason"] == "memory_write_content_unavailable_or_unsafe"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.stem for path in (repo_root / "memories").glob("*.md")} == memory_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    memory_authority = final_response["turn_plan"]["memory_write_authority"]
    assert memory_authority["action"] == "memory_write"
    assert memory_authority["allowed"] is False
    assert memory_authority["content_available"] is False
    assert memory_authority["denied_reason"] == "memory_write_content_unavailable_or_unsafe"
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["none"]
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_concept_write_with_valid_meta_candidate_is_allowed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The user explicitly asked to create concept knowledge.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {"type": "create_concept", "reason": "The user asked to make this a concept."},
                    {"type": "respond", "reason": "Confirm the concept write."},
                ],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "That concept is worth keeping.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="create_concept",
            title="Graph Traversal Review Priority",
            card="BFS and DFS review should anchor graph exam preparation.",
            body="Graph exam preparation should prioritize BFS and DFS review before broader graph topics.",
            rationale="The existing meta interpreter produced a structured concept candidate.",
        ),
    )

    concept_ids_before = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "Make this a concept: graph exam prep should start with BFS and DFS review.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["surfaces"][0]["status"] == "handled_by_concept_write"
    assert payload["meta_action"]["action"] == "create_concept"
    assert payload["graph_action"]["type"] == "create_concept"
    assert payload["created_record"]["source"] == "concept"
    assert payload["created_record"]["id"] not in concept_ids_before
    assert (repo_root / "concepts" / f"{payload['created_record']['id']}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    concept_authority = final_response["turn_plan"]["concept_write_authority"]
    assert concept_authority["action"] == "concept_write"
    assert concept_authority["allowed"] is True
    assert concept_authority["authority"] == "control_panel"
    assert concept_authority["content_available"] is True
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["concept_write"]
    assert final_response["turn_plan"]["write_projection"]["intended_write_kind"] == "concept_write"
    assert final_response["turn_plan"]["write_projection"]["effect_agreement"] == "aligned"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_concept_write_with_empty_candidate_content_is_denied(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path)

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The user explicitly asked to create concept knowledge.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {"type": "create_concept", "reason": "The user asked to make this a concept."},
                    {"type": "respond", "reason": "Confirm the concept write."},
                ],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I can discuss that in chat.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="create_concept",
            rationale="Malformed concept candidate without persisted content fields.",
        ),
    )

    concept_ids_before = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": "Concept note: raw user text should not count as candidate content.",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "concept_write_content_unavailable_or_unsafe"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.stem for path in (repo_root / "concepts").glob("*.md")} == concept_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    concept_authority = final_response["turn_plan"]["concept_write_authority"]
    assert concept_authority["action"] == "concept_write"
    assert concept_authority["allowed"] is False
    assert concept_authority["content_available"] is False
    assert concept_authority["denied_reason"] == "concept_write_content_unavailable_or_unsafe"
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["none"]
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_ordinary_qna_does_not_create_concept_from_meta_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.88,
            reason="The user asked an ordinary Q&A question.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [{"type": "respond", "reason": "Answer in chat."}],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "BFS explores vertices in breadth-first layers using a queue.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="create_concept",
            title="Breadth-First Search",
            card="BFS explores graph vertices layer by layer.",
            body="Breadth-first search explores graph vertices in increasing distance from a start node.",
            rationale="The meta layer over-eagerly proposed a concept candidate for ordinary Q&A.",
        ),
    )

    concept_ids_before = {path.stem for path in (repo_root / "concepts").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={"message": "What is BFS?", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "BFS explores vertices in breadth-first layers using a queue."
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["meta_action"]["blocked_action"] == "create_concept"
    assert payload["meta_action"]["blocked_reason"] == "missing_structured_concept_write_intent"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert payload["learned"] == []
    assert {path.stem for path in (repo_root / "concepts").glob("*.md")} == concept_ids_before
    final_response = _latest_trace_payload(repo_root)["final_response"]
    concept_authority = final_response["turn_plan"]["concept_write_authority"]
    assert concept_authority["action"] == "concept_write"
    assert concept_authority["allowed"] is False
    assert concept_authority["denied_reason"] == "missing_structured_concept_write_intent"
    assert final_response["turn_plan"]["validation"]["warnings"] == []


@pytest.mark.parametrize(
    "message",
    [
        "Remember that my graph exam priority is BFS and DFS review.",
        "Remember that my preferred study block starts at 9.",
    ],
)
def test_explicit_remember_control_panel_writes_memory_instead_of_task_focus(
    tmp_path: Path,
    message: str,
) -> None:
    tasks_path = _write_tasks(
        tmp_path / "tasks" / "tasks.json",
        tasks=[
            {"id": "graph-review", "title": "Review graph algorithms", "priority": "high"},
        ],
    )
    client, repo_root = _client(tmp_path, tasks_path=tasks_path)

    memory_ids_before = {path.stem for path in (repo_root / "memories").glob("*.md")}
    response = client.post(
        "/api/chat",
        json={
            "message": message,
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface_invocation"]["intent"] == "memory_write"
    assert payload["surface_invocation"]["primary_surface"] == "chat"
    assert payload["surface_invocation"]["surfaces"][0]["status"] == "handled_by_memory_write"
    assert payload["active_surface_id"] is None
    assert payload["surface_payloads"] == []
    assert payload["meta_action"]["action"] == "create_memory"
    assert payload["graph_action"]["type"] == "create_memory"
    assert payload["created_record"]["source"] == "memory"
    assert payload["created_record"]["id"] not in memory_ids_before
    assert (repo_root / "memories" / f"{payload['created_record']['id']}.md").exists()
    assert "remembered" in payload["assistant_message"].lower()
    assert "task focus" not in payload["assistant_message"].lower()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["write_ledger"]["categories"] == ["memory_write"]
    assert final_response["turn_plan"]["write_projection"]["intended_write_kind"] == "memory_write"
    assert final_response["turn_plan"]["write_projection"]["effect_agreement"] == "aligned"
    assert final_response["turn_plan"]["memory_write_authority"]["allowed"] is True
    assert final_response["turn_plan"]["validation"]["warnings"] == []


def test_follow_up_after_artifact_promotion_keeps_selected_artifact_in_focus(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    promoted = client.post(
        "/api/concepts/promote",
        json={
            "workspace_id": "v5-milestone-1",
            "title": "Launch Strategy Notes",
            "content": "# Launch Strategy Notes\n\nThe focused MVP path is the current recommendation.",
        },
    )
    assert promoted.status_code == 200
    promoted_artifact = promoted.json()["promoted_record"]

    def _route(self, **kwargs):
        pinned_context = kwargs["pinned_context"]
        assert pinned_context is not None
        assert pinned_context["id"] == promoted_artifact["id"]
        assert pinned_context["source"] == "artifact"
        return NavigationDecision(
            mode="chat",
            confidence=0.96,
            reason="The user is following up on the promoted artifact.",
            preserve_pinned_context=True,
            pinned_context_reason="The promoted artifact stays in focus for the follow-up.",
            preserve_selected_record=True,
            selected_record_reason="The promoted artifact stays in focus for the follow-up.",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Promoted artifact follow-up should remain temporary."),
    )

    follow_up = client.post(
        "/api/chat",
        json={
            "message": "which one do you recommend?",
            "history": [
                {
                    "user_message": "Please promote the current launch notes.",
                    "assistant_message": "Done.",
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pinned_context_id": promoted_artifact["id"],
        },
    )
    assert follow_up.status_code == 200
    payload = follow_up.json()
    assert payload["mode"] == "fallback"
    assert payload["pinned_context_id"] == promoted_artifact["id"]
    assert payload["pinned_context"]["id"] == promoted_artifact["id"]
    assert payload["selected_record_id"] == promoted_artifact["id"]
    assert payload["selected_record"]["id"] == promoted_artifact["id"]
    assert payload["selected_record"]["source"] == "artifact"
    assert any(item["id"] == promoted_artifact["id"] for item in payload["working_memory"])
    assert payload["turn_interpretation"]["preserve_pinned_context"] is True
    assert payload["turn_interpretation"]["pinned_context_reason"] == "The promoted artifact stays in focus for the follow-up."
    assert payload["turn_interpretation"]["preserve_selected_record"] is True
    assert payload["turn_interpretation"]["selected_record_reason"] == "The promoted artifact stays in focus for the follow-up."
    assert len(payload["working_memory"]) <= 5
    assert payload["response_mode"]["kind"] == "grounded"


def test_promote_unsaved_whiteboard_draft_to_artifact_without_persisting_workspace(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    promoted = client.post(
        "/api/concepts/promote",
        json={
            "workspace_id": "email-draft-insights-on-predicting-behavior-and-the-importan",
            "title": "Email Draft: Insights on Predicting Behavior",
            "content": "# Email Draft: Insights on Predicting Behavior\n\nHi Michael,\n\nHere are a few thoughts on predicting behavior.",
        },
    )

    assert promoted.status_code == 200
    payload = promoted.json()
    promoted_artifact = payload["promoted_record"]
    assert promoted_artifact["source"] == "artifact"
    assert promoted_artifact["title"] == "Email Draft: Insights on Predicting Behavior"
    assert promoted_artifact["lineage_kind"] == "provenance"
    assert promoted_artifact["derived_from_id"] == "email-draft-insights-on-predicting-behavior-and-the-importan"
    assert promoted_artifact["revision_parent_id"] is None
    assert (repo_root / "artifacts" / f"{promoted_artifact['id']}.md").exists()
    assert not (repo_root / "workspaces" / "email-draft-insights-on-predicting-behavior-and-the-importan.md").exists()


def test_concept_revision_payload_exposes_revision_parent(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    concept_store = ConceptStore(repo_root / "concepts")
    concept_store.create_concept(
        title="Rules of Hangman (game)",
        card="Basic rules and gameplay flow for Hangman.",
        body="Players guess letters one at a time.",
    )
    revision = concept_store.create_revision(
        base_concept_id="rules-of-hangman-game",
        title="Rules of Hangman (game) Revision",
        card="Revised rules of Hangman.",
        body="A revised description of Hangman.",
        links_to=["what-are-the-rules-of-hangman"],
    )

    concept_response = client.get(f"/api/concepts/{revision.id}")
    assert concept_response.status_code == 200
    concept_payload = concept_response.json()
    assert concept_payload["lineage_kind"] == "revision"
    assert concept_payload["revision_parent_id"] == "rules-of-hangman-game"
    assert concept_payload["derived_from_id"] == "rules-of-hangman-game"
    assert concept_payload["comes_from"] == ["rules-of-hangman-game"]


def test_whiteboard_accept_uses_canonical_pinned_context_fields(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)
    observed: dict[str, object] = {}

    (repo_root / "artifacts" / "launch-comparison.md").write_text(
        (
            "---\n"
            "id: launch-comparison\n"
            "title: Launch Strategy Comparison\n"
            "type: scenario_comparison\n"
            "card: Comparison artifact for launch strategy branches.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Baseline versus constrained versus aggressive launch options.\n"
        ),
        encoding="utf-8",
    )

    class DummyTurn:
        def to_body_parts(self) -> ChatTurnBodyParts:
            return ChatTurnBodyParts(
                user_message="accept whiteboard",
                assistant_message="done",
                workspace_id="v5-milestone-1",
                workspace_title="Shared Workspace",
                workspace_content=None,
                workspace_update=None,
                concept_cards=[],
                trace_notes=[],
                saved_notes=[],
                vault_notes=[],
                candidate_concepts=[],
                candidate_trace_notes=[],
                candidate_saved_notes=[],
                candidate_vault_notes=[],
                candidate_memory=[],
                working_memory=[],
                recall_details=[],
                learned=[],
                memory_trace_record=None,
                response_mode={
                    "kind": "grounded",
                    "label": "Recall",
                    "recallCount": 0,
                    "workingMemoryCount": 0,
                    "groundingMode": "recall",
                    "groundingSources": [],
                    "contextSources": [],
                },
                vetting={"selected_ids": []},
                mode="fallback",
                meta_action=None,
                graph_action=None,
                created_record=None,
            )

    def _reply(self, **kwargs):
        observed.update(kwargs)
        return DummyTurn()

    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", _reply)

    response = client.post(
        "/api/chat/whiteboard/accept",
        json={
            "history": [],
            "workspace_id": "v5-milestone-1",
            "pinned_context_id": "launch-comparison",
            "pending_workspace_update": {
                "origin_user_message": "Draft a launch comparison in the whiteboard.",
                "status": "offered",
                "type": "offer_whiteboard",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert observed["selected_record_id"] == "launch-comparison"
    assert observed["selected_record_reason"] is None
    assert observed["preserve_selected_record"] is None
    assert payload["pinned_context_id"] == "launch-comparison"
    assert payload["selected_record_id"] == "launch-comparison"
    assert payload["pinned_context"]["id"] == "launch-comparison"
    assert payload["selected_record"]["id"] == "launch-comparison"
    assert payload["turn_interpretation"]["preserve_pinned_context"] is None
    assert payload["turn_interpretation"]["pinned_context_reason"] is None
    assert payload["turn_interpretation"]["preserve_selected_record"] is None
    assert payload["turn_interpretation"]["selected_record_reason"] is None


def test_navigator_openai_payload_uses_pinned_context_as_the_model_contract(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="v5-milestone-1",
        title="Shared Workspace",
        content="# Shared Workspace\n\nDraft content for inspection.\n",
        path=tmp_path / "workspaces" / "v5-milestone-1.md",
    )
    service = NavigatorService(model="gpt-4.1", openai_api_key="test-key")
    captured: dict[str, object] = {}

    class _FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "FakeResponse",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "mode": "chat",
                            "confidence": 0.91,
                            "reason": "Pinned context is already enough for this follow-up.",
                            "comparison_question": None,
                            "branch_count": 0,
                            "branch_labels": [],
                            "whiteboard_mode": "chat",
                            "pinned_context_id": "pinned-comparison",
                            "pinned_context": {"id": "pinned-comparison", "title": "Pinned comparison"},
                            "preserve_pinned_context": True,
                            "pinned_context_reason": "Keep the pinned comparison in focus.",
                        }
                    )
                },
            )()

    service.client = type("FakeClient", (), {"responses": _FakeResponses()})()

    decision = service.route_turn(
        user_message="What should we do next?",
        history=[{"role": "user", "content": "Earlier context."}],
        workspace=workspace,
        requested_whiteboard_mode="auto",
        pinned_context_id="pinned-comparison",
        pinned_context={"id": "pinned-comparison", "title": "Pinned comparison"},
        selected_record_id="legacy-selected-record",
        selected_record={"id": "legacy-selected-record", "title": "Legacy selected record"},
        pending_workspace_update=None,
        continuity_context={
            "current_whiteboard": {
                "workspace_id": "v5-milestone-1",
                "title": "Shared Workspace",
            },
            "recent_whiteboards": [
                {
                    "workspace_id": "email-insights-on-predicting-behavior",
                    "title": "Predicting Behavior Email",
                }
            ],
            "last_turn_referenced_record": {
                "record_id": "email-insights-on-predicting-behavior",
                "title": "Predicting Behavior Email",
                "source": "artifact",
                "reopenable_in_whiteboard": True,
            },
            "last_turn_recall": [
                {
                    "record_id": "email-insights-on-predicting-behavior",
                    "title": "Predicting Behavior Email",
                    "source": "artifact",
                }
            ],
        },
    )

    payload = json.loads(str(captured["input"]))
    schema = captured["text"]["format"]["schema"]
    assert payload["pinned_context_id"] == "pinned-comparison"
    assert payload["pinned_context"]["id"] == "pinned-comparison"
    assert payload["continuity_context"]["current_whiteboard"]["workspace_id"] == "v5-milestone-1"
    assert payload["continuity_context"]["last_turn_referenced_record"]["record_id"] == "email-insights-on-predicting-behavior"
    assert "selected_record_id" not in payload
    assert "selected_record" not in payload
    assert "selected_record_id" not in schema["properties"]
    assert "selected_record" not in schema["properties"]
    assert decision.to_dict()["preserve_pinned_context"] is True
    assert decision.to_dict()["preserve_selected_record"] is True
    assert decision.to_dict()["pinned_context_reason"] == "Keep the pinned comparison in focus."


def test_chat_builds_navigator_continuity_context_from_recent_whiteboards_and_memory_trace(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact_store = ArtifactStore(repo_root / "artifacts")
    trace_store = MemoryTraceStore(repo_root / "memory_trace")

    artifact = artifact_store.create_artifact(
        record_id="email-insights-on-predicting-behavior",
        title="Email Draft: Insights on Predicting Behavior and the Importance of Representation",
        card="A saved email draft about representation and predicting behavior.",
        body="Hi Joe,\n\nGood representations matter for predicting behavior.\n",
    )
    second_artifact = artifact_store.create_artifact(
        record_id="email-to-jerry",
        title="Draft Email to Jerry",
        card="A second saved email draft.",
        body="Hi Jerry,\n\nHow is your day going?\n",
    )
    (repo_root / "workspaces" / "email-insights-on-predicting-behavior.md").write_text(
        "# Email Draft: Insights on Predicting Behavior and the Importance of Representation\n\nHi Joe,\n\nGood representations matter for predicting behavior.\n",
        encoding="utf-8",
    )
    (repo_root / "workspaces" / "roadmap-draft.md").write_text(
        "# Roadmap Draft\n\nA second recent whiteboard.\n",
        encoding="utf-8",
    )

    trace_store.create_turn_trace(
        user_message="what was the other email we were drafting?",
        assistant_message=(
            'The other email draft in our records is titled "Email Draft: Insights on Predicting Behavior and the Importance of Representation."'
        ),
        working_memory=[
            {
                "id": artifact.id,
                "title": artifact.title,
                "source": artifact.source,
                "card": artifact.card,
            },
            {
                "id": second_artifact.id,
                "title": second_artifact.title,
                "source": second_artifact.source,
                "card": second_artifact.card,
            },
        ],
        history=[],
        workspace_id="v5-milestone-1",
        workspace_title="Shared Workspace",
        workspace_content=None,
        workspace_scope="excluded",
        learned=[],
        response_mode={
            "kind": "grounded",
            "label": "Recall",
            "grounding_mode": "recall",
            "context_sources": ["recall"],
            "recall_count": 1,
            "working_memory_count": 1,
        },
        scope="durable",
        referenced_record={
            "id": artifact.id,
            "title": artifact.title,
            "source": artifact.source,
        },
    )

    observed: dict[str, object] = {}

    def _route(self, **kwargs):
        observed.update(kwargs)
        return NavigationDecision(
            mode="chat",
            confidence=0.92,
            reason="Continuity context is available for this follow-up.",
            whiteboard_mode="chat",
        )

    class DummyTurn:
        def to_body_parts(self) -> ChatTurnBodyParts:
            return ChatTurnBodyParts(
                user_message="yea can you pull that up on the whiteboard?",
                assistant_message="Stub reply.",
                workspace_id="v5-milestone-1",
                workspace_title="Shared Workspace",
                workspace_content=None,
                workspace_update=None,
                concept_cards=[],
                trace_notes=[],
                saved_notes=[],
                vault_notes=[],
                candidate_concepts=[],
                candidate_trace_notes=[],
                candidate_saved_notes=[],
                candidate_vault_notes=[],
                candidate_memory=[],
                working_memory=[],
                recall_details=[],
                learned=[],
                memory_trace_record=None,
                response_mode={
                    "kind": "grounded",
                    "label": "Recall",
                    "note": "Supported by 1 recalled item from Recall.",
                    "grounding_mode": "recall",
                    "grounding_sources": ["recall"],
                    "context_sources": ["recall"],
                    "recall_count": 1,
                    "working_memory_count": 1,
                },
                vetting={"selected_ids": []},
                mode="openai",
                meta_action={"action": "no_op", "rationale": "Test stub."},
                graph_action=None,
                created_record=None,
            )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", lambda self, **kwargs: DummyTurn())

    response = client.post(
        "/api/chat",
        json={
            "message": "yea can you pull that up on the whiteboard?",
            "history": [
                {
                    "user_message": "what was the other email we were drafting?",
                    "assistant_message": (
                        'The other email draft in our records is titled "Email Draft: Insights on Predicting Behavior and the Importance of Representation."'
                    ),
                }
            ],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    continuity_context = observed["continuity_context"]
    assert continuity_context["current_whiteboard"]["workspace_id"] == "v5-milestone-1"
    assert continuity_context["last_turn_referenced_record"]["record_id"] == "email-insights-on-predicting-behavior"
    assert continuity_context["last_turn_recall"][0]["record_id"] == "email-insights-on-predicting-behavior"
    assert continuity_context["last_turn_recall"][1]["record_id"] == "email-to-jerry"
    assert len(continuity_context["recent_whiteboards"]) <= 3
    assert any(
        item["workspace_id"] == "email-insights-on-predicting-behavior"
        for item in continuity_context["recent_whiteboards"]
    )


def test_chat_keeps_last_turn_referenced_record_empty_when_latest_recall_is_ambiguous(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    artifact_store = ArtifactStore(repo_root / "artifacts")
    trace_store = MemoryTraceStore(repo_root / "memory_trace")

    first = artifact_store.create_artifact(
        record_id="email-to-jerry",
        title="Draft Email to Jerry",
        card="A saved email draft to Jerry.",
        body="Hi Jerry,\n\nHow is your day going?\n",
    )
    second = artifact_store.create_artifact(
        record_id="email-to-jay",
        title="Draft Email to Jay",
        card="A saved email draft to Jay.",
        body="Hi Jay,\n\nHow is the project moving along?\n",
    )

    trace_store.create_turn_trace(
        user_message="what were the two emails we were working on?",
        assistant_message="We were working on a draft to Jerry and a draft to Jay.",
        working_memory=[
            {
                "id": first.id,
                "title": first.title,
                "source": first.source,
                "card": first.card,
            },
            {
                "id": second.id,
                "title": second.title,
                "source": second.source,
                "card": second.card,
            },
        ],
        history=[],
        workspace_id="v5-milestone-1",
        workspace_title="Shared Workspace",
        workspace_content=None,
        workspace_scope="excluded",
        learned=[],
        response_mode={
            "kind": "grounded",
            "label": "Recall",
            "grounding_mode": "recall",
            "context_sources": ["recall"],
            "recall_count": 2,
            "working_memory_count": 2,
        },
        scope="durable",
    )

    observed: dict[str, object] = {}

    def _route(self, **kwargs):
        observed.update(kwargs)
        return NavigationDecision(
            mode="chat",
            confidence=0.81,
            reason="Continuity context is ambiguous, so keep the turn conservative.",
            whiteboard_mode="chat",
        )

    class DummyTurn:
        def to_body_parts(self) -> ChatTurnBodyParts:
            return ChatTurnBodyParts(
                user_message="pull that up on the whiteboard",
                assistant_message="Stub reply.",
                workspace_id="v5-milestone-1",
                workspace_title="Shared Workspace",
                workspace_content=None,
                workspace_update=None,
                concept_cards=[],
                trace_notes=[],
                saved_notes=[],
                vault_notes=[],
                candidate_concepts=[],
                candidate_trace_notes=[],
                candidate_saved_notes=[],
                candidate_vault_notes=[],
                candidate_memory=[],
                working_memory=[],
                recall_details=[],
                learned=[],
                memory_trace_record=None,
                response_mode={
                    "kind": "grounded",
                    "label": "Recall",
                    "note": "Supported by recalled items from Recall.",
                    "grounding_mode": "recall",
                    "grounding_sources": ["recall"],
                    "context_sources": ["recall"],
                    "recall_count": 2,
                    "working_memory_count": 2,
                },
                vetting={"selected_ids": []},
                mode="openai",
                meta_action={"action": "no_op", "rationale": "Test stub."},
                graph_action=None,
                created_record=None,
            )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.chat.ChatService.reply", lambda self, **kwargs: DummyTurn())

    response = client.post(
        "/api/chat",
        json={
            "message": "pull that up on the whiteboard",
            "history": [
                {
                    "user_message": "what were the two emails we were working on?",
                    "assistant_message": "We were working on a draft to Jerry and a draft to Jay.",
                }
            ],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    continuity_context = observed["continuity_context"]
    assert continuity_context["last_turn_referenced_record"] is None
    assert {item["record_id"] for item in continuity_context["last_turn_recall"]} == {
        "email-to-jerry",
        "email-to-jay",
    }


def test_workspace_save_can_target_new_workspace_id_and_activate_it(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    response = client.post(
        "/api/workspace",
        json={
            "workspace_id": "thank-you-email-to-judy",
            "content": "# Thank You Email to Judy\n\nHi Judy,\n\nThank you for the flowers.\n",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == "thank-you-email-to-judy"
    assert payload["title"] == "Thank You Email to Judy"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["artifact_snapshot"]["source"] == "artifact"
    assert payload["artifact_snapshot"]["artifact_origin"] == "whiteboard"
    assert payload["artifact_snapshot"]["artifact_lifecycle"] == "whiteboard_snapshot"
    assert (repo_root / "workspaces" / "thank-you-email-to-judy.md").exists()
    assert (repo_root / "artifacts" / f"{payload['artifact_snapshot']['id']}.md").exists()

    workspace = client.get("/api/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == "thank-you-email-to-judy"


def test_chat_can_use_unsaved_workspace_id_with_live_buffer(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    unsaved_content = "# Thank You Email to Judy\n\nHi Judy,\n\nThank you for the flowers.\n"
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        workspace = kwargs["workspace"]
        assert workspace.workspace_id == "thank-you-email-to-judy"
        assert workspace.title == "Thank You Email to Judy"
        assert workspace.content == unsaved_content
        return "I used the unsaved thank-you email draft."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Unsaved workspace buffers should stay transient until the user saves them.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Please review this draft.",
            "history": [],
            "workspace_id": "thank-you-email-to-judy",
            "workspace_scope": "visible",
            "workspace_content": unsaved_content,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I used the unsaved thank-you email draft."
    assert payload["workspace"]["workspace_id"] == "thank-you-email-to-judy"
    assert payload["workspace"]["title"] == "Thank You Email to Judy"
    assert payload["workspace"]["content"] == unsaved_content
    assert not (repo_root / "workspaces" / "thank-you-email-to-judy.md").exists()
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_chat_ignores_unsaved_workspace_when_whiteboard_is_out_of_scope(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        workspace = kwargs["workspace"]
        assert workspace.workspace_id == "thank-you-email-to-judy"
        assert workspace.content == ""
        return "I answered without pulling in the hidden whiteboard."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="A hidden unsaved whiteboard should not influence ordinary chat turns.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Just answer this in chat.",
            "history": [],
            "workspace_id": "thank-you-email-to-judy",
            "workspace_scope": "excluded",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I answered without pulling in the hidden whiteboard."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")
    assert payload["workspace"]["workspace_id"] == "thank-you-email-to-judy"
    assert payload["workspace"]["context_scope"] == "excluded"
    assert payload["workspace"]["content"] is None
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"


def test_chat_excludes_live_workspace_buffer_when_scope_is_excluded(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    hidden_buffer = "# Secret Draft\n\nThis should stay out of the turn.\n"

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        workspace = kwargs["workspace"]
        assert workspace.workspace_id == "v5-milestone-1"
        assert workspace.content == ""
        return "I answered without using the hidden live whiteboard buffer."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="A live whiteboard buffer should not count when the request explicitly excludes it.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Keep this in chat only.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "excluded",
            "workspace_content": hidden_buffer,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I answered without using the hidden live whiteboard buffer."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")
    assert payload["workspace"]["context_scope"] == "excluded"
    assert payload["workspace"]["content"] is None
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["context_sources"] == []


def test_open_accepts_record_id_alias_for_memory(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    opened = client.post("/api/concepts/open", json={"record_id": "user-prefers-chat-first-ux"})
    assert opened.status_code == 200
    opened_payload = opened.json()
    assert opened_payload["workspace_id"] == "user-prefers-chat-first-ux"
    assert opened_payload["scope"] == "durable"
    assert "# User Prefers Chat-First UX" in opened_payload["content"]
    assert "normal LLM conversation" in opened_payload["content"]
    assert opened_payload["graph_action"]["type"] == "open_saved_item_into_workspace"
    assert opened_payload["graph_action"]["record_id"] == "user-prefers-chat-first-ux"
    assert opened_payload["graph_action"]["concept_id"] == "user-prefers-chat-first-ux"
    assert opened_payload["graph_action"]["source"] == "memory"
    assert opened_payload["graph_action"]["source_scope"] == "durable"
    assert opened_payload["graph_action"]["opened_copy_scope"] == "durable"
    assert opened_payload["source_provenance"]["scope"] == "durable"
    assert opened_payload["opened_copy"]["writable"] is True


def test_open_canonical_saved_item_preserves_source_and_copy_provenance(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)
    record = MemoryStore(repo_root / "canonical" / "memories").create_memory(
        title="Canonical Briefing Note",
        card="Canonical memory card.",
        body="Canonical memory body.",
    )

    opened = client.post("/api/concepts/open", json={"record_id": record.id})

    assert opened.status_code == 200
    opened_payload = opened.json()
    assert opened_payload["workspace_id"] == record.id
    assert opened_payload["scope"] == "durable"
    assert opened_payload["source_provenance"] == {
        "relationship": "source_record",
        "record_id": record.id,
        "record_title": record.title,
        "source": "memory",
        "type": "memory",
        "scope": "canonical",
        "durability": "durable",
        "is_canonical": True,
    }
    assert "path" not in opened_payload["source_provenance"]
    assert opened_payload["opened_copy"]["scope"] == "durable"
    assert opened_payload["opened_copy"]["durability"] == "durable"
    assert opened_payload["opened_copy"]["is_canonical"] is False
    assert opened_payload["opened_copy"]["writable"] is True
    assert opened_payload["opened_copy"]["source_scope"] == "canonical"
    assert opened_payload["graph_action"]["source_scope"] == "canonical"
    assert opened_payload["graph_action"]["opened_copy_scope"] == "durable"


def test_open_missing_saved_item_returns_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    opened = client.post("/api/concepts/open", json={"record_id": "missing-saved-item"})

    assert opened.status_code == 404
    assert "was not found" in opened.json()["detail"]


@pytest.mark.parametrize("action", ["mark_incorrect", "forget"])
def test_record_corrections_hide_saved_items_without_hard_delete(
    tmp_path: Path,
    monkeypatch,
    action: str,
) -> None:
    client, repo_root = _client(tmp_path)
    record_id = "user-prefers-chat-first-ux"
    record_path = repo_root / "memories" / f"{record_id}.md"
    assert record_path.exists()
    assert record_id in _saved_note_ids(client.get("/api/memory").json())

    corrected = client.post(
        f"/api/records/memory/{record_id}/corrections",
        json={"action": action, "reason": "The saved preference is no longer correct."},
    )

    assert corrected.status_code == 200
    payload = corrected.json()["correction"]
    assert payload["source"] == "memory"
    assert payload["record_id"] == record_id
    assert payload["action"] == action
    assert payload["effect"] == "suppressed"
    assert payload["visibility"] == "hidden"
    assert payload["hard_deleted"] is False
    assert payload["scope"] == "durable"
    assert payload["hidden_record_scope"] == "durable"
    assert payload["status"] in {"hidden", "suppressed"}
    assert payload["correction_record"] == {
        "id": record_id,
        "source": "memory",
        "status": payload["status"],
        "correction_action": action,
        "scope": "durable",
        "suppresses_canonical": False,
    }
    assert not _payload_has_key(payload, "freshness")
    assert not _payload_has_key(payload, "confidence")
    assert record_path.exists()
    record_text = record_path.read_text(encoding="utf-8")
    assert "status: suppressed" in record_text
    assert f"correction_action: {action}" in record_text
    assert "correction_reason: The saved preference is no longer correct." in record_text

    memory = client.get("/api/memory")
    assert memory.status_code == 200
    assert record_id not in _saved_note_ids(memory.json())

    search = client.get("/api/memory/search", params={"query": "chat-first ux"})
    assert search.status_code == 200
    assert all(item.get("id") != record_id for item in search.json()["results"])

    fetched = client.get(f"/api/memory/{record_id}")
    assert fetched.status_code == 404

    opened = client.post("/api/concepts/open", json={"record_id": record_id})
    assert opened.status_code == 404

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="No durable write for correction regression."),
    )
    chat = client.post(
        "/api/chat",
        json={
            "message": "What do I prefer about chat-first UX?",
            "history": [],
            "selected_record_id": record_id,
            "memory_intent": "dont_save",
        },
    )
    assert chat.status_code == 200
    chat_payload = chat.json()
    assert chat_payload["pinned_context"] is None
    assert chat_payload["selected_record"] is None
    assert all(item.get("id") != record_id for item in chat_payload["candidate_memory_results"])
    assert all(item.get("id") != record_id for item in chat_payload["working_memory"])


def test_record_corrections_suppress_durable_records_from_experiment_scope(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)
    record_id = "user-prefers-chat-first-ux"
    durable_record_path = repo_root / "memories" / f"{record_id}.md"
    assert durable_record_path.exists()

    started = client.post("/api/experiment/start", json={"seed_from_workspace": False})
    assert started.status_code == 200
    session_id = started.json()["experiment"]["session_id"]
    experiment_suppression_path = repo_root / "state" / "experiments" / session_id / "memories" / f"{record_id}.md"
    assert not experiment_suppression_path.exists()

    corrected = client.post(
        f"/api/records/memory/{record_id}/corrections",
        json={"action": "mark_incorrect", "reason": "Do not use this durable memory in the experiment."},
    )

    assert corrected.status_code == 200
    payload = corrected.json()["correction"]
    assert payload["source"] == "memory"
    assert payload["record_id"] == record_id
    assert payload["action"] == "mark_incorrect"
    assert payload["scope"] == "experiment"
    assert payload["hidden_record_scope"] == "durable"
    assert payload["status"] in {"hidden", "suppressed"}
    assert payload["suppresses_canonical"] is False
    assert durable_record_path.exists()
    assert experiment_suppression_path.exists()

    memory = client.get("/api/memory")
    assert memory.status_code == 200
    assert record_id not in _saved_note_ids(memory.json())

    ended = client.post("/api/experiment/end")
    assert ended.status_code == 200
    assert ended.json()["ended"] is True

    memory_after = client.get("/api/memory")
    assert memory_after.status_code == 200
    assert record_id in _saved_note_ids(memory_after.json())


def test_record_corrections_suppress_canonical_memory_per_user_without_mutating_canonical(tmp_path: Path) -> None:
    client, repo_root = _client(
        tmp_path,
        auth_users={
            "eden": "eden-password",
            "jordan": "jordan-password",
        },
    )
    record_id = "canonical-launch-memory"
    canonical_memories = repo_root / "canonical" / "memories"
    canonical_memories.mkdir(parents=True, exist_ok=True)
    canonical_path = canonical_memories / f"{record_id}.md"
    canonical_text = (
        "---\n"
        f"id: {record_id}\n"
        "title: Canonical Launch Memory\n"
        "type: memory\n"
        "card: Canonical launch memory available to every user.\n"
        "created_at: 2026-04-29\n"
        "updated_at: 2026-04-29\n"
        "links_to: []\n"
        "comes_from: []\n"
        "status: active\n"
        "---\n\n"
        "Canonical launch memory body.\n"
    )
    canonical_path.write_text(canonical_text, encoding="utf-8")
    eden_headers = _basic_auth_header("eden", "eden-password")
    jordan_headers = _basic_auth_header("jordan", "jordan-password")

    assert record_id in _saved_note_ids(client.get("/api/memory", headers=eden_headers).json())
    assert record_id in _saved_note_ids(client.get("/api/memory", headers=jordan_headers).json())

    corrected = client.post(
        f"/api/records/memory/{record_id}/corrections",
        json={"action": "mark_incorrect", "reason": "Eden should not use this default."},
        headers=eden_headers,
    )

    assert corrected.status_code == 200
    payload = corrected.json()["correction"]
    assert payload["source"] == "memory"
    assert payload["record_id"] == record_id
    assert payload["scope"] == "durable"
    assert payload["hidden_record_scope"] == "canonical"
    assert payload["suppresses_canonical"] is True
    assert payload["hard_deleted"] is False
    assert payload["correction_record"]["suppresses_canonical"] is True
    assert canonical_path.read_text(encoding="utf-8") == canonical_text

    eden_tombstone = repo_root / "users" / "eden" / "memories" / f"{record_id}.md"
    jordan_tombstone = repo_root / "users" / "jordan" / "memories" / f"{record_id}.md"
    assert eden_tombstone.exists()
    assert "status: suppressed" in eden_tombstone.read_text(encoding="utf-8")
    assert "suppresses_canonical: true" in eden_tombstone.read_text(encoding="utf-8")
    assert not jordan_tombstone.exists()

    assert record_id not in _saved_note_ids(client.get("/api/memory", headers=eden_headers).json())
    assert client.get(f"/api/memory/{record_id}", headers=eden_headers).status_code == 404
    eden_search = client.get("/api/memory/search", params={"query": "canonical launch"}, headers=eden_headers)
    assert eden_search.status_code == 200
    assert all(item.get("id") != record_id for item in eden_search.json()["results"])

    jordan_memory = client.get("/api/memory", headers=jordan_headers)
    assert jordan_memory.status_code == 200
    assert record_id in _saved_note_ids(jordan_memory.json())
    jordan_fetch = client.get(f"/api/memory/{record_id}", headers=jordan_headers)
    assert jordan_fetch.status_code == 200
    assert jordan_fetch.json()["item"]["scope"] == "canonical"


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "make_temporary"},
        {"action": "direct_edit", "body": "Replace the saved item body."},
        {"action": "set_freshness", "freshness": "stale"},
        {"action": "set_confidence", "confidence": 0.2},
    ],
)
def test_record_corrections_reject_unsupported_mutation_semantics(
    tmp_path: Path,
    payload: dict[str, Any],
) -> None:
    client, repo_root = _client(tmp_path)
    record_id = "user-prefers-chat-first-ux"

    corrected = client.post(f"/api/records/memory/{record_id}/corrections", json=payload)

    assert corrected.status_code in {400, 422}
    assert (repo_root / "memories" / f"{record_id}.md").exists()
    memory = client.get("/api/memory")
    assert memory.status_code == 200
    assert record_id in _saved_note_ids(memory.json())


def test_draft_request_auto_drafts_whiteboard_without_memory_write(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    chat = client.post(
        "/api/chat",
        json={
            "message": "Help me draft an essay about preparing a Thanksgiving dinner.",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert chat.status_code == 200
    payload = chat.json()
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["surface_invocation"]["intent"] == "durable_artifact"
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["persisted"] is False
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    artifact_ids = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    assert "help-me-draft-an-essay-about-preparing-a-thanksgiving-dinner" in artifact_ids
    memory_ids = {path.stem for path in (repo_root / "memories").glob("*.md")}
    assert "help-me-draft-an-essay-about-preparing-a-thanksgiving-dinner" not in memory_ids


def test_plan_request_can_draft_detail_into_whiteboard(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    workspace_path = repo_root / "workspaces" / "v5-milestone-1.md"
    original_workspace = workspace_path.read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I drafted a 7-day road trip plan into the whiteboard so we can refine it together.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# 7-Day Road Trip From San Diego To San Francisco\n\n"
            "## Day 1\n"
            "- La Jolla Cove\n"
            "- Carlsbad Village\n"
            "- Mission San Juan Capistrano\n\n"
            "## Day 2\n"
            "- Laguna Beach\n"
            "- Huntington Beach Pier\n"
            "- The Queen Mary\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Whiteboard drafting should stay temporary unless the user explicitly saves it.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Let us plan a road trip from San Diego to San Francisco over 7 days with 3 sightseeing stops per day.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "draft",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["assistant_message"] == "I drafted a 7-day road trip plan into the whiteboard so we can refine it together."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["decision"] is None
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert payload["workspace_update"]["persisted"] is False
    assert "whiteboard" in payload["workspace_update"]["summary"].lower()
    assert payload["workspace"]["workspace_id"] == "v5-milestone-1"
    assert payload["workspace"]["title"] == "V5 Milestone 1 Workspace"
    assert payload["workspace"]["content"] is None
    assert payload["workspace_update"]["title"] == "7-Day Road Trip From San Diego To San Francisco"
    assert "## Day 1" in payload["workspace_update"]["content"]
    assert "Mission San Juan Capistrano" in payload["workspace_update"]["content"]
    assert "## Day 1" not in payload["assistant_message"]
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["workspace_update"]["artifact_snapshot_id"] == payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["draft_authority"]["action"] == "whiteboard_draft"
    assert final_response["turn_plan"]["draft_authority"]["allowed"] is True
    assert final_response["turn_plan"]["validation"]["warnings"] == []

    assert workspace_path.read_text(encoding="utf-8") == original_workspace


def test_work_product_request_can_offer_whiteboard_collaboration(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "offer"
        return (
            "CHAT_RESPONSE: This sounds like a concrete draft. Want me to pull up the whiteboard so we can write the email there?\n\n"
            "WHITEBOARD_OFFER: Whiteboard ready for collaboratively drafting the email."
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Offering whiteboard collaboration should not create durable state.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Write an email declining the meeting.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "offer",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["assistant_message"] == "This sounds like a concrete draft. Want me to pull up the whiteboard so we can write the email there?"
    assert payload["workspace_update"]["type"] == "offer_whiteboard"
    assert payload["workspace_update"]["status"] == "offered"
    assert payload["workspace_update"]["decision"] is None
    assert payload["workspace_update"]["proposal_kind"] == "offer"
    assert payload["workspace_update"]["persisted"] is False
    assert payload["workspace_update"]["summary"] == "Whiteboard ready for collaboratively drafting the email."
    assert payload["workspace"]["workspace_id"] == "v5-milestone-1"
    assert payload["workspace"]["content"] is None
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["turn_plan"]["draft_authority"]["action"] == "whiteboard_offer"
    assert final_response["turn_plan"]["draft_authority"]["allowed"] is True
    assert final_response["turn_plan"]["validation"]["warnings"] == []
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_same_line_whiteboard_offer_is_parsed_without_leaking_tags(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: Want me to open the whiteboard for this email? "
            "WHITEBOARD_OFFER: I can draft the beta invitation there."
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Offer stays pending."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft an email inviting a beta tester.",
            "history": [],
            "whiteboard_mode": "offer",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Want me to open the whiteboard for this email?"
    assert "WHITEBOARD_OFFER" not in payload["assistant_message"]
    assert payload["workspace_update"]["type"] == "offer_whiteboard"
    assert payload["workspace_update"]["summary"] == "I can draft the beta invitation there."


def test_natural_whiteboard_offer_can_be_structured_by_second_call(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    verifier_calls = []
    normalizer_calls = []

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I can open a whiteboard and draft a warm beta invitation there.",
    )
    def _verify(self, **kwargs):
        verifier_calls.append(kwargs)
        return ReplyVerification(
            ok=False,
            repair_strategy="normalize_json",
            issues=("missing_typed_whiteboard_offer",),
            retry_instruction="Convert the natural-language offer into an offer_whiteboard update.",
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._verify_openai_reply", _verify)
    def _structure(self, **kwargs):
        normalizer_calls.append(kwargs)
        return (
            "Want me to open the whiteboard for this email?",
            None,
            WorkspaceOffer(summary="I can draft the beta invitation there."),
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._structure_openai_reply", _structure)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Offer stays pending."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft an email inviting a beta tester.",
            "history": [],
            "whiteboard_mode": "offer",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Want me to open the whiteboard for this email?"
    assert payload["workspace_update"]["type"] == "offer_whiteboard"
    assert payload["workspace_update"]["summary"] == "I can draft the beta invitation there."
    assert verifier_calls
    assert verifier_calls[0]["whiteboard_mode"] == "offer"
    assert normalizer_calls[0]["verifier_feedback"].issues == ("missing_typed_whiteboard_offer",)


def test_staged_whiteboard_draft_retries_before_persisting_artifact(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    replies = [
        "CHAT_RESPONSE: I can draft that in the whiteboard.",
        "CHAT_RESPONSE: I drafted the email into the whiteboard.\nWHITEBOARD_DRAFT: # Beta Invitation\n\nHi Jamie,\n\nWould you like to try the Vantage beta?\n\nBest,\nJordan",
    ]
    calls = []
    artifact_count_before = len(list((repo_root / "artifacts").glob("*.md")))

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        calls.append(kwargs)
        return replies.pop(0)

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._verify_openai_reply",
        lambda self, **kwargs: ReplyVerification(ok=True),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Draft artifact is enough for this test."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft an email inviting Jamie to the private beta in the whiteboard.",
            "history": [],
            "whiteboard_mode": "draft",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(calls) == 2
    assert calls[0]["stage_retry_instruction"] is None
    assert "WHITEBOARD_DRAFT" in calls[1]["stage_retry_instruction"]
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["content"].startswith("# Beta Invitation")
    assert payload["stage_audit"]["accepted"] is True
    assert any(event["id"] == "stage_restage" for event in payload["stage_progress"])
    assert len(list((repo_root / "artifacts").glob("*.md"))) == artifact_count_before + 1


def test_surface_policy_overrides_interpreter_offer_for_durable_artifact(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
            lambda self, **kwargs: NavigationDecision(
                mode="chat",
                confidence=0.91,
                reason="The user is asking for a concrete work product, so the turn should invite whiteboard collaboration first.",
                whiteboard_mode="offer",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I drafted the email in the whiteboard so we can refine it there.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email Declining Meeting\n\n"
            "Subject: Meeting\n\n"
            "Hi Maya,\n\n"
            "I need to decline the meeting, but I appreciate the invitation.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="The surface policy made this an inspectable whiteboard draft.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Write an email declining the meeting.",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I drafted the email in the whiteboard so we can refine it there."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert "Subject: Meeting" in payload["workspace_update"]["content"]
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["turn_interpretation"]["whiteboard_mode_source"] == "surface_invocation"
    assert payload["surface_invocation"]["intent"] == "durable_artifact"
    assert payload["surface_invocation"]["primary_surface"] == "whiteboard"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_surface_policy_auto_drafts_simple_email_with_protocol(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
            lambda self, **kwargs: NavigationDecision(
                mode="chat",
                confidence=0.91,
                reason="The interpreter kept this in chat, but surface policy should promote durable artifacts.",
                whiteboard_mode="chat",
                control_panel={
                "actions": [
                    {"type": "apply_protocol", "protocol_kind": "email", "reason": "Use the email protocol."},
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        assert any(item.id == "email-drafting-protocol" for item in kwargs["vetted_memory"])
        return (
            "CHAT_RESPONSE: I drafted the email in the whiteboard so we can refine it there.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email Declining Meeting\n\n"
            "Subject: Meeting\n\n"
            "Hi Maya,\n\n"
            "I need to decline the meeting, but I appreciate the invitation.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="The whiteboard draft stays proposed until the user applies or saves it.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Write an email declining the meeting.",
            "history": [],
            "workspace_id": "v5-milestone-1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I drafted the email in the whiteboard so we can refine it there."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert payload["workspace_update"]["title"] == "Email Declining Meeting"
    assert "Subject: Meeting" in payload["workspace_update"]["content"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["turn_interpretation"]["whiteboard_mode_source"] == "surface_invocation"
    assert payload["surface_invocation"]["intent"] == "durable_artifact"
    assert payload["surface_invocation"]["primary_surface"] == "whiteboard"
    assert payload["surface_invocation"]["resolved_whiteboard_mode"] == "draft"
    assert any(item["id"] == "email-drafting-protocol" for item in payload["working_memory"])
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_explicit_whiteboard_request_bypasses_offer_step(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return NavigationDecision(
            mode="chat",
            confidence=0.89,
            reason="The turn is a concrete draft request that would normally invite whiteboard collaboration first.",
            whiteboard_mode="offer",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I drafted the thank-you email into the whiteboard so we can refine it together.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Subject: Thank You for the Flowers\n\n"
            "Hi Judy,\n\n"
            "Thank you so much for the flowers you dropped off. That was so thoughtful, and I really appreciated it.\n\n"
            "Warmly,\n"
            "[Your Name]\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="An explicit whiteboard draft request should stay temporary until the user chooses to save it.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Open the whiteboard and draft a thank-you email to Judy for the flowers she dropped off.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["assistant_message"] == "I drafted the thank-you email into the whiteboard so we can refine it together."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert payload["workspace_update"]["title"] == "Thank You Email To Judy"
    assert "Thank you so much for the flowers" in payload["workspace_update"]["content"]
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["turn_interpretation"]["whiteboard_mode_source"] == "request"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["workspace_update"]["artifact_snapshot_id"] == payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_whiteboard_draft_constraints_remove_em_dashes(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I updated the email.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email Draft\n\n"
            "Hi Jamie,\n\n"
            "If this is not the right time—that is completely fine.\n"
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Draft stays temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Remove any em dashes from the whiteboard email.",
            "history": [],
            "whiteboard_mode": "draft",
        },
    )
    assert response.status_code == 200
    content = response.json()["workspace_update"]["content"]
    assert "—" not in content
    assert "time, that" in content


def test_whiteboard_draft_constraints_shorten_optional_reading_section(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    long_section = " ".join(f"word{i}" for i in range(140))

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I updated the email.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email Draft\n\n"
            "Hi Jamie,\n\n"
            "See below.\n\n"
            "## Optional reading\n\n"
            f"{long_section}\n"
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Draft stays temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Add the essay as a short optional reading section to the email.",
            "history": [],
            "whiteboard_mode": "draft",
        },
    )
    assert response.status_code == 200
    content = response.json()["workspace_update"]["content"]
    assert "## Optional reading" in content
    assert len(re.findall(r"word\d+", content)) <= 75


def test_whiteboard_email_draft_preserves_known_signature_placeholder(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I updated the email.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email Draft\n\n"
            "Hi Priya,\n\n"
            "Here is the revised note.\n\n"
            "Best,\n"
            "[Your Name]\n"
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Draft stays temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Update this email with the new essay context.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": (
                "# Email Draft\n\n"
                "Hi Priya,\n\n"
                "Earlier draft.\n\n"
                "Best,\n"
                "Eden\n"
            ),
            "whiteboard_mode": "draft",
        },
    )
    assert response.status_code == 200
    content = response.json()["workspace_update"]["content"]
    assert "Best,\nEden" in content
    assert "[Your Name]" not in content


def test_pending_whiteboard_offer_deictic_whiteboard_follow_up_carries(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return NavigationDecision(
            mode="chat",
            confidence=0.93,
            reason="The user is pointing back to the pending draft with a narrow whiteboard follow-up.",
            whiteboard_mode="draft",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I put that in the whiteboard so we can keep refining it.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Hi Judy,\n\n"
            "Thank you again for the flowers.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="A narrow deictic whiteboard follow-up should stay pending."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Open it, put that in the whiteboard.",
            "history": [
                {
                    "user_message": pending_workspace_update["origin_user_message"],
                    "assistant_message": pending_workspace_update["origin_assistant_message"],
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert "pending_whiteboard" in payload["response_mode"]["context_sources"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"


def test_pending_whiteboard_offer_new_explicit_whiteboard_request_drops_stale_pending_context(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="This is a fresh whiteboard drafting request, not acceptance of the older pending offer.",
            whiteboard_mode="auto",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I drafted the 7-day road trip itinerary into the whiteboard so we can refine it there.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# 7-Day Road Trip Itinerary\n\n"
            "Day 1: Depart and drive north.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="A fresh explicit whiteboard request should stay temporary without carrying stale pending context."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Okay, draft a 7-day road trip itinerary in the whiteboard.",
            "history": [
                {
                    "user_message": pending_workspace_update["origin_user_message"],
                    "assistant_message": pending_workspace_update["origin_assistant_message"],
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert "pending_whiteboard" not in payload["response_mode"]["context_sources"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["turn_interpretation"]["whiteboard_mode_source"] == "request"


def test_pending_whiteboard_offer_follow_up_can_drive_draft_mode(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return NavigationDecision(
            mode="chat",
            confidence=0.95,
            reason="The user accepted the pending whiteboard invitation and wants the draft now.",
            whiteboard_mode="draft",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return (
            "CHAT_RESPONSE: I drafted the thank-you email into the whiteboard so we can refine the tone together.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Subject: Thank you for the flowers\n\n"
            "Hi Judy,\n\n"
            "Thank you so much for the beautiful flowers you dropped off. That was such a thoughtful surprise, and it really brightened my day.\n\n"
            "I really appreciated your kindness and wanted you to know how much it meant to me.\n\n"
            "Warmly,\n"
            "[Your Name]\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Explicit whiteboard drafting should stay temporary until the user saves it.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Yes. Whenever I ask for an email, do it with a whiteboard.",
            "history": [
                {
                    "user_message": "Lets draft an email to Judy thanking her for the flowers she dropped off.",
                    "assistant_message": "Would you like to pull up a whiteboard so we can write the thank-you email there?",
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["assistant_message"] == "I drafted the thank-you email into the whiteboard so we can refine the tone together."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["title"] == "Thank You Email To Judy"
    assert "Thank you so much for the beautiful flowers" in payload["workspace_update"]["content"]
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["context_sources"] == ["recent_chat", "pending_whiteboard"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["turn_interpretation"]["whiteboard_mode_source"] == "interpreter"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["workspace_update"]["artifact_snapshot_id"] == payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_pending_whiteboard_offer_follow_up_backfills_status_from_type_alias(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = {
        "type": "offer_whiteboard",
        "summary": "Whiteboard ready for collaboratively drafting the email.",
        "origin_user_message": "draft an email to jerry asking him how his day is going",
        "origin_assistant_message": "Would you like to pull up a whiteboard?",
    }

    def _route(self, **kwargs):
        pending = kwargs["pending_workspace_update"]
        assert pending is not None
        assert pending["type"] == "offer_whiteboard"
        assert pending["status"] == "offered"
        return NavigationDecision(
            mode="chat",
            confidence=0.95,
            reason="The user accepted the pending whiteboard invitation and wants the draft now.",
            whiteboard_mode="draft",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        pending = kwargs["pending_workspace_update"]
        assert pending is not None
        assert pending["type"] == "offer_whiteboard"
        assert pending["status"] == "offered"
        return (
            "CHAT_RESPONSE: The draft is now in the whiteboard.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email To Jerry\n\n"
            "Hi Jerry,\n\n"
            "How is your day going?\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Pending whiteboard context should stay temporary.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "yes, let's do that",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["response_mode"]["grounding_mode"] == "pending_whiteboard"
    assert payload["response_mode"]["context_sources"] == ["pending_whiteboard"]


def test_pending_whiteboard_offer_accept_phrase_lets_do_that_carries(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return NavigationDecision(
            mode="chat",
            confidence=0.92,
            reason="The user accepted the pending offer with a short confirmation phrase.",
            whiteboard_mode="draft",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I drafted the thank-you email into the whiteboard so we can refine it together.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Hi Judy,\n\n"
            "Thank you again for the flowers.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Short acceptance follow-ups should stay temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Let's do that.",
            "history": [
                {
                    "user_message": pending_workspace_update["origin_user_message"],
                    "assistant_message": pending_workspace_update["origin_assistant_message"],
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["context_sources"] == ["recent_chat", "pending_whiteboard"]


def test_pending_whiteboard_offer_continue_phrase_carries_with_reference(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The user asked to resume the pending draft explicitly.",
            whiteboard_mode="draft",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return (
            "CHAT_RESPONSE: I resumed the draft in the whiteboard so we can keep refining it.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Hi Judy,\n\n"
            "Thank you again for the flowers.\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Resumed whiteboard drafting should stay pending."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Resume that draft.",
            "history": [
                {
                    "user_message": pending_workspace_update["origin_user_message"],
                    "assistant_message": pending_workspace_update["origin_assistant_message"],
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["context_sources"] == ["recent_chat", "pending_whiteboard"]


def test_pending_whiteboard_offer_long_accept_message_does_not_carry(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()
    long_message = (
        "That works, but before we do anything else I want to switch topics completely and talk through "
        "the quarterly planning assumptions, the travel budget, the meeting schedule, the hiring plan, "
        "and several unrelated notes in one long message that should definitely exceed the pending follow-up guard."
    )
    assert len(long_message) > 240

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return NavigationDecision(
            mode="chat",
            confidence=0.75,
            reason="The message is too long to count as a narrow pending-offer follow-up.",
            whiteboard_mode="auto",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return "I answered without carrying the stale pending whiteboard offer."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Long unrelated turns should drop stale pending whiteboard context."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": long_message,
            "history": [],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["context_sources"] == []


def test_pending_whiteboard_offer_continue_without_reference_does_not_carry(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return NavigationDecision(
            mode="chat",
            confidence=0.76,
            reason="A generic continue message without draft reference should not carry stale pending context.",
            whiteboard_mode="auto",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return "I answered without carrying the pending whiteboard offer."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Continuation without a draft reference should stay ordinary chat."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Continue with the budget assumptions for next quarter.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["context_sources"] == []


def test_offer_mode_downgrades_misclassified_whiteboard_draft(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "offer"
        return (
            "CHAT_RESPONSE: Here is a draft email you can review in the whiteboard.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Email Draft\n\n"
            "Hi Jerry,\n\n"
            "How is your day going?\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Offer-first turns should not silently bypass the whiteboard invitation.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Write an email asking Jerry how his day is going.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "offer",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["assistant_message"] == "This looks like a concrete draft. Want me to open the whiteboard so we can work on it together?"
    assert payload["workspace_update"]["type"] == "offer_whiteboard"
    assert payload["workspace_update"]["status"] == "offered"
    assert payload["workspace_update"]["proposal_kind"] == "offer"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_visible_whiteboard_edit_follow_up_prefers_draft_over_offer(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="The user is revising a concrete work product.",
            whiteboard_mode="offer",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I updated the email draft in the whiteboard to add your signature.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email\n\n"
            "Hi Jerry,\n\n"
            "I hope your day is going well.\n\n"
            "Best,\n"
            "Jordan\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Updating the active whiteboard draft should stay temporary until it is saved.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Add a signature to the email.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": "# Thank You Email\n\nHi Jerry,\n\nI hope your day is going well.\n\nBest,\n[Your Name]\n",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["assistant_message"] == "I updated the email draft in the whiteboard to add your signature."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["status"] == "draft_ready"
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["response_mode"]["grounding_mode"] == "whiteboard"
    assert payload["response_mode"]["context_sources"] == ["whiteboard"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["workspace"]["context_scope"] == "visible"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_visible_whiteboard_greeting_edit_follow_up_prefers_draft_over_offer(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The user is revising the current whiteboard draft.",
            whiteboard_mode="offer",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I updated the greeting in the whiteboard draft.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email\n\n"
            "Dear Jerry,\n\n"
            "I hope your day is going well.\n\n"
            "Best,\n"
            "Jordan\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Greeting edits on the active draft should stay temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Change the greeting.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": "# Thank You Email\n\nHi Jerry,\n\nI hope your day is going well.\n\nBest,\nJordan\n",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I updated the greeting in the whiteboard draft."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["response_mode"]["grounding_mode"] == "whiteboard"
    assert payload["response_mode"]["context_sources"] == ["whiteboard"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["workspace"]["context_scope"] == "visible"
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_visible_whiteboard_make_and_mention_follow_up_prefers_draft_over_offer(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The model over-offered despite an active draft.",
            whiteboard_mode="offer",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I made the email warmer and mentioned the 20-minute feedback window.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Morgan Beta Invitation\n\n"
            "Hi Morgan,\n\n"
            "I hope you're doing well. I immediately thought of you for a small Vantage private beta next week. "
            "It would only take 20 minutes of feedback, and your perspective would be really helpful.\n\n"
            "Best,\n"
            "Jordan\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Active draft revision should stay temporary."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Make the email warmer and mention that the beta would only take 20 minutes of feedback.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": "# Morgan Beta Invitation\n\nHi Morgan,\n\nWould you join the Vantage beta?\n\nBest,\nJordan\n",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I made the email warmer and mentioned the 20-minute feedback window."
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"
    assert payload["workspace"]["context_scope"] == "visible"
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_visible_whiteboard_edit_follow_up_with_preserve_none_does_not_auto_preserve_selected_record(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    selected_record_path = repo_root / "concepts" / "rules-of-hangman-game.md"
    selected_record_path.write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )
    live_whiteboard = "# Thank You Email\n\nHi Jerry,\n\nI hope your day is going well.\n"

    def _route(self, **kwargs):
        assert kwargs["workspace"].content == live_whiteboard
        return NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="The user is editing the live whiteboard draft, so the whiteboard should stay in focus.",
            whiteboard_mode="draft",
            preserve_selected_record=None,
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.search.ConceptSearchService.search_context",
        lambda self, **kwargs: [
            CandidateMemory(
                id="email-polish",
                title="Email Polish",
                type="concept",
                card="Ways to tighten the draft email.",
                score=9.2,
                reason="The user is revising an email draft.",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="signature-note",
                title="Signature Note",
                type="concept",
                card="A reminder to add a closing signature.",
                score=8.9,
                reason="Another whiteboard-adjacent concept candidate.",
                source="concept",
                trust="high",
            ),
        ],
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["workspace"].content == live_whiteboard
        assert kwargs["selected_memory"] is None
        assert all(item.id != "rules-of-hangman-game" for item in kwargs["vetted_memory"])
        return "I updated the draft without pulling the selected record back in."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Live whiteboard edits should not auto-preserve an unrelated selected record.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Add it.",
            "history": [
                {
                    "user_message": "Change the greeting in the draft.",
                    "assistant_message": "Sure, I can adjust the draft.",
                }
            ],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": live_whiteboard,
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I updated the draft without pulling the selected record back in."
    assert payload["turn_interpretation"]["preserve_selected_record"] is None
    assert all(item["id"] != "rules-of-hangman-game" for item in payload["working_memory"])


def test_pending_whiteboard_follow_up_with_preserve_none_does_not_auto_preserve_selected_record(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    selected_record_path = repo_root / "concepts" / "rules-of-hangman-game.md"
    selected_record_path.write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return NavigationDecision(
            mode="chat",
            confidence=0.93,
            reason="The user is asking a short deictic follow-up on the pending whiteboard flow, so the whiteboard should stay in focus.",
            whiteboard_mode="draft",
            preserve_selected_record=None,
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr(
        "vantage_v5.services.search.ConceptSearchService.search_context",
        lambda self, **kwargs: [
            CandidateMemory(
                id="email-polish",
                title="Email Polish",
                type="concept",
                card="Ways to tighten the draft email.",
                score=9.2,
                reason="The user is continuing a whiteboard-related follow-up.",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="tone-note",
                title="Tone Note",
                type="concept",
                card="A reminder to keep the tone warm.",
                score=8.9,
                reason="Another candidate for the current drafting session.",
                source="concept",
                trust="high",
            ),
        ],
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        assert kwargs["selected_memory"] is None
        assert all(item.id != "rules-of-hangman-game" for item in kwargs["vetted_memory"])
        return "I carried the pending draft forward without reusing the selected record."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Pending whiteboard continuity should outrank an unrelated selected record.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Which one?",
            "history": [
                {
                    "user_message": pending_workspace_update["origin_user_message"],
                    "assistant_message": pending_workspace_update["origin_assistant_message"],
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I carried the pending draft forward without reusing the selected record."
    assert payload["turn_interpretation"]["preserve_selected_record"] is None
    assert "pending_whiteboard" in payload["response_mode"]["context_sources"]
    assert all(item["id"] != "rules-of-hangman-game" for item in payload["working_memory"])


def test_pending_whiteboard_offer_signature_edit_follow_up_carries(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        return NavigationDecision(
            mode="chat",
            confidence=0.92,
            reason="The user is making a greeting/signature edit to the pending draft.",
            whiteboard_mode="draft",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] == pending_workspace_update
        assert kwargs["whiteboard_mode"] == "draft"
        return (
            "CHAT_RESPONSE: I updated the pending draft with the new greeting and signature.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Thank You Email To Judy\n\n"
            "Dear Judy,\n\n"
            "Thank you again for the flowers.\n\n"
            "Best,\n"
            "Jordan\n"
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Greeting/signature edit should stay in the pending whiteboard flow."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "add a signature and greeting",
            "history": [
                {
                    "user_message": pending_workspace_update["origin_user_message"],
                    "assistant_message": pending_workspace_update["origin_assistant_message"],
                }
            ],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert "pending_whiteboard" in payload["response_mode"]["context_sources"]
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "draft"


def test_visible_whiteboard_edit_follow_up_respects_explicit_selected_record_preservation(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    selected_record_path = repo_root / "concepts" / "rules-of-hangman-game.md"
    selected_record_path.write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )
    live_whiteboard = "# Thank You Email\n\nHi Jerry,\n\nI hope your day is going well.\n"
    selected_record_reason = "Keep the selected record anchored even with the live whiteboard draft."

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.96,
            reason="The navigator explicitly keeps the selected record in focus even though the whiteboard is active.",
            whiteboard_mode="draft",
            preserve_selected_record=True,
            selected_record_reason=selected_record_reason,
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.search.ConceptSearchService.search_context",
        lambda self, **kwargs: [
            CandidateMemory(
                id="email-polish",
                title="Email Polish",
                type="concept",
                card="Ways to tighten the draft email.",
                score=9.2,
                reason="The user is revising an email draft.",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="signature-note",
                title="Signature Note",
                type="concept",
                card="A reminder to add a closing signature.",
                score=8.9,
                reason="Another whiteboard-adjacent concept candidate.",
                source="concept",
                trust="high",
            ),
        ],
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["workspace"].content == live_whiteboard
        assert kwargs["selected_memory"] is not None
        assert kwargs["selected_memory"].id == "rules-of-hangman-game"
        assert any(item.id == "rules-of-hangman-game" for item in kwargs["vetted_memory"])
        return "I kept the selected record in scope even with the live whiteboard."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="An explicit navigator preserve request should win over whiteboard continuity.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Add it.",
            "history": [
                {
                    "user_message": "Change the greeting in the draft.",
                    "assistant_message": "Sure, I can adjust the draft.",
                }
            ],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": live_whiteboard,
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I kept the selected record in scope even with the live whiteboard."
    assert any(item["id"] == "rules-of-hangman-game" for item in payload["working_memory"])
    assert payload["turn_interpretation"]["preserve_selected_record"] is True
    assert payload["turn_interpretation"]["selected_record_reason"] == selected_record_reason


def test_hidden_whiteboard_stale_pending_offer_stays_out_of_scope(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = _pending_offer_update()

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return NavigationDecision(
            mode="chat",
            confidence=0.78,
            reason="The user asked an unrelated ordinary chat question.",
            whiteboard_mode="auto",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        workspace = kwargs["workspace"]
        assert workspace.content == ""
        assert kwargs["pending_workspace_update"] is None
        return "I answered in chat without reusing the stale whiteboard offer."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="A hidden stale whiteboard offer should stay out of scope for unrelated chat.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What is a good subject line for a quick reply?",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "excluded",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I answered in chat without reusing the stale whiteboard offer."
    assert not payload["assistant_message"].startswith("This is new to me, but my best guess is:")
    assert payload["workspace"]["context_scope"] == "excluded"
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["context_sources"] == []


def test_chat_drops_pending_whiteboard_without_origin_user_message(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, openai_api_key="test-key")
    pending_workspace_update = {
        "type": "offer_whiteboard",
        "status": "offered",
        "summary": "Whiteboard ready for collaboratively drafting the thank-you email.",
        "origin_assistant_message": "Would you like to pull up a whiteboard so we can write the thank-you email there?",
    }

    def _route(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Pending whiteboard carry should be dropped without the original user prompt.",
            whiteboard_mode="auto",
        )

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert kwargs["pending_workspace_update"] is None
        return "I answered without claiming pending whiteboard grounding."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Pending carry without the origin prompt should not ground chat."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Yes, do it.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "pending_workspace_update": pending_workspace_update,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response_mode"]["grounding_mode"] == "ungrounded"
    assert payload["response_mode"]["context_sources"] == []


def test_chat_uses_current_whiteboard_buffer_before_reply(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    live_whiteboard = "# Live Draft\n\nThis whiteboard content has not been manually saved yet."
    workspace_path = repo_root / "workspaces" / "v5-milestone-1.md"
    original_workspace = workspace_path.read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
        workspace = kwargs["workspace"]
        assert workspace.content == live_whiteboard
        assert workspace.title == "Live Draft"
        return "I used the current whiteboard."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="The turn should stay chat-only after syncing the current whiteboard buffer.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What do you think of the current whiteboard?",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": live_whiteboard,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "I used the current whiteboard."
    assert payload["workspace"]["title"] == "Live Draft"
    assert payload["workspace"]["content"] == live_whiteboard
    assert payload["turn_interpretation"]["whiteboard_entry_mode"] == "continued_current"
    assert payload["workspace_update"] is None
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["grounding_sources"] == ["recall", "whiteboard"]
    assert payload["response_mode"]["context_sources"] == ["recall", "whiteboard"]
    assert payload["response_mode"]["legacy_context_sources"] == ["working_memory", "whiteboard"]
    assert payload["response_mode"]["label"] == "Recall + Whiteboard"
    assert workspace_path.read_text(encoding="utf-8") == original_workspace


def test_whiteboard_entry_mode_distinguishes_fresh_current_and_prior_material(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: "I used the current whiteboard.",
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="The turn stays chat-only while we inspect entry mode."),
    )

    fresh_response = client.post(
        "/api/chat",
        json={
            "message": "Start a fresh draft in the whiteboard.",
            "history": [],
            "workspace_id": "fresh-whiteboard-draft",
            "workspace_scope": "visible",
            "workspace_content": "# Fresh Draft\n\nThis draft starts from scratch.",
        },
    )
    assert fresh_response.status_code == 200
    fresh_payload = fresh_response.json()
    assert fresh_payload["turn_interpretation"]["whiteboard_entry_mode"] == "started_fresh"

    existing_response = client.post(
        "/api/chat",
        json={
            "message": "What do you think of the current whiteboard?",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": "# Live Draft\n\nThis whiteboard content has not been manually saved yet.",
        },
    )
    assert existing_response.status_code == 200
    existing_payload = existing_response.json()
    assert existing_payload["turn_interpretation"]["whiteboard_entry_mode"] == "continued_current"

    (repo_root / "concepts" / "whiteboard-source.md").write_text(
        (
            "---\n"
            "id: whiteboard-source\n"
            "title: Whiteboard Source\n"
            "type: concept\n"
            "card: Source material reopened into the whiteboard.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "This concept can be reopened into the whiteboard.\n"
        ),
        encoding="utf-8",
    )
    opened = client.post("/api/concepts/open", json={"record_id": "whiteboard-source"})
    assert opened.status_code == 200
    opened_payload = opened.json()

    prior_response = client.post(
        "/api/chat",
        json={
            "message": "Add a follow-up note.",
            "history": [],
            "workspace_id": "whiteboard-source",
            "workspace_scope": "visible",
            "workspace_content": opened_payload["content"],
        },
    )
    assert prior_response.status_code == 200
    prior_payload = prior_response.json()
    assert prior_payload["turn_interpretation"]["whiteboard_entry_mode"] == "started_from_prior_material"


def test_keep_in_chat_mode_ignores_whiteboard_signals(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: Keeping this in chat.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Draft That Should Stay Pending\n\n"
            "This should not become a workspace update."
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Keep-in-chat mode should ignore whiteboard signals.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Write a short launch checklist directly in chat.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "chat",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "Keeping this in chat."
    assert payload["workspace_update"] is None
    assert payload["workspace"]["content"] is None
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_navigation_can_preserve_selected_context_for_semantic_follow_up(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    (repo_root / "concepts" / "rules-of-hangman-game.md").write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )

    selected_record_reason = (
        "The selected hangman rules concept should stay in working memory because the user is continuing the same game and applying those rules."
    )

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.93,
            reason="This is a semantic follow-up on the selected hangman rules concept.",
            preserve_selected_record=True,
            selected_record_reason=selected_record_reason,
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _no_relevant_matches_for_tests)

    def _reply(self, **kwargs):
        assert any(item.id == "rules-of-hangman-game" for item in kwargs["vetted_memory"])
        return "The selected rules stay in scope for this turn."

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="Semantic continuity should not create a durable write by itself.",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "let us keep playing with these rules in mind",
            "history": [
                {
                    "user_message": "let us play with these settings",
                    "assistant_message": "Great! We'll play Hangman with 6 max incorrect guesses.",
                }
            ],
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "openai"
    assert payload["assistant_message"] == "The selected rules stay in scope for this turn."
    assert any(item["id"] == "rules-of-hangman-game" for item in payload["concept_cards"])
    assert any(
        item["id"] == "rules-of-hangman-game" and item["recall_reason"] == selected_record_reason
        for item in payload["working_memory"]
    )
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["preserve_selected_record"] is True
    assert payload["turn_interpretation"]["selected_record_reason"] == selected_record_reason
    assert payload["semantic_frame"]["follow_up_type"] == "continuation"
    assert payload["semantic_frame"]["referenced_object"]["id"] == "rules-of-hangman-game"
    assert payload["semantic_frame"]["commitments"][-1] == "Keep the pinned context active for this turn."
    assert selected_record_reason in payload["vetting"]["rationale"]


def test_continuity_anchor_stays_within_five_items(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    (repo_root / "concepts" / "rules-of-hangman-game.md").write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )
    (repo_root / "concepts" / "continuity-a.md").write_text(
        "---\n"
        "id: continuity-a\n"
        "title: Continuity A\n"
        "type: concept\n"
        "card: Continuity candidate A.\n"
        "created_at: 2026-04-13\n"
        "updated_at: 2026-04-13\n"
        "links_to: []\n"
        "comes_from: []\n"
        "status: active\n"
        "---\n\n"
        "continuity anchor test item a.\n",
        encoding="utf-8",
    )
    (repo_root / "concepts" / "continuity-b.md").write_text(
        "---\n"
        "id: continuity-b\n"
        "title: Continuity B\n"
        "type: concept\n"
        "card: Continuity candidate B.\n"
        "created_at: 2026-04-13\n"
        "updated_at: 2026-04-13\n"
        "links_to: []\n"
        "comes_from: []\n"
        "status: active\n"
        "---\n\n"
        "continuity anchor test item b.\n",
        encoding="utf-8",
    )

    def _route(self, **kwargs):
        return NavigationDecision(
            mode="chat",
            confidence=0.95,
            reason="The user is continuing the selected record.",
            preserve_selected_record=True,
            selected_record_reason="Keep the selected record as the continuity anchor.",
        )

    def _search_context(self, **kwargs):
        return [
            CandidateMemory(
                id="continuity-a",
                title="Continuity A",
                type="concept",
                card="Continuity candidate A.",
                score=9.4,
                reason="test candidate a",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="continuity-b",
                title="Continuity B",
                type="concept",
                card="Continuity candidate B.",
                score=9.2,
                reason="test candidate b",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="continuity-c",
                title="Continuity C",
                type="concept",
                card="Continuity candidate C.",
                score=9.0,
                reason="test candidate c",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="continuity-d",
                title="Continuity D",
                type="concept",
                card="Continuity candidate D.",
                score=8.8,
                reason="test candidate d",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="continuity-e",
                title="Continuity E",
                type="concept",
                card="Continuity candidate E.",
                score=8.6,
                reason="test candidate e",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="continuity-f",
                title="Continuity F",
                type="concept",
                card="Continuity candidate F.",
                score=8.4,
                reason="test candidate f",
                source="concept",
                trust="high",
            ),
        ]

    def _vet(self, *, message, candidates, continuity_hint=None, visible_artifacts=None):
        selected = [candidate for candidate in candidates if candidate.id != "rules-of-hangman-game"][:5]
        return selected, {
            "selected_ids": [candidate.id for candidate in selected],
            "none_relevant": False,
            "rationale": "Selected items were filtered from a broad working set.",
        }

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", _route)
    monkeypatch.setattr("vantage_v5.services.search.ConceptSearchService.search_context", _search_context)
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _vet)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Keep the working set bounded."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "let us keep playing with these rules in mind",
            "history": [
                {
                    "user_message": "let us play with these settings",
                    "assistant_message": "Great! We'll play Hangman with 6 max incorrect guesses.",
                }
            ],
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["working_memory"]) == 5
    assert any(item["id"] == "rules-of-hangman-game" for item in payload["working_memory"])
    assert payload["turn_interpretation"]["preserve_selected_record"] is True


def test_off_topic_selected_record_does_not_surface_in_working_memory(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    (repo_root / "concepts" / "rules-of-hangman-game.md").write_text(
        (
            "---\n"
            "id: rules-of-hangman-game\n"
            "title: Rules of Hangman (game)\n"
            "type: concept\n"
            "card: Basic rules and gameplay flow for Hangman, a classic word-guessing game.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Players guess letters one at a time, with up to 6 incorrect guesses before the game ends.\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="The user is asking about an unrelated task, so the selected record should not be forced into scope.",
            preserve_selected_record=False,
        ),
    )

    def _search_context(self, **kwargs):
        return [
            CandidateMemory(
                id="shared-workspace",
                title="Shared Workspace",
                type="concept",
                card="Shared workspace concept.",
                score=9.1,
                reason="related but not the selected record",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="persistent-memory",
                title="Persistent Memory",
                type="concept",
                card="Persistent memory concept.",
                score=8.8,
                reason="another unrelated candidate",
                source="concept",
                trust="high",
            ),
        ]

    monkeypatch.setattr("vantage_v5.services.search.ConceptSearchService.search_context", _search_context)
    monkeypatch.setattr(
        "vantage_v5.services.vetting.ConceptVettingService.vet",
        lambda self, *, message, candidates, continuity_hint=None, visible_artifacts=None: (
            candidates[:2],
            {
                "selected_ids": [candidate.id for candidate in candidates[:2]],
                "none_relevant": False,
                "rationale": "Selected unrelated candidates without preserving the off-topic record.",
            },
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "The selected Hangman rules should stay out of this answer."
            if kwargs["selected_memory"] is None and all(item.id != "rules-of-hangman-game" for item in kwargs["vetted_memory"])
            else (_ for _ in ()).throw(AssertionError("Off-topic selected record leaked into the chat model context."))
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Off-topic turns should not be forced back onto the selected record."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "What color should the launch button be?",
            "history": [
                {
                    "user_message": "let us play with these settings",
                    "assistant_message": "Great! We'll play Hangman with 6 max incorrect guesses.",
                }
            ],
            "selected_record_id": "rules-of-hangman-game",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "openai"
    assert payload["assistant_message"] == "The selected Hangman rules should stay out of this answer."
    assert payload["turn_interpretation"]["preserve_selected_record"] is False
    assert any(item["id"] == "shared-workspace" for item in payload["working_memory"])
    assert any(item["id"] == "persistent-memory" for item in payload["working_memory"])
    assert all(item["id"] != "rules-of-hangman-game" for item in payload["working_memory"])


def test_off_topic_selected_scenario_comparison_does_not_anchor_short_turn(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    (repo_root / "artifacts" / "launch-comparison.md").write_text(
        (
            "---\n"
            "id: launch-comparison\n"
            "title: Launch Strategy Comparison\n"
            "type: scenario_comparison\n"
            "card: Comparison artifact for launch strategy branches.\n"
            "created_at: 2026-04-13\n"
            "updated_at: 2026-04-13\n"
            "links_to: []\n"
            "comes_from: []\n"
            "status: active\n"
            "---\n\n"
            "Baseline versus constrained versus aggressive launch options.\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.88,
            reason="No explicit continuation signal for the selected scenario comparison.",
            preserve_selected_record=None,
        ),
    )

    monkeypatch.setattr(
        "vantage_v5.services.search.ConceptSearchService.search_context",
        lambda self, **kwargs: [
            CandidateMemory(
                id="email-drafting",
                title="Email Drafting",
                type="concept",
                card="Draft and refine short emails.",
                score=9.0,
                reason="The user is asking for a new email draft.",
                source="concept",
                trust="high",
            )
        ],
    )
    monkeypatch.setattr(
        "vantage_v5.services.vetting.ConceptVettingService.vet",
        lambda self, *, message, candidates, continuity_hint=None, visible_artifacts=None: (
            candidates[:1],
            {
                "selected_ids": [candidate.id for candidate in candidates[:1]],
                "none_relevant": False,
                "rationale": "Selected the email drafting concept without preserving the scenario comparison.",
            },
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "This short draft request should not revive the selected scenario comparison."
            if kwargs["selected_memory"] is None and all(item.id != "launch-comparison" for item in kwargs["vetted_memory"])
            else (_ for _ in ()).throw(AssertionError("Selected scenario comparison leaked into the short off-topic turn."))
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(action="no_op", rationale="Short off-topic turns should not revive a selected scenario comparison."),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "draft an email",
            "history": [
                {
                    "user_message": "Compare three launch approaches for our new software product.",
                    "assistant_message": "I created 3 scenario branches and a comparison artifact.",
                }
            ],
            "selected_record_id": "launch-comparison",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "openai"
    assert payload["assistant_message"] == "This short draft request should not revive the selected scenario comparison."
    assert payload["turn_interpretation"]["preserve_selected_record"] is None
    recalled_ids = {item["id"] for item in payload["working_memory"]}
    assert "launch-comparison" not in recalled_ids
    assert "email-drafting-protocol" in recalled_ids


def test_pending_whiteboard_draft_blocks_implicit_durable_write(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I staged the outline as a pending whiteboard draft.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Launch Outline\n\n"
            "## Goal\n"
            "- Ship a clearer first milestone.\n"
        ),
    )
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService._openai_decide",
        lambda self, **kwargs: MetaDecision(
            action="create_memory",
            rationale="This would have become memory without the whiteboard safety guard.",
            title="Blocked Memory",
            card="Blocked Memory.",
            body="Should not be written.",
            links_to=[],
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft a launch outline for me.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "draft",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["decision"] is None
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert payload["meta_action"]["action"] == "no_op"
    assert "does not make that draft durable" in payload["meta_action"]["rationale"].lower()
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    memory_ids = {path.stem for path in (repo_root / "memories").glob("*.md")}
    assert "blocked-memory" not in memory_ids


def test_pending_whiteboard_draft_blocks_explicit_remember_write(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr(
        "vantage_v5.services.chat.ChatService._openai_reply",
        lambda self, **kwargs: (
            "CHAT_RESPONSE: I staged the outline as a pending whiteboard draft.\n\n"
            "WHITEBOARD_DRAFT:\n"
            "# Launch Outline\n\n"
            "## Goal\n"
            "- Ship a clearer first milestone.\n"
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "message": "Draft a launch outline for me and remember it.",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "whiteboard_mode": "draft",
            "memory_intent": "remember",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_update"]["type"] == "draft_whiteboard"
    assert payload["workspace_update"]["decision"] is None
    assert payload["workspace_update"]["proposal_kind"] == "draft"
    assert payload["meta_action"]["action"] == "no_op"
    assert "does not make that draft durable" in payload["meta_action"]["rationale"].lower()
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    memory_ids = {path.stem for path in (repo_root / "memories").glob("*.md")}
    assert "draft-a-launch-outline-for-me-and-remember-it" not in memory_ids


def test_unexpected_chat_failures_return_500(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path)

    def _boom(*args, **kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("vantage_v5.server.ChatService.reply", _boom)

    response = client.post(
        "/api/chat",
        json={
            "message": "Please fail unexpectedly.",
            "history": [],
        },
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Chat request failed unexpectedly."


def test_chat_trace_files_do_not_overwrite_same_second_turns(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)

    monkeypatch.setattr("vantage_v5.services.chat.datetime", _FixedDatetime)

    first = client.post(
        "/api/chat",
        json={
            "message": "First trace turn.",
            "history": [],
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/chat",
        json={
            "message": "Second trace turn.",
            "history": [],
        },
    )
    assert second.status_code == 200

    trace_paths = {path.name for path in (repo_root / "traces").glob("chat-turn-*.json")}
    assert trace_paths == {
        "chat-turn-20260413T120000Z.json",
        "chat-turn-20260413T120000Z-2.json",
    }


def test_final_response_trace_caps_request_history(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"Earlier turn {index}"}
        for index in range(10)
    ]

    response = client.post(
        "/api/chat",
        json={
            "message": "Keep the trace history bounded.",
            "history": history,
        },
    )

    assert response.status_code == 200
    final_response = _latest_trace_payload(repo_root)["final_response"]
    assert final_response["request"]["message"] == "Keep the trace history bounded."
    assert final_response["request"]["history"] == history[-6:]
    assert final_response["turn_plan"]["request"]["message"] == "Keep the trace history bounded."
    assert final_response["turn_plan"]["request"]["history_count"] == 6


def test_transient_workspace_buffer_is_redacted_in_trace(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path)

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 4, 13, 12, 0, 1, tzinfo=UTC)

    monkeypatch.setattr("vantage_v5.services.chat.datetime", _FixedDatetime)

    response = client.post(
        "/api/chat",
        json={
            "message": "What do you think of the current whiteboard?",
            "history": [],
            "workspace_id": "v5-milestone-1",
            "workspace_scope": "visible",
            "workspace_content": "# Unsaved Draft\n\nThis text should stay transient.",
        },
    )
    assert response.status_code == 200

    trace_path = repo_root / "traces" / "chat-turn-20260413T120001Z.json"
    assert trace_path.exists()
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["workspace_is_transient"] is True
    assert trace_payload["workspace_excerpt"] is None
    assert trace_payload["turn"]["workspace"]["content"] is None
    final_response = trace_payload["final_response"]
    assert final_response["request"]["message"] == "What do you think of the current whiteboard?"
    assert final_response["request"]["workspace_content_supplied"] is True
    assert final_response["workspace_update"] is None
    assert final_response["graph_action"] is None
    assert final_response["created_record"] is None
    assert final_response["artifact_actions"] == []
    assert final_response["turn_plan"]["request"]["workspace_content_supplied"] is True


def test_experiment_mode_keeps_temporary_memory_isolated(tmp_path: Path) -> None:
    client, repo_root = _client(tmp_path)

    started = client.post("/api/experiment/start", json={"seed_from_workspace": False})
    assert started.status_code == 200
    start_payload = started.json()
    assert start_payload["experiment"]["active"] is True
    session_id = start_payload["experiment"]["session_id"]
    session_root = repo_root / "state" / "experiments" / session_id
    assert session_root.exists()
    assert start_payload["workspace"]["scope"] == "experiment"

    chat = client.post(
        "/api/chat",
        json={
            "message": "Please remember this temporary experiment lesson for the current experiment.",
            "history": [],
            "memory_intent": "remember",
        },
    )
    assert chat.status_code == 200
    chat_payload = chat.json()
    assert chat_payload["experiment"]["active"] is True
    assert chat_payload["meta_action"]["action"] == "create_memory"
    record_id = chat_payload["created_record"]["id"]
    assert chat_payload["created_record"]["scope"] == "experiment"
    assert chat_payload["created_record"]["source"] == "memory"
    assert chat_payload["created_record"]["durability"] == "temporary"
    assert chat_payload["created_record"]["why_learned"] == "Saved as memory because the user asked Vantage to remember it."
    assert chat_payload["created_record"]["correction_affordance"]["kind"] == "open_in_whiteboard"
    assert chat_payload["created_record"]["write_review"]["scope"] == "experiment"
    assert chat_payload["created_record"]["write_review"]["durability"] == "temporary"
    assert chat_payload["created_record"]["write_review"]["record"]["kind"] == "saved_note"
    assert (session_root / "memories" / f"{record_id}.md").exists()
    assert not (repo_root / "memories" / f"{record_id}.md").exists()

    memory = client.get("/api/memory")
    assert memory.status_code == 200
    assert any(item.get("scope") == "experiment" for item in memory.json()["saved_notes"])

    ended = client.post("/api/experiment/end")
    assert ended.status_code == 200
    assert ended.json()["ended"] is True
    assert not session_root.exists()

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["experiment"]["active"] is False

    memory_after = client.get("/api/memory")
    assert memory_after.status_code == 200
    assert all(item.get("scope") != "experiment" for item in memory_after.json()["saved_notes"])


def test_experiment_mode_keeps_scenario_outputs_isolated(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")

    started = client.post("/api/experiment/start", json={"seed_from_workspace": False})
    assert started.status_code == 200
    session_id = started.json()["experiment"]["session_id"]
    session_root = repo_root / "state" / "experiments" / session_id

    monkeypatch.setattr("vantage_v5.server.NavigatorService.route_turn", lambda self, **kwargs: _scenario_navigation())
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)
    monkeypatch.setattr("vantage_v5.services.scenario_lab.ScenarioLabService._openai_build_scenario", lambda self, **kwargs: _scenario_plan())

    response = client.post(
        "/api/chat",
        json={
            "message": "What if we cut milestone 1 scope by 40%?",
            "history": [],
            "workspace_id": "experiment-workspace",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "scenario_lab"
    assert payload["experiment"]["active"] is True
    assert payload["created_record"]["scope"] == "experiment"
    assert payload["created_record"]["durability"] == "temporary"
    assert payload["created_record"]["why_learned"] == "Saved as a Scenario Lab comparison hub so the branch comparison can be revisited."
    assert payload["created_record"]["correction_affordance"]["kind"] == "open_in_whiteboard"
    assert payload["created_record"]["write_review"]["write_reason"] == (
        "Saved as a Scenario Lab comparison hub so the branch comparison can be revisited."
    )
    assert payload["created_record"]["write_review"]["record"]["source"] == "artifact"
    assert payload["created_record"]["write_review"]["direct_mutation_supported"] is False

    artifact_id = payload["created_record"]["id"]
    assert (session_root / "artifacts" / f"{artifact_id}.md").exists()
    assert not (repo_root / "artifacts" / f"{artifact_id}.md").exists()

    for branch in payload["scenario_lab"]["branches"]:
        branch_id = branch["workspace_id"]
        assert (session_root / "workspaces" / f"{branch_id}.md").exists()
        assert not (repo_root / "workspaces" / f"{branch_id}.md").exists()
