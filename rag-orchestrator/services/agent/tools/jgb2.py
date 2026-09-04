"""`jgb2.query.<domain>` 五域工具（spec agentic-mcp-orchestration・任務 1.5）。

契約基準：`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 3
（`jgb2.query.<domain>` 列、域映射表、`FACE_BUILDER_REGISTRIES` 表）。

每個 `query_<domain>(identity, args) -> dict` 是**未包裝**的工具函式——回傳形狀見
`_ok_single`／`_ok_candidates`／`_no_match`／`_invalid_input`，由後續任務（1.4／1.7）
包成 `ToolResult`。⛔ 本檔不 import `services.agent.tools.registry`（1.3 平行中）。

身分（DSP-011，本系統只管額度、權限交 jgb2 API 裁）：
- bills／contracts：呼叫時帶 `viewer_user_id=identity.user_id`（jgb2 圈定，
  `get_bills`／`get_contracts` 的顯式轉發，見 `jgb_system_api.py`）；本工具層只要求
  `role_id` 存在才嘗試查詢（API 本身對 `user_id`/`bill_ref`/`contract_ids` 三選一
  另有 `_validate_identity` 檢查，查無識別即自然降級為空列 → `NO_MATCH`）。
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
from services.jgb.bills import BILL_FACE_BUILDERS
from services.jgb.contracts import FACE_BUILDERS as CONTRACT_FACE_BUILDERS
from services.jgb.accounts import ACCOUNT_FACE_BUILDERS
from services.jgb.iot import METER_FACE_BUILDERS
from services.jgb.estates import ESTATE_FACE_BUILDERS

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


def _ok_candidates(domain: str, tag: str, rows: list, cap: int,
                    skip_refine: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {"facts": "", "candidates": rows,
                 "candidate_cap": cap, "skip_refine": skip_refine},
        "provenance": [{"source": f"jgb2:{domain}#{tag}", "text": "", "citable": True}],
        "text_for_model": "",
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
                    status: str, rows: list[dict[str, Any]], cap: int) -> dict[str, Any]:
    if status == "empty":
        return _no_match()
    if status == "single":
        row = rows[0]
        facts = builder(row, "")
        tag = str(row.get("id") or row.get("member_user_id") or tag_hint)
        return _ok_single(domain, tag, facts, cap)
    skip_refine = status == "candidates_all"
    return _ok_candidates(domain, tag_hint, rows, cap, skip_refine)


# ── bills ───────────────────────────────────────────────────────────────────
async def query_bills(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    builder = BILL_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    if not role_id:
        return _no_match()
    user_id = getattr(identity, "user_id", None)
    api = _get_api()

    async def fetch(q: Optional[str]) -> list[dict[str, Any]]:
        resp = await api.get_bills(role_id=role_id, user_id=user_id,
                                    viewer_user_id=user_id, bill_ref=q)
        return _rows_of(resp)

    cap = _candidate_cap()
    ref, keyword = args.get("ref"), args.get("keyword")
    status, rows = await _resolve(ref, keyword, cap, fetch_ref=fetch, fetch_default=fetch)
    return _finish_generic("bills", face, builder, status, rows, cap)


# ── contracts ────────────────────────────────────────────────────────────────
async def query_contracts(identity: Any, args: dict[str, Any]) -> dict[str, Any]:
    face = args.get("face")
    builder = CONTRACT_FACE_BUILDERS.get(face) if isinstance(face, str) else None
    if builder is None:
        return _invalid_input()

    role_id = getattr(identity, "role_id", None)
    if not role_id:
        return _no_match()
    user_id = getattr(identity, "user_id", None)
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
    return _finish_generic("contracts", face, builder, status, rows, cap)


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
    return _finish_generic("meters", face, builder, status, rows, cap)


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
            return _ok_candidates("accounts", face, rows, cap, True)
        return _ok_candidates("accounts", face, rows[:cap], cap, False)

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

    if ref or sentinel:
        # ref 為 session slot 已確立值 → 單筆；sentinel 亦視為單筆（決定性說明零命中）。
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
        return _ok_candidates("estates", face, rows, cap, True)
    return _ok_candidates("estates", face, rows[:cap], cap, False)
