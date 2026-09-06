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
| 32 | —  | 內容已審謂詞單一來源（spec knowledge-outline-and-intent-architecture 3.1）|

32 不屬於上表那條編號衝突：它來自另一個 spec，附錄 B 直接就叫「不變量 32」。
31／32 都是**三態**（PASS／WARN・SKIP／FAIL），故與 27–30 一樣放在 `CHECKS` 之外，
由 `main()` 各自印——放進 `CHECKS` 會讓 `ok is None` 被當成 FAIL。

用法：python3 scripts/audit/checks/agent_boundary.py [--self-test]
"""
import ast
import importlib.util
import os
import subprocess
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

_DECISION_CALL_NAMES = frozenset({"set_decision", "set_agent_decision"})


def _set_decision_dict_literals(tree):
    """找 `set_decision(...)`／`set_agent_decision(...)` 呼叫裡的字典字面量
    引數（含關鍵字 `snapshot=` 與位置引數），回傳每個字典字面量的鍵集合清單。

    ⚠️ **只認字面量**：這是靜態掃描，掃不到「先組成變數再傳進去」的呼叫——
    這是刻意的邊界，不是漏洞（見 `runtime.py:_emit_agent_decision` 的呼叫點
    docstring）：呼叫端若真的把 dict 拆成變數再傳，等於自己選擇跳出這條
    不變量的可視範圍，責任在呼叫端，不是這條 checker 該用執行期手段去追。
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fname = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else "")
            if fname not in _DECISION_CALL_NAMES:
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


def _agent_rel(rel: str) -> bool:
    return rel.replace(os.sep, "/").startswith("services/agent/")


def check_30_decision_snapshot_no_verbatim(paths=None, agent_root=None):
    """design 21：`set_decision(...)`／`set_agent_decision(...)` 傳入的字典
    字面量鍵名（遞迴掃巢狀字典）不得為 `answer`／`quote`／`text`／
    `user_message`（原文外洩到 decision_snapshot）。

    **r7 處置**：比照 `check_27`——`services/agent/**` 路徑下 0 個這類呼叫
    ⇒ **大聲失敗**，⛔ 不再印「空集合通過」。理由同 27：這條不變量的價值
    全靠「真的掃到 agent 路徑有落地計量」，2.5 接線後 `runtime.py` 一定會
    有至少一個呼叫，掃到 0 個只可能是接線斷了或這條不變量自己失焦。

    `agent_root` 只給自測用（覆寫 `services/agent/` 目錄的實際掃描位置，
    讓自測能建構「agent 路徑真的 0 個呼叫」這個情境而不必動到真檔案）。
    """
    paths = list(paths) if paths is not None else ["services/usage_metering.py"]
    agent_dir = agent_root if agent_root is not None else os.path.join(RAG, "services", "agent")
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
    agent_calls = 0
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
        if _agent_rel(rel):
            agent_calls += len(calls)
        for lineno, d in calls:
            hit = _flatten_dict_keys(d) & DECISION_BANNED_KEYS
            if hit:
                bad.append(
                    f"{rel} 第 {lineno} 行 set_decision/set_agent_decision(...) "
                    f"字典含原文鍵 {sorted(hit)}"
                )
    if bad:
        return False, "；".join(bad)
    if agent_calls == 0:
        detail = (
            "services/agent/** 路徑下 0 個 set_decision/set_agent_decision 呼叫——"
            "大聲失敗（agent runtime 應該要落 decision_snapshot.agent，見 tasks 2.5；"
            "掃到 0 個代表 2.5 的計量接線斷了，不是「還沒有原文外洩」）"
        )
        if notes:
            detail += "；" + "；".join(notes)
        return False, detail
    detail = f"{checked} 個字典字面量已檢查（其中 agent 路徑 {agent_calls} 個），均無原文鍵"
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


