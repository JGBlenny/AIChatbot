"""documind-ocr-mapping 端點（design.md 元件 1）。需求 1.1–1.6。

`POST /api/v1/ocr-mapping/{document_type}`：收 DocuMind 回應全文＋身分 → 回 JGB 欄位草稿。
HTTP 邊界只做四件：大小守門、型別守門、Pydantic 驗證、錯誤碼對映；⛔ 映射邏輯一律在 services/ocr_mapping/。

⚠️ `document_type` 路徑參數刻意宣告成 `str` 而非 Enum：讓「不支援的型別」走本端點的 400
`UNSUPPORTED_DOCUMENT_TYPE`，⛔ 不被 FastAPI 自動變成 422（呼叫端要能分辨「型別錯」與「payload 壞」）。
⚠️ 認證沿用全域 `api_key_auth` middleware（`RAG_API_AUTH_ENFORCE`）；本端點 ⛔ 不列入豁免。
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from services import usage_metering as _um
from services.ocr_mapping.mapper import run_mapping
from services.ocr_mapping.models import DocumentType, FieldSource, MappingResult, OcrMappingRequest
from services.ocr_mapping.name_splitter import NamePolicy

router = APIRouter(prefix="/api/v1/ocr-mapping", tags=["ocr-mapping"])

_SUPPORTED = {t.value for t in DocumentType}


def _err(status: int, code: str, detail: str) -> JSONResponse:
    """沿用 DocuMind 與 `External\\*` 的錯誤形狀：{"detail": …, "error_code": …}。"""
    return JSONResponse(status_code=status, content={"detail": detail, "error_code": code})


_DEFAULT_MAX_BODY_MB = 2.0


def _max_body_bytes() -> int:
    """每請求讀 env（與 RERANKER_INPUT_LIMIT 等既有慣例相同），測試可 monkeypatch。
    ⚠️ 2026-09-03 對抗驗證 ②-5：壞值曾讓每次呼叫 500、負值讓每次 413 ⇒ 壞值／≤0／空一律回預設。"""
    raw = os.getenv("OCR_MAPPING_MAX_BODY_MB", "")
    try:
        mb = float(raw) if raw.strip() else _DEFAULT_MAX_BODY_MB
    except ValueError:
        mb = _DEFAULT_MAX_BODY_MB
    if mb <= 0:
        mb = _DEFAULT_MAX_BODY_MB
    return int(mb * 1024 * 1024)


def _name_policy() -> NamePolicy:
    try:
        return NamePolicy(os.getenv("OCR_NAME_POLICY", NamePolicy.split.value))
    except ValueError:
        return NamePolicy.split


_IDENTITY_KEYS = ("mode", "role_id", "target_user", "vendor_id", "user_id", "session_id")


def _meter_begin(data: dict) -> None:
    """需求 9.3／9.3a：端點內自記（既有 middleware 只認 /api/v1/message，⛔ 不動它、⛔ 不雙落點）。
    `begin()` 只讀身分六鍵；`session_id` 前綴命中 `INTERNAL_RULES` ⇒ is_internal，未帶 ⇒ 外部。"""
    _um.begin({k: data.get(k) for k in _IDENTITY_KEYS})
    _um.set_path("ocr_mapping")


def _reject(request: Request, status: int, code: str, detail: str) -> JSONResponse:
    _um.finalize(status="rejected", http_status=status, db_pool=getattr(request.app.state, "db_pool", None))
    return _err(status, code, detail)


def _log_summary(result: MappingResult) -> None:
    """需求 9.5：日誌只印欄位名／source／confidence，⛔ 不印 value／raw／ocr_raw.text（個資）。"""
    absent = [n for n, f in result.fields.items() if f.source is FieldSource.absent]
    srcs = {n: f.source.value for n, f in result.fields.items() if f.source is not FieldSource.absent}
    print(f"[ocr-mapping] type={result.document_type.value} status={result.status} "
          f"pages={result.provenance.total_pages} needs_review={result.provenance.needs_review} "
          f"absent={len(absent)}/{len(result.fields)} sources={srcs} "
          f"needs_confirmation={result.needs_confirmation} unmapped_clauses={len(result.unmapped_clauses)}")


@router.post("/{document_type}", response_model=MappingResult,
             summary="DocuMind OCR 結果 → JGB 欄位草稿（同步、無狀態）")
async def map_document(document_type: str, request: Request):
    raw = await request.body()
    try:                                                                          # 先取身分建計量 context（拒絕也要記）
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = None
    _meter_begin(data if isinstance(data, dict) else {})

    if len(raw) > _max_body_bytes():                                              # 需求 1.5
        return _reject(request, 413, "BODY_TOO_LARGE", f"請求體 {len(raw)} bytes 超過上限 {_max_body_bytes()} bytes")
    if document_type not in _SUPPORTED:                                           # 需求 1.3
        return _reject(request, 400, "UNSUPPORTED_DOCUMENT_TYPE",
                       f"document_type 必須是 {sorted(_SUPPORTED)} 之一，實得 {document_type!r}")
    if data is None:
        return _reject(request, 422, "INVALID_DOCUMIND_PAYLOAD", "JSON 解析失敗")
    if not isinstance(data, dict):
        return _reject(request, 422, "INVALID_DOCUMIND_PAYLOAD", "請求體必須是 JSON 物件")
    if data.get("document_type") != document_type:                                # 需求 1.2：⛔ 不以任一方為準靜默處理
        return _reject(request, 400, "DOCUMENT_TYPE_MISMATCH",
                       f"路徑 document_type={document_type!r} 與請求體 {data.get('document_type')!r} 不一致")
    try:
        req = OcrMappingRequest(**data)
    except ValidationError as e:                                                  # 需求 1.1：契約不符
        return _reject(request, 422, "INVALID_DOCUMIND_PAYLOAD", str(e)[:600])

    try:
        result = run_mapping(req, name_policy=_name_policy())                     # 空頁亦 200 draft（需求 1.4）
    except Exception as e:                                                        # ②-3：未預期例外仍要計量、⛔ 不洩個資
        print(f"[ocr-mapping] ERROR type={document_type} exc={type(e).__name__}")
        _um.finalize(status="error", http_status=500, db_pool=getattr(request.app.state, "db_pool", None))
        return _err(500, "MAPPING_ERROR", f"映射失敗：{type(e).__name__}")
    _log_summary(result)
    _um.finalize(status="success", http_status=200, db_pool=getattr(request.app.state, "db_pool", None))
    return result


__all__ = ["router"]
