"""追溯掃描器單元測試（spec testing-traceability 元件 5・任務 4.3）。

以 fixture 資料驗證五類缺口判定與矩陣輸出。純離線、無外部相依 → unit。
"""
import json
import os
import sys

import pytest

# tools/ 在 rag-orchestrator/ 下；conftest 已將根加入 sys.path。
from tools.traceability.scan import (
    scan_requirements,
    scan_tests,
    scan_docs,
    build_matrix,
    TestRef,
    DocRef,
)

pytestmark = pytest.mark.unit


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def spec_tree(tmp_path):
    """建立 specs/ 含一個 spec、兩條需求（1.1, 1.2）。"""
    req = """# 需求

#### 驗收條件
1.1 系統 **shall** 做 A。
1.2 系統 **shall** 做 B。
"""
    _write(tmp_path / "specs" / "demo" / "requirements.md", req)
    return tmp_path


@pytest.mark.req("testing-traceability:8.1")
def test_scan_requirements_parses_numeric_ids(spec_tree):
    reqs = scan_requirements(spec_tree / "specs")
    assert reqs == {"demo": ["1.1", "1.2"]}


@pytest.mark.req("testing-traceability:6.1")
def test_scan_tests_reads_marker_and_docstring(tmp_path):
    src = '''
import pytest

@pytest.mark.req("demo:1.1")
def test_marked():
    """驗證 A。"""
    assert True

def test_docstring_only():
    """對應 demo:1.2 行為。"""
    assert True

def test_untagged():
    assert True
'''
    _write(tmp_path / "tests" / "test_sample.py", src)
    refs = scan_tests(tmp_path / "tests")
    by_name = {r.nodeid.split("::")[-1]: r for r in refs}
    assert by_name["test_marked"].req_ids == ("demo:1.1",)
    assert by_name["test_marked"].source == "marker"
    assert by_name["test_docstring_only"].req_ids == ("demo:1.2",)
    assert by_name["test_docstring_only"].source == "docstring"
    assert by_name["test_untagged"].req_ids == ()


@pytest.mark.req("testing-traceability:6.3")
def test_orphan_requirement_when_no_test():
    reqs = {"demo": ["1.1", "1.2"]}
    tests = [TestRef("tests/t.py::test_a", "unit", ("demo:1.1",), "marker")]
    report = build_matrix(reqs, tests, [])
    assert "demo:1.2" in report.orphan_requirements
    assert "demo:1.1" not in report.orphan_requirements


@pytest.mark.req("testing-traceability:6.5")
def test_orphan_test_when_untagged():
    reqs = {"demo": ["1.1"]}
    tests = [TestRef("tests/t.py::test_untagged", "unit", (), "")]
    report = build_matrix(reqs, tests, [])
    assert report.orphan_tests == ["tests/t.py::test_untagged"]


@pytest.mark.req("testing-traceability:6.4")
def test_dangling_ref_when_requirement_absent():
    reqs = {"demo": ["1.1"]}
    tests = [TestRef("tests/t.py::test_a", "unit", ("demo:9.9",), "marker")]
    report = build_matrix(reqs, tests, [])
    assert any("demo:9.9" in d for d in report.dangling_refs)


@pytest.mark.req("testing-traceability:7.3")
def test_docs_unbacked_when_no_test_covers_referenced_req():
    reqs = {"demo": ["1.1"]}
    docs = [DocRef("docs/f.md", "章節 A", ("demo:1.1",))]
    report = build_matrix(reqs, [], docs)  # 無任何測試
    assert "docs/f.md › 章節 A" in report.docs_unbacked


@pytest.mark.req("testing-traceability:7.4")
def test_docs_stale_when_behavior_keyword_missing_in_backing_tests():
    reqs = {"demo": ["1.1"]}
    tests = [TestRef("tests/t.py::test_something_else", "unit", ("demo:1.1",), "marker")]
    docs = [DocRef("docs/f.md", "CTA 章節", ("demo:1.1",), behavior="markdown")]
    report = build_matrix(reqs, tests, docs)
    # 背書測試 nodeid 不含 "markdown" → 候選過時
    assert any("CTA 章節" in s for s in report.docs_stale)


@pytest.mark.req("testing-traceability:7.4")
def test_docs_not_stale_when_keyword_present():
    reqs = {"demo": ["1.1"]}
    tests = [TestRef("tests/t.py::test_cta_markdown_link", "unit", ("demo:1.1",), "marker")]
    docs = [DocRef("docs/f.md", "CTA 章節", ("demo:1.1",), behavior="markdown")]
    report = build_matrix(reqs, tests, docs)
    assert report.docs_stale == []


@pytest.mark.req("testing-traceability:7.1")
def test_scan_docs_parses_tested_by_annotation(tmp_path):
    md = """# 文件

## CTA 連結

行為說明。
<!-- tested-by: demo:1.1 behavior="markdown CTA" -->

## 其他
"""
    _write(tmp_path / "docs" / "feature.md", md)
    docs = scan_docs(tmp_path / "docs")
    assert len(docs) == 1
    assert docs[0].req_ids == ("demo:1.1",)
    assert docs[0].section == "CTA 連結"
    assert "markdown" in docs[0].behavior


@pytest.mark.req("testing-traceability:8.1")
def test_to_markdown_and_to_json_and_gap_count():
    reqs = {"demo": ["1.1", "1.2"]}
    tests = [
        TestRef("tests/t.py::test_a", "unit", ("demo:1.1",), "marker"),
        TestRef("tests/t.py::test_untagged", "unit", (), ""),
    ]
    report = build_matrix(reqs, tests, [])
    js = report.to_json()
    assert js["gap_count"] == report.gap_count()
    # 1 孤兒需求(1.2) + 1 孤兒測試 = 2
    assert report.gap_count() == 2
    md = report.to_markdown()
    assert "追溯矩陣" in md
    assert "demo:1.1" in md
    # JSON 可序列化
    json.dumps(js, ensure_ascii=False)
