from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from pathlib import Path
import re
from typing import Any

import yaml

from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.calendar import resolve_calendar_date
from vantage_v5.services.calendar import week_start_for
from vantage_v5.services.product_scope import operational_product_scope
from vantage_v5.services.product_scope import ProductScope
from vantage_v5.services.product_scope import product_scope_for_record
from vantage_v5.services.product_scope import transient_product_scope
from vantage_v5.services.search import tokenize
from vantage_v5.services.tasks import LocalTaskProvider
from vantage_v5.services.vector_index import cosine_similarity
from vantage_v5.services.vector_index import semantic_vector
from vantage_v5.services.vector_index import VectorDocument
from vantage_v5.services.vector_index import VectorHit
from vantage_v5.services.vector_index import VectorIndex
from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.workspaces import WorkspaceDocument


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
DOMAIN_PATTERNS = {
    "calendar": re.compile(r"\b(?:calendar|schedule|event|meeting|appointment|office hours|availability|planned|plan my day|today look like|time block|when should)\b", re.IGNORECASE),
    "tasks": re.compile(r"\b(?:task|tasks|todo|to-do|homework|assignment|priority|priorities|need to|have to|focus on|finish|complete)\b", re.IGNORECASE),
    "whiteboard": re.compile(r"\b(?:whiteboard|draft|write|compose|essay|email|code|outline|proposal|document|material|materials|saved note|artifact|plan)\b", re.IGNORECASE),
    "memory": re.compile(r"\b(?:remember|memory|memories|recall|last time|we talked)\b", re.IGNORECASE),
    "concept": re.compile(r"\b(?:concept|explain|theory|principle|idea|definition)\b", re.IGNORECASE),
    "protocol": re.compile(r"\b(?:protocol|template|procedure|guideline|workflow)\b", re.IGNORECASE),
}
OPERATION_PATTERNS = {
    "read": re.compile(r"\b(?:show|tell|what|list|find|pull up|open|look at|go back|revisit)\b", re.IGNORECASE),
    "draft": re.compile(r"\b(?:draft|write|compose|outline|create|build|prepare)\b", re.IGNORECASE),
    "edit": re.compile(r"\b(?:edit|revise|update|change|replace|rename|move|reschedule|cancel|complete)\b", re.IGNORECASE),
    "schedule": re.compile(r"\b(?:schedule|calendar|time block|when should|at \d|from \d)\b", re.IGNORECASE),
    "remember": re.compile(r"\b(?:remember|save|learn|note that)\b", re.IGNORECASE),
    "reopen": re.compile(r"\b(?:go back|pull up|reopen|last|previous|working on)\b", re.IGNORECASE),
}
TEMPORAL_RE = re.compile(
    r"\b(?P<relative>today|tomorrow|yesterday|this week|next week|last week)\b"
    r"|\b(?P<last_weekday>last\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b"
    r"|\b(?P<iso>\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
ENTITY_RE = re.compile(r"\"([^\"]+)\"|'([^']+)'|\b([A-Z][A-Za-z0-9]*(?:\s+[A-Z0-9][A-Za-z0-9]*){0,5})\b")
SURFACE_KINDS = {"today_briefing", "calendar_day", "calendar_week", "task_focus", "whiteboard"}
HARD_SURFACE_INTENTS = {"chat_only", "scenario_comparison", "current_artifact_followup"}
RESOURCE_VALUE_LIMIT = 2800
VECTOR_MATCH_THRESHOLD = 0.16
VECTOR_BONUS_WEIGHT = 3.6
DERIVATIVE_ARTIFACT_PENALTY = 1.2
ATTENTION_STOPWORDS = {
    "about",
    "can",
    "could",
    "does",
    "find",
    "have",
    "how",
    "like",
    "look",
    "looks",
    "material",
    "materials",
    "please",
    "show",
    "tell",
    "what",
    "what's",
    "whats",
    "would",
    "you",
}
QUESTION_ENTITIES = {
    "Can",
    "Could",
    "How",
    "Please",
    "Show",
    "Tell",
    "What",
    "What's",
    "Would",
}
MY_DAY_RE = re.compile(
    r"\b(?:my day|the day|today)\b.{0,80}\b(?:look like|planned|plan|schedule|agenda|commitments?)\b|"
    r"\b(?:what(?:'s| is)?|tell me about|show me|walk me through)\b.{0,80}\b(?:my day|the day|today)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class TemporalReference:
    raw_text: str
    relation: str
    start: date
    end: date
    grain: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "relation": self.relation,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "grain": self.grain,
        }


@dataclass(frozen=True, slots=True)
class QueryFrame:
    raw_text: str
    normalized_text: str
    tokens: tuple[str, ...]
    domains: tuple[str, ...]
    operations: tuple[str, ...]
    entities: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    temporal_references: tuple[TemporalReference, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "tokens": list(self.tokens),
            "domains": list(self.domains),
            "operations": list(self.operations),
            "entities": list(self.entities),
            "artifact_kinds": list(self.artifact_kinds),
            "temporal_references": [item.to_dict() for item in self.temporal_references],
        }


@dataclass(frozen=True, slots=True)
class AttentionResource:
    id: str
    kind: str
    app: str
    title: str
    summary: str
    keys: tuple[str, ...]
    content: str
    source: str
    scope: str
    durability: str
    is_canonical: bool
    source_status: dict[str, Any]
    timestamps: dict[str, str]
    value_ref: dict[str, Any]
    suggested_surface: str | None = None
    data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AttentionCandidate:
    id: str
    resource_id: str
    kind: str
    app: str
    title: str
    summary: str
    source: str
    scope: str
    durability: str
    is_canonical: bool
    score: float
    matched_keys: tuple[str, ...]
    temporal_matches: tuple[str, ...]
    suggested_surface: str | None
    why_candidate: str
    value_ref: dict[str, Any]
    retrieval_scores: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "kind": self.kind,
            "app": self.app,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "scope": self.scope,
            "durability": self.durability,
            "is_canonical": self.is_canonical,
            "score": self.score,
            "matched_keys": list(self.matched_keys),
            "temporal_matches": list(self.temporal_matches),
            "suggested_surface": self.suggested_surface,
            "why_candidate": self.why_candidate,
            "value_ref": dict(self.value_ref),
            "retrieval_scores": dict(self.retrieval_scores),
        }


@dataclass(frozen=True, slots=True)
class SelectedAttentionResource:
    id: str
    resource_id: str
    kind: str
    app: str
    title: str
    summary: str
    source: str
    scope: str
    durability: str
    is_canonical: bool
    content: str
    data: dict[str, Any]
    source_status: dict[str, Any]
    timestamps: dict[str, str]
    suggested_surface: str | None
    why_selected: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "kind": self.kind,
            "app": self.app,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "scope": self.scope,
            "durability": self.durability,
            "is_canonical": self.is_canonical,
            "content": self.content,
            "data": dict(self.data),
            "source_status": dict(self.source_status),
            "timestamps": dict(self.timestamps),
            "suggested_surface": self.suggested_surface,
            "why_selected": self.why_selected,
        }


