"""unit：`FineIndex` 內文鍵 ↔ `index_eval` 內文臂鍵集合對照（任務 3.7）。

Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-3.7-fine-index-content-keys-20260907.md`
§4.3／§4.4。

三把尺：
1. 合成正本——`FineIndex` 送去 embed 的鍵文字多重集合＝`index_eval` 內文臂（`title+phrasing+content`）
   的鍵文字多重集合。
2. 真正本（`rag-orchestrator/canon/prospect.md`）——同一等式，⛔ assert 訊息只印數量／布林＋細目
   id，不印鍵文字（正本講法是去識別後的真流量）。
3. 突變控制——用 3.4 凍結的 embedding 快取重放第二份材料 49 格：有內文鍵 r@5 必須高於拿掉內文鍵，
   且兩者都要對齊 3.4 報告 `second_material.article` 臂的數字。前置兩道 SKIP 閘門（快取不在本機／
   正本 sha 與報告不符）；兩道都過後任何鍵查不到向量 ⇒ `FineIndex` 落 `not_ready` ⇒ 本測試**失敗**
   （不是 skip——這才是「快取覆蓋」的正對照）。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import sys
from collections import Counter

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # tests/unit/agent → tests/unit → tests → rag-orchestrator
_REPO = os.path.dirname(_RAG)  # rag-orchestrator の親＝repo 根（容器內＝`/`，host＝AIChatbot/）

sys.path.insert(0, _RAG)
from tools.canon import index_eval as ie  # noqa: E402

from services.agent.canon.canon_parser import parse_canon, parse_canon_text
from services.agent.canon.candidate_selector import CandidateSelector
from services.agent.canon.fine_index import FineIndex
from services.agent.identity import Identity

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.7"),
]

B2B_PROSPECT = Identity(vendor_id=1, target_user="prospect", mode="b2b")


# ═══════════════════════════════════════════════════════════════════════════
# 共用小工具
# ═══════════════════════════════════════════════════════════════════════════

class _FakeBackend:
    """記錄每次送去 embed 的文字（保序）的假後端；回傳決定性單位向量。"""

    def __init__(self, dim: int = 4):
        self._dim = dim
        self.texts: list[str] = []

    async def embed(self, texts):
        self.texts.extend(texts)
        out = []
        for t in texts:
            digest = hashlib.sha256(t.encode("utf-8")).digest()
            out.append([(digest[i] + 1) / 256.0 for i in range(self._dim)])
        return out


def _real_canon_path() -> str:
    return os.path.join(_RAG, "canon", "prospect.md")


# ═══════════════════════════════════════════════════════════════════════════
# §4.3-13：合成正本鍵集合對照
# ═══════════════════════════════════════════════════════════════════════════

_FRONT_MATTER = """---
audience: prospect
version: 2026-09-07.test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
"""

_SHARED_CONTENT = "共用內文句ZZSHARED跨細目重複"


def _block(slug: str, title: str, phrasings: list[tuple[str, str]], contents: list[str]) -> str:
    lines = [f"### {title} {{#prospect/A/{slug}}}"]
    if phrasings:
        lines.append("- phrasings:")
        for text, status in phrasings:
            lines.append(f'  - {{text: "{text}", source: "question_summary:1", status: {status}}}')
    lines += [
        "- sources: [kb:1]",
        "- reviewed: {by: test, at: 2026-09-07}",
        "- instance_applicability: general",
    ]
    lines.extend(contents)
    lines.append("")
    return "\n".join(lines)


def _synthetic_doc():
    """3 細目：講法含 proposed／retired（不進索引）；內文句 2–3 句／細目，一句跨細目重複。"""
    body = "".join([
        _block(
            "fine-1", "標題一ZZPARITY1",
            [("講法核可1ZZPARITY1", "approved"), ("講法核可2ZZPARITY1", "approved"),
             ("講法提案ZZPARITY1", "proposed"), ("講法退役ZZPARITY1", "retired")],
            [_SHARED_CONTENT, "內文二ZZPARITY1"],
        ),
        _block(
            "fine-2", "標題二ZZPARITY2",
            [("講法核可ZZPARITY2", "approved")],
            [_SHARED_CONTENT, "內文二ZZPARITY2", "內文三ZZPARITY2"],
        ),
        _block(
            "fine-3", "標題三ZZPARITY3",
            [("講法核可1ZZPARITY3", "approved"), ("講法核可2ZZPARITY3", "approved"),
             ("講法退役ZZPARITY3", "retired")],
            ["內文一ZZPARITY3", "內文二ZZPARITY3"],
        ),
    ])
    return parse_canon_text(_FRONT_MATTER + body)


def _expected_content_arm_texts(doc) -> list[str]:
    """依細目序串接 `title+phrasing+content` 臂的鍵文字（與 `FineIndex._key_plan` 同序）。"""
    fine_keys = ie.build_fine_keys(doc.fines())
    out: list[str] = []
    for fine in doc.fines():
        out.extend(text for _kind, text, _art in fine_keys[fine.id][ie.ARM_TITLE_PHRASING_CONTENT])
    return out


async def test_synthetic_doc_embedded_key_multiset_matches_index_eval_content_arm():
    doc = _synthetic_doc()
    backend = _FakeBackend()
    index = FineIndex(backend)
    await index.prepare(doc)
    assert index.state == "ready"

    expected_texts = _expected_content_arm_texts(doc)
    assert Counter(backend.texts) == Counter(expected_texts)

    fine_keys = ie.build_fine_keys(doc.fines())
    assert set(backend.texts) == set(ie.all_index_texts(fine_keys))

    # 正對照：跨細目重複句確實存在（鑑別力）
    assert backend.texts.count(_SHARED_CONTENT) == 2
    assert index.content_key_count == sum(len(f.content_units) for f in doc.fines())


# ═══════════════════════════════════════════════════════════════════════════
# §4.3-14：真正本鍵集合對照（只印數量，⛔ 不印鍵文字）
# ═══════════════════════════════════════════════════════════════════════════

async def test_real_canon_embedded_key_multiset_matches_index_eval_content_arm_counts_only():
    doc = parse_canon(_real_canon_path())
    backend = _FakeBackend()
    index = FineIndex(backend)
    await index.prepare(doc)
    assert index.state == "ready"

    fine_keys = ie.build_fine_keys(doc.fines())

    # 逐細目比對：布林＋細目 id，⛔ 不帶出鍵文字
    per_fine_expected = {
        fine.id: [text for _kind, text, _art in fine_keys[fine.id][ie.ARM_TITLE_PHRASING_CONTENT]]
        for fine in doc.fines()
    }
    idx = 0
    mismatched_fine_ids: list[str] = []
    for fine in doc.fines():
        expected_slice = per_fine_expected[fine.id]
        n = len(expected_slice)
        actual_slice = backend.texts[idx: idx + n]
        if actual_slice != expected_slice:
            mismatched_fine_ids.append(fine.id)
        idx += n
    assert not mismatched_fine_ids, f"{len(mismatched_fine_ids)} 個細目鍵序不符：{mismatched_fine_ids}"
    assert idx == len(backend.texts), (idx, len(backend.texts))

    # 整體多重集合等式：⛔ assert 訊息只印數量
    a = set(backend.texts)
    b = set(ie.all_index_texts(fine_keys))
    n_diff = len(a ^ b)
    assert n_diff == 0, f"{n_diff} 把鍵不一致"

    fines = doc.fines()
    n_fines = len(fines)
    n_approved = sum(1 for f in fines for p in f.phrasings if p.status == "approved")
    n_content = sum(len(f.content_units) for f in fines)

    assert index.content_key_count == n_content
    assert index.entry_count == n_fines + n_approved + n_content


# ═══════════════════════════════════════════════════════════════════════════
# §4.4：突變控制——第二份材料 49 格，3.4 凍結快取重放
# ═══════════════════════════════════════════════════════════════════════════

class _CacheBackend:
    """查 3.4 凍結快取（`ie._cache_key(text)`）的假後端；未命中 ⇒ `None`（⛔ 不打真 API）。"""

    def __init__(self, vectors: dict):
        self._vectors = vectors

    async def embed(self, texts):
        return [self._vectors.get(ie._cache_key(t)) for t in texts]


def _repo_paths() -> tuple[str, str, str, str]:
    cache_path = os.path.join(
        _REPO, ".claude", "skills", "outline-curation", "raw", "index-eval-20260907", "embeddings.json"
    )
    report_path = os.path.join(
        _REPO, ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "index-eval-20260907.json",
    )
    map_v2_path = os.path.join(
        _REPO, ".kiro", "specs", "presales-grounding-gate", "coverage-map", "map-v2.json"
    )
    canon_v3_path = os.path.join(
        _REPO, ".claude", "skills", "outline-curation", "runs", "2026-09-06T00-00-00Z",
        "answerability-canon-v3.json",
    )
    return cache_path, report_path, map_v2_path, canon_v3_path


def _strip_content_units(doc):
    """剝掉每細目的 `content_units`（`canon_sha256` 原樣複製，⛔ 不重算）——突變控制材料。"""
    new_coarses = []
    for coarse in doc.coarses:
        new_fines = tuple(dataclasses.replace(f, content_units=()) for f in coarse.fines)
        new_coarses.append(dataclasses.replace(coarse, fines=new_fines))
    return dataclasses.replace(doc, coarses=tuple(new_coarses))


def _real_canon_secrets(doc) -> list[str]:
    out = []
    for fine in doc.fines():
        out.append(fine.title)
        out.extend(p.text for p in fine.phrasings)
        out.extend(fine.content_units)
    return out


async def test_second_material_recall_with_content_keys_beats_without_and_matches_report(caplog):
    cache_path, report_path, map_v2_path, canon_v3_path = _repo_paths()

    if not os.path.isfile(cache_path):
        pytest.skip("3.4 embedding 快取不在本機（gitignored）")

    doc = parse_canon(_real_canon_path())

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)
    if doc.canon_sha256 != report["inputs_sha"]["canon_sha256"]:
        pytest.skip("正本已變（sha 不符 3.4 報告）、需重跑 3.4 全跑更新快取與報告")

    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    vectors = cache["vectors"]

    stripped = _strip_content_units(doc)
    assert stripped.canon_sha256 == doc.canon_sha256, "正對照：剝掉內文句後 sha 仍與原 doc 相同（刻意複製）"

    index = FineIndex(_CacheBackend(vectors))
    await index.prepare(doc)
    assert index.state == "ready", "有內文鍵版本未 ready——快取缺鍵（見上方兩道 SKIP 閘門是否已過）"

    index_stripped = FineIndex(_CacheBackend(vectors))
    await index_stripped.prepare(stripped)
    assert index_stripped.state == "ready", "拿掉內文鍵版本未 ready——快取缺鍵"

    cells, excluded = ie.load_second_material(map_v2_path, canon_v3_path)
    report_sm = report["results"]["second_material"]["article"]
    assert excluded == report_sm["excluded_deliberate"], (excluded, report_sm["excluded_deliberate"])

    mappable_cells = [c for c in cells if c["gold"]]
    mappable = len(mappable_cells)
    assert mappable == report_sm["arms"]["title"]["mappable"], (mappable, report_sm["arms"]["title"]["mappable"])

    # 隱私正對照：先證 caplog 擷取器活著（沿 §4.1-8 慣例）
    caplog.set_level(logging.DEBUG)
    marker = "ZZCAPTUREPROBE"
    logging.getLogger("tests.fine_index_content_parity.probe").warning(marker)
    assert marker in caplog.text, "caplog 沒抓到標記 ⇒ 日誌擷取器壞了，下面的斷言不成立"
    caplog.clear()

    secrets = _real_canon_secrets(doc) + [c["question"] for c in mappable_cells]

    selector_with = CandidateSelector(index)
    selector_without = CandidateSelector(index_stripped)
    hit5_with = 0
    hit5_without = 0
    for cell in mappable_cells:
        gold = set(cell["gold"])
        sel_with = await selector_with.select(doc, B2B_PROSPECT, cell["question"])
        assert sel_with is not None
        if set(sel_with["candidate_ids"]) & gold:
            hit5_with += 1
        sel_without = await selector_without.select(stripped, B2B_PROSPECT, cell["question"])
        assert sel_without is not None
        if set(sel_without["candidate_ids"]) & gold:
            hit5_without += 1

    leaked = [s for s in secrets if s in caplog.text]
    assert not leaked, f"外洩 {len(leaked)} 筆文字到 caplog"

    assert hit5_with > hit5_without, (hit5_with, hit5_without, mappable)

    got_with = round(hit5_with / mappable, 4)
    got_without = round(hit5_without / mappable, 4)
    expected_with = report_sm["arms"][ie.ARM_TITLE_PHRASING_CONTENT]["recall_at_5"]
    expected_without = report_sm["arms"][ie.ARM_TITLE_PHRASING]["recall_at_5"]
    assert got_with == expected_with, (got_with, expected_with, hit5_with, mappable)
    assert got_without == expected_without, (got_without, expected_without, hit5_without, mappable)
