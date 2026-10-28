"""正本組裝（spec knowledge-outline-and-intent-architecture・任務 3.2｜design 元件 5）。

`CanonDoc`（git 正本）→ `OutlineDoc`／`outline:toc`／`kb.get("outline:*")` 的解析結果。
**組裝來源＝正本 Markdown，⛔ 不讀 DB**——DB 的售前池是正本的衍生物（匯入產物），
大綱不得反過來以衍生物為來源（R2.6／R5.4）。

## 圖書館形態（DSP-058）
正本只有**一份**（`canon/jgb/` 九架），受眾隔離改由**受眾視圖**承擔：
`build_outline(doc, audience, identity, …)` 依細目的 `target_user`／`business_types`
兩軸切出該受眾看得到的那一份。⛔ 沒有「載入哪一份正本」這個隔離機制了——
⛔ 不得以「受眾隔離靠載入哪一份正本」為由放寬視圖過濾。

## 啟動契約（`load_canon_or_die`）
1. 內容**只**來自 `canon/jgb/[A-I].md` 的解析結果（`canon_parser.parse_canon_dir`）。
2. `canon/jgb.json` 逐位元組比對 `export_json(doc, <tmp>)` 的重導出結果——
   ⚠️ **⛔ 不是只比 `canon_sha256` 欄**：`canon_sha256` 只涵蓋九架 `.md` 的位元組，
   `.json` 內容改一位元 sha 仍相等。
3. `canon/jgb/CATALOG.md` 同樣逐位元組比對 `export_catalog` 的重導出結果——
   目錄是衍生物，手改它＝正本與衍生物分裂，⛔ 不放行。
4. 缺檔／缺架／不同源／格式錯 ⇒ `CanonLoadError`（訊息含 resolved path）。
   呼叫端（`app.py::_init_agent_runtime`）在 `_agent_configured()` 為真時升為啟動紅，
   否則 agent 停用（既有語義，⛔ 本檔不新增降級路徑）。

## 可見性（`_axes_visible` ／ `canon_visible`）
兩層，⛔ 不得合併：
- `_axes_visible(effective_target_user, mode, fine, vendor_business_types)`＝**受眾＋業態**
  兩軸（⛔ 不看 `reviewed_by`）——它決定「這個細目屬不屬於這個受眾的視圖」。
- `canon_visible(identity, fine, …)`＝`reviewed_by is not None` **且** `_axes_visible`——
  它決定「內容可不可以被引用」。與 SQL 謂詞的逐格對照由
  `test_visible_subset_sql_equiv_req.py` 釘：pm／prospect／tenant 三格逐格相等，
  `system_admin` 一格是**刻意的不對稱**（見下方 DSP-053a）。

`build_outline` 只納 `_axes_visible` 為真的細目：未審者**只出標題**（`text=""`、
`citable=False`），⛔ 不出現在別的受眾視圖裡（連標題都不給）。

`canon_visible` 是元件 6 `FineIndex.visible_subset` 的**逐細目前身**，規則照 design 元件 6 原文：
分支判準與 `vendor_knowledge_retriever_v2.build_visibility_predicate` 的 `is_b2b_mode`
**同式**（`target_user ∈ {property_manager, system_admin}` **或** `mode == 'b2b'`，
⚠️ ⛔ 不是只看 mode——`Identity(target_user=property_manager, mode=b2c)` 必須走嚴格分支），
角色正規化重用 `VendorKnowledgeRetrieverV2._effective_target_user`（⛔ 不另寫一套）。

**b2b 分支「`target_user` 空＝不可見」**（DSP-052 補救 (c)；
與 SQL 謂詞同式，兩側同步）：b2b 分支的 `target_user` 是**必填鑰匙**，⛔ 沒有
「空＝不設限」的放行。理由：`tenant` 是合法值、`audience_of` 靠 `or mode == "b2b"`
把它路由到業者受眾，放行空細目即跨受眾可見且靜默。**b2c 分支⛔不動**（空放行
＋`all_users`），這條不對稱本身就是隔離機制。

**`system_admin` 的正本可見性＝`property_manager`**（DSP-053a）：
`_axes_visible` 的 b2b 分支拿 `CANON_TARGET_USER_FOLD` 把鑰匙折成 `property_manager`。
⚠️ 這是**兩側刻意的一處不對稱**：`kb.search` 的 `build_visibility_predicate` ⛔ 不折，
SQL 側 `kb.target_user && ARRAY['system_admin']` 對 `system_admin` 回 0 列。
⛔ 不得以「收斂兩側」為由把折疊補進 SQL 謂詞，也 ⛔ 不得拿它當理由放寬 b2b 業態或角色條件。

**刻意不套的 SQL 條件**（對照 `build_visibility_predicate`）：
- 業者軸（謂詞條件 1）：正本細目無 vendor 欄，匯入寫 NULL ⇒ 該條件恆真。
- 上架旗標（謂詞條件 2）：正本無此旗標，「未審＝不可引用」由 `reviewed_by` 承擔。
- 保留分類（謂詞條件 3）：正本無「系統脈絡／對話規則」類細目。
- **不新增** SQL 沒有的 `doc.audience == 身分受眾` 逐細目比對：正本只有一份
  （`doc.audience == "jgb"`），受眾隔離由 `_axes_visible` 的 `target_user` 軸承擔，
  ⛔ 不是拿 `doc.audience` 比身分（那一欄在圖書館形態下對每個身分都不相等）。

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
    CANON_NAME,
    FINE_ID_RE,
    CanonDoc,
    CanonFormatError,
    FineItem,
    export_catalog,
    export_json,
    parse_canon_dir,
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

#: `Audience` Literal 的字面集合（`build_outline` 的 `audience` 參數值域由
#: `OutlineDoc.audience` 的 pydantic 驗證強制；本常數保留給呼叫端與
#: `fine_index.INDEX_AUDIENCES` 對照。⚠️ ⛔ 不是正本名——正本名只有 `CANON_NAME`＝`jgb`）。
CANON_AUDIENCES: frozenset = frozenset(get_args(Audience))

#: 衍生目錄檔名（`canon/jgb/CATALOG.md`）——啟動時逐位元組核對，⛔ 不手改。
CATALOG_FILENAME = "CATALOG.md"

#: b2b 分支的嚴格業態（與 `build_visibility_predicate` 條件 6a 同值）。
B2B_BUSINESS_TYPE = "system_provider"
#: b2b 分支判準的角色集合（與 SQL `is_b2b_mode` 同值）。
B2B_TARGET_USERS: frozenset = frozenset({"property_manager", "system_admin"})
#: 正本可見性上，`system_admin` 的鑰匙＝`property_manager`（DSP-053a）。
#: ⛔ 只作用於 `_axes_visible` 的比對鑰匙，⛔ 不改 `B2B_TARGET_USERS`／`is_b2b`／`audience_of`／SQL 謂詞。
CANON_TARGET_USER_FOLD: dict = {"system_admin": "property_manager"}
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
    """正本載入失敗：缺架／缺衍生物／`.md` 與 `.json`／`CATALOG.md` 不同源／格式錯。

    ⛔ 不是 fail-soft 訊號——呼叫端只在 agent 開關全關時才吞它（既有語義）。
    """


class CanonSectionInvisibleError(ValueError):
    """`build_canon_sections` 收到一個 `canon_visible` 為假的 id（9.8 DSP-059 D′ F1）。

    ⚠️ 這不是「靜默跳過」的訊號——`_select_outline`（`runtime.py`）接住它後
    整回合降級為 toc-only（`candidate_fallback_toc_only`），並額外記
    `candidate_invisible_id` 違規；⛔ 本函式自己 ⛔ 不吞、⛔ 不回退。
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


