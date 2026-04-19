from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any

from openai import OpenAI

from vantage_v5.services.search import CandidateMemory
from vantage_v5.storage.workspaces import WorkspaceDocument

LOW_CONTEXT_TURN_RE = re.compile(r"[a-zA-Z0-9]+")
FOLLOW_UP_CUES = (
    "what about",
    "which one",
    "the first",
    "the second",
    "the third",
    "that one",
    "this one",
    "those",
    "these",
    "compare that",
    "compare it",
    "compare",
    "recommend",
    "recommendation",
    "tradeoff",
    "tradeoffs",
    "risk",
    "risks",
    "elaborate",
    "expand",
    "go deeper",
    "tell me more",
    "same one",
    "baseline",
    "rerun",
    "again",
)
WHITEBOARD_EDIT_VERB_RE = re.compile(
    r"\b(?:update|revise|edit|refine|rewrite|change|adjust|add|remove|include|incorporate|personalize|polish|tighten|shorten|expand|improve)\b",
    re.IGNORECASE,
)
WHITEBOARD_EDIT_TARGET_RE = re.compile(
    r"\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|it|this|that)\b",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ContinuityHint:
    kind: str
    summary: str
    preserve_selected_record: bool
    anchor_candidate: CandidateMemory | None = None
    workspace_summary: str | None = None
    pending_summary: str | None = None
    selected_record_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "summary": self.summary,
            "preserve_selected_record": self.preserve_selected_record,
            "workspace_summary": self.workspace_summary,
            "pending_summary": self.pending_summary,
            "selected_record_reason": self.selected_record_reason,
        }


class ConceptVettingService:
    def __init__(self, *, model: str, openai_api_key: str | None) -> None:
        self.model = model
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    def vet(
        self,
        *,
        message: str,
        candidates: list[CandidateMemory],
        continuity_hint: dict[str, Any] | None = None,
    ) -> tuple[list[CandidateMemory], dict[str, Any]]:
        if not candidates:
            return [], {"none_relevant": True, "rationale": "No search candidates."}
        if self.client:
            try:
                return self._openai_vet(message=message, candidates=candidates, continuity_hint=continuity_hint)
            except Exception:
                logger.exception("OpenAI vetting failed; falling back to deterministic candidate selection.")
                return self._fallback_vet(candidates=candidates, continuity_hint=continuity_hint)
        return self._fallback_vet(candidates=candidates, continuity_hint=continuity_hint)

    def _openai_vet(
        self,
        *,
        message: str,
        candidates: list[CandidateMemory],
        continuity_hint: dict[str, Any] | None,
    ) -> tuple[list[CandidateMemory], dict[str, Any]]:
        payload = {
            "user_message": message,
            "candidates": [candidate.to_dict() for candidate in candidates],
            "selection_limit": 5,
            "continuity_hint": continuity_hint,
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage memory vetting call. "
                "Select only the memory items that are genuinely relevant to the user's current message. "
                "Candidates may be timeless concepts, saved memories, saved artifacts, or read-only vault notes. "
                "Prefer timeless concepts for reasoning, prefer saved memories and artifacts for continuity, and include a vault note when it is uniquely useful. "
                "A continuity hint may summarize a selected record, a live whiteboard draft, or a pending whiteboard follow-up. "
                "Use that hint as context, but still return only the items that are genuinely relevant. "
                "Return up to 5 item ids. If none are relevant, say so. "
                "Prefer a focused subset over a broad noisy set."
            ),
            input=json.dumps(payload),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "concept_vetting",
                    "strict": False,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "selected_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "none_relevant": {"type": "boolean"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["selected_ids", "none_relevant", "rationale"],
                    },
                }
            },
        )
        result = json.loads(response.output_text)
        selected_ids = set(result.get("selected_ids", [])[:5])
        vetted = [candidate for candidate in candidates if candidate.id in selected_ids][:5]
        return vetted, result

    @staticmethod
    def _fallback_vet(
        *,
        candidates: list[CandidateMemory],
        continuity_hint: dict[str, Any] | None,
    ) -> tuple[list[CandidateMemory], dict[str, Any]]:
        if not candidates:
            rationale = "No candidates."
            if continuity_hint:
                rationale = f"{rationale} Continuity hint: {continuity_hint.get('summary', '').strip()}".strip()
            return [], {"none_relevant": True, "rationale": rationale}
        top_score = candidates[0].score
        threshold = max(1.0, top_score * 0.35)
        vetted = [candidate for candidate in candidates if candidate.score >= threshold][:5]
        rationale = "Deterministic score threshold over merged memory search candidates."
        if continuity_hint:
            summary = str(continuity_hint.get("summary") or "").strip()
            if summary:
                rationale = f"{rationale} Continuity hint: {summary}"
        return vetted, {
            "selected_ids": [candidate.id for candidate in vetted],
            "none_relevant": not bool(vetted),
            "rationale": rationale,
        }


