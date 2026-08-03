from typing import Any

from fastapi import HTTPException


ERROR_MESSAGES = {
    "authentication_required": "請先登入後再繼續操作。",
    "invalid_credentials": "帳號或密碼錯誤。",
    "session_already_active": "此帳號目前已在其他裝置登入。",
    "invalid_replacement_challenge": "登入確認已失效，請重新登入。",
    "too_many_login_attempts": "登入嘗試次數過多，請稍後再試。",
    "invalid_request_origin": "無法驗證請求來源。",
    "invalid_request": "輸入內容有誤，請檢查後再試。",
    "not_found": "找不到要求的資料。",
    "conflict": "目前的資料狀態無法完成此操作。",
    "too_many_requests": "操作次數過多，請稍後再試。",
    "server_error": "系統暫時無法完成操作，請稍後再試。",
    "service_unavailable": "服務暫時無法使用，請稍後再試。",
    "image_generation_timeout": "圖片生成逾時，請稍後再試。",
    "image_generation_failed": "圖片生成失敗，請稍後再試。",
    "generation_in_progress": "圖片正在生成中，請稍候。",
    "generation_failed": "這次圖片生成失敗，請重新送出要求。",
    "another_generation_in_progress": "另一張圖片正在生成中，請稍候。",
    "hourly_generation_limit": "已達每小時圖片生成上限，請稍後再試。",
    "daily_generation_limit": "已達每日圖片生成上限，請明天再試。",
    "storage_capacity_reached": "圖片儲存空間不足，暫時無法建立新圖片。",
}

LEGACY_DETAIL_CODES = {
    "Authentication required": "authentication_required",
    "Invalid username or password": "invalid_credentials",
    "Too many login attempts": "too_many_login_attempts",
    "Invalid request origin": "invalid_request_origin",
    "Image generation is temporarily unavailable": "service_unavailable",
    "The image service timed out. Please try again.": "image_generation_timeout",
    "The image operation failed": "image_generation_failed",
}


def api_error(
    status_code: int,
    code: str,
    message: str | None = None,
    **metadata: Any,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message or ERROR_MESSAGES.get(code, ERROR_MESSAGES["server_error"]),
            **metadata,
        },
    )


def safe_error_detail(status_code: int, detail: Any) -> dict[str, Any]:
    if isinstance(detail, dict):
        code = str(detail.get("code") or _fallback_code(status_code))
        return {
            **detail,
            "code": code,
            "message": ERROR_MESSAGES.get(code, _fallback_message(status_code)),
        }
    code = LEGACY_DETAIL_CODES.get(str(detail), _fallback_code(status_code))
    return {"code": code, "message": ERROR_MESSAGES.get(code, _fallback_message(status_code))}


def _fallback_code(status_code: int) -> str:
    if status_code == 401:
        return "authentication_required"
    if status_code == 403:
        return "invalid_request_origin"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if status_code == 422:
        return "invalid_request"
    if status_code == 429:
        return "too_many_requests"
    if status_code == 503:
        return "service_unavailable"
    if status_code == 504:
        return "image_generation_timeout"
    if status_code == 507:
        return "storage_capacity_reached"
    if status_code >= 500:
        return "server_error"
    return "invalid_request"


def _fallback_message(status_code: int) -> str:
    return ERROR_MESSAGES[_fallback_code(status_code)]
