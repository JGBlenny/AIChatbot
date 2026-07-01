"""unit:api 型對話設定讀回一致 + reset 即時生效（conversational-diagnosis 任務 7.2 / R5.3, R5.4）。

驗證後端持久層契約（後端 payload 不變、沿用既有快取清除）：
  - `_config_from_row` 將 api 型 grounding_scope（endpoint/params/required_slots/result_mapping）
    原樣載回 ConversationalConfig（讀回一致，R5.3）；
  - `reset_cache` 後重載即反映編輯後的 api 設定（即時生效，R5.4）。
以假 db_pool 注入「對話規則」列，確定性 unit。前端 build/讀回由 7.1 `vite build` 編譯閘把關。
"""
import pytest

from services import conversational_config as cc

pytestmark = pytest.mark.unit


# api 型 grounding_scope（合約首案；全由設定提供）
API_GS = {
    "select": "api",
    "endpoint": "jgb_contracts",
    "required_slots": ["contract_ref"],
    "params": {
        "role_id": "{session.role_id}",
        "contract_ids": "{form.contract_ref|if_numeric}",
        "keyword": "{form.contract_ref|if_text}",
    },
    "result_mapping": {
        "list_path": "data", "id_field": "id",
        "label_field": "title", "refine_param": "contract_ids",
    },
}


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, *a, **k):
        return self._rows


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *a):
        return False


class _FakePool:
    def __init__(self, rows):
        self._conn = _FakeConn(rows)

    def acquire(self):
        return _FakeAcquire(self._conn)


def _api_row(grounding_scope=API_GS, category="條件診斷:合約", key="contract_diag"):
    cfg = {"key": key, "persona_role": "property_manager", "answer_mode": "conversational",
           "enabled": True, "topic_scope": {"mode": "category", "category": category},
           "grounding_scope": grounding_scope}
    return {"target_user": ["property_manager"], "generation_metadata": {"conversational_config": cfg}}


@pytest.fixture(autouse=True)
def _reset_cache():
    cc.reset_cache()
    yield
    cc.reset_cache()


# ── 讀回一致：api grounding_scope 原樣載回（R5.3，後端 payload 不變）──
@pytest.mark.req("conversational-diagnosis:5.3")
def test_config_from_row_preserves_api_grounding_scope():
    cfg = cc._config_from_row(["property_manager"],
                              {"conversational_config": _api_row()["generation_metadata"]["conversational_config"]})
    assert cfg is not None
    assert cfg.grounding_scope == API_GS                     # 完整原樣（含 params/result_mapping 巢狀）
    assert cfg.topic_scope == {"mode": "category", "category": "條件診斷:合約"}
    assert cfg.key == "contract_diag"
    assert cfg.enabled is True


# ── reset 後重載反映編輯後設定（R5.4 即時生效）──
@pytest.mark.req("conversational-diagnosis:5.4")
async def test_reset_cache_makes_edited_api_config_live():
    pool1 = _FakePool([_api_row()])
    cfg1 = await cc.config_for_category(pool1, "條件診斷:合約")
    assert cfg1.grounding_scope["endpoint"] == "jgb_contracts"

    # 模擬後台改設定（換 endpoint）→ 後端 _reset_caches() 已清快取
    cc.reset_cache()
    edited = {**API_GS, "endpoint": "jgb_contracts_v2"}
    pool2 = _FakePool([_api_row(grounding_scope=edited)])
    cfg2 = await cc.config_for_category(pool2, "條件診斷:合約")
    assert cfg2.grounding_scope["endpoint"] == "jgb_contracts_v2"  # 即時生效（讀到新值）


# ── 未清快取則沿用舊值（佐證「即時生效」確由 reset 觸發，而非每次查庫）──
@pytest.mark.req("conversational-diagnosis:5.4")
async def test_without_reset_keeps_cached_value():
    pool1 = _FakePool([_api_row()])
    await cc.config_for_category(pool1, "條件診斷:合約")  # 載入快取
    edited = {**API_GS, "endpoint": "jgb_contracts_v2"}
    pool2 = _FakePool([_api_row(grounding_scope=edited)])
    cfg = await cc.config_for_category(pool2, "條件診斷:合約")  # 未 reset → 仍用快取
    assert cfg.grounding_scope["endpoint"] == "jgb_contracts"
