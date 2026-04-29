from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from openai import OpenAI

from vantage_v5.services.search import CandidateMemory
from vantage_v5.storage.markdown_store import MarkdownRecord


SUPPORTED_PROTOCOL_KINDS = {"email", "research_paper", "scenario_lab"}
BUILT_IN_PROTOCOLS: dict[str, dict[str, Any]] = {
    "scenario_lab": {
        "id": "scenario-lab-protocol",
        "title": "Scenario Lab Protocol",
        "card": "Use first-principles, counterfactual, causal, and tradeoff reasoning when comparing scenario branches.",
        "body": (
            "## Protocol\n\n"
            "Use this protocol whenever Vantage compares alternatives, explores branches, or runs Scenario Lab.\n\n"
            "## Reasoning Guidance\n\n"
            "- Start from first-principles reasoning: identify the core objective, constraints, and non-negotiables.\n"
            "- Use counterfactual reasoning: make each branch change a meaningful assumption, not just a label.\n"
            "- Trace causal mechanisms: explain why first-order and second-order effects follow.\n"
            "- Surface tradeoffs: name what each branch gains, risks, and gives up.\n"
            "- Make assumptions explicit so the comparison is inspectable and revisable.\n\n"
            "## Output Requirements\n\n"
            "- State shared assumptions before branch-specific changes.\n"
            "- Keep branches decision-useful and mutually distinct.\n"
            "- Include risks, open questions, and a practical recommendation.\n"
        ),
        "variables": {
            "reasoning_lenses": [
                "first-principles reasoning",
                "counterfactual reasoning",
                "causal mechanism tracing",
                "tradeoff analysis",
                "assumption surfacing",
            ],
            "default_surface": "scenario_lab",
        },
        "applies_to": ["scenario_lab", "scenario comparison", "what-if analysis", "decision support"],
    }
}


@dataclass(slots=True)
class ProtocolWrite:
    protocol_id: str
    protocol_kind: str
    title: str
    card: str
    body: str
    variables: dict[str, Any]
    applies_to: list[str]
    metadata: dict[str, Any]


@dataclass(slots=True)
class ProtocolInterpretation:
    protocol_write: ProtocolWrite | None = None
    recall_protocol_kinds: list[str] | None = None
    rationale: str = ""


