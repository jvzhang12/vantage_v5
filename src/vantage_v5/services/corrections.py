from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from vantage_v5.services.protocols import BUILT_IN_PROTOCOLS


SUPPORTED_CORRECTION_ACTIONS = {"mark_incorrect", "forget"}
SUPPORTED_CORRECTION_SCOPES = {"current", "durable", "experiment"}
SUPPORTED_CORRECTION_SOURCES = {"concept", "memory", "artifact"}
SOURCE_STORE_KEYS = {
    "concept": "concept_store",
    "memory": "memory_store",
    "artifact": "artifact_store",
}
BUILT_IN_PROTOCOL_IDS = {
    str(value)
    for protocol_kind, protocol in BUILT_IN_PROTOCOLS.items()
    for value in (protocol_kind, protocol.get("id"))
    if value
}


class CorrectionRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    source: str
    record_id: str
    action: str
    requested_scope: str
    effective_scope: str
    hidden_record_scope: str
    status: str
    reason: str | None
    corrected_at: str
    suppresses_canonical: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "record_id": self.record_id,
            "action": self.action,
            "effect": "suppressed",
            "visibility": "hidden",
            "hard_deleted": False,
            "requested_scope": self.requested_scope,
            "scope": self.effective_scope,
            "hidden_record_scope": self.hidden_record_scope,
            "status": self.status,
            "reason": self.reason,
            "corrected_at": self.corrected_at,
            "suppresses_canonical": self.suppresses_canonical,
            "correction_record": {
                "id": self.record_id,
                "source": self.source,
                "status": self.status,
                "correction_action": self.action,
                "scope": self.effective_scope,
                "suppresses_canonical": self.suppresses_canonical,
            },
        }


class SavedItemCorrectionService:
    def apply(
        self,
        *,
        source: str,
        record_id: str,
        action: str,
        reason: str | None,
        scope: str,
        durable_scope: dict[str, Any],
        runtime: dict[str, Any],
        has_active_experiment: bool,
    ) -> CorrectionResult:
        normalized_source = _normalize_source(source)
        normalized_action = _normalize_action(action)
        requested_scope = _normalize_scope(scope)
        _reject_built_in_protocol(normalized_source, record_id)

        effective_scope = _effective_scope(
            requested_scope,
            runtime=runtime,
            has_active_experiment=has_active_experiment,
        )
        writable_store = _store_for_scope(
            source=normalized_source,
            scope=effective_scope,
            durable_scope=durable_scope,
            runtime=runtime,
        )
        corrected_at = datetime.now(tz=UTC).isoformat()
        cleaned_reason = _clean_reason(reason)

        existing_record = _try_get(writable_store, record_id)
        if existing_record is not None:
            _reject_protocol_record(existing_record)
            corrected_record = writable_store.suppress_record(
                record_id,
                correction_action=normalized_action,
                reason=cleaned_reason,
                corrected_at=corrected_at,
                suppresses_canonical=_suppresses_canonical(existing_record),
            )
            return CorrectionResult(
                source=normalized_source,
                record_id=corrected_record.id,
                action=normalized_action,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                hidden_record_scope=effective_scope,
                status=corrected_record.status,
                reason=cleaned_reason,
                corrected_at=corrected_at,
                suppresses_canonical=_suppresses_canonical(corrected_record),
            )

        hidden_record, hidden_scope = _find_hidden_record(
            normalized_source,
            record_id,
            effective_scope=effective_scope,
            durable_scope=durable_scope,
        )
        _reject_protocol_record(hidden_record)
        suppresses_canonical = hidden_scope == "canonical"
        tombstone = writable_store.write_suppression_record(
            record_id=hidden_record.id,
            title=hidden_record.title,
            card=hidden_record.card or f"Suppressed {normalized_source} record.",
            body=f"Suppression marker for {normalized_source} record '{hidden_record.id}'.",
            type=hidden_record.type,
            links_to=[],
            comes_from=[hidden_record.id],
            correction_action=normalized_action,
            reason=cleaned_reason,
            corrected_at=corrected_at,
            suppresses_canonical=suppresses_canonical,
            metadata={
                "suppressed_record_source": normalized_source,
                "suppressed_record_scope": hidden_scope,
            },
        )
        return CorrectionResult(
            source=normalized_source,
            record_id=tombstone.id,
            action=normalized_action,
            requested_scope=requested_scope,
            effective_scope=effective_scope,
            hidden_record_scope=hidden_scope,
            status=tombstone.status,
            reason=cleaned_reason,
            corrected_at=corrected_at,
            suppresses_canonical=suppresses_canonical,
        )


