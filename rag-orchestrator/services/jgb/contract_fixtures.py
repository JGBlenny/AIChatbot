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


class ForeignContractFieldError(ValueError):
    """fixture 出現投影不存在的欄位（契約保真失效）。"""


def assert_contract_projection(record: "dict[str, Any]") -> None:
    foreign = set(record) - EXTERNAL_CONTRACT_FIELDS
    if foreign:
        raise ForeignContractFieldError(f"合約 fixture 含投影外欄位：{sorted(foreign)}")


class ContractFixtureTable:
    """可依 **request 參數**收斂的合約資料集。

    差異矩陣（刻意）：兩列的 `id`／`title`／`city・district`／`rent`／期間／
    `is_history` 皆不同——**任一過濾條件寫錯都會得到不同結果集**。
    """

    _ROWS: "tuple[dict[str, Any], ...]" = (
        {
            "id": 678, "status": 5, "bit_status": 47, "active": 1,
            "is_history": 0, "is_history_done": 0, "estate_id": 456,
            "title": "信義區套房A", "city": "台北市", "district": "信義區",
            "address": "信義路五段7號", "currency": "TWD",
            "rent": 25000.00, "deposit_amount": 50000.00,
            "date_start": 20260101, "date_end": 20261231,
            "allow_early_termination": True, "early_termination_days": 30,
            "is_auto_generate_invoice": 0, "to_user_connect": True,
            "is_tenant_registered": True, "to_user_phone": "0912345678",
            "to_user_email": "tenant@example.com", "property_purpose_key": 1,
            "father_id": None, "early_termination_wish_date_end": None,
            "enable_late_fee": 1, "calc_late_fee_buffer_days": 7, "late_fee_percent": 5.0,
            "early_termination_penalty_type": 1, "early_termination_penalty": 1.0,
            "early_termination_penalty_amount": 25000.00,
            "early_termination_notice_date": None,
            "contract_inviting_at": "2025-12-10 10:00:00",
            "contract_inviting_expire_at": "2026-01-09 10:00:00",
            "contract_inviting_sign_at": "2025-12-12 11:00:00",
            "contract_finish_sign_at": "2025-12-13 09:30:00",
            "to_user_login_email": "tenant@example.com", "is_newest": 1,
            "created_at": "2025-12-10 09:00:00", "updated_at": "2026-01-01 00:00:00",
        },
        {
            "id": 600, "status": 10, "bit_status": 3087, "active": 1,
            "is_history": 1, "is_history_done": 1, "estate_id": 400,
            "title": "中山區雅房B", "city": "台北市", "district": "中山區",
            "address": "中山北路二段10號", "currency": "TWD",
            "rent": 18000.00, "deposit_amount": 36000.00,
            "date_start": 20250101, "date_end": 20251231,
            "allow_early_termination": False, "early_termination_days": 0,
            "is_auto_generate_invoice": 0, "to_user_connect": True,
            "is_tenant_registered": True, "to_user_phone": "0923456789",
            "to_user_email": "tenant2@example.com", "property_purpose_key": 1,
            "father_id": None, "early_termination_wish_date_end": None,
            "enable_late_fee": 0, "calc_late_fee_buffer_days": 0, "late_fee_percent": 0.0,
            "early_termination_penalty_type": None, "early_termination_penalty": 0.0,
            "early_termination_penalty_amount": 0.0,
            "early_termination_notice_date": None,
            "contract_inviting_at": "2024-12-05 10:00:00",
            "contract_inviting_expire_at": "2025-01-04 10:00:00",
            "contract_inviting_sign_at": "2024-12-06 11:00:00",
            "contract_finish_sign_at": "2024-12-07 09:30:00",
            "to_user_login_email": "tenant2@example.com", "is_newest": 1,
            "created_at": "2024-12-05 09:00:00", "updated_at": "2025-12-31 23:59:59",
        },
    )

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
        for row in self._ROWS:
            assert_contract_projection(row)

    def rows(self) -> "list[dict[str, Any]]":
        return [dict(r) for r in self._ROWS]

    def by_id(self, contract_id: int) -> Optional["dict[str, Any]"]:
        for row in self._ROWS:
            if row["id"] == contract_id:
                return dict(row)
        return None
