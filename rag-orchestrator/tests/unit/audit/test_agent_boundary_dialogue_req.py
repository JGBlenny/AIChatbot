"""不變量 28（擴充）、28b、28c、31（擴充）的 pytest 收編——DSP-131 計畫 §5.2 第 5 項（F9）。

⛔ 不重寫 checker 邏輯，只呼叫 `scripts/audit/checks/agent_boundary.py`。
⚠️ 28c 在本片的 worktree **預期紅**（`runtime.py` 3 處 `entry` 字面比較，由主會話併回時改）；
本檔 ⛔ 斷言真樹 28c 為綠，只驗量尺看得見（植入必紅、乾淨不誤報、掃描面正對照）。
"""
import importlib.util
import os

import pytest

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:DSP-131:DA7"

_RAG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
_CHECKER_PY = os.path.join(os.path.dirname(_RAG_ROOT), "scripts", "audit", "checks",
                           "agent_boundary.py")


@pytest.fixture(scope="module")
def ab():
    assert os.path.exists(_CHECKER_PY), _CHECKER_PY
    spec = importlib.util.spec_from_file_location("agent_boundary_checker_dlg", _CHECKER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.req(_REQ)
def test_new_checks_are_registered_and_return_bool(ab):
    by_num = {num: fn for num, _label, fn in ab.CHECKS}
    assert by_num["28b"] is ab.check_28b_dialogue_router_no_mcp_import
    assert by_num["28c"] is ab.check_28c_no_entry_literal_compare
    for num in ("28b", "28c"):
        assert by_num[num]()[0] in (True, False)


# ── 28：對話 API 路徑在閘內 ─────────────────────────────────────────────

@pytest.mark.req(_REQ)
def test_28_real_tree_covers_dialogue_routes(ab):
    ok, detail = ab.check_28_mcp_auth_unconditional()
    assert ok is True, detail
    assert "DIALOGUE_TURN_PATH=/api/v1/agent/turn" in detail
    assert "註冊 2 個路由" in detail


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("kw", [
    dict(router_src=None),
    dict(facade_src='GATED_PREFIXES = ("/mcp",)\nDIALOGUE_TURN_PATH = "/api/v1/agent/turn"\n'
                    'DIALOGUE_UPLOAD_TICKET_PATH = "/api/v1/agent/upload-ticket"\n'),
    dict(auth_src='_EXEMPT_PREFIX = ("/docs", "/api/v1/agent")\n'),
    dict(upload_src='UPLOAD_PATH = "/api/v1/agent/turn"\n'),
], ids=["router-missing", "path-not-gated", "path-exempt", "path-is-upload-exempt"])
def test_28_planted_dialogue_route_gaps_are_caught(ab, kw):
    args = dict(auth_src='_EXEMPT_PREFIX = ("/docs", "/redoc", "/openapi")\n', facade_paths=[],
                router_src=ab._FAKE_ROUTER_28, facade_src=ab._FAKE_FACADE_28,
                upload_src=ab._FAKE_UPLOAD_28)
    assert ab.check_28_mcp_auth_unconditional(**args)[0] is True     # 正對照
    if kw.get("router_src", "x") is None:
        bad, _info = ab.scan_28_dialogue_routes(None, args["facade_src"], ("/docs",),
                                                args["upload_src"])
        assert bad
        return
    args.update(kw)
    ok, detail = ab.check_28_mcp_auth_unconditional(**args)
    assert ok is False, detail


@pytest.mark.req(_REQ)
def test_28_literal_route_path_is_caught(ab):
    src = ab._FAKE_ROUTER_28.replace("mcp_facade.DIALOGUE_TURN_PATH", "'/api/v1/agent/turn'")
    ok, detail = ab.check_28_mcp_auth_unconditional(
        auth_src='_EXEMPT_PREFIX = ("/docs",)\n', facade_paths=[], router_src=src,
        facade_src=ab._FAKE_FACADE_28, upload_src=ab._FAKE_UPLOAD_28)
    assert ok is False and "路徑不是" in detail


# ── 28b：路由不 import mcp.* ────────────────────────────────────────────

@pytest.mark.req(_REQ)
def test_28b_real_router_has_no_mcp_import(ab):
    ok, detail = ab.check_28b_dialogue_router_no_mcp_import()
    assert ok is True, detail


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("planted", [
    "import mcp\n", "from mcp.server.fastmcp import Context\n", "import mcp.types as t\n",
    "import importlib\nX = importlib.import_module('mcp')\n",
])
def test_28b_planted_mcp_import_is_caught(ab, planted):
    assert ab.check_28b_dialogue_router_no_mcp_import(src=ab._FAKE_ROUTER_28)[0] is True
    ok, detail = ab.check_28b_dialogue_router_no_mcp_import(src=planted + ab._FAKE_ROUTER_28)
    assert ok is False, detail


# ── 28c：identity.py 以外無 entry 字面比較 ──────────────────────────────

@pytest.mark.req(_REQ)
def test_28c_real_tree_scan_surface_is_not_empty(ab):
    """正對照：掃描面真的掃到東西（⛔ 斷言真樹無命中，見模組 docstring）。"""
    hits, scanned, errors = ab.scan_28c_entry_literals()
    assert not errors, errors
    assert len(scanned) >= 20
    for must in ("services/agent/mcp_facade.py", "services/agent/runtime.py", "app.py",
                 "routers/agent_dialogue.py", "services/agent/tools/registry.py"):
        assert must in scanned, must
    assert "services/agent/identity.py" not in scanned
    # 命中只可能落在 runtime.py（本片之內改過的檔都已改用 is_backend_entry）
    assert {rel for rel, _ln, _s in hits} <= {"services/agent/runtime.py"}, hits


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("src", [
    'if entry == "mcp":\n    pass\n',
    'x = identity.entry != "mcp"\n',
    'x = getattr(identity, "entry", None) != "rest"\n',
    'x = "dialogue" == identity.entry\n',
    'x = identity.entry in ("mcp", "dialogue")\n',
    'x = state["entry"] == "mcp"\n',
])
def test_28c_planted_literal_compare_is_caught(ab, src):
    ok, detail = ab.check_28c_no_entry_literal_compare(
        sources={"services/x.py": src}, must_include=("services/x.py",))
    assert ok is False and "services/x.py:" in detail, detail


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("src", [
    "x = is_backend_entry(entry)\n",
    'f(entry="mcp")\n',
    'x = channel == "mcp"\n',
    '"""entry == "mcp"（說明文字）"""\n',
])
def test_28c_clean_forms_are_not_flagged(ab, src):
    ok, detail = ab.check_28c_no_entry_literal_compare(
        sources={"services/x.py": src}, must_include=("services/x.py",))
    assert ok is True, detail


# ── 31：對話 API 每呼叫一列的覆蓋登記 ──────────────────────────────────

@pytest.mark.req(_REQ)
def test_31_registers_dialogue_coverage(ab):
    ok, detail = ab.check_31_mcp_usage_events_coverage()
    assert ok is True, detail
    assert ab.DIALOGUE_USAGE_TEST_FUNC in detail


@pytest.mark.req(_REQ)
def test_31_missing_dialogue_coverage_is_fail_not_warn(ab, tmp_path):
    base = tmp_path / "test_mcp_facade_req.py"
    base.write_text("def test_x():\n    pass\n")
    other = tmp_path / "test_dialogue.py"
    other.write_text("def test_other():\n    pass\n")
    assert ab.check_31_mcp_usage_events_coverage(
        path=str(base), dialogue_path=str(tmp_path / "nope.py"))[0] is False
    assert ab.check_31_mcp_usage_events_coverage(path=str(base), dialogue_path=str(other))[0] is False


@pytest.mark.req(_REQ)
def test_self_test_still_passes(ab):
    assert ab.self_test() == 0
