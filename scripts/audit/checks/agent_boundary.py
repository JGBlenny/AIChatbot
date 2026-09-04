#!/usr/bin/env python3
"""Agent／MCP 邊界不變量（spec agentic-mcp-orchestration・任務 1.2）。

design.md 附錄 B 稱這五條為「不變量 18–22」，但合併時發現
`scripts/audit/check_invariants.sh` 現況的 18–22 已被另一條工作線
（R10-P2/P3/P4、canonical contract、registry V2 scope lock）占用——
兩條工作線各自遞增到相同號碼後才合併，是編號衝突，非同一件事被覆寫。
已記錄 DSP-013（`python3 ~/.claude/canon/decisions.py unresolved`），
業主裁決前本檔＋`check_invariants.sh` 一律採用**不衝突**的新編號
27–31，並在每條輸出中保留 design.md 的原始編號以利對照。

| 本檔 print 的編號 | design.md 附錄 B 編號 | 內容 |
|---|---|---|
| 27 | 18 | `ToolSpec.input_schema` 無身分鍵（掃 `services/agent/**/*.py`）|
| 28 | 19 | `_EXEMPT_PREFIX` 不含 `/mcp`；門面內不得出現 `auth_enforced` |
| 29 | 20 | 可見性謂詞單一來源（`build_visibility_predicate`） |
| 30 | 21 | `decision_snapshot.agent*` 無原文鍵 |
| 31 | 22 | `/mcp` 每呼叫一列 `usage_events`（登記，見 1.7） |

用法：python3 scripts/audit/checks/agent_boundary.py [--self-test]
"""
import ast
import os
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def _resolve_rag_root():
    """`rag-orchestrator/` 的絕對路徑。

    ⚠️ 本檔會在兩種佈局下跑：① host（`make audit`）——`REPO/rag-orchestrator`
    存在；② pytest 測試容器（`docker-compose.dev.yml`）——`./rag-orchestrator`
    掛在 `/app`、`./scripts` 另掛在 `/scripts`，兩者在容器內不是同一棵樹的
    子目錄，`REPO/rag-orchestrator` 算不出正確路徑。`RAG_ORCHESTRATOR_ROOT`
    env var 提供第三種明示覆寫（供未來佈局變動時不必再改本檔）。"""
    override = os.environ.get("RAG_ORCHESTRATOR_ROOT")
    if override and os.path.isdir(override):
        return override
    candidate = os.path.join(REPO, "rag-orchestrator")
    if os.path.isdir(candidate):
        return candidate
    if os.path.isdir("/app") and os.path.isdir(os.path.join("/app", "services")):
        return "/app"
    return candidate


RAG = _resolve_rag_root()

IDENTITY_KEYS = frozenset(
    {"vendor_id", "role_id", "user_id", "target_user", "mode", "viewer_user_id"}
)
DECISION_BANNED_KEYS = frozenset({"answer", "quote", "text", "user_message"})


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _parse(src):
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


# ───────────────────────── 27（design 18）ToolSpec.input_schema 無身分鍵 ─────────────────────────

def _dict_str_keys(node):
    """`ast.Dict` 字面量的字串鍵集合（跳過非常數鍵，例如 `**spread`）。"""
    keys = set()
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            keys.add(k.value)
    return keys


def _find_input_schema_dicts(tree, src):
    """掃 `ToolSpec(...)`／`register(...)` 呼叫裡 `input_schema=` 或
    `"input_schema":` 對應的字典字面量，回傳其 `properties` 鍵集合的清單
    （含所在行號方便定位）。"""
    found = []  # [(lineno, properties_keys)]
    for node in ast.walk(tree):
        schema_dict = None
        lineno = getattr(node, "lineno", 0)
        if isinstance(node, ast.Call):
            fname = ""
            if isinstance(node.func, ast.Name):
                fname = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fname = node.func.attr
            if fname in ("ToolSpec", "register"):
                for kw in node.keywords:
                    if kw.arg == "input_schema" and isinstance(kw.value, ast.Dict):
                        schema_dict = kw.value
                # 位置參數字典（ToolSpec({...}) 之類）也掃
                for arg in node.args:
                    if isinstance(arg, ast.Dict) and "input_schema" in ast.dump(arg):
                        pass  # 字典本身不含自身鍵名，交由下方字面量掃描兜底
        elif isinstance(node, ast.Dict):
            keys = _dict_str_keys(node)
            if "input_schema" in keys:
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "input_schema" and isinstance(v, ast.Dict):
                        schema_dict = v
        if schema_dict is not None:
            props_keys = set()
            for k, v in zip(schema_dict.keys, schema_dict.values):
                if isinstance(k, ast.Constant) and k.value == "properties" and isinstance(v, ast.Dict):
                    props_keys |= _dict_str_keys(v)
            found.append((lineno, props_keys))
    return found


