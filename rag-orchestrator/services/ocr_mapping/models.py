"""契約模型（design.md 元件 2）：DocuMind 回應（輸入）與映射草稿（輸出）。

⚠️ 設計判斷
- 輸入模型對 DocuMind 的兩個「文件上有、樣本裡是空／null」的頂層鍵（`field_confidences`、
  `consensus`）一律 Optional／預設空——DocuMind 未來若自己做跨頁共識，page_merger 會優先採用
  （需求 2.6），⛔ 不在這裡假設它們一定有值。
- `pages[]` 允許為空：需求 1.4 要求空頁回 200 `draft`，⛔ 不是 422。
- `FieldValue` 沿用 `services/jgb/repair_prefill.py` 的「值＋出處」語意（SlotValue），
  並擴 `jgb_value`（給 JGB 送，日期為 Ymd 整數）、`confidence`、`raw`（可逆對照）、`page`、`conflicts`。
- `MappingResult.fields` 的鍵集合對同一 `document_type` 恆定（需求 4.3／9.1）——由
  `TRANSCRIPT_FIELDS`／`CONTRACT_FIELDS` 常數定義，並由 model validator 強制；
  LIFF 端得以固定綁欄位，⛔ 不需另行補鍵。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Final, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# 列舉與常數
# ─────────────────────────────────────────────────────────────────────────────
class DocumentType(str, Enum):
    """本 spec 只收兩型；`repair_photo` 走既有 Step 0.5 vision、`bill` 尚無消費端（需求 1.3、範圍外）。"""
    transcript = "transcript"
    contract = "contract"


class FieldSource(str, Enum):
    """欄位值的出處（需求 9.1 值域封閉）。

    ocr            直接來自 DocuMind `structured_data`
    derived        決定性換算（民國年→西元、中文數字、租期月數）；⛔ 無 LLM、無猜測
    llm_extracted  保留值域——D1 已定案 A（2026-09-03，DocuMind `rental_terms`），目前**沒有任何產生者**；
                   ⛔ 不移除：移除等於改回應契約，且 R8 若日後復活仍用此值
    absent         沒讀到；⛔ 不得以其他欄位推算補位（押金二選一鐵則）
    """
    ocr = "ocr"
    derived = "derived"
    llm_extracted = "llm_extracted"
    absent = "absent"


#: 謄本五欄：鍵名沿用 DocuMind 原名（需求 3.1：JGB `estates` 落點待產品決定，⛔ 不在此對應）。
TRANSCRIPT_FIELDS: Final[Tuple[str, ...]] = (
    "land_number", "building_number", "area", "rights_scope", "owner",
)

#: 合約 → JGB 租約欄位（line-bot §7.2 表）。表中未列者一律 absent（需求 4.1／4.3）。
CONTRACT_FIELDS: Final[Tuple[str, ...]] = (
    "date_start", "date_end", "lease_signing_date", "lease_months",
    "rent", "currency", "cycle_date", "cycle",
    "deposit_type", "deposit", "deposit_amount",
    "to_user_last_name", "to_user_first_name", "party_b_full_name",
    "early_termination_days", "early_termination_penalty", "early_termination_penalty2",
)

#: JGB `Contract::isWriteDone()` 無條件必填（line-bot 建約規格 §2.5）；任一 absent ⇒ `draft`（需求 4.4）。
REQUIRED_FOR_WRITE: Final[Tuple[str, ...]] = ("date_start", "date_end", "cycle_date", "rent")

_FIELDS_BY_TYPE: Final[Dict[DocumentType, Tuple[str, ...]]] = {
    DocumentType.transcript: TRANSCRIPT_FIELDS,
    DocumentType.contract: CONTRACT_FIELDS,
}

MAPPING_VERSION: Final[str] = "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# 輸入：DocuMind 回應（原樣接收；⛔ 不在此做任何映射）
# ─────────────────────────────────────────────────────────────────────────────
class OcrRaw(BaseModel):
    text: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="OCR 引擎自評 0–1")


class DocuMindStats(BaseModel):
    model_config = ConfigDict(extra="allow")
    total_time_ms: Optional[int] = None
    total_pages: Optional[int] = None
    llm_pages_used: Optional[int] = None
    estimated_cost: Optional[float] = Field(None, description="該次請求的 LLM 費用（美元）")


class DocuMindPage(BaseModel):
    """DocuMind `pages[i]`。`llm_postprocessed` 未觸發時為 **null**（不是空物件），需求 2.4 要求照常參與合併。"""
    model_config = ConfigDict(extra="allow")
    page_number: int = Field(..., ge=1)
    ocr_raw: OcrRaw = Field(default_factory=OcrRaw)
    rule_postprocessed: Optional[Dict[str, Any]] = None
    llm_postprocessed: Optional[Dict[str, Any]] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="鍵依 document_type 而異")
    field_confidences: Dict[str, float] = Field(default_factory=dict)
    consensus: Optional[Dict[str, Any]] = None


class OcrMappingRequest(BaseModel):
    """端點請求體 ＝ DocuMind 回應全文 ＋ 呼叫者身分（需求 1.1）。

    身分四鍵供 `usage_metering.begin()` 判 `user_type`／`is_internal`（需求 9.3／9.3a）：
    `begin()` 只讀 `mode／role_id／target_user／vendor_id`，`session_id` 前綴決定內部流量。
    """
    model_config = ConfigDict(extra="allow")

    # DocuMind 回應
    document_type: DocumentType
    total_pages: int = Field(..., ge=0)
    pages: List[DocuMindPage]                       # 允許空（需求 1.4）
    needs_review: bool
    review_item_id: Optional[str] = None
    stats: Optional[DocuMindStats] = None
    field_confidences: Dict[str, float] = Field(default_factory=dict, description="頂層；樣本中為空")
    consensus: Optional[Dict[str, Any]] = Field(None, description="頂層；樣本中為 null")
    file_name: Optional[str] = None
    answer: Optional[str] = None

    # 呼叫者身分
    vendor_id: int = Field(..., ge=1)
    role_id: str
    user_id: Optional[str] = None
    mode: Literal["b2c", "b2b"] = "b2c"
    target_user: Optional[str] = None
    session_id: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 輸出：欄位值物件與草稿
# ─────────────────────────────────────────────────────────────────────────────
FieldScalar = Union[str, int, float]


class FieldConflict(BaseModel):
    """多頁不同值時的落選值（需求 2.3）。"""
    value: Optional[Union[FieldScalar, List[str]]] = None
    page: Optional[int] = None
    confidence: Optional[float] = None


class FieldValue(BaseModel):
    """一個 JGB 欄位的值＋出處。預設即 absent（需求 7.4：absent 的 confidence 為 null）。"""
    value: Optional[Union[FieldScalar, List[str]]] = None
    jgb_value: Optional[FieldScalar] = Field(None, description="給 JGB 送；日期為 Ymd 整數，其餘同 value")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_source: Literal["field", "page_level"] = "field"
    source: FieldSource = FieldSource.absent
    raw: Optional[str] = Field(None, description="原文全段；derived 值的可逆對照（需求 5.6）")
    page: Optional[int] = None
    conflicts: List[FieldConflict] = Field(default_factory=list)


class Provenance(BaseModel):
    document_type: DocumentType
    total_pages: int = Field(..., ge=0)
    needs_review: bool
    review_item_id: Optional[str] = None
    documind_estimated_cost: Optional[float] = None
    mapping_version: str
    notes: List[str] = Field(default_factory=list)


class MappingResult(BaseModel):
    status: Literal["draft", "ready"]
    document_type: DocumentType
    fields: Dict[str, FieldValue]
    needs_confirmation: List[str] = Field(default_factory=list)
    unmapped_clauses: List[str] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _fields_key_set_is_fixed(self) -> "MappingResult":
        """需求 4.3／9.1：同型 `fields` 鍵集合恆定——多一鍵少一鍵都拒絕，⛔ 不靜默補齊。"""
        expected = set(_FIELDS_BY_TYPE[self.document_type])
        actual = set(self.fields)
        if actual != expected:
            missing, extra = sorted(expected - actual), sorted(actual - expected)
            raise ValueError(
                f"fields 鍵集合與 {self.document_type.value} 契約不符：缺 {missing}、多 {extra}"
            )
        return self


def empty_fields(document_type: DocumentType) -> Dict[str, FieldValue]:
    """回該型的固定鍵集合，每欄 absent。mapper 以此為底再覆寫，保證鍵集合恆定。"""
    return {name: FieldValue() for name in _FIELDS_BY_TYPE[document_type]}


__all__ = [
    "CONTRACT_FIELDS", "DocuMindPage", "DocuMindStats", "DocumentType", "FieldConflict",
    "FieldScalar", "FieldSource", "FieldValue", "MAPPING_VERSION", "MappingResult",
    "OcrMappingRequest", "OcrRaw", "Provenance", "REQUIRED_FOR_WRITE", "TRANSCRIPT_FIELDS",
    "empty_fields",
]
