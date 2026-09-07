"""
JGB 修繕（Repair）領域檔

`jgb2.query.repairs`（transport-agent-mcp-orchestration 收案修正 5）：修繕進度
決定性 fact-builder。facts 只引用系統存值（單號／物件名／分類／狀態／急迫／
建單時間／指派或處理中時間），⛔ 不推測未落欄位的內容。

`emergency_status` 語義（⚠️ 不可望文生義，見 conversational-repair 地雷紀錄）：
**2＝緊急、1＝非緊急**——與欄位名字面直覺相反，一律照 `RepairFixtureTable`／
`RepairApiController` 的既定映射讀值，不得自行改寫。
"""

from typing import Any, Callable, Optional

RepairFaceBuilder = Callable[[dict, str], str]   # (repair_row, user_question) -> facts 文字

#: `RepairApiController@index` mapping.status（`transport.py:_repairs_index` 同表）。
_STATUS_ZH: dict[int, str] = {
    1: "申請中", 2: "安排修繕", 16: "完成修繕", 32: "結單", 64: "封存",
}

#: `emergency_status`：1＝非緊急、2＝緊急。
_URGENCY_ZH: dict[int, str] = {1: "非緊急", 2: "緊急"}


def _status_zh(status: Any) -> str:
    try:
        return _STATUS_ZH.get(int(status), f"狀態值 {status}（系統未定義的狀態，請以後台顯示為準）")
    except (TypeError, ValueError):
        return "狀態不明"


def _urgency_zh(emergency_status: Any) -> str:
    try:
        return _URGENCY_ZH.get(int(emergency_status), "急迫程度不明")
    except (TypeError, ValueError):
        return "急迫程度不明"


def build_repair_status_facts(repair: dict, user_question: str = "") -> str:
    """修繕進度 facts：單號、物件名、分類、狀態中文、急迫、建單時間、
    指派／處理中時間——**決定性字串**，不推測未落欄位。
    """
    repair_id = repair.get("id", "?")
    estate_title = repair.get("estate_title") or "（未記錄物件名稱）"
    category_name = repair.get("category_name") or "（未分類）"
    lines = [f"修繕單 #{repair_id}（物件：{estate_title}，分類：{category_name}）："]

    lines.append(f"目前狀態：{_status_zh(repair.get('status'))}。")
    lines.append(f"急迫程度：{_urgency_zh(repair.get('emergency_status'))}。")

    apply_at = repair.get("apply_at")
    if apply_at:
        lines.append(f"建單時間：{apply_at}（系統存值）。")

    assign_at = repair.get("assign_at")
    complete_at = repair.get("complete_at")
    if complete_at:
        lines.append(f"完成修繕時間：{complete_at}（系統存值）。")
    elif assign_at:
        lines.append(f"已指派處理，指派時間：{assign_at}（尚未回報完成）。")
    else:
        lines.append("尚未指派處理。")

    broken_reason = repair.get("broken_reason")
    if broken_reason:
        lines.append(f"報修原因：{broken_reason}。")

    return "\n".join(lines)


# face → builder（面向名與 category_config 子分類一致）
REPAIR_FACE_BUILDERS: dict[str, RepairFaceBuilder] = {
    "修繕進度": build_repair_status_facts,
}
