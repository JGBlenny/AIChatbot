"""`OutlineAssembler`（spec agentic-mcp-orchestration・任務 3.2｜design 元件 5）。

**組裝來源＝程式，⛔ 無 LLM**（R5.4：可重跑、決定性、版本戳＋sha256）。

## 本檔與 `services/agent/prompt_assembler.py`（任務 3.1）的關係
3.1 只**定義介面**（`OutlineDocLike`／`OutlineSectionLike` Protocol，
`runtime_checkable` 結構型別）——它不 import 本檔，本檔也不 import 它。
本檔的 `OutlineDoc`／`OutlineSection`（pydantic `BaseModel`）欄位對齊該
Protocol：`OutlineDoc{audience, version, sha256, token_count, sections, text}`、
`OutlineSection{id, title, text, source_ids, citable}`——多出的
`token_count_approx` 欄位是本檔自用的附加資訊，Protocol 是結構型別，
多欄位不影響滿足關係。

## 與 `services/agent/tools/kb.py`（任務 1.4）的關係
`kb.py` 定義的 `OutlineResolver = Callable[[Identity, str],
Union[ToolResult, Awaitable[ToolResult]]]`——`kb_get()` 對 `outline:*` 直接
`return outline_resolver(identity, kb_id)`（或 await 後原樣回傳），**不做任何
形狀轉換**。因此 `make_outline_resolver()` 必須回傳 `ToolResult`，⛔ 不是
裸 dict——這是已合併程式碼定的實際契約（CANON：程式如何跑，程式說了算），
本檔對齊它。

## 售前大綱＝正本組裝（任務 3.2，2026-09-07 業主核）
`build_prospect_outline` **不再讀 DB**：它讀 git 正本（`rag-orchestrator/canon/prospect.md`
＋同源 `.json`），逐細目組成章節，並附一節 `outline:toc`。組裝規則、可見性與啟動失敗語義
都在 `services/agent/canon/canon_assembler.py`（design 元件 5）。
⚠️ 舊的「六模組分類表＋邊界句抽取＋DSP-009／CTA 固定節」已**退役**：粗目 G／F 在正本內
承接那兩節的角色。`build_toc(db_pool, audience, vendor_id)`（pm／tenant 的『系統脈絡』目錄）
**保留現役**，它有 vendor 過濾，⛔ 不得拿掉。
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from services.agent.identity import Audience, Identity
from services.agent.tools.registry import Provenance, ToolResult
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

# ---------------------------------------------------------------------------
# 資料模型（對齊 prompt_assembler.py 的 OutlineDocLike／OutlineSectionLike）
# ---------------------------------------------------------------------------


class OutlineSection(BaseModel):
    # id 兩種形狀：正本細目節＝細目 id（`prospect/A/product-overview`，3.2 起），
    # 目錄節＝`outline:toc`／`outline:toc:<row id>`（pm／tenant）。
    # `kb.get` 一律以 `outline:<id>` 取用（`tools/kb.py:kb_get` 以此前綴路由）。
    id: str
    title: str
    text: str
    source_ids: list[int] = []
    citable: bool = True


class OutlineDoc(BaseModel):
    audience: Audience
    version: str
    sha256: str
    token_count: int
    sections: list[OutlineSection]
    text: str
    #: R5.5 token 計數退化旗標——tiktoken 編碼取不到時 True（`len(text)//2` 近似）。
    #: 非 Protocol 欄位（`OutlineDocLike` 不要求），⛔ 不影響結構型別滿足關係。
    token_count_approx: bool = False


class OutlineBudgetExceeded(Exception):
    """R5.5：大綱／目錄超過 token 預算——啟動即紅，⛔ 不得靜默截斷。"""


# ---------------------------------------------------------------------------
# token 計數（R5.5：tiktoken；取不到編碼 ⇒ 近似值＋approx=True）
# ---------------------------------------------------------------------------


def _count_tokens(text: str) -> tuple[int, bool]:
    """回傳 `(token_count, approx)`。`approx=True` ⇒ 用 `len(text)//2` 近似。"""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), False
    except Exception:  # noqa: BLE001 — 離線／套件缺失／編碼檔抓不到，一律 fail-soft
        return max(1, len(text) // 2), True


# ---------------------------------------------------------------------------
# psycopg2 讀取（pm／tenant 的『系統脈絡』目錄；⛔ 不混用 asyncpg `$n`）
# ⚠️ 售前大綱的 DB 讀取（`_fetch_prospect_pool_rows`）已於 3.2 退役——正本是 git，
#    DB 售前池是它的衍生物，大綱⛔不以衍生物為來源。
# ---------------------------------------------------------------------------


#: build_toc 用的角色→target_user 對應（design 元件 5：「$tu = <audience 對應
#: target_user>」）。⛔ 不重用 `VendorKnowledgeRetrieverV2._effective_target_user`
#: ——那支是「未知角色→tenant」的可見性 fail-safe 正規化，語意是知識池過濾；
#: 這裡的映射是「TOC 只服務 pm／tenant 兩種身分」的窄範圍宣告，兩者目的不同、
#: 硬共用會讓其中一邊改動時誤傷另一邊。
_TOC_AUDIENCE_TARGET_USER: dict[str, str] = {
    "property_manager": "property_manager",
    "tenant": "tenant",
}


def _fetch_toc_rows(db_pool, audience: str, vendor_id: Optional[int]) -> list[tuple]:
    """`系統脈絡` 列（`(id, question_summary, answer, updated_at)`），加 vendor／target_user 過濾。

    ⛔ **不照抄 `services/system_context.py:_fetch_base`／`_fetch_appends`**
    （design 元件 5 明文禁止）——那兩支只切 `category`／`target_user`，完全
    沒有 `vendor_ids` 過濾（`system_context.py` 是「系統脈絡＝跨業者共用底座」
    的既有假設；agentic 大綱要對到 MCP 門面解析出的單一 `vendor_id`，不能照搬）。
    這裡只借它們「`target_user` 分層＋`IS NULL` 放行通用列」的語義，自寫成
    本檔獨立的 psycopg2 `%s` 條件（見不變量 29 附註：這兩個條件因不走
    `build_visibility_predicate`——`系統脈絡` 是該謂詞明確排除的保留分類，
    套用它反而會把系統脈絡列全部濾掉——ⓘ 這是刻意的例外，不是遺漏）。
    """
    if audience not in _TOC_AUDIENCE_TARGET_USER:
        raise ValueError(
            f"build_toc 只服務 audience ∈ {sorted(_TOC_AUDIENCE_TARGET_USER)}，"
            f"得到 {audience!r}（prospect 用 build_prospect_outline）"
        )
    target_user_token = _TOC_AUDIENCE_TARGET_USER[audience]

    # 這兩個條件獨立於 build_visibility_predicate，見上方 docstring 的理由。
    _vendor_filter_sql = "AND (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])"
    _target_user_filter_sql = "AND (kb.target_user IS NULL OR kb.target_user && %s::text[])"

    sql = (
        "SELECT kb.id, kb.question_summary, kb.answer, kb.updated_at "
        "FROM knowledge_base kb "
        "WHERE kb.category = %s AND kb.is_active = TRUE "
        f"{_vendor_filter_sql} {_target_user_filter_sql} "
        "ORDER BY kb.id"
    )
    params = [
        VendorKnowledgeRetrieverV2.SYSTEM_DOC_CATEGORY,
        [vendor_id],
        [target_user_token, "all_users"],
    ]
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        db_pool.putconn(conn)


# ---------------------------------------------------------------------------
# 決定性組裝
# ---------------------------------------------------------------------------

_SECTION_SEP = "\n\n---\n\n"


def _max_updated_at_iso(rows: list[tuple], updated_at_index: int) -> str:
    """池空 ⇒ epoch（決定性、⛔ 用當下時間——那會讓空池每次組裝的 version 都不同）。"""
    values = [r[updated_at_index] for r in rows if r[updated_at_index] is not None]
    if not values:
        return datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat()
    latest = max(values)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return latest.isoformat()


def _build_doc(
    *, audience: Audience, sections: list[OutlineSection], version: str
) -> OutlineDoc:
    # DSP-020：章節標題帶 section id——它是資料段行首標記裡的 `source` 那一段
    # （DSP-029a：模型照抄整串標記，⛔ 不再自己填 source 欄位）
    # （`outline:contract`），只給標題模型無從得知 id（影子 2026-09-05 實測）。
    text = _SECTION_SEP.join(f"【{s.id}】{s.title}\n{s.text}" for s in sections)
    # sha 涵蓋 version（＝池列 max(updated_at)），⛔ 不只涵蓋 text——
    # 這樣「內容沒變、只有某列 updated_at 被 touch 過」也會讓快取判斷為「已變」，
    # 對應 R5.1「售前池任一列更新 ⇒ 重新組裝大綱（快取失效）」；只掛 text 會讓
    # 一次無內容變更的 UPDATE（例如審核旗標重寫同一批列）漏掉快取失效。
    sha = hashlib.sha256(f"{version}\x00{text}".encode("utf-8")).hexdigest()
    token_count, approx = _count_tokens(text)
    return OutlineDoc(
        audience=audience,
        version=version,
        sha256=sha,
        token_count=token_count,
        sections=sections,
        text=text,
        token_count_approx=approx,
    )


async def build_prospect_outline(db_pool) -> OutlineDoc:
    """R2.6／R5.4：git 正本（`canon/prospect.md`）→ 逐細目章節 ＋ `outline:toc`。

    ⚠️ **`db_pool` 保留於簽名但不再使用**（`app.py` 不改；3.2 起大綱不讀 DB）。
    步驟（design 元件 5「呼叫鏈與失敗語義」）：

    1. `load_canon_or_die(resolve_canon_dir(), "prospect")`——`.md` 解析＋`.json`
       逐位元組同源比對；缺檔／不同源／格式錯 ⇒ raise（`_agent_configured()` 為真
       時由 `app.py` 升成啟動紅，否則 agent 停用；⛔ 不新增降級路徑）。
    2. `register_canon("prospect", doc)`——`make_outline_resolver` 每回合要用同一份
       `CanonDoc` 套可見性（`OutlineDoc` 是 pydantic，⛔ 不掛在它身上）。
    3. `build_outline(doc)` ＋ 附 `outline:toc` 節（**啟動時**以售前**靜態身分**算一次：
       prospect 正本單一受眾、走 b2b 分支、不依 vendor ⇒ 啟動時算得出來。
       ⚠️ 每回合的候選子集與動態 toc 是 4.1 `CandidateOutlineDoc`，⛔ 不在本片）。
    4. `check_budget(min(env 上限, 正本 budget_tokens))`——正本自帶的預算是上限之一，
       ⛔ 不讓 env 單方面把上限開大（security-reviewer P2-3）。
    """
    from services.agent.canon.canon_assembler import (  # 循環相依 ⇒ 函式內 import
        build_canon_toc, build_outline, load_canon_or_die, register_canon, resolve_canon_dir,
    )

    canon = load_canon_or_die(resolve_canon_dir(), "prospect")
    register_canon("prospect", canon)

    doc = build_outline(canon)
    # 售前靜態身分：prospect ＝ b2b ＋ 無 role_id（memory project_presales_target_user_routing；
    # jgb2 面板送 prospect 時 mode=b2b）。⛔ 勿改回 b2c——那會走 vendor 業態分支，
    # 而啟動時沒有真實 vendor 可解析（vendor_id=0 只是佔位）。
    toc = build_canon_toc(
        canon,
        Identity(vendor_id=0, target_user="prospect", mode="b2b"),
        vendor_business_types=frozenset(),
    )
    doc = _build_doc(
        audience=canon.audience,
        sections=list(doc.sections) + [toc],
        version=canon.version,
    )
    check_budget(doc, min(default_token_limit("prospect"), canon.budget_tokens))
    return doc


def _clip_first_paragraph(answer: str, limit: int = 120) -> str:
    if not answer:
        return ""
    first = re.split(r"\n\s*\n", answer.strip(), maxsplit=1)[0].strip()
    first = " ".join(first.split())
    return first if len(first) <= limit else first[: limit - 1] + "…"


async def build_toc(db_pool, audience: Audience, vendor_id: int) -> OutlineDoc:
    """R5.3：pm／tenant 身分的『系統脈絡』目錄（只列標題層級，`citable=False`）。

    章節皆不可引用（決策 10 修訂：目錄只導航、不當事實依據；細節交
    `kb.get`／`help.read`／`jgb2.query` 走各自的可見性與 citable 判定）。
    """
    rows = _fetch_toc_rows(db_pool, audience, vendor_id)
    sections = [
        OutlineSection(
            id=f"outline:toc:{row_id}",
            title=question_summary or "",
            text=_clip_first_paragraph(answer or ""),
            source_ids=[row_id],
            citable=False,
        )
        for row_id, question_summary, answer, _updated_at in rows
    ]
    version = _max_updated_at_iso(rows, updated_at_index=3)
    return _build_doc(audience=audience, sections=sections, version=version)


def check_budget(doc: OutlineDoc, limit_tokens: int) -> None:
    """R5.5：`doc.token_count > limit_tokens` ⇒ raise（啟動即紅，⛔ 不靜默截斷）。"""
    if doc.token_count > limit_tokens:
        raise OutlineBudgetExceeded(
            f"{doc.audience} 大綱／目錄 token_count={doc.token_count} 超過上限 "
            f"{limit_tokens}（version={doc.version}）"
        )


#: R5.5 env 對應表（呼叫端在啟動時讀，傳給 `check_budget`；本檔只提供預設值
#: 常數表，⛔ 自己讀 env——讀 env 的時機與位置屬 2.5 接線範圍）。
OUTLINE_TOKEN_LIMIT_DEFAULTS: dict[str, int] = {
    "prospect": 12_000,
    "property_manager": 8_000,
    "tenant": 8_000,
}
# 🔴 2026-09-07 實測：整份售前正本大綱（38 細目＋toc）cl100k 為 10,336 tokens，中文約 1.1 字元/token（research 假設 1.6 是錯的）；
# 10,000 是估錯的數字 ⇒ 業主裁 12,000（正本 budget_tokens 同步），4.1 後每回合只注入 K 候選、整份正本是退路。
OUTLINE_TOKEN_LIMIT_ENV: dict[str, str] = {
    "prospect": "AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT",
    "property_manager": "AGENT_OUTLINE_TOKEN_LIMIT_PM",
    "tenant": "AGENT_OUTLINE_TOKEN_LIMIT_TENANT",
}


def default_token_limit(audience: Audience) -> int:
    """`OUTLINE_TOKEN_LIMIT_ENV[audience]` 覆寫，缺省用 `OUTLINE_TOKEN_LIMIT_DEFAULTS`。"""
    env_key = OUTLINE_TOKEN_LIMIT_ENV.get(audience)
    default = OUTLINE_TOKEN_LIMIT_DEFAULTS.get(audience)
    if default is None:
        raise ValueError(f"未知 audience={audience!r}")
    raw = os.environ.get(env_key or "", "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{env_key}={raw!r} 不是合法整數") from exc


# ---------------------------------------------------------------------------
# kb.get("outline:*") resolver（1.4 接線用；`tools/kb.py:OutlineResolver` 契約）
# ---------------------------------------------------------------------------


def make_outline_resolver(cache: dict):
    """回傳 `Callable[[Identity, str], ToolResult]`，供 `kb_get(outline_resolver=...)`。

    `cache` 形狀：`{audience: OutlineDoc}`（`Audience` → 該身分目前生效的
    大綱／目錄）。由呼叫端（2.5）維護——重跑 `build_prospect_outline`／
    `build_toc` 後覆寫對應鍵即可失效重建，本函式只做**查找**，⛔ 自己不重建、
    不持有 db_pool（重建時機屬 Runtime／排程，不是 resolver 的職責）。

    ⚠️ **已註冊正本的受眾走正本**（3.2）：`canon_assembler.get_canon(audience)` 有值時
    改呼叫 `resolve_canon_section`，每回合套 `canon_visible`（未審／不可見／不存在
    一律 `NO_MATCH`）；未註冊（pm／tenant 的 DB TOC）維持下列 cache 查找邏輯。

    找不到大綱（cache 未就緒）或找不到該 section id ⇒ `ToolResult(ok=False,
    error="NO_MATCH")`——與 `kb.py` 池外查詢同一錯誤語意，⛔ 對模型區分兩種
    「找不到」（design：不對模型洩漏「不存在」與「無權限」的差異，這裡延伸為
    「不存在」與「大綱還沒建好」同樣不區分）。
    """

    def resolver(identity: Identity, kb_id: str) -> ToolResult:
        from services.agent.canon.canon_assembler import (  # 循環相依 ⇒ 函式內 import
            get_canon, resolve_canon_section,
        )

        audience = identity.resolved_audience()
        canon = get_canon(audience)
        if canon is not None:
            # F7 修補的產線接線點：目錄與 `outline:<fine id>` 都**每回合**套可見性，
            # identity 逐次傳入（⛔ 不綁在工廠——工廠只建一次，身分每回合不同）。
            # `vendor_business_types` 在 3.2 固定空集合（prospect＝b2b 分支不看它）；
            # b2c 受眾接上正本時由呼叫端解析後傳入（元件 6）。
            return resolve_canon_section(
                canon, identity, kb_id, vendor_business_types=frozenset()
            )
        doc = cache.get(audience)
        if doc is None:
            return ToolResult(ok=False, error="NO_MATCH")
        for section in doc.sections:
            if section.id == kb_id:
                return ToolResult(
                    ok=True,
                    data={
                        "id": section.id,
                        "question_summary": section.title,
                        "answer": section.text,
                    },
                    provenance=[
                        Provenance(source=section.id, text=section.text, citable=section.citable)
                    ],
                    text_for_model=section.text,
                )
        return ToolResult(ok=False, error="NO_MATCH")

    return resolver
