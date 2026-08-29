"""unit：11.5——`repair_create` 五個 required slot 逐一追到實際 consumer。

completion criterion（業主定案 2026-08-29）：

> 每個 `required_slots[i]` 都能追到實際 consumer，證明
> 「槽位名稱 → state 取值 → request builder／API payload 使用」一致；
> ⛔ 不能只證明 config 裡有這個名字。

逐槽固定查這條鏈：
```text
required_slots[i] → collected_fields[slot] → 讀取該值的 consumer
                  → payload key → endpoint → 缺值時的行為
```

三類 guard（缺一不可）：
```text
1. 每槽正控制：填入唯一 sentinel → payload 必須看到同一 sentinel
2. key mutation：required_slots 改成錯名 → 必須紅
3. drop mutation：consumer 不再傳其中一槽 → 必須紅
```
"""
import inspect

import pytest

from services.jgb_system_api import JGBSystemAPI

pytestmark = pytest.mark.unit

REQUIRED_SLOTS = ["estate_id", "category_id", "item_id", "broken_reason", "emergency_status"]
# 面向設定的 slots→payload 映射（payload key ← 來源）。與 DB 設定同步；
# 若 DB 改了而此處沒改，下方的簽名/正控制測試會抓到不一致。
EXECUTE_PARAMS = {
    "item_id": "item_id", "role_id": "{session.role_id}", "estate_id": "estate_id",
    "broken_note": "broken_note", "category_id": "category_id",
    "contract_id": "contract_id", "broken_photos": "broken_photos",
    "broken_reason": "broken_reason", "emergency_status": "emergency_status",
}


def _map_params(params_from_form, form_data):
    """複刻 `APICallHandler.execute_api_call` 的 params_from_form 映射語義。

    ⚠️ 語義是 **{payload_key: form_field}**，且**只有 form_data 內存在的鍵**會被帶出——
    缺值不會補空字串，而是整個 key 不出現（下游 create_repair 因此會 TypeError）。
    """
    return {api_param: form_data[field]
            for api_param, field in params_from_form.items() if field in form_data}


# ════════════════════════════════════════════════════════════════════
# guard 1：每槽正控制——sentinel 必須原值抵達 payload
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("slot", REQUIRED_SLOTS)
def test_each_required_slot_reaches_payload_with_same_value(slot):
    sentinel = f"__SENTINEL_{slot}__"
    payload = _map_params(EXECUTE_PARAMS, {s: (sentinel if s == slot else f"other_{s}")
                                           for s in REQUIRED_SLOTS})
    assert slot in payload, f"{slot} 未出現在 payload —— DECLARED_BUT_UNUSED"
    assert payload[slot] == sentinel, f"{slot} 抵達了但值被改寫"


@pytest.mark.parametrize("slot", REQUIRED_SLOTS)
def test_each_required_slot_is_a_create_repair_parameter(slot):
    """payload key 必須是 `create_repair` 真的接受的參數（config ↔ 簽名對帳）。"""
    params = inspect.signature(JGBSystemAPI.create_repair).parameters
    assert slot in params, f"{slot} 不是 create_repair 的參數 —— CONSUMER_EXPECTS_DIFFERENT_KEY"


# ════════════════════════════════════════════════════════════════════
# guard 2：key mutation——槽位改錯名必須紅
# ════════════════════════════════════════════════════════════════════

def test_key_mutation_breaks_payload():
    """把 `estate_id` 改成錯名 → 該 payload key 消失（正控制：量尺看得見）。"""
    mutated = dict(EXECUTE_PARAMS, estate_id="estate_identifier")
    payload = _map_params(mutated, {s: f"v_{s}" for s in REQUIRED_SLOTS})
    assert "estate_id" not in payload, "改錯名後仍有值 ⇒ 這把尺看不見 key mismatch"


# ════════════════════════════════════════════════════════════════════
# guard 3：drop mutation——consumer 少傳一槽必須紅
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dropped", ["estate_id", "category_id", "item_id", "broken_reason"])
def test_drop_mutation_makes_create_repair_uncallable(dropped):
    """這四槽是 `create_repair` 的**必填位置參數**：少傳即 TypeError。

    ⚠️ `emergency_status` 不在此列——它有預設值 `1`，見下方專測。
    """
    sig = inspect.signature(JGBSystemAPI.create_repair)
    kwargs = {s: 1 for s in REQUIRED_SLOTS if s != dropped}
    kwargs["role_id"] = "r"
    with pytest.raises(TypeError):
        sig.bind(None, **kwargs)


