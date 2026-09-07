"""unit：AST 護欄——身分槽位 ⛔ 不得流進可見性／查詢／身分重建
（Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §4.1-6／§4.3-5｜
knowledge-outline-and-intent-architecture:4.2）。

守的是什麼：`identity`／`identity_source` 是每回合由**入口身分**現算的派生值，
`identity_detail` 是**模型自由文字**。三者都只該進 prompt 的槽位段；一旦有人把
它們餵進可見性謂詞、jgb2 查詢、或拿去重建 `Identity`，就等於讓對話內容決定資料
可見範圍——那正是 F10 護欄要擋的形狀。

⛔ **不改 `test_retired_symbols_req.py::find_retired_symbol_usages`**：那支只看
Import／Attribute／Name，原理上看不到 `slots["identity"]` 這種 Subscript 取值。
本檔另寫一支**污染追蹤**掃描器，並與它並存。

掃描器（`find_identity_taint_into_sinks`）：
① 種子＝對名為 `slots`／`flat` 的 dict 取 `identity`／`identity_source`／
   `identity_detail`——`Subscript` 常數鍵與 `.get("…")` 兩種寫法；
② 一層區域變數傳遞（種子 → 變數、變數 → 變數）；
③ sink 封閉表見 `_SINK_*` 三個常數；
④ 走訪 sink 呼叫的 `args`／`keywords` 子樹找種子或被污染的名字。

掃描函式獨立於斷言之外 ⇒ 可直接餵假原始碼做**正對照**（每種 sink 形狀各一段），
證明它不是形同虛設；乾淨樣本必綠；真 `services/agent/**` 必綠。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.2"),
]

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_SERVICES_DIR = REPO_ROOT / "services" / "agent"

#: 被追蹤的槽位鍵（派生兩鍵＋模型自由文字的 `identity_detail`）。
TAINT_KEYS = frozenset({"identity", "identity_source", "identity_detail"})

#: 種子容器名——`runtime._slots_for_prompt` 回的表在產線就叫 `slots`／`flat`。
TAINT_CONTAINERS = frozenset({"slots", "flat"})

#: sink：函式名（不論裸名或屬性呼叫皆算）。
_SINK_NAMES = frozenset({
    "Identity",                    # 重建身分
    "dataclass_replace",           # `dataclasses.replace` 的既有別名（mcp_facade 已在用）
    "build_visibility_predicate",
    "fetch_visible_row",
    "canon_visible",
    "build_canon_toc",
    "resolve_canon_section",
    "visible_subset",
    "query_bills",
    "query_contracts",
    "query_meters",
    "query_accounts",
    "query_estates",
    "kb_get",
    "kb_search",
})

#: sink：只在**屬性呼叫**時算（裸名太泛，會把無關的 `select`／`call` 也掃進來）。
_SINK_ATTR_ONLY = frozenset({"select", "call"})

#: sink：整段點號路徑（`dataclasses.replace` ⛔ 不能只看 `replace`——字串也有 `.replace`）。
_SINK_DOTTED = frozenset({"dataclasses.replace"})


def _dotted(func: ast.AST) -> str:
    try:
        return ast.unparse(func)
    except Exception:                                    # pragma: no cover - 3.8 以下
        return ""


def _is_sink(func: ast.AST) -> bool:
    if _dotted(func) in _SINK_DOTTED:
        return True
    if isinstance(func, ast.Name):
        return func.id in _SINK_NAMES
    if isinstance(func, ast.Attribute):
        return func.attr in _SINK_NAMES or func.attr in _SINK_ATTR_ONLY
    return False


def _sink_label(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return "<call>"


def _is_seed(node: ast.AST) -> bool:
    """`slots["identity"]`／`flat.get("identity_detail")` 這兩種**取值**形狀。"""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        if node.value.id in TAINT_CONTAINERS and isinstance(node.ctx, ast.Load):
            key = node.slice
            if isinstance(key, ast.Constant) and key.value in TAINT_KEYS:
                return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        base = node.func.value
        if (
            node.func.attr == "get"
            and isinstance(base, ast.Name)
            and base.id in TAINT_CONTAINERS
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in TAINT_KEYS
        ):
            return True
    return False


def _contains_seed(node: ast.AST) -> bool:
    return any(_is_seed(child) for child in ast.walk(node))


def _mentions(node: ast.AST, names: "set[str]") -> bool:
    return any(isinstance(c, ast.Name) and c.id in names for c in ast.walk(node))


def _tainted_names(tree: ast.AST) -> "set[str]":
    """一層區域變數傳遞：種子 → 變數，再跑一輪讓 變數 → 變數 也算到。"""
    tainted: set = set()
    for _ in range(2):
        for node in ast.walk(tree):
            value = getattr(node, "value", None)
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) or value is None:
                continue
            if not (_contains_seed(value) or _mentions(value, tainted)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        tainted.add(name.id)
    return tainted


def find_identity_taint_into_sinks(source: str) -> "list[str]":
    """回傳「身分槽位流進 sink」的 sink 名稱清單（可重複）；語法錯誤回空。"""
    hits: list = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return hits

    tainted = _tainted_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_sink(node.func):
            continue
        args = list(node.args) + [kw.value for kw in node.keywords]
        for arg in args:
            if _contains_seed(arg) or _mentions(arg, tainted):
                hits.append(_sink_label(node.func))
                break
    return hits


def _iter_agent_service_files():
    assert AGENT_SERVICES_DIR.is_dir(), (
        f"正對照失敗：{AGENT_SERVICES_DIR} 不存在——查核目錄本身有問題，"
        "不是「查無污染」"
    )
    files = sorted(AGENT_SERVICES_DIR.rglob("*.py"))
    assert files, "services/agent/ 下找不到任何 .py 檔——掃描條件本身壞了"
    return files


# ---------------------------------------------------------------------------
# 正對照：每種 sink 形狀各一段假碼必紅
# ---------------------------------------------------------------------------
_POSITIVE_CONTROLS = {
    "dataclasses.replace": (
        "import dataclasses\n"
        "def f(identity, slots):\n"
        "    return dataclasses.replace(identity, target_user=slots['identity'])\n",
        "replace",
    ),
    "dataclass_replace": (
        "from dataclasses import replace as dataclass_replace\n"
        "def f(identity, flat):\n"
        "    return dataclass_replace(identity, mode=flat.get('identity_source'))\n",
        "dataclass_replace",
    ),
    "Identity(...)": (
        "def f(slots):\n"
        "    return Identity(vendor_id=1, target_user=slots['identity'])\n",
        "Identity",
    ),
    "build_visibility_predicate": (
        "def f(slots):\n"
        "    return build_visibility_predicate(slots['identity'])\n",
        "build_visibility_predicate",
    ),
    "fetch_visible_row": (
        "async def f(pool, slots):\n"
        "    return await fetch_visible_row(pool, slots['identity_detail'])\n",
        "fetch_visible_row",
    ),
    "canon_visible": (
        "def f(doc, flat):\n"
        "    return canon_visible(doc, flat.get('identity'))\n",
        "canon_visible",
    ),
    "build_canon_toc": (
        "def f(doc, slots):\n"
        "    return build_canon_toc(doc, slots['identity'])\n",
        "build_canon_toc",
    ),
    "resolve_canon_section": (
        "def f(doc, slots):\n"
        "    return resolve_canon_section(doc, slots['identity'], 'outline:x')\n",
        "resolve_canon_section",
    ),
    "visible_subset": (
        "def f(index, doc, slots):\n"
        "    return index.visible_subset(slots['identity'], doc)\n",
        "visible_subset",
    ),
    "CandidateSelector.select": (
        "async def f(selector, doc, slots, q):\n"
        "    return await selector.select(doc, slots['identity'], q)\n",
        "select",
    ),
    "registry.call": (
        "async def f(registry, slots, args):\n"
        "    return await registry.call(slots['identity'], 'kb.get', args, 3.0)\n",
        "call",
    ),
    "jgb2.query_bills": (
        "async def f(slots):\n"
        "    return await query_bills(slots['identity'], {})\n",
        "query_bills",
    ),
    "jgb2.query_contracts": (
        "async def f(slots):\n"
        "    return await query_contracts(slots['identity_detail'], {})\n",
        "query_contracts",
    ),
    "jgb2.query_meters": (
        "async def f(flat):\n"
        "    return await query_meters(flat.get('identity'), {})\n",
        "query_meters",
    ),
    "jgb2.query_accounts": (
        "async def f(slots):\n"
        "    return await query_accounts(slots['identity'], {})\n",
        "query_accounts",
    ),
    "jgb2.query_estates": (
        "async def f(slots):\n"
        "    return await query_estates(slots['identity'], {})\n",
        "query_estates",
    ),
    "kb_get": (
        "async def f(slots):\n"
        "    return await kb_get(slots['identity'], {'id': 1})\n",
        "kb_get",
    ),
    "kb_search": (
        "async def f(slots):\n"
        "    return await kb_search(slots['identity_source'], {'q': 'x'})\n",
        "kb_search",
    ),
}


@pytest.mark.parametrize("shape", sorted(_POSITIVE_CONTROLS))
def test_scanner_catches_every_sink_shape(shape):
    source, expected = _POSITIVE_CONTROLS[shape]
    hits = find_identity_taint_into_sinks(source)
    assert expected in hits, f"掃描器沒抓到 {shape} 這種形狀——掃描器本身失效"


def test_scanner_follows_one_level_of_local_variable():
    source = (
        "async def f(slots):\n"
        "    who = slots['identity']\n"
        "    same = who\n"
        "    return await kb_search(same, {'q': 'x'})\n"
    )
    assert "kb_search" in find_identity_taint_into_sinks(source)


def test_scanner_is_silent_on_clean_code():
    """乾淨樣本：非身分槽位進 sink、身分槽位只進 prompt 段 ⇒ 不得中。"""
    clean = (
        "def f(slots, identity, registry, args):\n"
        "    prompt_slots = dict(slots)\n"
        "    prompt_slots['identity'] = identity.resolved_audience()\n"
        "    n = slots['unit_count']\n"
        "    return kb_search(identity, {'q': n}), registry.call(identity, 'kb.get', args, 3.0)\n"
    )
    assert find_identity_taint_into_sinks(clean) == []


def test_scanner_ignores_unrelated_replace():
    """`str.replace` ⛔ 不是 sink（只有 `dataclasses.replace` 整段路徑才算）。"""
    source = (
        "def f(slots):\n"
        "    return slots['identity'].replace('a', 'b')\n"
    )
    assert find_identity_taint_into_sinks(source) == []


# ---------------------------------------------------------------------------
# 真原始碼必綠
# ---------------------------------------------------------------------------
def test_agent_services_dir_has_python_files():
    """正對照組：掃描目標非空（否則「查無污染」只是掃到空目錄）。"""
    assert len(_iter_agent_service_files()) > 0


@pytest.mark.parametrize("py_file", _iter_agent_service_files())
def test_no_identity_slot_reaches_a_sink(py_file):
    hits = find_identity_taint_into_sinks(py_file.read_text(encoding="utf-8"))
    assert hits == [], (
        f"{py_file.relative_to(REPO_ROOT)} 把身分槽位餵進了 {sorted(set(hits))}——"
        "對話內容不得決定資料可見範圍"
    )
