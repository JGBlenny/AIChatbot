"""正本組裝（spec knowledge-outline-and-intent-architecture・任務 3.2｜design 元件 5）。

`CanonDoc`（git 正本）→ `OutlineDoc`／`outline:toc`／`kb.get("outline:*")` 的解析結果。
**組裝來源＝正本 Markdown，⛔ 不讀 DB**——DB 的售前池是正本的衍生物（匯入產物），
大綱不得反過來以衍生物為來源（R2.6／R5.4；Plan `inputs/plan-3.2-canon-assembler-20260907.md` §1）。

## 啟動契約（`load_canon_or_die`）
1. 內容**只**來自 `<audience>.md` 的解析結果（`canon_parser.parse_canon`）。
2. `<audience>.json` 逐位元組比對 `export_json(doc, <tmp>)` 的重導出結果——
   ⚠️ **⛔ 不是只比 `canon_sha256` 欄**：`canon_sha256` 只涵蓋 `.md` 的位元組，
   `.json` 內容改一位元 sha 仍相等（security-reviewer 2026-09-07 P1-1）。
3. 缺檔／不同源／格式錯／`audience` 非字面 ⇒ `CanonLoadError`（訊息含 resolved path）。
   呼叫端（`app.py::_init_agent_runtime`）在 `_agent_configured()` 為真時升為啟動紅，
   否則 agent 停用（既有語義，⛔ 本檔不新增降級路徑）。

## 可見性（`canon_visible`）
元件 6 `FineIndex.visible_subset` 的**逐細目前身**，規則照 design 元件 6 原文：
分支判準與 `vendor_knowledge_retriever_v2.build_visibility_predicate` 的 `is_b2b_mode`
**同式**（`target_user ∈ {property_manager, system_admin}` **或** `mode == 'b2b'`，
⚠️ ⛔ 不是只看 mode——`Identity(target_user=property_manager, mode=b2c)` 必須走嚴格分支），
角色正規化重用 `VendorKnowledgeRetrieverV2._effective_target_user`（⛔ 不另寫一套）。

**刻意不套的 SQL 條件**（對照 `build_visibility_predicate`，業主 2026-09-07 §8.1 核）：
- 業者軸（謂詞條件 1）：正本細目無 vendor 欄，匯入寫 NULL ⇒ 該條件恆真。
- 上架旗標（謂詞條件 2）：正本無此旗標，「未審＝不可引用」由 `reviewed_by` 承擔。
- 保留分類（謂詞條件 3）：正本無「系統脈絡／對話規則」類細目。
- **不新增** SQL 沒有的 `doc.audience == 身分受眾` 逐細目比對：受眾隔離靠「載入哪一份正本」。

上面四項的字面 ⛔ 不得出現在 `canon_visible` 內（不變量 29b：出現＝有人手抄 SQL 條件）。

## 與 `outline.py` 的循環相依
`canon_assembler` 需要 `outline._build_doc`／`OutlineSection`，`outline` 需要本檔的
`get_canon`／`resolve_canon_section` ⇒ 兩邊都以**函式內 import** 解，⛔ 不在模組層互指。
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, get_args

from services.agent.canon.canon_parser import (
    CanonDoc,
    CanonFormatError,
    FineItem,
    export_json,
    parse_canon,
)
from services.agent.identity import Audience, Identity
from services.agent.tools.registry import Provenance, ToolResult
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

logger = logging.getLogger(__name__)

#: `resolve_canon_dir()` 的覆寫 env；⚠️ **只在 `DB_ENV=test` 生效**（測試用 tmp 複本）。
CANON_DIR_ENV = "AGENT_CANON_DIR"
#: 覆寫的守門 env（`tests/conftest.py` 與 dev compose 設 `test`；prod 不設）。
DB_ENV_KEY = "DB_ENV"
DB_ENV_TEST_VALUE = "test"

#: `Audience` Literal 的字面集合——`load_canon_or_die` 只接受這三個（P3-1）。
CANON_AUDIENCES: frozenset = frozenset(get_args(Audience))

#: b2b 分支的嚴格業態（與 `build_visibility_predicate` 條件 6a 同值）。
B2B_BUSINESS_TYPE = "system_provider"
#: b2b 分支判準的角色集合（與 SQL `is_b2b_mode` 同值）。
B2B_TARGET_USERS: frozenset = frozenset({"property_manager", "system_admin"})
#: b2c 分支的通用角色標記（與 SQL 條件 4 的 `'all_users'` 同值）。
ALL_USERS_TOKEN = "all_users"

#: `kb.get` 的大綱前綴（`tools/kb.py:kb_get` 以此路由到 `outline_resolver`）。
OUTLINE_ID_PREFIX = "outline:"
#: 目錄節 id（design 元件 6「第二次機會」）。
TOC_SECTION_ID = "outline:toc"
TOC_SECTION_TITLE = "正本目錄"
#: 目錄行分隔符（全形直線，design 元件 5 `"<fine.id>｜<title>"`）。
TOC_LINE_SEP = "｜"


class CanonLoadError(RuntimeError):
    """正本載入失敗：缺檔／`.md` 與 `.json` 不同源／格式錯／受眾非字面。

    ⛔ 不是 fail-soft 訊號——呼叫端只在 agent 開關全關時才吞它（既有語義）。
    """


# ---------------------------------------------------------------------------
# 正本目錄解析與載入
# ---------------------------------------------------------------------------


def _default_canon_dir() -> Path:
    """`<rag root>/canon`——本檔在 `<rag root>/services/agent/canon/` 底下。"""
    return Path(__file__).resolve().parents[3] / "canon"


def resolve_canon_dir() -> Path:
    """正本目錄的 resolved 絕對路徑。

    預設 `<rag root>/canon`（Dockerfile `COPY . .` ⇒ 映像內 `/app/canon`）。
    `AGENT_CANON_DIR` **只在 `DB_ENV=test` 生效**（P3-1）——其餘環境忽略並 log
    warning，⛔ 不讓線上環境被一個 env var 換掉知識正本。
    """
    default = _default_canon_dir().resolve()
    override = os.environ.get(CANON_DIR_ENV, "").strip()
    if not override:
        return default
    if os.environ.get(DB_ENV_KEY, "").strip() == DB_ENV_TEST_VALUE:
        return Path(override).resolve()
    logger.warning(
        "%s=%r 已忽略：覆寫只在 %s=%s 生效，改用預設正本目錄 %s",
        CANON_DIR_ENV, override, DB_ENV_KEY, DB_ENV_TEST_VALUE, default,
    )
    return default


def _exported_json_bytes(doc: CanonDoc, audience: str) -> bytes:
    """`export_json` 的重導出位元組（寫到暫存檔再讀回——它是寫檔 API，⛔ 無記憶體版）。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, f"{audience}.json")
        export_json(doc, out_path)
        with open(out_path, "rb") as fh:
            return fh.read()


