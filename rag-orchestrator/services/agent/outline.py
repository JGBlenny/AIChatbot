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

## 六模組主題頁分段規則（局部決定，tasks.md 3.2 收案註記標「需局部決定」）
`categories` 欄位現況五值：`售前模組`／`售前顧問`／`售前方案`／`售前價格`／
`售前競品`（`docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin
-tAc "SELECT DISTINCT unnest(categories) FROM knowledge_base WHERE categories
IS NOT NULL"` 可重跑查證）。只有 `售前模組` 底下的列需要再依關鍵字細分成
kb 3622 §3「六大模組」（房源／租約／帳務／團隊／IoT／修繕，見
`docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tAc
"SELECT answer FROM knowledge_base WHERE id=3622"`）；其餘四類 categories
本身已是自然分段單位，各自成一個非模組頁面小節（顧問定位／方案與試用／
價格與試用／競品比較）——**這不在 R5.1「六模組主題頁」字面之內，但若略去
會讓 23 筆售前池裡約 14 筆（顧問/方案/價格/競品類）完全進不了大綱**，
與 R5.1 使用者故事「我問的每一句都應對到同一份完整的產品大綱」相牴觸，
故本檔把它們當成大綱的第五類必要小節，一併列在 `text` 內、以獨立 section id
呈現，供 `check_impl` 或後續 review 追認或調整此局部決定。
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
from services.vendor_knowledge_retriever_v2 import (
    VendorKnowledgeRetrieverV2,
    build_visibility_predicate,
)

# ---------------------------------------------------------------------------
# 資料模型（對齊 prompt_assembler.py 的 OutlineDocLike／OutlineSectionLike）
# ---------------------------------------------------------------------------


class OutlineSection(BaseModel):
    id: str  # 形如 "outline:contract"；kb.get("outline:*") 取回它
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
# 六大模組分類表（kb 3622 §3，⛔ 無 LLM——純字串包含比對，固定順序、先中先得）
# ---------------------------------------------------------------------------

#: (slug, 標題, 關鍵字集合)。比對對象＝該列 `question_summary`（+ `categories`
#: 陣列以空白接起）。⚠️ **有序**——3604「大房東報表」同時含團隊與帳務相關字，
#: 團隊排在帳務之前才能命中「團隊」而非被「代收代付」誤分去帳務；反過來看，
#: 「批次匯入」在房源模組先比對，避免被誤分去帳務／租約。
SIX_MODULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("listing", "房源", ("房源", "物件集中", "社區歸戶", "批次上傳", "批次匯入", "VR看屋")),
    ("lease", "租約", ("合約", "簽約", "電子簽章", "委託合約", "社宅", "範本")),
    ("team", "團隊", ("團隊", "協作", "角色權限", "大房東報表", "代收代付", "月結")),
    ("billing", "帳務", ("帳務", "帳單", "收租", "對帳", "金流", "發票", "儲值", "催繳", "逾期", "繳租", "遲繳", "拖欠")),
    ("iot", "IoT設備", ("智慧電錶", "智慧門鎖", "電表", "IoT", "硬體", "抄表", "換鎖")),
    ("repair", "修繕", ("修繕", "報修", "維修", "進度追蹤")),
)
#: `售前模組` 底下沒命中任何六大模組關鍵字時的兜底桶——⛔ 不丟資料，寧可粗分。
_MODULE_FALLBACK_SLUG = "module-misc"
_MODULE_FALLBACK_TITLE = "其他產品功能"

#: 非模組 categories → (slug, 標題)。這四類與 `售前模組` 並列、⛔ 不強行塞進
#: 六大模組（見本檔 docstring「六模組主題頁分段規則」）。
NON_MODULE_CATEGORY_SECTIONS: dict[str, tuple[str, str]] = {
    "售前顧問": ("positioning", "定位與顧問"),
    "售前方案": ("plans", "個人房東方案"),
    "售前價格": ("pricing", "價格與試用"),
    "售前競品": ("competitors", "競品比較"),
}
_MODULE_CATEGORY = "售前模組"

