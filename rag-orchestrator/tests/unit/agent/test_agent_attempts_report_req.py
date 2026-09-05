"""unit：`tools/agent_attempts_report.py`（spec agentic-mcp-orchestration
tasks 4.3c）。

離線分析工具——讀 `agent_eval.py --dump-texts` 的 texts 旁路 jsonl，彙總
被拒中間嘗試的統計。全部離線：不呼叫模型／DB，輸入只有本機 jsonl。

覆蓋：
- `classify_ref_shape`：缺段／多段／含中文／含空白／其他五類逐一命中；
  正對照——結構正確的三段式＋§ ref 不得落進任何一個「格式缺陷」桶。
- `reject_reason_counts`：`SCHEMA_PARSE`／`SCHEMA:<cause>`／一般 reason 分流。
- `final_kind_after_reject_counts`：只算「本回合至少一次嘗試被拒」的記錄。
- `ref_invalid_shape_counts`：只算 `schema_cause=="ref_invalid"`，
  `ref_source_not_found` 等其他成因不進這張表。
- `quote_not_covering_shape_distribution`：句數／refs 數分佈。
- `load_texts_jsonl`：略過 `_warning` 表頭。
- CLI `main`：讀檔＋輸出 markdown（`--out`）；報表不含任何原始 `ref` 字串或原文。
"""
from __future__ import annotations

import json

import pytest

