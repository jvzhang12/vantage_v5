from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import shutil

from fastapi.testclient import TestClient

from vantage_v5.config import AppConfig
from vantage_v5.services.meta import MetaDecision
from vantage_v5.services.meta import MetaService
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.scenario_lab import ScenarioBranchPlan
from vantage_v5.services.scenario_lab import ScenarioComparisonPlan
from vantage_v5.services.scenario_lab import ScenarioPlan
from vantage_v5.services.search import CandidateMemory
from vantage_v5.server import create_app
from vantage_v5.storage.workspaces import WorkspaceDocument


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _test_repo(tmp_path: Path) -> Path:
    source = _repo_root()
    repo_root = tmp_path / "vantage-v5"
    repo_root.mkdir()
    for folder in ["concepts", "memories", "memory_trace", "artifacts", "workspaces", "fixtures"]:
        shutil.copytree(source / folder, repo_root / folder)
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


def _client(tmp_path: Path, *, openai_api_key: str | None = None) -> tuple[TestClient, Path]:
    repo_root = _test_repo(tmp_path)
    app = create_app(
        AppConfig(
            repo_root=repo_root,
            openai_api_key=openai_api_key,
            model="gpt-4.1",
            port=8005,
            active_workspace="v5-milestone-1",
            nexus_root=repo_root / "fixtures" / "nexus",
            nexus_include_paths=["allowed"],
            nexus_exclude_paths=["private"],
        )
    )
    return TestClient(app), repo_root


def _fallback_vet_for_tests(self, *, message, candidates, continuity_hint=None):
    vetted = candidates[:4]
    return vetted, {
        "selected_ids": [candidate.id for candidate in vetted],
        "none_relevant": not bool(vetted),
        "rationale": "Test vetting path selected the highest-ranked candidates.",
    }


def _no_relevant_matches_for_tests(self, *, message, candidates, continuity_hint=None):
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