def load_canon_or_die(canon_dir, audience: str) -> CanonDoc:
    """讀 `<canon_dir>/<audience>.md`＋`.json`，同源才回 `CanonDoc`；否則 `CanonLoadError`。

    ⚠️ **內容只來自 `.md`**——`.json` 只當同源憑證比對，⛔ 不從它取任何欄位。
    ⚠️ 比對方式是**逐位元組**（見模組 docstring 第 2 點），⛔ 不是只比 `canon_sha256`。
    """
    if audience not in CANON_AUDIENCES:
        raise CanonLoadError(
            f"audience={audience!r} 不是 Audience 字面（合法值 {sorted(CANON_AUDIENCES)}）"
        )
    base = Path(canon_dir).resolve()
    md_path = base / f"{audience}.md"
    json_path = base / f"{audience}.json"

    if not md_path.is_file():
        raise CanonLoadError(f"正本 Markdown 缺檔：{md_path}")
    if not json_path.is_file():
        raise CanonLoadError(f"正本導出 JSON 缺檔：{json_path}")

    try:
        doc = parse_canon(str(md_path))
    except CanonFormatError as exc:
        raise CanonLoadError(f"正本格式錯誤（{md_path}）：{exc}") from exc
    except OSError as exc:  # 讀檔失敗（權限／編碼）也是啟動紅，⛔ 不吞
        raise CanonLoadError(f"正本讀取失敗（{md_path}）：{exc}") from exc

    if doc.audience != audience:
        raise CanonLoadError(
            f"正本 front matter audience={doc.audience!r} 與檔名受眾 {audience!r} 不符（{md_path}）"
        )

    with open(json_path, "rb") as fh:
        versioned = fh.read()
    exported = _exported_json_bytes(doc, audience)
    if versioned != exported:
        raise CanonLoadError(
            f"正本 JSON 與 Markdown 不同源（逐位元組比對失敗）：{json_path}"
            f"（版控 {len(versioned)} bytes vs 重導出 {len(exported)} bytes）"
        )
    return doc


