"""正本格式與解析（spec knowledge-outline-and-intent-architecture 元件 4；任務 2.1）。

Markdown 正本（`rag-orchestrator/canon/<audience>.md`）→ `CanonDoc`（決定性、附 `canon_sha256`）；`export_json` 單向導出。

格式（design 元件 4）：
- front matter 七鍵：`audience, version, reviewers, language, budget_tokens, target_user, business_types`。
- 粗目＝`## 標題 {#X}`（X 為單一大寫字母）；細目＝`### 標題 {#<audience>/<X>/<slug>}`，id 正則 `^[a-z_]+/[A-Z]/[a-z0-9-]+$`。
- 細目屬性區塊＝細目標題後連續的 `- key:` 行（鍵限 ATTR_KEYS）＋ `phrasings` 的 `  - {text: …, source: …, status: …}` 子項。
- 屬性區塊之後每一非空行＝一個內容句（`content_units`），與 `provenance_units.split_sentences` 切法恆等（一行不得含多句）。

嚴格性（F8）：**屬性區塊內任何無法解析的行一律 `CanonFormatError`（列號＋原因），⛔ 不落 `content_units`**——否則講法（含去識別後的真流量）會進 system prompt 成可引用句。
講法規則：`source: traffic:*` 的講法 ≤20 字且不含 ≥4 位數字串（去識別後仍不得帶識別碼形狀）。

與 hook `.claude/hooks/outline_gate.py::check_structure` 的關係：hook 是編輯時的粗篩（PostToolUse），本檔是唯一的完整解析；
兩者的鍵清單與正則刻意同值（tests 守）。
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Optional

from services.agent.provenance_units import split_sentences

FRONT_MATTER_KEYS: tuple[str, ...] = (
    "audience", "version", "reviewers", "language", "budget_tokens", "target_user", "business_types",
)
AUDIENCES: tuple[str, ...] = ("prospect", "property_manager", "tenant")
ATTR_KEYS: tuple[str, ...] = (
    "phrasings", "sources", "reviewed", "see_also", "policy", "policy_ref",
    "target_user", "business_types", "categories", "instance_applicability",
)
POLICIES: tuple[str, ...] = ("answerable", "deliberate_no", "not_available")
PHRASING_STATUSES: tuple[str, ...] = ("proposed", "approved", "retired")
INSTANCE_APPLICABILITY: tuple[str, ...] = ("instance", "general")

FINE_ID_RE = re.compile(r"^[a-z_]+/[A-Z]/[a-z0-9-]+$")
COARSE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*\{#([A-Z])\}\s*$")
FINE_HEADING_RE = re.compile(r"^###\s+(.+?)\s*\{#([^}]+)\}\s*$")
ATTR_LINE_RE = re.compile(r"^-\s*([a-zA-Z_]+)\s*:\s*(.*)$")
CONTINUATION_RE = re.compile(r"^\s+-\s+(.*)$")
PHRASING_ITEM_RE = re.compile(
    r'^\{\s*text\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*source\s*:\s*"([^"]+)"\s*,\s*status\s*:\s*([a-z]+)\s*\}$'
)
REVIEWED_RE = re.compile(r"^\{\s*by\s*:\s*([A-Za-z0-9_.@-]+)\s*,\s*at\s*:\s*(\d{4}-\d{2}-\d{2})\s*\}$")
LIST_RE = re.compile(r"^\[(.*)\]$")
TRAFFIC_DIGITS_RE = re.compile(r"\d{4,}")
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

    def fines(self) -> tuple[FineItem, ...]:
        return tuple(f for c in self.coarses for f in c.fines)


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------

def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip()


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
                doc_defaults: dict) -> FineItem:
    phr = tuple(attrs.get("phrasings", ()))
    policy = attrs.get("policy", "answerable")
    if "instance_applicability" not in attrs:
        raise CanonFormatError(head_lineno, f"細目 {fid} 缺必填屬性 instance_applicability（instance｜general）")
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
        instance_applicability=attrs["instance_applicability"],
    )


def _parse_attr_value(key: str, raw: str, lineno: int):
    if key in ("sources", "see_also", "target_user", "business_types", "categories"):
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
    if key == "instance_applicability":
        v = _parse_scalar(raw, lineno, "instance_applicability")
        if v not in INSTANCE_APPLICABILITY:
            raise CanonFormatError(lineno, f"instance_applicability 須為 {INSTANCE_APPLICABILITY} 之一，得到 {v!r}")
        return v
    raise CanonFormatError(lineno, f"屬性 {key!r} 不支援")  # pragma: no cover — 上游已擋


def parse_canon_text(text: str, source_path: Optional[str] = None) -> CanonDoc:
    """解析正本全文（決定性）。任何格式錯 ⇒ CanonFormatError（列號＋原因）。"""
    canon_sha = _sha256_text(text)
    lines = text.split("\n")
    fm, body_start = _parse_front_matter(lines)
    defaults = {"target_user": fm["target_user"], "business_types": fm["business_types"]}

    coarses: list[CoarseItem] = []
    fines_of_current: list[FineItem] = []
    current_coarse: Optional[tuple[str, str]] = None  # (id, title)
    seen_coarse: set[str] = set()
    seen_fine: dict[str, int] = {}

    # 細目狀態機
    fine_open = False
    fine_head_lineno = 0
    fine_id = ""
    fine_title = ""
    attrs: dict = {}
    content: list[str] = []
    in_attr_block = False        # 尚未出現內容行（屬性區塊仍可延伸）
    open_list_key: Optional[str] = None  # phrasings 子項延續中

    def close_fine():
        nonlocal fine_open, attrs, content, in_attr_block, open_list_key
        if fine_open:
            fines_of_current.append(_build_fine(fine_head_lineno, fine_id, current_coarse[0], fine_title, attrs, content, defaults))
        fine_open = False
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

        cm = COARSE_HEADING_RE.match(line)
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
            if aud != fm["audience"]:
                raise CanonFormatError(lineno, f"細目 id 受眾 {aud!r} 與 front matter audience {fm['audience']!r} 不符")
            if ccode != current_coarse[0]:
                raise CanonFormatError(lineno, f"細目 id 粗目碼 {ccode!r} 與所在粗目 {current_coarse[0]!r} 不符")
            if fid in seen_fine:
                raise CanonFormatError(lineno, f"細目 id 重複 {fid!r}（首見於第 {seen_fine[fid]} 行）")
            seen_fine[fid] = lineno
            fine_open, fine_head_lineno, fine_id, fine_title = True, lineno, fid, title
            in_attr_block = True
            continue

        if line.startswith("#"):
            raise CanonFormatError(lineno, f"標題行無法解析（粗目須 `## 標題 {{#X}}`、細目須 `### 標題 {{#id}}`）：{line.strip()!r}")

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
                continue
            if cont:
                if open_list_key != "phrasings":
                    raise CanonFormatError(lineno, f"縮排子項只允許在 phrasings 底下：{line.strip()!r}")
                attrs["phrasings"].append(_parse_phrasing_item(cont.group(1), lineno))
                continue
            if line.startswith("-") or line[0].isspace():
                raise CanonFormatError(lineno, f"屬性區塊內無法解析的行（⛔ 不落內容）：{line.strip()!r}")
            # 第一個內容行：屬性區塊結束
            in_attr_block = False
            open_list_key = None

        # 內容區
        if am or cont or line.startswith("-") or line[0].isspace():
            raise CanonFormatError(lineno, f"內容區出現屬性形狀的行（屬性須在內容之前）：{line.strip()!r}")
        unit = line.strip()
        if len(split_sentences(unit)) != 1:
            raise CanonFormatError(lineno, f"一行只能一句（provenance_units 切法恆等）：{unit!r}")
        content.append(unit)

    close_coarse()
    if not coarses:
        raise CanonFormatError(len(lines), "正本沒有任何粗目")

    approved = sorted((f.id, p.text) for c in coarses for f in c.fines for p in f.phrasings if p.status == "approved")
    phrasing_sha = _sha256_text(json.dumps(approved, ensure_ascii=False, separators=(",", ":")))
    return CanonDoc(
        audience=fm["audience"], version=fm["version"], reviewers=fm["reviewers"], language=fm["language"],
        budget_tokens=fm["budget_tokens"], target_user=fm["target_user"], business_types=fm["business_types"],
        coarses=tuple(coarses), canon_sha256=canon_sha, phrasing_set_sha256=phrasing_sha, source_path=source_path,
    )


def parse_canon(path: str) -> CanonDoc:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return parse_canon_text(text, source_path=path)


# ---------------------------------------------------------------------------
# 導出與守門
# ---------------------------------------------------------------------------

def to_dict(doc: CanonDoc) -> dict:
    d = asdict(doc)
    d.pop("source_path", None)
    return d


def export_json(doc: CanonDoc, out_path: str) -> str:
    """單向導出 JSON（鍵排序、UTF-8、結尾換行）；回 canon_sha256，JSON 內帶同一 sha。"""
    payload = json.dumps(to_dict(doc), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    return doc.canon_sha256


def content_text(doc: CanonDoc) -> str:
    """可引用內容全文（只含 content_units；⛔ 不含講法）——組 OutlineDoc.text 的唯一來源。"""
    return "\n".join(u for f in doc.fines() for u in f.content_units)


def phrasing_leaks(doc: CanonDoc, text: Optional[str] = None) -> list[str]:
    """守門：講法（NFKC）出現在可引用文字中 ⇒ 列出；空清單＝乾淨。text 省略時檢查 content_text(doc)。"""
    hay = _nfkc(text if text is not None else content_text(doc))
    leaks = []
    for f in doc.fines():
        for p in f.phrasings:
            needle = _nfkc(p.text)
            if needle and needle in hay:
                leaks.append(f"{f.id}: {p.text}")
    return leaks
