"""不變量 27–31（design.md 附錄 B 稱「不變量 18–22」，編號衝突見 DSP-013）
的 unit 覆蓋——spec agentic-mcp-orchestration・任務 1.2。

`scripts/audit/checks/agent_boundary.py` 本身有 `--self-test`（CLI 層的
正/反對照），本檔補的是**pytest 收編**：讓 `make test`／CI 也跑得到這五條
checker，不必額外記得跑 `make audit`。⛔ 不重寫 checker 邏輯，只呼叫它。

編號對照：
| 本檔測的函式 | make audit 印的編號 | design.md 附錄 B 編號 |
|---|---|---|
| check_27_toolspec_identity_keys | 27 | 18 |
| check_28_mcp_auth_unconditional | 28 | 19 |
| check_29_predicate_single_source | 29 | 20 |
| check_30_decision_snapshot_no_verbatim | 30 | 21 |
| check_31_mcp_usage_events_coverage | 31 | 22（WARN-only 登記，1.7 落地） |
| check_32_review_state_single_source | 32 | —（spec knowledge-outline-and-intent-architecture 3.1）|

⚠️ 32 的 DB 子檢查走 `docker exec … psql`，測試容器內**沒有** docker——
故本檔對 32 一律**注入假查詢函式**，⛔ 不連 DB（真 DB 側由 `make audit` 在 host 跑）。
"""
import importlib.util
import os

import pytest

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:1.2"

_RAG_ROOT = os.path.dirname(  # rag-orchestrator/
    os.path.dirname(  # tests/
        os.path.dirname(  # tests/unit/
            os.path.dirname(os.path.abspath(__file__))  # tests/unit/audit/
        )
    )
)
_REPO_ROOT = os.path.dirname(_RAG_ROOT)
_CHECKER_PY = os.path.join(_REPO_ROOT, "scripts", "audit", "checks", "agent_boundary.py")