# ───────────────────────── 32 內容已審謂詞單一來源（spec knowledge-outline-and-intent-architecture 3.1）─────────────────────────
#
# 不變量：`outline_approved_by` 這個欄位名的**字串常數**只准出現在
# `services/agent/canon/review_state.py`；掃描面＝`services/agent/**` ＋ `tools/**`
# （排除 tests）。⛔ 無豁免表（業主 2026-09-07 裁 (a)）。
#
# ⚠️ **掃描範圍刻意界定為 AST 字串常數**（`ast.Constant(str)`，含 f-string 的
# 字面片段），⛔ 不含 docstring、識別字（dataclass 欄位名、kwarg、屬性）、註解。
# 理由：謂詞繞過只可能發生在**送進 DB 的 SQL 字串**——把 docstring 也算進來，
# 只會逼人把說明刪掉，不會多擋任何一條繞過路徑。
#
# 三個子檢查，缺一不可：
#   ① 字面越界 ⇒ FAIL（列出 file:line）
#   ② `review_state` 使用命中 <1 ⇒ FAIL（空跑不得綠：掃描面搬家或接線斷了時，
#      「沒有越界字面」這個結論是假的）
#   ③ DB 側值域外列數（psql 不可達 ⇒ **FAIL，⛔ 不是 SKIP**）

REVIEW_STATE_REL = "services/agent/canon/review_state.py"

#: 32 專用的 review_state 符號（被 import 或被呼叫都算「使用」）。
_REVIEW_STATE_SYMBOLS = ("content_reviewed_predicate", "COLUMN")

#: D1 前預期的唯一值域外值（現況 29 列）。⛔ 不是豁免表——它只決定
#: 「印 SKIP(pending-D1) 還是實紅」，任何**其他**值都直接 FAIL。
_PENDING_D1_VALUE = "owner-20260905"


def _load_review_state(rag_root=None):
    """把 `review_state.py` 當獨立模組載進來（它只 import `re`／`typing`，無套件相依）。

    ⛔ 不在本檔複製 `COLUMN`／`DOMAIN_REGEX`——那等於再開一個真值來源，
    正是這條不變量要擋的事。載不到 ⇒ 讓呼叫端大聲失敗。
    """
    root = rag_root if rag_root is not None else RAG
    path = os.path.join(root, REVIEW_STATE_REL)
    spec = importlib.util.spec_from_file_location("_inv32_review_state", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{REVIEW_STATE_REL} 載不進來（路徑 {path}）")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _review_state_paths(rag_root=None):
    """**只供 32**：`services/agent/**/*.py` ＋ `tools/**/*.py`（排除任何 tests 目錄）。

    ⛔ 不與 `_agent_py_paths()`（27／30 用）共用——那支只走 `services/agent/`，
    改它會連帶動到另外兩條不變量的掃描面（design 附錄 B E7）。
    """
    root = rag_root if rag_root is not None else RAG
    out = []
    for sub in (os.path.join("services", "agent"), "tools"):
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for cur, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in ("tests", "__pycache__"))
            for fn in sorted(files):
                if fn.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(cur, fn), root))
    return sorted(out)


def _docstring_constant_ids(tree):
    """module／class／function body 首個 `Expr(Constant str)` 的節點 id 集合。"""
    ids = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            ids.add(id(first.value))
    return ids


