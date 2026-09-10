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
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from services.agent.identity import Audience, Identity
from services.agent.tools.registry import Provenance, ToolResult
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# vendor_business_types 單一來源解析（design 元件 6；tasks 6.2 前置 P3-b）
# ---------------------------------------------------------------------------

_default_vendor_resolver = None  # 模組級延遲單例，同 routers/chat.py 的 get_vendor_param_resolver 慣例


def _get_default_vendor_resolver():
    global _default_vendor_resolver
    if _default_vendor_resolver is None:
        from services.vendor_parameter_resolver import VendorParameterResolver

        _default_vendor_resolver = VendorParameterResolver()
    return _default_vendor_resolver


def resolve_vendor_business_types(identity: Identity, resolver=None) -> frozenset:
    """`vendor_business_types` 單一來源（design 元件 6）——每回合最多呼叫一次，

    結果交呼叫端傳給 `build_canon_toc`／`candidate_outline`（`visible_subset`）／
    `selector.select`／`resolve_canon_section` 三＋二個呼叫點，⛔ 不在
    `FineIndex`／`canon_visible` 內部查 DB。

    - `identity.vendor_id` 為 `None`／`0`，或受眾為 `prospect`（prospect 走 b2b
      分支，`canon_visible` 不看這個集合——見 `canon_assembler.canon_visible`）
      ⇒ 回 `frozenset()`，且**不呼叫 resolver**（維持與 3.2 現況逐位元相同的
      空集合輸入）。
    - 否則以 `VendorParameterResolver.get_vendor_info(vendor_id)` 取
      `business_types` 正規化成 `frozenset[str]`。
    - resolver 例外、查無業者、或 `business_types` 缺漏 ⇒ **fail-closed**回
      `frozenset()`（業態限定細目不可見）——⛔ 不 raise、⛔ 不放行。
    """
    vendor_id = identity.vendor_id
    if not vendor_id or identity.resolved_audience() == "prospect":
        return frozenset()

    active_resolver = resolver if resolver is not None else _get_default_vendor_resolver()
    try:
        info = active_resolver.get_vendor_info(vendor_id)
    except Exception:  # noqa: BLE001 — fail-closed，⛔ 不外溢
        logger.warning("resolve_vendor_business_types_failed vendor_id=%s", vendor_id, exc_info=True)
        return frozenset()

    if not info:
        return frozenset()

    raw_types = info.get("business_types") if isinstance(info, dict) else None
    if not raw_types:
        return frozenset()
    try:
        # ⚠️ `business_types` 是 DB 來的值：非可迭代純量（例如整數）或含不可轉字串的
        # 元素會在這裡炸，而本函式的契約是 **fail-closed 回空集合、⛔ 不外溢**
        # （verifier P4）——⛔ 不要拿掉這層 try，讓一筆髒資料把整個回合掀掉。
        # str 本身可迭代，但逐字元切開不是業態 ⇒ 同樣視為髒資料。
        if isinstance(raw_types, (str, bytes)):
            raise TypeError("business_types 是純量字串，不是列表")
        return frozenset(str(t) for t in raw_types)
    except Exception:  # noqa: BLE001 — fail-closed，⛔ 不外溢
        logger.warning(
            "resolve_vendor_business_types_bad_shape vendor_id=%s type=%s",
            vendor_id, type(raw_types).__name__,
        )
        return frozenset()


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


