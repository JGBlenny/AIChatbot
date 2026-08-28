"""e2e：Real API contract smoke（spec conversational-routing-execution 任務 12.1／12.2）。

要回答的**唯一**問題：

> **mock 假設與現實 contract 是否漂移**（params → endpoint → response schema）。

⚠️ 射程限制（R4.4，逐條照抄，實作不得擴張）：
```text
真 API SHALL **僅**用於確認 mock 假設與現實 contract 是否漂移；
SHALL NOT 作為驗證控制流的起點；
SHALL NOT 作為 Req.3 的主要驗收證據。
```

## 為什麼只比 schema、不比資料值

真資料每天都在變（帳單會新增、合約會換階段）。拿資料值當斷言基準，
測試會因為「業務照常運作」而變紅——那種紅不帶資訊，只會訓練人略過它。
本檔比的是**鍵的集合**：宣告的欄位還在不在、真 API 有沒有長出沒宣告的欄位。

## 「宣告」在哪裡

⚠️ 不另立一份 schema 快照。`services/jgb/fixtures.py` 的 `EXTERNAL_BILL_FIELDS`
與 `services/jgb/contract_fixtures.py` 的 `EXTERNAL_CONTRACT_FIELDS`
**本身就是** mock 假設（其檔頭明文對齊 jgb2 `formatBill` 的白名單投影）。
再抄一份等於讓兩份宣告各自漂移，屆時測試綠不代表 mock 正確。

## 預設略過，不進 CI 阻擋路徑（任務 12.1 明文）

需 `RUN_E2E=1`（conftest 既有 e2e 閘門）**且** `ALLOW_REAL_JGB_API=1`
（`scripts/run-tests.sh` 既有的顯式開關；未開時 runner 一律強制注入替身）。
略過理由帶 `[gate]` 前綴 ⇒ 歸入 `gate_skipped`，不混進 `env_skipped`。

## 成本量級（R7.2）

**零 LLM 呼叫**；每次執行 3 個唯讀 HTTP GET（contracts／bills／bill_detail 各一）。
⚠️ 本檔**不得**新增任何寫入端點——`_post_request` 的唯一呼叫者是 `/repairs`，
不在本檔可達集合內。
"""
import os

import pytest

from services.jgb.contract_fixtures import EXTERNAL_CONTRACT_FIELDS
from services.jgb.fixtures import EXTERNAL_BILL_FIELDS

pytestmark = pytest.mark.e2e

#: 顯式開關：未開 → `[gate]` 略過（預設不跑，不阻擋 CI）
_REAL_API_ON = os.getenv("ALLOW_REAL_JGB_API") == "1"
#: ⚠️ 開了 ALLOW_REAL_JGB_API 仍可能被 runner 或容器設成替身；替身回的是
#:    fixtures 自己，拿它比 fixtures 恆等於通過＝**假綠**，必須一併擋掉。
_MOCK_ON = os.getenv("USE_MOCK_JGB_API", "true").lower() != "false"

requires_real_api = pytest.mark.skipif(
    not _REAL_API_ON or _MOCK_ON,
    reason=("[gate] 契約 smoke 需真 JGB API：須 ALLOW_REAL_JGB_API=1 "
            "且 USE_MOCK_JGB_API=false（替身回 fixtures 自己，比對恆真＝假綠）"))

#: 取樣用角色；真實資料由該角色名下取得（唯讀）
_ROLE_ID = os.getenv("SMOKE_ROLE_ID", "20151")


def _rows(payload):
    """從 API envelope 取出資料列；形狀不符**大聲失敗**，不靜默回空。

    ⚠️ 靜默回 [] 會讓「取不到資料」偽裝成「沒有漂移」——否定結論的破壞力比肯定大。
    """
    assert isinstance(payload, dict), f"API envelope 不是 dict：{type(payload)}"
    data = payload.get("data")
    if isinstance(data, dict):
        data = data.get("data")
    assert isinstance(data, list), f"取不到資料列（data 形狀＝{type(data)}）——不是「沒有漂移」"
    return data


def schema_drift(rows, declared: "frozenset[str]") -> "dict[str, set]":
    """比對**鍵集合**，回 `{missing, extra}`；⛔ 不碰任何資料值。

    ```text
    missing  宣告有、真 API 沒有 → mock 假設了一個現實已不存在的欄位
    extra    真 API 有、宣告沒有 → contract 長出新欄位，fixtures 不再是忠實投影
    ```
    ⚠️ 取**聯集**而非首列：單列可能因該筆狀態而缺欄，那不是 contract 漂移。
    """
    seen: "set[str]" = set()
    for r in rows:
        assert isinstance(r, dict), f"資料列不是 dict：{type(r)}"
        seen |= set(r.keys())
    return {"missing": set(declared) - seen, "extra": seen - set(declared)}


# ── 正對照組：先證明比對器咬得動，再相信它對真 API 的 PASS ────────────────────
#
# ⚠️ 這條**不需要**真 API，永遠會跑。理由見專案規約「否定結論」：
#    回報「沒有漂移」之前，必須有一個已知必然被抓到的項目證明工具是活的。

@pytest.mark.req("conversational-routing-execution:4.4")
def test_drift_detector_sees_both_directions():
    declared = frozenset({"id", "total", "status"})
    # 缺一個宣告欄位 ＋ 多一個未宣告欄位
    rows = [{"id": 1, "total": 100, "unexpected_new_field": "x"}]
    d = schema_drift(rows, declared)
    assert d["missing"] == {"status"}, "比對器看不見『宣告有、真 API 沒有』"
    assert d["extra"] == {"unexpected_new_field"}, "比對器看不見『真 API 長出新欄位』"

    # 無漂移時必須乾淨——否則它只是恆紅，同樣沒有鑑別力
    clean = schema_drift([{"id": 1, "total": 100, "status": 2}], declared)
    assert clean == {"missing": set(), "extra": set()}