def _load_checker():
    spec = importlib.util.spec_from_file_location("agent_boundary_checker", _CHECKER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ab():
    assert os.path.exists(_CHECKER_PY), (
        f"{_CHECKER_PY} 不存在——checker 檔案位置變了，本測試的 import 路徑要跟著改"
    )
    return _load_checker()


# ── 正對照：checker 自己的 --self-test 全過 ──────────────────────────────

@pytest.mark.req(_SPEC)
def test_checker_self_test_passes(ab):
    """`agent_boundary.py --self-test` 的每一組正/反對照都必須為真。

    ⛔ 這條紅了不代表現況違規，代表 checker 本身壞了——其餘四條測試的 PASS 不可信。
    """
    assert ab.self_test() == 0


# ── 27（design 18）ToolSpec.input_schema 無身分鍵 ────────────────────────

@pytest.mark.req(_SPEC)
def test_27_current_agent_tree_has_no_identity_keys(ab):
    ok, detail = ab.check_27_toolspec_identity_keys()
    assert ok is True, detail


@pytest.mark.req("agentic-mcp-orchestration:1.10")
def test_27_actually_scans_something(ab):
    """量尺自證（1.10 P2）：這條不變量原本只掃 `registry.py`——那裡一個
    `input_schema` 字面量都沒有，於是長期「掃到 0 個、印綠燈」。

    正對照：現況必須掃到 ≥2 個檔的 spec（`kb.py` 的兩個＋`mcp_facade.py` 的
    `HELP_READ_SPEC`／`_jgb2_spec`）。掃到 0 個時 checker 必須 FAIL。
    """
    specs, errors = ab.scan_27_specs()
    assert not errors, errors
    files = {rel for rel, _lineno, _keys in specs}
    assert len(specs) >= 4, f"只掃到 {len(specs)} 個 input_schema：{specs}"
    assert any(f.endswith("tools/kb.py") for f in files), files
    assert any(f.endswith("mcp_facade.py") for f in files), files


@pytest.mark.req("agentic-mcp-orchestration:1.10")
def test_27_empty_scan_is_loud_failure(ab):
    """掃到 0 個 spec ⇒ FAIL（⛔ 不得再回「空集合通過」）。"""
    ok, detail = ab.check_27_toolspec_identity_keys(src="X = 1\n")
    assert ok is False, f"空跑仍印綠燈：{detail}"


@pytest.mark.req(_SPEC)
def test_27_planted_identity_key_is_caught(ab):
    """量尺自證：植入 vendor_id 到 input_schema.properties 必須被抓到。"""
    bad_src = (
        "from services.agent.tools.registry import ToolSpec\n"
        "SPEC = ToolSpec(name='kb.get', "
        "input_schema={'properties': {'kb_id': {'type': 'string'}, "
        "'vendor_id': {'type': 'integer'}}})\n"
    )
    ok, detail = ab.check_27_toolspec_identity_keys(src=bad_src)
    assert ok is False, f"植入的身分鍵沒被抓到——checker 是瞎的：{detail}"


# ── 28（design 19）/mcp 無條件 401 ────────────────────────────────────────

@pytest.mark.req(_SPEC)
def test_28_current_exempt_prefix_excludes_mcp(ab):
    ok, detail = ab.check_28_mcp_auth_unconditional()
    assert ok is True, detail


@pytest.mark.req(_SPEC)
def test_28_planted_mcp_exemption_is_caught(ab):
    ok, detail = ab.check_28_mcp_auth_unconditional(
        auth_src='_EXEMPT_PREFIX = ("/docs", "/mcp")\n', facade_paths=[])
    assert ok is False, f"植入的 /mcp 豁免沒被抓到：{detail}"


@pytest.mark.req(_SPEC)
def test_28_planted_auth_enforced_reference_is_caught(ab, tmp_path):
    dirty = tmp_path / "mcp_facade_bad.py"
    dirty.write_text(
        "from services.api_key_auth import auth_enforced\n"
        "def handler():\n    if auth_enforced():\n        pass\n"
    )
    ok, detail = ab.check_28_mcp_auth_unconditional(
        auth_src='_EXEMPT_PREFIX = ("/docs",)\n', facade_paths=[str(dirty)])
    assert ok is False, f"門面內出現 auth_enforced 沒被抓到：{detail}"


# ── 29（design 20）可見性謂詞單一來源 ────────────────────────────────────

@pytest.mark.req(_SPEC)
def test_29_current_search_functions_use_single_source(ab):
    ok, detail = ab.check_29_predicate_single_source()
    assert ok is True, detail


@pytest.mark.req(_SPEC)
def test_29_hardcoded_where_clause_is_caught(ab):
    """量尺自證：函式本體字面寫死 `vendor_ids` 在 WHERE 片段裡必須被抓到。"""
    bad_src = (
        "def _vector_search():\n"
        "    sql = '''SELECT kb.id FROM knowledge_base kb\n"
        "        WHERE kb.is_active AND kb.vendor_ids && %s::int[]'''\n"
        "    return sql\n"
    )
    orig_read = ab._read
    ab._read = lambda path: bad_src if path.endswith("_fake_pytest_dirty.py") else orig_read(path)
    try:
        ok, detail = ab.check_29_predicate_single_source(
            targets=[("services/_fake_pytest_dirty.py", "_vector_search")])
    finally:
        ab._read = orig_read
    assert ok is False, f"字面寫死的 vendor_ids 沒被抓到：{detail}"


@pytest.mark.req(_SPEC)
def test_29_select_projection_columns_do_not_false_positive(ab):
    """正對照：SELECT 投影裡的 `kb.vendor_ids`／`kb.business_types` 欄位名
    （非 WHERE 條件）不得被誤判——這是 design.md 附錄 B 已知的假陽性風險。"""
    clean_src = (
        "def _vector_search():\n"
        "    visibility_sql, params = build_visibility_predicate(identity)\n"
        "    sql = f'''SELECT kb.id, kb.vendor_ids, kb.business_types "
        "FROM knowledge_base kb\n"
        "        WHERE kb.embedding IS NOT NULL {visibility_sql}'''\n"
        "    return sql\n"
    )
    orig_read = ab._read
    ab._read = lambda path: clean_src if path.endswith("_fake_pytest_clean.py") else orig_read(path)
    try:
        ok, detail = ab.check_29_predicate_single_source(
            targets=[("services/_fake_pytest_clean.py", "_vector_search")])
    finally:
        ab._read = orig_read
    assert ok is True, f"SELECT 投影欄位名被誤判成 WHERE 違規：{detail}"


# ── 30（design 21）decision_snapshot.agent* 無原文鍵 ─────────────────────

@pytest.mark.req(_SPEC)
def test_30_current_set_decision_calls_have_no_verbatim_keys(ab):
    ok, detail = ab.check_30_decision_snapshot_no_verbatim()
    assert ok is True, detail


@pytest.mark.req(_SPEC)
def test_30_planted_answer_key_is_caught(ab):
    bad_src = "def f():\n    set_decision(snapshot={'agent': {'answer': a}})\n"
    orig_read = ab._read
    ab._read = lambda path: bad_src if path.endswith("_fake_pytest_um_dirty.py") else orig_read(path)
    try:
        ok, detail = ab.check_30_decision_snapshot_no_verbatim(
            paths=["services/_fake_pytest_um_dirty.py"])
    finally:
        ab._read = orig_read
    assert ok is False, f"植入的 answer 原文鍵沒被抓到：{detail}"


# ── 31（design 22）/mcp usage_events 覆蓋登記 ────────────────────────────

@pytest.mark.req(_SPEC)
def test_31_reports_warn_not_fail_before_task_1_7(ab):
    """1.7（MCP 門面）尚未落地時，本 checker 必須是 WARN（`ok is None`），
    ⛔ 不得回 False——那會在門面完成前就把 make audit 卡死在不該紅的規則上。
    """
    ok, detail = ab.check_31_mcp_usage_events_coverage()
    assert ok in (True, None), f"預期 WARN 或 PASS，實得 FAIL：{detail}"


# ── 32 內容已審謂詞單一來源（spec knowledge-outline-and-intent-architecture 3.1）──

_SPEC_32 = "knowledge-outline-and-intent-architecture:3.1"


def _fake_db(total="1048\n", out_of_domain="", derived="0\n"):
    """32 的假 psql：⛔ 不連 DB、⛔ 不呼叫 docker。"""
    def query(sql):
        if "canon_ref" in sql:
            return derived
        if "!~" in sql:
            return out_of_domain
        return total
    return query


@pytest.mark.req(_SPEC_32)
def test_32_current_tree_has_no_stray_column_literal(ab):
    """現樹：`outline_approved_by` 字面只在 `review_state.py`（DB 側用假查詢隔離）。"""
    ok, detail = ab.check_32_review_state_single_source(query=_fake_db())
    assert ok is True, detail


@pytest.mark.req(_SPEC_32)
def test_32_actually_scans_and_finds_consumers(ab):
    """量尺自證：真的掃到檔案，且真的有檔案取用單一來源（⛔ 不是空跑綠燈）。"""
    bad, usages, scanned, errors = ab.scan_32_literals()
    assert not errors, errors
    assert not bad, bad
    assert scanned >= 5, f"只掃到 {scanned} 個檔——掃描面可能搬家了"
    assert len(usages) >= 1, "0 個檔取用 review_state——接線斷了"
    assert any(u.replace("\\", "/").endswith("tools/kb.py") for u in usages), usages


@pytest.mark.req(_SPEC_32)
def test_32_zero_usage_is_loud_failure(ab, tmp_path):
    """空跑不得綠：假樹裡沒有任何消費端 ⇒ FAIL。"""
    canon = tmp_path / "services" / "agent" / "canon"
    canon.mkdir(parents=True)
    (canon / "review_state.py").write_text(
        'COLUMN = "outline_approved_by"\nDOMAIN_REGEX = r"^x$"\n', encoding="utf-8")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "nothing.py").write_text("X = 1\n", encoding="utf-8")
    ok, detail = ab.check_32_review_state_single_source(
        rag_root=str(tmp_path), query=_fake_db())
    assert ok is False, f"零使用命中仍印綠燈：{detail}"