@dataclass(frozen=True, slots=True)
class NavigatorSelection:
    selected_ids: tuple[str, ...]
    primary_resource_id: str | None
    supporting_resource_ids: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    surface_to_open: str | None
    reason: str
    confidence: float
    fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_ids": list(self.selected_ids),
            "primary_resource_id": self.primary_resource_id,
            "supporting_resource_ids": list(self.supporting_resource_ids),
            "rejected_candidate_ids": list(self.rejected_candidate_ids),
            "surface_to_open": self.surface_to_open,
            "reason": self.reason,
            "confidence": self.confidence,
            "fallback": self.fallback,
        }


@dataclass(frozen=True, slots=True)
class AttentionTurn:
    query_frame: QueryFrame
    candidates: tuple[AttentionCandidate, ...]
    resources: dict[str, AttentionResource]

    def compact_candidates(self, *, limit: int = 8) -> list[dict[str, Any]]:
        return [candidate.to_dict() for candidate in self.candidates[:limit]]

    def select(self, raw_selection: Any, *, limit: int = 4) -> tuple[NavigatorSelection, tuple[SelectedAttentionResource, ...]]:
        selection = normalize_navigator_selection(raw_selection, candidates=self.candidates, limit=limit)
        selected = tuple(
            self._selected_resource(candidate_id, selection.reason)
            for candidate_id in selection.selected_ids
            if candidate_id in self.resources
        )
        return selection, tuple(item for item in selected if item is not None)

    def _selected_resource(self, resource_id: str, why_selected: str) -> SelectedAttentionResource | None:
        resource = self.resources.get(resource_id)
        if resource is None:
            return None
        return SelectedAttentionResource(
            id=f"selected-{resource.id}",
            resource_id=resource.id,
            kind=resource.kind,
            app=resource.app,
            title=resource.title,
            summary=resource.summary,
            source=resource.source,
            scope=resource.scope,
            durability=resource.durability,
            is_canonical=resource.is_canonical,
            content=_limit_text(resource.content, RESOURCE_VALUE_LIMIT),
            data=dict(resource.data or {}),
            source_status=dict(resource.source_status),
            timestamps=dict(resource.timestamps),
            suggested_surface=resource.suggested_surface,
            why_selected=why_selected or "Navigator selected this resource from the deterministic attention shortlist.",
        )


class AttentionEngine:
    def __init__(
        self,
        *,
        calendar_provider: LocalCalendarProvider,
        task_provider: LocalTaskProvider,
        vector_index: VectorIndex | None = None,
        today: date | None = None,
    ) -> None:
        self.calendar_provider = calendar_provider
        self.task_provider = task_provider
        self.vector_index = vector_index
        self.today = today or date.today()

    def prepare_turn(
        self,
        *,
        message: str,
        runtime: dict[str, Any],
        workspace: WorkspaceDocument,
        visible_artifacts: list[dict[str, Any]] | None = None,
    ) -> AttentionTurn:
        query_frame = build_query_frame(message, today=self.today)
        resources = _dedupe_resources(
            [
                *self._visible_resources(visible_artifacts or []),
                *self._workspace_resources(runtime=runtime, active_workspace=workspace),
                *self._record_resources(runtime=runtime),
                *self._operational_resources(query_frame),
            ]
        )
        vector_hits = self._vector_hits(query_frame=query_frame, resources=resources)
        candidates = tuple(_rank_resources(
            query_frame=query_frame,
            resources=resources,
            today=self.today,
            vector_hits=vector_hits,
        ))
        return AttentionTurn(
            query_frame=query_frame,
            candidates=candidates,
            resources={resource.id: resource for resource in resources},
        )

    def _vector_hits(
        self,
        *,
        query_frame: QueryFrame,
        resources: list[AttentionResource],
    ) -> dict[str, VectorHit]:
        if self.vector_index is None:
            return {}
        documents = [_vector_document(resource) for resource in resources]
        try:
            self.vector_index.sync(documents)
            return {
                hit.resource_id: hit
                for hit in self.vector_index.query(query_frame.raw_text, limit=24)
            }
        except Exception:
            return {}

    def _visible_resources(self, visible_artifacts: list[dict[str, Any]]) -> list[AttentionResource]:
        resources: list[AttentionResource] = []
        for index, artifact in enumerate(visible_artifacts):
            if not isinstance(artifact, dict):
                continue
            kind = _clean_text(artifact.get("kind")) or "visible_artifact"
            title = _clean_text(artifact.get("title") or artifact.get("label") or artifact.get("id")) or kind.replace("_", " ").title()
            summary = _clean_text(artifact.get("summary")) or "Visible in the user's current Vantage view."
            content = _clean_text(artifact.get("content")) or summary
            data = artifact.get("data") if isinstance(artifact.get("data"), dict) else {}
            resource_id = _resource_id("visible", _clean_text(artifact.get("id")) or f"{kind}-{index + 1}")
            timestamps = _timestamps_from_surface_data(data)
            product_scope = transient_product_scope()
            resources.append(
                AttentionResource(
                    id=resource_id,
                    kind=kind,
                    app=_app_for_kind(kind),
                    title=title,
                    summary=summary,
                    keys=_resource_keys(title, summary, content, kind),
                    content=content,
                    source="visible_artifact",
                    scope=product_scope.scope,
                    durability=product_scope.durability,
                    is_canonical=product_scope.is_canonical,
                    source_status={"visible": True, "read_only": True},
                    timestamps=timestamps,
                    value_ref={"kind": kind, "source": "visible_artifact", "id": artifact.get("id")},
                    suggested_surface=kind if kind in SURFACE_KINDS else None,
                    data=dict(data),
                )
            )
        return resources

    def _workspace_resources(self, *, runtime: dict[str, Any], active_workspace: WorkspaceDocument) -> list[AttentionResource]:
        workspace_store = runtime.get("workspace_store")
        workspaces_dir = getattr(workspace_store, "workspaces_dir", None)
        resources: list[AttentionResource] = [
            _workspace_resource(
                active_workspace,
                source="active_workspace",
                active=True,
                runtime_scope=str(runtime.get("scope") or "durable"),
            )
        ]
        if isinstance(workspaces_dir, Path) and workspaces_dir.exists():
            for path in sorted(workspaces_dir.glob("*.md")):
                if path.stem == active_workspace.workspace_id:
                    continue
                try:
                    document = workspace_store.load(path.stem)
                except Exception:
                    continue
                resources.append(
                    _workspace_resource(
                        document,
                        source="workspace_store",
                        active=False,
                        runtime_scope=str(runtime.get("scope") or "durable"),
                    )
                )
        return resources

    def _record_resources(self, *, runtime: dict[str, Any]) -> list[AttentionResource]:
        resources: list[AttentionResource] = []
        store_calls = (
            ("concept_store", "list_concepts"),
            ("reference_concept_store", "list_concepts"),
            ("memory_store", "list_memories"),
            ("reference_memory_store", "list_memories"),
            ("artifact_store", "list_artifacts"),
            ("reference_artifact_store", "list_artifacts"),
            ("memory_trace_store", "list_recent_traces"),
        )
        for store_key, method_name in store_calls:
            store = runtime.get(store_key)
            method = getattr(store, method_name, None)
            if not callable(method):
                continue
            try:
                records = method()
            except Exception:
                continue
            for record in records:
                if isinstance(record, MarkdownRecord):
                    resources.append(_record_resource(record, store_key=store_key, runtime=runtime))
        return resources

    def _operational_resources(self, query_frame: QueryFrame) -> list[AttentionResource]:
        resources: list[AttentionResource] = []
        wants_calendar = "calendar" in query_frame.domains or "schedule" in query_frame.operations
        wants_tasks = "tasks" in query_frame.domains
        wants_week = "week" in query_frame.normalized_text
        has_day_frame = bool(query_frame.temporal_references)
        if wants_calendar or has_day_frame and "scheduled" in {item.relation for item in query_frame.temporal_references}:
            target_date = _target_date(query_frame, self.today)
            try:
                if wants_week:
                    calendar_week = self.calendar_provider.week(target_date).to_dict()
                    resources.append(_calendar_week_resource(calendar_week))
                else:
                    calendar_day = self.calendar_provider.day(target_date).to_dict()
                    resources.append(_calendar_day_resource(calendar_day))
            except Exception:
                pass
        if wants_tasks or "schedule" in query_frame.operations and "calendar" not in query_frame.domains:
            target_date = _target_date(query_frame, self.today)
            try:
                resources.append(_task_focus_resource(self.task_provider.focus(target_date).to_dict()))
            except Exception:
                pass
        return resources