class ProtocolInterpreter:
    def __init__(self, *, model: str, openai_api_key: str | None) -> None:
        self.model = model
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    def interpret(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        existing_protocols: list[MarkdownRecord],
    ) -> ProtocolInterpretation:
        if self.client is None:
            return ProtocolInterpretation(rationale="No model client is configured for protocol interpretation.")
        try:
            return self._openai_interpret(
                message=message,
                history=history,
                existing_protocols=existing_protocols,
            )
        except Exception:
            return ProtocolInterpretation(rationale="Protocol interpretation failed; no protocol action was taken.")

    def _openai_interpret(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        existing_protocols: list[MarkdownRecord],
    ) -> ProtocolInterpretation:
        protocol_payload = [
            {
                "id": record.id,
                "title": record.title,
                "protocol_kind": record.metadata.get("protocol_kind"),
                "variables": record.metadata.get("variables") or {},
                "applies_to": record.metadata.get("applies_to") or [],
                "card": record.card,
            }
            for record in existing_protocols
            if record.type == "protocol"
        ]
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage protocol interpreter. "
                "Interpret whether this turn should update a reusable protocol, recall an existing protocol, both, or neither. "
                "Protocols are user-modifiable instructions for recurring work types such as email drafting, research-paper drafting, or Scenario Lab reasoning. "
                "Do not update a protocol for a one-off draft edit unless the user is setting or changing a general preference. "
                "If the user asks to draft, revise, or polish work that matches an existing protocol, include that protocol kind in recall_protocol_kinds. "
                "If the user sets a general preference such as email signature, tone, formatting, or research-paper structure, return upsert_protocol with structured variables. "
                "Turn-specific overrides should not become protocols unless the user frames them as reusable. "
                "Only use supported protocol kinds: email, research_paper, scenario_lab."
            ),
            input=json.dumps(
                {
                    "user_message": message,
                    "recent_chat": history[-6:],
                    "existing_protocols": protocol_payload,
                    "supported_protocol_kinds": sorted(SUPPORTED_PROTOCOL_KINDS),
                }
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "protocol_interpretation",
                    "strict": False,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["none", "upsert_protocol"],
                            },
                            "protocol_kind": {
                                "type": ["string", "null"],
                                "enum": ["email", "research_paper", "scenario_lab", None],
                            },
                            "variables": {
                                "type": ["object", "null"],
                                "additionalProperties": True,
                            },
                            "applies_to": {
                                "type": ["array", "null"],
                                "items": {"type": "string"},
                            },
                            "recall_protocol_kinds": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["email", "research_paper", "scenario_lab"],
                                },
                            },
                            "rationale": {"type": "string"},
                        },
                        "required": [
                            "action",
                            "protocol_kind",
                            "variables",
                            "applies_to",
                            "recall_protocol_kinds",
                            "rationale",
                        ],
                    },
                }
            },
        )
        result = json.loads(response.output_text)
        protocol_kind = _supported_protocol_kind(result.get("protocol_kind"))
        recall_kinds = _supported_protocol_kinds(result.get("recall_protocol_kinds") or [])
        protocol_write = None
        if result.get("action") == "upsert_protocol" and protocol_kind is not None:
            protocol_write = build_protocol_write_from_interpretation(
                protocol_kind=protocol_kind,
                variables=result.get("variables") if isinstance(result.get("variables"), dict) else {},
                applies_to=result.get("applies_to") if isinstance(result.get("applies_to"), list) else [],
                source_instruction=message,
                existing_protocols=existing_protocols,
            )
            if protocol_kind not in recall_kinds:
                recall_kinds = [protocol_kind, *recall_kinds]
        return ProtocolInterpretation(
            protocol_write=protocol_write,
            recall_protocol_kinds=recall_kinds,
            rationale=str(result.get("rationale") or "").strip(),
        )


def build_protocol_write_from_interpretation(
    *,
    protocol_kind: str,
    variables: dict[str, Any],
    applies_to: list[str],
    source_instruction: str,
    existing_protocols: list[MarkdownRecord],
) -> ProtocolWrite:
    existing = _find_protocol(existing_protocols, protocol_kind)
    merged_variables = _default_variables(protocol_kind)
    merged_variables.update(_protocol_variables(existing))
    merged_variables.update(_clean_variables(variables))
    clean_applies_to = _clean_string_list(applies_to) or _applies_to(protocol_kind)
    title = _protocol_title(protocol_kind)
    card = _protocol_card(protocol_kind, merged_variables)
    body = _protocol_body(
        protocol_kind=protocol_kind,
        variables=merged_variables,
        latest_instruction=source_instruction,
    )
    metadata = {
        "source_instruction": " ".join(source_instruction.strip().split()),
        "learned_by": "llm_protocol_interpreter",
    }
    return ProtocolWrite(
        protocol_id=_protocol_id(protocol_kind),
        protocol_kind=protocol_kind,
        title=title,
        card=card,
        body=body,
        variables=merged_variables,
        applies_to=clean_applies_to,
        metadata=metadata,
    )


