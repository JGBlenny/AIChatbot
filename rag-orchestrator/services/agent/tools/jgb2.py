"""`jgb2.query.<domain>` 五域工具（spec agentic-mcp-orchestration・任務 1.5）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 3
（`jgb2.query.<domain>` 列、域映射表、`FACE_BUILDER_REGISTRIES` 表）。

每個 `query_<domain>(identity, args) -> dict` 是**未包裝**的工具函式——回傳形狀見
`_ok_single`／`_ok_candidates`／`_no_match`／`_invalid_input`，由後續任務（1.4／1.7）
包成 `ToolResult`。⛔ 本檔不 import `services.agent.tools.registry`（1.3 平行中）。

身分（DSP-011，本系統只管額度、權限交 jgb2 API 裁）：
- **bills／contracts（1.10 P1 修正，⛔ 勿改回只看 role_id）**：受眾決定要幾張證。
  `property_manager` ⇒ `role_id` 單證即可（pm 查的是自己名下整個 role 的帳單／
  合約，1.5 收案時刻意不帶 `user_id`，否則 jgb2 的 `to_user_id` 圈定會把 pm 自己
  的查詢過濾成空）；**其餘受眾（tenant／prospect）⇒ 一律
  `JGBSystemAPI._validate_identity(role_id, user_id)` 雙證，缺一即 `NO_MATCH`**。
  理由：`viewer_user_id` 空值不會被轉發（`jgb_system_api.py` 只在非空時放進
  params），而 jgb2 的 `get_contracts` 只要 `role_id` 就受理、`get_bills` 只要
  `role_id`＋`bill_ref` 就受理——租客缺 `user_id` 時等於拿整個 role 的個資。
  受眾取自 `identity.resolved_audience()`（`services/agent/identity.py`）；
  取不到一律 **fail-closed 當 tenant**（要雙證），見 `_audience_of`。
  雙證通過後仍帶 `viewer_user_id=identity.user_id` 交 jgb2 圈定（Layer 2）。
- accounts／meters／estates：本工具層以 `JGBSystemAPI._validate_identity(role_id,
  user_id)` 作為**雙證閘門**（沿用既有函式，純粹檢查兩者皆非空——不代表這兩個
  API 呼叫本身消費 `user_id`，多數不支援 viewer 圈定，見域映射表「不支援」欄）；
  缺一律 `NO_MATCH`。

⚠️ `identity.role_id`／`identity.user_id`：任務 1.3 正在替 `Identity`
（`services/agent/identity.py`）加這兩個欄位，本檔一律用
`getattr(identity, "role_id", None)` 取，⛔ 不改 identity.py、不假設欄位必存在。

已知缺口（留待業主裁決，見任務回報）：`ACCOUNT_FACE_BUILDERS` 的兩個鍵
（`登入排障`／`團隊成員權限`）在既有系統中分別掛在**不同**主查資料源
（`登入排障` 讀 `jgb_contracts` 合約列，`團隊成員權限` 讀 `jgb_team_members`
成員列——見 `services/jgb_response_formatter.py:198` 起的既有分派），但 design
域映射表只給 accounts 域指定 `get_team_members`／`get_member_permissions`
兩個 API。本工具的 `query_accounts` 因此**只**走成員/權限流程；`face="登入排障"`
雖仍是合法 enum 值（不觸發 `INVALID_INPUT`），但套用成員流程會取不到
`登入排障` builder 需要的合約欄位，非正確 facts——這是設計缺口而非本任務
能自行決定的取捨，⛔ 未經業主裁決不得默默「修好」。
"""
from __future__ import annotations

import os
from typing import Any, Awaitable, Callable, Optional

from services.jgb_system_api import JGBSystemAPI
from services.jgb.bills import (
    BILL_FACE_BUILDERS,
    _bill_amount_due as _bill_amount,
    _bill_status as _bill_status_of,
    _format_date_int as _bill_format_date,
    _get_status_label as _bill_status_label,
    _money as _bill_money,
)
from services.jgb.contracts import (
    FACE_BUILDERS as CONTRACT_FACE_BUILDERS,
    _format_date_int as _contract_format_date,
)
from services.jgb.accounts import ACCOUNT_FACE_BUILDERS
from services.jgb.iot import METER_FACE_BUILDERS
from services.jgb.estates import ESTATE_FACE_BUILDERS, estate_status_zh
from services.jgb.repairs import (
    REPAIR_FACE_BUILDERS,
    _status_zh as _repair_status_zh,
    build_repair_category_tree_facts,
)