def _non_docstring_str_constants(tree):
    """`[(lineno, value)]`：所有字串常數（含 f-string 字面片段），**排除 docstring**。"""
    docs = _docstring_constant_ids(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append((getattr(node, "lineno", 0), node.value))
    return out


def _uses_review_state(tree):
    """這個檔有沒有從 `review_state` 取用單一來源（import 符號或呼叫謂詞）。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("review_state"):
            for alias in node.names:
                if alias.name in _REVIEW_STATE_SYMBOLS:
                    return True
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "content_reviewed_predicate":
                return True
            if isinstance(f, ast.Attribute) and f.attr == "content_reviewed_predicate":
                return True
    return False


def scan_32_literals(paths=None, rag_root=None, column=None):
    """回 `(bad, usage_files, scanned, errors)`。

    `bad` = `[(rel, lineno)]` 越界字面；`usage_files` = 有使用 `review_state` 的檔；
    `errors` = 硬錯誤（讀不到／語法錯，⛔ 一律大聲失敗不吞成空集合）。
    """
    root = rag_root if rag_root is not None else RAG
    col = column if column is not None else _load_review_state(rag_root).COLUMN
    rels = list(paths) if paths is not None else _review_state_paths(rag_root)
    bad, usage_files, errors = [], [], []
    scanned = 0
    for rel in rels:
        text = _read(os.path.join(root, rel))
        if text is None:
            errors.append(f"{rel} 讀不到——大聲失敗")
            continue
        tree = _parse(text)
        if tree is None:
            errors.append(f"{rel} 語法錯誤，無法 AST 掃描——大聲失敗")
            continue
        scanned += 1
        norm = rel.replace(os.sep, "/")
        if norm != REVIEW_STATE_REL:
            for lineno, value in _non_docstring_str_constants(tree):
                if col in value:
                    bad.append((rel, lineno))
        if _uses_review_state(tree):
            usage_files.append(rel)
    return bad, sorted(set(usage_files)), scanned, errors


def psql_query_32(sql):
    """`docker exec … psql -tAc`（比照 `scripts/audit/checks/retired_row_isolation.py`）。

    ⛔ 失敗一律丟例外——psql 不可達時**不得**當成「沒有違規」（F5）。
    """
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip() or out.stdout.strip()}")
    return out.stdout


def check_32_review_state_single_source(paths=None, rag_root=None, query=None):
    """32：內容已審謂詞單一來源（三態：True／None＝SKIP(pending-D1)／False）。

    `query` 只給自測用（注入假查詢函式，⛔ 不連 DB）；預設走 `psql_query_32`。
    """
    try:
        rs = _load_review_state(rag_root)
    except Exception as e:  # noqa: BLE001
        return False, f"{REVIEW_STATE_REL} 載不進來（{e}）——單一來源不存在，大聲失敗"

    bad, usage_files, scanned, errors = scan_32_literals(
        paths=paths, rag_root=rag_root, column=rs.COLUMN)
    if errors:
        return False, "；".join(errors)
    if bad:
        listed = "、".join(f"{rel}:{lineno}" for rel, lineno in bad)
        return False, (f"`{rs.COLUMN}` 字面出現在 {REVIEW_STATE_REL} 以外的字串常數："
                       f"{listed}——⛔ 無豁免表，一律改用 review_state 的常數／謂詞")
    if len(usage_files) < 1:
        return False, (f"掃了 {scanned} 個檔，但 0 個檔使用 review_state"
                       f"（import {'／'.join(_REVIEW_STATE_SYMBOLS)} 或呼叫謂詞）——"
                       "大聲失敗：沒有任何消費端時「無越界字面」是空跑綠燈，"
                       "只代表掃描面搬家了或接線斷了")

    static_detail = (f"掃 {scanned} 個檔（services/agent/**＋tools/**，排除 tests）"
                     f"無越界字面；{len(usage_files)} 個檔取用單一來源"
                     f"（{'、'.join(usage_files)}）")

    q = query if query is not None else psql_query_32
    try:
        total = int(q("SELECT count(*) FROM knowledge_base").strip())
        raw = q("SELECT outline_approved_by || '|' || count(*)::text "
                "FROM knowledge_base "
                "WHERE outline_approved_by IS NOT NULL "
                f"AND outline_approved_by !~ '{rs.DOMAIN_REGEX}' "
                "GROUP BY outline_approved_by ORDER BY 1")
        derived = int(q("SELECT count(*) FROM knowledge_base "
                        "WHERE generation_metadata->>'canon_ref' IS NOT NULL").strip())
    except Exception as e:  # noqa: BLE001
        return False, (f"{static_detail}；但 DB 子檢查無法執行（{e}）——"
                       "⛔ 大聲失敗，不當成「沒有值域外的列」")

    # 正對照：knowledge_base 必然非空。它若為 0，上面的「值域外 0 列」是查詢
    # 或環境壞了，不是真的沒有違規（CLAUDE.md 否定結論三要件）。
    if total <= 0:
        return False, (f"{static_detail}；DB 正對照失敗：knowledge_base 查到 {total} 列——"
                       "⛔ 這是查詢或連線壞了，不是「值域外 0 列」")

    out_of_domain = {}
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        value, _sep, count = line.rpartition("|")
        out_of_domain[value] = int(count)

    db_detail = f"DB：{total} 列，衍生列（canon_ref）{derived}"
    if not out_of_domain:
        return True, f"{static_detail}；{db_detail}，值域外 0 列"
    if set(out_of_domain) == {_PENDING_D1_VALUE} and derived == 0:
        return None, (f"SKIP(pending-D1)：{static_detail}；{db_detail}，"
                      f"值域外只有 {_PENDING_D1_VALUE} {out_of_domain[_PENDING_D1_VALUE]} 列"
                      "——D1（改寫成 pool-marked-<date> 後 VALIDATE CONSTRAINT）尚未執行，"
                      "此子檢查在 D1 後轉硬失敗")
    listed = "、".join(f"{v}×{n}" for v, n in sorted(out_of_domain.items()))
    return False, (f"{static_detail}；{db_detail}，值域外列：{listed}"
                   f"（衍生列 {derived}）——⛔ 只有「值域外全為 {_PENDING_D1_VALUE} "
                   "且衍生列＝0」才算 pending-D1")


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
    # agent 路徑的假呼叫（給「有呼叫、無原文鍵」與「set_agent_decision 別名」兩案用）。
    agent_clean_src = (
        "def f():\n"
        "    usage_metering.set_agent_decision({'trace_id': t, 'final_kind': k})\n"
    )
    agent_zero_src = "def f():\n    return 1\n"  # agent 路徑存在但 0 個呼叫

    orig_read = _read
    fakes = {
        os.path.join(RAG, "services/_fake_um_clean.py"): clean_src,
        os.path.join(RAG, "services/_fake_um_dirty.py"): dirty_src,
        os.path.join(RAG, "services/_fake_um_nested.py"): dirty_nested,
        os.path.join(RAG, "services/agent/_fake_agent_clean.py"): agent_clean_src,
        os.path.join(RAG, "services/agent/_fake_agent_zero.py"): agent_zero_src,
    }

    def fake_read(path):
        return fakes.get(path, orig_read(path))

    _read = fake_read
    try:
        with tempfile.TemporaryDirectory() as empty_agent_dir:
            cases = [
                ("正對照：現況 usage_metering.py + services/agent/** 通過（真的掃到 agent 呼叫）",
                 check_30_decision_snapshot_no_verbatim()[0] is True),
                ("假檔：無原文鍵（非 agent 路徑，但真實 agent 路徑仍會被自動併入）→ 通過",
                 check_30_decision_snapshot_no_verbatim(paths=["services/_fake_um_clean.py"])[0] is True),
                ("假檔：answer 鍵 → 必須紅",
                 check_30_decision_snapshot_no_verbatim(paths=["services/_fake_um_dirty.py"])[0] is False),
                ("假檔：巢狀字典裡的 quote 鍵 → 必須紅",
                 check_30_decision_snapshot_no_verbatim(paths=["services/_fake_um_nested.py"])[0] is False),
                ("假檔：agent 路徑用 set_agent_decision 別名、無原文鍵 → 通過",
                 check_30_decision_snapshot_no_verbatim(
                     paths=["services/agent/_fake_agent_clean.py"],
                     agent_root=empty_agent_dir,  # 蓋掉真實 agent 目錄，只看這一個假檔
                 )[0] is True),
                ("正對照：agent 路徑存在但 0 個 set_decision/set_agent_decision 呼叫 → 必須紅",
                 check_30_decision_snapshot_no_verbatim(
                     paths=["services/agent/_fake_agent_zero.py"],
                     agent_root=empty_agent_dir,
                 )[0] is False),
            ]
    finally:
        _read = orig_read
    return cases


def _self_test_32():
    """32 的正反對照。⛔ 全部不連 DB（注入假查詢函式）。"""
    clean_db = {
        "SELECT count(*) FROM knowledge_base": "1048\n",
        "!~": "",
        "canon_ref": "0\n",
    }

    def _fake_query(mapping):
        def q(sql):
            if "canon_ref" in sql:
                return mapping["canon_ref"]
            if "!~" in sql:
                return mapping["!~"]
            return mapping["SELECT count(*) FROM knowledge_base"]
        return q

    def _unreachable(_sql):
        raise RuntimeError("Cannot connect to the Docker daemon（自測模擬）")

    real_ok, real_detail = check_32_review_state_single_source(query=_fake_query(clean_db))
    _bad, real_usages, real_scanned, real_errors = scan_32_literals()

    with tempfile.TemporaryDirectory() as td:
        canon_dir = os.path.join(td, "services", "agent", "canon")
        os.makedirs(canon_dir)
        os.makedirs(os.path.join(td, "tools"))
        # 假樹的 review_state（同名常數；⛔ 值不重要，重要的是掃描面界定）
        with open(os.path.join(canon_dir, "review_state.py"), "w", encoding="utf-8") as f:
            f.write('COLUMN = "outline_approved_by"\n'
                    'DOMAIN_REGEX = r"^(reviewed:[^[:space:]]+|pool-marked-[0-9]{8})$"\n')
        # ① 零使用命中
        with open(os.path.join(td, "tools", "no_usage.py"), "w", encoding="utf-8") as f:
            f.write("X = 1\n")
        zero_ok, _d = check_32_review_state_single_source(
            rag_root=td, query=_fake_query(clean_db))
        # ② 使用命中（供 ③④ 當底），③ 越界 SQL 字面
        with open(os.path.join(td, "tools", "consumer.py"), "w", encoding="utf-8") as f:
            f.write("from services.agent.canon.review_state import COLUMN\n"
                    "SQL = f'SELECT {COLUMN} FROM knowledge_base'\n")
        usage_ok, _d = check_32_review_state_single_source(
            rag_root=td, query=_fake_query(clean_db))
        with open(os.path.join(td, "tools", "dirty.py"), "w", encoding="utf-8") as f:
            f.write("from services.agent.canon.review_state import COLUMN\n"
                    "SQL = 'SELECT id FROM knowledge_base "
                    "WHERE outline_approved_by IS NOT NULL'\n")
        literal_ok, literal_detail = check_32_review_state_single_source(
            rag_root=td, query=_fake_query(clean_db))
        os.remove(os.path.join(td, "tools", "dirty.py"))
        # ④ 同一個字面只出現在 docstring ⇒ 不得誤報
        with open(os.path.join(td, "tools", "documented.py"), "w", encoding="utf-8") as f:
            f.write('"""說明：這裡談 outline_approved_by 這個欄位。"""\n'
                    "def f():\n"
                    '    """也談 outline_approved_by。"""\n'
                    "    return 1\n")
        docstring_ok, docstring_detail = check_32_review_state_single_source(
            rag_root=td, query=_fake_query(clean_db))

        # DB 三態（靜態面固定用假樹的乾淨狀態）
        unreachable_ok, _d = check_32_review_state_single_source(
            rag_root=td, query=_unreachable)
        pending_ok, _d = check_32_review_state_single_source(
            rag_root=td,
            query=_fake_query({**clean_db, "!~": "owner-20260905|29\n"}))
        other_value_ok, _d = check_32_review_state_single_source(
            rag_root=td,
            query=_fake_query({**clean_db, "!~": "owner-20260905|29\nreviewed:|1\n"}))
        derived_ok, _d = check_32_review_state_single_source(
            rag_root=td,
            query=_fake_query({**clean_db, "!~": "owner-20260905|29\n", "canon_ref": "7\n"}))
        empty_table_ok, _d = check_32_review_state_single_source(
            rag_root=td,
            query=_fake_query({**clean_db, "SELECT count(*) FROM knowledge_base": "0\n"}))

    cases = [
        ("正對照：現樹靜態面乾淨且 review_state 使用命中 ≥1",
         real_ok in (True, None) and not real_errors and len(real_usages) >= 1),
        (f"正對照：現樹真的掃到東西（{real_scanned} 個檔，⛔ 不是空跑）", real_scanned >= 5),
        ("假樹：0 個使用命中 → 必須紅（空跑不得綠）", zero_ok is False),
        ("假樹：有使用命中、無越界字面 → 通過", usage_ok is True),
        ("假樹：review_state 以外出現 SQL 字面 → 必須紅", literal_ok is False),
        ("假樹：同一字面只在 docstring → ⛔ 不得誤報",
         docstring_ok is True),
        ("DB 不可達 → 必須紅（⛔ 不是 SKIP、不是綠）", unreachable_ok is False),
        ("DB 值域外只有 owner-20260905 且衍生列 0 → SKIP(pending-D1)", pending_ok is None),
        ("DB 值域外出現其他值 → 必須紅", other_value_ok is False),
        ("DB 衍生列 ≥1（D1 已動）→ 必須紅", derived_ok is False),
        ("DB 正對照失敗（knowledge_base 0 列）→ 必須紅", empty_table_ok is False),
    ]
    return cases


def self_test() -> int:
    all_cases = []
    all_cases += _self_test_27()
    all_cases += _self_test_28()
    all_cases += _self_test_29()
    all_cases += _self_test_30()
    all_cases += _self_test_32()
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
    try:
        ok32, detail32 = check_32_review_state_single_source()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 不變量 32：內容已審謂詞單一來源 —— 檢查無法執行（{e}）——大聲失敗")
        return 1
    if ok32 is None:
        print(f"⚠️  不變量 32：內容已審謂詞單一來源（3.1）—— {detail32}")
    else:
        print(f"{'✅' if ok32 else '❌'} 不變量 32：內容已審謂詞單一來源（3.1）—— {detail32}")
        fail = fail or (not ok32)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
