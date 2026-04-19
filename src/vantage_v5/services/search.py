from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol
import re


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
TOKEN_ALIASES = {
    "mechanism": {"mechanistic"},
    "mechanistic": {"mechanism"},
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "help",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "we",
    "with",
}


class SearchableRecord(Protocol):
    id: str
    title: str
    type: str
    card: str
    searchable_text: str
    body: str
    source: str
    trust: str
    path_hint: str | None


@dataclass(slots=True)
class CandidateMemory:
    id: str
    title: str
    type: str
    card: str
    score: float
    reason: str
    source: str
    trust: str
    body: str = ""
    path: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "card": self.card,
            "score": self.score,
            "reason": self.reason,
            "source": self.source,
            "source_label": _source_label(self.source),
            "trust": self.trust,
            "body": self.body,
            "path": self.path,
        }


CandidateConcept = CandidateMemory


def tokenize(text: str) -> set[str]:
    tokens = {variant for token in TOKEN_RE.findall(text) for variant in _token_variants(token.lower())}
    filtered = {token for token in tokens if token not in STOPWORDS}
    return filtered or tokens


class ConceptSearchService:
    def search(
        self,
        *,
        query: str,
        concepts: list[SearchableRecord] | None = None,
        records: list[SearchableRecord] | None = None,
        limit: int = 10,
    ) -> list[CandidateMemory]:
        pool = records if records is not None else concepts or []
        return self._search_records(query=query, records=pool, limit=limit)

    def search_memory(
        self,
        *,
        query: str,
        saved_note_records: list[SearchableRecord],
        vault_records: list[SearchableRecord],
        limit: int = 12,
    ) -> list[CandidateMemory]:
        saved_notes = self._search_records(query=query, records=saved_note_records, limit=limit)
        vault = self._search_records(query=query, records=vault_records, limit=limit)
        return _shape_merged_candidates(saved_notes + vault, limit=limit)

    def search_context(
        self,
        *,
        query: str,
        memory_trace_records: list[SearchableRecord] | None = None,
        concept_records: list[SearchableRecord],
        saved_note_records: list[SearchableRecord],
        vault_records: list[SearchableRecord],
        limit: int = 16,
    ) -> list[CandidateMemory]:
        memory_trace = self._search_records(query=query, records=memory_trace_records or [], limit=limit)
        concepts = self._search_records(query=query, records=concept_records, limit=limit)
        saved_notes = self._search_records(query=query, records=saved_note_records, limit=limit)
        vault = self._search_records(query=query, records=vault_records, limit=limit)
        return _shape_merged_candidates(memory_trace + concepts + saved_notes + vault, limit=limit)

    def _search_records(
        self,
        *,
        query: str,
        records: list[SearchableRecord],
        limit: int,
    ) -> list[CandidateMemory]:
        query_tokens = tokenize(query)
        query_phrase = _normalized_phrase(query)
        candidates: list[CandidateMemory] = []

        for record in records:
            title_tokens = tokenize(record.title)
            card_tokens = tokenize(record.card)
            body_tokens = tokenize(record.body[:1000])
            path_text = _record_path_text(record)
            path_tokens = tokenize(path_text)
            links_text = _record_joined_text(getattr(record, "links_to", []))
            lineage_text = _record_joined_text(getattr(record, "comes_from", []))
            links_tokens = tokenize(links_text)
            lineage_tokens = tokenize(lineage_text)
            context_tokens = tokenize(record.searchable_text[:1600])

            title_overlap = len(query_tokens & title_tokens)
            card_overlap = len(query_tokens & card_tokens)
            body_overlap = len(query_tokens & body_tokens)
            path_overlap = len(query_tokens & path_tokens)
            links_overlap = len(query_tokens & links_tokens)
            lineage_overlap = len(query_tokens & lineage_tokens)
            context_overlap = len(query_tokens & context_tokens)

            signal_score = (
                (title_overlap * 3.0)
                + (card_overlap * 2.2)
                + (path_overlap * 2.15)
                + (links_overlap * 1.8)
                + (lineage_overlap * 1.55)
                + (body_overlap * 1.0)
                + (context_overlap * 0.35)
            )
            signal_score += _phrase_bonus(query_phrase, record.title, weight=1.65)
            signal_score += _phrase_bonus(query_phrase, record.card, weight=1.2)
            signal_score += _phrase_bonus(query_phrase, path_text, weight=1.55)
            signal_score += _phrase_bonus(query_phrase, links_text, weight=0.9)
            signal_score += _phrase_bonus(query_phrase, lineage_text, weight=0.9)
            signal_score += _phrase_bonus(query_phrase, record.body, weight=0.45)
            signal_score += _phrase_bonus(query_phrase, record.searchable_text, weight=0.45)
            if signal_score <= 0:
                continue
            score = signal_score + _source_bonus(record.source)

            candidates.append(
                CandidateMemory(
                    id=record.id,
                    title=record.title,
                    type=record.type,
                    card=record.card,
                    score=round(score, 4),
                    reason=(
                        f"{record.source}: title={title_overlap} "
                        f"card={card_overlap} path={path_overlap} "
                        f"links={links_overlap} lineage={lineage_overlap} "
                        f"body={body_overlap} context={context_overlap}"
                    ),
                    source=record.source,
                    trust=record.trust,
                    body=record.body,
                    path=record.path_hint,
                )
            )

        candidates.sort(key=lambda item: (item.score, _source_priority(item.source)), reverse=True)
        return candidates[:limit]


