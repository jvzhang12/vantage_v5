from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from openai import OpenAI

from vantage_v5.services.search import CandidateMemory
from vantage_v5.services.search import tokenize
from vantage_v5.storage.markdown_store import slugify
from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass(slots=True)
class MetaDecision:
    action: str
    rationale: str
    title: str | None = None
    card: str | None = None
    body: str | None = None
    target_concept_id: str | None = None
    links_to: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "rationale": self.rationale,
            "title": self.title,
            "card": self.card,
            "body": self.body,
            "target_concept_id": self.target_concept_id,
            "links_to": self.links_to or [],
        }


class MetaService:
    def __init__(self, *, model: str, openai_api_key: str | None) -> None:
        self.model = model
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    def decide(
        self,
        *,
        user_message: str,
        assistant_message: str,
        workspace: WorkspaceDocument,
        vetted_items: list[CandidateMemory],
        history: list[dict[str, str]],
        memory_mode: str,
        workspace_update: dict[str, Any] | None = None,
    ) -> MetaDecision:
        if _is_pending_whiteboard_update(workspace_update):
            return MetaDecision(
                action="no_op",
                rationale=(
                    "Pending whiteboard offers and drafts stay inspectable until the user explicitly "
                    "applies or saves them on a later turn. A same-turn save or remember request does "
                    "not make that draft durable."
                ),
            )
        if memory_mode == "dont_save":
            return MetaDecision(
                action="no_op",
                rationale="User explicitly disabled memory writes for this turn.",
            )
        if self.client:
            try:
                return self._openai_decide(
                    user_message=user_message,
                    assistant_message=assistant_message,
                    workspace=workspace,
                    vetted_items=vetted_items,
                    history=history,
                    memory_mode=memory_mode,
                )
            except Exception:
                pass
        return self._fallback_decide(
            user_message=user_message,
            assistant_message=assistant_message,
            workspace=workspace,
            vetted_items=vetted_items,
            memory_mode=memory_mode,
        )

    def _openai_decide(
        self,
        *,
        user_message: str,
        assistant_message: str,
        workspace: WorkspaceDocument,
        vetted_items: list[CandidateMemory],
        history: list[dict[str, str]],
        memory_mode: str,
    ) -> MetaDecision:
        concept_ids = [item.id for item in vetted_items if item.source == "concept"]
        concept_items = [item for item in vetted_items if item.source == "concept"]
        source_notes = [
            {"id": item.id, "title": item.title, "path": item.path}
            for item in vetted_items
            if item.source == "vault_note"
        ]
        payload = {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "memory_mode": memory_mode,
            "workspace": {
                "workspace_id": workspace.workspace_id,
                "title": workspace.title,
                "content_excerpt": workspace.content[:1200],
            },
            "recent_history": history[-6:],
            "vetted_items": [item.to_dict() for item in vetted_items],
            "related_concept_ids": concept_ids,
            "source_notes": source_notes,
            "allowed_actions": [
                "no_op",
                "create_concept",
                "create_memory",
                "promote_workspace_to_artifact",
            ],
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage V5 meta call. "
                "Decide the highest-value graph action for this turn relative to the existing knowledge graph. "
                "Create_concept is the default durable action for stable, reusable, or generalizable turns when the turn crystallizes knowledge that should live in the concept graph. "
                "Concepts are timeless, generalizable knowledge. "
                "Memories are retained user, project, or session facts. "
                "Artifacts are concrete outputs like drafts, plans, essays, or workspace snapshots. "
                "The only write actions available in this phase are create_concept, create_memory, and promote_workspace_to_artifact. "
                "Only create a concept when the content is clearly timeless and generalizable. "
                "When a new concept is closely related to vetted concepts but still distinct, prefer create_concept with links_to pointing at the nearby concept neighborhood instead of suppressing it. "
                "Reserve no_op for near-duplicate restatements or clearly non-durable turns. "
                "Only create a memory when the user explicitly asks to remember or save something durable. "
                "Only promote a workspace to an artifact when the workspace itself is the thing being saved. "
                "When deciding between create_concept and no_op for a stable knowledge turn, bias toward create_concept. "
                "Choose no_op only when the turn is clearly transient, workspace-only, not durable enough to matter later, or would create a near-duplicate of a vetted concept."
            ),
            input=json.dumps(payload),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "meta_decision",
                    "strict": False,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": [
                                    "no_op",
                                    "create_concept",
                                    "create_memory",
                                    "promote_workspace_to_artifact",
                                ],
                            },
                            "rationale": {"type": "string"},
                            "title": {"type": ["string", "null"]},
                            "card": {"type": ["string", "null"]},
                            "body": {"type": ["string", "null"]},
                            "target_concept_id": {"type": ["string", "null"]},
                            "links_to": {
                                "type": ["array", "null"],
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "action",
                            "rationale",
                            "title",
                            "card",
                            "body",
                            "target_concept_id",
                            "links_to",
                        ],
                    },
                }
            },
        )
        result = json.loads(response.output_text)
        related_links = _related_concept_links(
            concept_items,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        duplicate_concept = _duplicate_concept_id(
            concept_items,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        requested_links = _validated_link_targets(result.get("links_to") or [], concept_ids)
        merged_links = list(dict.fromkeys([*requested_links, *related_links]))[:3]

        if result["action"] == "create_concept" and duplicate_concept is not None:
            return MetaDecision(
                action="no_op",
                rationale=(
                    f"{result['rationale']} A near-duplicate concept already exists "
                    f"({duplicate_concept}), so the write was suppressed."
                ).strip(),
                title=result.get("title"),
                card=result.get("card"),
                body=result.get("body"),
                target_concept_id=result.get("target_concept_id"),
                links_to=merged_links,
            )
        return MetaDecision(
            action=result["action"],
            rationale=result["rationale"],
            title=result.get("title"),
            card=result.get("card"),
            body=result.get("body"),
            target_concept_id=result.get("target_concept_id"),
            links_to=merged_links if result["action"] == "create_concept" else requested_links,
        )

    @staticmethod
    def _fallback_decide(
        *,
        user_message: str,
        assistant_message: str,
        workspace: WorkspaceDocument,
        vetted_items: list[CandidateMemory],
        memory_mode: str,
    ) -> MetaDecision:
        lowered = user_message.lower()
        concept_items = [item for item in vetted_items if item.source == "concept"]
        concept_links = _related_concept_links(
            concept_items,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        duplicate_concept = _duplicate_concept_id(
            concept_items,
            user_message=user_message,
            assistant_message=assistant_message,
        )

        if "save as concept" in lowered or "make this a concept" in lowered or "turn this into a concept" in lowered:
            if duplicate_concept is not None:
                return MetaDecision(
                    action="no_op",
                    rationale=(
                        f"A near-duplicate concept already exists ({duplicate_concept}), so no duplicate concept was created."
                    ),
                    links_to=concept_links,
                )
            return MetaDecision(
                action="create_concept",
                rationale="The user explicitly asked to save this as a timeless concept.",
                title=_title_from_message(user_message),
                card=_sentence_card_from_text(assistant_message, fallback=user_message),
                body=_body_from_turn(user_message, assistant_message),
                links_to=concept_links,
            )

        if "save as artifact" in lowered or "promote workspace" in lowered:
            return MetaDecision(
                action="promote_workspace_to_artifact",
                rationale="The user explicitly asked to promote the shared workspace into a saved artifact.",
                title=workspace.title,
                card=_sentence_card_from_text(workspace.content, fallback=workspace.title),
                body=workspace.content,
                links_to=concept_links,
            )

        if memory_mode == "remember":
            return MetaDecision(
                action="create_memory",
                rationale="The user explicitly asked to remember this turn.",
                title=_title_from_message(user_message),
                card=_sentence_card_from_text(assistant_message, fallback=user_message),
                body=_body_from_turn(user_message, assistant_message),
                links_to=concept_links,
            )

        explicit_memory_phrases = {
            "remember this",
            "save this",
            "save this as memory",
        }
        if any(marker in lowered for marker in explicit_memory_phrases):
            return MetaDecision(
                action="create_memory",
                rationale="The user explicitly asked for this information to become saved memory.",
                title=_title_from_message(user_message),
                card=_sentence_card_from_text(assistant_message, fallback=user_message),
                body=_body_from_turn(user_message, assistant_message),
                links_to=concept_links,
            )

        if duplicate_concept is not None:
            return MetaDecision(
                action="no_op",
                rationale=f"A near-duplicate concept already exists ({duplicate_concept}), so no duplicate concept was created.",
                links_to=concept_links,
            )

        if _looks_like_generalizable_turn(user_message=user_message, assistant_message=assistant_message):
            return MetaDecision(
                action="create_concept",
                rationale="The turn reads like reusable knowledge, so it should be preserved as a concept.",
                title=_title_from_message(user_message),
                card=_sentence_card_from_text(assistant_message, fallback=user_message),
                body=_body_from_turn(user_message, assistant_message),
                links_to=concept_links,
            )

        return MetaDecision(
            action="no_op",
            rationale="No durable graph change was confident enough for this turn.",
        )


def _title_from_message(message: str) -> str:
    cleaned = message.strip().rstrip("?.!")
    if len(cleaned) <= 80:
        return cleaned.title()
    return cleaned[:77].rstrip() + "..."


def _is_pending_whiteboard_update(workspace_update: dict[str, Any] | None) -> bool:
    if workspace_update is None:
        return False
    return workspace_update.get("type") in {"offer_whiteboard", "draft_whiteboard"}


def _sentence_card_from_text(text: str, *, fallback: str) -> str:
    compact = " ".join(text.strip().split())
    if not compact:
        compact = " ".join(fallback.strip().split())
    if "." in compact:
        sentence = compact.split(".", 1)[0].strip() + "."
    else:
        sentence = compact[:157].rstrip()
        if sentence and not sentence.endswith("."):
            sentence += "."
    return sentence[:180]


def _body_from_turn(user_message: str, assistant_message: str) -> str:
    return (
        "## Source Turn\n\n"
        f"User: {user_message.strip()}\n\n"
        "## Assistant Response\n\n"
        f"{assistant_message.strip()}\n"
    )


def _looks_like_generalizable_turn(*, user_message: str, assistant_message: str) -> bool:
    lowered = user_message.lower()
    assistant_lowered = assistant_message.lower()

    if _contains_any(
        lowered,
        (
            "draft ",
            "write ",
            "compose ",
            "email",
            "whiteboard",
            "artifact",
            "essay",
            "outline",
            "proposal",
            "memo",
            "report",
            "shopping list",
            "itinerary",
            "road trip",
            "letter",
            "rewrite ",
            "summarize ",
        ),
    ):
        return False

    if _contains_any(
        lowered,
        (
            "save as concept",
            "make this a concept",
            "turn this into a concept",
            "what is ",
            "what are ",
            "how does ",
            "how do ",
            "why does ",
            "why do ",
            "explain ",
            "compare ",
            "difference between ",
            "rules of ",
            "rule of ",
            "best way to ",
            "how to ",
            "what should ",
            "what makes ",
            "strategy",
            "tradeoff",
            "principle",
        ),
    ):
        return True

    return _contains_any(
        assistant_lowered,
        (
            "here are",
            "in general",
            "typically",
            "usually",
            "the rules are",
            "this means",
            "tradeoffs",
            "best fit",
            "best guess",
            "a concept is",
            "the concept is",
            "one way to think",
        ),
    )


def _duplicate_concept_id(
    concept_items: list[CandidateMemory],
    *,
    user_message: str,
    assistant_message: str,
) -> str | None:
    proposed_title = _title_from_message(user_message)
    proposed_title_slug = slugify(proposed_title)
    proposed_card = _sentence_card_from_text(assistant_message, fallback=user_message)
    normalized_card = _normalized_phrase(proposed_card)

    for item in concept_items:
        if slugify(item.title) == proposed_title_slug:
            return item.id
        if item.card and _normalized_phrase(item.card) == normalized_card:
            return item.id
    return None


def _related_concept_links(
    concept_items: list[CandidateMemory],
    *,
    user_message: str,
    assistant_message: str,
    limit: int = 3,
) -> list[str]:
    if not concept_items:
        return []
    user_tokens = tokenize(user_message)
    ranked: list[tuple[int, str]] = []
    for item in concept_items:
        concept_tokens = tokenize(f"{item.title} {item.card} {item.body[:400]}")
        user_overlap = len(user_tokens & concept_tokens)
        user_phrase_match = _contains_any(
            user_message.lower(),
            (_normalized_phrase(item.title), _normalized_phrase(item.card)),
        )

        if user_overlap >= 1:
            ranked.append((user_overlap * 10, item.id))
            continue
        if user_phrase_match:
            ranked.append((9, item.id))
            continue
    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    return [item_id for _, item_id in ranked[:limit]]


def _validated_link_targets(links_to: list[str], allowed_ids: list[str]) -> list[str]:
    allowed = set(allowed_ids)
    ordered: list[str] = []
    for link in links_to:
        normalized = str(link).strip()
        if normalized and normalized in allowed and normalized not in ordered:
            ordered.append(normalized)
    return ordered[:3]


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle and needle in haystack for needle in needles)


def _normalized_phrase(text: str) -> str:
    return " ".join(text.lower().split())
