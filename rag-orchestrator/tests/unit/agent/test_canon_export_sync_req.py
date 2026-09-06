"""unit：正本同源硬把關（spec knowledge-outline-and-intent-architecture 任務 2.5；需求 2.9）。

`rag-orchestrator/canon/<audience>.md` 是唯一正本；同目錄的 `<audience>.json` 必須逐位元等於
`export_json(parse_canon(md))` 的輸出——JSON 永遠是 Markdown 的衍生物，⛔ 手改 JSON 或忘了重導出都紅。
正對照：把導出的 JSON 竄改一位元 ⇒ 必紅（守門真的在看位元組，不是看檔案存在）。
"""
from __future__ import annotations

import glob
import os

import pytest

from services.agent.canon.canon_parser import export_json, parse_canon

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.5")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # rag-orchestrator/
CANON_DIR = os.path.join(_RAG, "canon")
CANON_MDS = sorted(p for p in glob.glob(os.path.join(CANON_DIR, "*.md")) if os.path.basename(p) != "README.md")

SAMPLE = """---
audience: prospect
version: 2026-09-06.1
reviewers: [owner]
language: zh-TW
budget_tokens: 10000
target_user: [prospect]
business_types: [system_provider]
---
## A 產品基本盤 {#A}
### 系統定位 {#prospect/A/positioning}
- sources: [kb:3585]
- instance_applicability: general
金箍棒把物件、合約、收租集中管理。
"""


def _exported_bytes(md_path: str, tmp_dir: str) -> bytes:
    doc = parse_canon(md_path)
    out = os.path.join(tmp_dir, os.path.basename(md_path)[:-3] + ".json")
    export_json(doc, out)
    with open(out, "rb") as fh:
        return fh.read()


@pytest.mark.parametrize("md_path", CANON_MDS or [pytest.param(None, id="no-canon-yet")])
def test_versioned_json_is_byte_identical_to_export(md_path, tmp_path):
    """每份正本的版控 JSON ＝ 重新導出的 JSON（逐位元）。尚無正本時本案例以 skip 標示（不是綠）。"""
    if md_path is None:
        pytest.skip("rag-orchestrator/canon/ 尚無正本 .md（占位期）")
    json_path = md_path[:-3] + ".json"
    assert os.path.exists(json_path), f"缺版控導出檔 {json_path}：請跑 export_json 並一起提交"
    with open(json_path, "rb") as fh:
        versioned = fh.read()
    assert versioned == _exported_bytes(md_path, str(tmp_path)), f"{json_path} 與 Markdown 導出不一致：JSON 是衍生物，請重導出"


def test_tampering_one_byte_is_detected(tmp_path):
    """正對照：同一份正本，導出兩次逐位元相同；把其中一份改一位元 ⇒ 比對必紅。"""
    md = tmp_path / "prospect.md"
    md.write_text(SAMPLE, encoding="utf-8")
    a = _exported_bytes(str(md), str(tmp_path / "a")) if (tmp_path / "a").mkdir() is None else b""
    b = _exported_bytes(str(md), str(tmp_path / "b")) if (tmp_path / "b").mkdir() is None else b""
    assert a == b and len(a) > 100
    tampered = bytearray(a)
    idx = a.index(b'"version"') + len(b'"version": "') + 1
    tampered[idx] = ord("9") if tampered[idx] != ord("9") else ord("8")
    assert bytes(tampered) != a
    # 竄改 Markdown 一個字 ⇒ 導出也變（canon_sha256 隨位元組走）
    md2 = tmp_path / "prospect2.md"
    md2.write_text(SAMPLE.replace("集中管理。", "集中管理！"), encoding="utf-8")
    (tmp_path / "c").mkdir()
    assert _exported_bytes(str(md2), str(tmp_path / "c")) != a
