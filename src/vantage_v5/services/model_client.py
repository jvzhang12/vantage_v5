from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import time
from typing import Any

from openai import OpenAI


MODEL_PROVIDER_OPENAI = "openai"
MODEL_PROVIDER_CODEX_OAUTH = "codex_oauth"
CODEX_OAUTH_RESPONSES_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_OAUTH_EXPIRY_MARGIN_SECONDS = 60


@dataclass(frozen=True, slots=True)
class ModelClientConfig:
    provider: str = MODEL_PROVIDER_OPENAI
    openai_api_key: str | None = None
    codex_auth_path: Path | None = None
    codex_base_url: str | None = None


@dataclass(frozen=True, slots=True)
class CodexOAuthCredential:
    access_token: str
    refresh_token: str | None
    account_id: str | None
    expires_at: int | None
    auth_path: Path

    def is_expired(self, *, margin_seconds: int = CODEX_OAUTH_EXPIRY_MARGIN_SECONDS) -> bool:
        if self.expires_at is None:
            return False
        return self.expires_at <= int(time.time()) + margin_seconds


@dataclass(frozen=True, slots=True)
class CollectedResponse:
    output_text: str


def normalize_model_provider(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"codex", "codex_oauth", "openai_codex", "openai_codex_oauth"}:
        return MODEL_PROVIDER_CODEX_OAUTH
    if normalized in {"openai", "openai_api", "api_key"}:
        return MODEL_PROVIDER_OPENAI
    return MODEL_PROVIDER_OPENAI


def default_model_for_provider(provider: str) -> str:
    if normalize_model_provider(provider) == MODEL_PROVIDER_CODEX_OAUTH:
        return "gpt-5.5"
    return "gpt-4.1"


def create_model_client(config: ModelClientConfig | None = None) -> Any | None:
    cfg = config or ModelClientConfig()
    provider = normalize_model_provider(cfg.provider)
    if provider == MODEL_PROVIDER_CODEX_OAUTH:
        credential = load_codex_oauth_credential(cfg.codex_auth_path)
        if credential is None or credential.is_expired():
            return None
        client = OpenAI(
            api_key=credential.access_token,
            base_url=(cfg.codex_base_url or CODEX_OAUTH_RESPONSES_BASE_URL),
        )
        return _CodexOAuthClientAdapter(client)
    if cfg.openai_api_key:
        return OpenAI(api_key=cfg.openai_api_key)
    return None


def resolve_codex_auth_path(auth_path: Path | None = None) -> Path:
    if auth_path is not None:
        return auth_path.expanduser()
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "auth.json"
    return Path.home() / ".codex" / "auth.json"


def load_codex_oauth_credential(auth_path: Path | None = None) -> CodexOAuthCredential | None:
    path = resolve_codex_auth_path(auth_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    tokens = payload.get("tokens")
    if not isinstance(tokens, dict):
        return None
    access_token = _string_value(tokens.get("access_token"))
    if not access_token:
        return None
    refresh_token = _string_value(tokens.get("refresh_token"))
    account_id = _string_value(tokens.get("account_id"))
    return CodexOAuthCredential(
        access_token=access_token,
        refresh_token=refresh_token,
        account_id=account_id,
        expires_at=_decode_jwt_exp(access_token),
        auth_path=path,
    )


def codex_oauth_status(auth_path: Path | None = None) -> dict[str, Any]:
    credential = load_codex_oauth_credential(auth_path)
    if credential is None:
        return {
            "configured": False,
            "source": "codex_cli",
            "masked_account_id": "",
            "expires_at": None,
            "expired": False,
            "detail": "Codex OAuth is not signed in for this machine.",
        }
    expired = credential.is_expired(margin_seconds=CODEX_OAUTH_EXPIRY_MARGIN_SECONDS)
    return {
        "configured": not expired,
        "source": "codex_cli",
        "masked_account_id": _mask_identifier(credential.account_id),
        "expires_at": _iso_timestamp(credential.expires_at),
        "expired": expired,
        "detail": "Using Codex OAuth from the local Codex CLI session." if not expired else "Codex OAuth is expired. Run codex login to refresh it.",
    }


def _decode_jwt_exp(token: str) -> int | None:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except (ValueError, json.JSONDecodeError, OSError):
        return None
    exp = claims.get("exp") if isinstance(claims, dict) else None
    return int(exp) if isinstance(exp, int | float) else None


def _iso_timestamp(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, UTC).isoformat()


def _mask_identifier(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return f"{text[:2]}...{text[-2:]}"
    return f"{text[:4]}...{text[-4:]}"


def _string_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


class _CodexOAuthClientAdapter:
    def __init__(self, client: OpenAI) -> None:
        self._client = client
        self.responses = _CodexOAuthResponsesAdapter(client.responses)


class _CodexOAuthResponsesAdapter:
    def __init__(self, responses: Any) -> None:
        self._responses = responses

    def create(self, *args: Any, **kwargs: Any) -> Any:
        if "input" in kwargs:
            kwargs = {**kwargs, "input": _codex_responses_input(kwargs["input"])}
        kwargs["store"] = False
        kwargs["stream"] = True
        stream = self._responses.create(*args, **kwargs)
        return _collect_codex_response_stream(stream)


def _codex_responses_input(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": value,
                }
            ],
        }
    ]


def _collect_codex_response_stream(stream: Any) -> CollectedResponse:
    text_parts: list[str] = []
    final_response: Any = None
    failed_response: Any = None
    for event in stream:
        event_type = str(getattr(event, "type", "") or "")
        if event_type == "response.output_text.delta":
            delta = getattr(event, "delta", "")
            if isinstance(delta, str):
                text_parts.append(delta)
        elif event_type == "response.completed":
            final_response = getattr(event, "response", None)
        elif event_type in {"response.failed", "response.incomplete"}:
            failed_response = getattr(event, "response", None)
    if failed_response is not None:
        error = getattr(failed_response, "error", None)
        raise RuntimeError(_provider_error_message(error) or "Codex OAuth response stream failed.")
    output_text = "".join(text_parts).strip()
    if not output_text and final_response is not None:
        output_text = _response_output_text(final_response).strip()
    return CollectedResponse(output_text=output_text)


def _response_output_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str):
        return direct
    parts: list[str] = []
    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return ""
    for item in output:
        content = getattr(item, "content", None)
        if not isinstance(content, list):
            continue
        for content_item in content:
            text = getattr(content_item, "text", None)
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def _provider_error_message(error: Any) -> str:
    if error is None:
        return ""
    if isinstance(error, str):
        return error
    message = getattr(error, "message", None)
    if isinstance(message, str):
        return message
    return ""
