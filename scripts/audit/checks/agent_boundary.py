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
| 28 | 19 | `_EXEMPT_PREFIX` 不含 `/mcp`；門面與對話 API 路由內不得出現 `auth_enforced`；對話 API 路徑都在 `GATED_PREFIXES` 內、不在豁免（DSP-131）|
| 29 | 20 | 可見性謂詞單一來源（`build_visibility_predicate`） |
| 30 | 21 | `decision_snapshot.agent*` 無原文鍵 |
| 31 | 22 | `/mcp` 與對話 API 每呼叫一列 `usage_events`（登記覆蓋測試，見 1.7、DSP-131）|
| 29b | — | canon 可見性單一來源（`canon_assembler.canon_visible`；同 spec 3.2）|
| 32 | —  | 內容已審謂詞單一來源（spec knowledge-outline-and-intent-architecture 3.1）|
| 28b | — | 對話 API 路由（`routers/agent_dialogue.py`）不 import `mcp`／`mcp.*`（DSP-131 F9）|
| 28c | — | `identity.py` 以外不得拿 `entry` 跟入口字面值（`"mcp"`／`"dialogue"`／`"rest"`）比較（DSP-131 F9）|

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

#: 對話 API 路由檔（DSP-131）。28 掃它的 `auth_enforced` 與路由路徑；28b 掃它的 import。
DIALOGUE_ROUTER_REL = "routers/agent_dialogue.py"
FACADE_REL = "services/agent/mcp_facade.py"
UPLOAD_STORE_REL = "services/agent/upload_store.py"
#: 28 掃 `auth_enforced` 的預設檔清單。
FACADE_AUTH_PATHS = (FACADE_REL, "routers/agent.py", DIALOGUE_ROUTER_REL)
#: 對話 API 路徑常數（住在 `mcp_facade.py`）；路由檔只准用這兩個名字註冊路徑。
DIALOGUE_PATH_CONSTS = ("DIALOGUE_TURN_PATH", "DIALOGUE_UPLOAD_TICKET_PATH")
#: 算「註冊路由」的呼叫（`router.<attr>(path, ...)`）。
_ROUTE_REGISTER_ATTRS = frozenset({
    "add_api_route", "api_route", "add_route", "add_api_websocket_route", "websocket",
    "get", "post", "put", "patch", "delete", "options", "head", "trace",
})


def _module_literal_assigns(tree):
    """模組最上層 `NAME = <字面量>`（含帶型別註記）⇒ `{NAME: 值}`；非字面量略過。"""
    out = {}
    for node in getattr(tree, "body", []):
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name):
                try:
                    out[t.id] = ast.literal_eval(value)
                except (ValueError, TypeError, SyntaxError):
                    pass
    return out


