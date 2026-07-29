import httpx
from openai import APITimeoutError

from app.api.v1.routes.images import internal_server_error
from app.services.image_generation import print_prompt_comparison


def test_prompt_comparison_logs_lengths_not_content(capsys) -> None:
    marker = "SENSITIVE_PROMPT_MARKER"

    print_prompt_comparison(marker, marker + "_REVISED")

    output = capsys.readouterr()
    assert marker not in output.out
    assert marker not in output.err
    assert "chars:" in output.out


def test_internal_error_hides_exception_content(capsys) -> None:
    marker = "SENSITIVE_EXCEPTION_MARKER"

    response = internal_server_error(
        "test_operation",
        RuntimeError(marker),
        image_id="image-test-id",
    )

    output = capsys.readouterr()
    assert marker not in output.out
    assert marker not in output.err
    assert marker not in str(response.detail)
    assert response.status_code == 500
    assert "RuntimeError" in output.out


def test_image_api_timeout_returns_gateway_timeout(capsys) -> None:
    error = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))

    response = internal_server_error(
        "image_recolor",
        error,
        image_id="image-test-id",
    )

    output = capsys.readouterr()
    assert response.status_code == 504
    assert response.detail == {
        "code": "image_generation_timeout",
        "message": "圖片生成逾時，請稍後再試。",
    }
    assert "APITimeoutError" in output.out