class CandidateOutlineDoc(BaseModel):
    """一回合的候選子集大綱（任務 4.1｜Plan §2.1-1）。

    與 `OutlineDoc` 同型別家族、滿足同一個 `OutlineDocLike` Protocol——`PromptAssembler`
    只看結構型別，不在乎具體類別。兩個建構子（`from_selection`／`from_visible`）都
    **複製 `full` 的 `audience`／`version`／`sha256`**（⛔ 不重算、不填
    `identity.resolved_audience()`——否則 `test_outline_audience_mismatch_fails_closed`
    會恆真），只有 `sections`／`text`／`token_count`／`token_count_approx` 是這一回合
    當場重算的。

    ⛔ 兩者都不含 `full` 自帶的 `outline:toc` 以外的非細目節——`sections` 一律是
    候選／可見細目（來自 `full.sections`）＋呼叫端當回合算好的 `toc` 一節，
    `full` 若自帶啟動期靜態 toc 不會被沿用（它從來不在候選／可見集合裡）。
    """

    audience: Audience
    version: str
    sha256: str
    token_count: int
    sections: list[OutlineSection]
    text: str
    token_count_approx: bool = False

    @classmethod
    def from_selection(cls, full: "OutlineDoc", sel, toc: OutlineSection) -> "CandidateOutlineDoc":
        """`sel["candidate_ids"]` 順序從 `full.sections` 取；找不到的 id ⇒ `ValueError`
        （⛔ 不靜默跳過——那會讓「候選 id 對不到大綱」的資料錯誤悄悄變成少一節）。
        """
        by_id = {section.id: section for section in full.sections}
        picked: list[OutlineSection] = []
        for fine_id in sel["candidate_ids"]:
            section = by_id.get(fine_id)
            if section is None:
                raise ValueError(
                    f"候選 id {fine_id!r} 不在 full.sections 內（sha256={full.sha256[:12]}）"
                )
            picked.append(section)
        return cls._from_sections(full, picked, toc)

    @classmethod
    def from_visible(
        cls, full: "OutlineDoc", visible_ids: "frozenset[str]", toc: OutlineSection
    ) -> "CandidateOutlineDoc":
        """降級用：`full.sections` 中 id ∈ `visible_ids` 者（正本序）＋`toc`。

        這是 3.2 verifier P3 債的修補點：降級也只給可見細目，⛔ 不是未過濾整份。
        """
        picked = [section for section in full.sections if section.id in visible_ids]
        return cls._from_sections(full, picked, toc)

    @classmethod
    def _from_sections(
        cls, full: "OutlineDoc", picked: list[OutlineSection], toc: OutlineSection
    ) -> "CandidateOutlineDoc":
        # 重用 `_build_doc` 的組裝式（【id】title\ntext 接法）與 token 估算器，
        # ⛔ 不在此重寫第二份公式；sha256 隨後被 full 的值覆蓋（⛔ 不採 `_build_doc`
        # 自己算的那個——那個涵蓋的是候選子集的 text，語意是「這份子集的雜湊」，
        # 我們要的是「這份子集出自哪一份完整正本」）。
        assembled = _build_doc(
            audience=full.audience, sections=list(picked) + [toc], version=full.version
        )
        return cls(
            audience=full.audience,
            version=full.version,
            sha256=full.sha256,
            token_count=assembled.token_count,
            sections=assembled.sections,
            text=assembled.text,
            token_count_approx=assembled.token_count_approx,
        )


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

    ⛔ **不照抄舊鏈「系統脈絡」查詢的取法**（design 元件 5 明文禁止；原實作在
    `services/system_context.py:_fetch_base`／`_fetch_appends`，⛔ 該實作已隨
    舊鏈於 2026-09-10 退役）——那兩支只切 `category`／`target_user`，完全
    沒有 `vendor_ids` 過濾（舊鏈把「系統脈絡」當「跨業者共用底座」，這是它的
    既有假設；agentic 大綱要對到 MCP 門面解析出的單一 `vendor_id`，不能照搬）。
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


#: 啟動期組 `outline:toc` 用的**靜態身分**（受眾 → `Identity` 欄位）。
#: ⛔ 只列有 git 正本的受眾：tenant 沒有正本，且 b2c 靜態身分在啟動時解析不出
#: 業態（`vendor_id=0` 只是佔位）⇒ 缺鍵＝不可組裝，`build_audience_outline` 直接 raise。
#: prospect 那一列的三個值 ⛔ 不得更動——它是 3.2 起 `build_prospect_outline` 逐位元
#: 相同輸出的一部分（售前＝b2b ＋ 無 role_id；勿改回 b2c，見下方 `build_audience_outline`）。
_STATIC_TOC_IDENTITY: dict[str, dict] = {
    "prospect": {"vendor_id": 0, "target_user": "prospect", "mode": "b2b"},
    # DSP-037（業主 2026-09-07）：pm 正本上線。pm 走 b2b 分支（正本 front matter
    # `business_types: [system_provider]`／`target_user: [property_manager]`），
    # 故 `mode="b2b"`＋`target_user="property_manager"` ⇒ `canon_visible` 兩條件都成立。
    "property_manager": {
        "vendor_id": 0, "target_user": "property_manager", "mode": "b2b",
    },
}