def build_query_frame(message: str, *, today: date | None = None) -> QueryFrame:
    today = today or date.today()
    raw_text = str(message or "")
    normalized = " ".join(raw_text.strip().split()).lower()
    tokens = tuple(sorted(token for token in tokenize(normalized) if token not in ATTENTION_STOPWORDS))
    domains = [name for name, pattern in DOMAIN_PATTERNS.items() if pattern.search(raw_text)]
    operations = tuple(name for name, pattern in OPERATION_PATTERNS.items() if pattern.search(raw_text))
    temporal_references = list(_temporal_references(raw_text, today=today))
    if _is_my_day_request(raw_text):
        for domain in ("calendar", "tasks"):
            if domain not in domains:
                domains.append(domain)
        if not any(reference.raw_text.lower() == "today" for reference in temporal_references):
            temporal_references.append(TemporalReference("today", "scheduled", today, today, "day"))
    entities = tuple(_entities(raw_text))
    artifact_kinds = tuple(_artifact_kinds(raw_text, domains=tuple(domains)))
    return QueryFrame(
        raw_text=raw_text,
        normalized_text=normalized,
        tokens=tokens,
        domains=tuple(domains),
        operations=operations,
        entities=entities,
        artifact_kinds=artifact_kinds,
        temporal_references=tuple(temporal_references),
    )


def normalize_navigator_selection(
    raw_selection: Any,
    *,
    candidates: tuple[AttentionCandidate, ...],
    limit: int = 4,
) -> NavigatorSelection:
    candidate_ids = [candidate.resource_id for candidate in candidates]
    candidate_id_set = set(candidate_ids)
    id_aliases = {
        alias: candidate.resource_id
        for candidate in candidates
        for alias in (candidate.resource_id, candidate.id)
        if alias
    }
    selection = raw_selection if isinstance(raw_selection, dict) else {}
    raw_ids = selection.get("selected_ids") if isinstance(selection.get("selected_ids"), list) else []
    selected_ids = tuple(
        dict.fromkeys(
            id_aliases.get(str(item).strip(), "")
            for item in raw_ids
            if id_aliases.get(str(item).strip(), "") in candidate_id_set
        )
    )[:limit]
    fallback = False
    reason = _clean_text(selection.get("reason"))
    confidence = _clamp_float(selection.get("confidence"), default=0.0)
    if not selected_ids:
        fallback = True
        fallback_candidates = _fallback_selected_candidates(candidates, limit=limit)
        selected_ids = tuple(candidate.resource_id for candidate in fallback_candidates)
        reason = "Deterministic fallback selected the highest-signal attention candidates."
        confidence = 0.55 if selected_ids else 0.0
    raw_primary_resource_id = _clean_text(selection.get("primary_resource_id"))
    primary_resource_id = id_aliases.get(raw_primary_resource_id, raw_primary_resource_id)
    if primary_resource_id not in selected_ids:
        primary_resource_id = selected_ids[0] if selected_ids else None
    primary_resource_id = _preferred_primary_resource_id(
        primary_resource_id,
        selected_ids=selected_ids,
        candidates=candidates,
    )
    selected_ids = _primary_first(selected_ids, primary_resource_id)
    supporting = tuple(item for item in selected_ids if item != primary_resource_id)
    rejected = tuple(candidate_id for candidate_id in candidate_ids if candidate_id not in selected_ids)
    surface_to_open = _clean_text(selection.get("surface_to_open"))
    if surface_to_open not in SURFACE_KINDS:
        surface_to_open = None
    surface_to_open = _selection_surface_to_open(
        surface_to_open,
        primary_resource_id=primary_resource_id,
        selected_ids=selected_ids,
        candidates=candidates,
    )
    return NavigatorSelection(
        selected_ids=selected_ids,
        primary_resource_id=primary_resource_id,
        supporting_resource_ids=supporting,
        rejected_candidate_ids=rejected,
        surface_to_open=surface_to_open,
        reason=reason or "Navigator selected context from the deterministic attention shortlist.",
        confidence=confidence,
        fallback=fallback,
    )


