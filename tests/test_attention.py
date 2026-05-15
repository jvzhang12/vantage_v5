from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from vantage_v5.services.attention import AttentionEngine
from vantage_v5.services.attention import apply_attention_surface_selection
from vantage_v5.services.attention import build_query_frame
from vantage_v5.services.attention import NavigatorSelection
from vantage_v5.services.attention import normalize_navigator_selection
from vantage_v5.services.attention import SelectedAttentionResource
from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.tasks import LocalTaskProvider
from vantage_v5.services.vector_index import SQLiteVectorIndex
from vantage_v5.services.vector_index import VectorDocument
from vantage_v5.services.vector_index import VectorHit
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.workspaces import WorkspaceStore


def test_query_frame_parses_temporal_worked_on_reference() -> None:
    frame = build_query_frame(
        "Let's go back to the draft we were working on last Tuesday.",
        today=date(2026, 5, 14),
    )

    assert "reopen" in frame.operations
    assert "whiteboard" in frame.domains
    assert frame.temporal_references[0].raw_text == "last Tuesday"
    assert frame.temporal_references[0].relation == "worked_on"
    assert frame.temporal_references[0].start == date(2026, 5, 12)


def test_query_frame_interprets_my_day_as_today_calendar_and_tasks() -> None:
    frame = build_query_frame(
        "What does my day look like?",
        today=date(2026, 5, 14),
    )

    assert frame.domains == ("calendar", "tasks")
    assert "calendar_day" in frame.artifact_kinds
    assert "task_focus" in frame.artifact_kinds
    assert frame.temporal_references[0].raw_text == "today"
    assert frame.temporal_references[0].relation == "scheduled"
    assert "what" not in frame.tokens
    assert frame.entities == ()


