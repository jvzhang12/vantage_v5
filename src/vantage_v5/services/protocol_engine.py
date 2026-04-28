from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import PreparedTurnContext
from vantage_v5.services.executor import ExecutedAction
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.protocols import BUILT_IN_PROTOCOLS
from vantage_v5.services.protocols import ProtocolInterpreter
from vantage_v5.services.protocols import build_protocol_write_from_update
from vantage_v5.services.protocols import built_in_protocol_kind_for_lookup
from vantage_v5.services.protocols import find_protocol_record
from vantage_v5.services.protocols import protocol_candidates_for_kinds
from vantage_v5.services.protocols import normalize_protocol_kind
from vantage_v5.services.search import CandidateMemory
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.markdown_store import MarkdownRecord


@dataclass(frozen=True, slots=True)
class ResolvedProtocolAction:
    protocol_kind: str
    reason: str | None = None
    source: str = "navigator_control_panel"

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_kind": self.protocol_kind,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ResolvedTurnProtocols:
    actions: tuple[ResolvedProtocolAction, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def applied_protocol_kinds(self) -> list[str]:
        return [action.protocol_kind for action in self.actions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied_protocol_kinds": self.applied_protocol_kinds,
            "actions": [action.to_dict() for action in self.actions],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ProtocolGuidance:
    protocol_kinds: tuple[str, ...] = ()
    candidates: tuple[CandidateMemory, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def applied_protocol_kinds(self) -> list[str]:
        return list(self.protocol_kinds)

    def candidate_memory(self) -> list[CandidateMemory]:
        return list(self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied_protocol_kinds": self.applied_protocol_kinds,
            "candidate_count": len(self.candidates),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ProtocolTurnResult:
    protocol_action: ExecutedAction | None = None
    protocol_record: MarkdownRecord | None = None
    recall_protocol_kinds: tuple[str, ...] = ()
    concept_records: tuple[MarkdownRecord, ...] = ()
    rationale: str = ""

    @property
    def has_update(self) -> bool:
        return self.protocol_action is not None


@dataclass(frozen=True, slots=True)
class ProtocolCatalogEntry:
    record: MarkdownRecord | None = None
    built_in_kind: str | None = None

    @property
    def is_built_in(self) -> bool:
        return self.built_in_kind is not None


@dataclass(frozen=True, slots=True)
class ProtocolCatalog:
    entries: tuple[ProtocolCatalogEntry, ...] = ()


class ProtocolEngine:
    def __init__(self, *, model: str = "", openai_api_key: str | None = None) -> None:
        self.protocol_interpreter = ProtocolInterpreter(model=model, openai_api_key=openai_api_key)

    def resolve_for_turn(
        self,
        *,
        navigation: NavigationDecision,
        request: ChatTurnRequestContext,
        context: PreparedTurnContext,
    ) -> ResolvedTurnProtocols:
        del request, context
        control_panel = navigation.control_panel
        if not isinstance(control_panel, dict):
            return ResolvedTurnProtocols()
        raw_actions = control_panel.get("actions")
        if not isinstance(raw_actions, list):
            return ResolvedTurnProtocols()

        actions: list[ResolvedProtocolAction] = []
        warnings: list[str] = []
        seen: set[str] = set()
        for index, raw_action in enumerate(raw_actions):
            if not isinstance(raw_action, dict):
                continue
            action_type = str(raw_action.get("type") or "").strip()
            if action_type != "apply_protocol":
                continue
            raw_protocol_kind = raw_action.get("protocol_kind") or raw_action.get("kind")
            protocol_kind = normalize_protocol_kind(raw_protocol_kind)
            if protocol_kind is None:
                warnings.append(f"Ignored unsupported protocol action at index {index}.")
                continue
            if protocol_kind in seen:
                continue
            seen.add(protocol_kind)
            reason = str(raw_action.get("reason") or "").strip() or None
            actions.append(ResolvedProtocolAction(protocol_kind=protocol_kind, reason=reason))
        return ResolvedTurnProtocols(actions=tuple(actions), warnings=tuple(warnings))

    def interpret_and_apply(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        concept_records: list[MarkdownRecord],
        concept_store: ConceptStore,
    ) -> ProtocolTurnResult:
        protocol_interpretation = self.protocol_interpreter.interpret(
            message=message,
            history=history,
            existing_protocols=concept_records,
        )
        protocol_write = protocol_interpretation.protocol_write
        protocol_record = None
        protocol_action = None
        merged_concepts = list(concept_records)
        if protocol_write is not None:
            protocol_record = concept_store.upsert_protocol(
                protocol_id=protocol_write.protocol_id,
                title=protocol_write.title,
                card=protocol_write.card,
                body=protocol_write.body,
                protocol_kind=protocol_write.protocol_kind,
                variables=protocol_write.variables,
                applies_to=protocol_write.applies_to,
                metadata=protocol_write.metadata,
            )
            protocol_action = ExecutedAction(
                action="upsert_protocol",
                status="executed",
                summary=f"Updated protocol '{protocol_record.title}'.",
                record_id=protocol_record.id,
                source="concept",
                record_title=protocol_record.title,
            )
            merged_concepts = _merge_records(merged_concepts, [protocol_record])
        return ProtocolTurnResult(
            protocol_action=protocol_action,
            protocol_record=protocol_record,
            recall_protocol_kinds=tuple(protocol_interpretation.recall_protocol_kinds or []),
            concept_records=tuple(merged_concepts),
            rationale=protocol_interpretation.rationale,
        )

    def protocol_records(self, concept_records: list[MarkdownRecord]) -> list[MarkdownRecord]:
        records = [
            record
            for record in concept_records
            if record.type == "protocol"
        ]
        deduped: list[MarkdownRecord] = []
        seen: set[str] = set()
        for record in records:
            protocol_kind = str(record.metadata.get("protocol_kind") or "").strip().lower()
            key = protocol_kind or record.id
            if key in seen:
                continue
            seen.add(key)
            deduped.append(record)
        return deduped

    def list_catalog(
        self,
        *,
        concept_records: list[MarkdownRecord],
        include_builtins: bool,
    ) -> ProtocolCatalog:
        records = self.protocol_records(concept_records)
        entries = [ProtocolCatalogEntry(record=record) for record in records]
        if include_builtins:
            persisted_kinds = {
                str(record.metadata.get("protocol_kind") or "").strip().lower()
                for record in records
                if str(record.metadata.get("protocol_kind") or "").strip()
            }
            entries.extend(
                ProtocolCatalogEntry(built_in_kind=protocol_kind)
                for protocol_kind in sorted(BUILT_IN_PROTOCOLS)
                if protocol_kind not in persisted_kinds
            )
        return ProtocolCatalog(entries=tuple(entries))

    def lookup_catalog_entry(
        self,
        *,
        concept_records: list[MarkdownRecord],
        protocol_kind_or_id: str,
    ) -> ProtocolCatalogEntry | None:
        records = self.protocol_records(concept_records)
        protocol = find_protocol_record(records, protocol_kind_or_id)
        if protocol is not None:
            return ProtocolCatalogEntry(record=protocol)
        built_in_kind = built_in_protocol_kind_for_lookup(protocol_kind_or_id)
        if built_in_kind is not None:
            return ProtocolCatalogEntry(built_in_kind=built_in_kind)
        return None

    def update_from_api(
        self,
        *,
        protocol_kind: str,
        concept_records: list[MarkdownRecord],
        concept_store: ConceptStore,
        title: str | None,
        card: str | None,
        body: str | None,
        variables: dict[str, Any] | None,
        applies_to: list[str] | None,
    ) -> MarkdownRecord:
        normalized_kind = normalize_protocol_kind(protocol_kind)
        if normalized_kind is None:
            raise ValueError(f"Unsupported protocol kind: {protocol_kind}")
        protocol_write = build_protocol_write_from_update(
            protocol_kind=normalized_kind,
            title=title,
            card=card,
            body=body,
            variables=variables,
            applies_to=applies_to,
            existing_protocols=concept_records,
        )
        return concept_store.upsert_protocol(
            protocol_id=protocol_write.protocol_id,
            title=protocol_write.title,
            card=protocol_write.card,
            body=protocol_write.body,
            protocol_kind=protocol_write.protocol_kind,
            variables=protocol_write.variables,
            applies_to=protocol_write.applies_to,
            metadata=protocol_write.metadata,
        )

    def build_guidance(
        self,
        *,
        protocol_kinds: list[str],
        concept_records: list[MarkdownRecord],
        limit: int = 4,
    ) -> ProtocolGuidance:
        normalized_kinds: list[str] = []
        warnings: list[str] = []
        for raw_kind in protocol_kinds:
            protocol_kind = normalize_protocol_kind(raw_kind)
            if protocol_kind is None:
                warnings.append(f"Ignored unsupported protocol kind: {raw_kind}")
                continue
            if protocol_kind not in normalized_kinds:
                normalized_kinds.append(protocol_kind)
        candidates = protocol_candidates_for_kinds(
            protocol_kinds=normalized_kinds,
            concept_records=concept_records,
            limit=limit,
        )
        return ProtocolGuidance(
            protocol_kinds=tuple(normalized_kinds),
            candidates=tuple(candidates),
            warnings=tuple(warnings),
        )


def _merge_records(*record_lists: list[MarkdownRecord]) -> list[MarkdownRecord]:
    merged: dict[tuple[str, str], MarkdownRecord] = {}
    for records in record_lists:
        for record in records:
            merged[(record.source, record.id)] = record
    return list(merged.values())