def selected_attention_visible_artifacts(selected: tuple[SelectedAttentionResource, ...]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for item in selected:
        if item.kind not in SURFACE_KINDS and item.suggested_surface not in SURFACE_KINDS:
            continue
        artifacts.append(
            {
                "id": item.resource_id,
                "kind": item.suggested_surface or item.kind,
                "title": item.title,
                "summary": item.summary,
                "content": item.content,
                "data": item.data,
                "source_refs": [
                    {
                        "id": item.resource_id,
                        "title": item.title,
                        "source": item.source,
                        "scope": item.scope,
                        "durability": item.durability,
                        "is_canonical": item.is_canonical,
                        "kind": item.kind,
                        "read_only": bool(item.source_status.get("read_only", True)),
                        "writable": bool(item.source_status.get("writable")),
                    }
                ],
            }
        )
    return artifacts


def apply_attention_surface_selection(
    surface_invocation: dict[str, Any],
    selection: NavigatorSelection | None,
    *,
    selected_resources: tuple[SelectedAttentionResource, ...] = (),
) -> dict[str, Any]:
    payload = dict(surface_invocation or {})
    if selection is None or not selection.surface_to_open:
        return payload
    surface = selection.surface_to_open
    if surface not in {"calendar_day", "calendar_week", "task_focus", "today_briefing", "whiteboard"}:
        return payload
    if str(payload.get("intent") or "").strip().lower() in HARD_SURFACE_INTENTS:
        return payload

    existing_primary = str(payload.get("primary_surface") or "chat").strip().lower()
    same_primary = existing_primary == surface
    selected_supporting_surfaces = _supporting_surfaces_for_selection(
        surface,
        selection=selection,
        selected_resources=selected_resources,
    )
    existing_supporting_surfaces = (
        [
            str(kind or "").strip().lower()
            for kind in payload.get("supporting_surfaces") or []
            if str(kind or "").strip().lower() in SURFACE_KINDS
        ]
        if same_primary
        else []
    )
    supporting_surfaces = [
        kind
        for kind in dict.fromkeys([*existing_supporting_surfaces, *selected_supporting_surfaces])
        if kind != surface
    ]
    payload["primary_surface"] = surface
    if not same_primary or not _clean_text(payload.get("intent")):
        payload["intent"] = "attention_selected_context"
    payload["supporting_surfaces"] = supporting_surfaces
    surfaces = [
        {
            "kind": surface,
            "role": "primary",
            "reason": selection.reason,
            "status": "selected",
        },
        *[
            {
                "kind": supporting_surface,
                "role": "supporting",
                "reason": "Navigator selected this supporting context from the deterministic attention shortlist.",
                "status": "selected",
            }
            for supporting_surface in supporting_surfaces
        ],
    ]
    payload["surfaces"] = surfaces
    payload["write_behavior"] = _attention_write_behavior(surface, existing=payload.get("write_behavior"))
    payload["reason"] = selection.reason
    payload["confidence"] = max(float(payload.get("confidence") or 0.0), selection.confidence)
    payload["trigger"] = "attention_navigator"
    payload["selection_authority"] = "attention_navigator"
    return payload


def attention_payload(
    *,
    turn: AttentionTurn | None,
    selection: NavigatorSelection | None,
    selected_resources: tuple[SelectedAttentionResource, ...] = (),
) -> dict[str, Any]:
    if turn is None:
        return {
            "query_frame": None,
            "attention_candidates": [],
            "navigator_selection": None,
            "selected_attention_resources": [],
        }
    return {
        "query_frame": turn.query_frame.to_dict(),
        "attention_candidates": turn.compact_candidates(),
        "navigator_selection": selection.to_dict() if selection else None,
        "selected_attention_resources": [item.to_dict() for item in selected_resources],
    }


def _supporting_surfaces_for_selection(
    primary_surface: str,
    *,
    selection: NavigatorSelection,
    selected_resources: tuple[SelectedAttentionResource, ...],
) -> list[str]:
    if primary_surface == "today_briefing":
        return ["calendar_day", "task_focus"]

    supporting: list[str] = []
    supporting_ids = set(selection.supporting_resource_ids)
    for resource in selected_resources:
        if resource.resource_id == selection.primary_resource_id and resource.resource_id not in supporting_ids:
            continue
        surface = resource.suggested_surface if resource.suggested_surface in SURFACE_KINDS else resource.kind
        if surface in SURFACE_KINDS and surface != primary_surface:
            supporting.append(surface)
    return list(dict.fromkeys(supporting))


def _attention_write_behavior(surface: str, *, existing: Any) -> str:
    existing_text = _clean_text(existing)
    if surface == "whiteboard":
        return existing_text if existing_text == "draft_only" else "open_only"
    if existing_text and existing_text != "none":
        return existing_text
    if surface in {"calendar_day", "calendar_week", "today_briefing"}:
        return "read_only"
    if surface == "task_focus":
        return "proposal_only"
    return "none"


def _preferred_primary_resource_id(
    primary_resource_id: str | None,
    *,
    selected_ids: tuple[str, ...],
    candidates: tuple[AttentionCandidate, ...],
) -> str | None:
    if not primary_resource_id:
        return primary_resource_id
    by_id = {candidate.resource_id: candidate for candidate in candidates}
    primary = by_id.get(primary_resource_id)
    if primary is None or primary.source != "artifact":
        return primary_resource_id
    comes_from = primary.value_ref.get("comes_from")
    if not isinstance(comes_from, list):
        return primary_resource_id
    selected_id_set = set(selected_ids)
    primary_title = _normalized_title(primary.title)
    for parent_id in comes_from:
        parent_resource_id = _resource_id("artifact", str(parent_id).strip())
        parent = by_id.get(parent_resource_id)
        if parent_resource_id not in selected_id_set or parent is None:
            continue
        if _normalized_title(parent.title) == primary_title:
            return parent_resource_id
    return primary_resource_id


def _primary_first(selected_ids: tuple[str, ...], primary_resource_id: str | None) -> tuple[str, ...]:
    if not primary_resource_id or primary_resource_id not in selected_ids:
        return selected_ids
    return (primary_resource_id, *(item for item in selected_ids if item != primary_resource_id))


def _normalized_title(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _selection_surface_to_open(
    requested_surface: str | None,
    *,
    primary_resource_id: str | None,
    selected_ids: tuple[str, ...],
    candidates: tuple[AttentionCandidate, ...],
) -> str | None:
    by_id = {candidate.resource_id: candidate for candidate in candidates}
    primary = by_id.get(primary_resource_id or "")
    selected = [by_id[item] for item in selected_ids if item in by_id]
    selected_whiteboard = next((_candidate for _candidate in selected if _is_openable_whiteboard_candidate(_candidate)), None)
    if selected_whiteboard is not None and (not requested_surface or _is_visible_operational_candidate(primary)):
        return "whiteboard"
    if requested_surface:
        return requested_surface
    if primary is not None and primary.source != "visible_artifact":
        surface = primary.suggested_surface if primary.suggested_surface in SURFACE_KINDS else primary.kind
        return surface if surface in SURFACE_KINDS else None
    return None


def _is_openable_whiteboard_candidate(candidate: AttentionCandidate) -> bool:
    if candidate.source == "visible_artifact":
        return False
    return candidate.suggested_surface == "whiteboard" or candidate.app == "whiteboard" or candidate.kind == "whiteboard"


def _is_visible_operational_candidate(candidate: AttentionCandidate | None) -> bool:
    if candidate is None or candidate.source != "visible_artifact":
        return False
    surface = candidate.suggested_surface if candidate.suggested_surface in SURFACE_KINDS else candidate.kind
    return surface in {"today_briefing", "calendar_day", "calendar_week", "task_focus"}


def _temporal_references(message: str, *, today: date) -> list[TemporalReference]:
    relation = _temporal_relation(message)
    references: list[TemporalReference] = []
    for match in TEMPORAL_RE.finditer(message):
        raw = match.group(0)
        lowered = raw.lower()
        if match.group("iso"):
            start = resolve_calendar_date(raw)
            references.append(TemporalReference(raw, relation, start, start, "day"))
        elif lowered == "today":
            references.append(TemporalReference(raw, relation, today, today, "day"))
        elif lowered == "tomorrow":
            target = today + timedelta(days=1)
            references.append(TemporalReference(raw, relation, target, target, "day"))
        elif lowered == "yesterday":
            target = today - timedelta(days=1)
            references.append(TemporalReference(raw, relation, target, target, "day"))
        elif lowered == "this week":
            start = week_start_for(today)
            references.append(TemporalReference(raw, relation, start, start + timedelta(days=6), "week"))
        elif lowered == "next week":
            start = week_start_for(today) + timedelta(days=7)
            references.append(TemporalReference(raw, relation, start, start + timedelta(days=6), "week"))
        elif lowered == "last week":
            start = week_start_for(today) - timedelta(days=7)
            references.append(TemporalReference(raw, relation, start, start + timedelta(days=6), "week"))
        elif lowered.startswith("last "):
            weekday = lowered.split()[-1]
            target = _previous_weekday(today, WEEKDAYS[weekday])
            references.append(TemporalReference(raw, relation, target, target, "day"))
    return references


def _temporal_relation(message: str) -> str:
    lowered = message.lower()
    if re.search(r"\b(?:created|made|started|wrote|drafted)\b", lowered):
        return "created"
    if re.search(r"\b(?:edited|updated|changed|worked on|working on|revised)\b", lowered):
        return "worked_on"
    if re.search(r"\b(?:due|deadline|by)\b", lowered):
        return "due"
    if re.search(r"\b(?:scheduled|calendar|meeting|appointment|planned|event)\b", lowered):
        return "scheduled"
    return "mentioned"


def _previous_weekday(today: date, weekday: int) -> date:
    delta = (today.weekday() - weekday) % 7
    if delta == 0:
        delta = 7
    return today - timedelta(days=delta)


def _entities(message: str) -> list[str]:
    entities: list[str] = []
    for match in ENTITY_RE.finditer(message):
        value = next((group for group in match.groups() if group), "")
        value = " ".join(value.strip().split())
        if value and value.lower() not in {"i", "vantage"} and value not in QUESTION_ENTITIES and value not in entities:
            entities.append(value)
    return entities[:8]


def _artifact_kinds(message: str, *, domains: tuple[str, ...]) -> list[str]:
    lowered = message.lower()
    kinds: list[str] = []
    if "calendar" in domains:
        kinds.append("calendar_week" if "week" in lowered else "calendar_day")
    if "tasks" in domains:
        kinds.append("task_focus")
    if "whiteboard" in domains:
        kinds.append("whiteboard")
    if "email" in lowered or "essay" in lowered or "code" in lowered or "draft" in lowered:
        kinds.append("whiteboard")
    return list(dict.fromkeys(kinds))


def _is_my_day_request(message: str) -> bool:
    return bool(MY_DAY_RE.search(message))


def _workspace_resource(
    document: WorkspaceDocument,
    *,
    source: str,
    active: bool,
    runtime_scope: str,
) -> AttentionResource:
    timestamps = _file_timestamps(document.path)
    content = document.content or ""
    product_scope = ProductScope(
        scope="experiment" if runtime_scope == "experiment" else "durable",
        durability="temporary" if runtime_scope == "experiment" else "durable",
    )
    return AttentionResource(
        id=_resource_id("workspace", document.workspace_id),
        kind="whiteboard",
        app="whiteboard",
        title=document.title,
        summary=_first_line(content) or ("Active whiteboard." if active else "Saved whiteboard."),
        keys=_resource_keys(document.workspace_id, document.title, content, "whiteboard"),
        content=content,
        source=source,
        scope=product_scope.scope,
        durability=product_scope.durability,
        is_canonical=product_scope.is_canonical,
        source_status={"active": active, "read_only": False, "writable": True},
        timestamps=timestamps,
        value_ref={"workspace_id": document.workspace_id, "path": str(document.path)},
        suggested_surface="whiteboard",
    )


def _record_resource(record: MarkdownRecord, *, store_key: str, runtime: dict[str, Any]) -> AttentionResource:
    timestamps = _record_timestamps(record)
    record_kind = "protocol" if record.type == "protocol" else record.source
    app = "protocol" if record_kind == "protocol" else ("whiteboard" if record.source == "artifact" else record.source)
    content = record.body or record.card
    product_scope = product_scope_for_record(
        record,
        canonical_root=_runtime_path(runtime.get("canonical_root")),
        experiment_root=_runtime_path(runtime.get("experiment_root")),
        fallback_scope=str(runtime.get("scope") or "durable"),
    )
    return AttentionResource(
        id=_resource_id(record.source, record.id),
        kind=record_kind,
        app=app,
        title=record.title,
        summary=record.card or _first_line(content),
        keys=_resource_keys(record.id, record.title, record.type, record.card, content, " ".join(record.links_to), " ".join(record.comes_from), _metadata_text(record.metadata)),
        content=content,
        source=record.source,
        scope=product_scope.scope,
        durability=product_scope.durability,
        is_canonical=product_scope.is_canonical,
        source_status={"store": store_key, "trust": record.trust, "read_only": True},
        timestamps=timestamps,
        value_ref={
            "record_id": record.id,
            "path": str(record.path),
            "source": record.source,
            "comes_from": list(record.comes_from),
        },
        suggested_surface="whiteboard" if record.source == "artifact" else None,
    )


def _vector_document(resource: AttentionResource) -> VectorDocument:
    return VectorDocument(
        resource_id=resource.id,
        kind=resource.kind,
        app=resource.app,
        title=resource.title,
        summary=resource.summary,
        source=resource.source,
        text=" ".join([*resource.keys, resource.content]),
        metadata={
            "value_ref": resource.value_ref,
            "timestamps": resource.timestamps,
            "suggested_surface": resource.suggested_surface,
        },
    )


def _calendar_day_resource(calendar_day: dict[str, Any]) -> AttentionResource:
    date_value = str(calendar_day.get("date") or "")
    events = [event for event in calendar_day.get("events", []) if isinstance(event, dict)]
    titles = [str(event.get("title") or "Event").strip() for event in events[:5]]
    summary = _clean_text(calendar_day.get("summary")) or f"{len(events)} calendar events for {date_value}."
    content = _calendar_day_markdown(calendar_day)
    product_scope = operational_product_scope()
    return AttentionResource(
        id=_resource_id("calendar_day", date_value),
        kind="calendar_day",
        app="calendar",
        title=f"Calendar day {date_value}".strip(),
        summary=summary,
        keys=_resource_keys("calendar", "schedule", date_value, *titles, content),
        content=content,
        source="calendar",
        scope=product_scope.scope,
        durability=product_scope.durability,
        is_canonical=product_scope.is_canonical,
        source_status=dict(calendar_day.get("source") if isinstance(calendar_day.get("source"), dict) else {}),
        timestamps={"scheduled_at": date_value},
        value_ref={"resource": "calendar.day", "date": date_value},
        suggested_surface="calendar_day",
        data={"calendar": calendar_day, "date": date_value},
    )


def _calendar_week_resource(calendar_week: dict[str, Any]) -> AttentionResource:
    start_date = str(calendar_week.get("start_date") or "")
    end_date = str(calendar_week.get("end_date") or "")
    content = _calendar_week_markdown(calendar_week)
    product_scope = operational_product_scope()
    return AttentionResource(
        id=_resource_id("calendar_week", start_date),
        kind="calendar_week",
        app="calendar",
        title=f"Calendar week {start_date}".strip(),
        summary=f"Calendar week from {start_date} through {end_date}.",
        keys=_resource_keys("calendar", "schedule", "week", start_date, end_date, content),
        content=content,
        source="calendar",
        scope=product_scope.scope,
        durability=product_scope.durability,
        is_canonical=product_scope.is_canonical,
        source_status=dict(calendar_week.get("source") if isinstance(calendar_week.get("source"), dict) else {}),
        timestamps={"scheduled_at": start_date, "scheduled_end_at": end_date},
        value_ref={"resource": "calendar.week", "week_start": start_date},
        suggested_surface="calendar_week",
        data={"calendar_week": calendar_week, "date": start_date},
    )


def _task_focus_resource(task_focus: dict[str, Any]) -> AttentionResource:
    date_value = str(task_focus.get("date") or "")
    content = _task_focus_markdown(task_focus)
    product_scope = operational_product_scope()
    return AttentionResource(
        id=_resource_id("task_focus", date_value),
        kind="task_focus",
        app="tasks",
        title=f"Task focus {date_value}".strip(),
        summary=f"Task focus for {date_value}.",
        keys=_resource_keys("tasks", "todo", "focus", date_value, content),
        content=content,
        source="tasks",
        scope=product_scope.scope,
        durability=product_scope.durability,
        is_canonical=product_scope.is_canonical,
        source_status=dict(task_focus.get("source") if isinstance(task_focus.get("source"), dict) else {}),
        timestamps={"due_at": date_value},
        value_ref={"resource": "tasks.focus", "date": date_value},
        suggested_surface="task_focus",
        data={"tasks": task_focus, "date": date_value},
    )


def _rank_resources(
    *,
    query_frame: QueryFrame,
    resources: list[AttentionResource],
    today: date,
    vector_hits: dict[str, VectorHit] | None = None,
) -> list[AttentionCandidate]:
    candidates: list[AttentionCandidate] = []
    query_tokens = set(query_frame.tokens)
    query_phrase = query_frame.normalized_text
    vector_hits = vector_hits or {}
    query_vector = semantic_vector(query_frame.raw_text)
    artifact_ids = {
        str(resource.value_ref.get("record_id") or "").strip()
        for resource in resources
        if resource.source == "artifact"
    }
    prefer_source_artifacts = _should_prefer_source_artifact(query_frame)
    for resource in resources:
        rule_score = 0.0
        temporal_score = 0.0
        matched: list[str] = []
        temporal_matches: list[str] = []
        key_text = " ".join(resource.keys).lower()
        title_text = resource.title.lower()
        key_tokens = tokenize(key_text)
        title_tokens = tokenize(resource.title)
        token_overlap = sorted(query_tokens & key_tokens)
        title_overlap = sorted(query_tokens & title_tokens)
        if resource.source == "visible_artifact":
            rule_score += 8.0
            matched.append("visible_artifact")
        if resource.app in query_frame.domains or resource.kind in query_frame.artifact_kinds:
            rule_score += 4.0
            matched.append(resource.app if resource.app in query_frame.domains else resource.kind)
        for entity in query_frame.entities:
            if entity.lower() in title_text or entity.lower() in key_text:
                rule_score += 3.2
                matched.append(entity)
        if query_phrase and len(query_phrase) >= 4 and (query_phrase in title_text or query_phrase in key_text):
            rule_score += 5.0
            matched.append("phrase")
        if title_overlap:
            rule_score += len(title_overlap) * 1.9
            matched.extend(title_overlap[:4])
        if token_overlap:
            rule_score += min(len(token_overlap), 8) * 0.55
            matched.extend(token_overlap[:6])
        for reference in query_frame.temporal_references:
            if _resource_matches_time(resource, reference):
                temporal_score += 5.0
                temporal_matches.append(f"{reference.relation}:{reference.raw_text}")
        source_score = _source_priority(resource)
        recency_score = _recency_bonus(resource, today=today)
        local_vector_similarity = cosine_similarity(query_vector, semantic_vector(resource.title, resource.summary, *resource.keys))
        vector_hit = vector_hits.get(resource.id)
        indexed_vector_similarity = vector_hit.similarity if vector_hit is not None else 0.0
        vector_similarity = max(local_vector_similarity, indexed_vector_similarity)
        vector_bonus = _vector_bonus(vector_similarity)
        if vector_bonus:
            matched.append("semantic_vector")
        trace_scope_penalty = _memory_trace_scope_penalty(
            resource,
            query_frame=query_frame,
            temporal_matches=temporal_matches,
        )
        derivative_artifact_penalty = _derivative_artifact_penalty(
            resource,
            artifact_ids=artifact_ids,
            prefer_source_artifacts=prefer_source_artifacts,
        )
        score = max(
            0.0,
            rule_score
            + temporal_score
            + source_score
            + recency_score
            + vector_bonus
            - trace_scope_penalty
            - derivative_artifact_penalty,
        )
        if score < 1.0 and resource.source != "visible_artifact":
            continue
        candidates.append(
            AttentionCandidate(
                id=f"candidate-{resource.id}",
                resource_id=resource.id,
                kind=resource.kind,
                app=resource.app,
                title=resource.title,
                summary=resource.summary,
                source=resource.source,
                scope=resource.scope,
                durability=resource.durability,
                is_canonical=resource.is_canonical,
                score=round(score, 4),
                matched_keys=tuple(dict.fromkeys([item for item in matched if item])),
                temporal_matches=tuple(temporal_matches),
                suggested_surface=resource.suggested_surface,
                why_candidate=_candidate_reason(
                    resource,
                    matched=matched,
                    temporal_matches=temporal_matches,
                    vector_similarity=vector_similarity,
                ),
                value_ref=dict(resource.value_ref),
                retrieval_scores={
                    "deterministic": round(rule_score + source_score + recency_score, 4),
                    "temporal": round(temporal_score, 4),
                    "vector_similarity": round(vector_similarity, 4),
                    "local_vector_similarity": round(local_vector_similarity, 4),
                    "indexed_vector_similarity": round(indexed_vector_similarity, 4),
                    "vector_bonus": round(vector_bonus, 4),
                    "trace_scope_penalty": round(-trace_scope_penalty, 4),
                    "derivative_artifact_penalty": round(-derivative_artifact_penalty, 4),
                    "hybrid": round(score, 4),
                },
            )
        )
    candidates.sort(key=lambda item: (item.score, _candidate_priority(item), item.title.lower()), reverse=True)
    return candidates[:12]


def _fallback_selected_candidates(candidates: tuple[AttentionCandidate, ...], *, limit: int) -> list[AttentionCandidate]:
    if not candidates:
        return []
    eligible = [
        candidate
        for candidate in candidates
        if candidate.source == "visible_artifact"
        or candidate.kind in {"calendar_day", "calendar_week", "task_focus"}
        or candidate.temporal_matches
        or candidate.score >= 8.0
    ]
    if not eligible:
        return []
    top_score = eligible[0].score
    threshold = max(6.0, top_score * 0.55)
    return [candidate for candidate in eligible if candidate.score >= threshold][:limit]


def _resource_matches_time(resource: AttentionResource, reference: TemporalReference) -> bool:
    fields_by_relation = {
        "created": ("created_at", "file_created_at", "updated_at", "file_modified_at"),
        "worked_on": ("last_edited_at", "last_opened_at", "last_mentioned_at", "updated_at", "file_modified_at", "created_at"),
        "due": ("due_at",),
        "scheduled": ("scheduled_at", "scheduled_end_at"),
        "mentioned": ("created_at", "updated_at", "file_modified_at", "scheduled_at", "due_at"),
    }
    fields = fields_by_relation.get(reference.relation, fields_by_relation["mentioned"])
    for field in fields:
        value = resource.timestamps.get(field)
        parsed = _parse_date_value(value)
        if parsed and reference.start <= parsed <= reference.end:
            return True
    return False


def _candidate_reason(
    resource: AttentionResource,
    *,
    matched: list[str],
    temporal_matches: list[str],
    vector_similarity: float = 0.0,
) -> str:
    reasons: list[str] = []
    if resource.source == "visible_artifact":
        reasons.append("already visible in the user's workspace")
    if matched:
        reasons.append(f"matched keys: {', '.join(list(dict.fromkeys(matched))[:4])}")
    if temporal_matches:
        reasons.append(f"matched time: {', '.join(temporal_matches[:2])}")
    if vector_similarity >= VECTOR_MATCH_THRESHOLD:
        reasons.append(f"semantic vector similarity: {vector_similarity:.2f}")
    if not reasons:
        reasons.append("ranked by deterministic source and recency signals")
    return "; ".join(reasons)


def _vector_bonus(similarity: float) -> float:
    if similarity < VECTOR_MATCH_THRESHOLD:
        return 0.0
    return min(VECTOR_BONUS_WEIGHT, similarity * VECTOR_BONUS_WEIGHT)


def _source_priority(resource: AttentionResource) -> float:
    if resource.source == "visible_artifact":
        return 1.8
    if resource.kind in {"calendar_day", "calendar_week", "task_focus"}:
        return 1.2
    if resource.kind == "protocol":
        return 0.85
    if resource.source == "artifact":
        return 0.7
    if resource.source == "memory":
        return 0.55
    if resource.source == "memory_trace":
        return 0.45
    if resource.source == "concept":
        return 0.35
    return 0.2


def _memory_trace_scope_penalty(
    resource: AttentionResource,
    *,
    query_frame: QueryFrame,
    temporal_matches: list[str],
) -> float:
    if resource.source != "memory_trace":
        return 0.0
    if "memory" in query_frame.domains or "reopen" in query_frame.operations:
        return 0.0
    if temporal_matches:
        return 0.0
    return 18.0


def _should_prefer_source_artifact(query_frame: QueryFrame) -> bool:
    explicit_derivative_terms = {
        "action",
        "first",
        "immediate",
        "next",
        "step",
    }
    if set(query_frame.tokens) & explicit_derivative_terms:
        return False
    if not ({"read", "reopen"} & set(query_frame.operations)):
        return False
    return any(
        phrase in query_frame.normalized_text
        for phrase in (
            "exam preparation",
            "find my",
            "find the",
            "material",
            "materials",
            "pull up",
            "study plan",
        )
    )


def _derivative_artifact_penalty(
    resource: AttentionResource,
    *,
    artifact_ids: set[str],
    prefer_source_artifacts: bool,
) -> float:
    if not prefer_source_artifacts or resource.source != "artifact":
        return 0.0
    comes_from = resource.value_ref.get("comes_from")
    if not isinstance(comes_from, list):
        return 0.0
    if not any(str(parent_id).strip() in artifact_ids for parent_id in comes_from):
        return 0.0
    title = resource.title.lower()
    if not any(term in title for term in ("action", "first", "immediate", "next", "step")):
        return 0.0
    return DERIVATIVE_ARTIFACT_PENALTY


def _candidate_priority(candidate: AttentionCandidate) -> int:
    if candidate.source == "visible_artifact":
        return 6
    if candidate.kind in {"calendar_day", "calendar_week", "task_focus"}:
        return 5
    if candidate.kind == "protocol":
        return 4
    if candidate.source in {"artifact", "memory"}:
        return 3
    if candidate.source == "memory_trace":
        return 2
    return 1


def _recency_bonus(resource: AttentionResource, *, today: date) -> float:
    parsed_values = [_parse_date_value(value) for value in resource.timestamps.values()]
    parsed = [value for value in parsed_values if value is not None]
    if not parsed:
        return 0.0
    days = min(abs((today - value).days) for value in parsed)
    if days <= 1:
        return 0.55
    if days <= 7:
        return 0.35
    if days <= 30:
        return 0.18
    return 0.0


def _record_timestamps(record: MarkdownRecord) -> dict[str, str]:
    timestamps = _file_timestamps(record.path)
    try:
        text = record.path.read_text(encoding="utf-8")
        metadata, _body = _split_frontmatter(text)
    except Exception:
        metadata = {}
    for key in ("created_at", "updated_at", "last_opened_at", "last_mentioned_at", "last_edited_at", "due_at"):
        value = metadata.get(key)
        if value is not None:
            timestamps[key] = str(value)
    if record.source == "memory_trace":
        trace_time = _trace_timestamp(record.id)
        if trace_time:
            timestamps.setdefault("created_at", trace_time)
            timestamps.setdefault("mentioned_at", trace_time)
    return timestamps


def _file_timestamps(path: Path) -> dict[str, str]:
    timestamps: dict[str, str] = {}
    try:
        stat = path.stat()
    except OSError:
        return timestamps
    timestamps["file_modified_at"] = datetime.fromtimestamp(stat.st_mtime, tz=UTC).date().isoformat()
    try:
        timestamps["file_created_at"] = datetime.fromtimestamp(stat.st_birthtime, tz=UTC).date().isoformat()
    except AttributeError:
        pass
    return timestamps


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    try:
        _, remainder = text.split("---\n", 1)
        frontmatter_text, body = remainder.split("\n---\n", 1)
    except ValueError:
        return {}, text
    metadata = yaml.safe_load(frontmatter_text) or {}
    return metadata if isinstance(metadata, dict) else {}, body


def _trace_timestamp(record_id: str) -> str:
    match = re.search(r"turn-(\d{14})", record_id)
    if not match:
        return ""
    try:
        return datetime.strptime(match.group(1), "%Y%m%d%H%M%S").date().isoformat()
    except ValueError:
        return ""


def _timestamps_from_surface_data(data: dict[str, Any]) -> dict[str, str]:
    timestamps: dict[str, str] = {}
    date_value = _clean_text(data.get("date"))
    if date_value:
        timestamps["mentioned_at"] = date_value
    calendar = data.get("calendar") if isinstance(data.get("calendar"), dict) else {}
    if calendar.get("date"):
        timestamps["scheduled_at"] = str(calendar.get("date"))
    calendar_week = data.get("calendar_week") if isinstance(data.get("calendar_week"), dict) else {}
    if calendar_week.get("start_date"):
        timestamps["scheduled_at"] = str(calendar_week.get("start_date"))
    tasks = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
    if tasks.get("date"):
        timestamps["due_at"] = str(tasks.get("date"))
    return timestamps


def _target_date(query_frame: QueryFrame, today: date) -> date:
    if query_frame.temporal_references:
        explicit = next(
            (reference for reference in query_frame.temporal_references if re.fullmatch(r"\d{4}-\d{2}-\d{2}", reference.raw_text)),
            None,
        )
        if explicit is not None:
            return explicit.start
        return query_frame.temporal_references[0].start
    return today


def _dedupe_resources(resources: list[AttentionResource]) -> list[AttentionResource]:
    by_id: dict[str, AttentionResource] = {}
    for resource in resources:
        by_id.setdefault(resource.id, resource)
    return list(by_id.values())


def _resource_keys(*values: Any) -> tuple[str, ...]:
    keys: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text:
            keys.append(text[:1600])
    return tuple(keys)


def _resource_id(prefix: str, value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", str(value or "").strip()).strip("-").lower()
    return f"{prefix}:{cleaned or 'resource'}"


def _runtime_path(value: Any) -> Path | None:
    if value is None:
        return None
    try:
        return Path(value)
    except TypeError:
        return None


def _app_for_kind(kind: str) -> str:
    if kind.startswith("calendar") or kind == "today_briefing":
        return "calendar"
    if kind == "task_focus":
        return "tasks"
    if kind in {"whiteboard", "draft"}:
        return "whiteboard"
    return "artifact"


def _calendar_day_markdown(calendar_day: dict[str, Any]) -> str:
    lines = [f"# Calendar {calendar_day.get('date') or ''}".strip()]
    events = [event for event in calendar_day.get("events", []) if isinstance(event, dict)]
    if events:
        lines.append("## Events")
        for event in events[:12]:
            lines.append(f"- {event.get('start')} to {event.get('end')}: {event.get('title') or 'Event'}")
    else:
        lines.append("No scheduled events.")
    free_blocks = [block for block in calendar_day.get("free_blocks", []) if isinstance(block, dict)]
    if free_blocks:
        lines.append("## Open Blocks")
        for block in free_blocks[:8]:
            lines.append(f"- {block.get('start')} to {block.get('end')} ({block.get('duration_minutes')} min)")
    return "\n".join(lines)


def _calendar_week_markdown(calendar_week: dict[str, Any]) -> str:
    lines = [f"# Calendar Week {calendar_week.get('start_date') or ''}".strip()]
    for day in calendar_week.get("days", []) if isinstance(calendar_week.get("days"), list) else []:
        if not isinstance(day, dict):
            continue
        events = [event for event in day.get("events", []) if isinstance(event, dict)]
        lines.append(f"## {day.get('date')}")
        if events:
            for event in events[:8]:
                lines.append(f"- {event.get('start')} to {event.get('end')}: {event.get('title') or 'Event'}")
        else:
            lines.append("- Open")
    return "\n".join(lines)


def _task_focus_markdown(task_focus: dict[str, Any]) -> str:
    lines = [f"# Task Focus {task_focus.get('date') or ''}".strip()]
    groups = task_focus.get("groups") if isinstance(task_focus.get("groups"), dict) else {}
    for group_name in ("must_do_today", "good_next", "can_defer", "unscheduled"):
        lines.append(f"## {group_name.replace('_', ' ').title()}")
        items = [item for item in groups.get(group_name, []) if isinstance(item, dict)]
        if not items:
            lines.append("- None")
        for item in items[:10]:
            due = f" due {item.get('due_date')}" if item.get("due_date") else ""
            lines.append(f"- {item.get('title') or 'Task'}{due}")
    return "\n".join(lines)


def _metadata_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_metadata_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_metadata_text(item) for item in value)
    return _clean_text(value)


def _parse_date_value(value: Any) -> date | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _clamp_float(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _first_line(value: str) -> str:
    for line in str(value or "").splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            return cleaned[:220]
    return ""


def _limit_text(value: str, limit: int) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "\n..."


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())