@pytest.mark.req(_SPEC_32)
def test_32_planted_sql_literal_is_caught(ab, tmp_path):
    """量尺自證：在 `review_state.py` 以外植入含欄位名的 SQL 字串常數必須被抓到。"""
    canon = tmp_path / "services" / "agent" / "canon"
    canon.mkdir(parents=True)
    (canon / "review_state.py").write_text(
        'COLUMN = "outline_approved_by"\nDOMAIN_REGEX = r"^x$"\n', encoding="utf-8")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "dirty.py").write_text(
        "from services.agent.canon.review_state import COLUMN\n"
        "SQL = 'SELECT id FROM knowledge_base WHERE outline_approved_by IS NOT NULL'\n",
        encoding="utf-8")
    ok, detail = ab.check_32_review_state_single_source(
        rag_root=str(tmp_path), query=_fake_db())
    assert ok is False, f"植入的字面沒被抓到——checker 是瞎的：{detail}"
    assert "dirty.py" in detail


@pytest.mark.req(_SPEC_32)
def test_32_docstring_mention_is_not_flagged(ab, tmp_path):
    """界定自證：同一個字面只出現在 docstring ⇒ ⛔ 不得誤報（否則只是逼人刪說明）。"""
    canon = tmp_path / "services" / "agent" / "canon"
    canon.mkdir(parents=True)
    (canon / "review_state.py").write_text(
        'COLUMN = "outline_approved_by"\nDOMAIN_REGEX = r"^x$"\n', encoding="utf-8")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "consumer.py").write_text(
        '"""這個模組談 outline_approved_by 這個欄位。"""\n'
        "from services.agent.canon.review_state import COLUMN\n"
        "def f():\n"
        '    """也談 outline_approved_by。"""\n'
        "    return f'SELECT {COLUMN} FROM knowledge_base'\n",
        encoding="utf-8")
    ok, detail = ab.check_32_review_state_single_source(
        rag_root=str(tmp_path), query=_fake_db())
    assert ok is True, f"docstring 內的提及被誤判成違規：{detail}"