def build_protocol_write_from_update(
    *,
    protocol_kind: str,
    title: str | None,
    card: str | None,
    body: str | None,
    variables: dict[str, Any] | None,
    applies_to: list[str] | None,
    existing_protocols: list[MarkdownRecord],
) -> ProtocolWrite:
    supported_kind = _supported_protocol_kind(protocol_kind)
    if supported_kind is None:
        raise ValueError(f"Unsupported protocol kind: {protocol_kind}")
    existing = _find_protocol(existing_protocols, supported_kind)
    built_in = BUILT_IN_PROTOCOLS.get(supported_kind)
    merged_variables = _default_variables(supported_kind)
    merged_variables.update(_protocol_variables(existing))
    merged_variables.update(_clean_variables(variables or {}))
    clean_applies_to = _clean_string_list(applies_to or [])
    if not clean_applies_to and existing is not None:
        clean_applies_to = _clean_string_list(existing.metadata.get("applies_to") or [])
    if not clean_applies_to:
        clean_applies_to = _applies_to(supported_kind)
    clean_title = _clean_text(title)
    clean_card = _clean_text(card)
    clean_body = str(body or "").strip()
    if not clean_title:
        clean_title = existing.title if existing is not None else str((built_in or {}).get("title") or _protocol_title(supported_kind))
    if not clean_card:
        clean_card = existing.card if existing is not None else _protocol_card(supported_kind, merged_variables)
    if not clean_body:
        clean_body = existing.body if existing is not None else str(
            (built_in or {}).get("body")
            or _protocol_body(
                protocol_kind=supported_kind,
                variables=merged_variables,
                latest_instruction="Updated through the protocol API.",
            )
        )
    metadata = {
        "learned_by": "protocol_api",
        "override_of_builtin": supported_kind in BUILT_IN_PROTOCOLS,
        "override_of_canonical": _is_canonical_record(existing) if existing is not None else False,
    }
    return ProtocolWrite(
        protocol_id=_protocol_id(supported_kind),
        protocol_kind=supported_kind,
        title=clean_title,
        card=clean_card,
        body=clean_body,
        variables=merged_variables,
        applies_to=clean_applies_to,
        metadata=metadata,
    )


def find_protocol_record(records: list[MarkdownRecord], protocol_kind_or_id: str) -> MarkdownRecord | None:
    lookup = str(protocol_kind_or_id or "").strip().lower()
    if not lookup:
        return None
    for record in records:
        if record.type != "protocol":
            continue
        record_kind = str(record.metadata.get("protocol_kind") or "").strip().lower()
        if record.id.lower() == lookup or record_kind == lookup:
            return record
    return None


def built_in_protocol_kind_for_lookup(protocol_kind_or_id: str) -> str | None:
    lookup = str(protocol_kind_or_id or "").strip().lower()
    if not lookup:
        return None
    kind = _supported_protocol_kind(lookup)
    if kind in BUILT_IN_PROTOCOLS:
        return kind
    for built_in_kind, built_in in BUILT_IN_PROTOCOLS.items():
        if str(built_in.get("id") or "").strip().lower() == lookup:
            return built_in_kind
    return None


def normalize_protocol_kind(value: Any) -> str | None:
    return _supported_protocol_kind(value)


def protocol_candidates_for_kinds(
    *,
    protocol_kinds: list[str],
    concept_records: list[MarkdownRecord],
    limit: int = 4,
) -> list[CandidateMemory]:
    supported_kinds = _supported_protocol_kinds(protocol_kinds)
    if not supported_kinds:
        return []
    candidates: list[CandidateMemory] = []
    seen: set[str] = set()
    for record in concept_records:
        if record.type != "protocol":
            continue
        record_kind = str(record.metadata.get("protocol_kind") or "").strip().lower()
        if record_kind not in supported_kinds:
            continue
        if record_kind in seen:
            continue
        seen.add(record_kind)
        label = record_kind.replace("_", " ")
        candidates.append(
            CandidateMemory(
                id=record.id,
                title=record.title,
                type=record.type,
                card=record.card,
                score=80.0,
                reason=f"protocol: interpreter selected {label} protocol for this turn",
                why_recalled=f"{record.title} applies because Vantage interpreted this as {label} work.",
                source=record.source,
                trust=record.trust,
                body=record.body,
                path=record.path_hint,
                protocol={
                    "protocol_kind": record_kind,
                    "variables": record.metadata.get("variables") or {},
                    "applies_to": record.metadata.get("applies_to") or [],
                    "modifiable": bool(record.metadata.get("modifiable", True)),
                    "is_builtin": False,
                    "is_canonical": _is_canonical_record(record),
                    "overrides_builtin": bool(record.metadata.get("override_of_builtin")),
                    "overrides_canonical": bool(record.metadata.get("override_of_canonical")),
                },
            )
        )
    for protocol_kind in supported_kinds:
        if protocol_kind in seen:
            continue
        built_in = BUILT_IN_PROTOCOLS.get(protocol_kind)
        if built_in is None:
            continue
        label = protocol_kind.replace("_", " ")
        candidates.append(
            CandidateMemory(
                id=str(built_in["id"]),
                title=str(built_in["title"]),
                type="protocol",
                card=str(built_in["card"]),
                score=80.0,
                reason=f"protocol: navigator applied built-in {label} protocol",
                why_recalled=f"{built_in['title']} applies because the Navigator pressed apply_protocol for {label}.",
                source="concept",
                trust="high",
                body=str(built_in["body"]),
                path=None,
                protocol={
                    "protocol_kind": protocol_kind,
                    "variables": built_in.get("variables") or {},
                    "applies_to": built_in.get("applies_to") or [],
                    "modifiable": True,
                    "is_builtin": True,
                    "overrides_builtin": False,
                },
            )
        )
    return candidates[:limit]