#: R6.2 同款封閉詞集的「邊界句」抽取——answer 內含這些詞的**句子**進邊界句段
#: （非整列排除；該列仍留在自己的模組／類別小節）。
_BOUNDARY_TERMS: tuple[str, ...] = ("不支援", "無法", "不提供")
#: 中文常見句界符號（含分號、換行），用來把 answer 切成句子做邊界句抽取——
#: 含分號是刻意的：「支援 A；不支援 B」這種同句用分號並列兩個子句時，若不切開，
#: 抽出的「邊界句」會夾帶前半句「支援 A」，讓一句混合正負面資訊的話整句被
#: 誤標成邊界句引用來源。
_SENTENCE_SPLIT_RE = re.compile(r"[。！？；\n]+")

#: DSP-009（`.claude/DECISIONS.md`）五類「刻意不補」——逐字沿用該條目原文的
#: 列舉，⛔ 不改寫措辭（改寫等於自行重新裁決範圍）。
DSP009_DELIBERATE_GAPS: tuple[str, ...] = (
    "客戶案例／規模",
    "SLA／賠償",
    "資安認證／資料存放",
    "個資法",
    "客製報價",
)

#: 售前 handoff 固定句（`services/conversational_config.py:PRESALES_HANDOFF_MESSAGE`）
#: 為本系統既有的單一事實常數，直接沿用；⛔ 不在本檔另造一份轉人措辭。
from services.conversational_config import PRESALES_HANDOFF_MESSAGE  # noqa: E402

#: CTA 段：`services/conversational_config.py:PRESALES_CTA_RULES`／
#: `PRESALES_ANSWER_RULES` 是**寫給模型的排版／合成指令**（第二人稱祈使句、
#: 大量「務必」「⛔」「範例」），語意上是「LLM 系統提示的一段」而非「大綱事實
#: 內容」；直接塞進 `OutlineDoc.text` 會讓一段指令文字偽裝成 `kb.get` 可引用
#: 的「知識」，與 R11.5 白名單「大綱＝已審核知識列組裝」的定位不符（見本檔
#: docstring）。故本檔 ⛔ 不 import 它，改用下列固定句——純陳述「有哪些出口」
#: 的事實句，可安全被引用。
_CTA_TEXT = (
    "下一步：可免費試用一個月親自體驗；"
    "如需方案與費用可參考 https://www.jgbsmart.com/pricing；"
    "想預約 demo 或請專人協助可至 https://www.jgbsmart.com/demo-form；"
    "或點對話下方『找真人』直接聯繫。"
)


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
# psycopg2 讀取（與 `tools/kb.py:fetch_visible_row` 同款 pool 取法——
# `build_visibility_predicate` 回傳 `%s` 佔位符，⛔ 不混用 asyncpg `$n`）
# ---------------------------------------------------------------------------


def _fetch_prospect_pool_rows(db_pool, identity: Identity) -> list[tuple]:
    """`(id, question_summary, answer, categories, updated_at)` 已審核售前池列。

    **不變量 29**（`scripts/audit/checks/agent_boundary.py:check_29_predicate_single_source`）
    只掃描 `services/agent/prompt_assembler.py:build_prospect_outline` 這個
    `(檔案, 函式)` 對；`build_prospect_outline` 現落在本檔
    `services/agent/outline.py`，不在該掃描清單內——**回報**：這條不變量目前
    對本檔是「找不到此函式，略過」（`notes`，非 `bad`），空跑通過而非真的驗過。
    ⛔ 依 brief 指示不改 checker；已在此處留痕供主 session 決定是否把
    `services/agent/outline.py` 加進 3.2 定案時的目標清單。
    本函式仍照不變量 29 的精神實作：不自行寫死 `vendor_ids`／`business_types`
    字面 WHERE 條件，唯一謂詞來源是 `build_visibility_predicate()`。
    """
    predicate_sql, predicate_params = build_visibility_predicate(identity)
    sql = (
        "SELECT kb.id, kb.question_summary, kb.answer, kb.categories, kb.updated_at "
        "FROM knowledge_base kb "
        f"WHERE kb.outline_approved_by IS NOT NULL {predicate_sql} "
        "ORDER BY kb.id"
    )
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, list(predicate_params))
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        db_pool.putconn(conn)


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
# 六模組／類別分類（純函式，⛔ 無 LLM）
# ---------------------------------------------------------------------------


