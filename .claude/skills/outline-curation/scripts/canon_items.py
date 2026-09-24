#!/usr/bin/env python3
"""共用：讀既有正本 Markdown → 候選項目清單／排除清單（knowledge-outline-and-intent-architecture 任務 9.3⑤「從既有正本重切」）。

供 `structure_propose.py prepare --canon`、`intake.py --canon`、`apply_proposal.py --canon` 共用。
⛔ 不用 regex 另寫解析——唯一解析器是 `services.agent.canon.canon_parser.parse_canon`／`parse_canon_dir`；
`parse_canon_auto` 依路徑是否為目錄二擇一（9.6 S4，供 `structure_propose.py`／`intake.py`／
`apply_proposal.py`／`answerability_args.py`／`canon_source_check.py` 共用，⛔ 各自判斷）。

候選 id 形狀與 `answerability_args.candidate_from_kb_row` 一致（`tmp:kb:<id>`），
讓既有正本細目的 `fine.id` 能直接當 `merge_of`／`id_map.old` 使用的 id 對齊。
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for _cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(_cand, "services")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from services.agent.canon.canon_parser import (  # noqa: E402
        CanonDoc, FineItem, SHELF_FILES, parse_canon, parse_canon_dir,
    )
except ImportError as exc:  # pragma: no cover
    print(f"[canon_items] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise SystemExit(2)

TMP_PREFIX = "tmp:kb:"
#: 擴充模式（brief-9.7）候選前綴：某架**既有**細目，與 `TMP_PREFIX`（新材料）區分。
TMP_CANON_PREFIX = "tmp:canon:"
#: 九架碼（字母序），供擴充模式 `--shelf` 值域檢查共用（⛔ 各腳本各自硬寫一份）。
SHELF_CODES: tuple[str, ...] = tuple(f[:-3] for f in SHELF_FILES)


def load_exclude(path: str | None) -> tuple[frozenset, str]:
    """讀 `--exclude` JSON：`{"excluded": [fine.id, …], "why": "…"}`。無檔 ⇒ 空集合、why=""。"""
    if not path:
        return frozenset(), ""
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    excluded = doc.get("excluded", [])
    if not isinstance(excluded, list):
        raise ValueError("--exclude 的 excluded 必須是清單")
    return frozenset(str(x) for x in excluded), str(doc.get("why", ""))


def candidate_from_fine(fine: FineItem) -> dict:
    """既有正本一個細目 → 候選 `{id,title,content}`，id 形狀與 `candidate_from_kb_row` 一致（`tmp:kb:<fine.id>`）。"""
    return {"id": f"{TMP_PREFIX}{fine.id}", "title": fine.title, "content": " ".join(fine.content_units)}


def bare_id(candidate_or_old_id: str) -> str:
    """`tmp:kb:<fine.id>` → `<fine.id>`；非此形狀原樣回傳（呼叫端已知形狀時使用）。"""
    if candidate_or_old_id.startswith(TMP_PREFIX):
        return candidate_or_old_id[len(TMP_PREFIX):]
    return candidate_or_old_id


def candidate_from_shelf_fine(fine: FineItem) -> dict:
    """擴充模式（brief-9.7）：某架既有一個細目 → 候選 `{id,title,content}`，id 前綴
    `tmp:canon:`（與新材料 `tmp:kb:`／`tmp:draft:` 區分——擴充模式的 prompt 需要分辨
    「架內既有」與「本次新材料」）。"""
    return {"id": f"{TMP_CANON_PREFIX}{fine.id}", "title": fine.title, "content": " ".join(fine.content_units)}


def bare_canon_id(candidate_or_old_id: str) -> str:
    """`tmp:canon:<fine.id>` → `<fine.id>`；非此形狀原樣回傳。"""
    if candidate_or_old_id.startswith(TMP_CANON_PREFIX):
        return candidate_or_old_id[len(TMP_CANON_PREFIX):]
    return candidate_or_old_id


def fine_shelf_letter(fine_id: str) -> str:
    """細目所屬架字母（計畫 9.10 S5 第二輪；DSP-070 病灶修復）：細目 id 中段
    （`<正本名或受眾>/<架字母>/<slug>`，`FINE_ID_RE` 強制單一大寫字母）。

    ⛔ 不得用 `fine.coarse_id`（粗目 id）判斷「細目屬於哪一架」——粗目 id 自計畫 9.10 S1
    起恆為 `<架字母>-<slug>`（一架可有多個粗目），S5 移除裸字母後粗目 id **永遠不等於**
    架字母本身，`coarse_id == shelf` 這種比法會靜默回空（本函式與粗目 id 的形狀完全無關，
    也不因粗目 id 是裸字母或帶 slug 而改變行為）。三支腳本（`canon_items.shelf_items`、
    `apply_proposal.render_expand`、`attach_phrasings`）共用同一份，⛔ 不各自重寫一套。
    """
    return fine_id.split("/")[1]


def shelf_items(canon_path: str, shelf: str) -> tuple[CanonDoc, list]:
    """擴充模式（brief-9.7）：回 `(canon_doc, items)`——`canon_doc`＝整座圖書館（九架）解析結果
    （供呼叫端核對「新細目 id 不與任何架撞」用整座的 fine id 集合）；`items`＝**只限 `shelf`**
    的既有細目候選（`tmp:canon:<fine.id>`），依 `fine.id` 升冪排序（決定性）。`canon_path` 必須
    是目錄（圖書館正本）——擴充模式不支援單檔封存正本。"""
    if not os.path.isdir(canon_path):
        raise ValueError(f"擴充模式 --canon 須為圖書館目錄（九架），得到單檔：{canon_path!r}")
    doc = load_canon_doc(canon_path)
    fines = sorted((f for f in doc.fines() if fine_shelf_letter(f.id) == shelf), key=lambda f: f.id)
    return doc, [candidate_from_shelf_fine(f) for f in fines]


def parse_canon_auto(canon_path: str) -> CanonDoc:
    """路徑是目錄 ⇒ `parse_canon_dir`（圖書館正本，DSP-058），否則 `parse_canon`（單檔，含封存檔）——
    9.6 S4：共用一個判斷點，⛔ 各腳本各自判斷（`os.path.isdir` 分派）。"""
    return parse_canon_dir(canon_path) if os.path.isdir(canon_path) else parse_canon(canon_path)


def load_canon_doc(canon_path: str) -> CanonDoc:
    return parse_canon_auto(canon_path)


def canon_items(canon_path: str, exclude_path: str | None) -> tuple[str, list, frozenset, str]:
    """回 `(audience, items, excluded_ids, why)`。`items` 已排除 `excluded_ids`，依 `fine.id` 升冪排序、
    決定性（`parse_canon` 本身即決定性）。`excluded_ids` 為既有正本細目 id（不含 `tmp:kb:` 前綴）。"""
    doc = load_canon_doc(canon_path)
    excluded, why = load_exclude(exclude_path)
    fines = sorted(doc.fines(), key=lambda f: f.id)
    items = [candidate_from_fine(f) for f in fines if f.id not in excluded]
    return doc.audience, items, excluded, why
