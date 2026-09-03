"""unit 層：測資 fixture 本身要能過契約模型（需求 10.2）。

⚠️ 合約樣本是手構的（非真實 DocuMind 回應）——本檔只驗「fixture 形狀合法」，
⛔ 不得把它當 e2e 證據（需求 10.2／10.4 已明定）。
"""
import json
from pathlib import Path

import pytest

from services.ocr_mapping.models import DocumentType, OcrMappingRequest

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parent / "fixtures"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "user_id": "12291", "mode": "b2c",
            "target_user": "landlord", "session_id": "backtest_session_ocr_fixture"}


def load(name: str) -> dict:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.req("documind-ocr-mapping:10.2")
def test_transcript_fixture_is_deidentified_multi_page_and_valid():
    data = load("documind_transcript_sample.json")
    assert "去識別化" in data["_note"]
    req = OcrMappingRequest(**{k: v for k, v in data.items() if not k.startswith("_")}, **IDENTITY)
    assert req.document_type is DocumentType.transcript and len(req.pages) == 4
    assert req.pages[3].structured_data == {}                       # 空頁參與合併（R2.4）
    assert req.pages[1].llm_postprocessed is None                   # null 不是空物件
    assert req.needs_review is True and req.review_item_id


@pytest.mark.req("documind-ocr-mapping:10.2")
def test_contract_fixture_is_marked_non_real_and_valid():
    data = load("documind_contract_sample.json")
    assert "非真實" in data["_note"]                                # ⛔ 不得充當 e2e
    req = OcrMappingRequest(**{k: v for k, v in data.items() if not k.startswith("_")}, **IDENTITY)
    assert req.document_type is DocumentType.contract and len(req.pages) == 3
    sd = req.pages[0].structured_data
    assert set(sd) >= {"contract_metadata", "parties", "financial_terms"}   # DocuMind contract 型三組
    # 同一欄位跨頁出現不同格式（民國 vs 西元）——留給 R2.3／R5.3 的衝突測試用
    assert req.pages[0].structured_data["contract_metadata"]["signing_date"] != req.pages[2].structured_data["contract_metadata"]["signing_date"]