def _normalize_source(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized in {"vault_note", "memory_trace"}:
        raise CorrectionRejected(f"Corrections are not supported for source '{normalized}'.")
    if normalized not in SUPPORTED_CORRECTION_SOURCES:
        raise CorrectionRejected(f"Unsupported correction source '{source}'.")
    return normalized


def _normalize_action(action: str) -> str:
    normalized = str(action or "").strip().lower()
    if normalized not in SUPPORTED_CORRECTION_ACTIONS:
        raise CorrectionRejected(f"Unsupported correction action '{action}'.")
    return normalized


def _normalize_scope(scope: str) -> str:
    normalized = str(scope or "current").strip().lower()
    if normalized not in SUPPORTED_CORRECTION_SCOPES:
        raise CorrectionRejected(f"Unsupported correction scope '{scope}'.")
    return normalized


def _effective_scope(
    requested_scope: str,
    *,
    runtime: dict[str, Any],
    has_active_experiment: bool,
) -> str:
    if requested_scope == "current":
        return "experiment" if str(runtime.get("scope") or "") == "experiment" else "durable"
    if requested_scope == "experiment" and not has_active_experiment:
        raise CorrectionRejected("Experiment-scoped corrections require an active experiment.")
    return requested_scope


def _store_for_scope(
    *,
    source: str,
    scope: str,
    durable_scope: dict[str, Any],
    runtime: dict[str, Any],
) -> Any:
    store_key = SOURCE_STORE_KEYS[source]
    if scope == "experiment":
        if str(runtime.get("scope") or "") != "experiment":
            raise CorrectionRejected("Experiment-scoped corrections require an active experiment.")
        return runtime[store_key]
    if scope == "durable":
        return durable_scope[store_key]
    raise CorrectionRejected(f"Unsupported correction scope '{scope}'.")


def _find_hidden_record(
    source: str,
    record_id: str,
    *,
    effective_scope: str,
    durable_scope: dict[str, Any],
) -> tuple[Any, str]:
    candidates: list[tuple[Any, str]] = []
    if effective_scope == "experiment":
        candidates.append((durable_scope[SOURCE_STORE_KEYS[source]], "durable"))
    candidates.append((durable_scope["canonical_scope"][SOURCE_STORE_KEYS[source]], "canonical"))
    for store, scope in candidates:
        record = _try_get(store, record_id)
        if record is not None:
            return record, scope
    raise FileNotFoundError(f"Saved item '{record_id}' was not found.")


def _try_get(store: Any, record_id: str) -> Any | None:
    try:
        return store.get(record_id)
    except FileNotFoundError:
        return None


def _reject_built_in_protocol(source: str, record_id: str) -> None:
    if source == "concept" and str(record_id or "").strip() in BUILT_IN_PROTOCOL_IDS:
        raise CorrectionRejected("Built-in protocols cannot be hidden with saved-item corrections.")


def _reject_protocol_record(record: Any) -> None:
    if str(getattr(record, "type", "") or "").strip().lower() == "protocol":
        raise CorrectionRejected("Protocols cannot be hidden with saved-item corrections.")


def _suppresses_canonical(record: Any) -> bool:
    metadata = getattr(record, "metadata", {}) if isinstance(getattr(record, "metadata", {}), dict) else {}
    return bool(metadata.get("suppresses_canonical"))


def _clean_reason(reason: str | None) -> str | None:
    cleaned = " ".join(str(reason or "").strip().split())
    return cleaned or None
