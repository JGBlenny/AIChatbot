"""unit：F6 不變量——jgb2 寫入方法只能從登記在 `ACTION_SPECS` 的 `scope="write"` 工具呼叫
（plan-assistant-11-items-20261014 §3f 4；安全審查 F6）。

為什麼要這條：寫入工具的確認兌現（`registry._wrap_write_tool`）只包在 `ACTION_SPECS`
登記、`scope=="write"` 的函式外面。任何其他地方直接呼叫 `JGBSystemAPI` 的寫入方法，
就等於開了一條不經確認卡、不經兌現的寫入路徑——而那條路在功能上完全看不出來。

證法（AST，⛔ 靠 grep 字串）：掃 `services/agent/` 下每一個 `.py`，凡是**提到**寫入方法名的
節點——屬性存取（`api.create_repair`，含不呼叫只取值）、裸名稱（`from … import create_repair`
之後的呼叫）、`getattr(x, "create_repair")` 這類字串動態存取——都必須落在
`tools/action.py` 裡、且**最內層外圍函式**是 `ACTION_SPECS` 登記的 write handler。
正對照：①真樹上 5 個寫入方法每一個都至少被允許的 handler 呼叫一次（掃描器真的看得到）；
②測試自己構造的違規假樹必須被逐條抓到（掃描器真的會報）。
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator, Optional

import pytest

from services.agent.tools import action as action_tools

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R4.2")]

#: `JGBSystemAPI` 的寫入方法（§3f 4 逐字）。
WRITE_METHODS = frozenset({
    "create_repair", "agent_patch_bill_due_date",
    "assistant_create_estate", "assistant_create_contract", "assistant_create_bill",
})

AGENT_ROOT = Path(action_tools.__file__).resolve().parents[1]          # services/agent
ACTION_FILE = Path(action_tools.__file__).resolve()
_DYNAMIC_ACCESS = frozenset({"getattr", "setattr", "hasattr", "delattr"})


def _walk(node: ast.AST, func: Optional[str] = None) -> Iterator[tuple]:
    """`(節點, 最內層外圍函式名)`；lambda 視為匿名函式（名稱 `<lambda>`，⛔ 算任何 handler）。"""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inner = child.name
        elif isinstance(child, ast.Lambda):
            inner = "<lambda>"
        else:
            inner = func
        yield child, func
        yield from _walk(child, inner)


def _mentions(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Attribute) and node.attr in WRITE_METHODS:
        return node.attr
    if isinstance(node, ast.Name) and node.id in WRITE_METHODS:
        return node.id
    if isinstance(node, ast.alias) and (
            node.name.split(".")[-1] in WRITE_METHODS or node.asname in WRITE_METHODS):
        return node.name                                  # 改名匯入（`as acb`）也算
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _DYNAMIC_ACCESS):
        for arg in node.args:
            if isinstance(arg, ast.Constant) and arg.value in WRITE_METHODS:
                return f"{node.func.id}:{arg.value}"
    return None


def scan(root: Path, action_file: Path, allowed: frozenset) -> tuple:
    """`(violations, allowed_hits)`：違規清單（`檔:行:函式:方法`）與允許的命中集合。"""
    violations: list = []
    allowed_hits: set = set()
    files = sorted(root.rglob("*.py"))
    if not files:
        raise AssertionError(f"掃描範圍內沒有任何 .py：{root}")               # 大聲失敗
    for py in files:
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        in_action = py.resolve() == action_file.resolve()
        for node, func in _walk(tree):
            hit = _mentions(node)
            if hit is None:
                continue
            line = getattr(node, "lineno", 0)
            if in_action and func in allowed and isinstance(node, ast.Attribute):
                allowed_hits.add((func, hit))
                continue
            violations.append(f"{py.relative_to(root)}:{line}:{func}:{hit}")
    return violations, allowed_hits


def _allowed_handlers() -> frozenset:
    names = set()
    for spec, fn in action_tools.ACTION_SPECS:
        assert spec["scope"] == "write" and spec["mcp_only"] is True, spec["name"]
        assert Path(fn.__code__.co_filename).resolve() == ACTION_FILE, spec["name"]
        names.add(fn.__name__)
    return frozenset(names)


def test_write_methods_are_only_called_by_registered_write_handlers():
    violations, hits = scan(AGENT_ROOT, ACTION_FILE, _allowed_handlers())
    assert violations == [], violations
    # 正對照①：5 個寫入方法每一個都被看見至少一次（⛔ 掃描器看不到東西也會「0 違規」）
    assert {method for _func, method in hits} == WRITE_METHODS, hits
    assert hits >= {
        ("repair_create", "create_repair"),
        ("bill_due_extend", "agent_patch_bill_due_date"),
        ("estate_create", "assistant_create_estate"),
        ("contract_create", "assistant_create_contract"),
        ("manual_bill_create", "assistant_create_bill"),
    }


def test_scanner_catches_a_fabricated_violation(tmp_path):
    """正對照②：自造違規假樹——每一種違規形狀都必須被抓到，合法那一處不得被報。"""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "action.py").write_text(
        "async def ok_handler(api):\n"
        "    return await api.create_repair(role_id='1')\n"
        "async def helper(api):\n"
        "    return await api.assistant_create_estate('1', '2', {})\n"
        "async def ok_handler_with_lambda(api):\n"
        "    f = lambda: api.assistant_create_bill('1', '2', {})\n"
        "    return f\n",
        encoding="utf-8",
    )
    (tmp_path / "rogue.py").write_text(
        "from services.jgb_system_api import JGBSystemAPI\n"
        "async def sneaky(api):\n"
        "    await api.agent_patch_bill_due_date('1', '2026-01-01')\n"
        "    fn = getattr(api, 'assistant_create_contract')\n"
        "    return fn\n"
        "write = JGBSystemAPI.create_repair\n",
        encoding="utf-8",
    )
    (tmp_path / "imports.py").write_text(
        "from somewhere import assistant_create_bill as acb\n", encoding="utf-8")
    violations, hits = scan(tmp_path, tools / "action.py",
                            frozenset({"ok_handler", "ok_handler_with_lambda"}))
    assert hits == {("ok_handler", "create_repair")}
    flagged = {v.split(":", 2)[0] + ":" + v.split(":", 2)[1] for v in violations}
    assert flagged == {
        "tools/action.py:4",        # 未登記的 helper 呼叫寫入方法
        "tools/action.py:6",        # 登記 handler 內的 lambda（⛔ 算 handler 本身）
        "rogue.py:3",               # 他檔直接呼叫
        "rogue.py:4",               # getattr 字串動態存取
        "rogue.py:6",               # 取方法物件（不呼叫）
        "imports.py:1",             # 以名稱匯入
    }, violations


def test_scanner_fails_loudly_on_empty_tree(tmp_path):
    with pytest.raises(AssertionError, match="沒有任何"):
        scan(tmp_path, tmp_path / "tools" / "action.py", frozenset())