def build_continuity_hint(
    *,
    message: str,
    history: list[dict[str, str]],
    selected_memory: CandidateMemory | None,
    preserve_selected_record: bool,
    selected_record_reason: str | None,
    pending_workspace_update: dict[str, Any] | None,
    workspace: WorkspaceDocument,
    workspace_scope: str,
) -> ContinuityHint | None:
    workspace_continuity = _workspace_continuity_summary(message=message, workspace=workspace, workspace_scope=workspace_scope)
    pending_continuity = _pending_workspace_summary(message=message, pending_workspace_update=pending_workspace_update)

    if selected_memory is not None and preserve_selected_record:
        label = _selected_memory_label(selected_memory)
        summary = selected_record_reason or (
            f"Selected {label} '{selected_memory.title}' is in focus for this turn."
        )
        if selected_memory.type == "scenario_comparison" and selected_record_reason is None:
            summary = f"Selected scenario comparison artifact '{selected_memory.title}' is in focus for this turn."
        return ContinuityHint(
            kind="selected_record",
            summary=summary,
            preserve_selected_record=preserve_selected_record,
            anchor_candidate=selected_memory,
            workspace_summary=workspace_continuity,
            pending_summary=pending_continuity,
            selected_record_reason=selected_record_reason,
        )

    if pending_continuity is not None:
        return ContinuityHint(
            kind="pending_whiteboard",
            summary=pending_continuity,
            preserve_selected_record=False,
            anchor_candidate=None,
            workspace_summary=workspace_continuity,
            pending_summary=pending_continuity,
        )

    if workspace_continuity is not None:
        return ContinuityHint(
            kind="workspace_draft",
            summary=workspace_continuity,
            preserve_selected_record=False,
            anchor_candidate=None,
            workspace_summary=workspace_continuity,
        )

    return None


def should_preserve_selected_record(
    *,
    message: str,
    history: list[dict[str, str]],
    selected_memory: CandidateMemory | None,
) -> bool:
    if selected_memory is None or not history:
        return False
    normalized = " ".join(message.strip().split())
    if not normalized:
        return False
    tokens = LOW_CONTEXT_TURN_RE.findall(normalized)
    token_count = len(tokens)
    if token_count <= 2:
        return True
    if _message_looks_like_follow_up(normalized):
        return True
    return False


def anchor_selected_record_candidate(
    vetted_memory: list[CandidateMemory],
    vetting: dict[str, Any],
    selected_memory: CandidateMemory,
    *,
    continuity_reason: str | None = None,
    limit: int = 5,
) -> tuple[list[CandidateMemory], dict[str, Any]]:
    if any(item.id == selected_memory.id and item.source == selected_memory.source for item in vetted_memory):
        return vetted_memory, vetting

    anchored = [selected_memory, *vetted_memory]
    anchored = _merge_candidate_memory(anchored, [], limit=limit)
    selected_ids = [selected_memory.id, *[item.id for item in vetted_memory if item.id != selected_memory.id]][:limit]
    source_label = _selected_memory_label(selected_memory)
    continuity_note = continuity_reason or (
        f"Selected {source_label} '{selected_memory.title}' was kept as continuity context for this turn."
    )
    rationale = str(vetting.get("rationale", "")).strip()
    merged_rationale = f"{rationale} {continuity_note}".strip() if rationale else continuity_note
    updated_vetting = {
        **vetting,
        "selected_ids": selected_ids,
        "none_relevant": False,
        "rationale": merged_rationale,
    }
    return anchored, updated_vetting