from tools.agent_attempts_report import (
    classify_ref_shape,
    final_kind_after_reject_counts,
    load_texts_jsonl,
    main,
    quote_not_covering_shape_distribution,
    ref_invalid_shape_counts,
    reject_reason_counts,
    render_report_md,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# classify_ref_shape
# ---------------------------------------------------------------------------


def test_classify_ref_shape_missing_segment():
    assert classify_ref_shape("not-a-real-marker") == "缺段"
    assert classify_ref_shape("aaaa1111bbbb2222:call_1§0") == "缺段"


def test_classify_ref_shape_extra_segment():
    assert classify_ref_shape("aaaa1111bbbb2222:call_1:kb:1:extra§0") == "多段"


def test_classify_ref_shape_contains_chinese():
    assert classify_ref_shape("aaaa1111bbbb2222:call_1:知識庫§0") == "含中文"


def test_classify_ref_shape_contains_whitespace():
    assert classify_ref_shape("aaaa1111bbbb2222: call_1 :kb§0") == "含空白"


def test_classify_ref_shape_well_formed_is_not_a_defect_bucket():
    """正對照：結構正確的三段式＋§ ref（即便 nonce 對不上本回合、實際上是
    `ref_source_not_found` 這類內容錯誤）不得被誤判成任何一個格式缺陷桶。

    ⚠️ 刻意選一個 `source` 段**不含冒號**的例子（如 `kb`）——本函式用單純的
    `:` 切段判斷段數，`source` 本身合法含冒號（如 `kb:3600`）時這個簡化
    heuristic 無法與「真的多一段」區分，屬已知限制，見函式 docstring。"""
    well_formed = "aaaa1111bbbb2222:call_1:kb§2"
    shape = classify_ref_shape(well_formed)
    assert shape not in {"缺段", "多段", "含中文", "含空白"}
    assert shape == "其他"


# ---------------------------------------------------------------------------
# reject_reason_counts ／ final_kind_after_reject_counts
# ---------------------------------------------------------------------------


def _attempt(*, ok, reason=None, schema_cause=None, kind="answer", sentences=None, resolve_errors=None):
    d = {
        "attempt": 1,
        "kind": kind if ok is not None else None,
        "verdict": {"ok": ok, "reason": reason, "schema_cause": schema_cause},
    }
    if ok is None:  # SCHEMA_PARSE 形狀（見 runtime.py：不含 fact_class 等鍵）
        d = {"attempt": 1, "kind": None, "raw_len": 42, "verdict": {"reason": "SCHEMA_PARSE"}}
        return d
    d["sentences"] = sentences or []
    d["resolve_errors"] = resolve_errors or {}
    return d


def test_reject_reason_counts_splits_schema_parse_and_schema_cause():
    records = [
        {"kind": "answer", "attempts": [
            _attempt(ok=None),
            _attempt(ok=False, reason="SCHEMA", schema_cause="ref_invalid"),
            _attempt(ok=True, kind="answer"),
        ]},
        {"kind": "handoff", "attempts": [
            _attempt(ok=False, reason="QUOTE_NOT_COVERING"),
            _attempt(ok=False, reason="QUOTE_NOT_COVERING"),
        ]},
    ]
    counts = reject_reason_counts(records)
    assert counts["SCHEMA_PARSE"] == 1
    assert counts["SCHEMA:ref_invalid"] == 1
    assert counts["QUOTE_NOT_COVERING"] == 2
    assert sum(counts.values()) == 4  # 兩筆 ok=True 不計


def test_final_kind_after_reject_counts_only_counts_records_with_a_reject():
    records = [
        {"kind": "answer", "attempts": [_attempt(ok=True)]},  # 從沒被拒 ⇒ 不計
        {"kind": "answer", "attempts": [_attempt(ok=False, reason="QUOTE_TOO_SHORT"), _attempt(ok=True)]},
        {"kind": "handoff", "attempts": [_attempt(ok=None)]},  # SCHEMA_PARSE 也算被拒過
    ]
    counts = final_kind_after_reject_counts(records)
    assert counts == {"answer": 1, "handoff": 1}


# ---------------------------------------------------------------------------
# ref_invalid_shape_counts
# ---------------------------------------------------------------------------


def test_ref_invalid_shape_counts_only_counts_ref_invalid_cause():
    records = [
        {
            "kind": "answer",
            "attempts": [
                _attempt(
                    ok=False, reason="SCHEMA", schema_cause="ref_invalid",
                    sentences=[{"text": "x", "kind": "fact", "refs": ["not-a-real-marker"]}],
                    resolve_errors={"0:0": "ref_invalid"},
                ),
                _attempt(
                    ok=False, reason="SCHEMA", schema_cause="ref_source_not_found",
                    sentences=[{"text": "y", "kind": "fact", "refs": ["aaaa1111bbbb2222:call_1:kb:9§0"]}],
                    resolve_errors={"0:0": "ref_source_not_found"},
                ),
            ],
        }
    ]
    counts = ref_invalid_shape_counts(records)
    assert counts == {"缺段": 1}  # ref_source_not_found 那筆不進表


# ---------------------------------------------------------------------------
# quote_not_covering_shape_distribution
# ---------------------------------------------------------------------------


def test_quote_not_covering_shape_distribution_counts_sentences_and_refs():
    records = [
        {
            "kind": "answer",
            "attempts": [
                _attempt(
                    ok=False, reason="QUOTE_NOT_COVERING",
                    sentences=[
                        {"text": "a", "kind": "fact", "refs": ["r1"]},
                        {"text": "b", "kind": "fact", "refs": ["r2", "r3"]},
                    ],
                ),
                _attempt(
                    ok=False, reason="QUOTE_NOT_COVERING",
                    sentences=[{"text": "c", "kind": "fact", "refs": []}],
                ),
                _attempt(ok=False, reason="QUOTE_TOO_SHORT", sentences=[]),  # 不同拒因 ⇒ 不計
            ],
        }
    ]
    dist = quote_not_covering_shape_distribution(records)
    assert dist["n_sentences"] == {2: 1, 1: 1}
    assert dist["n_refs"] == {3: 1, 0: 1}


# ---------------------------------------------------------------------------
# load_texts_jsonl ／ CLI
# ---------------------------------------------------------------------------


def test_load_texts_jsonl_skips_warning_header(tmp_path):
    path = tmp_path / "topics.jsonl"
    path.write_text(
        json.dumps({"_warning": "人工抽審用"}, ensure_ascii=False) + "\n"
        + json.dumps({"set": "topics", "idx": "t1", "kind": "answer", "attempts": []}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    records = load_texts_jsonl(path)
    assert len(records) == 1
    assert records[0]["idx"] == "t1"


def test_main_writes_markdown_report_without_any_raw_ref_or_text(tmp_path):
    secret_marker = "not-a-real-marker-含中文-should-not-leak"
    path = tmp_path / "topics.jsonl"
    row = {
        "set": "topics", "idx": "t1", "turn": 0, "chain": "agent",
        "q": "問句原文不該出現在報表", "answer": "答案原文不該出現在報表",
        "handoff_reason": None, "kind": "answer", "refs": [],
        "attempts": [
            _attempt(
                ok=False, reason="SCHEMA", schema_cause="ref_invalid",
                sentences=[{"text": "答案原文不該出現在報表", "kind": "fact", "refs": [secret_marker]}],
                resolve_errors={"0:0": "ref_invalid"},
            ),
            _attempt(ok=True, kind="answer"),
        ],
    }
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    out_path = tmp_path / "report.md"
    code = main([str(path), "--out", str(out_path)])
    assert code == 0
    report = out_path.read_text(encoding="utf-8")
    assert "含中文" in report          # 樣態名可以出現
    assert secret_marker not in report  # ⛔ 原始標記字串不得出現
    assert "問句原文不該出現在報表" not in report
    assert "答案原文不該出現在報表" not in report


def test_main_reports_missing_file(tmp_path, capsys):
    code = main([str(tmp_path / "does-not-exist.jsonl")])
    assert code == 1
    err = capsys.readouterr().err
    assert "找不到檔案" in err


def test_render_report_md_handles_empty_records():
    report = render_report_md([])
    assert "無資料" in report
