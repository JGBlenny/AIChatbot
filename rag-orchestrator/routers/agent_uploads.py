"""瀏覽器直傳端點 `POST /api/v1/agent/uploads`（UD-1；JGB 規格草稿 §3）。

這條路**不帶 API 金鑰、不帶 `X-JGB-Identity`**——瀏覽器只拿得到上傳票。
因此它是 `McpServiceGate` 與 `api_key_guard` 唯一的豁免，且只在「路徑**完全等於**
`UPLOAD_PATH`、方法 POST／OPTIONS」時豁免（S1，見 `mcp_facade.is_upload_request`）。
同一前綴下的其他路徑（`/api/v1/agent/trace`、`/api/v1/agent/uploads/x`…）照舊過閘。

檢查順序（每一步不過就停，⛔ 往下讀 body）：
  ① Origin：`AGENT_UPLOAD_ALLOWED_ORIGINS` 未設／空／只有 `*` ⇒ **開放模式**，不檢查 Origin
     （業主 2026-10-29 裁示「不需要擋」：端點不收 cookie，白名單擋不住 curl，閘門是上傳票；
     取消計畫 S8 的「Origin 白名單、沒帶 Origin 一律拒」與凍結清單 A1(e) 的預設行為）；
     有設白名單 ⇒ Origin 必帶且在名單內，否則 403（留給正式站日後收緊）；
  ② 上傳票：`Authorization: Bearer <upload_token>`（⛔ 放網址）——S8；
  ③ 票的張數已滿 ⇒ 429；
  ④ `Content-Length` 超過上限 ⇒ 413（邊讀邊計數，超過即停，⛔ 讀完整包）；
  ⑤ multipart 在記憶體解析（⛔ Starlette `UploadFile` 的暫存檔落地），恰一個 `file`；
  ⑥ 型別只看內容（magic bytes），⛔ 看副檔名與瀏覽器送的 Content-Type ⇒ 415；
  ⑦ 存入暫存 ⇒ 201。

CORS：上傳路徑已脫離 `app.py` 的全域 `CORSMiddleware`（`_CorsExceptUpload`），
預檢由本檔自己回應，⛔ 帶 credentials。開放模式：預檢與所有回應（含錯誤）ACAO 一律 `*`；
白名單模式：ACAO 只回白名單內那個 Origin＋`Vary: Origin`。

⛔ 不記錄任何票、upload_id、檔名、內容；log 只有錯誤碼。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from services.agent import upload_store as US
from services.agent.limits import LIMITS

try:  # python-multipart ≥0.0.13 的套件名
    from python_multipart.multipart import MultipartParser, parse_options_header
except ImportError:  # pragma: no cover - 舊版套件名
    from multipart.multipart import MultipartParser, parse_options_header  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter()

#: multipart 外框（boundary、part 標頭）可多出的位元組；body 上限＝檔案上限＋此值。
MULTIPART_OVERHEAD_BYTES = 16 * 1024
_PREFLIGHT_MAX_AGE_S = "600"

ERR_TOKEN_INVALID = "UPLOAD_TOKEN_INVALID"
ERR_TOKEN_EXPIRED = "UPLOAD_TOKEN_EXPIRED"
ERR_ORIGIN = "ORIGIN_NOT_ALLOWED"
ERR_TOO_LARGE = "FILE_TOO_LARGE"
ERR_UNSUPPORTED = "UNSUPPORTED_FILE_TYPE"
ERR_LIMIT = "UPLOAD_LIMIT_REACHED"
ERR_MALFORMED = "UPLOAD_MALFORMED"

_MESSAGES = {
    ERR_TOKEN_INVALID: "沒帶上傳票或上傳票不對",
    ERR_TOKEN_EXPIRED: "上傳票已過期，請重新取票",
    ERR_ORIGIN: "Origin 不在允許名單",
    ERR_TOO_LARGE: "檔案超過大小上限",
    ERR_UNSUPPORTED: "檔案類型不在允許範圍",
    ERR_LIMIT: "這張上傳票已傳滿檔數上限",
    ERR_MALFORMED: "請以 multipart/form-data 的 file 欄位上傳恰好一個檔案",
}


#: 開放模式的 ACAO 值。白名單模式永遠回不出它：`load_upload_allowed_origins` 會丟掉 `*`。
_ANY_ORIGIN = "*"


def _allowed_origin(request: Request) -> Optional[str]:
    """本次回應的 ACAO 值；`None` ⇒ 拒（403、⛔ ACAO）。每次現讀 env。

    開放模式（白名單去掉 `*` 後是空集合）⇒ 一律 `"*"`，不看 Origin（業主 2026-10-29 裁示）。
    白名單模式 ⇒ 白名單內的 Origin 原字串；沒帶或不在名單 ⇒ `None`。
    """
    allowed = US.load_upload_allowed_origins()
    if not allowed:
        return _ANY_ORIGIN
    origin = request.headers.get("origin")
    if not origin:
        return None
    origin = origin.strip()
    return origin if origin in allowed else None


def origin_policy_label() -> str:
    """啟動訊息用：分辨開放模式與白名單模式（只印個數，⛔ 印名單內容）。"""
    n = len(US.load_upload_allowed_origins())
    if not n:
        return f"Origin 不檢查（開放；{US.UPLOAD_ALLOWED_ORIGINS_ENV} 未設／空／只有 *）"
    return f"Origin 白名單 {n} 個（{US.UPLOAD_ALLOWED_ORIGINS_ENV}）"


def _cors_headers(origin: Optional[str]) -> dict:
    if origin is None:
        return {}
    if origin == _ANY_ORIGIN:
        return {"Access-Control-Allow-Origin": _ANY_ORIGIN}
    return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}


def _error(status: int, code: str, origin: Optional[str]) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error_code": code, "message": _MESSAGES[code]},
        headers=_cors_headers(origin),
    )


def _bearer(request: Request) -> Optional[str]:
    raw = request.headers.get("authorization")
    if not raw:
        return None
    scheme, _, value = raw.partition(" ")
    if scheme.lower() != "bearer":
        return None
    value = value.strip()
    return value or None


class _Malformed(Exception):
    pass


def _parse_single_file(body: bytes, content_type: str) -> bytes:
    """在記憶體解析 multipart，回恰一個 `file` 欄位的位元組；其他形狀 ⇒ `_Malformed`。

    檔名與 part 的 Content-Type 一律丟棄（S11：丟棄瀏覽器檔名）。
    """
    ctype, params = parse_options_header(content_type or "")
    if ctype != b"multipart/form-data":
        raise _Malformed()
    boundary = params.get(b"boundary")
    if not boundary:
        raise _Malformed()

    parts: list = []
    state: dict = {"cur": None, "field": bytearray(), "value": bytearray()}

    def on_part_begin() -> None:
        state["cur"] = {"headers": {}, "data": bytearray()}

    def on_header_field(data: bytes, start: int, end: int) -> None:
        state["field"] += data[start:end]

    def on_header_value(data: bytes, start: int, end: int) -> None:
        state["value"] += data[start:end]

    def on_header_end() -> None:
        state["cur"]["headers"][bytes(state["field"]).lower()] = bytes(state["value"])
        state["field"] = bytearray()
        state["value"] = bytearray()

    def on_part_data(data: bytes, start: int, end: int) -> None:
        state["cur"]["data"] += data[start:end]

    def on_part_end() -> None:
        parts.append(state["cur"])
        state["cur"] = None

    parser = MultipartParser(boundary, {
        "on_part_begin": on_part_begin,
        "on_header_field": on_header_field,
        "on_header_value": on_header_value,
        "on_header_end": on_header_end,
        "on_part_data": on_part_data,
        "on_part_end": on_part_end,
    })
    try:
        parser.write(body)
        parser.finalize()
    except Exception:  # noqa: BLE001 — 解析器的錯誤一律當形狀不對
        raise _Malformed() from None

    if len(parts) != 1:
        raise _Malformed()
    disposition = parts[0]["headers"].get(b"content-disposition", b"")
    dtype, dparams = parse_options_header(disposition)
    if dtype != b"form-data" or dparams.get(b"name") != b"file":
        raise _Malformed()
    return bytes(parts[0]["data"])


@router.options(US.UPLOAD_PATH, include_in_schema=False)
async def upload_preflight(request: Request) -> Response:
    """CORS 預檢：開放模式一律 ACAO `*`；白名單模式只對名單內的 Origin 回 ACAO，其餘 403、⛔ ACAO。"""
    origin = _allowed_origin(request)
    if origin is None:
        return _error(403, ERR_ORIGIN, None)
    headers = _cors_headers(origin)
    headers.update({
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Max-Age": _PREFLIGHT_MAX_AGE_S,
    })
    return Response(status_code=204, headers=headers)


@router.post(US.UPLOAD_PATH, include_in_schema=False)
async def upload_file(request: Request) -> Response:
    # ① Origin：開放模式不檢查；白名單模式沒帶或不在名單 ⇒ 403
    origin = _allowed_origin(request)
    if origin is None:
        return _error(403, ERR_ORIGIN, None)

    # ② 上傳票（⛔ 放網址；只認 Authorization 標頭）
    try:
        handle = US.STORE.verify_ticket(_bearer(request))
    except US.UploadTokenExpired:
        return _error(401, ERR_TOKEN_EXPIRED, origin)
    except US.UploadTokenInvalid:
        return _error(401, ERR_TOKEN_INVALID, origin)

    # ③ 張數已滿 ⇒ 不必讀 body
    if not US.STORE.has_capacity(handle):
        return _error(429, ERR_LIMIT, origin)

    # ④ 大小上限：宣告長度先擋，再邊讀邊計數
    max_bytes = LIMITS.upload_max_bytes
    body_cap = max_bytes + MULTIPART_OVERHEAD_BYTES
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > body_cap:
                return _error(413, ERR_TOO_LARGE, origin)
        except ValueError:
            return _error(400, ERR_MALFORMED, origin)
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > body_cap:
            return _error(413, ERR_TOO_LARGE, origin)

    # ⑤ multipart（記憶體內）
    try:
        data = _parse_single_file(bytes(buf), request.headers.get("content-type", ""))
    except _Malformed:
        return _error(400, ERR_MALFORMED, origin)
    finally:
        del buf
    if len(data) > max_bytes:
        return _error(413, ERR_TOO_LARGE, origin)
    if not data:
        return _error(415, ERR_UNSUPPORTED, origin)

    # ⑥ 型別只看內容
    content_type = US.sniff_content_type(data)
    if content_type is None or content_type not in US.ACCEPT.get(handle.binding.purpose, ()):
        return _error(415, ERR_UNSUPPORTED, origin)

    # ⑦ 存入（張數判斷與計數原子；票若在讀 body 期間過期也在此擋下）
    try:
        receipt = US.STORE.add_upload(handle, content_type=content_type, data=data)
    except US.UploadLimitReached:
        return _error(429, ERR_LIMIT, origin)
    except US.UploadTokenExpired:
        return _error(401, ERR_TOKEN_EXPIRED, origin)
    except US.UploadTokenInvalid:
        return _error(401, ERR_TOKEN_INVALID, origin)
    finally:
        del data

    return JSONResponse(
        status_code=201,
        content={
            "upload_id": receipt.upload_id,
            "content_type": receipt.content_type,
            "size": receipt.size,
            "sha256": receipt.sha256,
        },
        headers={**_cors_headers(origin), "Cache-Control": "no-store"},
    )