def _exported_json_bytes(doc: CanonDoc) -> bytes:
    """`export_json` 的重導出位元組（寫到暫存檔再讀回——它是寫檔 API，⛔ 無記憶體版）。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, f"{CANON_NAME}.json")
        export_json(doc, out_path)
        with open(out_path, "rb") as fh:
            return fh.read()


def _exported_catalog_bytes(doc: CanonDoc) -> bytes:
    """`export_catalog` 的重導出位元組（同上，寫暫存再讀回 ⇒ 比的是落地位元組）。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, CATALOG_FILENAME)
        export_catalog(doc, out_path)
        with open(out_path, "rb") as fh:
            return fh.read()


def load_canon_or_die(canon_dir) -> CanonDoc:
    """讀 `<canon_dir>/jgb/`（九架）＋`jgb.json`＋`jgb/CATALOG.md`，三者同源才回 `CanonDoc`。

    ⚠️ **內容只來自九架 `.md`**——`.json`／`CATALOG.md` 只當同源憑證比對，
    ⛔ 不從它們取任何欄位。
    ⚠️ 比對方式是**逐位元組**（見模組 docstring 第 2／3 點），⛔ 不是只比 `canon_sha256`。
    ⚠️ **無 `audience` 參數**（DSP-058）：正本只有一份，受眾在 `build_outline` 才分。
    """
    base = Path(canon_dir).resolve()
    shelf_dir = base / CANON_NAME
    json_path = base / f"{CANON_NAME}.json"
    catalog_path = shelf_dir / CATALOG_FILENAME

    if not shelf_dir.is_dir():
        raise CanonLoadError(f"正本目錄缺席或不是目錄：{shelf_dir}")
    if not json_path.is_file():
        raise CanonLoadError(f"正本導出 JSON 缺檔：{json_path}")
    if not catalog_path.is_file():
        raise CanonLoadError(f"正本衍生目錄缺檔：{catalog_path}")

    try:
        doc = parse_canon_dir(str(shelf_dir))
    except CanonFormatError as exc:
        raise CanonLoadError(f"正本格式錯誤（{shelf_dir}）：{exc}") from exc
    except OSError as exc:  # 讀檔失敗（權限／編碼）也是啟動紅，⛔ 不吞
        raise CanonLoadError(f"正本讀取失敗（{shelf_dir}）：{exc}") from exc

    with open(json_path, "rb") as fh:
        versioned = fh.read()
    exported = _exported_json_bytes(doc)
    if versioned != exported:
        raise CanonLoadError(
            f"正本 JSON 與 Markdown 不同源（逐位元組比對失敗）：{json_path}"
            f"（版控 {len(versioned)} bytes vs 重導出 {len(exported)} bytes）"
        )

    with open(catalog_path, "rb") as fh:
        versioned_catalog = fh.read()
    exported_catalog = _exported_catalog_bytes(doc)
    if versioned_catalog != exported_catalog:
        raise CanonLoadError(
            f"正本 CATALOG.md 與九架不同源（逐位元組比對失敗）：{catalog_path}"
            f"（版控 {len(versioned_catalog)} bytes vs 重導出 {len(exported_catalog)} bytes）"
        )
    return doc