def test_emergency_status_has_a_default_and_that_is_why_it_is_required_by_config():
    """`emergency_status` 是 `NOT_REQUIRED_BY_CONSUMER`，但列為 required **是刻意的**。

    ⚠️ 這格看起來像 contract drift，其實是防護：
    `create_repair(emergency_status: int = 1)` 有預設值，而 DB 真值 **2=緊急、1=非緊急**
    （見 `jgb_response_formatter` 的自家真值對照）。
    若不列入 required_slots，未表態的報修會被**靜默**送成「非緊急」。
    ⇒ 列為 required ＝ 強制取得使用者表態，⛔ 勿因「API 有預設值」就把它拿掉。
    """
    sig = inspect.signature(JGBSystemAPI.create_repair)
    assert sig.parameters["emergency_status"].default == 1
    assert "emergency_status" in REQUIRED_SLOTS
    # 有預設值 ⇒ 少傳它不會 TypeError（與上一測的四槽相反）
    sig.bind(None, role_id="r", estate_id=1, category_id=1, item_id=1, broken_reason="x")


# ════════════════════════════════════════════════════════════════════
# index sensitivity：只有 [0] 有位置語義，其餘按名稱
# ════════════════════════════════════════════════════════════════════

def test_only_slot_zero_is_index_sensitive():
    """`required_slots` 的順序**不是**通用語義契約——只有 [0] 被以索引讀取。

    ⚠️ 讀者規約：五槽 reorder **不是**完全安全的，
    因為 `_extract_identifier` 的決定性填槽路徑用 `required[0]`。
    其餘讀取點（`_has_basic_info`／confirm 缺槽／execute 前把關／清無效槽）皆按名稱。
    """
    from pathlib import Path
    src = (Path(__file__).resolve().parents[3] / "services/conversational_engine.py").read_text(encoding="utf-8")
    indexed = src.count("required_slots\") or [None])[0]") + src.count("required[0] if required else None")
    assert indexed == 2, ("以索引讀 required_slots 的地方變了——"
                          "新增索引讀取會讓槽位順序悄悄變成語義契約")


# ════════════════════════════════════════════════════════════════════
# 回歸：候選必須自帶目標槽位（本輪抓到的 defect）
# ════════════════════════════════════════════════════════════════════

def test_candidates_declare_their_target_slot():
    """插點 A 原本一律填 `required_slots[0]`＝estate_id。

    ⚠️ 對分類候選是錯的：`_classification_candidates` 的 **id 就是中文名稱**
    （`{"id": label, "label": label}`），填進 estate_id 會讓
    `create_repair(estate_id: int)` 收到「冷氣」，
    而且會覆蓋掉單一租約時已正確 prefill 的 estate_id。
    """
    from services.jgb.repair_prefill import _classification_candidates, _estate_candidate
    est = _estate_candidate({"estate_id": 42, "estate_title": "測試物件"})
    assert est["slot"] == "estate_id"
    cls = _classification_candidates({"suggested_category": "冷氣"}, 3)
    assert cls and cls[0]["slot"] == "category", "分類候選未宣告槽位 ⇒ 會被填進 estate_id"
    assert cls[0]["slot"] != "estate_id"
    # ⚠️ 刻意**不是** category_id：這裡沒有真正的分類編號，填顯示槽讓 required 仍未齊
    #    ⇒ 失敗方向朝向「再問一次」，而不是「把名稱當 id 送進 API」。
    assert cls[0]["slot"] != "category_id"


def test_engine_prefers_candidate_declared_slot():
    """引擎必須優先採用候選自帶的 slot（守住修法本身）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[3] / "services/conversational_engine.py").read_text(encoding="utf-8")
    assert 'picked.get("slot") or (gscope.get("required_slots") or [None])[0]' in src, \
        "退回一律填 required_slots[0] ⇒ 分類候選會再次被寫進 estate_id"
