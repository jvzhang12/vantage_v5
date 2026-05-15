from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Any, Protocol

from vantage_v5.services.search import tokenize


SEMANTIC_ALIASES = {
    "agenda": {"calendar", "schedule", "plan"},
    "appointment": {"calendar", "event", "meeting"},
    "assignment": {"homework", "task", "deadline"},
    "automobile": {"car", "drive", "vehicle"},
    "bicycle": {"bike", "cycling", "route"},
    "bike": {"bicycle", "cycling", "route"},
    "calendar": {"agenda", "schedule", "event"},
    "car": {"automobile", "drive", "vehicle"},
    "checkin": {"meeting", "sync"},
    "cycling": {"bike", "bicycle", "route"},
    "deadline": {"due", "task", "assignment"},
    "draft": {"write", "compose", "document"},
    "due": {"deadline", "task"},
    "email": {"message", "correspondence", "draft"},
    "errand": {"grocery", "run", "store"},
    "event": {"calendar", "appointment", "schedule"},
    "exam": {"midterm", "test", "study"},
    "grocery": {"errand", "store", "shopping"},
    "homework": {"assignment", "task", "study"},
    "itinerary": {"travel", "trip", "route"},
    "meeting": {"appointment", "sync", "calendar"},
    "message": {"email", "correspondence", "draft"},
    "midterm": {"exam", "test", "study"},
    "note": {"memory", "record"},
    "paper": {"essay", "draft", "document"},
    "priority": {"focus", "important", "task"},
    "schedule": {"calendar", "agenda", "plan"},
    "shopping": {"grocery", "errand", "store"},
    "study": {"homework", "exam", "review"},
    "sync": {"meeting", "checkin"},
    "todo": {"task", "checklist"},
    "travel": {"trip", "itinerary", "route"},
    "trip": {"travel", "itinerary", "route"},
    "vehicle": {"car", "automobile", "drive"},
}


@dataclass(frozen=True, slots=True)
class VectorDocument:
    resource_id: str
    kind: str
    app: str
    title: str
    summary: str
    source: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VectorHit:
    resource_id: str
    similarity: float
    backend: str
    embedding_model: str


class VectorIndex(Protocol):
    def sync(self, documents: list[VectorDocument]) -> None:
        ...

    def query(self, text: str, *, limit: int = 16) -> list[VectorHit]:
        ...


class LocalHashEmbeddingProvider:
    model = "local-hash-token-v1"

    def embed(self, text: str) -> dict[str, float]:
        return dict(semantic_vector(text))


class SQLiteVectorIndex:
    backend = "sqlite-vector-json-v1"

    def __init__(self, path: Path, *, embedding_provider: LocalHashEmbeddingProvider | None = None) -> None:
        self.path = path
        self.embedding_provider = embedding_provider or LocalHashEmbeddingProvider()

    def sync(self, documents: list[VectorDocument]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            self._ensure_schema(conn)
            for document in documents:
                self._upsert(conn, document)

    def query(self, text: str, *, limit: int = 16) -> list[VectorHit]:
        query_vector = self.embedding_provider.embed(text)
        if not query_vector:
            return []
        try:
            with self._connect() as conn:
                self._ensure_schema(conn)
                rows = conn.execute(
                    "select resource_id, embedding_json from vector_resources"
                ).fetchall()
        except sqlite3.Error:
            return []
        hits: list[VectorHit] = []
        for resource_id, embedding_json in rows:
            resource_vector = _decode_embedding(embedding_json)
            similarity = cosine_similarity(query_vector, resource_vector)
            if similarity <= 0:
                continue
            hits.append(
                VectorHit(
                    resource_id=str(resource_id),
                    similarity=round(similarity, 6),
                    backend=self.backend,
                    embedding_model=self.embedding_provider.model,
                )
            )
        hits.sort(key=lambda item: item.similarity, reverse=True)
        return hits[:limit]

    def rebuild(self, documents: list[VectorDocument]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            self._ensure_schema(conn)
            conn.execute("delete from vector_resources")
            for document in documents:
                self._upsert(conn, document)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            create table if not exists vector_resources (
                resource_id text primary key,
                kind text not null,
                app text not null,
                title text not null,
                summary text not null,
                source text not null,
                content_hash text not null,
                embedding_model text not null,
                embedding_json text not null,
                metadata_json text not null,
                updated_at real not null
            )
            """
        )
        conn.execute("create index if not exists idx_vector_resources_kind on vector_resources(kind)")
        conn.execute("create index if not exists idx_vector_resources_app on vector_resources(app)")

    def _upsert(self, conn: sqlite3.Connection, document: VectorDocument) -> None:
        text = " ".join([document.title, document.summary, document.text]).strip()
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = conn.execute(
            "select content_hash, embedding_model from vector_resources where resource_id = ?",
            (document.resource_id,),
        ).fetchone()
        if existing and existing[0] == content_hash and existing[1] == self.embedding_provider.model:
            return
        embedding = self.embedding_provider.embed(text)
        conn.execute(
            """
            insert into vector_resources (
                resource_id, kind, app, title, summary, source, content_hash,
                embedding_model, embedding_json, metadata_json, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(resource_id) do update set
                kind = excluded.kind,
                app = excluded.app,
                title = excluded.title,
                summary = excluded.summary,
                source = excluded.source,
                content_hash = excluded.content_hash,
                embedding_model = excluded.embedding_model,
                embedding_json = excluded.embedding_json,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                document.resource_id,
                document.kind,
                document.app,
                document.title,
                document.summary,
                document.source,
                content_hash,
                self.embedding_provider.model,
                json.dumps(embedding, sort_keys=True),
                json.dumps(document.metadata, sort_keys=True, default=str),
                time.time(),
            ),
        )


def semantic_vector(*values: Any) -> Counter[str]:
    vector: Counter[str] = Counter()
    for value in values:
        text = " ".join(str(value or "").strip().split())
        if not text:
            continue
        for token in tokenize(text):
            vector[token] += 1.0
            for alias in SEMANTIC_ALIASES.get(token, ()):
                vector[alias] += 0.72
    return vector


def cosine_similarity(left: dict[str, float] | Counter[str], right: dict[str, float] | Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    if not overlap:
        return 0.0
    numerator = sum(float(left[token]) * float(right[token]) for token in overlap)
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left.values()))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


def _decode_embedding(value: Any) -> dict[str, float]:
    try:
        raw = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    embedding: dict[str, float] = {}
    for key, item in raw.items():
        try:
            embedding[str(key)] = float(item)
        except (TypeError, ValueError):
            continue
    return embedding