def _agent_py_paths():
    """`services/agent/**/*.py` 的相對路徑清單（走訪方式比照 `check_30`）。

    ⚠️ **1.10 修**：本檢查原本只掃 `services/agent/tools/registry.py`，
    但那裡沒有任何 `input_schema` 字面量——真正的 spec 住在
    `services/agent/tools/kb.py`（`KB_GET_SPEC`／`KB_SEARCH_SPEC`）與
    `services/agent/mcp_facade.py`（`HELP_READ_SPEC`／`_jgb2_spec`）。
    於是這條不變量長期掃到 0 個 spec 卻印綠燈（空跑綠燈）。
    """
    out = []
    agent_dir = os.path.join(RAG, "services", "agent")
    if os.path.isdir(agent_dir):
        for root, _dirs, files in os.walk(agent_dir):
            for fn in sorted(files):
                if fn.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(root, fn), RAG))
    return sorted(out)


def scan_27_specs(src=None, path=None, paths=None):
    """回傳 `(specs, errors)`。

    `specs` = `[(rel, lineno, properties_keys)]`；`errors` = 硬錯誤字串清單
    （檔案讀不到、AST 掃不動——一律大聲失敗，⛔ 不吞成「空集合通過」）。

    三種輸入模式：`src=` 單一記憶體來源（自測用）／`paths=` 明示清單／
    兩者皆無 ⇒ 走訪 `services/agent/**/*.py`。
    """
    if src is not None:
        sources = [(path or "<src>", src)]
    else:
        rels = list(paths) if paths is not None else _agent_py_paths()
        sources = []
        for rel in rels:
            sources.append((rel, _read(os.path.join(RAG, rel))))

    specs, errors = [], []
    for rel, text in sources:
        if text is None:
            errors.append(f"{rel} 讀不到——大聲失敗")
            continue
        tree = _parse(text)
        if tree is None:
            errors.append(f"{rel} 語法錯誤，無法 AST 掃描——大聲失敗")
            continue
        for lineno, keys in _find_input_schema_dicts(tree, text):
            specs.append((rel, lineno, keys))
    return specs, errors


def check_27_toolspec_identity_keys(src=None, path=None, paths=None):
    """design 18：`ToolSpec.input_schema` 不得含身分鍵。

    掃描範圍預設 `services/agent/**/*.py`（見 `_agent_py_paths`）。
    **掃到 0 個 spec ⇒ FAIL**——這條不變量的價值全靠「真的掃到東西」，
    掃不到只可能是路徑錯了或 spec 搬家了，⛔ 不得再印「空集合通過」。
    """
    specs, errors = scan_27_specs(src=src, path=path, paths=paths)
    label = (path or "<src>") if src is not None else (
        "、".join(paths) if paths is not None else "services/agent/**/*.py")
    if errors:
        return False, f"{label}：" + "；".join(errors)
    if not specs:
        return False, (f"{label}：掃到 0 個帶 input_schema 的 ToolSpec/register "
                       "字面量——大聲失敗（這條不變量若掃不到東西就只是空跑綠燈；"
                       "spec 可能搬家了，請更新掃描路徑）")
    bad = []
    for rel, lineno, keys in specs:
        hit = keys & IDENTITY_KEYS
        if hit:
            bad.append(f"{rel} 第 {lineno} 行 input_schema.properties 含身分鍵 {sorted(hit)}")
    if bad:
        return False, "；".join(bad)
    files = sorted({rel for rel, _l, _k in specs})
    return True, (f"{label}：掃到 {len(specs)} 個 input_schema（分佈於 {len(files)} 個檔："
                  f"{'、'.join(files)}），均無身分鍵")


# ───────────────────────── 28（design 19）/mcp 無條件 401；門面不得看 auth_enforced ─────────────────────────

