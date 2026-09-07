"""團隊成員 fixture 表（transport-extension-full-coverage：team_members／member_permissions
遷入 `JGBMockTransport`）。

資料來源：`services/jgb/fixture_data/demo_vendor4.json`（唯一來源）。三種形狀刻意併存：
擁有者（`character_id=0`）、一般成員、`character_name` 為 `None` 的成員
（pivot 無 character_id，見 `TeamMemberApiController::members():135-137` 的 null 分支）。

⚠️ `email`／`name` 為**內部欄位**：`members()` 只回 `member_user_id`／`character_id`／
`character_name`／`is_owner`／`match_field`（:112 起不回明文個資），
`permissions()` 也不投影這兩鍵——一律不得出現在 API 回應。
"""

from typing import Any, Optional

from services.jgb.fixture_store import demo_rows

#: `TeamMemberApiController::ABILITY_WHITELIST`（:17-32）逐鍵 32 個。
#: production 一律回滿 32 鍵（成員取 `Role::getPermissionByCharacter` 的值，擁有者全 true）。
ABILITY_WHITELIST: "tuple[str, ...]" = (
    "show_estate", "show_owner_estate", "add_estate", "edit_estate",
    "assign_estate", "export_estate",
    "show_contract", "show_owner_contract", "add_contract", "edit_contract",
    "send_contract_invitation", "sign_contract", "assign_contract", "export_contract",
    "show_bill", "show_owner_bill", "add_bill", "receive_bill", "pay_bill", "export_bill",
    "show_role", "edit_role", "show_role_team", "edit_role_team",
    "edit_role_payment", "edit_role_subscription",
    "show_repair", "show_owner_repair", "edit_repair", "export_repair",
    "show_recharge_account", "edit_recharge_account",
)

#: 非擁有者成員預設授予的能力子集（沿用既有替身行為，2026-08-25 盤查訂定）。
_GRANTED_FOR_MEMBER: "frozenset[str]" = frozenset({
    "show_owner_bill", "show_owner_contract", "show_owner_estate",
    "show_repair", "show_owner_repair",
})

INTERNAL_TEAM_MEMBER_FIELDS: "frozenset[str]" = frozenset({"email", "name"})
EXTERNAL_TEAM_MEMBER_FIELDS: "frozenset[str]" = frozenset({
    "member_user_id", "character_id", "character_name", "is_owner",
})


class TeamMemberFixtureTable:
    """可依 `keyword`（email／name contains）與 `user_id` 收斂的團隊成員資料集。"""

    def __init__(self) -> None:
        self._rows: "list[dict[str, Any]]" = list(demo_rows("team_members"))

    def rows(self) -> "list[dict[str, Any]]":
        return [dict(r) for r in self._rows]

    def by_user_id(self, user_id: Any) -> Optional["dict[str, Any]"]:
        for row in self._rows:
            if str(row["member_user_id"]) == str(user_id):
                return dict(row)
        return None

    def abilities_for(self, member: "dict[str, Any]") -> "dict[str, bool]":
        """依角色計算 32 鍵能力旗標——擁有者全 true，一般成員取授予子集。"""
        if member.get("is_owner"):
            return {k: True for k in ABILITY_WHITELIST}
        return {k: (k in _GRANTED_FOR_MEMBER) for k in ABILITY_WHITELIST}
