"""站內幫手 S1：三支唯讀統計／清單工具（DSP-074）。

- `jgb2.stats.unpaid_bills`：未收帳單統計（本月／逾期，總額＋逐筆明細）→ `get_unpaid_bill_summary`（jgb2-req#16）
- `jgb2.stats.in_progress_repairs`：執行中修繕清單 → `get_in_progress_repairs`（jgb2-req#17）
- `jgb2.stats.expiring_contracts`：N 個月內到期合約（預設 3）→ `get_expiring_contracts`（jgb2-req#18）

⚠️ 三個端點都是 `contract: proposed`（JGB 尚未實作，替身照期望契約回應），⛔ 不可讀成 JGB 已存在的行為。

身分（DSP-074，「這位成員在 JGB 畫面上看得到的」）：
一律要 `role_id`＋`user_id`（viewer）雙證，缺一 ⇒ `NO_MATCH`。⛔ 不沿用 `jgb2._identity_gate_ok`
的 pm 單證（那條路缺 `user_id` 會退回整個 role；這三支的語義是「這位成員看得到的」）。
`input_schema` ⛔ 含身分鍵（不變量 18／27）；呼叫端夾帶的身分鍵由 `ToolRegistry.call()` 剝除。

`success:false`（越權、逾時、回應形狀不對…）與真空資料（`success:true`、`count:0`）分開——
前者回**固定句**（`ERROR_TEXT`，⛔ 無插值、⛔ 不印 0、⛔ 不印空清單），後者才是「0 筆」的事實。

分頁（S1 修正②③，A5 一次全列會讓模型生成逾時）：明細每頁 `_PAGE_SIZE`（20）筆，選填 `page`（從 1 起）；
回「共 N 筆」＋該頁明細＋「還有 M 筆，要看下一頁嗎？」，⛔ 不靜默截斷。頁碼超過頁數 ⇒ 明確訊息（非錯誤）。
每頁只打一次上游（`page`／`per_page` 直接對應），總額與筆數取上游的全量值。
provenance 單位：一句「共 N 筆（＋總額）…」＋每筆明細一行（明細內 ⛔ 含句末標點，否則一行會被切成多個單位）。
⚠️ 有 provenance 的工具，模型只看到 provenance 單位（`runtime.py` 資料段不送 `text_for_model`），
所以「須逐筆列出」的指示同時寫在 `text_for_model` 與各工具的 `description`。

本檔不 import `services.agent.mcp_facade`；API 存取走 `jgb2._get_api()`（測試與 `tools/jgb2.py` 共用同一個注入點）。
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from services.agent.tools import jgb2 as _jgb2
from services.agent.tools.registry import ToolSpec
from services.jgb.bills import (
    _bill_status as _bill_status_of,
    _format_date_int as _bill_format_date,
    _get_status_label as _bill_status_label,
    _money,
)
from services.jgb.contracts import _format_date_int as _contract_format_date
from services.jgb.repairs import _status_zh as _repair_status_zh, _urgency_zh

#: 每頁明細筆數（也是送上游的 `per_page`）。A5：77 筆一次全列會讓模型生成逾時 ⇒ 分頁。
_PAGE_SIZE = 20

#: 上游失敗（`success:false`、形狀不對）一律這一句。⛔ 無插值：不把上游訊息、數字帶進去。
ERROR_TEXT = (
    "目前無法取得這份資料，請使用者稍後再試或洽客服。"
    "這不是「沒有資料」：⛔ 不要回報為零筆、零元或空清單。"
)

#: 接真 JGB（`USE_MOCK_JGB_API=false`）時三支統計端點 JGB 尚未開放（jgb2-req#16～#18）⇒
#: 不發請求，由 runtime 以這一句程式固定句結束回合（否則打到不存在的
#: 端點後，模型會改成轉人或反問「想處理哪一件事？」）。⛔ 無插值。
NOT_SUPPORTED_TEXT = "這項統計目前還不支援：JGB 系統尚未開放這個查詢，開放後就能直接查。"

#: 缺身分（缺 role_id 或 user_id）⇒ 與其他 jgb2 查詢工具同形的 NO_MATCH。
_UNPAID_SCOPES = {"this_month": "本月", "overdue": "逾期"}

_STAGE = {"property_manager": "M0"}      # 與 `jgb2.query.*` 同為 M0；tenant 缺鍵＝永不可見

#: 每則 `text_for_model` 的開頭指示（模型看不到它，見檔頭；`description` 另寫一份）。
_LIST_RULE = ("回答須列出{what}與本頁每一筆明細（逐筆）；"
              "若還有下一頁，須明說還有幾筆並問使用者要不要看下一頁。")

#: 句末標點會讓 `provenance_units` 把一行切成多個單位 ⇒ 明細內的自由文字一律換掉。
_SENTENCE_END_TRANS = str.maketrans({"。": "，", "！": "，", "？": "，", "!": ",", "?": ",",
                                     "\n": " ", "\r": " "})


# ── 共用 ────────────────────────────────────────────────────────────────────
def _viewer(identity: Any) -> Optional[tuple[str, str]]:
    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not (role_id and user_id):
        return None
    return str(role_id), str(user_id)


def _page_arg(args: dict[str, Any]) -> Optional[int]:
    """選填 `page`（從 1 起的整數）；缺省 1；不合法 ⇒ `None`（呼叫端回 INVALID_INPUT）。"""
    page = args.get("page", 1)
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        return None
    return page


def _one_line(value: Any) -> str:
    return str(value).translate(_SENTENCE_END_TRANS)


def _error_result() -> dict[str, Any]:
    """上游失敗固定句。`ok=True` 是為了讓模型看得到這一句（`ok=False` 只會讓模型看到錯誤碼）；
    沒有 provenance ⇒ 沒有可引用的『資料』，`facts` 也不是空字串（⛔ 不被當成『查無資料』）。"""
    return {
        "ok": True,
        "data": {"facts": ERROR_TEXT, "candidates": None, "skip_refine": True,
                 "upstream_error": True},
        "provenance": [],
        "text_for_model": ERROR_TEXT,
    }


def _not_supported_result() -> dict[str, Any]:
    """接真 JGB 時的「尚未開放」結果：`data.not_supported=True` 是 runtime 固定句出口的標記。"""
    return {
        "ok": True,
        "data": {"facts": NOT_SUPPORTED_TEXT, "candidates": None, "skip_refine": True,
                 "not_supported": True},
        "provenance": [],
        "text_for_model": NOT_SUPPORTED_TEXT,
    }


def _mock_only(handler: Callable[[Any, dict], Awaitable[dict[str, Any]]]):
    """統計端點只在替身可用；接真 JGB ⇒ 不發請求、回「尚未開放」。"""
    async def guarded(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
        # 真 `JGBSystemAPI` 一定有 `use_mock`；沒有這個屬性的是測試替身 ⇒ 沿用原行為。
        if getattr(_jgb2._get_api(), "use_mock", True) is False:
            return _not_supported_result()
        return await handler(identity, args)
    guarded.__name__ = handler.__name__
    return guarded


def _ok_result(tag: str, rule: str, facts: str, extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {"facts": facts, "candidates": None, "skip_refine": True, **extra},
        "provenance": [{"source": f"jgb2:stats#{tag}", "text": facts, "citable": True}],
        "text_for_model": f"{rule}\n{facts}",
    }


def _good_payload(resp: Any) -> Optional[dict[str, Any]]:
    """`success:true` 且 `data` 是帶 `items`（list）與 `count`（int）的物件才算有效；否則 `None`。"""
    if not isinstance(resp, dict) or resp.get("success") is not True:
        return None
    data = resp.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None
    count = data.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return None
    return data


def _summary(prefix: str, count: int, page: int, shown: int, extra: str = "") -> str:
    """「共 N 筆（＋總額）」＋分頁句——**單一句**（一個 provenance 單位）。"""
    head = f"{prefix}共 {count} 筆{extra}"
    if count <= _PAGE_SIZE and page == 1:
        return f"{head}，以下全部列出。" if count else f"{head}。"
    first = (page - 1) * _PAGE_SIZE + 1
    last = first + shown - 1
    remaining = count - last
    where = f"以下是第 {page} 頁（第 {first} 到 {last} 筆）"
    if remaining > 0:
        return f"{head}；{where}，還有 {remaining} 筆，要看下一頁嗎？"
    return f"{head}；{where}，已是最後一頁。"


async def _paged(
    tag: str, rule: str, page: int, fetch: Callable[[int], Awaitable[Any]],
    prefix: Callable[[dict[str, Any]], Optional[str]],
    extra: Callable[[dict[str, Any]], Optional[str]],
    row_line: Callable[[dict[str, Any]], str],
    more_data: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """打上游一次（第 `page` 頁）→ 「共 N 筆」＋該頁明細。任何形狀不對 ⇒ 上游失敗固定句。"""
    data = _good_payload(await fetch(page))
    if data is None:
        return _error_result()
    pre, ext = prefix(data), extra(data)
    if pre is None or ext is None:
        return _error_result()
    count = data["count"]
    items = [i for i in data["items"] if isinstance(i, dict)]
    total_pages = -(-count // _PAGE_SIZE)
    if count > 0 and page > total_pages:
        facts = f"{pre}共 {count} 筆，只有 {total_pages} 頁，沒有第 {page} 頁。"
        return _ok_result(tag, rule, facts, {"count": count, "page": page,
                                              "total_pages": total_pages, "listed": 0, **more_data(data)})
    if count > 0 and not items:                      # 該有明細卻沒有 ⇒ 不是「沒有資料」
        return _error_result()
    lines = [_summary(pre, count, page, len(items), ext)]
    lines.extend(row_line(i) for i in items)
    return _ok_result(tag, rule, "\n".join(lines),
                      {"count": count, "page": page, "total_pages": total_pages,
                       "listed": len(items), **more_data(data)})


def _ymd_compact(value: Any) -> str:
    """`apply_at`（`YYYYMMDDhhmmss` 字串）→ `YYYY/MM/DD`；形狀不符原樣回。"""
    s = str(value or "")
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[:4]}/{s[4:6]}/{s[6:8]}"
    return s or "未記錄"


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ── 未收帳單統計 ─────────────────────────────────────────────────────────────
async def unpaid_bills(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    scope = args.get("scope")
    page = _page_arg(args)
    if scope not in _UNPAID_SCOPES or page is None:
        return _jgb2._invalid_input()
    who = _viewer(identity)
    if who is None:
        return _jgb2._no_match()
    role_id, user_id = who
    api = _jgb2._get_api()

    async def fetch(p: int) -> Any:
        return await api.get_unpaid_bill_summary(
            role_id, user_id, scope, page=p, per_page=_PAGE_SIZE)

    def row_line(b: dict[str, Any]) -> str:
        sub = f"（{_one_line(b['sub_title'])}）" if b.get("sub_title") else ""
        amount = _money(b["total"]) if _is_num(b.get("total")) else "未記錄"
        return (f"帳單編號 {b.get('id', '?')}、{_one_line(b.get('title') or '')}{sub}、"
                f"到期日 {_bill_format_date(b.get('date_expire'))}、"
                f"狀態 {_bill_status_label(_bill_status_of(b))}、金額 {amount}")

    return await _paged(
        "unpaid_bills", _LIST_RULE.format(what="總額"), page, fetch,
        prefix=lambda d: (f"{_UNPAID_SCOPES[scope]}未收帳單（截至 {d.get('as_of') or '今日'}，"
                          "未收＝待繳費或待對帳，只含這位成員在 JGB 畫面上看得到的帳單）"),
        extra=lambda d: f"，總額 {_money(d['total_amount'])}" if _is_num(d.get("total_amount")) else None,
        row_line=row_line,
        more_data=lambda d: {"total_amount": d.get("total_amount")},
    )


# ── 執行中修繕清單 ───────────────────────────────────────────────────────────
async def in_progress_repairs(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    page = _page_arg(args)
    if page is None:
        return _jgb2._invalid_input()
    who = _viewer(identity)
    if who is None:
        return _jgb2._no_match()
    role_id, user_id = who
    api = _jgb2._get_api()

    async def fetch(p: int) -> Any:
        return await api.get_in_progress_repairs(role_id, user_id, page=p, per_page=_PAGE_SIZE)

    def row_line(r: dict[str, Any]) -> str:
        category = _one_line(r.get("category_name") or "（未分類）")
        if r.get("item_name"):
            category += f"／{_one_line(r['item_name'])}"
        reason = f"、報修原因 {_one_line(r['broken_reason'])}" if r.get("broken_reason") else ""
        return (f"單號 {r.get('id', '?')}、物件 {_one_line(r.get('estate_title') or '（未記錄物件名稱）')}、"
                f"分類 {category}、狀態 {_repair_status_zh(r.get('status'))}、"
                f"{_urgency_zh(r.get('emergency_status'))}、申請日 {_ymd_compact(r.get('apply_at'))}{reason}")

    return await _paged(
        "in_progress_repairs", _LIST_RULE.format(what="共幾筆"), page, fetch,
        prefix=lambda d: "執行中（未結案：申請中、安排修繕、完成修繕）修繕單（只含這位成員在 JGB 畫面上看得到的修繕單，結單與封存不在內）",
        extra=lambda d: "",
        row_line=row_line,
        more_data=lambda d: {},
    )


# ── N 個月內到期合約 ─────────────────────────────────────────────────────────
async def expiring_contracts(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    months = args.get("months", 3)
    page = _page_arg(args)
    if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 24 or page is None:
        return _jgb2._invalid_input()
    who = _viewer(identity)
    if who is None:
        return _jgb2._no_match()
    role_id, user_id = who
    api = _jgb2._get_api()

    async def fetch(p: int) -> Any:
        return await api.get_expiring_contracts(
            role_id, user_id, months=months, page=p, per_page=_PAGE_SIZE)

    def row_line(c: dict[str, Any]) -> str:
        rent_text = f"、月租 {_money(c['rent'])}" if _is_num(c.get("rent")) else ""
        addr = _one_line("".join(str(c.get(k) or "") for k in ("city", "district", "address")))
        left = c.get("days_left")
        left_text = f"（剩 {left} 天）" if isinstance(left, int) and not isinstance(left, bool) else ""
        return (f"合約編號 {c.get('id', '?')}、{_one_line(c.get('title') or '')}"
                f"{('、' + addr) if addr else ''}、到期日 {_contract_format_date(c.get('date_end'))}"
                f"{left_text}{rent_text}")

    return await _paged(
        "expiring_contracts", _LIST_RULE.format(what="共幾筆"), page, fetch,
        prefix=lambda d: (f"{months} 個月內到期的合約（{d.get('as_of') or '今日'} 至 {d.get('window_end') or '?'}，"
                          "只含這位成員在 JGB 畫面上看得到的合約）"),
        extra=lambda d: "",
        row_line=row_line,
        more_data=lambda d: {"months": months},
    )


# ── ToolSpec ────────────────────────────────────────────────────────────────
UNPAID_BILLS_SPEC: ToolSpec = {
    "name": "jgb2.stats.unpaid_bills",
    "description": (
        "未收帳單統計：回這位成員看得到的未收（待繳費或待對帳）帳單的筆數、總額與逐筆明細（每頁 20 筆）。"
        "scope=this_month 是到期日落在本月，scope=overdue 是到期日已過。"
        "回答須列出總額與本頁每一筆明細（逐筆），筆數、總額與明細逐字照工具結果，⛔ 自行加總或省略明細；"
        "結果說還有下一頁時，明說還有幾筆並問使用者要不要看下一頁，要看再以 page 取下一頁。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {"scope": {"type": "string", "enum": list(_UNPAID_SCOPES)},
                       "page": {"type": "integer", "minimum": 1}},
        "required": ["scope"],
        "additionalProperties": False,
    },
    "scope": "read",
    "stage": dict(_STAGE),
}

IN_PROGRESS_REPAIRS_SPEC: ToolSpec = {
    "name": "jgb2.stats.in_progress_repairs",
    "description": (
        "執行中修繕清單：回這位成員看得到的未結案（申請中、安排修繕、完成修繕）修繕單，"
        "先回共幾筆與第一頁（每頁 20 筆），不受候選上限，結單與封存不在內。"
        "回答須列出共幾筆與本頁每一筆明細（逐筆），逐字照工具結果；"
        "結果說還有下一頁時，明說還有幾筆並問使用者要不要看下一頁，要看再以 page 取下一頁。"
    ),
    "input_schema": {"type": "object", "properties": {"page": {"type": "integer", "minimum": 1}},
                     "additionalProperties": False},
    "scope": "read",
    "stage": dict(_STAGE),
}

EXPIRING_CONTRACTS_SPEC: ToolSpec = {
    "name": "jgb2.stats.expiring_contracts",
    "description": (
        "N 個月內到期合約：回這位成員看得到、到期日落在今天起 N 個月內的合約（每頁 20 筆）；"
        "months 預設 3（1 到 24）。回答須列出共幾筆與本頁每一筆明細（逐筆），逐字照工具結果；"
        "結果說還有下一頁時，明說還有幾筆並問使用者要不要看下一頁，要看再以 page 取下一頁。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {"months": {"type": "integer", "minimum": 1, "maximum": 24},
                       "page": {"type": "integer", "minimum": 1}},
        "additionalProperties": False,
    },
    "scope": "read",
    "stage": dict(_STAGE),
}

#: `mcp_facade.build_registry` 逐一註冊（形狀同 `action.ACTION_SPECS`）。
STATS_SPECS: list[tuple[ToolSpec, Callable[[Any, dict], Awaitable[dict[str, Any]]]]] = [
    (UNPAID_BILLS_SPEC, _mock_only(unpaid_bills)),
    (IN_PROGRESS_REPAIRS_SPEC, _mock_only(in_progress_repairs)),
    (EXPIRING_CONTRACTS_SPEC, _mock_only(expiring_contracts)),
]
