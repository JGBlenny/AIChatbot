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
值域檢查交給 `confirm_card`（那裡自帶同一份真值，見該檔模組 docstring
「`emergency_status` 是已知地雷」一節——舊鏈曾有第二份對照表可互相對帳，
已隨舊鏈於 2026-09-10 退役，現在 `confirm_card` 的真值是唯一來源）。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Final, Optional

from services.agent.confirm_card import (
    CONTRACT_CREATE_ACTION,
    DEFAULT_CATEGORY_NAME,
    ESTATE_CREATE_ACTION,
    MANUAL_BILL_CREATE_ACTION,
    ConfirmCardError,
    category_name_of,
    closed_body,
    emergency_status_of,
    render,
    repair_photos_of,
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
ESTATE_CREATE_NAME: Final[str] = f"jgb2.action.{ESTATE_CREATE_ACTION}"
CONTRACT_CREATE_NAME: Final[str] = f"jgb2.action.{CONTRACT_CREATE_ACTION}"
MANUAL_BILL_CREATE_NAME: Final[str] = f"jgb2.action.{MANUAL_BILL_CREATE_ACTION}"

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


#: S2 三個新動作只給業者（pm）：建物件／合約／手動帳單是業者後台操作，租客與
#: prospect **缺鍵＝永不可見**（⛔ 沿用既有兩支的 tenant M4——那兩支本來就有租客情境）。
PM_ONLY_STAGE: Final[dict] = {"property_manager": "M1"}


def _action_spec(name: str, description: str, *, stage: Optional[dict] = None) -> ToolSpec:
    """各支工具的 spec 只差名字、說明與 stage；既有兩支的 stage 表由 design 元件 2 定
    （pm M1／tenant M4，prospect **缺鍵＝永不可見**）。`mcp_only=True` 是硬性要求（`register()` 會擋）。"""
    spec: ToolSpec = {
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
    if stage is not None:
        spec["stage"] = dict(stage)
    return spec


#: ⚠️ description 是**模型唯一看得到的 payload 契約**——模型要靠它組
#: `confirm.request` 的 `payload` 字串。逐字寫**定義**，⛔ 不寫例子
#: （例子會被模型當成可以照抄的值）。
BILL_DUE_EXTEND_SPEC: ToolSpec = _action_spec(
    BILL_DUE_EXTEND_NAME,
    "把一張帳單的到期日往後調整。"
    "本工具只能在使用者按下確認按鈕之後由系統執行；"
    "要發動它，必須先用 confirm.request 出示確認，payload 的 action 填 bill_due_extend。"
    "payload 欄位定義："
    "days＝往後延的天數，正整數，一律必填；"
    "bill_id＝要調整的帳單編號，選填：手上已經有編號才填；"
    "estate_name＝使用者口述的物件名稱，照原話填入；"
    "period＝使用者口述的期別原話，照原話填入；"
    "缺帳單編號時 estate_name 與 period 兩欄代替它必填，系統會以物件與期別對到帳單，"
    "⛔ 不為了取得帳單編號反問使用者；"
    "date_expire_before＝這張帳單目前的到期日，八位數字的年月日；"
    "date_expire_after＝調整後的到期日，八位數字的年月日；"
    "這兩個日期欄位只在你已經填了 bill_id 時才填，值必須取自系統查到的帳單資料，"
    "⛔ 不要向使用者索取、也不要憑印象填；"
    "取得方式＝出示確認之前先以 jgb2.query.bills（ref 填帳單編號）查這張帳單，"
    "從回傳的繳費期限取值；填了編號卻查不到這張帳單就不能出確認；"
    "缺帳單編號時這兩欄不要填，系統對到帳單之後會依帳單的繳費期限與 days 算；"
    "延後天數從原到期日或今天較晚的一天起算；算出來的新到期日一定在今天之後，"
    "不一致一律拒絕；"
    "這個日期不得早於今天；由起算日加上天數算出來就一定在今天之後，"
    "⛔ 不因原到期日已過而反問要改到哪一天，直接提出確認。",
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

#: S2（§3f 1／2；jgb2-req#19～#21）。⚠️ 三支共用的紀律逐字寫進 description：
#: payload 只能有列出的欄位（多一個鍵、或任何身分／團隊／歸屬欄位 ⇒ 不出卡）；
#: 使用者沒講的選填欄位**不要填**（系統不補值、卡上也不會出現）。
_CLOSED_COMMON: Final[str] = (
    "本工具只能在使用者按下確認按鈕之後由系統執行；"
    "要發動它，必須先用 confirm.request 出示確認。"
    "payload 只能包含下列欄位，⛔ 不得加入其他欄位，"
    "⛔ 不得填入 role_id、user_id 或任何團隊、擁有者、歸屬類欄位（一律由登入身分決定）；"
    "使用者沒有講的選填欄位一律不要填，⛔ 不要自行補值或猜測；"
    "缺必填欄位時 confirm.request 會回報缺少哪些欄位，請據以向使用者追問。"
)

ESTATE_CREATE_SPEC: ToolSpec = _action_spec(
    ESTATE_CREATE_NAME,
    "依使用者給的資料建立一筆新物件。" + _CLOSED_COMMON +
    "payload 的 action 填 estate_create。payload 欄位定義："
    "title＝物件名稱（必填，60 字內）；city＝縣市名稱（必填）；district＝行政區名稱（必填）；"
    "address＝縣市行政區之後的地址（必填，100 字內）；"
    "use_for＝用途，只能是 residential（住宅）、business（商用）、parking_space（車位）其中之一（必填）；"
    "space_type＝空間類型（選填）；building＝建物類型（選填）；"
    "room_count＝房間數，0 到 99 的整數（選填）；size＝面積，大於 0 的數字（選填）；"
    "rent＝租金，整數元（選填）；floor＝樓層（選填）。"
    "必填：title、city、district、address、use_for。",
    stage=PM_ONLY_STAGE,
)

CONTRACT_CREATE_SPEC: ToolSpec = _action_spec(
    CONTRACT_CREATE_NAME,
    "為既有物件建立一份新合約。" + _CLOSED_COMMON +
    "payload 的 action 填 contract_create。payload 欄位定義："
    "estate_name＝使用者口述的物件名稱或物件編號，照原話填入，由系統比對成唯一一個物件並印在確認卡上（必填）；"
    "⛔ 不要自己填物件編號欄位，系統會解析；"
    "date_start＝起租日，八位數字的年月日（必填）；date_end＝到期日，八位數字的年月日，必須晚於起租日（必填）；"
    "rent＝月租金，整數元（必填）；"
    "to_user_email＝承租人 Email；to_user_phone＝承租人電話；兩者至少填一個；"
    "deposit_amount＝押金，整數元（選填）；title＝合約名稱（選填）。"
    "必填：estate_name、date_start、date_end、rent，以及 to_user_email 與 to_user_phone 至少一個。",
    stage=PM_ONLY_STAGE,
)

MANUAL_BILL_CREATE_SPEC: ToolSpec = _action_spec(
    MANUAL_BILL_CREATE_NAME,
    "為既有合約建立一張手動帳單。" + _CLOSED_COMMON +
    "payload 的 action 填 manual_bill_create。payload 欄位定義："
    "contract_ref＝使用者口述的合約名稱或合約編號，照原話填入，由系統比對成唯一一份合約並印在確認卡上；"
    "使用者只講物件時改填 estate_name＝物件名稱，系統以該物件唯一一份有效合約為準"
    "（該物件有多份或沒有有效合約時會回報缺少合約，請向使用者問清楚是哪一份合約）；"
    "⛔ 不要自己填合約編號欄位，系統會解析；"
    "title＝帳單項目名稱（必填，60 字內）；total＝金額，大於 0 的整數元（必填）；"
    "date_expire＝繳費期限，八位數字的年月日，不得早於今天（必填）；"
    "sub_title＝帳單說明（選填，100 字內）。"
    "必填：contract_ref 或 estate_name 其中之一、title、total、date_expire。",
    stage=PM_ONLY_STAGE,
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


async def viewer_bill_row(api: Any, role_id: Any, user_id: Any,
                          bill_id: Any) -> tuple:
    """`("one"|"none"|"error", row)`——**這位成員看得到的這一張帳單**（第 3 步 A0 RC1）。

    以 `get_bills(bill_id=…, viewer_user_id=…)` 單筆探測（jgb2 `/bills` 的 `bill_id` 過濾＋viewer
    圈定），⛔ 依賴列表第一頁（舊寫法讀第一頁 50 筆，排在後面的帳單一律被當成看不到）。
    回傳列仍逐筆比對 id（上游若無視 `bill_id` 參數，也只認同一個編號）。
    `"none"`＝查過、沒有（不存在與看不到**同一個結果**，⛔ 細分）；`"error"`＝沒查成。
    兌現端（`bill_due_extend`）與出卡前預檢（`write_forms` 表單宣告）共用本函式。"""
    if isinstance(bill_id, bool) or not isinstance(bill_id, (str, int)):
        return "none", None
    ref = str(bill_id).strip()
    if not ref or not role_id or not user_id:
        return "none", None
    try:
        rows = jgb2_tools._rows_checked(await api.get_bills(
            role_id=role_id, user_id=user_id, viewer_user_id=user_id, bill_id=ref))
    except jgb2_tools.UpstreamFailure:
        return "error", None
    hits = [r for r in rows if isinstance(r, dict) and str(r.get("id")).strip() == ref]
    return ("one", hits[0]) if len(hits) == 1 else ("none", None)


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

    ⚠️ **兌現端不做期別對帳**（第六批 A｜line-bot #2）：`estate_name`／`period`
    只是**出卡前**的替代輸入，`confirm.request` 在出卡當下就已經把對到的
    `bill_id`／`date_expire_before`／`date_expire_after` 填進 payload，並與卡文字
    的雜湊綁死。缺 `bill_id` 的 payload 在這裡一律 `INVALID_INPUT`
    （`_validated_payload` → `render()` 缺欄位即拋）——⛔ 不得在兌現端再對一次帳：
    那等於讓「使用者按下確認時看到的那一張」與「實際被改的那一張」可以是兩張。
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
    # 第 3 步 A0 RC1（⛔ 掛開關：語義不變的錯誤修正）：可見性改以 `bill_id`＋`viewer_user_id`
    # 單筆探測（`viewer_bill_row`），⛔ 再讀列表第一頁。沒查成也回同一個 `_no_match()`（同改動前：
    # 改動前 `_rows_of` 對沒查成回空列 ⇒ 同樣落到這裡）。
    status, _row = await viewer_bill_row(api, role_id, user_id, bill_id)
    if status != "one":
        # 不存在／不在可見範圍——**兩者共用同一個回答**（同 jgb2 的 404 資訊折疊：
        # 「帳單不存在或無權存取」），⛔ 不細分成可探測的預言機。
        return _no_match()

    # 站內幫手 S5（F5／S5-8，jgb2-req#23 擴及 PATCH）：寫入 body 帶登入身分（只取 identity）。
    resp = await api.agent_patch_bill_due_date(
        bill_id, after_iso, idempotency_key=args.get("confirmation_token"),
        role_id=role_id, user_id=user_id,
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


def _single_leaf_item_id(tree: list, category_id: Any) -> Any:
    """大類底下**恰好只有一個**細項 ⇒ 回該細項 id；否則 `None`。

    2026-10-16 正式機：jgb2 `POST /api/external/v1/repairs` 規定 `item_id` 必填整數
    （`RepairApiController` 驗證規則，master／preview 皆同），只送大類回 400。
    只有一個細項時（例「其他」→「自定義」）沒有選擇空間，補上不會選錯；
    多個細項時 ⛔ 代選（猜錯分類的代價是一張看起來正常、實際分類錯的工單）。
    """
    for node in tree or []:
        if isinstance(node, dict) and node.get("id") == category_id:
            items = [i for i in node.get("items") or [] if isinstance(i, dict) and i.get("id") is not None]
            return items[0].get("id") if len(items) == 1 else None
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
    # 站內幫手 S3（F10）：照片中繼資料只取 payload 內程式寫入、卡上印過張數、已綁進
    # 雜湊的那一份（`render()` 已驗過形狀）；超過上限時 payload 只有張數，⛔ 不附。
    # ⛔ 不送位元組——上傳方式依 jgb2-req#22（S6 定案）。
    broken_photos = repair_photos_of(payload) or None

    role_id, user_id = _identity_pair(identity)
    if not role_id or not user_id:
        return _no_match()

    api = jgb2_tools._get_api()

    # 站內幫手 S5（A3(a)、S5-8）：物件以**這位成員看得到的**範圍解析（`viewer_user_id`）
    # ——看不到的物件與不存在同樣 `NO_MATCH`，⛔ 寫入別人看不到的物件。
    # A-2a（計畫 §4.5 (iv)、§11 P1-1）：卡 payload 有 `estate_id`（只會是出卡前程式依選定寫入、
    # 已綁進雜湊並印在卡上的那一筆；模型自帶的出卡前即丟）⇒ 只依編號確認仍看得到
    # （`_visible_estate_by_id`，看不到 ⇒ `NO_MATCH`），⛔ 依名稱重解；沒有 ⇒ 現行名稱解析。
    if "estate_id" in payload:
        estate = await _visible_estate_by_id(api, role_id, user_id, payload["estate_id"])
    else:
        estate = _resolve_estate(
            jgb2_tools._rows_of(
                await api.get_estate_status(role_id=role_id, keyword=estate_name,
                                            viewer_user_id=user_id)
            ),
            estate_name,
        )
    if estate is None or estate.get("id") is None:
        return _no_match()

    category_tree = jgb2_tools._rows_of(await api.get_repair_categories(
        role_id=role_id, viewer_user_id=user_id))
    resolved = _resolve_category(category_tree, category_name)
    if resolved is None:
        # 分類名稱不在分類樹裡——這是 payload 的內容問題（形狀是對的），
        # ⛔ 不退回「隨便挑一個大類」。
        return _invalid_input()
    category_id, item_id = resolved
    if item_id is None:
        # 只到大類、且該大類只有一個細項 ⇒ 用那個細項（jgb2 要求 item_id 必填）。
        item_id = _single_leaf_item_id(category_tree, category_id)

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
        broken_photos=broken_photos,
        # S2（P4-1；jgb2-req#22／#23）：寫入 body 一律帶登入成員——**只取 identity**
        # （`_identity_pair`），⛔ 不從 payload 讀。缺它時提案替身回 400（S0 延後項）。
        user_id=user_id,
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


# ---------------------------------------------------------------------------
# S2（§3f 1d／3）：帶 viewer 的物件／合約讀取——出卡端解析、兌現端確認共用
#
# ⚠️ 兩端用**同一條讀取路徑**（同一支 API、同一組身分參數），差別只在：
#    出卡端（`tools/confirm.py`）依**名稱或編號**解析成唯一一筆，並把編號寫進 payload；
#    兌現端（本檔）**只依 payload 內的編號**確認該筆仍屬本團隊且這位成員看得到，
#    ⛔ 不依名稱重新解析（那會讓「卡上那一筆」與「被寫的那一筆」可以是兩筆）。
# ⚠️ 身分：`role_id`＋`viewer_user_id=user_id`（DSP-074）；⛔ 不帶 `user_id` 參數
#    （`/estates` 的 `user_id` 是另一個語義的過濾，`/contracts` 的是承租人）。
# ---------------------------------------------------------------------------
def _real_rows(rows: list) -> list:
    """濾掉 `get_estate_status` 的查無哨兵（`found=False`），⛔ 不靠巧合。"""
    return [r for r in rows if isinstance(r, dict) and r.get("found") is not False]


async def _viewer_estate_rows(api, role_id: str, user_id: str, ref: str) -> list:
    """物件名稱或編號 → 這位成員看得到的候選列（與 `repair_create` 同一支 API，另帶 viewer）。

    站內幫手 S5（S5-1）：上游「沒查成」⇒ `jgb2.UpstreamFailure`（⛔ 折成空列——空列會被
    出卡端講成「查不到」）；查無（含 403／404）⇒ 空列。
    """
    return _real_rows(jgb2_tools._rows_checked(
        await api.get_estate_status(role_id=role_id, keyword=ref, viewer_user_id=user_id)
    ))


async def _visible_estate_by_id(api, role_id: str, user_id: str, estate_id: Any) -> Optional[dict]:
    """兌現端：payload 內的物件編號是否仍屬本團隊且這位成員看得到；否 ⇒ `None`。"""
    wanted = str(estate_id).strip()
    try:
        rows = await _viewer_estate_rows(api, role_id, user_id, wanted)
    except jgb2_tools.UpstreamFailure:
        return None
    for row in rows:
        if str(row.get("id")).strip() == wanted:
            return row
    return None


async def _viewer_contract_rows(api, role_id: str, user_id: str, *,
                                contract_ids: Optional[str] = None,
                                keyword: Optional[str] = None) -> tuple:
    """`(rows, has_more)`：這位成員看得到的合約列（`/contracts/status-overview`＋viewer）。

    `has_more`＝上游還有下一頁——呼叫端據此判「無法確定唯一」（⛔ 只看第一頁就下結論）。
    """
    kwargs: dict = {"role_id": role_id, "viewer_user_id": user_id}
    if contract_ids is not None:
        kwargs["contract_ids"] = contract_ids
    if keyword is not None:
        kwargs["keyword"] = keyword
    resp = await api.get_contracts(**kwargs)
    # S5（S5-1）：沒查成 ⇒ `jgb2.UpstreamFailure`（同 `_viewer_estate_rows`）。
    rows = [r for r in jgb2_tools._rows_checked(resp) if isinstance(r, dict)]
    pagination = (resp or {}).get("pagination") if isinstance(resp, dict) else None
    has_more = bool(isinstance(pagination, dict) and pagination.get("has_more"))
    return rows, has_more


async def _visible_contract_by_id(api, role_id: str, user_id: str, contract_id: Any) -> Optional[dict]:
    """兌現端：payload 內的合約編號是否仍屬本團隊且這位成員看得到；否 ⇒ `None`。"""
    wanted = str(contract_id).strip()
    if not wanted.isdigit():
        return None
    try:
        rows, _ = await _viewer_contract_rows(api, role_id, user_id, contract_ids=wanted)
    except jgb2_tools.UpstreamFailure:
        return None
    for row in rows:
        if str(row.get("id")).strip() == wanted:
            return row
    return None


def _created_id(resp: Any) -> str:
    """下游建立成功的回應 → 形狀安全的新編號；不成功或沒給編號 ⇒ `""`。"""
    if not (resp or {}).get("success"):
        return ""
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    return _scalar(data.get("id"))


# ---------------------------------------------------------------------------
# jgb2.action.estate_create（jgb2-req#19）
# ---------------------------------------------------------------------------
async def estate_create(identity: Identity, args: dict) -> ToolResult:
    """依 payload 建立物件。順序：形狀（封閉欄位表）→ 寫。新物件沒有既有資源可讀。

    body＝`closed_body`（只含使用者給了的欄位；⛔ 補值）；身分只取 identity。
    """
    payload = _validated_payload(ESTATE_CREATE_ACTION, args)
    if payload is None:
        return _invalid_input()
    role_id, user_id = _identity_pair(identity)
    if not role_id or not user_id:
        return _no_match()
    api = jgb2_tools._get_api()
    resp = await api.assistant_create_estate(
        role_id, user_id, closed_body(ESTATE_CREATE_ACTION, payload),
        idempotency_key=args.get("confirmation_token"),
    )
    estate_id = _created_id(resp)
    if not estate_id:
        logger.warning("[agent] estate_create 下游寫入未成功或缺編號")
        return _no_match()
    return _receipt({"estate_id": estate_id}, "物件已建立。")


# ---------------------------------------------------------------------------
# jgb2.action.contract_create（jgb2-req#20）
# ---------------------------------------------------------------------------
async def contract_create(identity: Identity, args: dict) -> ToolResult:
    """依 payload 建立合約。順序：形狀 → **寫前先讀**（payload 內的 `estate_id`）→ 寫。

    ⚠️ 物件編號是出卡端解析後寫進 payload、納入雜湊的那一個（§3f 1d）——
    這裡只確認它仍屬本團隊且這位成員看得到，否則 `NO_MATCH`；⛔ 不依名稱重新解析。
    """
    payload = _validated_payload(CONTRACT_CREATE_ACTION, args)
    if payload is None:
        return _invalid_input()
    role_id, user_id = _identity_pair(identity)
    if not role_id or not user_id:
        return _no_match()
    api = jgb2_tools._get_api()
    body = closed_body(CONTRACT_CREATE_ACTION, payload)
    if await _visible_estate_by_id(api, role_id, user_id, body["estate_id"]) is None:
        return _no_match()
    resp = await api.assistant_create_contract(
        role_id, user_id, body, idempotency_key=args.get("confirmation_token"),
    )
    contract_id = _created_id(resp)
    if not contract_id:
        logger.warning("[agent] contract_create 下游寫入未成功或缺編號")
        return _no_match()
    return _receipt({"contract_id": contract_id, "estate_id": _scalar(body["estate_id"])},
                    "合約已建立。")


# ---------------------------------------------------------------------------
# jgb2.action.manual_bill_create（jgb2-req#21）
# ---------------------------------------------------------------------------
async def manual_bill_create(identity: Identity, args: dict) -> ToolResult:
    """依 payload 建立手動帳單。順序：形狀 → **寫前先讀**（payload 內的 `contract_id`）→ 寫。

    ⚠️ 同 `contract_create`：只用 payload 內的合約編號，⛔ 不依名稱或物件重新解析。
    日期「不得早於今天」由 Runtime 兌現閘（`fields_before_today`）在呼叫本工具前擋。
    """
    payload = _validated_payload(MANUAL_BILL_CREATE_ACTION, args)
    if payload is None:
        return _invalid_input()
    role_id, user_id = _identity_pair(identity)
    if not role_id or not user_id:
        return _no_match()
    api = jgb2_tools._get_api()
    body = closed_body(MANUAL_BILL_CREATE_ACTION, payload)
    if await _visible_contract_by_id(api, role_id, user_id, body["contract_id"]) is None:
        return _no_match()
    resp = await api.assistant_create_bill(
        role_id, user_id, body, idempotency_key=args.get("confirmation_token"),
    )
    bill_id = _created_id(resp)
    if not bill_id:
        logger.warning("[agent] manual_bill_create 下游寫入未成功或缺編號")
        return _no_match()
    return _receipt({"bill_id": bill_id, "contract_id": _scalar(body["contract_id"])},
                    "手動帳單已建立。")


ACTION_SPECS: Final[tuple] = (
    (BILL_DUE_EXTEND_SPEC, bill_due_extend),
    (REPAIR_CREATE_SPEC, repair_create),
    (ESTATE_CREATE_SPEC, estate_create),
    (CONTRACT_CREATE_SPEC, contract_create),
    (MANUAL_BILL_CREATE_SPEC, manual_bill_create),
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
    "viewer_bill_row",
    "repair_create",
    "ESTATE_CREATE_NAME",
    "ESTATE_CREATE_SPEC",
    "CONTRACT_CREATE_NAME",
    "CONTRACT_CREATE_SPEC",
    "MANUAL_BILL_CREATE_NAME",
    "MANUAL_BILL_CREATE_SPEC",
    "PM_ONLY_STAGE",
    "estate_create",
    "contract_create",
    "manual_bill_create",
]