# ---------------------------------------------------------------------------
# 模組層正本註冊表（`OutlineDoc` 是 pydantic BaseModel，⛔ 不掛未宣告屬性）
# ---------------------------------------------------------------------------

#: 單槽註冊表（DSP-058：正本只有一份）——鍵恆為 `CANON_NAME`，⛔ 不再逐受眾一份。
_CANON_REGISTRY: dict = {}


def register_canon(doc: CanonDoc) -> None:
    """把**這個行程實際載入的那份**正本登記起來（`build_audience_outline` 第一次載入時呼叫）。

    ⚠️ 兩個受眾視圖共用同一份 `CanonDoc`（⛔ 不各存一份——那會出現兩份可能不同步的正本）。
    """
    _CANON_REGISTRY[CANON_NAME] = doc


def get_canon() -> Optional[CanonDoc]:
    """已註冊的那份正本；尚未註冊 ⇒ `None`（⛔ 不即時載入——載入時機屬啟動接線）。"""
    return _CANON_REGISTRY.get(CANON_NAME)


def reset_canon_registry() -> None:
    """清空註冊表（測試隔離用；⛔ 產線不呼叫）。"""
    _CANON_REGISTRY.clear()


def canon_registry_shas() -> dict:
    """`{"jgb": canon_sha256}`——health 用的觀測值，⛔ 不重算、不重讀檔。

    ⚠️ 鍵是**正本名**不是受眾（DSP-058）：⛔ 不得拿它當「哪些受眾已就緒」的指標。
    """
    return {name: doc.canon_sha256 for name, doc in sorted(_CANON_REGISTRY.items())}


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------