def check_28_mcp_auth_unconditional(auth_src=None, facade_paths=None):
    """design 19：`_EXEMPT_PREFIX` 不含 `/mcp`；`mcp_facade.py`／`routers/agent.py`
    內不得出現 `auth_enforced` 名稱（否則等於讓 `/mcp` 又受
    `RAG_API_AUTH_ENFORCE` 擺佈）。"""
    auth_path = "services/api_key_auth.py"
    if auth_src is None:
        auth_src = _read(os.path.join(RAG, auth_path))
    bad = []
    if auth_src is None:
        bad.append(f"{auth_path} 不存在——找不到 _EXEMPT_PREFIX，大聲失敗")
    else:
        tree = _parse(auth_src)
        exempt_val = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "_EXEMPT_PREFIX" for t in node.targets
                ):
                    exempt_val = ast.literal_eval(node.value) if isinstance(node.value, (ast.Tuple, ast.List)) else None
        if exempt_val is None:
            bad.append(f"{auth_path} 找不到 `_EXEMPT_PREFIX = (...)` 字面量賦值——大聲失敗")
        elif any(str(p).startswith("/mcp") for p in exempt_val):
            bad.append(f"{auth_path}：_EXEMPT_PREFIX 含 /mcp（{exempt_val}）——/mcp 會變成不需認證")

    facade_paths = facade_paths or ["services/agent/mcp_facade.py", "routers/agent.py"]
    notes = []
    for rel in facade_paths:
        src = _read(os.path.join(RAG, rel))
        if src is None:
            notes.append(f"{rel} 尚未建立，略過")
            continue
        if "auth_enforced" in src:
            bad.append(f"{rel} 出現 `auth_enforced`——/mcp 認證不得受 RAG_API_AUTH_ENFORCE 左右")
    return (len(bad) == 0), ("；".join(bad) if bad else "；".join(notes) or "通過")


# ───────────────────────── 29（design 20）可見性謂詞單一來源 ─────────────────────────

PREDICATE_FUNC = "build_visibility_predicate"
_BANNED_COLS = ("vendor_ids", "business_types")


def _func_node(tree, qualname):
    """支援 `mod.py:func_name` 形式；找 `FunctionDef`/`AsyncFunctionDef`。"""
    name = qualname.split(":")[-1]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _where_fragment(s: str) -> str:
    """只取 SQL 字面量裡 `WHERE` 之後、或本身以 `AND` 開頭的片段——
    否則 SELECT 投影裡的 `kb.vendor_ids`／`kb.business_types` 欄位名
    會被誤判成 WHERE 條件（design.md 附錄 B 已知風險，2026-09-04）。"""
    stripped = s.strip()
    up = s.upper()
    idx = up.find("WHERE")
    if idx != -1:
        return s[idx:]
    if stripped.upper().startswith("AND"):
        return s
    return ""


