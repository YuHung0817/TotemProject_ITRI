from types import SimpleNamespace

import pytest

from app.core.secrets import (
    SecretConfigurationError,
    get_openai_api_key,
)


def test_development_uses_local_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        app_env="development",
        openai_api_key="local-test-key",
        openai_api_key_parameter_name="",
        aws_region="",
    )
    monkeypatch.setattr("app.core.secrets.get_settings", lambda: settings)
    get_openai_api_key.cache_clear()

    assert get_openai_api_key() == "local-test-key"


def test_parameter_store_uses_decryption_and_region(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        app_env="production",
        openai_api_key="",
        openai_api_key_parameter_name="/totem/production/openai-api-key",
        aws_region="ap-northeast-1",
    )
    calls: dict = {}

    class FakeSsmClient:
        def get_parameter(self, **kwargs):
            calls.update(kwargs)
            return {"Parameter": {"Value": "parameter-test-key"}}

    def fake_client(service_name: str, **kwargs):
        calls["service_name"] = service_name
        calls.update(kwargs)
        return FakeSsmClient()

    monkeypatch.setattr("app.core.secrets.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.secrets.boto3.client", fake_client)
    get_openai_api_key.cache_clear()

    assert get_openai_api_key() == "parameter-test-key"
    assert calls == {
        "service_name": "ssm",
        "region_name": "ap-northeast-1",
        "Name": "/totem/production/openai-api-key",
        "WithDecryption": True,
    }


def test_production_rejects_plain_environment_key(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        app_env="production",
        openai_api_key="must-not-be-used",
        openai_api_key_parameter_name="",
        aws_region="ap-northeast-1",
    )
    monkeypatch.setattr("app.core.secrets.get_settings", lambda: settings)
    get_openai_api_key.cache_clear()

    with pytest.raises(
        SecretConfigurationError,
        match="OPENAI_API_KEY_PARAMETER_NAME is required",
    ):
        get_openai_api_key()