def _classify_module_row(question_summary: str, categories: Optional[list]) -> tuple[str, str]:
    """`售前模組` 列 → `(slug, title)`；六個關鍵字集合皆未命中 ⇒ 兜底桶。"""
    haystack = " ".join([question_summary or "", " ".join(categories or [])])
    for slug, title, keywords in SIX_MODULES:
        if any(kw in haystack for kw in keywords):
            return slug, title
    return _MODULE_FALLBACK_SLUG, _MODULE_FALLBACK_TITLE


def _classify_row(categories: Optional[list], question_summary: str) -> tuple[str, str]:
    """任一已審核售前池列 → `(section_slug, section_title)`。

    優先序（固定、⛔ 依資料猜測調整）：`售前模組`（再細分六大模組）→ 四個
    非模組 categories（見 `NON_MODULE_CATEGORY_SECTIONS`）→ 兜底桶（categories
    缺值或不在已知五值內時，一律不遺漏地收進兜底桶，⛔ 不靜默丟列）。
    """
    cats = categories or []
    if _MODULE_CATEGORY in cats:
        return _classify_module_row(question_summary, cats)
    for cat in cats:
        if cat in NON_MODULE_CATEGORY_SECTIONS:
            return NON_MODULE_CATEGORY_SECTIONS[cat]
    return _MODULE_FALLBACK_SLUG, _MODULE_FALLBACK_TITLE


