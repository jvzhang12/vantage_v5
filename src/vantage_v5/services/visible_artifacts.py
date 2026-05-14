from __future__ import annotations

import json
from typing import Any


MAX_VISIBLE_ARTIFACTS = 4
MAX_CONTENT_CHARS = 12_000
MAX_DATA_CHARS = 18_000


def normalize_visible_artifacts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    artifacts: list[dict[str, Any]] = []
    for raw in value[:MAX_VISIBLE_ARTIFACTS]:
        if not isinstance(raw, dict):
            continue
        artifact_id = _text(raw.get("id")) or f"visible-artifact-{len(artifacts) + 1}"
        kind = _text(raw.get("kind")) or "artifact"
        title = _text(raw.get("title")) or _humanize(kind)
        content = _text(raw.get("content") or raw.get("content_markdown") or raw.get("contentMarkdown"))
        if not content:
            continue
        artifact = {
            "id": artifact_id[:160],
            "kind": kind[:80],
            "title": title[:180],
            "summary": _text(raw.get("summary"))[:500],
            "content": _truncate(content, MAX_CONTENT_CHARS),
            "source": _text(raw.get("source"))[:120] or "visible_user_view",
            "active": raw.get("active") is not False,
        }
        source_refs = raw.get("source_refs") or raw.get("sourceRefs")
        if isinstance(source_refs, list):
            artifact["source_refs"] = [_shallow_dict(ref) for ref in source_refs[:8] if isinstance(ref, dict)]
        data = raw.get("data")
        if isinstance(data, dict):
            artifact["data"] = _truncate_json(data, MAX_DATA_CHARS)
        artifacts.append(artifact)
    return artifacts


def visible_artifacts_prompt_payload(artifacts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return normalize_visible_artifacts(artifacts or [])


def visible_artifacts_have_context(artifacts: list[dict[str, Any]] | None) -> bool:
    return any(_text(artifact.get("content")) for artifact in artifacts or [] if isinstance(artifact, dict))


def _shallow_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key)[:80]: _text(raw)[:300] if not isinstance(raw, (int, float, bool)) else raw
        for key, raw in value.items()
        if raw is not None
    }


def _truncate_json(value: dict[str, Any], limit: int) -> dict[str, Any] | str:
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {}
    if len(serialized) <= limit:
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError:
            return serialized
        return parsed if isinstance(parsed, dict) else serialized
    return _truncate(serialized, limit)


def _truncate(value: str, limit: int) -> str:
    text = _text(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}\n...[truncated]"


def _humanize(value: str) -> str:
    return _text(value).replace("_", " ").replace("-", " ").title() or "Artifact"


def _text(value: Any) -> str:
    return str(value or "").strip()
