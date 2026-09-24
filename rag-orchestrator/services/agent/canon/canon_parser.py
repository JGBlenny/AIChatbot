"""正本格式與解析（spec knowledge-outline-and-intent-architecture 元件 4；任務 2.1）。

Markdown 正本（`rag-orchestrator/canon/<audience>.md`）→ `CanonDoc`（決定性、附 `canon_sha256`）；`export_json` 單向導出。

格式（design 元件 4）：
- front matter 七鍵：`audience, version, reviewers, language, budget_tokens, target_user, business_types`。
- 粗目＝`## 標題 {#X}`（X 為單一大寫字母）；細目＝`### 標題 {#<audience>/<X>/<slug>}`，id 正則 `^[a-z_]+/[A-Z]/[a-z0-9-]+$`。
- 細目屬性區塊＝細目標題後連續的 `- key:` 行（鍵限 ATTR_KEYS）＋ `phrasings` 的 `  - {text: …, source: …, status: …}` 子項。
- 屬性區塊之後每一非空行＝一個內容句（`content_units`），與 `provenance_units.split_sentences` 切法恆等（一行不得含多句）。

嚴格性（F8）：**屬性區塊內任何無法解析的行一律 `CanonFormatError`（列號＋原因），⛔ 不落 `content_units`**——否則講法（含去識別後的真流量）會進 system prompt 成可引用句。
講法規則：`source: traffic:*` 的講法 ≤20 字且不含 ≥4 位數字串（去識別後仍不得帶識別碼形狀）。
target_user 值域（任務 9.1a）：front matter 與每個細目的 target_user 每一值須 ∈ `_target_user_universe()`
（`VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS`，⛔ 不含 `all_users`，DSP-052），對所有來源生效，否則 `CanonFormatError`。
see_also 目標存在性（任務 9.1a）：每個 `see_also` 的 id 必須是本正本內存在的細目 id，否則 `CanonFormatError`。

與 hook `.claude/hooks/outline_gate.py::check_structure` 的關係：hook 是編輯時的粗篩（PostToolUse），本檔是唯一的完整解析；
兩者的鍵清單與正則刻意同值（tests 守）。

圖書館形態（DSP-058／計畫 9.6 S1）：`parse_canon_dir("rag-orchestrator/canon/jgb")` 讀「一目錄＋九架」
（`A.md…I.md`，front matter 六鍵 `SHELF_FRONT_MATTER_KEYS`、細目 id 首段＝`CANON_NAME`、
`target_user`／`business_types` 必填非空），`export_catalog` 導出衍生目錄。
目錄路徑另有跨架檢查（9.6 S3）：同一句講法（NFKC，approved／proposed）⛔ 不得掛在兩個細目上
（跨架亦然）——同值規則在 hook `check_phrasing_unique` 以整個 `jgb/` 目錄為作用域再擋一次。

一架多粗目（計畫 9.10 S1；計畫 9.10 S5 移除裸字母後定案）：架內可有 ≥1 個
`## 標題 {#<字母>-<slug>}`（**唯一**合法形態）；粗目 id 首字母須＝檔名字母、且跨架全域唯一。
架標題唯一來源是 front matter `title`（`CanonDoc.shelf_titles`）；目錄路徑 ⛔ 不再有任何
「fm title 與架內 `## 標題` 相等」檢查——新形態下架內本就沒有與架同名的 `##`。
舊形態（架內恰一個裸字母 `{#X}` 粗目、id＝檔名字母）已於計畫 9.10 S5（DSP-070）**整條移除**，
⛔ 無旗標、⛔ 無相容入口；被取代的舊 210 條正本存進 git `c06575a9`，要讀就 `git show` 取出。
⚠️ **舊單檔路徑（`parse_canon`／`parse_canon_text`／`export_json` 對單檔的輸出）語義與位元組一律原封**——
兩條路徑共用同一台主體狀態機 `_parse_body`，差別只在 front matter 與三個旗標；單檔路徑的
`COARSE_HEADING_RE` 仍同時容納裸字母與 `<字母>-<slug>` 兩形態（⛔ 計畫 9.10 S5 不動）。
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from services.agent.provenance_units import split_sentences
from services.instance_applicability import (  # 不變量 10：宣告鍵與值域只從契約模組取，⛔ 不在此重寫字面
    APPLICABILITY_GENERAL, APPLICABILITY_INSTANCE, KNOWLEDGE_APPLICABILITY_KEY,
)

FRONT_MATTER_KEYS: tuple[str, ...] = (
    "audience", "version", "reviewers", "language", "budget_tokens", "target_user", "business_types",
)
AUDIENCES: tuple[str, ...] = ("prospect", "property_manager", "tenant")

# --- 圖書館形態（DSP-058；9.6 S1）------------------------------------------
# 一份目錄＋九架：`rag-orchestrator/canon/jgb/A.md … I.md`。⛔ 舊單檔路徑（`parse_canon`）語義原封。
CANON_NAME = "jgb"
#: 架檔 front matter **恰**六鍵（⛔ 無 budget_tokens、⛔ 無 target_user／business_types 檔級預設）。
SHELF_FRONT_MATTER_KEYS: tuple[str, ...] = ("coarse", "title", "scope", "version", "reviewers", "language")
#: 固定白名單、字母序。⛔ 不 glob——glob 會讓「多一個檔」變成靜默多讀，白名單讓它變成大聲失敗。
SHELF_FILES: tuple[str, ...] = tuple(f"{c}.md" for c in "ABCDEFGHI")
#: 目錄內允許共存的**衍生物／說明**檔名（⛔ 不被當正本讀）。
SHELF_DERIVED_OK: tuple[str, ...] = ("CATALOG.md", "README.md")
#: 講法唯一性納入的狀態（9.6 S3）：`retired` 不算——它是「退役講法」，留著只為可追溯，
#: ⛔ 不進索引（`fine_index.INDEXED_PHRASING_STATUS`）也就不會造成同分互搶。
PHRASING_UNIQUE_STATUSES: tuple[str, ...] = ("approved", "proposed")
#: b2b 業態嚴格過濾是 `business_types && ARRAY['system_provider']`（⛔ 無 IS NULL 放行）；
#: 正本細目不含它＝在 b2b 分支永遠不可見 ⇒ parser 直接擋，⛔ 不讓它靜默落成半可見資料。
CANON_BUSINESS_TYPE_REQUIRED = "system_provider"
ATTR_KEYS: tuple[str, ...] = (
    "phrasings", "sources", "reviewed", "see_also", "policy", "policy_ref",
    "target_user", "business_types", "categories", KNOWLEDGE_APPLICABILITY_KEY,
)
POLICIES: tuple[str, ...] = ("answerable", "deliberate_no", "not_available")
PHRASING_STATUSES: tuple[str, ...] = ("proposed", "approved", "retired")
INSTANCE_APPLICABILITY: tuple[str, ...] = (APPLICABILITY_INSTANCE, APPLICABILITY_GENERAL)

FINE_ID_RE = re.compile(r"^[a-z_]+/[A-Z]/[a-z0-9-]+$")
#: 粗目標頭——**單檔路徑**（`shelf_letter is None`）：容納裸字母（`{#A}`）與新形態（`{#A-slug}`），
#: ⛔ 計畫 9.10 S5 不動這一條（單檔路徑語義原封）。
COARSE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*\{#([A-Z](?:-[a-z0-9-]+)?)\}\s*$")
#: 粗目標頭——**目錄路徑**（計畫 9.10 S5／DSP-070）：⛔ 只認 `<架字母>-<slug>`，無寬版退路。
SHELF_COARSE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*\{#([A-I]-[a-z0-9-]+)\}\s*$")
#: 目錄路徑裸字母偵測（計畫 9.10 S5 item 7b）：先行擋住，給出點名「已停用」的專用訊息，
#: ⛔ 只在 `shelf_letter is not None` 生效——否則收緊 SHELF_COARSE_HEADING_RE 後，裸字母
#: 粗目只會落到泛用的「標題行無法解析」，驗收第一條（訊息逐字含停用聲明）不可達。
BARE_COARSE_HEADING_RE = re.compile(r"^##\s+.+\{#[A-Z]\}\s*$")
#: 目錄路徑裸字母停用聲明（計畫 9.10 S5／DSP-070；驗收逐字比對）。
BARE_COARSE_DISABLED_MSG = "粗目 id 須為 `<架字母>-<slug>`，裸字母形態已於 DSP-067／S5 停用"
FINE_HEADING_RE = re.compile(r"^###\s+(.+?)\s*\{#([^}]+)\}\s*$")
ATTR_LINE_RE = re.compile(r"^-\s*([a-zA-Z_]+)\s*:\s*(.*)$")
CONTINUATION_RE = re.compile(r"^\s+-\s+(.*)$")
PHRASING_ITEM_RE = re.compile(
    r'^\{\s*text\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*source\s*:\s*"([^"]+)"\s*,\s*status\s*:\s*([a-z]+)\s*\}$'
)
REVIEWED_RE = re.compile(r"^\{\s*by\s*:\s*([A-Za-z0-9_.@-]+)\s*,\s*at\s*:\s*(\d{4}-\d{2}-\d{2})\s*\}$")
LIST_RE = re.compile(r"^\[(.*)\]$")
TRAFFIC_DIGITS_RE = re.compile(r"\d{4,}")
# 「屬性形狀」的行（F8 守門，verifier 2026-09-06 P2）：掉了 `- ` 前綴的屬性行、掉了 `  - ` 前綴的 phrasing 子項，
# 不論出現在屬性區塊尾端或內容區，一律 raise、⛔ 不落 content_units。
ATTR_SHAPED_RE = re.compile(r"^\s*(?:\{|[A-Za-z_]+\s*:\s)")
TRAFFIC_MAX_CHARS = 20


class CanonFormatError(ValueError):
    """正本格式錯誤：訊息一律「第 N 行：原因」。"""

    def __init__(self, lineno: int, reason: str):
        self.lineno = lineno
        self.reason = reason
        super().__init__(f"第 {lineno} 行：{reason}")


@dataclass(frozen=True)
class Phrasing:
    text: str
    source: str
    status: str


@dataclass(frozen=True)
class FineItem:
    id: str
    coarse_id: str
    title: str
    phrasings: tuple[Phrasing, ...]
    content_units: tuple[str, ...]
    content_sha256: str
    sources: tuple[str, ...]
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    see_also: tuple[str, ...]
    policy: str
    policy_ref: Optional[str]
    target_user: tuple[str, ...]
    business_types: tuple[str, ...]
    categories: tuple[str, ...]
    instance_applicability: str


@dataclass(frozen=True)
class CoarseItem:
    id: str
    title: str
    fines: tuple[FineItem, ...]


@dataclass(frozen=True)
class CanonDoc:
    audience: str
    version: str
    reviewers: tuple[str, ...]
    language: str
    budget_tokens: int
    target_user: tuple[str, ...]
    business_types: tuple[str, ...]
    coarses: tuple[CoarseItem, ...]
    canon_sha256: str
    phrasing_set_sha256: str
    source_path: Optional[str] = field(default=None, compare=False)
    #: 正本名：單檔路徑＝`audience` 值；目錄路徑＝`CANON_NAME`。細目 id 首段須等於它。
    name: str = ""
    #: True＝由 `parse_canon_dir` 解析而來。⛔ 只影響**導出形狀**：
    #: 單檔導出必須與 9.6 之前逐位元相同（`test_canon_export_sync_req` 釘版控 JSON），故 `name`／`scopes` 不進單檔導出。
    library: bool = field(default=False, compare=False)
    #: 每架的歸位判準（`(粗目碼, scope)` 依粗目碼排序）；只有目錄路徑有值。
    scopes: tuple[tuple[str, str], ...] = ()
    #: 架標題（`(架字母, front matter title)`，依架字母排序）；只有目錄路徑有值（計畫 9.10 S1）。
    #: 新形態下架內沒有與架同名的 `##`，架標題**唯一來源**就是這裡——與 `scopes` 同款只在目錄路徑進導出。
    shelf_titles: tuple[tuple[str, str], ...] = ()

    def fines(self) -> tuple[FineItem, ...]:
        return tuple(f for c in self.coarses for f in c.fines)


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------

def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _nfkc(s: str) -> str:
    """NFKC＋去除所有空白（含全形）：守門比對不因插入空白而繞過（verifier 2026-09-06 advisory 1）。"""
    return "".join(unicodedata.normalize("NFKC", s).split())


def _parse_list(raw: str, lineno: int, what: str) -> tuple[str, ...]:
    m = LIST_RE.match(raw.strip())
    if not m:
        raise CanonFormatError(lineno, f"{what} 須為 [a, b] 清單，得到 {raw.strip()!r}")
    inner = m.group(1).strip()
    if not inner:
        return ()
    items = tuple(x.strip() for x in inner.split(","))
    if any(not x or " " in x for x in items):
        raise CanonFormatError(lineno, f"{what} 清單項不得為空或含空白：{raw.strip()!r}")
    return items


def _target_user_universe() -> frozenset:
    """target_user 封閉集（任務 9.1a）：不變量 10，⛔ 不在此重寫字面，單一來源 import。

    函式內 import 破循環相依（`canon_assembler` 模組層 import 本檔，見該檔頂端說明；
    與 `outline.py` 解 `canon_assembler` 循環相依同一手法）。
    """
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    # DSP-052：正本 ⛔ 不用 `all_users` 表中立（b2b 分支不放行 ⇒ 半可見）；中立一律寫空清單。
    # DB 側 b2c 仍合法使用 all_users——這是刻意的單向不對稱，⛔ 不動 build_visibility_predicate。
    return frozenset(VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS)


def _validate_target_user(values: tuple[str, ...], lineno: int) -> None:
    universe = _target_user_universe()
    bad = [v for v in values if v not in universe]
    if bad:
        raise CanonFormatError(
            lineno, f"target_user 值不在允許集合 {sorted(universe)} 內：{bad!r}",
        )


def _parse_scalar(raw: str, lineno: int, what: str) -> str:
    v = raw.strip()
    if not v:
        raise CanonFormatError(lineno, f"{what} 缺值")
    if v.startswith("[") or v.startswith("{"):
        raise CanonFormatError(lineno, f"{what} 須為純量，得到 {v!r}")
    return v


# ---------------------------------------------------------------------------
# front matter
# ---------------------------------------------------------------------------

def _parse_front_matter(lines: list[str]) -> tuple[dict, int]:
    if not lines or lines[0].strip() != "---":
        raise CanonFormatError(1, "缺 front matter（首行須為 ---）")
    fm: dict = {}
    idx = 1
    while idx < len(lines) and lines[idx].strip() != "---":
        line = lines[idx]
        lineno = idx + 1
        if line.strip():
            if ":" not in line:
                raise CanonFormatError(lineno, f"front matter 行無法解析：{line.strip()!r}")
            key, _, val = line.partition(":")
            key = key.strip()
            if key not in FRONT_MATTER_KEYS:
                raise CanonFormatError(lineno, f"front matter 不允許的鍵 {key!r}")
            if key in fm:
                raise CanonFormatError(lineno, f"front matter 鍵重複 {key!r}")
            fm[key] = (val, lineno)
        idx += 1
    if idx >= len(lines):
        raise CanonFormatError(len(lines), "front matter 未閉合（缺結尾 ---）")
    missing = [k for k in FRONT_MATTER_KEYS if k not in fm]
    if missing:
        raise CanonFormatError(idx + 1, f"front matter 缺鍵：{', '.join(missing)}")
    out: dict = {}
    out["audience"] = _parse_scalar(*fm["audience"], "audience")
    if out["audience"] not in AUDIENCES:
        raise CanonFormatError(fm["audience"][1], f"audience 須為 {AUDIENCES} 之一，得到 {out['audience']!r}")
    out["version"] = _parse_scalar(*fm["version"], "version")
    out["language"] = _parse_scalar(*fm["language"], "language")
    raw_bt, ln_bt = fm["budget_tokens"]
    if not raw_bt.strip().isdigit():
        raise CanonFormatError(ln_bt, f"budget_tokens 須為正整數，得到 {raw_bt.strip()!r}")
    out["budget_tokens"] = int(raw_bt.strip())
    out["reviewers"] = _parse_list(*fm["reviewers"], "reviewers")
    out["target_user"] = _parse_list(*fm["target_user"], "target_user")
    _validate_target_user(out["target_user"], fm["target_user"][1])
    out["business_types"] = _parse_list(*fm["business_types"], "business_types")
    return out, idx + 1


# ---------------------------------------------------------------------------
# 細目屬性區塊
# ---------------------------------------------------------------------------

def _parse_phrasing_item(raw: str, lineno: int) -> Phrasing:
    m = PHRASING_ITEM_RE.match(raw.strip())
    if not m:
        raise CanonFormatError(lineno, f"phrasings 子項須為 {{text: \"…\", source: \"…\", status: …}}，得到 {raw.strip()!r}")
    text = m.group(1).replace('\\"', '"')
    source, status = m.group(2), m.group(3)
    if status not in PHRASING_STATUSES:
        raise CanonFormatError(lineno, f"phrasings status 須為 {PHRASING_STATUSES} 之一，得到 {status!r}")
    if not text.strip():
        raise CanonFormatError(lineno, "phrasings text 不得為空")
    if source.startswith("traffic:"):
        if len(text) > TRAFFIC_MAX_CHARS:
            raise CanonFormatError(lineno, f"traffic 講法超過 {TRAFFIC_MAX_CHARS} 字（{len(text)}）")
        if TRAFFIC_DIGITS_RE.search(text):
            raise CanonFormatError(lineno, "traffic 講法含 ≥4 位數字串（疑似識別碼）")
    return Phrasing(text=text, source=source, status=status)


def _build_fine(head_lineno: int, fid: str, coarse_id: str, title: str, attrs: dict, content: list[str],
                doc_defaults: dict, require_fine_attrs: bool = False) -> FineItem:
    phr = tuple(attrs.get("phrasings", ()))
    policy = attrs.get("policy", "answerable")
    if KNOWLEDGE_APPLICABILITY_KEY not in attrs:
        raise CanonFormatError(head_lineno, f"細目 {fid} 缺必填屬性 {KNOWLEDGE_APPLICABILITY_KEY}（{'｜'.join(INSTANCE_APPLICABILITY)}）")
    if require_fine_attrs:
        # 目錄路徑無檔級預設（DSP-058）：兩個可見性軸只認**明列**成員，缺／空 ⇒ 大聲失敗，
        # ⛔ 不落成 ()——那會變成 b2b 不可見、b2c 不設限的半可見資料。
        for key in ("target_user", "business_types", "sources"):
            if not attrs.get(key):
                raise CanonFormatError(
                    head_lineno,
                    f"細目 {fid} 缺必填屬性 {key}（目錄正本無檔級預設，須明列非空清單；sources＝每句可對回的權威，定義 D6）",
                )
        if CANON_BUSINESS_TYPE_REQUIRED not in attrs["business_types"]:
            raise CanonFormatError(
                head_lineno,
                f"細目 {fid} 的 business_types 須含 {CANON_BUSINESS_TYPE_REQUIRED!r}"
                f"（b2b 業態過濾是嚴格 && 交集，不含即永不可見）",
            )
    reviewed = attrs.get("reviewed")
    units = tuple(content)
    return FineItem(
        id=fid, coarse_id=coarse_id, title=title, phrasings=phr, content_units=units,
        content_sha256=_sha256_text("\n".join(units)),
        sources=tuple(attrs.get("sources", ())),
        reviewed_by=reviewed[0] if reviewed else None, reviewed_at=reviewed[1] if reviewed else None,
        see_also=tuple(attrs.get("see_also", ())),
        policy=policy, policy_ref=attrs.get("policy_ref"),
        target_user=tuple(attrs.get("target_user", doc_defaults["target_user"])),
        business_types=tuple(attrs.get("business_types", doc_defaults["business_types"])),
        categories=tuple(attrs.get("categories", ())),
        instance_applicability=attrs[KNOWLEDGE_APPLICABILITY_KEY],
    )


def _parse_attr_value(key: str, raw: str, lineno: int):
    if key == "target_user":
        vals = _parse_list(raw, lineno, key)
        _validate_target_user(vals, lineno)
        return vals
    if key in ("sources", "see_also", "business_types", "categories"):
        return _parse_list(raw, lineno, key)
    if key == "reviewed":
        m = REVIEWED_RE.match(raw.strip())
        if not m:
            raise CanonFormatError(lineno, f"reviewed 須為 {{by: …, at: YYYY-MM-DD}}，得到 {raw.strip()!r}")
        return (m.group(1), m.group(2))
    if key == "policy":
        v = _parse_scalar(raw, lineno, "policy")
        if v not in POLICIES:
            raise CanonFormatError(lineno, f"policy 須為 {POLICIES} 之一，得到 {v!r}")
        return v
    if key == "policy_ref":
        return _parse_scalar(raw, lineno, "policy_ref")
    if key == KNOWLEDGE_APPLICABILITY_KEY:
        v = _parse_scalar(raw, lineno, KNOWLEDGE_APPLICABILITY_KEY)
        if v not in INSTANCE_APPLICABILITY:
            raise CanonFormatError(lineno, f"{KNOWLEDGE_APPLICABILITY_KEY} 須為 {INSTANCE_APPLICABILITY} 之一，得到 {v!r}")
        return v
    raise CanonFormatError(lineno, f"屬性 {key!r} 不支援")  # pragma: no cover — 上游已擋


def _parse_body(
    lines: list[str],
    body_start: int,
    *,
    id_prefix: str,
    id_prefix_kind: str,
    defaults: dict,
    require_fine_attrs: bool = False,
    shelf_letter: Optional[str] = None,
) -> tuple[list[CoarseItem], dict, list]:
    """正本主體狀態機——**單檔與目錄兩條路徑共用同一台**（⛔ 不複製一份）。

    回 `(coarses, seen_fine, pending_see_also)`。`see_also` 目標存在性由呼叫端在收齊全部細目後核對：
    單檔＝本檔內，目錄＝跨九架（故不能在這裡就驗）。

    `id_prefix_kind`：`"audience"`＝單檔路徑（訊息沿用「受眾」字樣，⛔ 不改——既有回歸測試釘它）；
    `"name"`＝目錄路徑（訊息說「正本名」）。

    `shelf_letter`（計畫 9.10 S1）：細目 id 中段的比對基準。`None`（單檔路徑）⇒ 比對行為與訊息
    **逐字不變**（仍比 `current_coarse[0]`，既有回歸測試釘住那句）；目錄路徑傳入架字母 ⇒ 改比
    架字母（新形態下一架可有多個粗目，粗目 id 不再等於架字母，細目中段仍是架字母）。
    """
    coarses: list[CoarseItem] = []
    fines_of_current: list[FineItem] = []
    current_coarse: Optional[tuple[str, str]] = None  # (id, title)
    seen_coarse: set[str] = set()
    seen_fine: dict[str, int] = {}
    # see_also 目標存在性（任務 9.1a）：目標可能在檔案更後面才出現，須等整檔 seen_fine 收齊後再驗，
    # 故先蒐集 (來源細目 id, see_also 清單, `see_also:` 行號) 待整檔解析完再逐一核對。
    pending_see_also: list[tuple[str, tuple[str, ...], int]] = []

    # 細目狀態機
    fine_open = False
    fine_head_lineno = 0
    fine_id = ""
    fine_title = ""
    attrs: dict = {}
    content: list[str] = []
    in_attr_block = False        # 尚未出現內容行（屬性區塊仍可延伸）
    open_list_key: Optional[str] = None  # phrasings 子項延續中
    see_also_lineno = 0          # 當前細目 `see_also:` 屬性行行號（0＝本細目未宣告）

    def close_fine():
        nonlocal fine_open, attrs, content, in_attr_block, open_list_key, see_also_lineno
        if fine_open:
            sa = attrs.get("see_also", ())
            if sa:
                pending_see_also.append((fine_id, sa, see_also_lineno))
            fines_of_current.append(_build_fine(
                fine_head_lineno, fine_id, current_coarse[0], fine_title, attrs, content, defaults,
                require_fine_attrs=require_fine_attrs,
            ))
        fine_open = False
        see_also_lineno = 0
        attrs, content, in_attr_block, open_list_key = {}, [], False, None

    def close_coarse():
        nonlocal fines_of_current, current_coarse
        close_fine()
        if current_coarse is not None:
            coarses.append(CoarseItem(id=current_coarse[0], title=current_coarse[1], fines=tuple(fines_of_current)))
        fines_of_current = []
        current_coarse = None

    for i in range(body_start, len(lines)):
        lineno = i + 1
        line = lines[i]

        if shelf_letter is not None and BARE_COARSE_HEADING_RE.match(line):
            # 目錄路徑專用：裸字母粗目已停用（計畫 9.10 S5／DSP-070），先行偵測給出點名訊息，
            # ⛔ 不落到下面 SHELF_COARSE_HEADING_RE 不匹配後的泛用「標題行無法解析」。
            raise CanonFormatError(lineno, BARE_COARSE_DISABLED_MSG)

        cm = (COARSE_HEADING_RE if shelf_letter is None else SHELF_COARSE_HEADING_RE).match(line)
        if cm:
            close_coarse()
            title, cid = cm.group(1), cm.group(2)
            if cid in seen_coarse:
                raise CanonFormatError(lineno, f"粗目碼重複 {cid!r}")
            seen_coarse.add(cid)
            current_coarse = (cid, title)
            continue

        fmh = FINE_HEADING_RE.match(line)
        if fmh:
            if current_coarse is None:
                raise CanonFormatError(lineno, "細目出現在任何粗目之前")
            close_fine()
            title, fid = fmh.group(1), fmh.group(2)
            if not FINE_ID_RE.match(fid):
                raise CanonFormatError(lineno, f"細目 id 不合法格式 {fid!r}（須為 <audience>/<粗目碼>/<slug>）")
            aud, ccode, _slug = fid.split("/")
            if aud != id_prefix:
                if id_prefix_kind == "audience":
                    raise CanonFormatError(lineno, f"細目 id 受眾 {aud!r} 與 front matter audience {id_prefix!r} 不符")
                raise CanonFormatError(lineno, f"細目 id 首段 {aud!r} 與正本名 {id_prefix!r} 不符")
            if shelf_letter is None:
                if ccode != current_coarse[0]:
                    raise CanonFormatError(lineno, f"細目 id 粗目碼 {ccode!r} 與所在粗目 {current_coarse[0]!r} 不符")
            elif ccode != shelf_letter:
                raise CanonFormatError(lineno, f"細目 id 中段 {ccode!r} 與所在架 {shelf_letter!r} 不符")
            if fid in seen_fine:
                raise CanonFormatError(lineno, f"細目 id 重複 {fid!r}（首見於第 {seen_fine[fid]} 行）")
            seen_fine[fid] = lineno
            fine_open, fine_head_lineno, fine_id, fine_title = True, lineno, fid, title
            in_attr_block = True
            continue

        if line.startswith("#"):
            raise CanonFormatError(
                lineno,
                "標題行無法解析（粗目須 `## 標題 {#<架字母>-<slug>}`、"
                f"細目須 `### 標題 {{#id}}`）：{line.strip()!r}",
            )

        if not fine_open:
            if line.strip():
                raise CanonFormatError(lineno, f"粗目底下、細目之外不得有內容：{line.strip()!r}")
            continue

        if not line.strip():
            # 空行：屬性區塊內忽略；內容區內忽略（不算句）
            continue

        am = ATTR_LINE_RE.match(line)
        cont = CONTINUATION_RE.match(line)

        if in_attr_block:
            if am:
                key, raw = am.group(1), am.group(2)
                if key not in ATTR_KEYS:
                    raise CanonFormatError(lineno, f"屬性區塊出現不允許的鍵 {key!r}")
                if key in attrs:
                    raise CanonFormatError(lineno, f"屬性重複 {key!r}")
                if key == "phrasings":
                    if raw.strip():
                        raise CanonFormatError(lineno, "phrasings 須以子項列出（`- phrasings:` 後換行縮排 `- {…}`）")
                    attrs["phrasings"] = []
                    open_list_key = "phrasings"
                else:
                    attrs[key] = _parse_attr_value(key, raw, lineno)
                    open_list_key = None
                    if key == "see_also":
                        see_also_lineno = lineno
                continue
            if cont:
                if open_list_key != "phrasings":
                    raise CanonFormatError(lineno, f"縮排子項只允許在 phrasings 底下：{line.strip()!r}")
                attrs["phrasings"].append(_parse_phrasing_item(cont.group(1), lineno))
                continue
            if line.startswith("-") or line[0].isspace() or ATTR_SHAPED_RE.match(line):
                raise CanonFormatError(lineno, f"屬性區塊內無法解析的行（⛔ 不落內容）：{line.strip()!r}")
            # 第一個內容行：屬性區塊結束
            in_attr_block = False
            open_list_key = None

        # 內容區
        if am or cont or line.startswith("-") or line[0].isspace() or ATTR_SHAPED_RE.match(line):
            raise CanonFormatError(lineno, f"內容區出現屬性形狀的行（屬性須在內容之前）：{line.strip()!r}")
        unit = line.strip()
        if len(split_sentences(unit)) != 1:
            raise CanonFormatError(lineno, f"一行只能一句（provenance_units 切法恆等）：{unit!r}")
        content.append(unit)

    close_coarse()
    return coarses, seen_fine, pending_see_also


def _check_see_also(pending_see_also: list, seen_fine: dict, scope_label: str) -> None:
    """see_also 目標存在性（任務 9.1a）：seen_fine 收齊後逐一核對。"""
    for src_fid, targets, sa_lineno in pending_see_also:
        for target in targets:
            if target not in seen_fine:
                raise CanonFormatError(sa_lineno, f"細目 {src_fid} 的 see_also 目標不存在於{scope_label} {target!r}")


def _check_phrasing_unique(coarses) -> None:
    """同一句講法（NFKC 後）⛔ 不得掛在兩個細目上——**跨架亦然**（9.6 S3；hook 同值規則）。

    理由（tasks 9.1c 實測）：同一句講法掛兩個細目 ⇒ 兩者向量相同、分數同分，
    `CandidateSelector` 的 `(-score, fine_id)` 排序只能靠 id 字典序決定誰進 K，
    「哪一條被選中」就成了改名字就會變的事。
    ⚠️ 只看 `PHRASING_UNIQUE_STATUSES`（approved／proposed）；`retired` 不算。
    ⚠️ **同一細目內**重複同一句不在本條範圍（那是冗餘、不是搶分），⛔ 不順手擴大。

    行號取**後出現**的那個細目的標題行（`seen_fine` 記的是細目標題行號）——跨架時
    訊息另帶兩個細目 id，查得到是哪兩條。
    """
    seen: dict = {}      # nfkc(text) -> (fine_id, 原文)
    for coarse in coarses:
        for fine in coarse.fines:
            for phrasing in fine.phrasings:
                if phrasing.status not in PHRASING_UNIQUE_STATUSES:
                    continue
                key = _nfkc(phrasing.text)
                if not key:
                    continue
                prev = seen.get(key)
                if prev is None:
                    seen[key] = (fine.id, phrasing.text)
                    continue
                if prev[0] != fine.id:
                    raise CanonFormatError(
                        0,
                        f"講法跨細目重複 {phrasing.text!r}：細目 {prev[0]!r} 與 {fine.id!r}"
                        "（同一句掛兩條 ⇒ 同分，誰進候選只剩 id 字典序決定）",
                    )


def _phrasing_set_sha(coarses) -> str:
    """approved 講法集合的 sha（單檔與目錄同一算法）。"""
    approved = sorted((f.id, p.text) for c in coarses for f in c.fines for p in f.phrasings if p.status == "approved")
    return _sha256_text(json.dumps(approved, ensure_ascii=False, separators=(",", ":")))


def parse_canon_text(text: str, source_path: Optional[str] = None) -> CanonDoc:
    """解析正本全文（決定性）。任何格式錯 ⇒ CanonFormatError（列號＋原因）。

    ⚠️ 單檔路徑（9.6 之前的語義）**原封**：front matter 七鍵、細目 id 首段＝`audience`、
    `target_user`／`business_types` 缺省繼承檔級預設。圖書館形態走 `parse_canon_dir`。
    """
    canon_sha = _sha256_text(text)
    lines = text.split("\n")
    fm, body_start = _parse_front_matter(lines)
    defaults = {"target_user": fm["target_user"], "business_types": fm["business_types"]}

    coarses, seen_fine, pending_see_also = _parse_body(
        lines, body_start, id_prefix=fm["audience"], id_prefix_kind="audience", defaults=defaults,
    )
    if not coarses:
        raise CanonFormatError(len(lines), "正本沒有任何粗目")
    _check_see_also(pending_see_also, seen_fine, "本正本")

    return CanonDoc(
        audience=fm["audience"], version=fm["version"], reviewers=fm["reviewers"], language=fm["language"],
        budget_tokens=fm["budget_tokens"], target_user=fm["target_user"], business_types=fm["business_types"],
        coarses=tuple(coarses), canon_sha256=canon_sha, phrasing_set_sha256=_phrasing_set_sha(coarses),
        source_path=source_path, name=fm["audience"],
    )


def parse_canon(path: str) -> CanonDoc:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return parse_canon_text(text, source_path=path)


# ---------------------------------------------------------------------------
# 目錄（圖書館）路徑：一份目錄＋九架（DSP-058）
# ---------------------------------------------------------------------------

def _parse_shelf_front_matter(lines: list[str], shelf_letter: str) -> tuple[dict, int]:
    """架檔 front matter：**恰**六鍵 SHELF_FRONT_MATTER_KEYS（多鍵／缺鍵一律 raise）。"""
    if not lines or lines[0].strip() != "---":
        raise CanonFormatError(1, "缺 front matter（首行須為 ---）")
    fm: dict = {}
    idx = 1
    while idx < len(lines) and lines[idx].strip() != "---":
        line = lines[idx]
        lineno = idx + 1
        if line.strip():
            if ":" not in line:
                raise CanonFormatError(lineno, f"front matter 行無法解析：{line.strip()!r}")
            key, _, val = line.partition(":")
            key = key.strip()
            if key not in SHELF_FRONT_MATTER_KEYS:
                raise CanonFormatError(lineno, f"架 front matter 不允許的鍵 {key!r}（恰六鍵 {SHELF_FRONT_MATTER_KEYS}）")
            if key in fm:
                raise CanonFormatError(lineno, f"front matter 鍵重複 {key!r}")
            fm[key] = (val, lineno)
        idx += 1
    if idx >= len(lines):
        raise CanonFormatError(len(lines), "front matter 未閉合（缺結尾 ---）")
    missing = [k for k in SHELF_FRONT_MATTER_KEYS if k not in fm]
    if missing:
        raise CanonFormatError(idx + 1, f"架 front matter 缺鍵：{', '.join(missing)}")

    out: dict = {}
    out["coarse"] = _parse_scalar(*fm["coarse"], "coarse")
    if out["coarse"] != shelf_letter:
        raise CanonFormatError(fm["coarse"][1], f"coarse {out['coarse']!r} 與檔名字母 {shelf_letter!r} 不符")
    out["title"] = _parse_scalar(*fm["title"], "title")
    # `scope`＝歸位判準（計畫附錄 A）。缺鍵走上面的「缺鍵」；空白值由 `_parse_scalar` 擋（⛔ 不放行空 scope）。
    out["scope"] = _parse_scalar(*fm["scope"], "scope")
    out["version"] = _parse_scalar(*fm["version"], "version")
    out["language"] = _parse_scalar(*fm["language"], "language")
    out["reviewers"] = _parse_list(*fm["reviewers"], "reviewers")
    return out, idx + 1


def _shelf_paths(base: Path) -> list[tuple[str, str, Path]]:
    """回 [(檔名, 粗目碼, 路徑)]（字母序）。白名單外 `.md`／缺架／符號連結／逃出目錄一律 raise。"""
    if not base.is_dir():
        raise CanonFormatError(0, f"正本目錄不存在或不是目錄：{base}")

    allowed = set(SHELF_FILES) | set(SHELF_DERIVED_OK)
    for entry in sorted(p.name for p in base.iterdir() if p.name.endswith(".md")):
        if entry not in allowed:
            raise CanonFormatError(
                0,
                f"正本目錄出現白名單外的 .md：{entry}"
                f"（架只認 {SHELF_FILES}；衍生物只認 {SHELF_DERIVED_OK}）",
            )

    out: list[tuple[str, str, Path]] = []
    for fname in SHELF_FILES:
        p = base / fname
        # ⚠️ 順序刻意：先問符號連結再問存在——`exists()` 會跟隨連結，壞連結會被誤報成「缺架」。
        if p.is_symlink():
            raise CanonFormatError(0, f"架 {fname} 是符號連結（⛔ 不跟隨；正本必須是目錄內的真檔）")
        if not p.exists():
            raise CanonFormatError(0, f"缺架 {fname}")
        resolved = p.resolve()
        if resolved.parent != base or not resolved.is_file():
            raise CanonFormatError(0, f"架 {fname} 逃出正本目錄或不是一般檔案：{resolved}")
        out.append((fname, fname[:-3], p))
    return out


def parse_canon_dir(dir_path: str) -> CanonDoc:
    """解析「一目錄＋九架」正本（DSP-058；決定性）。

    - 只讀固定白名單 `A.md…I.md`（⛔ 不 glob）；每架 front matter 恰六鍵、`coarse`＝檔名字母。
    - 粗目（計畫 9.10 S1，一架多粗目；S5／DSP-070 移除裸字母後定案）：①每架至少一個粗目
      ②每個粗目 id 首字母＝檔名字母 ③粗目 id 跨架唯一。⛔ 無「fm title 與架內 `## 標題`
      相等」檢查——架標題唯一來源＝`shelf_titles`。
    - 細目 id 首段須等於 `CANON_NAME`；`target_user`／`business_types` **必填非空**（⛔ 無檔級預設）。
    - `canon_sha256` ＝ `sha256("\\n".join(每架全文 sha256, 依字母序))`——任何一架動一位元就變。
    - `budget_tokens` 目錄路徑恆為 `0`（架 front matter 無此鍵；預算上限由 `outline.py` 常數表管）。
    """
    base = Path(dir_path).resolve()
    shelves = _shelf_paths(base)

    coarses: list[CoarseItem] = []
    seen_fine: dict = {}
    pending_see_also: list = []
    scopes: list[tuple[str, str]] = []
    shelf_titles: list[tuple[str, str]] = []
    shelf_shas: list[str] = []
    head: Optional[dict] = None
    coarse_owner: dict[str, str] = {}  # 粗目 id -> 首見架檔名（③ 跨架唯一）

    for fname, letter, path in shelves:
        text = path.read_text(encoding="utf-8")
        shelf_shas.append(_sha256_text(text))
        lines = text.split("\n")
        try:
            fm, body_start = _parse_shelf_front_matter(lines, letter)
            shelf_coarses, shelf_seen, shelf_pending = _parse_body(
                lines, body_start,
                id_prefix=CANON_NAME, id_prefix_kind="name",
                defaults={"target_user": (), "business_types": ()},
                require_fine_attrs=True,
                shelf_letter=letter,
            )
            # 計畫 9.10 S1，三條不變量取代舊的「恰一個粗目」與「粗目碼＝檔名字母」：
            if not shelf_coarses:
                raise CanonFormatError(body_start + 1, "架至少須有一個粗目")
            for coarse in shelf_coarses:
                # ⚠️ 順序刻意：跨架重複先查——粗目 id 跨架重複時，後出現的那個必然也會撞
                # 「首字母≠檔名字母」（唯一能讓 id 通過②的檔只有一個），先查③才報得出
                # 「跨架重複」而不是被②先攔截、訊息永遠報不出跨架這件事。
                if coarse.id in coarse_owner:
                    raise CanonFormatError(
                        body_start + 1,
                        f"粗目 id 跨架重複 {coarse.id!r}（首見於 {coarse_owner[coarse.id]}）",
                    )
                if coarse.id[0] != letter:
                    raise CanonFormatError(
                        body_start + 1, f"粗目 id {coarse.id!r} 首字母與檔名字母 {letter!r} 不符",
                    )
                coarse_owner[coarse.id] = fname
        except CanonFormatError as exc:
            # 訊息格式維持「第 N 行：…」，原因前面補上是哪一架（跨檔錯誤沒有檔名就無從查起）。
            raise CanonFormatError(exc.lineno, f"{fname}：{exc.reason}") from exc

        if head is None:
            head = {"version": fm["version"], "reviewers": fm["reviewers"], "language": fm["language"]}
        else:
            for key in ("version", "reviewers", "language"):
                if fm[key] != head[key]:
                    raise CanonFormatError(0, f"{fname}：{key} 與前面各架不一致（{fm[key]!r} vs {head[key]!r}）")

        for fid, lineno in shelf_seen.items():
            if fid in seen_fine:
                raise CanonFormatError(lineno, f"{fname}：細目 id 跨架重複 {fid!r}")
            seen_fine[fid] = lineno
        coarses.extend(shelf_coarses)
        pending_see_also.extend(shelf_pending)
        scopes.append((letter, fm["scope"]))
        shelf_titles.append((letter, fm["title"]))

    _check_see_also(pending_see_also, seen_fine, "本正本（跨架）")
    _check_phrasing_unique(coarses)

    assert head is not None  # SHELF_FILES 非空 ⇒ 迴圈必至少跑一次
    canon_sha = _sha256_text("\n".join(shelf_shas))
    return CanonDoc(
        audience=CANON_NAME, version=head["version"], reviewers=head["reviewers"], language=head["language"],
        budget_tokens=0, target_user=(), business_types=(),
        coarses=tuple(coarses), canon_sha256=canon_sha, phrasing_set_sha256=_phrasing_set_sha(coarses),
        source_path=str(base), name=CANON_NAME, library=True, scopes=tuple(scopes),
        shelf_titles=tuple(shelf_titles),
    )


# ---------------------------------------------------------------------------
# 導出與守門
# ---------------------------------------------------------------------------

def to_dict(doc: CanonDoc) -> dict:
    d = asdict(doc)
    d.pop("source_path", None)
    # ⚠️ 單檔路徑的導出必須與 9.6 之前**逐位元相同**（`test_canon_export_sync_req` 拿版控 JSON 對位元組）
    # ⇒ 9.6／9.10 新增的欄位只在目錄路徑進導出。`library` 本身是解析來源標記，兩條路徑都不進導出。
    if not d.pop("library", False):
        d.pop("name", None)
        d.pop("scopes", None)
        d.pop("shelf_titles", None)
    return d


def _reject_bare_coarse_ids(doc: CanonDoc, caller: str) -> None:
    """導出防線（計畫 9.10 S5 item 7c）：⛔ 只查**目錄路徑**（`doc.library`）的裸字母粗目 id。

    `parse_canon_dir` 本身已在解析階段（`BARE_COARSE_HEADING_RE`）擋住裸字母，正常情況下
    不可能走到這裡；本檢查是移除 `export_catalog` 的 `is_bare` 分支後的第二道防線——
    否則萬一有裸字母粗目繞過 parser 直接組出 `CanonDoc`，會靜默落進新形態分支、輸出錯誤
    的衍生物而非大聲失敗。訊息點名該粗目 id。

    ⛔ 不查**單檔路徑**（`library=False`）：單檔路徑的 `FINE_ID_RE` 細目中段強制單一大寫
    字母、且須等於所在粗目 id（`COARSE_HEADING_RE` 逐字不動），有內容的粗目本就必須是
    裸字母——這是單檔路徑既有、未變的合法形態，不是本片要清除的目錄路徑舊格式。
    """
    if not doc.library:
        return
    for coarse in doc.coarses:
        if len(coarse.id) == 1:
            raise CanonFormatError(
                0, f"{caller}：粗目 id {coarse.id!r} 為裸字母形態，已於 DSP-067／S5 停用",
            )


def export_json(doc: CanonDoc, out_path: str) -> str:
    """單向導出 JSON（鍵排序、UTF-8、結尾換行）；回 canon_sha256，JSON 內帶同一 sha。"""
    _reject_bare_coarse_ids(doc, "export_json")
    payload = json.dumps(to_dict(doc), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    return doc.canon_sha256


CATALOG_FIELD_SEP = "｜"
CATALOG_PHRASING_SEP = "／"


def export_catalog(doc: CanonDoc, out_path: str) -> str:
    """導出衍生目錄 `CATALOG.md`（決定性；⛔ 不含 content_units，⛔ 不手改）。

    逐**粗目**輸出（計畫 9.10 S2；S5／DSP-070 移除裸字母後只剩一種形態）：`coarse.id`
    恆為 `<架字母>-<slug>` ⇒ 以 `coarse.id[0]` 取 `shelf_titles`／`scopes`：該架**第一次
    出現**時先出架層兩行（`## <架字母> <架標題> {#<架字母>}`、`scope: …`），之後每個粗目
    一行 `### <粗目 id> <粗目標題> {#<粗目 id>}`，再接該粗目的細目行。查無鍵 ⇒ raise
    （點名架字母與粗目 id），⛔ 不回退空字串或省略該行——`.get(key, "")` 會把空 scope
    靜默寫進被位元組比對的衍生物，比對的是自己的導出，永遠測不出來。
    每細目一行 `<id>｜<title>｜target_user=<a,b>｜<approved 講法以「／」串接>`。
    空行規則：架與架之間一個空行；同架的粗目之間不插空行。
    回傳寫出去的全文（呼叫端要比位元組時免得再讀檔）。
    """
    _reject_bare_coarse_ids(doc, "export_catalog")
    scope_of = dict(doc.scopes)
    shelf_title_of = dict(doc.shelf_titles)
    out: list[str] = []
    current_shelf: Optional[str] = None  # 目前正在輸出哪一架（同架粗目間不插空行）

    for coarse in doc.coarses:
        shelf = coarse.id[0]
        if shelf != current_shelf:
            if out:
                out.append("")
            if shelf not in shelf_title_of:
                raise CanonFormatError(
                    0, f"export_catalog：架 {shelf!r} 缺 shelf_titles（粗目 {coarse.id!r}）",
                )
            if shelf not in scope_of:
                raise CanonFormatError(
                    0, f"export_catalog：架 {shelf!r} 缺 scopes（粗目 {coarse.id!r}）",
                )
            out.append(f"## {shelf} {shelf_title_of[shelf]} {{#{shelf}}}")
            out.append(f"scope: {scope_of[shelf]}")
            current_shelf = shelf
        out.append(f"### {coarse.id} {coarse.title} {{#{coarse.id}}}")
        for fine in coarse.fines:
            phrasings = CATALOG_PHRASING_SEP.join(p.text for p in fine.phrasings if p.status == "approved")
            out.append(CATALOG_FIELD_SEP.join([
                fine.id, fine.title, "target_user=" + ",".join(fine.target_user), phrasings,
            ]))
    payload = "\n".join(out) + "\n"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    return payload


def content_text(doc: CanonDoc) -> str:
    """可引用內容全文（只含 content_units；⛔ 不含講法）——組 OutlineDoc.text 的唯一來源。"""
    return "\n".join(u for f in doc.fines() for u in f.content_units)


LEAK_CONTAINS_MIN_CHARS = 10  # 主題詞組（「大房東報表」「Bananas」）本來就會出現在內容句裡；只有整句長度的講法才用包含比對


def phrasing_leaks(doc: CanonDoc, text: Optional[str] = None) -> list[str]:
    """守門：講法進了可引用文字 ⇒ 列出；空清單＝乾淨。

    判準（NFKC＋去空白後）：①講法與某一內容句**整句相等**；或②講法長度 ≥ LEAK_CONTAINS_MIN_CHARS 且**包含**於可引用文字。
    主題詞組（「合約」「大房東報表」）本來就會是內容句的子字串，子字串比對對它們恆誤判，故 ② 設長度下限；
    真流量原句（≥10 字的完整問句）被塞進內容行、或任何講法整句成為一個內容行，仍抓得到。text 省略時檢查 content_text(doc)。"""
    if text is not None:
        units = [text]
    else:
        units = [u for f in doc.fines() for u in f.content_units]
    hay_units = [_nfkc(u) for u in units]
    hay = "\n".join(hay_units)
    leaks = []
    for f in doc.fines():
        for p in f.phrasings:
            needle = _nfkc(p.text)
            if not needle:
                continue
            if needle in hay_units or (len(needle) >= LEAK_CONTAINS_MIN_CHARS and needle in hay):
                leaks.append(f"{f.id}: {p.text}")
    return leaks