def scan_28_dialogue_routes(router_src, facade_src, exempt_prefixes, upload_src):
    """對話 API 路由（DSP-131 F9）：回 `(bad, info)`。

    ① 路由檔必須存在（⛔ 略過——它不在，`/api/v1/agent/turn` 的閘覆蓋就無從驗起）；
    ② `mcp_facade.py` 的 `DIALOGUE_TURN_PATH`／`DIALOGUE_UPLOAD_TICKET_PATH` 都以
       `GATED_PREFIXES` 之一開頭、⛔ 以 `_EXEMPT_PREFIX` 之一開頭、⛔ 等於上傳豁免的
       `UPLOAD_PATH`（`McpServiceGate(exempt_upload=True)` 唯一放行的路徑）；
    ③ 路由檔每個註冊路由的呼叫，路徑引數都是這兩個常數名之一（寫字串字面量 ⇒ 紅：
       ②驗不到它），且兩個常數都有被註冊（正對照：不是掃到 0 個路由）。
    """
    bad, info = [], []
    if router_src is None:
        bad.append(f"{DIALOGUE_ROUTER_REL} 不存在——對話 API 路由的閘覆蓋無從驗起，大聲失敗")
    if facade_src is None:
        bad.append(f"{FACADE_REL} 讀不到——找不到對話 API 路徑常數，大聲失敗")
        return bad, info
    ftree = _parse(facade_src)
    if ftree is None:
        bad.append(f"{FACADE_REL} 語法錯誤——大聲失敗")
        return bad, info
    consts = _module_literal_assigns(ftree)
    gated = consts.get("GATED_PREFIXES")
    if not (isinstance(gated, tuple) and gated and all(isinstance(p, str) and p for p in gated)):
        bad.append(f"{FACADE_REL} 找不到 `GATED_PREFIXES = (...)` 字串 tuple——大聲失敗")
        gated = ()
    upload_path = None
    if upload_src is None:
        bad.append(f"{UPLOAD_STORE_REL} 讀不到——找不到 UPLOAD_PATH，大聲失敗")
    else:
        upload_path = _module_literal_assigns(_parse(upload_src) or ast.Module(body=[])).get("UPLOAD_PATH")
        if not isinstance(upload_path, str):
            bad.append(f"{UPLOAD_STORE_REL} 找不到 `UPLOAD_PATH = \"...\"`——大聲失敗")
    exempt = tuple(str(p) for p in (exempt_prefixes or ()))
    for name in DIALOGUE_PATH_CONSTS:
        path = consts.get(name)
        if not isinstance(path, str) or not path:
            bad.append(f"{FACADE_REL} 找不到 `{name} = \"...\"`——大聲失敗")
            continue
        if gated and not path.startswith(gated):
            bad.append(f"{name}={path!r} 不在 GATED_PREFIXES {gated} 內——McpServiceGate 擋不到")
        if exempt and path.startswith(exempt):
            bad.append(f"{name}={path!r} 落在 _EXEMPT_PREFIX {exempt}——會變成不需金鑰")
        if upload_path is not None and path == upload_path:
            bad.append(f"{name}={path!r} 等於上傳豁免路徑 UPLOAD_PATH——閘會直接放行")
        info.append(f"{name}={path}")

    if router_src is None:
        return bad, info
    rtree = _parse(router_src)
    if rtree is None:
        bad.append(f"{DIALOGUE_ROUTER_REL} 語法錯誤——大聲失敗")
        return bad, info
    # 路由物件＝被 `APIRouter(...)`／`FastAPI(...)` 賦值的名字；只認它們身上的註冊呼叫
    # （`request.headers.get("content-length")` 之類不是路由）。
    router_names = set()
    for node in ast.walk(rtree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            fn = node.value.func
            callee = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if callee in ("APIRouter", "FastAPI"):
                router_names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    if not router_names:
        bad.append(f"{DIALOGUE_ROUTER_REL} 找不到 `<名> = APIRouter(...)`——大聲失敗")
    used, registrations = set(), 0
    for node in ast.walk(rtree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in _ROUTE_REGISTER_ATTRS
                and isinstance(node.func.value, ast.Name) and node.func.value.id in router_names):
            continue
        path_arg = node.args[0] if node.args else next(
            (kw.value for kw in node.keywords if kw.arg == "path"), None)
        registrations += 1
        if path_arg is None:
            bad.append(f"{DIALOGUE_ROUTER_REL} 第 {node.lineno} 行 `.{node.func.attr}(...)` 沒有路徑引數")
            continue
        name = (path_arg.attr if isinstance(path_arg, ast.Attribute)
                else path_arg.id if isinstance(path_arg, ast.Name) else None)
        if name in DIALOGUE_PATH_CONSTS:
            used.add(name)
        else:
            bad.append(f"{DIALOGUE_ROUTER_REL} 第 {node.lineno} 行 `.{node.func.attr}(...)` 的路徑"
                       f"不是 {'／'.join(DIALOGUE_PATH_CONSTS)} 之一——閘覆蓋驗不到它")
    missing = [n for n in DIALOGUE_PATH_CONSTS if n not in used]
    if missing:
        bad.append(f"{DIALOGUE_ROUTER_REL} 沒有用 {'、'.join(missing)} 註冊路由"
                   f"（掃到 {registrations} 個路由註冊）——大聲失敗")
    info.append(f"{DIALOGUE_ROUTER_REL} 註冊 {registrations} 個路由")
    return bad, info


def check_28_mcp_auth_unconditional(auth_src=None, facade_paths=None,
                                    router_src=None, facade_src=None, upload_src=None):
    """design 19：`_EXEMPT_PREFIX` 不含 `/mcp`；`mcp_facade.py`／`routers/agent.py`／
    `routers/agent_dialogue.py` 內不得出現 `auth_enforced` 名稱（否則等於讓 `/mcp`
    又受 `RAG_API_AUTH_ENFORCE` 擺佈）；對話 API 路徑的閘覆蓋見 `scan_28_dialogue_routes`。

    `router_src`／`facade_src`／`upload_src` 供自測植入；未給 ⇒ 讀真檔。"""
    auth_path = "services/api_key_auth.py"
    if auth_src is None:
        auth_src = _read(os.path.join(RAG, auth_path))
    bad = []
    exempt_val = None
    if auth_src is None:
        bad.append(f"{auth_path} 不存在——找不到 _EXEMPT_PREFIX，大聲失敗")
    else:
        tree = _parse(auth_src)
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

    facade_paths = facade_paths or list(FACADE_AUTH_PATHS)
    notes = []
    for rel in facade_paths:
        src = _read(os.path.join(RAG, rel))
        if src is None:
            notes.append(f"{rel} 尚未建立，略過")
            continue
        if "auth_enforced" in src:
            bad.append(f"{rel} 出現 `auth_enforced`——/mcp 認證不得受 RAG_API_AUTH_ENFORCE 左右")

    route_bad, route_info = scan_28_dialogue_routes(
        router_src if router_src is not None else _read(os.path.join(RAG, DIALOGUE_ROUTER_REL)),
        facade_src if facade_src is not None else _read(os.path.join(RAG, FACADE_REL)),
        exempt_val or (),
        upload_src if upload_src is not None else _read(os.path.join(RAG, UPLOAD_STORE_REL)),
    )
    bad += route_bad
    notes += route_info
    return (len(bad) == 0), ("；".join(bad) if bad else "；".join(notes) or "通過")


# ───────────────────────── 28b 對話 API 路由不 import mcp.*（DSP-131 F9）─────────────────────────

def check_28b_dialogue_router_no_mcp_import(src=None, rel=DIALOGUE_ROUTER_REL):
    """對話 API 與 MCP 在協定層分開：路由檔 ⛔ import `mcp`／`mcp.*`（絕對 import；
    含 `importlib.import_module("mcp…")`／`__import__("mcp…")`）。

    路由檔不存在或掃不動 ⇒ 紅；掃到 0 個 import ⇒ 紅（正對照：它至少要 import
    `mcp_facade` 才建得出 `_invoke`，掃到 0 個代表掃錯檔）。"""
    if src is None:
        src = _read(os.path.join(RAG, rel))
    if src is None:
        return False, f"{rel} 不存在——大聲失敗"
    tree = _parse(src)
    if tree is None:
        return False, f"{rel} 語法錯誤，無法 AST 掃描——大聲失敗"

    def _is_mcp(name):
        return isinstance(name, str) and (name == "mcp" or name.startswith("mcp."))

    bad, imports = [], 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += 1
            for a in node.names:
                if _is_mcp(a.name):
                    bad.append(f"第 {node.lineno} 行 import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            imports += 1
            if node.level == 0 and _is_mcp(node.module):
                bad.append(f"第 {node.lineno} 行 from {node.module} import …")
        elif isinstance(node, ast.Call):
            fn = node.func
            fname = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if fname in ("import_module", "__import__") and node.args and isinstance(
                    node.args[0], ast.Constant) and _is_mcp(node.args[0].value):
                bad.append(f"第 {node.lineno} 行 {fname}({node.args[0].value!r})")
    if bad:
        return False, f"{rel}：" + "；".join(bad) + "——對話 API 不得依賴 MCP SDK"
    if imports == 0:
        return False, f"{rel}：掃到 0 個 import——掃錯檔或檔案被清空，大聲失敗"
    return True, f"{rel}：掃到 {imports} 個 import，無 mcp／mcp.*"


# ───────────────────────── 28c identity.py 以外無 entry 字面比較（DSP-131 F9）─────────────────────────
#
# 不變量：入口判斷只准經 `identity.is_backend_entry()`（或 identity.py 內的定義）。
# 在別處寫 `entry == "mcp"` 會讓新入口 `"dialogue"` 靜默落到另一側；寫 `entry != "rest"`
# 會讓任何未知值放行。故掃描面（`services/**`、`routers/**`、`app.py`，⛔ 含 tests）
# 內任何 `entry` 與入口字面值的比較一律紅。
#
# 「`entry`」的認法：名字 `entry`、屬性 `.entry`、`getattr(x, "entry", …)`、
# `x["entry"]`、`x.get("entry", …)`；比較子：`==`、`!=`、`in`、`not in`、`is`、`is not`；
# 另一側：字串常數，或全由字串常數組成的 tuple／list／set，且至少一個是入口值。

ENTRY_LITERALS = frozenset({"mcp", "dialogue", "rest"})
ENTRY_LITERAL_ALLOWED_REL = "services/agent/identity.py"
_ENTRY_CMP_OPS = (ast.Eq, ast.NotEq, ast.In, ast.NotIn, ast.Is, ast.IsNot)


def _is_entry_ref(node):
    if isinstance(node, ast.Name):
        return node.id == "entry"
    if isinstance(node, ast.Attribute):
        return node.attr == "entry"
    if isinstance(node, ast.Subscript):
        sl = node.slice
        return isinstance(sl, ast.Constant) and sl.value == "entry"
    if isinstance(node, ast.Call) and len(node.args) >= 1:
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "getattr" and len(node.args) >= 2:
            return isinstance(node.args[1], ast.Constant) and node.args[1].value == "entry"
        if isinstance(fn, ast.Attribute) and fn.attr == "get":
            return isinstance(node.args[0], ast.Constant) and node.args[0].value == "entry"
    return False


def _entry_literal_values(node):
    """`node` 是入口字面值（或其集合）⇒ 回那些值；否則 `None`。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        vals = {node.value}
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)) and node.elts and all(
            isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts):
        vals = {e.value for e in node.elts}
    else:
        return None
    return vals if vals & ENTRY_LITERALS else None


def entry_literal_hits_in_tree(tree):
    """回 `[(lineno, 片段)]`。"""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left] + list(node.comparators)
        for i, op in enumerate(node.ops):
            if not isinstance(op, _ENTRY_CMP_OPS):
                continue
            a, b = operands[i], operands[i + 1]
            if (_is_entry_ref(a) and _entry_literal_values(b)) or (
                    _is_entry_ref(b) and _entry_literal_values(a)):
                try:
                    snippet = ast.unparse(node)
                except Exception:  # noqa: BLE001
                    snippet = type(op).__name__
                hits.append((node.lineno, snippet))
                break
    return hits


def _entry_scan_rels(rag_root=None):
    root = rag_root or RAG
    rels = []
    for top in ("services", "routers"):
        base = os.path.join(root, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "tests"))
            for fn in sorted(files):
                if fn.endswith(".py") and not fn.startswith("test_"):
                    rels.append(os.path.relpath(os.path.join(dirpath, fn), root))
    if os.path.isfile(os.path.join(root, "app.py")):
        rels.append("app.py")
    return sorted(r for r in rels if r != ENTRY_LITERAL_ALLOWED_REL)


def scan_28c_entry_literals(sources=None, rag_root=None):
    """回 `(hits, scanned_rels, errors)`；`hits`＝`[(rel, lineno, 片段)]`。
    `sources={rel: src}` 供自測植入（仍套用 identity.py／tests 排除規則）。"""
    if sources is not None:
        items = [(rel, src) for rel, src in sorted(sources.items())
                 if rel != ENTRY_LITERAL_ALLOWED_REL
                 and "/tests/" not in f"/{rel}" and not os.path.basename(rel).startswith("test_")]
    else:
        root = rag_root or RAG
        items = [(rel, _read(os.path.join(root, rel))) for rel in _entry_scan_rels(root)]
    hits, scanned, errors = [], [], []
    for rel, src in items:
        if src is None:
            errors.append(f"{rel} 讀不到")
            continue
        tree = _parse(src)
        if tree is None:
            errors.append(f"{rel} 語法錯誤")
            continue
        scanned.append(rel)
        for lineno, snippet in entry_literal_hits_in_tree(tree):
            hits.append((rel, lineno, snippet))
    return hits, scanned, errors


#: 正對照：掃描面必含的檔（掃不到 ⇒ 掃描面搬家了，結論不可信）。
_ENTRY_SCAN_MUST_INCLUDE = (FACADE_REL, "services/agent/runtime.py", "app.py")


def check_28c_no_entry_literal_compare(sources=None, rag_root=None, must_include=None):
    hits, scanned, errors = scan_28c_entry_literals(sources=sources, rag_root=rag_root)
    if errors:
        return False, "；".join(errors) + "——大聲失敗"
    if not scanned:
        return False, "掃到 0 個檔——掃描面路徑錯了，大聲失敗"
    must = _ENTRY_SCAN_MUST_INCLUDE if must_include is None else must_include
    lost = [m for m in must if m not in scanned]
    if lost:
        return False, f"掃描面缺 {'、'.join(lost)}（共掃 {len(scanned)} 檔）——大聲失敗"
    if hits:
        listed = "；".join(f"{rel}:{ln} `{snip}`" for rel, ln, snip in hits)
        return False, (f"{ENTRY_LITERAL_ALLOWED_REL} 以外有 {len(hits)} 處 entry 字面比較"
                       f"（改用 is_backend_entry()）：{listed}")
    return True, f"掃 {len(scanned)} 檔（services/、routers/、app.py，不含 tests 與 identity.py），無 entry 字面比較"


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
        # ⚠️ `services/agent/outline.py:_fetch_prospect_pool_rows` 已於 3.2 退役
        #    （大綱改由 git 正本組裝、不讀 DB）——記憶體側的可見性由**不變量 29b**
        #    盯 `canon_assembler.canon_visible`，⛔ 不要把它加回本清單：29 對每個
        #    target 強制 `_calls_predicate`，記憶體鏡像不可能呼叫 SQL 謂詞。
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
    info = ("INFO：舊鏈曾另有手抄可見性條件未搬、⛔ 本不變量當時不動它們（1.1 留項③，"
            "見 tasks.md 收案註記）——"
            "services/conversational_engine.py:_grounding_by_ids（研究筆記指出無業者過濾）、"
            "services/conversational_engine.py:_grounding_by_category、"
            "services/system_context.py:_fetch_base；三者皆已隨舊鏈於 2026-09-10 舊鏈"
            "隔離 S3 一起刪除，這條 INFO 保留當歷史記錄，⛔ 不再是「未搬」的待辦——"
            "已無可搬的目標。")
    if bad:
        return False, "；".join(bad)
    detail = f"{checked} 個函式已檢查，均引用 {PREDICATE_FUNC} 且無字面違禁欄位" if checked else "0 個函式存在，通過（空集合）"
    if notes:
        detail += "；" + "；".join(notes)
    return True, detail + "。" + info


# ─────────────── 29b（3.2）canon 可見性單一來源（記憶體側） ───────────────

#: 記憶體側可見性的唯一實作位置（spec knowledge-outline-and-intent-architecture 3.2）。
CANON_ASSEMBLER_REL = "services/agent/canon/canon_assembler.py"
CANON_VISIBLE_FUNC = "canon_visible"
#: `canon_visible` 必須引用的角色正規化 helper（design 元件 6 明訂重用、⛔ 不另寫一套）。
TARGET_USER_NORMALIZER = "_effective_target_user"
#: 四個消費端：目錄、`outline:*` 解析、受眾視圖組裝、每回合候選節組裝都必須經過
#: 同一個判準（F7 修補點；DSP-058／9.6 S3 加 `build_outline`——視圖的 `citable`
#: 由它決定，⛔ 不得改成自己看 `fine.reviewed_by`，那就是第二份可見性真相；
#: 9.8 DSP-059 D′ S2 加 `build_canon_sections`——⛔ 不是 `outline.py` 內的
#: `from_canon`，那支只轉呼叫，真正逐 id 判準在 `canon_assembler.py` 本檔）。
CANON_VISIBLE_CALLERS = (
    "build_canon_toc", "resolve_canon_section", "build_outline", "build_canon_sections",
)
#: **刻意不套**的 SQL 條件（正本無 vendor 欄／無上架旗標）——出現在
#: `canon_visible` 內＝有人手抄 SQL 條件進記憶體版，一律 FAIL。
_CANON_BANNED_LITERALS = ("vendor_ids", "is_active")


def _calls_named(node, name):
    """函式本體是否呼叫 `name(...)`／`x.name(...)`。"""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id == name:
                return True
            if isinstance(f, ast.Attribute) and f.attr == name:
                return True
    return False


def _references_name(node, name):
    """函式本體是否出現識別字 `name`（裸名或屬性名，含呼叫）。"""
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name:
            return True
        if isinstance(n, ast.Attribute) and n.attr == name:
            return True
    return False


def check_29b_canon_visibility_single_source(rel=None):
    """3.2：記憶體側可見性只有一份，且沒有手抄 SQL 條件。

    四條規則（缺一即 FAIL，⛔ 不 SKIP——這條的目標是**必須存在**的產線函式）：
    ① `canon_assembler.py:canon_visible` 存在；
    ② 它引用 `_effective_target_user`（角色正規化與 SQL 側同一支）；
    ③ `build_canon_toc`／`resolve_canon_section`／`build_outline` 都直接呼叫
       `canon_visible`（目錄、`outline:*` 解析、受眾視圖都要過同一道閘門）；
       ⚠️ `build_outline` 另外呼叫 `_axes_visible`（受眾＋業態兩軸，不看已審）——
       那是**納入**判準，`canon_visible` 是**可引用**判準，⛔ 兩者不得互相取代。
    ④ `canon_visible` 內不得出現 `vendor_ids`／`is_active` 字面（含字串常數與識別字）
       ——那是刻意不套的 SQL 條件，出現＝手抄。

    ⚠️ 與 29 的分工：29 盯 **SQL 側**（必須呼叫 `build_visibility_predicate`），
    29b 盯 **記憶體側**；「兩者等價」的契約測試屬 3.3（design 元件 11），⛔ 不在此。
    """
    rel = rel or CANON_ASSEMBLER_REL
    src = _read(os.path.join(RAG, rel))
    if src is None:
        return False, (f"{rel} 讀不到——記憶體側可見性的單一來源不存在（大聲失敗："
                       "⛔ 不當成「還沒建立、略過」）")
    tree = _parse(src)
    if tree is None:
        return False, f"{rel} 語法錯誤，無法 AST 掃描——大聲失敗"

    fn = _func_node(tree, CANON_VISIBLE_FUNC)
    if fn is None:
        return False, f"{rel}:{CANON_VISIBLE_FUNC} 不存在——可見性單一來源不見了"

    bad = []
    if not _references_name(fn, TARGET_USER_NORMALIZER):
        bad.append(f"{rel}:{CANON_VISIBLE_FUNC} 未引用 {TARGET_USER_NORMALIZER}()"
                   "——角色正規化必須與 SQL 側同一支，⛔ 不得另寫")
    for caller in CANON_VISIBLE_CALLERS:
        node = _func_node(tree, caller)
        if node is None:
            bad.append(f"{rel}:{caller} 不存在——可見性的消費端少一個")
        elif not _calls_named(node, CANON_VISIBLE_FUNC):
            bad.append(f"{rel}:{caller} 未呼叫 {CANON_VISIBLE_FUNC}()"
                       "——這條路徑沒有套可見性")
    for banned in _CANON_BANNED_LITERALS:
        hit = any(banned in v for v in _string_constants(fn)) or _references_name(fn, banned)
        if hit:
            bad.append(f"{rel}:{CANON_VISIBLE_FUNC} 出現 `{banned}` 字面"
                       "——那是刻意不套的 SQL 條件，出現＝手抄")
    if bad:
        return False, "；".join(bad)
    return True, (f"{rel}:{CANON_VISIBLE_FUNC} 存在、引用 {TARGET_USER_NORMALIZER}、"
                  f"被 {'／'.join(CANON_VISIBLE_CALLERS)} 呼叫，且無 "
                  f"{'／'.join(_CANON_BANNED_LITERALS)} 字面")


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

#: 對話 API「每呼叫恰一列」的覆蓋測試（DSP-131 計畫 §5.2 第 5 項）。
DIALOGUE_USAGE_TEST_REL = "tests/unit/agent/test_agent_dialogue_router_req.py"
DIALOGUE_USAGE_TEST_FUNC = "test_each_dialogue_call_writes_exactly_one_row"


def check_31_mcp_usage_events_coverage(path="tests/integration/agent/test_mcp_facade_req.py",
                                       dialogue_path=DIALOGUE_USAGE_TEST_REL,
                                       dialogue_func=DIALOGUE_USAGE_TEST_FUNC):
    """design 22：屬整合測試（任務 1.7 落地）。本 checker 只登記覆蓋
    測試檔是否存在——`/mcp` 那份不存在 ⇒ WARN（非 FAIL），避免在 1.7 完成前把
    make audit 卡死在一條尚不該紅的規則上。

    DSP-131：`/mcp` 那份在 ⇒ 對話 API 那份也必須在，且含 `dialogue_func` 這支測試
    （⛔ WARN：對話 API 已上線的路徑沒有理由「待落地」）。路徑以 `RAG` 解析（host 與
    測試容器 `/app` 兩種佈局都對；原本以 `REPO` 拼，在容器內恆為 WARN）。"""
    full = os.path.join(RAG, path)
    if not os.path.exists(full):
        return None, f"{path} 不存在——WARN：/mcp 每呼叫一列 usage_events 待任務 1.7 落地，尚無測試覆蓋"
    src = _read(os.path.join(RAG, dialogue_path))
    if src is None:
        return False, f"{dialogue_path} 不存在——對話 API 每呼叫一列 usage_events 沒有測試覆蓋，大聲失敗"
    tree = _parse(src)
    if tree is None:
        return False, f"{dialogue_path} 語法錯誤——大聲失敗"
    funcs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if dialogue_func not in funcs:
        return False, (f"{dialogue_path} 沒有 `{dialogue_func}`（掃到 {len(funcs)} 個函式）"
                       "——對話 API 每呼叫一列的覆蓋被拿掉了，大聲失敗")
    return True, f"/mcp 由 {path} 覆蓋；對話 API 由 {dialogue_path}::{dialogue_func} 覆蓋"


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
    ("29b", "canon 可見性單一來源（3.2）", check_29b_canon_visibility_single_source),
    ("28b", "對話 API 路由不 import mcp.*（DSP-131）", check_28b_dialogue_router_no_mcp_import),
    ("28c", "identity.py 以外無 entry 字面比較（DSP-131）", check_28c_no_entry_literal_compare),
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
    cases += _self_test_28_dialogue_routes(good_auth)
    return cases


_FAKE_FACADE_28 = (
    'GATED_PREFIXES = ("/mcp", "/api/v1/agent")\n'
    'DIALOGUE_TURN_PATH = "/api/v1/agent/turn"\n'
    'DIALOGUE_UPLOAD_TICKET_PATH = "/api/v1/agent/upload-ticket"\n'
)
_FAKE_UPLOAD_28 = 'UPLOAD_PATH = "/api/v1/agent/uploads"\n'
_FAKE_ROUTER_28 = (
    "from fastapi import APIRouter\n"
    "from services.agent import mcp_facade\n"
    "def build_router(registry, deps):\n"
    "    router = APIRouter()\n"
    "    async def h(request):\n"
    "        return request.headers.get('content-length')\n"
    "    router.add_api_route(mcp_facade.DIALOGUE_TURN_PATH, h, methods=['POST'])\n"
    "    router.add_api_route(mcp_facade.DIALOGUE_UPLOAD_TICKET_PATH, h, methods=['POST'])\n"
    "    return router\n"
)


def _self_test_28_dialogue_routes(good_auth):
    def run(router=_FAKE_ROUTER_28, facade=_FAKE_FACADE_28, upload=_FAKE_UPLOAD_28, auth=good_auth):
        return check_28_mcp_auth_unconditional(auth_src=auth, facade_paths=[], router_src=router,
                                               facade_src=facade, upload_src=upload)[0]

    real_router = _read(os.path.join(RAG, DIALOGUE_ROUTER_REL))
    return [
        ("28 正對照：現況對話 API 路由檔存在、路徑在閘內（含真檔掃描）",
         real_router is not None and check_28_mcp_auth_unconditional()[0] is True),
        ("28 假樹：乾淨路由（用常數註冊、headers.get 不算路由）→ 通過", run() is True),
        ("28 對話 API 路由檔不存在 → 必須紅（⛔ 略過）",
         scan_28_dialogue_routes(None, _FAKE_FACADE_28, ("/docs",), _FAKE_UPLOAD_28)[0] != []),
        ("28 路由用字串字面量註冊 → 必須紅",
         run(router=_FAKE_ROUTER_28.replace("mcp_facade.DIALOGUE_TURN_PATH", "'/api/v1/agent/turn'"))
         is False),
        ("28 路由少註冊一條常數 → 必須紅",
         run(router="\n".join(l for l in _FAKE_ROUTER_28.splitlines()
                              if "UPLOAD_TICKET_PATH" not in l) + "\n") is False),
        ("28 路由多一條 @router.post('/x') → 必須紅",
         run(router=_FAKE_ROUTER_28.replace(
             "    return router\n", "    router.post('/api/v1/agent/x')(h)\n    return router\n"))
         is False),
        ("28 找不到 APIRouter 賦值 → 必須紅",
         run(router=_FAKE_ROUTER_28.replace("router = APIRouter()", "router = make()")) is False),
        ("28 路徑不在 GATED_PREFIXES → 必須紅",
         run(facade=_FAKE_FACADE_28.replace('"/api/v1/agent/turn"', '"/v1/agent/turn"')) is False),
        ("28 路徑落在 _EXEMPT_PREFIX → 必須紅",
         run(auth='_EXEMPT_PREFIX = ("/docs", "/api/v1/agent/turn")\n') is False),
        ("28 路徑等於上傳豁免 UPLOAD_PATH → 必須紅",
         run(upload='UPLOAD_PATH = "/api/v1/agent/upload-ticket"\n') is False),
        ("28 門面缺路徑常數 → 必須紅",
         run(facade='GATED_PREFIXES = ("/mcp", "/api/v1/agent")\n') is False),
        ("28 門面缺 GATED_PREFIXES → 必須紅",
         run(facade=_FAKE_FACADE_28.splitlines()[1] + "\n" + _FAKE_FACADE_28.splitlines()[2] + "\n")
         is False),
        ("28 auth_enforced 預設掃描清單含對話 API 路由檔",
         DIALOGUE_ROUTER_REL in FACADE_AUTH_PATHS),
        ("28 對話 API 路由檔出現 auth_enforced → 必須紅",
         _router_with_auth_enforced_is_caught(good_auth)),
    ]


def _router_with_auth_enforced_is_caught(good_auth):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "agent_dialogue.py")
        with open(p, "w") as f:
            f.write("from services.api_key_auth import auth_enforced\n" + _FAKE_ROUTER_28)
        return check_28_mcp_auth_unconditional(
            auth_src=good_auth, facade_paths=[p], router_src=_FAKE_ROUTER_28,
            facade_src=_FAKE_FACADE_28, upload_src=_FAKE_UPLOAD_28)[0] is False


def _self_test_28b():
    good = _FAKE_ROUTER_28
    real = check_28b_dialogue_router_no_mcp_import()
    return [
        ("28b 正對照：現況路由檔掃到 ≥1 個 import 且無 mcp.*", real[0] is True and "import" in real[1]),
        ("28b 假檔乾淨 → 通過", check_28b_dialogue_router_no_mcp_import(src=good)[0] is True),
        ("28b import mcp → 必須紅",
         check_28b_dialogue_router_no_mcp_import(src="import mcp\n" + good)[0] is False),
        ("28b from mcp.server.fastmcp import X → 必須紅",
         check_28b_dialogue_router_no_mcp_import(
             src="from mcp.server.fastmcp import Context\n" + good)[0] is False),
        ("28b import mcp.types as t → 必須紅",
         check_28b_dialogue_router_no_mcp_import(src="import mcp.types as t\n" + good)[0] is False),
        ("28b 函式內 import mcp → 必須紅",
         check_28b_dialogue_router_no_mcp_import(
             src=good + "def f():\n    from mcp import types\n")[0] is False),
        ("28b importlib.import_module('mcp.x') → 必須紅",
         check_28b_dialogue_router_no_mcp_import(
             src=good + "import importlib\nM = importlib.import_module('mcp.server')\n")[0] is False),
        ("28b `import mcpx`／相對 `from .mcp import y` 不是 SDK → 通過",
         check_28b_dialogue_router_no_mcp_import(
             src="import mcpx\nfrom .mcp import y\n" + good)[0] is True),
        ("28b 0 個 import → 必須紅", check_28b_dialogue_router_no_mcp_import(src="X = 1\n")[0] is False),
        ("28b 檔案不存在 → 必須紅",
         check_28b_dialogue_router_no_mcp_import(rel="routers/_does_not_exist.py")[0] is False),
    ]


def _self_test_28c():
    must = ("services/x.py",)

    def hit(src, rel="services/x.py"):
        return check_28c_no_entry_literal_compare(sources={rel: src}, must_include=(rel,))[0] is False

    bad_forms = [
        ('if entry == "mcp":\n    pass\n', '`entry == "mcp"`'),
        ('ok = identity.entry != "mcp"\n', '`.entry != "mcp"`'),
        ('ok = getattr(identity, "entry", None) != "rest"\n', '`getattr(..., "entry") != "rest"`（對未知值放行）'),
        ('ok = "mcp" == identity.entry\n', "字面值在左"),
        ('ok = identity.entry in ("mcp", "dialogue")\n', "`in` tuple"),
        ('ok = entry not in {"rest"}\n', "`not in` set"),
        ('ok = state["entry"] == "dialogue"\n', '`x["entry"]`'),
        ('ok = payload.get("entry") == "mcp"\n', '`x.get("entry")`'),
        ('ok = entry is "mcp"\n', "`is`"),
        ('ok = 0 < n and a < entry == "mcp"\n', "鏈式比較"),
    ]
    good_forms = [
        ("ok = is_backend_entry(entry)\n", "is_backend_entry"),
        ('f(entry="mcp")\n', "關鍵字引數不是比較"),
        ('ok = channel == "mcp"\n', "非 entry 名字"),
        ("ok = entry == DEFAULT_ENTRY_CHANNEL\n", "跟常數名比（非字面）"),
        ('"""entry == "mcp" 只在 docstring"""\n', "docstring"),
        ('ok = entry == "other"\n', "非入口字面值"),
        ('M = {"mcp": 1}\nv = M[entry]\n', "查表"),
    ]
    hits_real, scanned_real, errors_real = scan_28c_entry_literals()
    cases = [
        ("28c 正對照：真樹掃描面 ≥20 檔、含 mcp_facade.py／runtime.py／app.py、讀檔無錯"
         "（⛔ 不斷言真樹無命中——runtime.py 的處置屬併回，見 DSP-131）",
         len(scanned_real) >= 20 and not errors_real
         and all(m in scanned_real for m in _ENTRY_SCAN_MUST_INCLUDE)),
        ("28c 正對照：真樹掃描面排除 identity.py 與 tests",
         ENTRY_LITERAL_ALLOWED_REL not in scanned_real
         and not any("/tests/" in f"/{r}" for r in scanned_real)),
    ]
    cases += [(f"28c 植入 {label} → 必須紅", hit(src)) for src, label in bad_forms]
    cases += [(f"28c {label} → 不得誤報", not hit(src)) for src, label in good_forms]
    cases += [
        ("28c identity.py 內的字面比較 → 豁免",
         check_28c_no_entry_literal_compare(
             sources={ENTRY_LITERAL_ALLOWED_REL: 'ok = entry == "mcp"\n', "services/x.py": "X = 1\n"},
             must_include=must)[0] is True),
        ("28c tests 內的字面比較 → 不掃",
         check_28c_no_entry_literal_compare(
             sources={"services/agent/tests/test_x.py": 'ok = entry == "mcp"\n',
                      "services/x.py": "X = 1\n"}, must_include=must)[0] is True),
        ("28c 掃描面缺必含檔 → 必須紅",
         check_28c_no_entry_literal_compare(sources={"services/x.py": "X = 1\n"},
                                            must_include=("app.py",))[0] is False),
        ("28c 0 個檔 → 必須紅", check_28c_no_entry_literal_compare(sources={}, must_include=())[0] is False),
        ("28c 語法錯誤 → 必須紅",
         check_28c_no_entry_literal_compare(sources={"services/x.py": "def (:\n"},
                                            must_include=must)[0] is False),
        ("28c 命中列出 file:line",
         "services/x.py:2" in check_28c_no_entry_literal_compare(
             sources={"services/x.py": 'X = 1\nok = entry != "rest"\n'}, must_include=must)[1]),
    ]
    return cases


def _self_test_31():
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "test_mcp_facade_req.py")
        with open(base, "w") as f:
            f.write("def test_x():\n    pass\n")
        dlg = os.path.join(td, "test_dialogue.py")
        with open(dlg, "w") as f:
            f.write(f"async def {DIALOGUE_USAGE_TEST_FUNC}():\n    pass\n")
        dlg_wo = os.path.join(td, "test_dialogue_wo.py")
        with open(dlg_wo, "w") as f:
            f.write("async def test_other():\n    pass\n")
        nope = os.path.join(td, "nope.py")
        real = check_31_mcp_usage_events_coverage()
        return [
            ("31 正對照：現況兩份覆蓋測試都在（RAG 解析，容器內也算得到）", real[0] is True),
            ("31 /mcp 覆蓋檔不存在 → WARN（None）",
             check_31_mcp_usage_events_coverage(path=nope, dialogue_path=dlg)[0] is None),
            ("31 對話 API 覆蓋檔不存在 → 必須紅",
             check_31_mcp_usage_events_coverage(path=base, dialogue_path=nope)[0] is False),
            ("31 對話 API 覆蓋檔缺該測試函式 → 必須紅",
             check_31_mcp_usage_events_coverage(path=base, dialogue_path=dlg_wo)[0] is False),
            ("31 兩份都在且含該函式 → 通過",
             check_31_mcp_usage_events_coverage(path=base, dialogue_path=dlg)[0] is True),
        ]


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


def _self_test_29b():
    global _read
    real_ok = check_29b_canon_visibility_single_source()[0]

    clean_src = (
        "def canon_visible(identity, fine, *, vendor_business_types):\n"
        "    tu = VendorKnowledgeRetrieverV2._effective_target_user(identity.target_user)\n"
        "    return tu in fine.target_user\n"
        "def build_canon_toc(doc, identity, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if canon_visible(identity, f, vendor_business_types=vendor_business_types)]\n"
        "def resolve_canon_section(doc, identity, sid, *, vendor_business_types):\n"
        "    return canon_visible(identity, sid, vendor_business_types=vendor_business_types)\n"
        "def build_outline(doc, audience, identity, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if canon_visible(identity, f, vendor_business_types=vendor_business_types)]\n"
        "def build_canon_sections(doc, identity, ids, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if f.id in ids and canon_visible(identity, f, vendor_business_types=vendor_business_types)]\n"
    )
    missing_func = clean_src.replace("def canon_visible", "def _renamed_visible")
    one_caller = clean_src.replace(
        "    return canon_visible(identity, sid, vendor_business_types=vendor_business_types)\n",
        "    return True\n")
    # DSP-058：第三個消費端（視圖組裝）漏掉閘門 ⇒ 必須紅（⛔ 不是「少一個無所謂」）。
    no_view_caller = clean_src.replace(
        "def build_outline(doc, audience, identity, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if canon_visible(identity, f, vendor_business_types=vendor_business_types)]\n",
        "def build_outline(doc, audience, identity, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if f.reviewed_by is not None]\n")
    # 9.8 DSP-059 D′ S2 F1：第四個消費端（每回合候選節組裝）漏掉閘門 ⇒ 必須紅。
    no_sections_caller = clean_src.replace(
        "def build_canon_sections(doc, identity, ids, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if f.id in ids and canon_visible(identity, f, vendor_business_types=vendor_business_types)]\n",
        "def build_canon_sections(doc, identity, ids, *, vendor_business_types):\n"
        "    return [f for f in doc.fines() if f.id in ids]\n")
    banned_literal = clean_src.replace(
        "    return tu in fine.target_user\n",
        "    if 'vendor_ids' in fine.raw:\n        return False\n    return tu in fine.target_user\n")
    no_normalizer = clean_src.replace(
        "    tu = VendorKnowledgeRetrieverV2._effective_target_user(identity.target_user)\n",
        "    tu = identity.target_user or 'tenant'\n")

    orig_read = _read
    fakes = {
        os.path.join(RAG, "services/_fake_canon_clean.py"): clean_src,
        os.path.join(RAG, "services/_fake_canon_missing.py"): missing_func,
        os.path.join(RAG, "services/_fake_canon_one_caller.py"): one_caller,
        os.path.join(RAG, "services/_fake_canon_banned.py"): banned_literal,
        os.path.join(RAG, "services/_fake_canon_no_norm.py"): no_normalizer,
        os.path.join(RAG, "services/_fake_canon_no_view_caller.py"): no_view_caller,
        os.path.join(RAG, "services/_fake_canon_no_sections_caller.py"): no_sections_caller,
    }

    def fake_read(path):
        return fakes.get(path, orig_read(path))

    _read = fake_read
    try:
        cases = [
            ("29b 正對照：現樹的 canon_visible 通過", real_ok is True),
            ("29b 假樹：規則齊備 → 通過（⛔ 不是恆紅）",
             check_29b_canon_visibility_single_source("services/_fake_canon_clean.py")[0] is True),
            ("29b 假樹：canon_visible 不存在 → 必須紅",
             check_29b_canon_visibility_single_source("services/_fake_canon_missing.py")[0] is False),
            ("29b 假樹：只有一個消費端呼叫 → 必須紅",
             check_29b_canon_visibility_single_source("services/_fake_canon_one_caller.py")[0] is False),
            ("29b 假樹：出現 vendor_ids 字面 → 必須紅",
             check_29b_canon_visibility_single_source("services/_fake_canon_banned.py")[0] is False),
            ("29b 假樹：未引用 _effective_target_user → 必須紅",
             check_29b_canon_visibility_single_source("services/_fake_canon_no_norm.py")[0] is False),
            ("29b 假樹：build_outline 改看 reviewed_by 不問 canon_visible → 必須紅",
             check_29b_canon_visibility_single_source("services/_fake_canon_no_view_caller.py")[0] is False),
            ("29b 假樹：build_canon_sections 未呼叫 canon_visible → 必須紅",
             check_29b_canon_visibility_single_source("services/_fake_canon_no_sections_caller.py")[0] is False),
            ("29b 檔案讀不到 → 必須紅（⛔ 不是略過通過）",
             check_29b_canon_visibility_single_source("services/_fake_canon_absent.py")[0] is False),
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
    all_cases += _self_test_28b()
    all_cases += _self_test_28c()
    all_cases += _self_test_31()
    all_cases += _self_test_29()
    all_cases += _self_test_29b()
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
        print(f"⚠️  不變量 31：/mcp 與對話 API 每呼叫一列 usage_events（design 22）—— {detail31}")
    else:
        print(f"{'✅' if ok31 else '❌'} 不變量 31：/mcp 與對話 API 每呼叫一列 usage_events（design 22）—— {detail31}")
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