@pytest.mark.req("conversational-routing-execution:4.4")
def test_row_shape_violation_fails_loudly():
    """前置條件拿不到就要大聲失敗，不得靜默跳過核心判斷。"""
    with pytest.raises(AssertionError):
        _rows({"data": "not-a-list"})
    with pytest.raises(AssertionError):
        _rows("not-a-dict")


# ── 真 API 契約 smoke（預設略過）────────────────────────────────────────────

@pytest.fixture(scope="module")
def api():
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


@requires_real_api
@pytest.mark.req("conversational-routing-execution:4.4")
async def test_jgb_contracts_schema_has_not_drifted(api):
    """`jgb_contracts`：params → endpoint 可用，且回傳鍵集合與宣告一致。"""
    rows = _rows(await api.get_contracts(role_id=_ROLE_ID))
    assert rows, f"[前置未滿足] role_id={_ROLE_ID} 名下查無合約——無法判定漂移"
    d = schema_drift(rows, EXTERNAL_CONTRACT_FIELDS)
    assert not d["missing"] and not d["extra"], (
        f"jgb_contracts contract 漂移：宣告缺少={sorted(d['extra'])}｜"
        f"真 API 已無={sorted(d['missing'])}（n={len(rows)} 列聯集）")


async def _some_bills(api):
    """取一批真實帳單——**照 production 實際送的參數形狀**。

    ⚠️ 2026-08-28 實跑逼出的 contract 事實：`jgb_bills` **只帶 role_id 會回 401**
    （`{'code': 401, 'message': '請先登入以查詢您的個人資料。'}`）——
    它需要 `contract_ids` 之類的收窄參數。production 的 `contract_closeout`
    正是以 `contract_ids={row.id}` 呼叫（見該面向 grounding_scope 的 secondary_call）。
    ⇒ smoke 必須複製**真實呼叫形狀**，否則測到的是自己編的用法，不是產線契約。
    """
    from services.jgb.contracts import ContractBit

    contracts = _rows(await api.get_contracts(role_id=_ROLE_ID))
    assert contracts, f"[前置未滿足] role_id={_ROLE_ID} 名下查無合約，取不到 contract_id"

    # ⚠️ 決定性收窄，不是盲目加大取樣：**合約要簽完才會有帳單**
    #    （2026-08-28 實測：bit=15 的合約有 6／2 筆帳單；bit=1 的一筆都沒有）。
    #    照序取前 N 筆會抽到一堆剛建立的合約，然後把「取樣抽歪」誤讀成「查無帳單」。
    signed = [c for c in contracts
              if isinstance(c.get("bit_status"), int)
              and c["bit_status"] & ContractBit.SIGNED]
    assert signed, ("[前置未滿足] 取回的合約沒有任何一筆已簽約（bit_status & SIGNED）"
                    "——無法取得帳單樣本，這**不是**「沒有漂移」")

    for c in signed[:5]:                          # 少量取樣（R7.2：受控規模）
        cid = c.get("id")
        if not cid:
            continue
        rows = _rows(await api.get_bills(role_id=_ROLE_ID, contract_ids=str(cid)))
        if rows:
            return rows, cid
    pytest.skip("[gate] 已簽約合約取樣皆無帳單——無法判定 bills 契約漂移（非「沒有漂移」）")


@requires_real_api
@pytest.mark.req("conversational-routing-execution:4.4")
async def test_jgb_bills_schema_has_not_drifted(api):
    """`jgb_bills`（任務 12.2 標的之一）。"""
    rows, cid = await _some_bills(api)
    d = schema_drift(rows, EXTERNAL_BILL_FIELDS)
    assert not d["missing"] and not d["extra"], (
        f"jgb_bills contract 漂移（contract_ids={cid}）："
        f"真 API 長出未宣告欄位={sorted(d['extra'])}｜"
        f"宣告了但真 API 已無={sorted(d['missing'])}（n={len(rows)} 列聯集）")


@requires_real_api
@pytest.mark.req("conversational-routing-execution:4.4")
async def test_jgb_bill_detail_schema_has_not_drifted(api):
    """`jgb_bill_detail`（任務 12.2 標的之二）。

    ⚠️ 需要一個真實 bill_id——由上一步的列表取得，**不硬編**：硬編的 id 會在
    該筆被封存後讓測試變成「查無」，而查無會被誤讀成「沒有漂移」。
    """
    listing, _cid = await _some_bills(api)
    bill_id = listing[0].get("id")
    assert bill_id, "[前置未滿足] 帳單列表首筆沒有 id，無法取明細"

    detail = await api.get_bill_detail(bill_id=bill_id, role_id=_ROLE_ID)
    assert isinstance(detail, dict), f"bill_detail envelope 不是 dict：{type(detail)}"
    body = detail.get("data")
    rows = body if isinstance(body, list) else [body]
    assert rows and isinstance(rows[0], dict), "[前置未滿足] bill_detail 取不到內容"

    d = schema_drift(rows, EXTERNAL_BILL_FIELDS)
    # ⚠️ 明細**允許**比列表多欄（項目明細等），只擋「宣告有、真 API 沒有」那一向；
    #    多出來的欄位另行報告，不當失敗——否則每次上游加欄都會誤報。
    assert not d["missing"], (
        f"jgb_bill_detail 已無宣告欄位={sorted(d['missing'])}（bill_id={bill_id}）")
    if d["extra"]:
        print(f"ℹ️ [contract smoke] jgb_bill_detail 有未宣告欄位（僅報告不擋）："
              f"{sorted(d['extra'])}")
