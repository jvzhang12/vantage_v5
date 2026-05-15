from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ProductScope:
    scope: str
    durability: str
    is_canonical: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "durability": self.durability,
            "is_canonical": self.is_canonical,
        }


def product_scope_for_record(
    record: Any,
    *,
    canonical_root: Path | None = None,
    experiment_root: Path | None = None,
    fallback_scope: str = "durable",
) -> ProductScope:
    source = str(getattr(record, "source", "") or "").strip().lower()
    metadata = getattr(record, "metadata", None)
    metadata = metadata if isinstance(metadata, dict) else {}
    path = getattr(record, "path", None)

    if source == "vault_note":
        return ProductScope(scope="reference", durability="read_only")
    if _path_is_relative_to(path, canonical_root):
        return ProductScope(scope="canonical", durability="durable", is_canonical=True)
    if _path_is_relative_to(path, experiment_root):
        return ProductScope(scope="experiment", durability="temporary")
    if source == "memory_trace":
        trace_scope = _clean_scope(metadata.get("trace_scope") or metadata.get("scope"))
        if trace_scope == "experiment":
            return ProductScope(scope="experiment", durability="temporary")
        if trace_scope == "canonical":
            return ProductScope(scope="canonical", durability="durable", is_canonical=True)
        if trace_scope:
            return ProductScope(scope=trace_scope, durability=_durability_for_scope(trace_scope))

    scope = _clean_scope(fallback_scope) or "durable"
    if scope == "reference":
        scope = "durable"
    return ProductScope(
        scope=scope,
        durability=_durability_for_scope(scope),
        is_canonical=scope == "canonical",
    )


def builtin_product_scope() -> ProductScope:
    return ProductScope(scope="builtin", durability="builtin")


def operational_product_scope() -> ProductScope:
    return ProductScope(scope="operational", durability="live")


def transient_product_scope() -> ProductScope:
    return ProductScope(scope="visible", durability="transient")


def _durability_for_scope(scope: str) -> str:
    if scope == "experiment":
        return "temporary"
    if scope == "builtin":
        return "builtin"
    if scope == "operational":
        return "live"
    if scope == "visible":
        return "transient"
    if scope == "reference":
        return "read_only"
    return "durable"


def _clean_scope(value: Any) -> str:
    return str(value or "").strip().lower()


def _path_is_relative_to(path: Any, root: Path | None) -> bool:
    if path is None or root is None:
        return False
    try:
        Path(path).resolve().relative_to(root.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False