_DEFAULT_CANDIDATE_CAP = 5


def _candidate_cap() -> int:
    """`CANDIDATE_CAP`（env，預設 5）；逐次讀取，不在 import 時凍結。"""
    raw = os.getenv("JGB2_CANDIDATE_CAP", "")
    try:
        return int(raw) if raw else _DEFAULT_CANDIDATE_CAP
    except ValueError:
        return _DEFAULT_CANDIDATE_CAP


# ── JGBSystemAPI 存取（測試以 monkeypatch 替換 `_api_singleton` 注入假身） ──
_api_singleton: Optional[JGBSystemAPI] = None


def _get_api() -> JGBSystemAPI:
    global _api_singleton
    if _api_singleton is None:
        _api_singleton = JGBSystemAPI()
    return _api_singleton


# ── 回傳外殼 ────────────────────────────────────────────────────────────────
def _no_match() -> dict[str, Any]:
    return {"ok": False, "error": "NO_MATCH"}


def _invalid_input() -> dict[str, Any]:
    return {"ok": False, "error": "INVALID_INPUT"}


def _ok_single(domain: str, tag: str, facts: str, cap: int) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {"facts": facts, "candidates": None,
                 "candidate_cap": cap, "skip_refine": True},
        "provenance": [{"source": f"jgb2:{domain}#{tag}", "text": facts, "citable": True}],
        "text_for_model": facts,
    }


# ── 候選清單文字（收案 1：候選結果要有文字）───────────────────────────────
#
# 依域投影一行摘要；狀態詞一律引用各域既有標籤表（`_bill_status_label`／
# `estate_status_zh`／`_repair_status_zh`），⛔ 不在本檔手抄一份新的狀態對照。

def _project_bill_row(row: dict) -> str:
    parts = [f"編號 {row.get('id', '?')}", str(row.get("title") or "")]
    parts.append(f"狀態 {_bill_status_label(_bill_status_of(row))}")
    if row.get("date_expire"):
        parts.append(f"到期日 {_bill_format_date(row.get('date_expire'))}")
    amount = _bill_amount(row)
    if amount is not None:
        parts.append(f"金額 {_bill_money(amount)}")
    return "、".join(parts)


def _project_contract_row(row: dict) -> str:
    parts = [f"編號 {row.get('id', '?')}", str(row.get("title") or "")]
    if row.get("date_end"):
        parts.append(f"到期日 {_contract_format_date(row.get('date_end'))}")
    return "、".join(parts)


def _project_estate_row(row: dict) -> str:
    parts = [f"編號 {row.get('id', '?')}", str(row.get("title") or "")]
    parts.append(f"狀態 {estate_status_zh(row.get('status'))}")
    return "、".join(parts)


def _project_meter_row(row: dict) -> str:
    parts = [f"編號 {row.get('id', '?')}", str(row.get("name") or "")]
    estate = row.get("estate_name")
    if estate:
        parts.append(f"所在物件 {estate}")
    return "、".join(parts)


def _project_repair_row(row: dict) -> str:
    parts = [f"單號 {row.get('id', '?')}", str(row.get("category_name") or "")]
    estate = row.get("estate_title")
    if estate:
        parts.append(f"物件 {estate}")
    parts.append(f"狀態 {_repair_status_zh(row.get('status'))}")
    return "、".join(parts)


def _project_generic_row(row: dict) -> str:
    """未列名域（如 accounts）的保底投影——不因缺表而印不出候選清單。"""
    label = row.get("title") or row.get("name") or row.get("id") or "?"
    return f"編號 {row.get('id', '?')}、{label}"


_ROW_PROJECTORS: dict[str, Callable[[dict], str]] = {
    "bills": _project_bill_row,
    "contracts": _project_contract_row,
    "estates": _project_estate_row,
    "meters": _project_meter_row,
    "repairs": _project_repair_row,
}


def _candidates_text(domain: str, query: Optional[str], rows: list) -> str:
    q = query if query else "無"
    lines = [f"查詢條件：{q}；符合 {len(rows)} 筆"
             "（以下為可見清單，⛔ 不是使用者指定編號的資料）"]
    projector = _ROW_PROJECTORS.get(domain, _project_generic_row)
    lines.extend(projector(row) for row in rows)
    lines.append("要取得某一筆的完整事實，請以 ref 指定該編號再查一次。")
    return "\n".join(lines)