def _token_variants(token: str) -> set[str]:
    variants = {token, *TOKEN_ALIASES.get(token, set())}
    if len(token) > 5 and token.endswith("ing"):
        stem = token[:-3]
        variants.add(stem)
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            variants.add(stem[:-1])
    if len(token) > 4 and token.endswith("ies"):
        variants.add(f"{token[:-3]}y")
    if len(token) > 4 and token.endswith("es") and not token.endswith("ses"):
        variants.add(token[:-2])
    if len(token) > 4 and token.endswith("s") and not token.endswith("ics"):
        variants.add(token[:-1])
    return {variant for variant in variants if variant}


def _source_bonus(source: str) -> float:
    return {
        "concept": 0.35,
        "memory": 0.2,
        "memory_trace": 0.18,
        "artifact": 0.15,
        "vault_note": 0.0,
    }.get(source, 0.0)


def _source_priority(source: str) -> int:
    return {
        "concept": 3,
        "memory": 2,
        "memory_trace": 2,
        "artifact": 2,
        "vault_note": 1,
    }.get(source, 0)


def _shape_merged_candidates(candidates: list[CandidateMemory], *, limit: int) -> list[CandidateMemory]:
    if limit <= 0 or not candidates:
        return []

    ordered = sorted(
        candidates,
        key=lambda item: (item.score, _source_priority(item.source), item.title.lower(), item.id),
        reverse=True,
    )
    source_counts: Counter[str] = Counter()
    shaped: list[tuple[float, float, int, int, CandidateMemory]] = []
    for index, candidate in enumerate(ordered):
        repeat_index = source_counts[candidate.source]
        source_counts[candidate.source] += 1
        adjusted_score = candidate.score - (_source_repeat_penalty(candidate.source) * repeat_index)
        shaped.append(
            (
                adjusted_score,
                candidate.score,
                _source_priority(candidate.source),
                -index,
                candidate,
            )
        )

    shaped.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    return [candidate for *_prefix, candidate in shaped[:limit]]


def _source_repeat_penalty(source: str) -> float:
    return {
        "concept": 0.24,
        "memory": 0.18,
        "memory_trace": 0.18,
        "artifact": 0.18,
        "vault_note": 0.12,
    }.get(source, 0.1)


def _source_label(source: str) -> str:
    return {
        "concept": "Concept KB",
        "memory": "Saved memory",
        "memory_trace": "Memory Trace",
        "artifact": "Saved artifact",
        "vault_note": "Reference note",
    }.get(source, "Record")


def _phrase_bonus(query_phrase: str, text: str, *, weight: float) -> float:
    if not query_phrase:
        return 0.0
    normalized = _normalized_phrase(text)
    if not normalized or query_phrase not in normalized:
        return 0.0
    return weight


def _normalized_phrase(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def _record_joined_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    if value is None:
        return ""
    return str(value).strip()


def _record_path_text(record: SearchableRecord) -> str:
    parts = [
        _record_joined_text(getattr(record, "relative_path", "")),
        _record_joined_text(getattr(record, "folder", "")),
        _record_joined_text(getattr(record, "path_hint", "")),
    ]
    return " ".join(part for part in parts if part)
