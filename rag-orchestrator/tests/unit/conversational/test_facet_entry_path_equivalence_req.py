"""unit：兩條面向進場路徑的等價性（spec conversational-routing-execution 任務 2.5）。

**要回答的唯一問題**：`trigger_facet_key` 直達能否在「grounding → 真 brain → answer」
這件事上，與分類路由進場等價？等價才可用直達進場跑 C4b，
從而把 2.4 的供裝需求由「完整 KB ＋ embedding」降為「面向配置＋系統脈絡＋規則」。

⚠️ **不得以「Face key 一樣」判等價**——`handle_trigger_facet` 一律經 `_seed_repair_facet`，
而分類路由對「未宣告 enabled_gate／prefill_api 的診斷面向」直接走 `_conversational_respond`。
本檔鎖的是**程式側**的等價前提：當面向兩鍵皆未宣告且本輪無圖時，
`_seed_repair_facet` 的三個前置步驟全為 no-op，最終落到與分類路由**逐參數相同**的呼叫。

⚠️ 等價性是**配置相依**的：若日後有人替 `bill_diagnosis` 補上 `enabled_gate`，
等價立即失效。配置側的前提由面向 seed 的 integration 測試負責，本檔不重複。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class _Cfg:
    """未宣告 enabled_gate／prefill_api 的診斷面向（對齊 bill_diagnosis／billing_anomaly 實況）。"""
    key = "bill_diagnosis"
    enabled = True
    persona_role = "pm_bill_diagnosis"
    grounding_scope = {"select": "api", "endpoint": "jgb_bills",
                       "required_slots": ["bill_ref"]}


def _request(image_urls=None):
    r = MagicMock()
    r.vendor_id, r.session_id, r.user_id, r.role_id = 7, "s1", "u1", "20151"
    r.message, r.mode, r.stream = "帳單為什麼發不出去", "b2b", False
    r.image_urls = image_urls
    return r


@pytest.mark.req("conversational-routing-execution:3.2")
async def test_seed_reduces_to_plain_respond_for_diagnosis_facet():
    """兩鍵皆未宣告＋無圖 → 三個前置全 no-op → 落到與分類路由逐參數相同的呼叫。"""
    from routers import chat as chat_mod
    req = MagicMock()
    req.app.state.db_pool = MagicMock()

    with patch.object(chat_mod, "_conversational_respond",
                      new=AsyncMock(return_value="RESP")) as respond:
        out = await chat_mod._seed_repair_facet(_request(), req, _Cfg())

    assert out == "RESP"
    respond.assert_awaited_once()
    args, kwargs = respond.await_args
    assert kwargs["start_if_absent"] is True
    assert isinstance(kwargs["config"], _Cfg)
    assert kwargs["prefill"] is None, (
        "診斷面向不得帶 prefill——帶了就與分類路由不等價，"
        "會在進場輪多種入槽位而污染 C4b 的驗證標的")


@pytest.mark.req("conversational-routing-execution:3.2")
async def test_gate_and_prefill_are_noop_when_keys_absent():
    """逐一確認三個前置步驟對診斷面向為 no-op（不是靠上一條的整體結果推論）。"""
    from routers import chat as chat_mod
    req = MagicMock()
    req.app.state.db_pool = MagicMock()
    cfg = _Cfg()

    assert await chat_mod._repair_gate_open(req.app.state.db_pool, 7, cfg) is True, \
        "未宣告 enabled_gate 應恆放行"
    assert await chat_mod._recognize_repair_image(req, _request(image_urls=None)) is None, \
        "無圖應不打 Vision"
    assert await chat_mod._run_repair_prefill(req, _request(), cfg, None) is None, \
        "未宣告 prefill_api 應不預填"


@pytest.mark.req("conversational-routing-execution:3.2")
async def test_transaction_facet_is_not_equivalent():
    """反向鎖：宣告了 enabled_gate 的交易面向**不**等價——不得拿本結論套用到 repair_create。"""
    from routers import chat as chat_mod

    class _TxCfg(_Cfg):
        key = "repair_create"
        grounding_scope = {"enabled_gate": "repair_enabled",
                           "prefill_api": "get_tenant_contracts"}

    assert chat_mod._gate_switch_key(_TxCfg()) == "repair_enabled"
    assert chat_mod._gate_switch_key(_Cfg()) is None
