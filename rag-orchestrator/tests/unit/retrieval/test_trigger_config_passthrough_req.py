"""補測試：檢索層觸發配置三欄透傳（spec trigger-vocabulary-debt・元件 1・R1.1/1.3）。

聚焦 `_format_result` 對 trigger_mode／trigger_keywords／immediate_prompt 三欄的透傳語意（純函式 → unit）：
- row 含三欄 → 產出 dict 帶對應三 key
- row 缺欄（DB NULL / 未 SELECT）→ 三 key 存在且為 None（消費層預設行為不變）

型別背景（依 knowledge_base schema）：
- trigger_mode  = varchar(20) → str | None
- immediate_prompt = text     → str | None
- trigger_keywords = text[]   → list[str] | None（psycopg2 直接回 Python list，比照既有 keywords 欄）
"""
import pytest

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = pytest.mark.unit


def _format(row):
    # _format_result 不觸及 reranker/連線副作用 → 以 unbound 方式呼叫，免實例化
    return VendorKnowledgeRetrieverV2._format_result(None, row)


@pytest.mark.req("trigger-vocabulary-debt:1.1")
def test_trigger_config_passthrough_present():
    """三欄有值時 → dict 原值透傳。"""
    row = {
        "id": 1,
        "trigger_mode": "manual",
        "trigger_keywords": ["還是不行", "試過了"],
        "immediate_prompt": "需要我幫您填寫表單嗎？",
    }
    r = _format(row)
    assert r["trigger_mode"] == "manual"
    assert r["trigger_keywords"] == ["還是不行", "試過了"]
    assert r["immediate_prompt"] == "需要我幫您填寫表單嗎？"


@pytest.mark.req("trigger-vocabulary-debt:1.3")
def test_trigger_config_passthrough_null():
    """row 缺三欄（DB NULL / 未 SELECT）→ 三 key 存在且為 None（消費層 else 分支行為不變）。"""
    row = {"id": 2}
    r = _format(row)
    assert "trigger_mode" in r and r["trigger_mode"] is None
    assert "trigger_keywords" in r and r["trigger_keywords"] is None
    assert "immediate_prompt" in r and r["immediate_prompt"] is None