def build_outline(doc: CanonDoc, audience: str, identity: Identity, *, vendor_business_types: frozenset):
    """`CanonDoc` → 某受眾的**視圖** `OutlineDoc`：每個屬於這個受眾的細目一節。

    - 納入判準＝`_axes_visible`（受眾＋業態兩軸，⛔ 不看 `reviewed_by`）：
      不屬於這個受眾的細目**連標題都不出現**（DSP-058 的受眾隔離就在這一行）。
    - `citable = canon_visible(...)`（＝已審且兩軸可見）；未審細目**只出標題**（`text=""`），
      模型看得到「有這個題目但目前無可引用內容」，⛔ 不把未審內容送進 system prompt。
    - `audience` 是**視圖受眾**（`prospect`／`property_manager`），⛔ 不得填 `doc.audience`
      ——那一欄在圖書館形態下恆為 `jgb`，填進去會讓 `_select_outline` 的受眾比對恆假、
      `OutlineDoc.audience` 的 `Audience` 值域也會當場炸。
    - `source_ids=[]`：正本細目的來源是 `fine.sources`（`kb:*`／`docs:*` 字串），
      ⛔ 不硬塞成 `OutlineSection.source_ids`（那是 int 的 DB 列 id 欄位）。
    - `version=doc.version`；sha 由 `_build_doc` 涵蓋 `version`＋`text`（既有規則）。
    - 標題行的 `【<id>】` 前綴由 `_build_doc` 自動加（DSP-020），⛔ 此處不重複加。
    """
    from services.agent.outline import OutlineSection, _build_doc  # 循環相依，見模組 docstring

    effective_target_user = VendorKnowledgeRetrieverV2._effective_target_user(
        identity.target_user
    )
    sections = []
    for fine in doc.fines():
        if not _axes_visible(
            effective_target_user, identity.mode, fine, vendor_business_types
        ):
            continue
        # ⚠️ 這裡刻意再問一次 `canon_visible`（不變量 29b 的第三個消費端）：
        # 「屬於這個受眾」與「可以被引用」是兩件事，⛔ 不得用 `fine.reviewed_by` 自行判。
        citable = canon_visible(identity, fine, vendor_business_types=vendor_business_types)
        sections.append(
            OutlineSection(
                id=fine.id,
                title=fine.title,
                text=("\n".join(fine.content_units) if citable else ""),
                source_ids=[],
                citable=citable,
            )
        )
    return _build_doc(audience=audience, sections=sections, version=doc.version)


def _axes_visible(
    effective_target_user: str, mode: str, fine: FineItem, vendor_business_types: frozenset
) -> bool:
    """**受眾＋業態**兩軸（⛔ 不看 `reviewed_by`）——「這個細目屬不屬於這個身分的視圖」。

    規則見模組 docstring：分支判準與 SQL `is_b2b_mode` 同式；角色正規化由呼叫端先做
    （`canon_visible` 走 `_effective_target_user`，⛔ 不在此另寫一套）。

    ⚠️ **b2b 分支的 `target_user` 空集合＝不可見**（DSP-052 補救 (c)）——
    ⛔ 不得改回 `(not fine_target_user) or ...`：合法值 `target_user="tenant"`＋`mode="b2b"`
    會被 `audience_of` 的 `or mode == "b2b"` 路由到 pm 受眾，b2b 分支又拿 tenant 當鑰匙
    ⇒ 放行「空＝不設限」的細目就是跨受眾可見，且 `_no_match()` 刻意不分不可見與不存在
    ⇒ **靜默**。b2c 分支照舊（空放行＋`all_users`）。

    ⚠️ **b2b 分支的比對鑰匙把 `system_admin` 折成 `property_manager`**（DSP-053a）：
    `system_admin` 在正本上看到的＝`property_manager` 看到的那一份。這是**刻意的單向不對稱**——
    `kb.search` 的 `build_visibility_predicate` ⛔ 不折（SQL 側 `target_user && ARRAY['system_admin']`
    ⇒ 0 列），釘在 `test_visible_subset_sql_equiv_req.py` 的 `b2b-system_admin` 格。
    ⛔ 折疊只作用於這把鑰匙：`B2B_TARGET_USERS`／`is_b2b` 判準／`audience_of` 路由一律不動。
    """
    is_b2b = (effective_target_user in B2B_TARGET_USERS) or (mode == "b2b")

    fine_target_user = set(fine.target_user)
    fine_business_types = set(fine.business_types)

    if is_b2b:
        if not (fine_business_types & {B2B_BUSINESS_TYPE}):
            return False
        key = CANON_TARGET_USER_FOLD.get(effective_target_user, effective_target_user)
        return bool(fine_target_user) and (key in fine_target_user)

    if fine_business_types and not (fine_business_types & set(vendor_business_types)):
        return False
    return (
        (not fine_target_user)
        or (effective_target_user in fine_target_user)
        or (ALL_USERS_TOKEN in fine_target_user)
    )


