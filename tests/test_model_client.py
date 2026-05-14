from __future__ import annotations

import base64
import json
from pathlib import Path

from vantage_v5.services.model_client import CODEX_OAUTH_RESPONSES_BASE_URL
from vantage_v5.services.model_client import codex_oauth_status
from vantage_v5.services.model_client import create_model_client
from vantage_v5.services.model_client import load_codex_oauth_credential
from vantage_v5.services.model_client import MODEL_PROVIDER_CODEX_OAUTH
from vantage_v5.services.model_client import ModelClientConfig


def test_load_codex_oauth_credential_reads_codex_cli_auth(tmp_path: Path) -> None:
    access_token = _fake_jwt(4_102_444_800)
    auth_path = _write_codex_auth(tmp_path / "auth.json", access_token=access_token)

    credential = load_codex_oauth_credential(auth_path)

    assert credential is not None
    assert credential.access_token == access_token
    assert credential.refresh_token == "refresh-token"
    assert credential.account_id == "account-id-123456"
    assert credential.expires_at == 4_102_444_800
    assert credential.is_expired() is False
    status = codex_oauth_status(auth_path)
    assert status["configured"] is True
    assert status["source"] == "codex_cli"
    assert status["masked_account_id"] == "acco...3456"
    assert access_token not in json.dumps(status)


def test_create_model_client_uses_codex_responses_base_url(tmp_path: Path, monkeypatch) -> None:
    access_token = _fake_jwt(4_102_444_800)
    auth_path = _write_codex_auth(tmp_path / "auth.json", access_token=access_token)
    captured: dict[str, object] = {}
    create_kwargs: dict[str, object] = {}

    class FakeEvent:
        def __init__(self, event_type: str, **kwargs: object) -> None:
            self.type = event_type
            for key, value in kwargs.items():
                setattr(self, key, value)

    class FakeResponses:
        def create(self, **kwargs: object) -> list[FakeEvent]:
            create_kwargs.update(kwargs)
            return [FakeEvent("response.output_text.delta", delta="OK")]

    class FakeOpenAI:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)
            self.responses = FakeResponses()

    monkeypatch.setattr("vantage_v5.services.model_client.OpenAI", FakeOpenAI)

    client = create_model_client(
        ModelClientConfig(
            provider=MODEL_PROVIDER_CODEX_OAUTH,
            codex_auth_path=auth_path,
        )
    )

    assert client is not None
    assert captured == {
        "api_key": access_token,
        "base_url": CODEX_OAUTH_RESPONSES_BASE_URL,
    }
    response = client.responses.create(model="gpt-5.5", store=False, stream=False, input="hello")
    assert response.output_text == "OK"
    assert create_kwargs["store"] is False
    assert create_kwargs["stream"] is True
    assert create_kwargs["input"] == [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        }
    ]


def test_create_model_client_returns_none_for_expired_codex_oauth(tmp_path: Path, monkeypatch) -> None:
    auth_path = _write_codex_auth(tmp_path / "auth.json", access_token=_fake_jwt(1))

    class FakeOpenAI:
        def __init__(self, **kwargs: object) -> None:
            raise AssertionError("expired Codex OAuth must not create a model client")

    monkeypatch.setattr("vantage_v5.services.model_client.OpenAI", FakeOpenAI)

    client = create_model_client(
        ModelClientConfig(
            provider=MODEL_PROVIDER_CODEX_OAUTH,
            codex_auth_path=auth_path,
        )
    )

    assert client is None
    assert codex_oauth_status(auth_path)["configured"] is False


def _write_codex_auth(path: Path, *, access_token: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": "refresh-token",
                    "account_id": "account-id-123456",
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _fake_jwt(exp: int) -> str:
    def encode(payload: dict[str, object]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode({'exp': exp})}.signature"
