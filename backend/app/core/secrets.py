from functools import lru_cache

import boto3

from app.core.config import get_settings


class SecretConfigurationError(RuntimeError):
    """A production secret is missing or cannot be loaded safely."""


@lru_cache
def get_openai_api_key() -> str:
    settings = get_settings()
    parameter_name = settings.openai_api_key_parameter_name.strip()

    if parameter_name:
        if not settings.aws_region.strip():
            raise SecretConfigurationError("AWS_REGION is required for Parameter Store")
        try:
            response = boto3.client("ssm", region_name=settings.aws_region).get_parameter(
                Name=parameter_name,
                WithDecryption=True,
            )
            value = response["Parameter"]["Value"].strip()
        except Exception as exc:
            raise SecretConfigurationError(
                "The image API credential could not be loaded"
            ) from exc
        if not value:
            raise SecretConfigurationError("The image API credential is empty")
        return value

    if settings.app_env == "production":
        raise SecretConfigurationError(
            "OPENAI_API_KEY_PARAMETER_NAME is required in production"
        )
    return settings.openai_api_key.strip()