def test_chat_search_and_concept_inspection(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

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
    assert payload["selected_record"] is None
    assert payload["selected_record_id"] is None
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "auto"
    assert payload["workspace"]["context_scope"] == "excluded"
    assert "vetting" in payload
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["graph_action"] is None
    ids = {concept["id"] for concept in payload["concept_cards"]}
    assert {"shared-workspace", "persistent-memory"} & ids
    assert any(note["source"] == "vault_note" for note in payload["vault_notes"])
    assert any(item["source"] == "concept" for item in payload["working_memory"])

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
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["graph_action"] is None
    assert payload["created_record"]["source"] == "artifact"
    assert payload["created_record"]["type"] == "scenario_comparison"
    assert payload["created_record"]["scenario_kind"] == "comparison"
    assert payload["created_record"]["scope"] == "durable"
    assert payload["learned"] == [payload["created_record"]]
    assert payload["selected_record"] is None
    assert payload["selected_record_id"] is None
    assert payload["scenario_lab"]["comparison_artifact"]["id"] == payload["created_record"]["id"]
    assert payload["scenario_lab"]["comparison_artifact"]["scenario_kind"] == "comparison"
    assert payload["scenario_lab"]["comparison_question"] == "What if we cut milestone 1 scope by 40%?"
    assert len(payload["scenario_lab"]["branches"]) == 3
    assert any(item["source"] == "concept" for item in payload["concept_cards"])

    artifact_id = payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{artifact_id}.md").exists()

    branch_ids = [branch["workspace_id"] for branch in payload["scenario_lab"]["branches"]]
    assert branch_ids == [
        "v5-milestone-1--baseline",
        "v5-milestone-1--reduced-scope",
        "v5-milestone-1--fast-launch",
    ]
    assert payload["created_record"]["base_workspace_id"] == "v5-milestone-1"
    assert payload["created_record"]["branch_workspace_ids"] == branch_ids
    assert payload["created_record"]["scenario_namespace_id"] == "v5-milestone-1"
    assert payload["created_record"]["namespace_mode"] == "anchored"
    assert payload["scenario_lab"]["comparison_artifact"]["branch_workspace_ids"] == branch_ids
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
    assert payload["response_mode"]["note"] == "No grounded context supported this answer."
    assert payload["assistant_message"].startswith("This is new to me, but my best guess is:")


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
    assert "model provider was unavailable for this turn" in payload["assistant_message"]


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
    assert payload["scenario_lab"]["error"]["message"] == "scenario lab boom"
    assert payload["scenario_lab_error"]["message"] == "scenario lab boom"
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
    assert branch_ids == [
        "launch-strategy--conservative-rollout",
        "launch-strategy--focused-mvp",
        "launch-strategy--aggressive-launch",
    ]
    assert payload["created_record"]["scenario_namespace_id"] == "launch-strategy"
    assert payload["created_record"]["namespace_mode"] == "detached"
    assert payload["created_record"]["branch_workspace_ids"] == branch_ids
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
        lambda self, *, message, candidates, continuity_hint=None: (
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
    assert "Relevant concepts: Rules of Hangman (game)." in follow_up_payload["assistant_message"]
    assert "rules-of-hangman-game" in follow_up_payload["vetting"]["selected_ids"]
    assert follow_up_payload["vetting"]["none_relevant"] is False
    assert follow_up_payload["response_mode"]["kind"] == "grounded"
    assert "continuity context" in follow_up_payload["vetting"]["rationale"].lower()


def test_best_guess_response_is_prefaced_when_no_working_memory(tmp_path: Path, monkeypatch) -> None:
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
    assert payload["working_memory"] == []
    assert payload["assistant_message"].startswith("This is new to me, but my best guess is:")
    assert payload["learned"] == []


def test_fallback_turn_can_create_concept_without_openai_key(tmp_path: Path, monkeypatch) -> None:
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
    assert payload["meta_action"]["action"] == "create_concept"
    assert payload["graph_action"]["type"] == "create_concept"
    assert payload["created_record"]["source"] == "concept"
    assert payload["learned"][0]["source"] == "concept"
    assert concept_path.exists()


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
    assert (repo_root / "memory_trace" / f"{payload['memory_trace_record']['id']}.md").exists()


def test_fallback_turn_creates_linked_concept_when_topic_is_related_but_not_duplicate(tmp_path: Path, monkeypatch) -> None:
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

    def _vet(self, *, message, candidates, continuity_hint=None):
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
    assert payload["meta_action"]["action"] == "create_concept"
    assert payload["graph_action"]["type"] == "create_concept"
    assert payload["created_record"]["source"] == "concept"
    assert payload["created_record"]["links_to"] == [matching_concept.id]
    assert payload["learned"] == [payload["created_record"]]
    assert payload["vetting"]["selected_ids"] == [matching_concept.id]
    assert concept_path.exists()


def test_fallback_turn_links_only_related_concepts(tmp_path: Path, monkeypatch) -> None:
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

    def _vet(self, *, message, candidates, continuity_hint=None):
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
    assert payload["meta_action"]["action"] == "create_concept"
    assert payload["created_record"]["links_to"] == [related_concept.id]


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
    assert "pending_whiteboard" in payload["response_mode"]["context_sources"]
    assert payload["graph_action"]["type"] == "save_workspace_iteration_artifact"
    assert payload["created_record"]["source"] == "artifact"
    assert payload["workspace_update"]["artifact_snapshot_id"] == payload["created_record"]["id"]
    assert (repo_root / "artifacts" / f"{payload['created_record']['id']}.md").exists()
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
    assert (repo_root / "memories" / f"{payload['created_record']['id']}.md").exists()


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
        selected_record = kwargs["selected_record"]
        assert selected_record is not None
        assert selected_record["id"] == promoted_artifact["id"]
        assert selected_record["source"] == "artifact"
        return NavigationDecision(
            mode="chat",
            confidence=0.96,
            reason="The user is following up on the promoted artifact.",
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
            "selected_record_id": promoted_artifact["id"],
        },
    )
    assert follow_up.status_code == 200
    payload = follow_up.json()
    assert payload["mode"] == "fallback"
    assert payload["selected_record_id"] == promoted_artifact["id"]
    assert payload["selected_record"]["id"] == promoted_artifact["id"]
    assert payload["selected_record"]["source"] == "artifact"
    assert any(item["id"] == promoted_artifact["id"] for item in payload["working_memory"])
    assert payload["turn_interpretation"]["preserve_selected_record"] is True
    assert payload["turn_interpretation"]["selected_record_reason"] == "The promoted artifact stays in focus for the follow-up."
    assert len(payload["working_memory"]) <= 5
    assert payload["response_mode"]["kind"] == "grounded"


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
    assert payload["assistant_message"].endswith("I answered without pulling in the hidden whiteboard.")
    assert payload["assistant_message"].startswith("This is new to me, but my best guess is:")
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
    assert payload["assistant_message"].endswith("I answered without using the hidden live whiteboard buffer.")
    assert payload["assistant_message"].startswith("This is new to me, but my best guess is:")
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
    assert opened_payload["graph_action"]["record_id"] == "user-prefers-chat-first-ux"
    assert opened_payload["graph_action"]["concept_id"] == "user-prefers-chat-first-ux"
    assert opened_payload["graph_action"]["source"] == "memory"


def test_draft_request_does_not_auto_write_memory(tmp_path: Path) -> None:
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
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    artifact_ids = {path.stem for path in (repo_root / "artifacts").glob("*.md")}
    assert "help-me-draft-an-essay-about-preparing-a-thanksgiving-dinner" not in artifact_ids


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
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_navigation_can_drive_auto_whiteboard_offer(tmp_path: Path, monkeypatch) -> None:
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
        assert kwargs["whiteboard_mode"] == "offer"
        return (
            "CHAT_RESPONSE: This is a concrete draft. Want me to open the whiteboard so we can write the email there?\n\n"
            "WHITEBOARD_OFFER: Whiteboard ready for collaboratively drafting the email."
        )

    monkeypatch.setattr("vantage_v5.services.chat.ChatService._openai_reply", _reply)
    monkeypatch.setattr(
        "vantage_v5.services.meta.MetaService.decide",
        lambda self, **kwargs: MetaDecision(
            action="no_op",
            rationale="The interpreter routed this turn into a non-durable whiteboard invitation.",
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
    assert payload["assistant_message"] == "This is a concrete draft. Want me to open the whiteboard so we can write the email there?"
    assert payload["workspace_update"]["type"] == "offer_whiteboard"
    assert payload["workspace_update"]["proposal_kind"] == "offer"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] == "offer"
    assert payload["turn_interpretation"]["whiteboard_mode_source"] == "interpreter"
    assert payload["graph_action"] is None
    assert payload["created_record"] is None
    assert (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8") == original_workspace


def test_explicit_whiteboard_request_bypasses_offer_step(tmp_path: Path, monkeypatch) -> None:
    client, repo_root = _client(tmp_path, openai_api_key="test-key")
    original_workspace = (repo_root / "workspaces" / "v5-milestone-1.md").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "vantage_v5.server.NavigatorService.route_turn",
        lambda self, **kwargs: NavigationDecision(
            mode="chat",
            confidence=0.89,
            reason="The turn is a concrete draft request that would normally invite whiteboard collaboration first.",
            whiteboard_mode="offer",
        ),
    )
    monkeypatch.setattr("vantage_v5.services.vetting.ConceptVettingService.vet", _fallback_vet_for_tests)

    def _reply(self, **kwargs):
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
    assert payload["assistant_message"].endswith("I answered in chat without reusing the stale whiteboard offer.")
    assert payload["assistant_message"].startswith("This is new to me, but my best guess is:")
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
    assert payload["workspace_update"] is None
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["grounding_sources"] == ["recall", "whiteboard"]
    assert payload["response_mode"]["context_sources"] == ["recall", "whiteboard"]
    assert payload["response_mode"]["legacy_context_sources"] == ["working_memory", "whiteboard"]
    assert payload["response_mode"]["label"] == "Recall + Whiteboard"
    assert workspace_path.read_text(encoding="utf-8") == original_workspace


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
    assert any(item["id"] == "rules-of-hangman-game" and item["reason"] == selected_record_reason for item in payload["working_memory"])
    assert payload["response_mode"]["kind"] == "grounded"
    assert payload["turn_interpretation"]["mode"] == "chat"
    assert payload["turn_interpretation"]["preserve_selected_record"] is True
    assert payload["turn_interpretation"]["selected_record_reason"] == selected_record_reason
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

    def _vet(self, *, message, candidates, continuity_hint=None):
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
        lambda self, *, message, candidates, continuity_hint=None: (
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
        lambda self, *, message, candidates, continuity_hint=None: (
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
    assert payload["working_memory"] == [
        {
            "id": "email-drafting",
            "title": "Email Drafting",
            "type": "concept",
            "card": "Draft and refine short emails.",
            "score": 9.0,
            "reason": "The user is asking for a new email draft.",
            "source": "concept",
            "source_label": "Concept KB",
            "trust": "high",
            "body": "",
            "path": None,
        }
    ]


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

    artifact_id = payload["created_record"]["id"]
    assert (session_root / "artifacts" / f"{artifact_id}.md").exists()
    assert not (repo_root / "artifacts" / f"{artifact_id}.md").exists()

    for branch in payload["scenario_lab"]["branches"]:
        branch_id = branch["workspace_id"]
        assert (session_root / "workspaces" / f"{branch_id}.md").exists()
        assert not (repo_root / "workspaces" / f"{branch_id}.md").exists()
