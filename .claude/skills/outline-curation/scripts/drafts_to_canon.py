#!/usr/bin/env python3
"""drafts_to_canon：把九架 `runs/outline-20260920/drafts-<X>.json` 決定性生成為新正本
（計畫 9.10 S3；DSP-067 程式面）。

- 輸入：`--drafts-dir` 下的 `drafts-A.json`…`drafts-I.json`（每架一份，`coarses[].fines[]`）；
  `--coarse-ids` 粗目 id 凍結表（`inputs/coarse-ids-20260921.md`）；`--front-matter-from`
  （既有 `canon/jgb/<X>.md`，只取 `coarse`／`title`／`scope`／`reviewers`／`language` 六鍵中的五鍵，
  `version` 另寫死 `GEN_VERSION`）。
- 輸出：`<--canon-root>/jgb/A.md…I.md`＋`CATALOG.md`（`export_catalog`）＋`<--canon-root>/jgb.json`
  （`export_json`）；`load_canon_or_die` 三源逐位元組核對。⛔ 不自己組 JSON／CATALOG，
  一律呼叫 `canon_parser`／`canon_assembler` 的既有函式。
- 另輸出 `dsp-068-deletions-<日期>.json`（標點例外的刪除清單）與
  `open-questions-<日期>.md`（`open_questions` 彙整，⛔ 不進正本）。

**DSP-068 標點例外**（見 `inputs/dsp-068-punctuation-lines-20260923.md`）：細目內容行中，
落在成對 `「」`／`『』`／`（）` 深度內、且緊接右括號前的終止符（`。！!？?`），寫入正本時刪去
（標籤主體逐字不變）。⛔ 只動內容行；標題／`phrasings`／屬性行一字不動。

決定性：同輸入兩次跑 `generate` 逐位元組相同（無時間戳；粗目依 drafts 出現順序、
細目依 drafts 出現順序，皆非重排）。

用法：
  python3 drafts_to_canon.py generate --drafts-dir <dir> --coarse-ids <凍結表.md> \\
      --front-matter-from <既有 canon/jgb 目錄> --canon-root <輸出 canon 目錄> \\
      --runs-out <runs/outline-20260920 目錄> --date 20260923 \\
      [--expect-deletion-lines 23 --expect-deletion-chars 27 --expect-open-questions 81] \\
      [--expect-reviewed-kept 62]
  python3 drafts_to_canon.py --self-test

**已審保留**（Plan 9.16 S1）：`--front-matter-from` 裡舊正本的 `- reviewed:` 行，若新生成的同 id
細目內容指紋（見 `fine_blocks`）相同，原樣寫回 `- sources:` 之後；不同或細目已刪 ⇒ 不寫回，列入
`<--runs-out>/reviewed-dropped-<日期>.json`（內容一改就要重審）。`--expect-reviewed-kept` 不符即停，
且此比對發生在寫任何檔之前。

`--expect-*`（選填）：與 `inputs/dsp-068-punctuation-lines-20260923.md`／drafts 語料實算比對，
不符即停；**省略時只印出實算數、不比對**——unit 測試用合成小語料，數字本就對不上凍結清單，
真跑九架 drafts 時才帶上這三個旗標核對。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for _cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(_cand, "services")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from services.agent.canon.canon_parser import (  # noqa: E402
        SHELF_FILES, CanonFormatError, export_catalog, export_json, parse_canon_dir,
    )
    from services.agent.provenance_units import split_sentences  # noqa: E402
except ImportError as exc:  # pragma: no cover
    print(f"[drafts_to_canon] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise

SHELVES: tuple[str, ...] = tuple("ABCDEFGHI")
GEN_VERSION = "2026-09-21.0"
PHRASING_SOURCE = "draft:outline-20260920"

OPEN_BRACKETS: dict = {"「": "」", "『": "』", "（": "）"}
CLOSE_BRACKETS: dict = {v: k for k, v in OPEN_BRACKETS.items()}
TERMINATORS = set("。！!？?")

_COARSE_ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*([A-Z])\s*\|\s*(.+?)\s*\|\s*`([A-Za-z0-9-]+)`\s*\|\s*\d+\s*\|$")


class GenerationError(SystemExit):
    """本檔的大聲失敗：訊息一律以「❌」開頭。⛔ 不吞、⛔ 不回退。"""

    def __init__(self, msg: str):
        super().__init__(f"❌ {msg}")


# ---------------------------------------------------------------------------
# 小工具：DSP-068 標點例外
# ---------------------------------------------------------------------------

def find_deletions(s: str) -> list[tuple[int, str]]:
    """`inputs/dsp-068-punctuation-lines-20260923.md` 的重跑法：逐字元掃、成對括號計深度，
    深度 >0 且該字元為終止符、且下一字元為右括號者，記下 (位移, 字元)。⛔ 不動 `s` 本身。"""
    dels: list[tuple[int, str]] = []
    stack: list[str] = []
    n = len(s)
    for i, ch in enumerate(s):
        if ch in OPEN_BRACKETS:
            stack.append(ch)
        elif ch in CLOSE_BRACKETS:
            if stack and stack[-1] == CLOSE_BRACKETS[ch]:
                stack.pop()
        if stack and ch in TERMINATORS and i + 1 < n and s[i + 1] in CLOSE_BRACKETS:
            dels.append((i, ch))
    return dels


def apply_deletions(s: str, dels: list[tuple[int, str]]) -> str:
    drop = {i for i, _ in dels}
    return "".join(ch for i, ch in enumerate(s) if i not in drop)


def is_balanced(line: str) -> bool:
    """`「」`／`『』`／`（）` 是否成對——純判定，⛔ 不在此拋例外（呼叫端要蒐集**全部**違規
    細目才一次報，見 `check_all_balanced`：驗收要求「兩條都沒做步驟 0」時兩個細目 id 都要點名，
    逐句 raise 只會報出第一個就中止）。"""
    stack: list[str] = []
    for ch in line:
        if ch in OPEN_BRACKETS:
            stack.append(ch)
        elif ch in CLOSE_BRACKETS:
            if not stack or stack[-1] != CLOSE_BRACKETS[ch]:
                return False
            stack.pop()
    return not stack


def check_all_balanced(violations: list[tuple[str, str]]) -> None:
    """引號平衡守門（無條件大聲失敗）：`violations`＝`[(fine_id, line), …]`（產出順序）。
    非空 ⇒ 中止並點名**所有**違規細目 id（去重、保序）＋各自第一個違規行。"""
    if not violations:
        return
    by_fine: dict = {}
    for fid, line in violations:
        by_fine.setdefault(fid, line)
    names = ", ".join(f"{fid}（{line!r}）" for fid, line in by_fine.items())
    raise GenerationError(f"生成的內容行引號不成對，共 {len(by_fine)} 條細目：{names}")


def sentence_to_lines(sentence: str, fine_id: str, sentence_index: int) -> tuple[list[str], list[dict], list[tuple[str, str]]]:
    """一條 draft 句子 ⇒ (內容行清單, 本句的刪除清單, 引號不平衡違規清單)。刪除先於切句
    ——刪掉會觸發切句的終止符，`split_sentences` 才不會在標籤中間斷開。"""
    s = sentence.rstrip()
    dels = find_deletions(s)
    modified = apply_deletions(s, dels) if dels else s
    pieces = [p.strip() for p in split_sentences(modified) if p.strip() != ""]
    if not pieces:
        raise GenerationError(f"細目 {fine_id} 第 {sentence_index} 句刪除後變空：{sentence!r}")
    violations: list[tuple[str, str]] = []
    for piece in pieces:
        if len(split_sentences(piece)) != 1:
            raise GenerationError(
                f"細目 {fine_id} 第 {sentence_index} 句刪除後仍可再切出多句（大聲失敗）：{piece!r}"
            )
        if not is_balanced(piece):
            violations.append((fine_id, piece))
    manifest = [
        {"fine_id": fine_id, "sentence_index": sentence_index, "offset": off, "char": ch}
        for off, ch in dels
    ]
    return pieces, manifest, violations


# ---------------------------------------------------------------------------
# 粗目 id 凍結表
# ---------------------------------------------------------------------------

def strip_arrow_suffix(title: str) -> str:
    idx = title.find("⇄")
    return title if idx == -1 else title[:idx].rstrip()


def load_coarse_table(path: str) -> dict:
    table: dict = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = _COARSE_ROW_RE.match(line.rstrip("\n"))
            if not m:
                continue
            shelf, title, cid = m.group(1), m.group(2), m.group(3)
            table[(shelf, title)] = cid
    return table


def lookup_coarse_id(table: dict, shelf: str, raw_title: str) -> str:
    title = strip_arrow_suffix(raw_title)
    key = (shelf, title)
    if key not in table:
        raise GenerationError(f"粗目標題查表落空（架 {shelf}）：{title!r}")
    return table[key]


# ---------------------------------------------------------------------------
# 架 front matter（沿用現行 canon/jgb/<X>.md 的五鍵；version 另寫死）
# ---------------------------------------------------------------------------

_FM_KEYS = ("coarse", "title", "scope", "reviewers", "language")


def load_shelf_front_matter(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    if not lines or lines[0].strip() != "---":
        raise GenerationError(f"{path}：缺 front matter（首行須為 ---）")
    fm: dict = {}
    idx = 1
    while idx < len(lines) and lines[idx].strip() != "---":
        line = lines[idx]
        if line.strip():
            if ":" not in line:
                raise GenerationError(f"{path} 第 {idx + 1} 行：front matter 無法解析：{line!r}")
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
        idx += 1
    missing = [k for k in _FM_KEYS if k not in fm]
    if missing:
        raise GenerationError(f"{path}：front matter 缺鍵 {missing}")
    return {k: fm[k] for k in _FM_KEYS}


# ---------------------------------------------------------------------------
# phrasings / 屬性行
# ---------------------------------------------------------------------------

def format_phrasing_line(text: str, fine_id: str) -> str:
    if '"' in text or "{" in text or "}" in text:
        raise GenerationError(f"細目 {fine_id} 的講法含 `\"`／`{{`／`}}`（大聲失敗）：{text!r}")
    return f'  - {{text: "{text}", source: "{PHRASING_SOURCE}", status: proposed}}'


def _nfkc(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s).split())


def _fmt_list(values: list[str]) -> str:
    return "[" + ", ".join(values) + "]"


# ---------------------------------------------------------------------------
# 生成單一細目 / 單一架
# ---------------------------------------------------------------------------

def build_fine_block(fine: dict, coarse_id: str) -> tuple[list[str], list[dict], list[str], list[tuple[str, str]]]:
    """回 (該細目的正本行清單, 本細目的 DSP-068 刪除清單, open_questions 清單, 引號不平衡違規清單)。"""
    fid = fine["proposed_id"]
    title = fine["title"]
    for key in ("sentences", "sources", "target_user", "business_types", "instance_applicability"):
        if key not in fine or (key != "instance_applicability" and not fine[key]):
            raise GenerationError(f"細目 {fid} 缺必填欄位 {key!r}")

    lines = [f"### {title} {{#{fid}}}"]
    if fine.get("phrasings"):
        lines.append("- phrasings:")
        for p in fine["phrasings"]:
            lines.append(format_phrasing_line(p, fid))
    lines.append(f"- sources: {_fmt_list(fine['sources'])}")
    lines.append(f"- target_user: {_fmt_list(fine['target_user'])}")
    lines.append(f"- business_types: {_fmt_list(fine['business_types'])}")
    lines.append(f"- instance_applicability: {fine['instance_applicability']}")

    manifest: list[dict] = []
    violations: list[tuple[str, str]] = []
    for si, sentence in enumerate(fine["sentences"]):
        pieces, dels, viol = sentence_to_lines(sentence, fid, si)
        lines.extend(pieces)
        manifest.extend(dels)
        violations.extend(viol)

    open_qs = [{"fine_id": fid, "question": q} for q in fine.get("open_questions", [])]
    return lines, manifest, open_qs, violations


def build_shelf_text(
    shelf: str, draft: dict, fm: dict, coarse_table: dict,
) -> tuple[str, list[dict], list[dict], list[tuple[str, str]]]:
    out = [
        "---",
        f"coarse: {fm['coarse']}",
        f"title: {fm['title']}",
        f"scope: {fm['scope']}",
        f"version: {GEN_VERSION}",
        f"reviewers: {fm['reviewers']}",
        f"language: {fm['language']}",
        "---",
    ]
    manifest: list[dict] = []
    open_qs: list[dict] = []
    violations: list[tuple[str, str]] = []
    for coarse in draft["coarses"]:
        cid = lookup_coarse_id(coarse_table, shelf, coarse["coarse"])
        ctitle = strip_arrow_suffix(coarse["coarse"])
        out.append(f"## {ctitle} {{#{cid}}}")
        for fine in coarse["fines"]:
            flines, fmanifest, foq, fviol = build_fine_block(fine, cid)
            out.extend(flines)
            manifest.extend(fmanifest)
            open_qs.extend(foq)
            violations.extend(fviol)
    return "\n".join(out) + "\n", manifest, open_qs, violations


# ---------------------------------------------------------------------------
# 已審保留（Plan 9.16 S1）：重生成不得抹掉業主已審標記，但內容一改就要重審
# ---------------------------------------------------------------------------

_FINE_HEAD_RE = re.compile(r"^### .*\{#([^}]+)\}$")
REVIEWED_PREFIX = "- reviewed:"
SOURCES_PREFIX = "- sources:"


def fine_blocks(text: str) -> dict:
    """架全文 ⇒ `{fine_id: (內容指紋, reviewed 原行或 None)}`。

    內容指紋＝細目區塊（`### 標題 {#id}` 起、到下一個 `###`／`##` 止）去掉 `- phrasings:`、
    講法子項（兩格縮排 `  - {…}`）與 `- reviewed:` 行後的 sha256——即標題＋句子＋`sources`＋
    `target_user`＋`business_types`＋`instance_applicability`。新舊兩側都走本函式，比對才一致。"""
    out: dict = {}
    fid: Optional[str] = None
    kept_lines: list[str] = []
    reviewed: Optional[str] = None

    def _close() -> None:
        if fid is not None:
            digest = hashlib.sha256("\n".join(kept_lines).encode("utf-8")).hexdigest()
            out[fid] = (digest, reviewed)

    for line in text.split("\n"):
        m = _FINE_HEAD_RE.match(line)
        if m or line.startswith("## "):
            _close()
            fid, kept_lines, reviewed = (m.group(1), [line], None) if m else (None, [], None)
            continue
        if fid is None:
            continue
        if line.startswith(REVIEWED_PREFIX):
            reviewed = line
        elif line == "- phrasings:" or line.startswith("  - "):
            continue
        elif line != "":
            kept_lines.append(line)
    _close()
    return out


def carry_reviewed(old_texts: dict, new_texts: dict) -> tuple[dict, list[str], list[dict]]:
    """把舊正本的 `reviewed` 行寫回新全文（內容指紋相同者，寫在 `- sources:` 之後）。
    回 (寫回後的新全文, 保留的細目 id, 丟棄清單)。純記憶體運算，⛔ 不寫檔。"""
    old_reviewed: dict = {}
    for shelf, text in old_texts.items():
        for fid, (digest, rline) in fine_blocks(text).items():
            if rline is not None:
                old_reviewed[fid] = (shelf, digest, rline)
    new_blocks: dict = {}
    for shelf, text in new_texts.items():
        for fid, (digest, _r) in fine_blocks(text).items():
            new_blocks[fid] = digest

    keep = {fid: v[2] for fid, v in old_reviewed.items() if new_blocks.get(fid) == v[1]}
    dropped = [
        {"fine_id": fid, "shelf": shelf, "reviewed": rline,
         "reason": "fine_removed" if fid not in new_blocks else "content_changed"}
        for fid, (shelf, digest, rline) in old_reviewed.items() if fid not in keep
    ]

    out_texts: dict = {}
    written: list[str] = []
    for shelf, text in new_texts.items():
        lines = text.split("\n")
        result: list[str] = []
        fid: Optional[str] = None
        for line in lines:
            m = _FINE_HEAD_RE.match(line)
            if m:
                fid = m.group(1)
            elif line.startswith("## "):
                fid = None
            result.append(line)
            if fid in keep and line.startswith(SOURCES_PREFIX):
                result.append(keep[fid])
                written.append(fid)
        out_texts[shelf] = "\n".join(result)
    missing = sorted(set(keep) - set(written))
    if missing or len(written) != len(set(written)):
        raise GenerationError(f"已審寫回失準：應寫 {len(keep)}、實寫 {len(written)}；缺 `- sources:` 的細目 {missing[:5]}")
    return out_texts, written, dropped


_PHRASING_LINE_RE = re.compile(r'^  - \{text: "(.*)", source: ".*", status: (\w+)\}$')


def carry_phrasing_approved(old_texts: dict, new_texts: dict) -> tuple[dict, int]:
    """把舊正本已 `approved` 的講法狀態寫回新全文（同細目、同句）。
    草稿沒有講法狀態，`format_phrasing_line` 一律產 `proposed`；不寫回的話，重新生成會把
    已核可講法（DSP-129）靜默打回 `proposed`、踢出索引。回 (寫回後的新全文, 寫回條數)。"""
    approved: set = set()
    for text in old_texts.values():
        fid: Optional[str] = None
        for line in text.split("\n"):
            m = _FINE_HEAD_RE.match(line)
            if m:
                fid = m.group(1)
            elif line.startswith("## "):
                fid = None
            else:
                p = _PHRASING_LINE_RE.match(line)
                if p and fid is not None and p.group(2) == "approved":
                    approved.add((fid, p.group(1)))

    out_texts: dict = {}
    n = 0
    for shelf, text in new_texts.items():
        result: list[str] = []
        fid = None
        for line in text.split("\n"):
            m = _FINE_HEAD_RE.match(line)
            if m:
                fid = m.group(1)
            elif line.startswith("## "):
                fid = None
            else:
                p = _PHRASING_LINE_RE.match(line)
                if p and p.group(2) == "proposed" and (fid, p.group(1)) in approved:
                    line = line[: -len("status: proposed}")] + "status: approved}"
                    n += 1
            result.append(line)
        out_texts[shelf] = "\n".join(result)
    return out_texts, n


# ---------------------------------------------------------------------------
# 跨架前置檢查（在寫任何檔案之前）
# ---------------------------------------------------------------------------

def check_cross_shelf(drafts: dict) -> tuple[int, int]:
    """回 (重複細目 id 數, 重複講法數)——**兩者都印出，即使是 0**（缺印＝檢查沒跑）。
    任一 >0 ⇒ 大聲失敗並列出前幾筆。"""
    seen_ids: dict = {}
    dup_ids: list[tuple[str, str, str]] = []
    seen_phr: dict = {}
    dup_phr: list[tuple[str, str, str]] = []
    for shelf in SHELVES:
        draft = drafts[shelf]
        for coarse in draft["coarses"]:
            for fine in coarse["fines"]:
                fid = fine["proposed_id"]
                if fid in seen_ids:
                    dup_ids.append((fid, seen_ids[fid], shelf))
                else:
                    seen_ids[fid] = shelf
                for p in fine.get("phrasings", []):
                    key = _nfkc(p)
                    if not key:
                        continue
                    if key in seen_phr and seen_phr[key] != fid:
                        dup_phr.append((p, seen_phr[key], fid))
                    else:
                        seen_phr.setdefault(key, fid)
    print(f"[drafts_to_canon] 跨架重複細目 id：{len(dup_ids)}")
    print(f"[drafts_to_canon] 跨架重複講法（NFKC）：{len(dup_phr)}")
    if dup_ids:
        raise GenerationError(f"細目 id 跨架重複 {len(dup_ids)} 筆：{dup_ids[:5]}")
    if dup_phr:
        raise GenerationError(f"講法跨細目重複 {len(dup_phr)} 筆：{dup_phr[:5]}")
    return len(dup_ids), len(dup_phr)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def load_drafts(drafts_dir: str) -> dict:
    drafts: dict = {}
    for shelf in SHELVES:
        path = os.path.join(drafts_dir, f"drafts-{shelf}.json")
        if not os.path.isfile(path):
            raise GenerationError(f"缺架 drafts：{path}")
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("shelf") != shelf:
            raise GenerationError(f"{path}：shelf 欄 {d.get('shelf')!r} 與檔名字母 {shelf!r} 不符")
        drafts[shelf] = d
    return drafts


def generate(
    drafts_dir: str, coarse_ids_path: str, front_matter_from: str, canon_root: str,
    runs_out: str, date_str: str,
    expect_deletion_lines: Optional[int] = None, expect_deletion_chars: Optional[int] = None,
    expect_open_questions: Optional[int] = None, expect_reviewed_kept: Optional[int] = None,
) -> None:
    drafts = load_drafts(drafts_dir)
    coarse_table = load_coarse_table(coarse_ids_path)
    print(f"[drafts_to_canon] 粗目 id 凍結表列數：{len(coarse_table)}")

    check_cross_shelf(drafts)

    shelf_dir = os.path.join(canon_root, "jgb")

    # 先在記憶體建好九架全文（⛔ 不邊建邊寫）——引號平衡守門要蒐集**全九架**的違規後才能一次
    # 點名所有細目 id；沒蒐集完就先落地，步驟 0 沒做時只會報出第一條就中止（驗收要求兩條都點名）。
    shelf_texts: dict[str, str] = {}
    old_texts: dict[str, str] = {}
    all_manifest: list[dict] = []
    all_open_qs: list[dict] = []
    all_violations: list[tuple[str, str]] = []
    for shelf in SHELVES:
        fm_path = os.path.join(front_matter_from, f"{shelf}.md")
        fm = load_shelf_front_matter(fm_path)
        with open(fm_path, encoding="utf-8") as fh:
            old_texts[shelf] = fh.read()
        text, manifest, open_qs, violations = build_shelf_text(shelf, drafts[shelf], fm, coarse_table)
        shelf_texts[shelf] = text
        all_manifest.extend(manifest)
        all_open_qs.extend(open_qs)
        all_violations.extend(violations)

    check_all_balanced(all_violations)

    # 已審保留（Plan 9.16 S1）：計算與 --expect-reviewed-kept 比對都在**寫任何檔之前**——
    # ⛔ 別挪到下面寫檔之後（下方其他數字是先寫後核；比對失敗時舊正本的已審標記會已被覆寫）。
    shelf_texts, kept, dropped = carry_reviewed(old_texts, shelf_texts)
    print(f"[drafts_to_canon] 已審保留：{len(kept)} 條／丟棄：{len(dropped)} 條")
    for d in dropped:
        print(f"[drafts_to_canon]   丟棄 {d['fine_id']}（{d['reason']}）")
    if expect_reviewed_kept is not None and len(kept) != expect_reviewed_kept:
        raise GenerationError(
            f"已審保留 {len(kept)} 條，與預期 {expect_reviewed_kept} 條不符（丟棄 {len(dropped)} 條）；未寫任何檔"
        )
    shelf_texts, n_phrasing = carry_phrasing_approved(old_texts, shelf_texts)
    print(f"[drafts_to_canon] 講法 approved 保留：{n_phrasing} 條")

    os.makedirs(runs_out, exist_ok=True)
    dropped_path = os.path.join(runs_out, f"reviewed-dropped-{date_str}.json")
    with open(dropped_path, "w", encoding="utf-8") as fh:
        json.dump(dropped, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")

    os.makedirs(shelf_dir, exist_ok=True)
    for shelf, text in shelf_texts.items():
        with open(os.path.join(shelf_dir, f"{shelf}.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    # 刪除清單數量核對（--expect-* 省略時只印出實算數；真跑九架 drafts 要帶上核對凍結清單）
    n_lines = len({(m["fine_id"], m["sentence_index"]) for m in all_manifest})
    n_chars = len(all_manifest)
    print(f"[drafts_to_canon] DSP-068 刪除清單實算：{n_lines} 行／{n_chars} 字元")
    if expect_deletion_lines is not None and (n_lines, n_chars) != (expect_deletion_lines, expect_deletion_chars):
        raise GenerationError(
            f"DSP-068 刪除清單實算 {n_lines} 行／{n_chars} 字元，"
            f"與凍結清單 {expect_deletion_lines} 行／{expect_deletion_chars} 字元不符"
        )

    os.makedirs(runs_out, exist_ok=True)
    deletions_path = os.path.join(runs_out, f"dsp-068-deletions-{date_str}.json")
    with open(deletions_path, "w", encoding="utf-8") as fh:
        json.dump(all_manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"[drafts_to_canon] open_questions 實算：{len(all_open_qs)} 則")
    if expect_open_questions is not None and len(all_open_qs) != expect_open_questions:
        raise GenerationError(
            f"open_questions 實算 {len(all_open_qs)} 則，與預期 {expect_open_questions} 則不符"
        )
    oq_path = os.path.join(runs_out, f"open-questions-{date_str}.md")
    with open(oq_path, "w", encoding="utf-8") as fh:
        fh.write(f"# 待裁問題彙整（{date_str}，共 {len(all_open_qs)} 則；⛔ 不進正本）\n\n")
        for i, oq in enumerate(all_open_qs, 1):
            fh.write(f"{i}. `{oq['fine_id']}`：{oq['question']}\n")

    # 產出順序：parse_canon_dir → export_json → export_catalog → load_canon_or_die 三源比對
    try:
        doc = parse_canon_dir(shelf_dir)
    except CanonFormatError as exc:
        raise GenerationError(f"生成物 parse_canon_dir 失敗：{exc}") from exc

    json_path = os.path.join(canon_root, "jgb.json")
    export_json(doc, json_path)
    catalog_path = os.path.join(shelf_dir, "CATALOG.md")
    export_catalog(doc, catalog_path)

    from services.agent.canon.canon_assembler import CanonLoadError, load_canon_or_die  # noqa: E402
    try:
        load_canon_or_die(canon_root)
    except CanonLoadError as exc:
        raise GenerationError(f"load_canon_or_die 三源比對失敗：{exc}") from exc

    print(
        f"[drafts_to_canon] 完成：{len(doc.coarses)} 粗目／{len(doc.fines())} 細目／"
        f"刪除 {n_lines} 行 {n_chars} 字元／open_questions {len(all_open_qs)} 則"
    )


# ---------------------------------------------------------------------------
# self-test（正對照 6、指定負對照 3：(a)(b)(c)）
# ---------------------------------------------------------------------------

def self_test() -> int:
    fails: list[str] = []

    # (a) 標籤結尾終止符被刪後落成一行、且刪的只有那一個字元
    s = "登入頁「還沒有帳號嗎？」旁的連結。"
    pieces, dels, viol = sentence_to_lines(s, "jgb/X/probe", 0)
    if len(pieces) != 1 or len(dels) != 1 or dels[0]["char"] != "？" or viol:
        fails.append(f"(a) 標籤結尾終止符刪除失準：pieces={pieces} dels={dels}")

    # P2：多句切成多行（引號外的終止符仍照常切）
    s2 = "第一步做這個。第二步做那個。"
    pieces2, dels2, viol2 = sentence_to_lines(s2, "jgb/X/probe2", 0)
    if pieces2 != ["第一步做這個。", "第二步做那個。"] or dels2 or viol2:
        fails.append(f"P2 多句切行失準：{pieces2}")

    # P3：粗目 id 凍結表查表成功（去 ⇄ 後綴）
    tmp_table_text = (
        "| # | 架 | 粗目標題 | 粗目 id | 細目數 |\n"
        "|---|---|---|---|---|\n"
        "| 1 | A | 測試粗目 | `A-probe` | 1 |\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(tmp_table_text)
        table_path = fh.name
    try:
        table = load_coarse_table(table_path)
        cid = lookup_coarse_id(table, "A", "測試粗目 ⇄ 由 B 移入")
        if cid != "A-probe":
            fails.append(f"P3 粗目查表（去 ⇄ 後綴）失準：{cid!r}")
    finally:
        os.unlink(table_path)

    # P4：phrasing 正常格式化
    line = format_phrasing_line("正常講法", "jgb/X/probe")
    if line != '  - {text: "正常講法", source: "draft:outline-20260920", status: proposed}':
        fails.append(f"P4 phrasing 格式化失準：{line!r}")

    # P4b：同細目同句的 approved 寫回；別細目同句、新講法維持 proposed（負對照）
    old_phr = {"X": '### t {#jgb/X/a}\n  - {text: "甲", source: "s", status: approved}\n'
                    '### t {#jgb/X/b}\n  - {text: "乙", source: "s", status: proposed}\n'}
    new_phr = {"X": '### t {#jgb/X/a}\n  - {text: "甲", source: "s", status: proposed}\n'
                    '  - {text: "新句", source: "s", status: proposed}\n'
                    '### t {#jgb/X/b}\n  - {text: "甲", source: "s", status: proposed}\n'}
    carried, n_carried = carry_phrasing_approved(old_phr, new_phr)
    if n_carried != 1 or carried["X"].count("status: approved}") != 1 or \
            '  - {text: "甲", source: "s", status: approved}\n  - {text: "新句"' not in carried["X"]:
        fails.append(f"P4b 講法 approved 寫回失準：n={n_carried}")

    # P5：跨架前置檢查在乾淨輸入下回 (0, 0) 且印出兩個計數（正對照，證明檢查有跑）
    clean_drafts = {
        sh: {"shelf": sh, "coarses": [{"coarse": f"粗目{sh}", "fines": [
            {"proposed_id": f"jgb/{sh}/only", "title": "t", "phrasings": ["獨有講法" + sh],
             "sentences": ["內容。"], "sources": ["s"], "target_user": ["prospect"],
             "business_types": ["system_provider"], "instance_applicability": "general",
             "open_questions": []},
        ]}]}
        for sh in SHELVES
    }
    n_id, n_phr = check_cross_shelf(clean_drafts)
    if (n_id, n_phr) != (0, 0):
        fails.append(f"P5 跨架前置檢查誤判：{(n_id, n_phr)}")

    # P6：引號平衡守門對合法內容行放行、不誤傷正常括號句
    if not is_balanced("正常的（帶括號）內容行。"):
        fails.append("P6 引號平衡守門誤殺合法行")

    # (b) 粗目標題查表落空 ⇒ 大聲失敗且訊息印出該標題
    try:
        lookup_coarse_id({}, "A", "查無此粗目")
        fails.append("(b) 粗目標題查表落空沒有大聲失敗")
    except SystemExit as exc:
        if "查無此粗目" not in str(exc):
            fails.append(f"(b) 失敗訊息未印出標題：{exc}")

    # (c) 講法含 `"` ⇒ 大聲失敗
    try:
        format_phrasing_line('含 " 的講法', "jgb/X/probe")
        fails.append('(c) 講法含 " 沒有大聲失敗')
    except SystemExit:
        pass

    # 負對照：跨架重複細目 id / 講法 ⇒ 大聲失敗
    dup_drafts = {
        sh: {"shelf": sh, "coarses": [{"coarse": f"粗目{sh}", "fines": [
            {"proposed_id": "jgb/A/dup", "title": "t", "phrasings": ["同一句講法"],
             "sentences": ["內容。"], "sources": ["s"], "target_user": ["prospect"],
             "business_types": ["system_provider"], "instance_applicability": "general",
             "open_questions": []},
        ]}]}
        for sh in SHELVES
    }
    try:
        check_cross_shelf(dup_drafts)
        fails.append("負對照：跨架重複細目 id 沒有大聲失敗")
    except SystemExit:
        pass

    # 引號不平衡 ⇒ 大聲失敗（無條件守門）
    if is_balanced("缺右括號的「內容。"):
        fails.append("引號不平衡沒有被判定失衡")

    # 負對照：兩條細目都不平衡 ⇒ check_all_balanced 一次點名兩者（步驟 0 未做的負對照場景）
    try:
        check_all_balanced([
            ("jgb/A/login-no-account-register-link", "尚未註冊的使用者也可從登入頁「還沒有帳號嗎？"),
            ("jgb/C/forcebinding-completion-states", "當所有物件都綁定完成時，畫面會顯示「恭喜！"),
        ])
        fails.append("check_all_balanced 對兩條違規細目沒有大聲失敗")
    except SystemExit as exc:
        msg = str(exc)
        if "jgb/A/login-no-account-register-link" not in msg or "jgb/C/forcebinding-completion-states" not in msg:
            fails.append(f"check_all_balanced 訊息未點名兩條細目：{msg}")

    for f in fails:
        print("❌ self-test:", f)
    if not fails:
        print("✅ self-test 通過（正對照 6、指定負對照 3｜(a)(b)(c)，另加 2 條額外負對照）")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    gp = sub.add_parser("generate")
    gp.add_argument("--drafts-dir", required=True)
    gp.add_argument("--coarse-ids", required=True)
    gp.add_argument("--front-matter-from", required=True)
    gp.add_argument("--canon-root", required=True)
    gp.add_argument("--runs-out", required=True)
    gp.add_argument("--date", required=True)
    gp.add_argument("--expect-deletion-lines", type=int, default=None)
    gp.add_argument("--expect-deletion-chars", type=int, default=None)
    gp.add_argument("--expect-open-questions", type=int, default=None)
    gp.add_argument("--expect-reviewed-kept", type=int, default=None)
    a = ap.parse_args()
    if a.cmd == "generate":
        if (a.expect_deletion_lines is None) != (a.expect_deletion_chars is None):
            raise GenerationError("--expect-deletion-lines 與 --expect-deletion-chars 須成對提供")
        generate(
            a.drafts_dir, a.coarse_ids, a.front_matter_from, a.canon_root, a.runs_out, a.date,
            expect_deletion_lines=a.expect_deletion_lines, expect_deletion_chars=a.expect_deletion_chars,
            expect_open_questions=a.expect_open_questions, expect_reviewed_kept=a.expect_reviewed_kept,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
