from __future__ import annotations

from typing import Any


def overlay_records(*record_lists: list[Any]) -> list[Any]:
    """Return records in precedence order, hiding lower-priority duplicates."""

    merged: dict[tuple[str, str], Any] = {}
    suppressed: set[tuple[str, str]] = set()
    for records in record_lists:
        for record in records:
            key = _record_key(record)
            if key is None:
                continue
            if _is_suppression_record(record):
                suppressed.add(key)
                continue
            if key in suppressed or key in merged:
                continue
            merged[key] = record
    return list(merged.values())


class ConceptOverlayStore:
    def __init__(self, *stores: Any) -> None:
        self.stores = tuple(store for store in stores if store is not None)

    def list_concepts(self) -> list[Any]:
        return overlay_records(
            *(store.list_concepts() for store in self.stores)
        )

    def get(self, record_id: str) -> Any:
        return _get_first_available(record_id, self.stores)


class MemoryOverlayStore:
    def __init__(self, *stores: Any) -> None:
        self.stores = tuple(store for store in stores if store is not None)

    def list_memories(self) -> list[Any]:
        return overlay_records(
            *(store.list_memories() for store in self.stores)
        )

    def get(self, record_id: str) -> Any:
        return _get_first_available(record_id, self.stores)


class ArtifactOverlayStore:
    def __init__(self, *stores: Any) -> None:
        self.stores = tuple(store for store in stores if store is not None)

    def list_artifacts(self) -> list[Any]:
        return overlay_records(
            *(store.list_artifacts() for store in self.stores)
        )

    def get(self, record_id: str) -> Any:
        return _get_first_available(record_id, self.stores)


def _get_first_available(record_id: str, stores: tuple[Any, ...]) -> Any:
    suppressed = False
    last_error: FileNotFoundError | None = None
    for store in stores:
        try:
            record = store.get(record_id)
        except FileNotFoundError as exc:
            last_error = exc
            continue
        if _is_suppression_record(record):
            suppressed = True
            break
        return record
    if suppressed:
        raise FileNotFoundError(f"Saved item '{record_id}' is hidden by a user override.")
    if last_error is not None:
        raise last_error
    raise FileNotFoundError(f"Saved item '{record_id}' was not found.")


def _record_key(record: Any) -> tuple[str, str] | None:
    source = str(getattr(record, "source", "") or "").strip()
    record_id = str(getattr(record, "id", "") or "").strip()
    if not source or not record_id:
        return None
    return (source, record_id)


def _is_suppression_record(record: Any) -> bool:
    status = str(getattr(record, "status", "") or "").strip().lower()
    metadata = getattr(record, "metadata", {}) if isinstance(getattr(record, "metadata", {}), dict) else {}
    return status in {"hidden", "suppressed"} or bool(metadata.get("suppresses_canonical"))