def protocol_kinds_from_control_panel(control_panel: dict[str, object] | None) -> list[str]:
    if not isinstance(control_panel, dict):
        return []
    actions = control_panel.get("actions")
    if not isinstance(actions, list):
        return []
    protocol_kinds: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("type") or "").strip()
        if action_type != "apply_protocol":
            continue
        protocol_kind = _supported_protocol_kind(action.get("protocol_kind") or action.get("kind"))
        if protocol_kind and protocol_kind not in protocol_kinds:
            protocol_kinds.append(protocol_kind)
    return protocol_kinds


def _find_protocol(records: list[MarkdownRecord], protocol_kind: str) -> MarkdownRecord | None:
    protocol_id = _protocol_id(protocol_kind)
    for record in records:
        record_kind = str(record.metadata.get("protocol_kind") or "").strip().lower()
        if record.type == "protocol" and (record.id == protocol_id or record_kind == protocol_kind):
            return record
    return None


def _is_canonical_record(record: MarkdownRecord) -> bool:
    return "canonical" in record.path.parts


def _protocol_variables(record: MarkdownRecord | None) -> dict[str, Any]:
    if record is None:
        return {}
    variables = record.metadata.get("variables")
    return dict(variables) if isinstance(variables, dict) else {}


def _clean_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _supported_protocol_kind(value: Any) -> str | None:
    kind = str(value or "").strip().lower()
    return kind if kind in SUPPORTED_PROTOCOL_KINDS else None


def _supported_protocol_kinds(values: list[Any]) -> list[str]:
    kinds: list[str] = []
    for value in values:
        kind = _supported_protocol_kind(value)
        if kind and kind not in kinds:
            kinds.append(kind)
    return kinds