def canon_visible(identity: Identity, fine: FineItem, *, vendor_business_types: frozenset) -> bool:
    """這個身分**引用得到**這個細目嗎（元件 6 `visible_subset` 的逐細目前身）。

    ＝`reviewed_by is not None` **且** `_axes_visible(...)`；與 SQL 謂詞的對照由
    `test_visible_subset_sql_equiv_req.py` 釘：pm／prospect／tenant 三格逐格相等；
    `system_admin` 這一格**刻意不相等**——正本側折成 `property_manager`（DSP-053a），
    `kb.search` 側對 `system_admin` 回 0 列。

    角色正規化重用 `VendorKnowledgeRetrieverV2._effective_target_user`
    （未知／`None` ⇒ tenant，fail-safe；⛔ 不另寫一套）。

    ⚠️ 分支判準讀**正規化後**的角色：對純量輸入與讀原值是恆等式（未知值兩邊都不在
    `B2B_TARGET_USERS`），差別只在 `target_user` 被傳成 list 時——讀原值會
    `TypeError: unhashable type: 'list'`。⚠️ SQL 側 `is_b2b_mode` 用的是 `in [...]`
    清單比對（list 輸入不炸、落 b2c 分支），故 list 輸入兩側分支會不同；`/mcp` 入口
    `parse_identity` 已先正規化成純量，正常路徑到不了那裡。
    """
    if fine.reviewed_by is None:
        return False
    return _axes_visible(
        VendorKnowledgeRetrieverV2._effective_target_user(identity.target_user),
        identity.mode,
        fine,
        vendor_business_types,
    )


def build_canon_toc(doc: CanonDoc, identity: Identity, *, vendor_business_types: frozenset):
    """`outline:toc` 節（目錄列**粗目**，⛔ 不列細目）。

    每個**含 ≥1 條可見已審細目**的粗目一行 `<粗目 id>｜<粗目標題>｜<可見細目數>`；
    零可見已審細目的粗目不出現（連粗目 id 都不列；細目平鋪會超出
    `OUTLINE_TOC_TOKEN_LIMIT`，列粗目才落在預算內）。粗目導航
    （`resolve_canon_section` 的 `outline:<粗目 id>`）才回傳該粗目底下的細目清單。

    ⛔ 另名，不與 pm／tenant 現役的 `outline.build_toc(db_pool, audience, vendor_id)` 同名
    （後者有 vendor 過濾，design 元件 5 明訂不得拿掉）。目錄只導航、不當事實依據。
    """
    from services.agent.outline import OutlineSection  # 循環相依，見模組 docstring

    lines = []
    for coarse in doc.coarses:
        count = sum(
            1
            for fine in coarse.fines
            if canon_visible(identity, fine, vendor_business_types=vendor_business_types)
        )
        if count:
            # 行首直接印 `kb.get` 可用的完整 id（`outline:<粗目 id>`）。
            # 只印裸 id 時，模型把資料段標記尾端的 `§<n>` 當成 id 呼叫 `kb.get("outline:32")`。
            lines.append(
                f"{OUTLINE_ID_PREFIX}{coarse.id}{TOC_LINE_SEP}{coarse.title}{TOC_LINE_SEP}{count}"
            )
    return OutlineSection(
        id=TOC_SECTION_ID,
        title=TOC_SECTION_TITLE,
        text="\n".join(lines),
        source_ids=[],
        citable=False,
    )