def _extract_boundary_sentences(answer: str) -> list[str]:
    """把 `answer` 內含 `_BOUNDARY_TERMS` 任一詞的句子抽出（原句、去頭尾空白）。"""
    if not answer:
        return []
    sentences = _SENTENCE_SPLIT_RE.split(answer)
    return [
        s.strip()
        for s in sentences
        if s.strip() and any(term in s for term in _BOUNDARY_TERMS)
    ]


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
    # DSP-020：章節標題帶 section id——模型引用大綱時 `Citation.source` 要填它
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
    """R5.1／R5.4：售前池（已審核）→ 六模組主題頁＋邊界句＋DSP-009＋CTA。

    ⛔ 無 LLM——純字串比對＋固定常數。同一批已審核列 ⇒ 同一份 `text`／`sha256`
    （決定性，供 unit 測試「組裝決定性」與快取失效判斷用）。只有
    `outline_approved_by IS NOT NULL` 的列進來（R11.6）；未審核列不影響
    `kb.get` 整數 id 取回（那條路徑走 `tools/kb.py:fetch_visible_row`，
    與本旗標無關，見 migration 檔頭註解）。
    """
    # prospect ＝ b2b ＋ 無 role_id（memory project_presales_target_user_routing；jgb2 面板送 prospect 時
    # mode=b2b；缺口地圖 POOL_PRED 亦為 business_types && ['system_provider']）。⛔ 勿改回 b2c：
    # b2c 分支對**本函式**（母體已鎖 outline_approved_by IS NOT NULL）會用 vendor 1 業態濾掉 23/31 筆純 system_provider 列
    # ⇒ 大綱只剩 8 筆（recheck 突變實測）；對**標記 SQL** 則反向多掃 50 筆通用列（預覽 81≠31）。兩邊都錯，方向不同。
    identity = Identity(vendor_id=1, target_user="prospect", mode="b2b")
    rows = _fetch_prospect_pool_rows(db_pool, identity)

    buckets: dict[str, dict] = {}  # slug -> {"title": str, "source_ids": [int]}
    boundary_sentences: list[tuple[int, str]] = []  # (row_id, sentence)

    for row_id, question_summary, answer, categories, _updated_at in rows:
        slug, title = _classify_row(categories, question_summary)
        bucket = buckets.setdefault(slug, {"title": title, "rows": []})
        bucket["rows"].append((row_id, question_summary, answer))
        for sentence in _extract_boundary_sentences(answer or ""):
            boundary_sentences.append((row_id, sentence))

    sections: list[OutlineSection] = []

    # 六模組（固定順序，即使某模組本輪 0 列也不產出空 section——⛔ 不放空章節
    # 誤導模型以為有內容可引用）。
    for slug, title, _kw in SIX_MODULES:
        bucket = buckets.pop(slug, None)
        if not bucket:
            continue
        body = "\n".join(
            f"- {qs}：{ans}" for _rid, qs, ans in bucket["rows"]
        )
        sections.append(
            OutlineSection(
                id=f"outline:{slug}",
                title=title,
                text=body,
                source_ids=[rid for rid, _qs, _ans in bucket["rows"]],
                citable=True,
            )
        )

    # 非模組類別（固定順序，理由同上）。
    for _cat, (slug, title) in NON_MODULE_CATEGORY_SECTIONS.items():
        bucket = buckets.pop(slug, None)
        if not bucket:
            continue
        body = "\n".join(
            f"- {qs}：{ans}" for _rid, qs, ans in bucket["rows"]
        )
        sections.append(
            OutlineSection(
                id=f"outline:{slug}",
                title=title,
                text=body,
                source_ids=[rid for rid, _qs, _ans in bucket["rows"]],
                citable=True,
            )
        )

    # 兜底桶（若有）。
    misc = buckets.pop(_MODULE_FALLBACK_SLUG, None)
    if misc:
        body = "\n".join(f"- {qs}：{ans}" for _rid, qs, ans in misc["rows"])
        sections.append(
            OutlineSection(
                id=f"outline:{_MODULE_FALLBACK_SLUG}",
                title=_MODULE_FALLBACK_TITLE,
                text=body,
                source_ids=[rid for rid, _qs, _ans in misc["rows"]],
                citable=True,
            )
        )

    # 邊界句段。
    if boundary_sentences:
        sections.append(
            OutlineSection(
                id="outline:boundary",
                title="邊界句",
                text="\n".join(f"- {s}" for _rid, s in boundary_sentences),
                source_ids=sorted({rid for rid, _s in boundary_sentences}),
                citable=True,
            )
        )

    # DSP-009 刻意不補（固定文字，非資料庫來源 ⇒ source_ids=[]）。
    sections.append(
        OutlineSection(
            id="outline:deliberate-gaps",
            title="刻意不補（遇到即轉人）",
            text="\n".join(f"- {item}：一律回覆「{PRESALES_HANDOFF_MESSAGE}」" for item in DSP009_DELIBERATE_GAPS),
            source_ids=[],
            citable=True,
        )
    )

    # CTA 出口。
    sections.append(
        OutlineSection(id="outline:cta", title="下一步出口", text=_CTA_TEXT, source_ids=[], citable=True)
    )

    version = _max_updated_at_iso(rows, updated_at_index=4)
    return _build_doc(audience="prospect", sections=sections, version=version)


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
    "prospect": 10_000,
    "property_manager": 8_000,
    "tenant": 8_000,
}
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

    找不到大綱（cache 未就緒）或找不到該 section id ⇒ `ToolResult(ok=False,
    error="NO_MATCH")`——與 `kb.py` 池外查詢同一錯誤語意，⛔ 對模型區分兩種
    「找不到」（design：不對模型洩漏「不存在」與「無權限」的差異，這裡延伸為
    「不存在」與「大綱還沒建好」同樣不區分）。
    """

    def resolver(identity: Identity, kb_id: str) -> ToolResult:
        audience = identity.resolved_audience()
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