def _ok_candidates(domain: str, tag: str, rows: list, cap: int,
                    skip_refine: bool, query: Optional[str] = None) -> dict[str, Any]:
    text = _candidates_text(domain, query, rows)
    return {
        "ok": True,
        "data": {"facts": "", "candidates": rows,
                 "candidate_cap": cap, "skip_refine": skip_refine},
        "provenance": [{"source": f"jgb2:{domain}#{tag}", "text": text, "citable": True}],
        "text_for_model": text,
    }


def _rows_of(resp: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """`TransportResponse`-like dict → 資料列 list（`success` 為假一律空列）。"""
    if not (resp or {}).get("success"):
        return []
    data = resp.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


# ── 身分閘（1.10 P1）────────────────────────────────────────────────────────
def _audience_of(identity: Any) -> str:
    """呼叫者受眾；**fail-closed**——取不到／算不出一律回 `"tenant"`（最嚴：要雙證）。

    ⛔ 不 import `services.agent.identity`：本檔對 identity 一律鴨子型別存取
    （見模組 docstring 的 1.3 註記），假身分（`SimpleNamespace`）也要能用。
    """
    resolver = getattr(identity, "resolved_audience", None)
    if callable(resolver):
        try:
            audience = resolver()
        except Exception:  # noqa: BLE001 — 算不出受眾＝未知＝按最嚴的 tenant 走
            return "tenant"
        if isinstance(audience, str) and audience:
            return audience
    return "tenant"


def _identity_gate_ok(identity: Any, role_id: Any, user_id: Any) -> bool:
    """bills／contracts 的身分閘：pm 單證、其餘雙證。

    ⚠️ **勿改回 `if not role_id`**（1.9 security review P1）：那讓 tenant 缺
    `user_id` 時仍發查詢，而 `viewer_user_id` 空值不轉發 ⇒ jgb2 只認 `role_id`
    ⇒ 回整個 role 的帳單／合約。契約見 `docs/api/mcp-facade.md` §4.2。
    """
    if _audience_of(identity) == "property_manager":
        return bool(role_id)
    return JGBSystemAPI._validate_identity(role_id, user_id)


Fetch = Callable[[Optional[str]], Awaitable[list[dict[str, Any]]]]


async def _resolve(
    ref: Optional[str], keyword: Optional[str], cap: int, *,
    fetch_ref: Fetch, fetch_keyword: Optional[Fetch] = None,
    fetch_default: Optional[Fetch] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """`ref`／`keyword`／兩者皆無 三態決定（契約：有 ref 查單筆；只有 keyword
    查候選 ≤cap 全列 `skip_refine`、超過只回前 cap 筆；兩者皆無視域走預設列表
    或 `NO_MATCH`）。回傳 `(status, rows)`；`status` ∈
    `{"empty", "single", "candidates_all", "candidates_more"}`。
    """
    if ref:
        rows = await fetch_ref(ref)
        return ("single", rows[:1]) if rows else ("empty", [])
    if keyword:
        rows = await (fetch_keyword or fetch_ref)(keyword)
        if not rows:
            return ("empty", [])
        if len(rows) == 1:
            # 收案 2：關鍵字命中恰一筆 ⇒ 不必再讓使用者從候選清單裡選，直接當單筆算。
            return ("single", rows)
        if len(rows) <= cap:
            return ("candidates_all", rows)
        return ("candidates_more", rows[:cap])
    if fetch_default is not None:
        rows = await fetch_default(None)
        if not rows:
            return ("empty", [])
        return ("candidates_all", rows[:cap])
    return ("empty", [])


def _finish_generic(domain: str, tag_hint: str, builder: Callable[[dict, str], str],
                    status: str, rows: list[dict[str, Any]], cap: int,
                    query: Optional[str] = None) -> dict[str, Any]:
    if status == "empty":
        return _no_match()
    if status == "single":
        row = rows[0]
        facts = builder(row, "")
        tag = str(row.get("id") or row.get("member_user_id") or tag_hint)
        return _ok_single(domain, tag, facts, cap)
    skip_refine = status == "candidates_all"
    return _ok_candidates(domain, tag_hint, rows, cap, skip_refine, query=query)


# ── bills ───────────────────────────────────────────────────────────────────
async def query_bills(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    builder = BILL_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not _identity_gate_ok(identity, role_id, user_id):
        return _no_match()
    api = _get_api()

    async def fetch(q: Optional[str]) -> list[dict[str, Any]]:
        resp = await api.get_bills(role_id=role_id, user_id=user_id,
                                    viewer_user_id=user_id, bill_ref=q)
        return _rows_of(resp)

    async def fetch_keyword(k: str) -> list[dict[str, Any]]:
        # 口語指涉（「8 月租金」「信義區那戶」）走 keyword（jgb2 `title LIKE`），⛔ 不當 bill_ref 送
        resp = await api.get_bills(role_id=role_id, user_id=user_id,
                                    viewer_user_id=user_id, keyword=k)
        return _rows_of(resp)

    cap = _candidate_cap()
    ref, keyword = args.get("ref"), args.get("keyword")
    status, rows = await _resolve(ref, keyword, cap, fetch_ref=fetch,
                                  fetch_keyword=fetch_keyword, fetch_default=fetch)
    return _finish_generic("bills", face, builder, status, rows, cap, query=ref or keyword)


# ── contracts ────────────────────────────────────────────────────────────────
async def query_contracts(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    builder = CONTRACT_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not _identity_gate_ok(identity, role_id, user_id):
        return _no_match()
    api = _get_api()

    async def fetch_ref(r: str) -> list[dict[str, Any]]:
        resp = await api.get_contracts(role_id=role_id, contract_ids=r,
                                        viewer_user_id=user_id)
        return _rows_of(resp)

    async def fetch_keyword(k: str) -> list[dict[str, Any]]:
        resp = await api.get_contracts(role_id=role_id, keyword=k,
                                        viewer_user_id=user_id)
        return _rows_of(resp)

    async def fetch_default(_: Optional[str]) -> list[dict[str, Any]]:
        resp = await api.get_contracts(role_id=role_id, viewer_user_id=user_id)
        return _rows_of(resp)

    cap = _candidate_cap()
    ref, keyword = args.get("ref"), args.get("keyword")
    status, rows = await _resolve(ref, keyword, cap, fetch_ref=fetch_ref,
                                  fetch_keyword=fetch_keyword, fetch_default=fetch_default)
    return _finish_generic("contracts", face, builder, status, rows, cap, query=ref or keyword)


# ── meters ───────────────────────────────────────────────────────────────────
async def query_meters(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    builder = METER_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not JGBSystemAPI._validate_identity(role_id, user_id):
        return _no_match()
    api = _get_api()

    async def fetch(q: Optional[str]) -> list[dict[str, Any]]:
        resp = await api.get_meters(role_id=role_id, keyword=q)
        return _rows_of(resp)

    cap = _candidate_cap()
    ref, keyword = args.get("ref"), args.get("keyword")
    status, rows = await _resolve(ref, keyword, cap, fetch_ref=fetch)
    return _finish_generic("meters", face, builder, status, rows, cap, query=ref or keyword)


# ── accounts（成員候選 vs. 已知 user_id 直查權限，兩條路徑不共用 _resolve）──
async def query_accounts(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    # 主 session 2026-09-04 收案裁：`登入排障` 的 builder 要合約列（is_tenant_registered／
    # to_user_login_email），本工具目前只走成員／權限資料源，餵成員列會產出錯誤 facts。
    # ⛔ 寧可拒（INVALID_INPUT）也不出錯 facts；改路由到 get_contracts 屬 design 域映射表修訂（1.7 前）。
    if face == "登入排障":
        return _invalid_input()
    builder = ACCOUNT_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not JGBSystemAPI._validate_identity(role_id, user_id):
        return _no_match()
    api = _get_api()
    cap = _candidate_cap()

    ref = args.get("ref")
    keyword = args.get("keyword")

    if ref:
        perm_resp = await api.get_member_permissions(role_id=role_id, user_id=str(ref))
        perm_rows = _rows_of(perm_resp)
        if not perm_rows:
            return _no_match()
        perm = perm_rows[0]
        member = dict(perm)
        member["permissions"] = perm_rows
        facts = builder(member, "")
        return _ok_single("accounts", str(ref), facts, cap)

    if keyword:
        members_resp = await api.get_team_members(role_id=role_id, keyword=keyword)
        rows = _rows_of(members_resp)
        if not rows:
            return _no_match()
        if len(rows) <= cap:
            return _ok_candidates("accounts", face, rows, cap, True, query=keyword)
        return _ok_candidates("accounts", face, rows[:cap], cap, False, query=keyword)

    # accounts 無預設列表（域映射表：ref／keyword 皆無 ⇒ NO_MATCH，僅 bills／contracts 例外）
    return _no_match()


# ── estates（secondary get_estate_detail 補 detail，builder 三參數）────────
async def query_estates(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    builder = ESTATE_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not JGBSystemAPI._validate_identity(role_id, user_id):
        return _no_match()
    api = _get_api()
    cap = _candidate_cap()

    ref = args.get("ref")
    keyword = args.get("keyword")
    q = ref or keyword
    if not q:
        # estates 無預設列表（同 accounts／meters：ref／keyword 皆無 ⇒ NO_MATCH）
        return _no_match()

    status_resp = await api.get_estate_status(role_id=role_id, keyword=q)
    rows = _rows_of(status_resp)
    if not rows:
        return _no_match()

    # sentinel（{"found": False,...}）＝ wrapper 查無，語意上零命中，但 builder
    # 對它有既定的「非刊登中」決定性措辭（estates.py:build_estate_status_facts）——
    # 視為單筆直接算 facts，⛔ 不落入候選 cap 邏輯（那是給「多筆待縮小」用的）。
    sentinel = rows[0].get("found") is False

    if ref or sentinel or (keyword and len(rows) == 1):
        # ref 為 session slot 已確立值 → 單筆；sentinel 亦視為單筆（決定性說明零命中）；
        # 收案 2：keyword 命中恰一筆同樣不必再讓使用者從候選清單選，直接當單筆算。
        row = rows[0]
        estate_id = row.get("id")
        detail = None
        if not sentinel and estate_id is not None:
            detail_resp = await api.get_estate_detail(estate_id=estate_id)
            detail_rows = _rows_of(detail_resp)
            detail = detail_rows[0] if detail_rows else None
        facts = builder(row, detail, "")
        tag = str(estate_id) if estate_id is not None else q
        return _ok_single("estates", tag, facts, cap)

    # keyword-only、非 sentinel：可能多筆待縮小，套候選 cap 邏輯（同其餘四域）。
    if len(rows) <= cap:
        return _ok_candidates("estates", face, rows, cap, True, query=q)
    return _ok_candidates("estates", face, rows[:cap], cap, False, query=q)


# ── repairs（收案修正 5：新讀工具，pm 單證身分閘同 bills）───────────────────
#: `RepairApiController@index` mapping.status──32＝結單、64＝封存視為「已結」，
#: 其餘（申請中／安排修繕／完成修繕）算「未結」，無 ref/keyword 時的預設列表口徑。
_CLOSED_REPAIR_STATUSES: frozenset = frozenset({32, 64})


async def query_repairs(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    # 收案 6：分類樹是靜態參考資料（同分類設定，非個資、不分業者），
    # `confirm.request` 驗 category_name 前模型要有地方查得到合法名稱——
    # 同 `query_accounts` 對「登入排障」的既有 face-bypass 寫法。
    if face == "修繕分類":
        return _ok_single("repairs", "categories",
                          build_repair_category_tree_facts(), _candidate_cap())
    builder = REPAIR_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    user_id = getattr(identity, "user_id", None)
    if not _identity_gate_ok(identity, role_id, user_id):
        return _no_match()
    api = _get_api()

    async def fetch_all() -> list[dict[str, Any]]:
        resp = await api.get_repairs(role_id=role_id, user_id=user_id)
        return _rows_of(resp)

    async def fetch_ref(r: str) -> list[dict[str, Any]]:
        rows = await fetch_all()
        return [row for row in rows if str(row.get("id")) == str(r)]

    async def fetch_keyword(k: str) -> list[dict[str, Any]]:
        rows = await fetch_all()
        kw = str(k)
        return [row for row in rows
                if kw in str(row.get("estate_title") or "")
                or kw in str(row.get("broken_reason") or "")
                or kw in str(row.get("broken_note") or "")]

    async def fetch_default(_: Optional[str]) -> list[dict[str, Any]]:
        rows = await fetch_all()
        return [row for row in rows if row.get("status") not in _CLOSED_REPAIR_STATUSES]

    cap = _candidate_cap()
    ref, keyword = args.get("ref"), args.get("keyword")
    status, rows = await _resolve(ref, keyword, cap, fetch_ref=fetch_ref,
                                  fetch_keyword=fetch_keyword, fetch_default=fetch_default)
    return _finish_generic("repairs", face, builder, status, rows, cap, query=ref or keyword)