def build_canon_sections(
    doc: CanonDoc, identity: Identity, ids: list[str], *, vendor_business_types: frozenset
) -> list:
    """逐 `ids` 查 fine → 節列表（9.8 DSP-059 D′ S2／security-reviewer F1／F3(a)）。

    每個 id 都必須 `canon_visible` 為真（可見**且**已審）；不可見／未審／不存在
    的 id ⇒ **raise `CanonSectionInvisibleError`**（⛔ 不靜默跳過、⛔ 不產生
    `citable=False` 的空節——那個「未審只出標題」的語義屬於 `build_outline`
    的**全集視圖**，本函式服務的是**一回合的候選子集**，子集裡不該出現任何
    模型看得到題目卻拿不到內容的節）。

    節組法與 `build_outline` 完全同式：`id=fine.id`（⛔ 不加 `outline:` 前綴——
    前綴由 `kb.get`／DSP-029a 標記端自帶）、`title=fine.title`、
    `text="\\n".join(fine.content_units)`、`source_ids=[]`、`citable=True`
    （不可見者已在上面 raise，不會走到這裡產生 `citable=False` 節）。
    """
    from services.agent.outline import OutlineSection  # 循環相依，見模組 docstring

    by_id = {fine.id: fine for fine in doc.fines()}
    sections = []
    for fine_id in ids:
        fine = by_id.get(fine_id)
        if fine is None or not canon_visible(
            identity, fine, vendor_business_types=vendor_business_types
        ):
            raise CanonSectionInvisibleError(
                f"id {fine_id!r} 對此身分不可見／未審／不存在"
                f"（audience={identity.resolved_audience()!r}）"
            )
        sections.append(
            OutlineSection(
                id=fine.id,
                title=fine.title,
                text="\n".join(fine.content_units),
                source_ids=[],
                citable=True,
            )
        )
    return sections


def _no_match() -> ToolResult:
    """不可見／未審／不存在一律同一個錯誤——⛔ 不對模型區分（design：不洩漏差異）。"""
    return ToolResult(ok=False, error="NO_MATCH")


def resolve_canon_section(
    doc: CanonDoc, identity: Identity, section_id: str, *, vendor_business_types: frozenset
) -> ToolResult:
    """`kb.get("outline:*")` 的正本解析：**每回合**套 `canon_visible`（F7 修補點）。

    - `outline:toc` ⇒ 該身分的目錄（`citable=False`）。
    - `outline:<fine.id>` ⇒ 可見且已審才回內容（`citable=True`）；否則 `NO_MATCH`。
    - `outline:<粗目 id>`（粗目導航）⇒ 該粗目下可見已審細目的
      `<細目 id>｜<標題>` 清單（`citable=False`）；粗目**存在但零可見已審細目**
      與粗目**不存在**逐欄位回傳相同的 `NO_MATCH`（⛔ 不對模型區分，`_no_match` 設計）。
      過渡期裸字母粗目（`outline:A`）與 `<架字母>-<slug>` 走同一條路徑。
    - 判別順序寫死：先比細目 id（`FINE_ID_RE` 形狀）、再比粗目 id、其餘 `NO_MATCH`
      （兩種 id 形狀互斥——細目 id 含 `/`、粗目 id 不含，不會碰撞）。
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
    raw_id = section_id[len(OUTLINE_ID_PREFIX):]

    if FINE_ID_RE.match(raw_id):
        for fine in doc.fines():
            if fine.id != raw_id:
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

    coarse = next((c for c in doc.coarses if c.id == raw_id), None)
    if coarse is None:
        return _no_match()
    lines = [
        # 同目錄：印完整 id（`outline:<細目 id>`），模型照抄即可開（裸 id 開不起來）。
        f"{OUTLINE_ID_PREFIX}{fine.id}{TOC_LINE_SEP}{fine.title}"
        for fine in coarse.fines
        if canon_visible(identity, fine, vendor_business_types=vendor_business_types)
    ]
    if not lines:
        return _no_match()
    text = "\n".join(lines)
    return ToolResult(
        ok=True,
        data={"id": section_id, "question_summary": coarse.title, "answer": text},
        provenance=[Provenance(source=section_id, text=text, citable=False)],
        text_for_model=text,
    )