def test_attention_ranks_temporal_artifact_for_last_tuesday(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    artifact = runtime["artifact_store"].create_artifact(
        title="Tuesday Email Draft",
        card="Draft we worked on for Morgan.",
        body="# Tuesday Email Draft\n\nA private beta email draft.",
        metadata={"last_edited_at": "2026-05-12"},
    )
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="Let's go back to the draft we were working on last Tuesday.",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    candidate = next(item for item in turn.candidates if item.resource_id == f"artifact:{artifact.id}")
    assert "worked_on:last Tuesday" in candidate.temporal_matches
    selection, selected = turn.select(
        {
            "selected_ids": [candidate.resource_id],
            "primary_resource_id": candidate.resource_id,
            "surface_to_open": "whiteboard",
            "reason": "The user asked to reopen the Tuesday draft.",
            "confidence": 0.9,
        }
    )
    assert selection.surface_to_open == "whiteboard"
    assert selected[0].title == "Tuesday Email Draft"


def test_attention_hybrid_ranking_uses_semantic_vector_similarity(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    artifact = runtime["artifact_store"].create_artifact(
        title="Grocery Run",
        card="Take the car to the store before lunch.",
        body="# Grocery Run\n\nTake the car to the store before lunch.",
    )
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="Find the automobile errand note.",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    candidate = next(item for item in turn.candidates if item.resource_id == f"artifact:{artifact.id}")
    assert candidate.retrieval_scores["vector_similarity"] > 0
    assert candidate.retrieval_scores["vector_bonus"] > 0
    assert "semantic_vector" in candidate.matched_keys
    assert "semantic vector similarity" in candidate.why_candidate
    assert candidate.to_dict()["retrieval_scores"]["hybrid"] == candidate.score


def test_attention_payloads_expose_record_scope_and_selected_provenance(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    canonical_root = tmp_path / "canonical"
    canonical_store = ConceptStore(canonical_root / "concepts")
    canonical = canonical_store.create_concept(
        title="Canonical Scope Marker",
        card="Canonical concept for attention provenance.",
        body="Canonical attention provenance marker.",
    )
    runtime["reference_concept_store"] = canonical_store
    runtime["canonical_root"] = canonical_root
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="Find the canonical attention provenance marker.",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    candidate = next(item for item in turn.candidates if item.resource_id == f"concept:{canonical.id}")
    candidate_payload = candidate.to_dict()
    assert candidate_payload["scope"] == "canonical"
    assert candidate_payload["durability"] == "durable"
    assert candidate_payload["is_canonical"] is True

    _selection, selected = turn.select(
        {
            "selected_ids": [candidate.resource_id],
            "primary_resource_id": candidate.resource_id,
            "reason": "Use the canonical concept.",
            "confidence": 0.9,
        }
    )
    selected_payload = selected[0].to_dict()
    assert selected_payload["scope"] == "canonical"
    assert selected_payload["durability"] == "durable"
    assert selected_payload["is_canonical"] is True
    assert selected_payload["source_status"]["store"] == "reference_concept_store"


def test_attention_retrieval_prefers_saved_artifact_over_unrequested_memory_trace(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    artifact = runtime["artifact_store"].create_artifact(
        title="Midterm Study Plan",
        card="Graph algorithms, runtime analysis, and study priorities.",
        body="# Midterm Study Plan\n\nPractice BFS, DFS, edge cases, and runtime analysis.",
    )
    runtime["memory_trace_store"].create_turn_trace(
        user_message="Can you find my exam preparation material about graphs and study priorities?",
        assistant_message="A prior answer that mentioned the midterm study plan.",
        working_memory=[],
        history=[],
        workspace_id=workspace.workspace_id,
        workspace_title=workspace.title,
        workspace_content=workspace.content,
        workspace_scope="included",
        learned=[],
        response_mode={"kind": "grounded"},
        scope="durable",
    )
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="Can you find my exam preparation material about graphs and study priorities?",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )
    selection = normalize_navigator_selection(None, candidates=turn.candidates)

    assert turn.candidates[0].resource_id == f"artifact:{artifact.id}"
    assert selection.primary_resource_id == f"artifact:{artifact.id}"
    trace_candidate = next(item for item in turn.candidates if item.source == "memory_trace")
    assert trace_candidate.retrieval_scores["trace_scope_penalty"] < 0


def test_sqlite_vector_index_persists_and_queries_semantic_hits(tmp_path: Path) -> None:
    index_path = tmp_path / "state" / "vector_index.sqlite3"
    index = SQLiteVectorIndex(index_path)
    index.sync([
        VectorDocument(
            resource_id="artifact:grocery-run",
            kind="artifact",
            app="whiteboard",
            title="Grocery Run",
            summary="Take the car to the store before lunch.",
            source="artifact",
            text="# Grocery Run\n\nTake the car to the store before lunch.",
            metadata={"source": "test"},
        )
    ])

    hits = index.query("Find the automobile errand note.", limit=3)

    assert index_path.exists()
    assert hits[0].resource_id == "artifact:grocery-run"
    assert hits[0].similarity > 0
    assert hits[0].backend == "sqlite-vector-json-v1"


def test_attention_uses_pluggable_vector_index_hits(tmp_path: Path) -> None:
    class FakeVectorIndex:
        synced: list[VectorDocument]

        def sync(self, documents: list[VectorDocument]) -> None:
            self.synced = documents

        def query(self, text: str, *, limit: int = 16) -> list[VectorHit]:
            return [
                VectorHit(
                    resource_id="artifact:quiet-match",
                    similarity=0.91,
                    backend="fake-vector-index",
                    embedding_model="fake",
                )
            ]

    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    artifact = runtime["artifact_store"].create_artifact(
        title="Quiet Match",
        card="A resource with no useful lexical overlap.",
        body="# Quiet Match\n\nA resource with no useful lexical overlap.",
    )
    fake_index = FakeVectorIndex()
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        vector_index=fake_index,
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="A completely different query.",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    candidate = next(item for item in turn.candidates if item.resource_id == f"artifact:{artifact.id}")
    assert any(document.resource_id == f"artifact:{artifact.id}" for document in fake_index.synced)
    assert candidate.retrieval_scores["indexed_vector_similarity"] == 0.91
    assert candidate.retrieval_scores["vector_bonus"] > 0


def test_attention_prefers_visible_artifact_as_current_view(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="What should I move next?",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[
            {
                "id": "calendar-week-2026-05-11",
                "kind": "calendar_week",
                "title": "Current Week",
                "summary": "Algorithms lab is visible.",
                "content": "# Calendar Week\n- Algorithms lab",
                "data": {"calendar_week": {"start_date": "2026-05-11"}},
            }
        ],
    )

    assert turn.candidates[0].source == "visible_artifact"
    assert turn.candidates[0].suggested_surface == "calendar_week"


def test_attention_indexes_calendar_and_tasks_for_operational_requests(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    events_path = tmp_path / "state" / "calendar" / "events.json"
    events_path.parent.mkdir(parents=True)
    events_path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "midterm",
                        "title": "Data Structures Midterm",
                        "start": "2026-05-14T10:00:00",
                        "end": "2026-05-14T11:30:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    tasks_path = tmp_path / "state" / "tasks" / "tasks.json"
    tasks_path.parent.mkdir(parents=True)
    tasks_path.write_text(json.dumps({"tasks": [{"id": "hw2", "title": "Finish homework 2", "due_date": "2026-05-14"}]}), encoding="utf-8")
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=events_path),
        task_provider=LocalTaskProvider(tasks_path=tasks_path),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="What does my calendar and homework look like today?",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    kinds = {candidate.kind for candidate in turn.candidates}
    assert "calendar_day" in kinds
    assert "task_focus" in kinds


def test_attention_my_day_fallback_prefers_operational_resources_over_old_traces(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    runtime["memory_trace_store"].create_turn_trace(
        user_message="What does my day look like?",
        assistant_message="A prior answer that should not beat live calendar context.",
        working_memory=[],
        history=[],
        workspace_id=workspace.workspace_id,
        workspace_title=workspace.title,
        workspace_content=workspace.content,
        workspace_scope="included",
        learned=[],
        response_mode={"kind": "grounded"},
        scope="durable",
    )
    events_path = tmp_path / "state" / "calendar" / "events.json"
    events_path.parent.mkdir(parents=True)
    events_path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "demo-checkin",
                        "title": "Demo check-in",
                        "start": "2026-05-14T11:00:00",
                        "end": "2026-05-14T11:30:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    tasks_path = tmp_path / "state" / "tasks" / "tasks.json"
    tasks_path.parent.mkdir(parents=True)
    tasks_path.write_text(json.dumps({"tasks": [{"id": "hw2", "title": "Finish homework 2", "due_date": "2026-05-14"}]}), encoding="utf-8")
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=events_path),
        task_provider=LocalTaskProvider(tasks_path=tasks_path),
        today=date(2026, 5, 14),
    )

    turn = engine.prepare_turn(
        message="What does my day look like?",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    selection = normalize_navigator_selection(None, candidates=turn.candidates)
    assert selection.surface_to_open in {"calendar_day", "task_focus"}
    assert selection.primary_resource_id in {"calendar_day:2026-05-14", "task_focus:2026-05-14"}
    assert not str(selection.primary_resource_id or "").startswith("memory_trace:")


def test_navigator_selection_falls_back_to_ranked_candidates(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    workspace = runtime["workspace_store"].save("working-draft", "# Working Draft\n\nCurrent scratchpad.")
    engine = AttentionEngine(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
        today=date(2026, 5, 14),
    )
    turn = engine.prepare_turn(
        message="Show my calendar today.",
        runtime=runtime,
        workspace=workspace,
        visible_artifacts=[],
    )

    selection = normalize_navigator_selection(None, candidates=turn.candidates)
    assert selection.fallback is True
    assert selection.selected_ids
    assert selection.surface_to_open == "calendar_day"
    payload = apply_attention_surface_selection({"primary_surface": "chat", "surfaces": []}, selection)
    assert payload["primary_surface"] == "calendar_day"


def test_attention_surface_selection_overrides_legacy_surface_choice() -> None:
    selection = NavigatorSelection(
        selected_ids=("task_focus:2026-05-14",),
        primary_resource_id="task_focus:2026-05-14",
        supporting_resource_ids=(),
        rejected_candidate_ids=("calendar_day:2026-05-14",),
        surface_to_open="task_focus",
        reason="Navigator selected the task focus as the relevant working surface.",
        confidence=0.87,
    )
    selected = (
        SelectedAttentionResource(
            id="selected-task_focus:2026-05-14",
            resource_id="task_focus:2026-05-14",
            kind="task_focus",
            app="tasks",
            title="Task focus 2026-05-14",
            summary="Task focus for 2026-05-14.",
            source="tasks",
            scope="operational",
            durability="live",
            is_canonical=False,
            content="# Tasks",
            data={"date": "2026-05-14"},
            source_status={"read_only": False, "writable": True},
            timestamps={"due_at": "2026-05-14"},
            suggested_surface="task_focus",
            why_selected="Navigator selected the task focus as the relevant working surface.",
        ),
    )

    payload = apply_attention_surface_selection(
        {
            "intent": "schedule_planning",
            "primary_surface": "calendar_day",
            "supporting_surfaces": ["task_focus", "whiteboard"],
            "write_behavior": "proposal_only",
            "surfaces": [{"kind": "calendar_day", "role": "primary", "status": "summoned"}],
        },
        selection,
        selected_resources=selected,
    )

    assert payload["primary_surface"] == "task_focus"
    assert payload["intent"] == "attention_selected_context"
    assert payload["supporting_surfaces"] == []
    assert payload["selection_authority"] == "attention_navigator"
    assert payload["surfaces"][0]["status"] == "selected"


def test_attention_surface_selection_respects_hard_chat_guard() -> None:
    selection = NavigatorSelection(
        selected_ids=("calendar_day:2026-05-14",),
        primary_resource_id="calendar_day:2026-05-14",
        supporting_resource_ids=(),
        rejected_candidate_ids=(),
        surface_to_open="calendar_day",
        reason="Calendar was relevant, but the user asked for chat only.",
        confidence=0.87,
    )

    payload = apply_attention_surface_selection(
        {
            "intent": "chat_only",
            "primary_surface": "chat",
            "supporting_surfaces": [],
            "write_behavior": "none",
        },
        selection,
    )

    assert payload["primary_surface"] == "chat"
    assert payload["intent"] == "chat_only"
    assert "selection_authority" not in payload


def _runtime(root: Path) -> dict:
    return {
        "workspace_store": WorkspaceStore(root / "workspaces"),
        "concept_store": ConceptStore(root / "concepts"),
        "reference_concept_store": None,
        "memory_store": MemoryStore(root / "memories"),
        "reference_memory_store": None,
        "artifact_store": ArtifactStore(root / "artifacts"),
        "reference_artifact_store": None,
        "memory_trace_store": MemoryTraceStore(root / "memory_trace"),
    }