# ---------------------------------------------------------------------------
# 模組層正本註冊表（`OutlineDoc` 是 pydantic BaseModel，⛔ 不掛未宣告屬性）
# ---------------------------------------------------------------------------

_CANON_REGISTRY: dict = {}


def register_canon(audience: str, doc: CanonDoc) -> None:
    """把某受眾**這個行程實際載入的那份**正本登記起來（`build_prospect_outline` 呼叫）。"""
    if audience not in CANON_AUDIENCES:
        raise CanonLoadError(
            f"audience={audience!r} 不是 Audience 字面（合法值 {sorted(CANON_AUDIENCES)}）"
        )
    _CANON_REGISTRY[audience] = doc


def get_canon(audience: str) -> Optional[CanonDoc]:
    """該受眾已註冊的正本；未註冊（pm／tenant 走 DB TOC）⇒ `None`。"""
    return _CANON_REGISTRY.get(audience)


def reset_canon_registry() -> None:
    """清空註冊表（測試隔離用；⛔ 產線不呼叫）。"""
    _CANON_REGISTRY.clear()


def canon_registry_shas() -> dict:
    """`{audience: canon_sha256}`——health 用的觀測值，⛔ 不重算、不重讀檔。"""
    return {aud: doc.canon_sha256 for aud, doc in sorted(_CANON_REGISTRY.items())}


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------


def build_outline(doc: CanonDoc):
    """`CanonDoc` → `OutlineDoc`：每細目一節（`id=fine.id`、`title=fine.title`）。

    - `citable = (fine.reviewed_by is not None)`；未審細目**只出標題**（`text=""`），
      模型看得到「有這個題目但目前無可引用內容」，⛔ 不把未審內容送進 system prompt。
    - `source_ids=[]`：正本細目的來源是 `fine.sources`（`kb:*`／`docs:*` 字串），
      ⛔ 不硬塞成 `OutlineSection.source_ids`（那是 int 的 DB 列 id 欄位）。
    - `version=doc.version`；sha 由 `_build_doc` 涵蓋 `version`＋`text`（既有規則）。
    - 標題行的 `【<id>】` 前綴由 `_build_doc` 自動加（DSP-020），⛔ 此處不重複加。
    """
    from services.agent.outline import OutlineSection, _build_doc  # 循環相依，見模組 docstring

    sections = [
        OutlineSection(
            id=fine.id,
            title=fine.title,
            text=("\n".join(fine.content_units) if fine.reviewed_by is not None else ""),
            source_ids=[],
            citable=fine.reviewed_by is not None,
        )
        for fine in doc.fines()
    ]
    return _build_doc(audience=doc.audience, sections=sections, version=doc.version)