@pytest.mark.req(_SPEC_32)
def test_32_db_unreachable_is_fail_not_skip(ab):
    """psql 不可達 ⇒ FAIL（⛔ 不是 SKIP、⛔ 不是綠）——F5。"""
    def boom(_sql):
        raise RuntimeError("Cannot connect to the Docker daemon（測試模擬）")
    ok, detail = ab.check_32_review_state_single_source(query=boom)
    assert ok is False, f"DB 不可達卻沒紅：{detail}"


@pytest.mark.req(_SPEC_32)
def test_32_pending_d1_is_skip(ab):
    """值域外只有 `owner-20260905` 且衍生列 0 ⇒ 三態的 None（SKIP(pending-D1)）。"""
    ok, detail = ab.check_32_review_state_single_source(
        query=_fake_db(out_of_domain="owner-20260905|29\n"))
    assert ok is None, f"預期 SKIP(pending-D1)，實得 {ok}：{detail}"
    assert "SKIP(pending-D1)" in detail


@pytest.mark.req(_SPEC_32)
def test_32_other_out_of_domain_value_is_fail(ab):
    """出現 `owner-20260905` 以外的值域外值 ⇒ FAIL（⛔ 這不是豁免表）。"""
    ok, detail = ab.check_32_review_state_single_source(
        query=_fake_db(out_of_domain="owner-20260905|29\nreviewed:|1\n"))
    assert ok is False, detail


@pytest.mark.req(_SPEC_32)
def test_32_derived_rows_flip_skip_to_fail(ab):
    """D1 已動（衍生列 ≥1）之後 SKIP 必須轉硬失敗。"""
    ok, detail = ab.check_32_review_state_single_source(
        query=_fake_db(out_of_domain="owner-20260905|29\n", derived="7\n"))
    assert ok is False, detail


@pytest.mark.req(_SPEC_32)
def test_32_empty_table_is_positive_control_failure(ab):
    """正對照：`knowledge_base` 查到 0 列 ⇒ FAIL（查詢或環境壞了，不是「沒有違規」）。"""
    ok, detail = ab.check_32_review_state_single_source(query=_fake_db(total="0\n"))
    assert ok is False, detail