def resolve_selected_record_candidate(
    record_id: str | None,
    concept_store: Any,
    reference_concept_store: Any | None,
    memory_store: Any,
    reference_memory_store: Any | None,
    artifact_store: Any,
    reference_artifact_store: Any | None,
    vault_store: Any,
    *,
    reason: str | None = None,
) -> CandidateMemory | None:
    if not record_id:
        return None

    record = _find_record(
        record_id,
        concept_store,
        reference_concept_store,
        memory_store,
        reference_memory_store,
        artifact_store,
        reference_artifact_store,
    )
    if record is not None:
        return CandidateMemory(
            id=record.id,
            title=record.title,
            type=record.type,
            card=record.card,
            score=1000.0,
            reason=reason or "Selected record preserved as continuity context for this turn.",
            source=record.source,
            trust=record.trust,
            body=record.body,
            path=record.path_hint,
        )

    try:
        note = vault_store.get(record_id)
    except FileNotFoundError:
        return None
    return CandidateMemory(
        id=note.id,
        title=note.title,
        type=note.type,
        card=note.card,
        score=1000.0,
        reason=reason or "Selected reference note preserved as continuity context for this turn.",
        source=note.source,
        trust=note.trust,
        body=note.body,
        path=note.relative_path,
    )


def _message_looks_like_follow_up(message: str) -> bool:
    lowered = message.lower()
    if any(cue in lowered for cue in FOLLOW_UP_CUES):
        return True
    tokens = [token.lower() for token in LOW_CONTEXT_TURN_RE.findall(lowered)]
    if len(tokens) <= 8 and any(token in {"it", "that", "this", "one", "they", "them"} for token in tokens):
        return True
    return False


def _pending_workspace_summary(
    *,
    message: str,
    pending_workspace_update: dict[str, Any] | None,
) -> str | None:
    if not _is_pending_workspace_update_active(pending_workspace_update):
        return None
    text = " ".join(message.strip().split()).lower()
    if not text:
        return "Pending whiteboard draft from the previous turn is still open."
    if _message_looks_like_follow_up(text) or _looks_like_pending_edit(text):
        return "Pending whiteboard draft from the previous turn is still open."
    return None


def _workspace_continuity_summary(
    *,
    message: str,
    workspace: WorkspaceDocument,
    workspace_scope: str,
) -> str | None:
    if workspace_scope == "excluded" or not workspace.content.strip():
        return None
    normalized = " ".join(message.strip().split())
    if not normalized:
        return None
    if _message_looks_like_follow_up(normalized) or _looks_like_workspace_edit(normalized):
        return f"Active whiteboard draft '{workspace.title}' is available as live context."
    return None


def _looks_like_workspace_edit(message: str) -> bool:
    return bool(WHITEBOARD_EDIT_VERB_RE.search(message) and WHITEBOARD_EDIT_TARGET_RE.search(message))


def _looks_like_pending_edit(message: str) -> bool:
    return bool(WHITEBOARD_EDIT_VERB_RE.search(message) and WHITEBOARD_EDIT_TARGET_RE.search(message))


def _selected_memory_label(candidate: CandidateMemory) -> str:
    if candidate.source == "concept":
        return "concept"
    if candidate.source == "vault_note":
        return "reference note"
    return "saved note"


def _find_record(record_id: str, *stores: Any) -> Any | None:
    for store in stores:
        if store is None:
            continue
        try:
            return store.get(record_id)
        except FileNotFoundError:
            continue
    return None


def _merge_candidate_memory(
    first: list[CandidateMemory],
    second: list[CandidateMemory],
    *,
    limit: int,
) -> list[CandidateMemory]:
    merged: dict[tuple[str, str], CandidateMemory] = {}
    for item in [*first, *second]:
        key = (item.source, item.id)
        existing = merged.get(key)
        if existing is None or item.score >= existing.score:
            merged[key] = item
    ordered = sorted(
        merged.values(),
        key=lambda item: (item.score, _candidate_source_priority(item.source)),
        reverse=True,
    )
    return ordered[:limit]


def _candidate_source_priority(source: str) -> int:
    return {
        "concept": 3,
        "memory": 2,
        "artifact": 2,
        "vault_note": 1,
    }.get(source, 0)


def _is_pending_workspace_update_active(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("type") in {"offer_whiteboard", "draft_whiteboard"}
        and value.get("status") in {"offered", "draft_ready"}
        and bool(value.get("origin_user_message"))
    )