def _clean_variables(variables: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in variables.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        if isinstance(value, list):
            cleaned[clean_key] = _clean_string_list(value)
        elif isinstance(value, dict):
            nested = _clean_variables(value)
            if nested:
                cleaned[clean_key] = nested
        elif value is not None:
            clean_value = " ".join(str(value).strip().split())
            if clean_value:
                cleaned[clean_key] = clean_value
    return cleaned


def _clean_string_list(values: list[Any]) -> list[str]:
    return [
        clean_value
        for clean_value in dict.fromkeys(" ".join(str(value).strip().split()) for value in values)
        if clean_value
    ]


def _default_variables(protocol_kind: str) -> dict[str, Any]:
    if protocol_kind == "email":
        return {
            "recipient_name": "Infer from the request; ask only when the recipient is ambiguous.",
            "sender_name": "Infer from the user's saved preference when available.",
            "signature": "",
            "style": ["clear", "useful", "human"],
            "format": ["include greeting, body, close, and signature for complete drafts"],
        }
    if protocol_kind == "research_paper":
        return {
            "citation_style": "Ask or infer from venue when unspecified.",
            "audience": "Academic readers in the relevant field.",
            "style": ["precise", "evidence-led", "structured"],
            "format": ["surface thesis, contribution, evidence, limitations, and references"],
        }
    if protocol_kind == "scenario_lab":
        return dict(BUILT_IN_PROTOCOLS["scenario_lab"]["variables"])
    return {}


def _applies_to(protocol_kind: str) -> list[str]:
    if protocol_kind == "email":
        return ["email", "emails", "business email", "draft email", "polish email"]
    if protocol_kind == "research_paper":
        return ["research paper", "paper", "manuscript", "abstract", "literature review"]
    if protocol_kind == "scenario_lab":
        return list(BUILT_IN_PROTOCOLS["scenario_lab"]["applies_to"])
    return [protocol_kind]


def _protocol_id(protocol_kind: str) -> str:
    return {
        "email": "email-drafting-protocol",
        "research_paper": "research-paper-drafting-protocol",
        "scenario_lab": "scenario-lab-protocol",
    }.get(protocol_kind, f"{protocol_kind}-protocol")


def _protocol_title(protocol_kind: str) -> str:
    return {
        "email": "Email Drafting Protocol",
        "research_paper": "Research Paper Drafting Protocol",
        "scenario_lab": "Scenario Lab Protocol",
    }.get(protocol_kind, f"{protocol_kind.replace('_', ' ').title()} Protocol")


def _protocol_card(protocol_kind: str, variables: dict[str, Any]) -> str:
    if protocol_kind == "email":
        signature = str(variables.get("signature") or "").strip()
        style = ", ".join(_as_list(variables.get("style"))[:3])
        parts = ["Reusable instructions for drafting email"]
        if signature:
            parts.append(f"signature: {signature}")
        if style:
            parts.append(f"style: {style}")
        return "; ".join(parts) + "."
    if protocol_kind == "research_paper":
        return "Reusable instructions for drafting research papers, abstracts, and manuscript sections."
    if protocol_kind == "scenario_lab":
        return str(BUILT_IN_PROTOCOLS["scenario_lab"]["card"])
    return "Reusable instructions for a recurring class of work."


def _protocol_body(
    *,
    protocol_kind: str,
    variables: dict[str, Any],
    latest_instruction: str,
) -> str:
    if protocol_kind == "email":
        return _email_protocol_body(variables=variables, latest_instruction=latest_instruction)
    if protocol_kind == "research_paper":
        return _research_paper_protocol_body(variables=variables, latest_instruction=latest_instruction)
    if protocol_kind == "scenario_lab":
        return str(BUILT_IN_PROTOCOLS["scenario_lab"]["body"])
    return (
        "## Protocol\n\n"
        "Use this protocol whenever the current request matches this recurring work type.\n\n"
        f"## Variables\n\n{_variables_markdown(variables)}\n\n"
        "## Latest Instruction\n\n"
        f"{latest_instruction.strip()}\n"
    )


def _email_protocol_body(*, variables: dict[str, Any], latest_instruction: str) -> str:
    return (
        "## Protocol\n\n"
        "Use this protocol whenever the user asks Vantage to draft, revise, polish, or format an email.\n\n"
        "## Variables\n\n"
        f"{_variables_markdown(variables)}\n\n"
        "## Procedure\n\n"
        "1. Infer routine fields such as recipient name, sender name, context, and desired outcome from the request.\n"
        "2. Ask a follow-up only when a missing variable would materially change the email.\n"
        "3. Draft with a clear greeting, useful body, appropriate close, and the configured signature when available.\n"
        "4. Respect any turn-specific override over this stored protocol.\n\n"
        "## Latest Instruction\n\n"
        f"{latest_instruction.strip()}\n"
    )


def _research_paper_protocol_body(*, variables: dict[str, Any], latest_instruction: str) -> str:
    return (
        "## Protocol\n\n"
        "Use this protocol whenever the user asks Vantage to draft, revise, outline, or polish research-paper material.\n\n"
        "## Variables\n\n"
        f"{_variables_markdown(variables)}\n\n"
        "## Procedure\n\n"
        "1. Identify the claim, contribution, evidence, intended audience, and venue constraints.\n"
        "2. Prefer precise academic structure over generic prose.\n"
        "3. Surface assumptions, limitations, and citation needs instead of inventing missing evidence.\n"
        "4. Respect any turn-specific override over this stored protocol.\n\n"
        "## Latest Instruction\n\n"
        f"{latest_instruction.strip()}\n"
    )


def _variables_markdown(variables: dict[str, Any]) -> str:
    lines = []
    for key, value in variables.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value if str(item).strip())
        else:
            rendered = str(value).strip()
        if rendered:
            lines.append(f"- {key}: {rendered}")
    return "\n".join(lines) if lines else "- none configured yet"


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