def canon_visible(identity: Identity, fine: FineItem, *, vendor_business_types: frozenset) -> bool:
    """這個身分看不看得到這個細目（元件 6 `visible_subset` 的逐細目前身）。

    規則見模組 docstring：未審一律否；分支判準與 SQL `is_b2b_mode` 同式；
    角色正規化重用 `_effective_target_user`（未知／`None` ⇒ tenant，fail-safe）。
    """
    if fine.reviewed_by is None:
        return False

    effective_target_user = VendorKnowledgeRetrieverV2._effective_target_user(
        identity.target_user
    )
    is_b2b = (identity.target_user in B2B_TARGET_USERS) or (identity.mode == "b2b")

    fine_target_user = set(fine.target_user)
    fine_business_types = set(fine.business_types)

    if is_b2b:
        if not (fine_business_types & {B2B_BUSINESS_TYPE}):
            return False
        return (not fine_target_user) or (effective_target_user in fine_target_user)

    if fine_business_types and not (fine_business_types & set(vendor_business_types)):
        return False
    return (
        (not fine_target_user)
        or (effective_target_user in fine_target_user)
        or (ALL_USERS_TOKEN in fine_target_user)
    )


def build_canon_toc(doc: CanonDoc, identity: Identity, *, vendor_business_types: frozenset):
    """`outline:toc` 節：每個**可見且已審**細目一行 `<fine.id>｜<title>`，`citable=False`。

    ⛔ 另名，不與 pm／tenant 現役的 `outline.build_toc(db_pool, audience, vendor_id)` 同名
    （後者有 vendor 過濾，design 元件 5 明訂不得拿掉）。目錄只導航、不當事實依據。
    """
    from services.agent.outline import OutlineSection  # 循環相依，見模組 docstring

    lines = [
        f"{fine.id}{TOC_LINE_SEP}{fine.title}"
        for fine in doc.fines()
        if canon_visible(identity, fine, vendor_business_types=vendor_business_types)
    ]
    return OutlineSection(
        id=TOC_SECTION_ID,
        title=TOC_SECTION_TITLE,
        text="\n".join(lines),
        source_ids=[],
        citable=False,
    )


def _no_match() -> ToolResult:
    """不可見／未審／不存在一律同一個錯誤——⛔ 不對模型區分（design：不洩漏差異）。"""
    return ToolResult(ok=False, error="NO_MATCH")


def resolve_canon_section(
    doc: CanonDoc, identity: Identity, section_id: str, *, vendor_business_types: frozenset
) -> ToolResult:
    """`kb.get("outline:*")` 的正本解析：**每回合**套 `canon_visible`（F7 修補點）。

    - `outline:toc` ⇒ 該身分的目錄（`citable=False`）。
    - `outline:<fine.id>` ⇒ 可見且已審才回內容（`citable=True`）；否則 `NO_MATCH`。
    - 其餘形狀（含裸 fine id）⇒ `NO_MATCH`。
    """
    if section_id == TOC_SECTION_ID:
        toc = build_canon_toc(doc, identity, vendor_business_types=vendor_business_types)
        return ToolResult(
            ok=True,
            data={"id": toc.id, "question_summary": toc.title, "answer": toc.text},
            provenance=[Provenance(source=toc.id, text=toc.text, citable=toc.citable)],
            text_for_model=toc.text,
        )

    if not section_id.startswith(OUTLINE_ID_PREFIX):
        return _no_match()
    fine_id = section_id[len(OUTLINE_ID_PREFIX):]

    for fine in doc.fines():
        if fine.id != fine_id:
            continue
        if not canon_visible(identity, fine, vendor_business_types=vendor_business_types):
            return _no_match()
        text = "\n".join(fine.content_units)
        return ToolResult(
            ok=True,
            data={"id": section_id, "question_summary": fine.title, "answer": text},
            provenance=[Provenance(source=section_id, text=text, citable=True)],
            text_for_model=text,
        )
    return _no_match()
