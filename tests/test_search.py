from __future__ import annotations

from pathlib import Path

from vantage_v5.services.search import CandidateMemory
from vantage_v5.services.search import ConceptSearchService
from vantage_v5.services.search import _shape_merged_candidates
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.vault import VaultNoteStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_note(root: Path, relative_path: str, *, title: str, tags: list[str], body: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    tags_block = "\n".join(f"  - {tag}" for tag in tags)
    path.write_text(
        (
            "---\n"
            f"title: {title}\n"
            "tags:\n"
            f"{tags_block}\n"
            "---\n\n"
            f"# {title}\n\n"
            f"{body.strip()}\n"
        ),
        encoding="utf-8",
    )


def test_search_prefers_matching_concepts() -> None:
    repo_root = _repo_root()
    store = ConceptStore(repo_root / "concepts")
    concepts = store.list_concepts()

    service = ConceptSearchService()
    candidates = service.search(
        query="shared workspace and persistent memory",
        concepts=concepts,
        limit=10,
    )

    ids = [candidate.id for candidate in candidates]
    assert "shared-workspace" in ids
    assert "persistent-memory" in ids
    assert candidates[0].score >= candidates[-1].score


def test_memory_search_can_merge_vault_notes() -> None:
    repo_root = _repo_root()
    memory_store = MemoryStore(repo_root / "memories")
    artifact_store = ArtifactStore(repo_root / "artifacts")
    vault_store = VaultNoteStore(
        vault_root=repo_root / "fixtures" / "nexus",
        include_paths=["allowed"],
        exclude_paths=["private"],
    )

    service = ConceptSearchService()
    candidates = service.search_memory(
        query="searchable library and durable memory",
        saved_note_records=memory_store.list_memories() + artifact_store.list_artifacts(),
        vault_records=vault_store.list_notes(),
        limit=12,
    )

    assert any(candidate.source in {"memory", "artifact"} for candidate in candidates)
    assert any(candidate.source == "vault_note" for candidate in candidates)
    assert all(candidate.id for candidate in candidates)


def test_search_drops_zero_signal_records_instead_of_promoting_them_by_source_bonus(tmp_path: Path) -> None:
    concept_store = ConceptStore(tmp_path / "concepts")
    artifact_store = ArtifactStore(tmp_path / "artifacts")

    concept = concept_store.create_concept(
        title="Shared Workspace",
        card="Workspace planning concept.",
        body="Shared workspace planning guidance.",
    )
    artifact_store.create_artifact(
        title="Completely Unrelated Artifact",
        card="Nothing about the query.",
        body="Totally different material.",
    )

    service = ConceptSearchService()
    candidates = service.search_context(
        query="shared workspace",
        concept_records=[concept],
        saved_note_records=artifact_store.list_artifacts(),
        vault_records=[],
        limit=5,
    )

    assert [candidate.id for candidate in candidates] == [concept.id]


def test_memory_search_prefers_memory_over_artifact_on_tied_match_signals(tmp_path: Path) -> None:
    memory_store = MemoryStore(tmp_path / "memories")
    artifact_store = ArtifactStore(tmp_path / "artifacts")

    memory = memory_store.create_memory(
        title="Shared Workspace",
        card="Shared workspace planning note",
        body="Shared workspace planning note.",
    )
    artifact = artifact_store.create_artifact(
        title="Shared Workspace",
        card="Shared workspace planning note",
        body="Shared workspace planning note.",
    )

    service = ConceptSearchService()
    candidates = service.search_memory(
        query="shared workspace",
        saved_note_records=[memory, artifact],
        vault_records=[],
        limit=5,
    )

    assert candidates[0].id == memory.id
    assert candidates[0].source == "memory"
    assert any(candidate.source == "artifact" for candidate in candidates)


def test_search_context_can_recall_recent_memory_trace_records(tmp_path: Path) -> None:
    trace_store = MemoryTraceStore(tmp_path / "memory_trace")
    concept_store = ConceptStore(tmp_path / "concepts")

    trace_record = trace_store.create_turn_trace(
        user_message="Jordan prefers warm thank-you emails to Jerry.",
        assistant_message="I can draft a warm thank-you email to Jerry and sign it from Jordan.",
        working_memory=[],
        history=[],
        workspace_id="experiment-workspace",
        workspace_title="Experiment Workspace",
        workspace_content="",
        workspace_scope="excluded",
        learned=[],
        response_mode={"kind": "best_guess", "grounding_mode": "ungrounded", "context_sources": [], "recall_count": 0},
        scope="durable",
    )
    concept_store.create_concept(
        title="Launch Planning",
        card="Planning concept.",
        body="A concept about launch planning.",
    )

    service = ConceptSearchService()
    candidates = service.search_context(
        query="what should I remember about Jordan and Jerry emails",
        memory_trace_records=trace_store.list_recent_traces(),
        concept_records=concept_store.list_concepts(),
        saved_note_records=[],
        vault_records=[],
        limit=5,
    )

    assert candidates
    assert candidates[0].id == trace_record.id
    assert candidates[0].source == "memory_trace"


def test_search_uses_links_and_lineage_signals(tmp_path: Path) -> None:
    memory_store = MemoryStore(tmp_path / "memories")
    artifact_store = ArtifactStore(tmp_path / "artifacts")

    linked_memory = memory_store.create_memory(
        title="Follow-up Draft",
        card="Draft note",
        body="Generic follow-up draft.",
        links_to=["jerry-email"],
        comes_from=["planning-thread"],
    )
    artifact = artifact_store.create_artifact(
        title="General Draft",
        card="Draft note",
        body="Generic follow-up draft.",
    )

    service = ConceptSearchService()
    link_candidates = service.search_memory(
        query="jerry email",
        saved_note_records=[linked_memory, artifact],
        vault_records=[],
        limit=5,
    )

    assert link_candidates[0].id == linked_memory.id
    assert "links=2" in link_candidates[0].reason

    lineage_candidates = service.search_memory(
        query="planning thread",
        saved_note_records=[linked_memory, artifact],
        vault_records=[],
        limit=5,
    )

    assert lineage_candidates[0].id == linked_memory.id
    assert "lineage=0" not in lineage_candidates[0].reason


def test_search_uses_path_driven_matching(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    _write_note(
        vault_root,
        "Planning/Decision/Decision Criteria.md",
        title="Workspace Notes",
        tags=["misc"],
        body="Generic planning note without the target phrase.",
    )
    _write_note(
        vault_root,
        "Misc/General Notes.md",
        title="General Notes",
        tags=["misc"],
        body="This note is generic. It mentions decision criteria later.",
    )

    store = VaultNoteStore(vault_root=vault_root)
    service = ConceptSearchService()
    records = store.list_notes()
    record_by_id = {record.id: record for record in records}

    candidates = service.search(records=records, query="decision criteria", limit=5)

    assert record_by_id[candidates[0].id].relative_path == "Planning/Decision/Decision Criteria.md"
    assert candidates[0].reason.startswith("vault_note:")


def test_shape_merged_candidates_balances_mixed_sources_when_scores_are_close() -> None:
    candidates = _shape_merged_candidates(
        [
            CandidateMemory(
                id="concept-a",
                title="Concept A",
                type="concept",
                card="",
                score=10.0,
                reason="concept",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="concept-b",
                title="Concept B",
                type="concept",
                card="",
                score=9.96,
                reason="concept",
                source="concept",
                trust="high",
            ),
            CandidateMemory(
                id="memory-a",
                title="Memory A",
                type="memory",
                card="",
                score=9.9,
                reason="memory",
                source="memory",
                trust="medium",
            ),
        ],
        limit=3,
    )

    assert [candidate.id for candidate in candidates] == ["concept-a", "memory-a", "concept-b"]


def test_reasoning_retrieval_prefers_planning_problem_solving_and_counterfactual_notes(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    _write_note(
        vault_root,
        "Reasoning Container/Concepts/Planning/Tradeoff Analysis as Decision Criteria.md",
        title="Tradeoff Analysis as Decision Criteria",
        tags=["planning", "tradeoff"],
        body="Tradeoff analysis makes choice criteria explicit so a plan can compare workable options.",
    )
    _write_note(
        vault_root,
        "Reasoning Container/Concepts/Problem Solving/Root Cause Analysis.md",
        title="Root Cause Analysis",
        tags=["problem-solving", "diagnosis"],
        body="Root cause analysis traces a visible symptom back to a changeable cause.",
    )
    _write_note(
        vault_root,
        "Reasoning Container/Concepts/Counterfactuals/Sensitivity Analysis and What Changes the Conclusion.md",
        title="Sensitivity Analysis and What Changes the Conclusion",
        tags=["counterfactuals", "sensitivity"],
        body="Sensitivity analysis asks which assumptions would change the conclusion.",
    )
    _write_note(
        vault_root,
        "Reasoning Container/Concepts/Debate/Steelmanning and Strong Opposition.md",
        title="Steelmanning and Strong Opposition",
        tags=["debate", "argument"],
        body="Steelmanning means reconstructing the strongest opposing view before criticizing it.",
    )
    _write_note(
        vault_root,
        "Reasoning Container/Concepts/Physics/Mechanistic Explanation.md",
        title="Mechanistic Explanation",
        tags=["physics", "mechanism"],
        body="Mechanistic explanation asks what interacting parts produce the observed behavior.",
    )

    store = VaultNoteStore(vault_root=vault_root)
    service = ConceptSearchService()
    records = store.list_notes()

    tradeoff_hits = service.search(records=records, query="help me think through tradeoffs in this plan", limit=5)
    assert tradeoff_hits
    assert tradeoff_hits[0].title == "Tradeoff Analysis as Decision Criteria"

    root_cause_hits = service.search(records=records, query="what is the root cause of this failure", limit=5)
    assert root_cause_hits
    assert root_cause_hits[0].title == "Root Cause Analysis"

    counterfactual_hits = service.search(records=records, query="what changes the conclusion here", limit=5)
    assert counterfactual_hits
    assert counterfactual_hits[0].title == "Sensitivity Analysis and What Changes the Conclusion"

    steelman_hits = service.search(records=records, query="steelman the opposing view", limit=5)
    assert steelman_hits
    assert steelman_hits[0].title == "Steelmanning and Strong Opposition"

    mechanism_hits = service.search(records=records, query="reason about mechanism and constraints", limit=5)
    assert mechanism_hits
    assert mechanism_hits[0].title == "Mechanistic Explanation"