async def build_audience_outline(audience: Audience, db_pool=None) -> OutlineDoc:
    """R2.6／R5.4：git 正本（`canon/<audience>.md`）→ 逐細目章節 ＋ `outline:toc`。

    ⚠️ **`db_pool` 保留於簽名但不再使用**（`app.py` 不改；3.2 起大綱不讀 DB）。
    步驟（design 元件 5「呼叫鏈與失敗語義」）：

    1. `load_canon_or_die(resolve_canon_dir(), audience)`——`.md` 解析＋`.json`
       逐位元組同源比對；缺檔／不同源／格式錯 ⇒ raise（呼叫端決定升成啟動紅或跳過）。
    2. `register_canon(audience, doc)`——`make_outline_resolver` 每回合要用同一份
       `CanonDoc` 套可見性（`OutlineDoc` 是 pydantic，⛔ 不掛在它身上）。
    3. `build_outline(doc)` ＋ 附 `outline:toc` 節（**啟動時**以該受眾的**靜態身分**
       算一次，見 `_STATIC_TOC_IDENTITY`。⚠️ 每回合的候選子集與動態 toc 是 4.1
       `CandidateOutlineDoc`，⛔ 不在本片）。
    4. `check_budget(min(env 上限, 正本 budget_tokens))`——正本自帶的預算是上限之一，
       ⛔ 不讓 env 單方面把上限開大（security-reviewer P2-3）。

    ⚠️ **本函式是 `build_prospect_outline` 的泛化**（DSP-037／S1b）：prospect 的
    輸出必須逐位元不變（`test_build_prospect_outline_registers_same_doc_and_leaves_sha_unchanged`
    是那條線的釘子），故步驟、順序、靜態身分、`_build_doc` 參數一字未動。
    """
    from services.agent.canon.canon_assembler import (  # 循環相依 ⇒ 函式內 import
        build_canon_toc, build_outline, load_canon_or_die, register_canon, resolve_canon_dir,
    )

    identity_fields = _STATIC_TOC_IDENTITY.get(audience)
    if identity_fields is None:
        raise ValueError(
            f"audience={audience!r} 沒有 git 正本靜態身分"
            f"（合法值 {sorted(_STATIC_TOC_IDENTITY)}；tenant 走 build_toc 的 DB 目錄）"
        )

    canon = load_canon_or_die(resolve_canon_dir(), audience)
    register_canon(audience, canon)

    doc = build_outline(canon)
    # 靜態身分見 `_STATIC_TOC_IDENTITY`：兩個受眾都是 b2b ＋ 無 role_id
    # （售前 memory project_presales_target_user_routing；jgb2 面板送 prospect 時 mode=b2b）。
    # ⛔ 勿改回 b2c——那會走 vendor 業態分支，而啟動時沒有真實 vendor 可解析
    # （`vendor_id=0` 只是佔位，`resolve_vendor_business_types` 對它回空集合且不查 DB）。
    static_identity = Identity(**identity_fields)
    toc = build_canon_toc(
        canon,
        static_identity,
        vendor_business_types=resolve_vendor_business_types(static_identity),
    )
    doc = _build_doc(
        audience=canon.audience,
        sections=list(doc.sections) + [toc],
        version=canon.version,
    )
    check_budget(doc, min(default_token_limit(audience), canon.budget_tokens))
    return doc


async def build_prospect_outline(db_pool) -> OutlineDoc:
    """`build_audience_outline("prospect", …)` 的**薄別名**（DSP-037／S1b 前的唯一入口）。

    ⛔ 不在此重寫第二份組裝式——輸出必須與泛化前逐位元相同。既有呼叫端
    （`scripts/`、測試、`app.py` 舊路徑）保留這個名字。
    """
    return await build_audience_outline("prospect", db_pool)


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
            # `vendor_business_types` 每回合最多解析一次（元件 6，tasks 6.2 前置
            # P3-b）：prospect／vendor_id 缺 ⇒ `resolve_vendor_business_types`
            # 回空集合且不呼叫 resolver；b2c 受眾解析真實業態。
            return resolve_canon_section(
                canon,
                identity,
                kb_id,
                vendor_business_types=resolve_vendor_business_types(identity),
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
