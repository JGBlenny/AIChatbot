"""合約 fixture 表（transport-extension：contracts 遷入 `JGBMockTransport`）。

**定位**：與 `fixtures.py`（帳單）同款——建立 deterministic synthetic API state，
使 production adapter「第一次查回 N 筆 → 使用者給識別 → 第二次依 request 重查」
這段行為**可被實測**，而不是被方法級 mock 吃掉。

**保真度：已對照 jgb2 原始碼**（2026-08-25，M2 audit）——
`jgb2/app/Http/Controllers/External/ContractApiController.php::formatContract()` 逐鍵，
與 `index()` 的 where 條件（`active=1`、`is_newest=1`、`contract_ids`、`keyword`）。
兩列資料值沿用原方法級 mock，使遷移對既有呼叫點為行為保持。
"""

from typing import Any, Optional

from services.jgb.fixture_store import demo_rows, demo_visibility

#: 現行方法級 mock 所使用的欄位集（見上方保真度聲明）
EXTERNAL_CONTRACT_FIELDS: "frozenset[str]" = frozenset({
    "id", "status", "bit_status", "active", "is_history", "is_history_done",
    "estate_id", "title", "city", "district", "address", "currency",
    "rent", "deposit_amount", "date_start", "date_end",
    "allow_early_termination", "early_termination_days", "is_auto_generate_invoice",
    "to_user_connect", "is_tenant_registered", "to_user_phone", "to_user_email",
    "property_purpose_key", "father_id", "early_termination_wish_date_end",
    "enable_late_fee", "calc_late_fee_buffer_days", "late_fee_percent",
    "early_termination_penalty_type", "early_termination_penalty",
    "early_termination_penalty_amount", "early_termination_notice_date",
    # G1 簽約邀請/完成簽約時間點、G2 承租方登入 email、G4 是否最新版本（formatContract 逐鍵）
    "contract_inviting_at", "contract_inviting_expire_at", "contract_inviting_sign_at",
    "contract_finish_sign_at", "to_user_login_email", "is_newest",
    "created_at", "updated_at",
})


#: **內部欄位**：production `index()` 有 `select` 也**確實用來過濾**，但 `formatContract()`
#: **不投影**（見 ContractApiController.php:45 select vs :108-155 formatContract）。
#: fixture 需要它才能重現 `user_id` 過濾，故存在於列上、但**不得出現在回應**。
INTERNAL_CONTRACT_FIELDS: "frozenset[str]" = frozenset({"to_user_id"})


class ForeignContractFieldError(ValueError):
    """fixture 出現投影不存在的欄位（契約保真失效）。"""


def assert_contract_projection(record: "dict[str, Any]") -> None:
    """fixture 列只能由「投影欄位 ∪ 內部欄位」組成。"""
    foreign = set(record) - EXTERNAL_CONTRACT_FIELDS - INTERNAL_CONTRACT_FIELDS
    if foreign:
        raise ForeignContractFieldError(f"合約 fixture 含投影外欄位：{sorted(foreign)}")


def project_contract(record: "dict[str, Any]") -> "dict[str, Any]":
    """輸出投影：剝掉內部欄位，使回應與 `formatContract()` 的鍵集一致。"""
    return {k: v for k, v in record.items() if k not in INTERNAL_CONTRACT_FIELDS}


class ContractFixtureTable:
    """可依 **request 參數**收斂的合約資料集。

    差異矩陣（刻意）：兩列的 `id`／`title`／`city・district`／`rent`／期間／
    `is_history`／`to_user_id` 皆不同——**任一過濾條件寫錯都會得到不同結果集**。

    ⚠️ 兩列分屬**不同租客**（9001／9002），故 `user_id` 過濾可證「1 筆」與「0 筆」兩型；
    「N 筆」型**不在本表射程**——它由 `tests/unit/conversational/test_repair_prefill_req.py`
    的 `_MANY` 測試替身涵蓋。不要為了湊 N 筆在此加第三列（會動到已被 4 個斷言
    釘住的 `[678, 600]` 差異矩陣）。
    """

    #: `getMapping()` 的 bit_status 標籤（沿用方法級 mock 原文）
    MAPPING: "dict[str, dict[str, str]]" = {
        "bit_status": {
            "1": "已建立", "2": "已發送簽約邀請", "4": "租客已簽名", "8": "雙方簽名完成",
            "16": "已發送點交", "32": "租客同意點交", "64": "已發送點退",
            "128": "租客同意點退", "256": "提前解約中", "512": "提前解約已確認",
            "1024": "歷史合約", "2048": "歷史完成",
        },
    }

    def __init__(self) -> None:
        #: 資料來源：`services/jgb/fixture_data/demo_vendor4.json`（唯一來源）——
        #: 本類不再硬編碼列值，每個實例各自持有一份可變列表（寫入不外溢到其他實例）。
        self._rows: "list[dict[str, Any]]" = list(demo_rows("contracts"))
        for row in self._rows:
            assert_contract_projection(row)
        #: `{str(contract_id): [user_id, ...]}`——目前僅宣告，未接上 `_contracts_index` 的過濾。
        self._visibility: "dict[str, list[int]]" = demo_visibility("contract")

    def rows(self) -> "list[dict[str, Any]]":
        return [dict(r) for r in self._rows]

    def by_id(self, contract_id: int) -> Optional["dict[str, Any]"]:
        for row in self._rows:
            if row["id"] == contract_id:
                return dict(row)
        return None

    def visible_to(self, contract_id: int) -> Optional["list[int]"]:
        return self._visibility.get(str(contract_id))

    def create(self, overrides: "dict[str, Any]") -> "dict[str, Any]":
        """寫入路徑（`POST /agent/v1/contracts`）：驗投影後附加一筆。

        預設 `active=1`／`is_newest=1`——`_contracts_index` 的恆定 where 條件
        （對齊 `ContractApiController@index:51-52`），未帶這兩鍵的新建合約
        在 index 查詢中會被恆定條件濾掉，等於「建了卻查不到」。
        """
        row = {"active": 1, "is_newest": 1, **overrides}
        assert_contract_projection(row)
        self._rows.append(row)
        return dict(row)
