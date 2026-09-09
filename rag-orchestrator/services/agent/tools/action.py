"""`jgb2.action.<x>` 寫入型工具（子 spec `agent-write-tools`・W4）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 2 stage 表與
元件 3 的 `jgb2.action.<x>` 列（`{payload, confirmation_token} → {receipt}`）。

## 這一層負責什麼、不負責什麼
- **不負責確認兌現**：那是 `ToolRegistry.register()` 對 `scope=="write"` 強制包上的
  共用 wrapper（`registry._wrap_write_tool`：`assert_redeemed(token, session_id)`
  ＋ pm 雙證）。⛔ 本檔不得自己再寫一份兌現邏輯，也不得假設「有 token 就是確認過」。
- **負責資源層級的範圍檢查**：只有工具自己知道它要動哪一筆資源，所以「這張帳單
  在不在這個身分看得到的清單裡」「這個物件名字查不查得到」寫在這裡。**寫之前先讀
  一次**，讀不到就 `NO_MATCH`，⛔ 不「先寫了再說」。
- **負責形狀契約**：payload 的形狀**沿用 `confirm_card.render()`**（同一套規則），
  ⛔ 不另立第二套——兩套規則遲早會分岔成「卡上驗得過、執行時驗不過」。

## 冪等鍵＝confirmation_token（design 元件 3「下游 idempotency key＝token」）
同一張 token 重送 ⇒ 下游回同一份 receipt、不重複建。⚠️ 這是**第二道**保險：
第一道是 Runtime 用 session 狀態裡的 `receipt` 直接短路（R4.3），根本不會走到這裡。

## ⛔ 憑證面
demo 只走替身 transport（`USE_MOCK_JGB_API=true`）。真 `agent/v1` 的簽章 client
與憑證儲存／輪替 **不在本契約**（Plan §2 非目標，S-3 DEFER）。

## `emergency_status` 是已知地雷
`1＝非緊急、2＝緊急`（jgb2 DB 真值，⛔ 不可望文生義）。本檔不自己對照，
值域檢查交給 `confirm_card`（那裡與 `jgb_response_formatter` 逐鍵對帳過）。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Final, Optional

from services.agent.confirm_card import (
    DEFAULT_CATEGORY_NAME,
    ConfirmCardError,
    category_name_of,
    emergency_status_of,
    render,
)
from services.agent.identity import Identity
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.registry import ToolResult, ToolSpec
# ⚠️ **import 模組、⛔ 不 `from … import _today`**：時鐘要在呼叫點取值
# （與 `tools/confirm.py`、`runtime.py` 同法），這樣測試 monkeypatch 才蓋得到。
from services.jgb import bills

logger = logging.getLogger(__name__)

BILL_DUE_EXTEND_ACTION: Final[str] = "bill_due_extend"
REPAIR_CREATE_ACTION: Final[str] = "repair_create"

BILL_DUE_EXTEND_NAME: Final[str] = f"jgb2.action.{BILL_DUE_EXTEND_ACTION}"
REPAIR_CREATE_NAME: Final[str] = f"jgb2.action.{REPAIR_CREATE_ACTION}"

#: 兩支工具共用的 `input_schema`。
#: ⚠️ `confirmation_token` **必須**在 `properties` 裡——`register()` 會補
#: `additionalProperties: False`，守門②放行後第④步才不會把它擋成 `INVALID_INPUT`。
_ACTION_INPUT_SCHEMA: Final[dict] = {
    "type": "object",
    "properties": {
        "payload": {"type": "object"},
        "confirmation_token": {"type": "string"},
    },
    "required": ["payload", "confirmation_token"],
    "additionalProperties": False,
}


def _action_spec(name: str, description: str) -> ToolSpec:
    """兩支工具的 spec 只差名字與說明；stage 表由 design 元件 2 定（pm M1／tenant M4，
    prospect **缺鍵＝永不可見**）。`mcp_only=True` 是硬性要求（`register()` 會擋）。"""
    return {
        "name": name,
        "description": description,
        # 字面量（⛔ 不用 dict(常數)）：稽核不變量 27 的 AST 掃描只認 ast.Dict，寫成常數呼叫會被靜默略過
        "input_schema": {
            "type": "object",
            "properties": {
                "payload": {"type": "object"},
                "confirmation_token": {"type": "string"},
            },
            "required": ["payload", "confirmation_token"],
            "additionalProperties": False,
        },
        "scope": "write",
        "mcp_only": True,
        "stage": {"property_manager": "M1", "tenant": "M4"},
    }


#: ⚠️ description 是**模型唯一看得到的 payload 契約**——模型要靠它組
#: `confirm.request` 的 `payload` 字串。逐字寫**定義**，⛔ 不寫例子
#: （例子會被模型當成可以照抄的值）。
BILL_DUE_EXTEND_SPEC: ToolSpec = _action_spec(
    BILL_DUE_EXTEND_NAME,
    "把一張帳單的到期日往後調整。"
    "本工具只能在使用者按下確認按鈕之後由系統執行；"
    "要發動它，必須先用 confirm.request 出示確認，payload 的 action 填 bill_due_extend。"
    "payload 欄位定義："
    "bill_id＝要調整的帳單編號；"
    "date_expire_before＝這張帳單目前的到期日，八位數字的年月日，"
    "必須取自系統查到的帳單資料，⛔ 不要向使用者索取、也不要憑印象填；"
    "取得方式＝出示確認之前先以 jgb2.query.bills（ref 填帳單編號）查這張帳單，"
    "從回傳的繳費期限取值；查不到這張帳單就不能出確認；"
    "days＝往後延的天數，正整數；"
    "date_expire_after＝調整後的到期日，八位數字的年月日，"
    "延後天數從原到期日或今天較晚的一天起算；算出來的新到期日一定在今天之後，"
    "不一致一律拒絕；"
    "這個日期不得早於今天；由起算日加上天數算出來就一定在今天之後，"
    "⛔ 不因原到期日已過而反問要改到哪一天，直接提出確認。"
    "四個欄位都必填，系統不會替你推算任何一個。",
)

REPAIR_CREATE_SPEC: ToolSpec = _action_spec(
    REPAIR_CREATE_NAME,
    "為某個物件建立一張修繕單。"
    "本工具只能在使用者按下確認按鈕之後由系統執行；"
    "要發動它，必須先用 confirm.request 出示確認，payload 的 action 填 repair_create。"
    "payload 欄位定義："
    "estate_name＝業務口述的物件名稱，照原話填入，由系統比對；⛔ 不要為了核對名稱反問業務；"
    "category_name＝口述能對上分類樹的一個分類時填該分類，對不上留空"
    "（選填；分類樹以 jgb2.query.repairs 查詢修繕分類取得，分類樹涵蓋不到時"
    "填該分類的上層大類；業務沒講就不要填，系統會歸到「其他」）；"
    "⛔ 不得為了分類反問業務、⛔ 不得自行編造分類名稱；"
    "description＝使用者口述的問題原文，⛔ 不因缺照片或補問而丟掉"
    "（允許是空字串，但這個欄位一定要存在，沒有描述就填空字串）；"
    "⛔ 不要為了補描述反問或代寫；"
    "emergency_status＝急迫程度的系統值（選填），對使用者只說緊急／非緊急，"
    "⛔ 不講欄位名或數值：業務說緊急才填 2，其餘不填（系統以非緊急建單）；"
    "⛔ 不要為了問急迫程度延後出示確認或反問。"
    "estate_name 與 description 必填（description 可為空字串），其餘兩欄缺值由系統補。",
)


# ---------------------------------------------------------------------------
# 共用小工具
# ---------------------------------------------------------------------------
def _no_match() -> ToolResult:
    return ToolResult(ok=False, error="NO_MATCH")


def _invalid_input() -> ToolResult:
    return ToolResult(ok=False, error="INVALID_INPUT")


def _receipt(receipt: dict, text_for_model: str) -> ToolResult:
    """成功回傳的唯一形狀：`data={"receipt": {...}}`。

    ⛔ `receipt` 只放**我們自己導出的識別碼與日期**，不放下游回應裡的任何自由文字：
    這份 dict 會被 Runtime 存進 session 狀態（`form_sessions.collected_data`）並
    餵給回覆句 formatter，把下游訊息原樣帶進來等於在確認鏈末端開一個沒人檢查的出口。
    """
    return ToolResult(ok=True, data={"receipt": receipt}, provenance=[],
                      text_for_model=text_for_model)


def _scalar(value: Any, *, max_len: int = 64) -> str:
    """把下游回應的一個欄位收斂成短字串；不是 str／int ⇒ `""`（⛔ 不硬轉）。"""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return ""
    text = str(value).strip()
    return text if 0 < len(text) <= max_len else ""


def _validated_payload(action: str, args: dict, *,
                       today: Optional[date] = None) -> Optional[dict]:
    """`args["payload"]` 過**與確認卡同一套**的形狀檢查；不合 ⇒ `None`。

    ⛔ 不另立第二套規則：`render()` 就是「使用者看到的那張卡認不認得這份 payload」的
    唯一判準，這裡只是丟掉它的輸出、留下它的驗證。

    Args:
        today: 驗算基準（`bill_due_extend` 的起算日）。**關鍵字參數**，由呼叫點以
            `bills._today()` 取值；⛔ 不從 `payload` 讀（render 對保留鍵一律拋）。
            缺省 `None` ⇒ 舊行為（沒有日期語義的動作用這條）。

    ⚠️ **跨午夜規則**（帶 `today` 時）：等式對 `today` **或 `today − 1 天`** 任一
    成立即通過。理由是決定性的、⛔ 不是特例分支：確認 token 的 TTL 是 600 s
    （`confirm.CONFIRM_TOKEN_TTL_S`）＜ 24 h ⇒ 出卡日只可能是兌現當日或前一天，
    兩者之外的日期本來就兌現不了。若只用兌現當日做嚴格等式，一張 23:59 出的卡在
    00:01 兌現就會 `INVALID_INPUT`，而那時 token 已經燒掉、使用者無從補救。
    ⚠️ 這是**驗算**的容忍度，⛔ 不是閘門的：`runtime` 的兌現閘仍以兌現當日的新
    時鐘檢查 `fields_before_today`（縱深），所以 `today − 1` 這條路徑救不了一張
    新到期日已經過去的卡。
    """
    payload = args.get("payload")
    if not isinstance(payload, dict):
        return None
    candidates = [today] if today is None else [today, today - timedelta(days=1)]
    for base in candidates:
        try:
            render(action, payload, today=base)
        except ConfirmCardError:
            continue
        return payload
    # ⛔ 例外訊息不外流（裡面有欄位名）；除錯落在這一行的 log，⛔ 不印欄位值。
    logger.info("[agent] %s：payload 形狀不符確認卡契約", action)
    return None


def _iso_date(yyyymmdd: Any) -> str:
    """`YYYYMMDD`（str／int）→ `YYYY-MM-DD`；形狀不合 ⇒ `""`。

    ⚠️ `render()` 已經驗過形狀，這裡再驗一次是因為**本函式的輸出會進出向請求**——
    ⛔ 不讓一個沒驗過的字串直接拼進 URL／body。
    """
    text = str(yyyymmdd).strip()
    if len(text) != 8 or not text.isdigit():
        return ""
    try:
        d = date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError:
        return ""
    return d.isoformat()


def _identity_pair(identity: Identity) -> tuple:
    """`(role_id, user_id)`；⚠️ **兩者都要**——pm 的讀是刻意的單證路徑，
    寫不是（S-8）。共用 wrapper 已經擋過 pm 缺 `user_id`，這裡不重複判定，
    只是把值取出來。"""
    return getattr(identity, "role_id", None), getattr(identity, "user_id", None)


# ---------------------------------------------------------------------------
# jgb2.action.bill_due_extend
# ---------------------------------------------------------------------------
async def bill_due_extend(identity: Identity, args: dict) -> ToolResult:
    """把 `payload.bill_id` 的到期日改成 `payload.date_expire_after`。

    順序固定：形狀 → **範圍讀** → 寫。範圍讀走 `get_bills(viewer_user_id=...)`，
    即替身依 fixture 宣告的可見性過濾後的清單；帳單不在那份清單裡 ⇒ `NO_MATCH`
    （⛔ 不用 `get_bill_detail`：那條路只要 `role_id` 就受理，等於沒有圈定）。

    ⚠️ 送出的是**絕對日期**（`date_expire_after`），⛔ 不是位移天數：使用者確認的
    是一個確定的日期，位移在下游重算一次就多一個「算出不同結果」的機會。
    """
    # ⚠️ 時鐘在**呼叫點**取（第三個呼叫點；見 `confirm_card` 檔尾「日期有效性」）：
    #    起算日＝原到期日與今天較晚者，兌現端不帶 today 就會把每一張逾期帳單的卡
    #    在 token 已經燒掉之後判成 `INVALID_INPUT`。
    payload = _validated_payload(BILL_DUE_EXTEND_ACTION, args, today=bills._today())
    if payload is None:
        return _invalid_input()
    bill_id = str(payload["bill_id"]).strip()
    after_iso = _iso_date(payload["date_expire_after"])
    if not after_iso:
        return _invalid_input()

    role_id, user_id = _identity_pair(identity)
    if not role_id or not user_id:
        return _no_match()

    api = jgb2_tools._get_api()
    visible = jgb2_tools._rows_of(
        await api.get_bills(role_id=role_id, user_id=user_id, viewer_user_id=user_id)
    )
    if not any(str(row.get("id")) == bill_id for row in visible):
        # 不存在／不在可見範圍——**兩者共用同一個回答**（同 jgb2 的 404 資訊折疊：
        # 「帳單不存在或無權存取」），⛔ 不細分成可探測的預言機。
        return _no_match()

    resp = await api.agent_patch_bill_due_date(
        bill_id, after_iso, idempotency_key=args.get("confirmation_token")
    )
    if not (resp or {}).get("success"):
        # 誠實回錯：⛔ 不重試、⛔ 不把下游訊息轉給模型（Runtime 會用固定句回覆）。
        logger.warning("[agent] bill_due_extend 下游寫入未成功")
        return _no_match()

    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    return _receipt(
        {
            "bill_id": _scalar(data.get("id")) or bill_id,
            "before": _scalar(data.get("due_date_before")),
            "after": _scalar(data.get("due_date_after")) or after_iso,
        },
        "帳單到期日已更新。",
    )


# ---------------------------------------------------------------------------
# jgb2.action.repair_create
# ---------------------------------------------------------------------------
def _resolve_estate(rows: list, estate_name: str) -> Optional[dict]:
    """物件名稱 → 唯一一列；**判不出唯一一列就回 `None`**（⛔ 不挑第一筆）。

    先取 `title` 完全相同的那些列；恰好一列 ⇒ 就是它。否則退回「整份候選恰好
    一列」才算數。⚠️ `get_estate_status` 查無時回的是 sentinel（`found=False`），
    在這裡會因為沒有 `id` 而自然落空——但仍明確濾掉，⛔ 不靠巧合。
    """
    candidates = [r for r in rows if isinstance(r, dict) and r.get("found") is not False]
    exact = [r for r in candidates
             if str(r.get("title") or "").strip() == estate_name.strip()]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _resolve_category(tree: list, category_name: str) -> Optional[tuple]:
    """分類名稱 → `(category_id, item_id)`；查不到 ⇒ `None`。

    兩種合法命中，**都必須是完全相同的名稱**：
      - 命中**父節點**（大類）⇒ `(父.id, None)`。line-bot 線③：分類樹涵蓋不到時
        退回大類是刻意允許的，⛔ 不編一個不存在的葉節點來湊。
      - 命中**葉節點**（細項）⇒ `(父.id, 葉.id)`。
    ⛔ 不做模糊比對：猜錯分類的代價是一張分類錯誤的工單，而它看起來完全正常。
    """
    name = category_name.strip()
    for node in tree or []:
        if not isinstance(node, dict):
            continue
        if str(node.get("name") or "").strip() == name:
            return (node.get("id"), None)
    for node in tree or []:
        if not isinstance(node, dict):
            continue
        for item in node.get("items") or []:
            if isinstance(item, dict) and str(item.get("name") or "").strip() == name:
                return (node.get("id"), item.get("id"))
    return None


async def repair_create(identity: Identity, args: dict) -> ToolResult:
    """依 `payload` 建立一張修繕單。

    順序固定：形狀 → **範圍讀**（物件名稱查得到、分類名稱在分類樹裡）→ 寫。
    兩個名稱任一解不出唯一結果 ⇒ `NO_MATCH`／`INVALID_INPUT`，⛔ 不挑一個最像的。

    **允許父節點分類＋空描述**（Plan W4 驗收、line-bot 線③ Q）：分類樹涵蓋不到時
    退回大類、描述留空，照樣開得成單。
    """
    payload = _validated_payload(REPAIR_CREATE_ACTION, args)
    if payload is None:
        return _invalid_input()
    estate_name = str(payload["estate_name"]).strip()
    # delta4：分類缺值 ⇒ 歸「其他」大類（依名稱在分類樹裡解，⛔ 不寫死 id）；急迫缺值 ⇒ 非緊急。
    category_name = category_name_of(payload) or DEFAULT_CATEGORY_NAME
    description = str(payload["description"])
    emergency_status = emergency_status_of(payload)

    role_id, user_id = _identity_pair(identity)
    if not role_id or not user_id:
        return _no_match()

    api = jgb2_tools._get_api()

    estate = _resolve_estate(
        jgb2_tools._rows_of(
            await api.get_estate_status(role_id=role_id, keyword=estate_name)
        ),
        estate_name,
    )
    if estate is None or estate.get("id") is None:
        return _no_match()

    resolved = _resolve_category(
        jgb2_tools._rows_of(await api.get_repair_categories()), category_name
    )
    if resolved is None:
        # 分類名稱不在分類樹裡——這是 payload 的內容問題（形狀是對的），
        # ⛔ 不退回「隨便挑一個大類」。
        return _invalid_input()
    category_id, item_id = resolved

    resp = await api.create_repair(
        role_id=role_id,
        estate_id=estate["id"],
        category_id=category_id,
        # ⚠️ 父節點分類 ⇒ `item_id=None`＝**未指定細項**，⛔ 不填 0 或任意葉節點 id。
        item_id=item_id,
        # ⚠️ 欄位對映（本檔的實作決定）：使用者在卡上確認的「問題描述」進
        #    `broken_reason`；`broken_note` 留空。⛔ 不把同一段文字複製兩份，
        #    也 ⛔ 不從分類樹的 `broken_reasons` 列舉裡挑一個看起來像的。
        broken_reason=description,
        broken_note="",
        emergency_status=emergency_status,
        idempotency_key=args.get("confirmation_token"),
    )
    if not (resp or {}).get("success"):
        logger.warning("[agent] repair_create 下游寫入未成功")
        return _no_match()

    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    repair_id = _scalar(data.get("id"))
    if not repair_id:
        # 下游說成功卻沒給單號：⛔ 不編一個，也 ⛔ 不宣稱成功。
        logger.warning("[agent] repair_create 下游回應缺單號")
        return _no_match()
    return _receipt(
        {
            "repair_id": repair_id,
            "estate_id": _scalar(estate.get("id")),
            "created_at": _scalar(data.get("created_at"), max_len=32),
        },
        "修繕單已建立。",
    )


ACTION_SPECS: Final[tuple] = (
    (BILL_DUE_EXTEND_SPEC, bill_due_extend),
    (REPAIR_CREATE_SPEC, repair_create),
)

__all__ = [
    "ACTION_SPECS",
    "BILL_DUE_EXTEND_ACTION",
    "BILL_DUE_EXTEND_NAME",
    "BILL_DUE_EXTEND_SPEC",
    "REPAIR_CREATE_ACTION",
    "REPAIR_CREATE_NAME",
    "REPAIR_CREATE_SPEC",
    "bill_due_extend",
    "repair_create",
]
