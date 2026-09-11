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
    """建立 specs/ 含一個 spec、兩條需求（1.1, 1.2）——舊式行內形。"""
    req = """# 需求

#### 驗收條件
1.1 系統 **shall** 做 A。
1.2 系統 **shall** 做 B。
"""
    _write(tmp_path / "specs" / "demo" / "requirements.md", req)
    return tmp_path


@pytest.fixture
def real_shape_spec_tree(tmp_path):
    """⚠️ 逐字沿用線上 requirements.md 的真實形狀。

    ⛔ 不得改成「剛好符合正規式」的合成格式：本檔的 fixture 曾自創
    `1.1 系統 shall ...` 這種真實檔案裡不存在的行內形，於是測試恆綠、
    而 `make trace`／CI 的追溯閘實際解析到 0 條需求、把 2083 支測試
    全判成孤兒。修改本 fixture 前先對一份真的 requirements.md。
    """
    req = """# 需求規格：demo

## 已拍板決策
1. 這是決策清單，⛔ 不是驗收條件，不得被算成需求 id。
2. 同上。

## 需求

### Requirement 1：意圖進場
#### 驗收標準（EARS）
1. WHEN 條件 A，THE SYSTEM SHALL 行為 A。
2. WHEN 條件 B，THE SYSTEM SHALL 行為 B。

### Requirement 2：槽位預填
#### 驗收標準（EARS）
1. WHEN 條件 C，THE SYSTEM SHALL 行為 C。
"""
    bullet = """# 需求規格：bullet

## Requirement 4：Mock 保真度
**背景**：散文段落，⛔ 不是驗收條件。

- 4.1 WHEN 條件 A，THEN SHALL 行為 A。
- 4.2 條件 B SHALL 行為 B。
"""
    r_style = """# 需求規格：rstyle

## R1（provenance：NECESSARY）｜業主裁定：APPROVE
內文。

## R2（provenance：SUPPORTED）｜業主裁定：APPROVE
內文。
"""
    _write(tmp_path / "specs" / "demo" / "requirements.md", req)
    _write(tmp_path / "specs" / "rstyle" / "requirements.md", r_style)
    _write(tmp_path / "specs" / "bullet" / "requirements.md", bullet)
    return tmp_path


@pytest.mark.req("testing-traceability:8.1")
def test_scan_requirements_parses_numeric_ids(spec_tree):
    reqs = scan_requirements(spec_tree / "specs")
    assert reqs == {"demo": ["1.1", "1.2"]}


@pytest.mark.req("testing-traceability:8.1")
def test_scan_requirements_parses_real_requirement_heading_shape(real_shape_spec_tree):
    """真實形狀：`### Requirement N` ＋ `#### 驗收標準（EARS）` 底下的編號項。"""
    reqs = scan_requirements(real_shape_spec_tree / "specs")
    assert reqs["demo"] == ["1", "1.1", "1.2", "2", "2.1"]


@pytest.mark.req("testing-traceability:8.1")
def test_scan_requirements_ignores_numbered_lists_outside_criteria(real_shape_spec_tree):
    """`## 已拍板決策` 底下的 1. 2. ⛔ 不得被算成驗收條件。"""
    reqs = scan_requirements(real_shape_spec_tree / "specs")
    assert "1.1" in reqs["demo"]          # 正對照：真的驗收條件有被收
    assert reqs["demo"].count("1.1") == 1  # 決策清單沒有汙染


@pytest.mark.req("testing-traceability:8.1")
def test_scan_requirements_parses_r_style_headings(real_shape_spec_tree):
    """`## RN` 標題形（routing-authority-model 等）⇒ id "N"。"""
    reqs = scan_requirements(real_shape_spec_tree / "specs")
    assert reqs["rstyle"] == ["1", "2"]


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


@pytest.mark.req("testing-traceability:8.1")
def test_scan_requirements_parses_bullet_form_ids(real_shape_spec_tree):
    """條列式明寫完整 id：`- 4.1 WHEN ...`（conversational-routing-execution 等 4 份用這形狀）。

    ⚠️ 這條是第二次補漏才加的：首版只支援 `#### 驗收標準` 底下的編號項，
    於是 `conversational-routing-execution:4.4` 之類仍被判成失效引用。
    ⛔ 新增 requirements.md 形狀時要先在這裡加一條，不要只改掃描器。
    """
    reqs = scan_requirements(real_shape_spec_tree / "specs")
    assert reqs["bullet"] == ["4", "4.1", "4.2"]