def _string_constants(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            yield n.value


def _calls_predicate(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id == PREDICATE_FUNC:
                return True
            if isinstance(f, ast.Attribute) and f.attr == PREDICATE_FUNC:
                return True
    return False


def check_29_predicate_single_source(targets=None):
    """design 20：`_vector_search`／`_keyword_search`／`fetch_visible_row`／
    `build_prospect_outline` 的函式本體字串常數（限 WHERE/AND 片段）不得
    含 `vendor_ids`／`business_types`；且必須呼叫 `build_visibility_predicate`。"""
    targets = targets or [
        ("services/vendor_knowledge_retriever_v2.py", "_vector_search"),
        ("services/vendor_knowledge_retriever_v2.py", "_keyword_search"),
        ("services/agent/tools/kb.py", "fetch_visible_row"),
        ("services/agent/outline.py", "_fetch_prospect_pool_rows"),
    ]
    bad = []
    notes = []
    checked = 0
    for rel, fname in targets:
        src = _read(os.path.join(RAG, rel))
        if src is None:
            notes.append(f"{rel} 尚未建立，略過")
            continue
        tree = _parse(src)
        if tree is None:
            bad.append(f"{rel} 語法錯誤，無法 AST 掃描——大聲失敗")
            continue
        fn = _func_node(tree, fname)
        if fn is None:
            notes.append(f"{rel}:{fname} 找不到此函式，略過")
            continue
        checked += 1
        for s in _string_constants(fn):
            frag = _where_fragment(s)
            if not frag:
                continue
            for col in _BANNED_COLS:
                if col in frag:
                    bad.append(f"{rel}:{fname} 的 SQL WHERE/AND 片段直接寫死 `{col}`"
                               f"（未經 {PREDICATE_FUNC} 這道單一來源）")
        if not _calls_predicate(fn):
            bad.append(f"{rel}:{fname} 未呼叫 {PREDICATE_FUNC}()——謂詞不是單一來源")
    info = ("INFO：舊鏈另有手抄可見性條件未搬、⛔ 本不變量不動它們（1.1 留項③，"
            "見 tasks.md 收案註記）——"
            "services/conversational_engine.py:_grounding_by_ids（研究筆記指出無業者過濾）、"
            "services/conversational_engine.py:_grounding_by_category、"
            "services/system_context.py:_fetch_base。")
    if bad:
        return False, "；".join(bad)
    detail = f"{checked} 個函式已檢查，均引用 {PREDICATE_FUNC} 且無字面違禁欄位" if checked else "0 個函式存在，通過（空集合）"
    if notes:
        detail += "；" + "；".join(notes)
    return True, detail + "。" + info


# ───────────────────────── 30（design 21）decision_snapshot.agent* 無原文鍵 ─────────────────────────

def _set_decision_dict_literals(tree):
    """找 `set_decision(...)` 呼叫裡的字典字面量引數（含關鍵字 `snapshot=`
    與位置引數），回傳每個字典字面量的鍵集合清單。"""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fname = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else "")
            if fname != "set_decision":
                continue
            dicts = [a for a in node.args if isinstance(a, ast.Dict)]
            dicts += [kw.value for kw in node.keywords if isinstance(kw.value, ast.Dict)]
            for d in dicts:
                out.append((node.lineno, d))
    return out


def _flatten_dict_keys(d: ast.Dict):
    """遞迴收集字典字面量（含巢狀字典字面量值）裡出現過的所有字串鍵。"""
    keys = set()
    for k, v in zip(d.keys, d.values):
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            keys.add(k.value)
        if isinstance(v, ast.Dict):
            keys |= _flatten_dict_keys(v)
    return keys


def check_30_decision_snapshot_no_verbatim(paths=None):
    """design 21：`set_decision(...)` 傳入的字典字面量鍵名不得為
    `answer`／`quote`／`text`／`user_message`（原文外洩到 decision_snapshot）。"""
    paths = paths or ["services/usage_metering.py"]
    agent_dir = os.path.join(RAG, "services", "agent")
    if os.path.isdir(agent_dir):
        for root, _dirs, files in os.walk(agent_dir):
            for fn in files:
                if fn.endswith(".py"):
                    rel = os.path.relpath(os.path.join(root, fn), RAG)
                    if rel not in paths:
                        paths.append(rel)
    bad = []
    notes = []
    checked = 0
    for rel in paths:
        src = _read(os.path.join(RAG, rel))
        if src is None:
            notes.append(f"{rel} 尚未建立，略過")
            continue
        tree = _parse(src)
        if tree is None:
            bad.append(f"{rel} 語法錯誤——大聲失敗")
            continue
        calls = _set_decision_dict_literals(tree)
        checked += len(calls)
        for lineno, d in calls:
            hit = _flatten_dict_keys(d) & DECISION_BANNED_KEYS
            if hit:
                bad.append(f"{rel} 第 {lineno} 行 set_decision(...) 字典含原文鍵 {sorted(hit)}")
    if bad:
        return False, "；".join(bad)
    detail = f"{checked} 個 set_decision(...) 字典字面量已檢查，均無原文鍵" if checked else "0 個呼叫，通過（空集合）"
    if notes:
        detail += "；" + "；".join(notes)
    return True, detail


# ───────────────────────── 31（design 22）/mcp 每呼叫一列 usage_events ─────────────────────────

def check_31_mcp_usage_events_coverage(path="tests/integration/agent/test_mcp_facade_req.py"):
    """design 22：屬整合測試（任務 1.7 落地）。本 checker 只登記覆蓋
    測試檔是否存在——不存在 ⇒ WARN（非 FAIL），避免在 1.7 完成前把
    make audit 卡死在一條尚不該紅的規則上。"""
    full = os.path.join(REPO, "rag-orchestrator", path)
    if os.path.exists(full):
        return True, f"由 {path} 覆蓋"
    return None, f"{path} 不存在——WARN：/mcp 每呼叫一列 usage_events 待任務 1.7 落地，尚無測試覆蓋"


CHECKS = [
    (27, "ToolSpec.input_schema 無身分鍵（design 18）", check_27_toolspec_identity_keys),
    (28, "/mcp 無條件 401（design 19）", check_28_mcp_auth_unconditional),
    (29, "可見性謂詞單一來源（design 20）", check_29_predicate_single_source),
    (30, "decision_snapshot.agent* 無原文鍵（design 21）", check_30_decision_snapshot_no_verbatim),
]


def _self_test_27():
    good_src = (
        "from services.agent.tools.registry import ToolSpec\n"
        "SPEC = ToolSpec(name='kb.search', input_schema={'properties': {'query': {'type': 'string'}}})\n"
    )
    bad_src = (
        "from services.agent.tools.registry import ToolSpec\n"
        "SPEC = ToolSpec(name='kb.get', input_schema={'properties': {'kb_id': {'type': 'string'}, 'vendor_id': {'type': 'integer'}}})\n"
    )
    kb_specs, kb_errors = scan_27_specs(paths=["services/agent/tools/kb.py"])
    all_specs, all_errors = scan_27_specs()
    all_files = {rel for rel, _l, _k in all_specs}
    cases = [
        ("正對照：現況 services/agent/**/*.py 通過",
         check_27_toolspec_identity_keys()[0] is True),
        ("正對照：kb.py 掃到 ≥2 個 input_schema（不是空跑）",
         len(kb_specs) >= 2 and not kb_errors),
        ("正對照：預設走訪至少涵蓋 2 個檔（kb.py ＋ mcp_facade.py）",
         len(all_files) >= 2 and not all_errors),
        ("正對照：mcp_facade.py 的 spec 有被掃到",
         any(rel.endswith("mcp_facade.py") for rel in all_files)),
        ("假 spec 無身分鍵 → 通過", check_27_toolspec_identity_keys(src=good_src)[0] is True),
        ("假 spec 含 vendor_id → 必須紅", check_27_toolspec_identity_keys(src=bad_src)[0] is False),
        ("假檔只有一個乾淨 spec 也算掃到 → 通過",
         check_27_toolspec_identity_keys(src=good_src, path="services/_fake_spec.py")[0] is True),
        ("空來源（0 個 spec）→ 必須紅（大聲失敗，⛔ 不再印空集合通過）",
         check_27_toolspec_identity_keys(src="X = 1\n")[0] is False),
        ("不存在的檔案 → 必須紅（讀不到＝大聲失敗）",
         check_27_toolspec_identity_keys(paths=["services/agent/tools/does_not_exist.py"])[0] is False),
    ]
    return cases


def _self_test_28():
    good_auth = '_EXEMPT_PREFIX = ("/docs", "/redoc", "/openapi")\n'
    bad_auth = '_EXEMPT_PREFIX = ("/docs", "/mcp")\n'
    with tempfile.TemporaryDirectory() as td:
        clean = os.path.join(td, "mcp_facade.py")
        with open(clean, "w") as f:
            f.write("def handler():\n    return 1\n")
        dirty = os.path.join(td, "mcp_facade_bad.py")
        with open(dirty, "w") as f:
            f.write("from services.api_key_auth import auth_enforced\n"
                    "def handler():\n    if auth_enforced():\n        pass\n")

        def facade_check(paths):
            return check_28_mcp_auth_unconditional(auth_src=good_auth, facade_paths=paths)

        cases = [
            ("正對照：現況 api_key_auth.py 通過", check_28_mcp_auth_unconditional()[0] is True),
            ("_EXEMPT_PREFIX 含 /mcp → 必須紅", check_28_mcp_auth_unconditional(auth_src=bad_auth, facade_paths=[])[0] is False),
            ("_EXEMPT_PREFIX 不存在 → 大聲失敗", check_28_mcp_auth_unconditional(auth_src="X = 1\n", facade_paths=[])[0] is False),
            ("門面不存在 → 略過（不誤報綠當紅、也不假裝有檔案）",
             check_28_mcp_auth_unconditional(auth_src=good_auth, facade_paths=[os.path.join(td, "nope.py")])[0] is True),
            ("門面存在但乾淨 → 通過", facade_check([clean])[0] is True),
            ("門面出現 auth_enforced → 必須紅", facade_check([dirty])[0] is False),
        ]
    return cases


def _self_test_29():
    global _read
    clean_src = (
        "def _vector_search():\n"
        "    visibility_sql, params = build_visibility_predicate(identity)\n"
        "    sql = f'''SELECT kb.id, kb.vendor_ids, kb.business_types FROM knowledge_base kb\\n"
        "        WHERE kb.embedding IS NOT NULL {visibility_sql}'''\n"
        "    return sql\n"
    )
    dirty_hardcode = (
        "def _vector_search():\n"
        "    sql = '''SELECT kb.id FROM knowledge_base kb\\n"
        "        WHERE kb.is_active AND kb.vendor_ids && %s::int[]'''\n"
        "    return sql\n"
    )
    dirty_no_call = (
        "def _vector_search():\n"
        "    sql = 'SELECT kb.id FROM knowledge_base kb WHERE kb.is_active'\n"
        "    return sql\n"
    )
    tgt_clean = [("services/_fake_clean.py", "_vector_search")]
    tgt_dirty1 = [("services/_fake_dirty1.py", "_vector_search")]
    tgt_dirty2 = [("services/_fake_dirty2.py", "_vector_search")]

    orig_read = _read
    fakes = {
        os.path.join(RAG, "services/_fake_clean.py"): clean_src,
        os.path.join(RAG, "services/_fake_dirty1.py"): dirty_hardcode,
        os.path.join(RAG, "services/_fake_dirty2.py"): dirty_no_call,
    }

    def fake_read(path):
        return fakes.get(path, orig_read(path))

    _read = fake_read
    try:
        cases = [
            ("正對照：現況兩個真函式通過", check_29_predicate_single_source()[0] is True),
            ("假函式：SELECT 投影含 vendor_ids/business_types 但 WHERE 片段乾淨 → 不誤報",
             check_29_predicate_single_source(targets=tgt_clean)[0] is True),
            ("假函式：WHERE 片段字面寫死 vendor_ids → 必須紅",
             check_29_predicate_single_source(targets=tgt_dirty1)[0] is False),
            ("假函式：完全不呼叫 build_visibility_predicate → 必須紅",
             check_29_predicate_single_source(targets=tgt_dirty2)[0] is False),
            ("不存在的目標函式 → 略過通過",
             check_29_predicate_single_source(targets=[("services/nope.py", "x")])[0] is True),
        ]
    finally:
        _read = orig_read
    return cases


def _self_test_30():
    global _read
    clean_src = "def f():\n    set_decision(snapshot={'presales': {'gate': 'B'}})\n"
    dirty_src = "def f():\n    set_decision(snapshot={'agent': {'answer': a}})\n"
    dirty_nested = "def f():\n    set_decision(snapshot={'agent': {'meta': {'quote': q}}})\n"

    orig_read = _read
    fakes = {
        os.path.join(RAG, "services/_fake_um_clean.py"): clean_src,
        os.path.join(RAG, "services/_fake_um_dirty.py"): dirty_src,
        os.path.join(RAG, "services/_fake_um_nested.py"): dirty_nested,
    }

    def fake_read(path):
        return fakes.get(path, orig_read(path))

    _read = fake_read
    try:
        cases = [
            ("正對照：現況 usage_metering.py + services/agent/** 通過",
             check_30_decision_snapshot_no_verbatim()[0] is True),
            ("假檔：無原文鍵 → 通過",
             check_30_decision_snapshot_no_verbatim(paths=["services/_fake_um_clean.py"])[0] is True),
            ("假檔：answer 鍵 → 必須紅",
             check_30_decision_snapshot_no_verbatim(paths=["services/_fake_um_dirty.py"])[0] is False),
            ("假檔：巢狀字典裡的 quote 鍵 → 必須紅",
             check_30_decision_snapshot_no_verbatim(paths=["services/_fake_um_nested.py"])[0] is False),
        ]
    finally:
        _read = orig_read
    return cases


def self_test() -> int:
    all_cases = []
    all_cases += _self_test_27()
    all_cases += _self_test_28()
    all_cases += _self_test_29()
    all_cases += _self_test_30()
    for name, ok in all_cases:
        print(f"{'✅' if ok else '❌'} {name}")
    ok31, detail31 = check_31_mcp_usage_events_coverage()
    print(f"{'⚠️ ' if ok31 is None else ('✅' if ok31 else '❌')} 31（design 22）登記：{detail31}")
    return 1 if any(not ok for _n, ok in all_cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    fail = False
    for num, label, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            print(f"❌ 不變量 {num}：{label} —— 檢查無法執行（{e}）——大聲失敗")
            fail = True
            continue
        print(f"{'✅' if ok else '❌'} 不變量 {num}：{label} —— {detail}")
        if not ok:
            fail = True
    ok31, detail31 = check_31_mcp_usage_events_coverage()
    if ok31 is None:
        print(f"⚠️  不變量 31：/mcp 每呼叫一列 usage_events（design 22）—— {detail31}")
    else:
        print(f"{'✅' if ok31 else '❌'} 不變量 31：/mcp 每呼叫一列 usage_events（design 22）—— {detail31}")
        fail = fail or (not ok31)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
