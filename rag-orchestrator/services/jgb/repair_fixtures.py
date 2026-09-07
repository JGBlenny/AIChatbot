"""修繕 fixture 表（transport-extension-full-coverage：repairs／repair_categories／
`POST /repairs`（create_repair）遷入 `JGBMockTransport`）。

資料來源：`services/jgb/fixture_data/demo_vendor4.json`（唯一來源）——
種子列 3001／3002 沿用既有方法級 mock 的原值（含 `emergency_status` 語義：
1=非緊急、2=緊急，見 conversational-repair 地雷紀錄，不可望文生義）。

⚠️ **新建工單 id 起始值刻意固定為 12346**：對齊既有 `_mock_create_repair` 的舊行為
（`tests/e2e/conversational/test_repair_scenarios_e2e_req.py` 的
`TEST_REPAIR_MOCK_TICKET` 預設即讀這個值）——變更會靜默打破那支 e2e 的預設期望。
"""

from typing import Any, Optional

from services.jgb.fixture_store import demo_rows, demo_section

#: `formatRepair()` 投影（`RepairApiController` 逐鍵，38 欄）。
EXTERNAL_REPAIR_FIELDS: "frozenset[str]" = frozenset({
    "id", "status", "emergency_status", "estate_id", "estate_title",
    "estate_full_address", "estate_room_number", "contract_id",
    "category_id", "category_name", "item_id", "item_name",
    "broken_reason", "broken_note", "broken_photos", "currency", "total",
    "manufacturer_name", "manufacturer_phone",
    "user_id", "user_name", "user_phone", "user_email",
    "to_user_id", "to_user_name", "to_user_phone", "to_user_email",
    "agent_user_id", "agent_name", "user_note", "to_user_note",
    "apply_at", "assign_at", "complete_at", "finish_at", "archive_at",
    "created_at", "updated_at",
})

#: 新建工單的起始 id（沿用既有 `_mock_create_repair` 行為，見上方模組說明）。
_FIRST_CREATED_ID = 12346


class ForeignRepairFieldError(ValueError):
    """fixture 出現投影不存在的欄位（契約保真失效）。"""


def assert_repair_projection(record: "dict[str, Any]") -> None:
    foreign = set(record) - EXTERNAL_REPAIR_FIELDS
    if foreign:
        raise ForeignRepairFieldError(f"修繕 fixture 含投影外欄位：{sorted(foreign)}")


class RepairFixtureTable:
    """可依 `status`／`estate_id`／`category_id`／`is_urgent`／`keyword` 收斂、可寫入的修繕資料集。"""

    def __init__(self) -> None:
        self._rows: "list[dict[str, Any]]" = list(demo_rows("repairs"))
        for row in self._rows:
            assert_repair_projection(row)
        self._next_id = _FIRST_CREATED_ID

    def rows(self) -> "list[dict[str, Any]]":
        return [dict(r) for r in self._rows]

    def by_id(self, repair_id: int) -> Optional["dict[str, Any]"]:
        for row in self._rows:
            if row["id"] == repair_id:
                return dict(row)
        return None

    def create(self, overrides: "dict[str, Any]") -> "dict[str, Any]":
        """`POST /repairs`（`RepairApiController@store`）：補滿投影欄位後附加一筆。"""
        base: "dict[str, Any]" = {k: None for k in EXTERNAL_REPAIR_FIELDS}
        base.update({
            "status": 1, "broken_photos": [], "currency": "TWD",
            "user_id": 1001, "user_name": "張管理",
            "user_phone": "0911-111-111", "user_email": "manager@example.com",
        })
        base.update(overrides)
        base["id"] = self._next_id
        self._next_id += 1
        assert_repair_projection(base)
        self._rows.append(base)
        return dict(base)


def repair_categories() -> "list[dict[str, Any]]":
    """`GET /repairs/categories`（`RepairApiController@categories`）樹狀資料。"""
    return demo_section("repair_categories") or []
