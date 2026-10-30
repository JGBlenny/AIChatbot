#!/usr/bin/env python3
"""AIChatbot 能對真 JGB 送出的「方法＋路徑」，逐條對照 jgb2 `origin/staging` 的 `external/v1` 路由。

為什麼有這支：2026-10-29 盤查發現 #16～#18 三條自訂讀取路由、`PATCH /agent/v1/bills/{id}` 這類
「JGB 根本沒有的路徑」被當成已接上，使用者按了確認才失敗。這支把「我們會送什麼」和「JGB 有什麼」
放在一起比，沒有的路徑必須列在 `GUARDED` 並且守衛真的存在，否則非 0 退出。

做什麼：
1. `git -C <jgb2 checkout> show origin/staging:routes/api.php`（唯讀；⛔ checkout／修改 jgb2），
   取出 `Route::prefix('external/v1')` 群組內每條 `Route::<method>('<path>')`。
2. 以 AST 掃 `services/**/*.py`：`_request`（GET）、`_post_request`（POST）、`_patch_request`（PATCH）、
   `_send("METHOD", path)`、`_assistant_write(req, path, ...)`（POST）的路徑參數，f-string 的
   `{x}` 一律正規化成 `{}`。路徑不是字串常數／f-string（算不出來）又不在包裝函式內 ⇒ 非 0（不猜）。
3. 每一組不在 JGB 的 方法＋路徑，必須在 `GUARDED` 內，且同時成立：
   a. 送出它的函式裡，在送出之前有 `if not self.use_mock: return ...`（接真 JGB 不發請求）；
   b. 出卡端的 `WRITE_NOT_SUPPORTED_ACTIONS`（`services/agent/tools/confirm.py`）含對應動作
      （使用者在按確認之前就被擋下）。
4. 正對照：`GET /api/external/v1/bills` 必須同時出現在 JGB 路由與我們的送出清單，否則是工具壞了（非 0）。

退出碼：0 通過；1 有不在 JGB 又沒守衛的路徑；2 工具／環境壞了（找不到 checkout、路由解析為空、
正對照沒中、AST 算不出路徑）。

用法（在 `rag-orchestrator/` 下）：
    python3 scripts/check_jgb_contract.py [--jgb2 ~/dev/work/jgb2/dev3] [--ref origin/staging]
    python3 scripts/check_jgb_contract.py --extra-send "GET /api/external/v1/bills/summary/unpaid"   # 自我測試：注入一條假路徑
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent          # rag-orchestrator/
SERVICES = ROOT / "services"
CONFIRM_PY = SERVICES / "agent" / "tools" / "confirm.py"
DEFAULT_JGB2 = Path("~/dev/work/jgb2/dev3").expanduser()
DEFAULT_REF = "origin/staging"
ROUTES_FILE = "routes/api.php"
GROUP_OPEN = "Route::prefix('external/v1')"
EXTERNAL_PREFIX = "/api/external/v1"

#: 正對照：兩邊都必須有。
POSITIVE_CONTROL = ("GET", "/api/external/v1/bills")

#: 呼叫哪個方法 ⇒ HTTP 方法（`_send` 由第一個參數決定、`_assistant_write` 固定 POST）。
SENDERS = {"_request": "GET", "_post_request": "POST", "_patch_request": "PATCH"}
#: 這幾個函式是「把參數往下傳」的包裝，裡面的路徑是變數，由呼叫端的常數負責（掃呼叫端）。
WRAPPERS = {"_request", "_post_request", "_patch_request", "_send", "_assistant_write"}

#: 允許「不在 JGB」的 方法＋路徑 ⇒ (守衛所在函式, WRITE_NOT_SUPPORTED_ACTIONS 內的對應名稱)。
#: 新增項目前先確認 JGB 真的沒有（或還沒做），並且兩道守衛都在。
GUARDED: dict[tuple[str, str], tuple[str, str]] = {
    ("PATCH", "/agent/v1/bills/{}"): ("agent_patch_bill_due_date", "BILL_DUE_EXTEND_ACTION"),
    ("POST", "/api/external/v1/estates"): ("_assistant_write", "estate_create"),
    ("POST", "/api/external/v1/contracts"): ("_assistant_write", "contract_create"),
    ("POST", "/api/external/v1/bills/manual"): ("_assistant_write", "manual_bill_create"),
}


class ToolBroken(Exception):
    """工具或環境壞了（退出碼 2）。"""


def canon(path: str) -> str:
    """`{anything}` ⇒ `{}`；去掉結尾斜線。"""
    return re.sub(r"\{[^}]*\}", "{}", path).rstrip("/") or "/"


# ── JGB 路由 ────────────────────────────────────────────────────────────────
def load_jgb_routes(checkout: Path, ref: str) -> set[tuple[str, str]]:
    if not checkout.is_dir():
        raise ToolBroken(f"找不到 jgb2 checkout：{checkout}（用 --jgb2 指定）")
    proc = subprocess.run(
        ["git", "-C", str(checkout), "show", f"{ref}:{ROUTES_FILE}"],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise ToolBroken(f"git show {ref}:{ROUTES_FILE} 失敗（{proc.stderr.strip()[:200]}）")
    lines = proc.stdout.splitlines()
    # 2026-10-30：JGB 把寫入路由（#19～#23）另開一個 `external/v1` 群組（中介層不同），只讀第一個群組會誤報「沒有」⇒ 每個群組都讀。
    starts = [i for i, ln in enumerate(lines) if GROUP_OPEN in ln]
    if not starts:
        raise ToolBroken(f"{ROUTES_FILE} 找不到 {GROUP_OPEN}（路由檔結構變了，工具要跟著改）")
    routes: set[tuple[str, str]] = set()
    for start in starts:
        for ln in lines[start + 1:]:
            if ln.rstrip() == "});":                     # 群組結尾（縮排 0）
                break
            m = re.search(r"Route::(get|post|put|patch|delete)\(\s*'([^']+)'", ln)
            if m:
                routes.add((m.group(1).upper(), canon(EXTERNAL_PREFIX + m.group(2))))
    if not routes:
        raise ToolBroken("external/v1 群組內解析不到任何路由")
    return routes


# ── AIChatbot 送出的路徑 ────────────────────────────────────────────────────
def _path_of(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return canon(node.value)
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                parts.append("{}")
        return canon("".join(parts))
    return None


class _Collector(ast.NodeVisitor):
    def __init__(self, rel: str):
        self.rel = rel
        self.func_stack: list[str] = []
        self.sends: list[dict] = []
        self.unresolved: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Call(self, node: ast.Call) -> None:
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else None
        method = path_node = None
        guard_fn = self.func_stack[-1] if self.func_stack else "<module>"
        if name in SENDERS and node.args:
            method, path_node = SENDERS[name], node.args[0]
        elif name == "_send" and len(node.args) >= 2:
            m = node.args[0]
            if isinstance(m, ast.Constant) and isinstance(m.value, str):
                method, path_node = m.value.upper(), node.args[1]
        elif name == "_assistant_write" and len(node.args) >= 2:
            method, path_node, guard_fn = "POST", node.args[1], "_assistant_write"
        if path_node is not None:
            path = _path_of(path_node)
            where = f"{self.rel}:{node.lineno} 在 {guard_fn}()"
            enclosing = self.func_stack[-1] if self.func_stack else ""
            if path is not None:
                self.sends.append({"method": method, "path": path, "guard_fn": guard_fn,
                                   "rel": self.rel, "lineno": node.lineno})
            elif enclosing not in WRAPPERS:
                self.unresolved.append(where)
        self.generic_visit(node)


def collect_sends() -> tuple[list[dict], list[str], dict[str, ast.AST]]:
    sends: list[dict] = []
    unresolved: list[str] = []
    trees: dict[str, ast.AST] = {}
    files = sorted(p for p in SERVICES.rglob("*.py") if "__pycache__" not in p.parts)
    if not files:
        raise ToolBroken(f"{SERVICES} 底下沒有 .py（路徑錯了？）")
    for path in files:
        rel = str(path.relative_to(ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        trees[rel] = tree
        col = _Collector(rel)
        col.visit(tree)
        sends += col.sends
        unresolved += col.unresolved
    return sends, unresolved, trees


# ── 守衛檢查 ────────────────────────────────────────────────────────────────
def _is_not_use_mock(test: ast.AST) -> bool:
    return (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Attribute) and test.operand.attr == "use_mock"
            and isinstance(test.operand.value, ast.Name) and test.operand.value.id == "self")


def has_real_jgb_guard(trees: dict[str, ast.AST], func_name: str, before_line: int) -> bool:
    """`func_name` 內、`before_line` 之前有 `if not self.use_mock:`，且該分支直接 return（不發請求）。"""
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                for inner in ast.walk(node):
                    if (isinstance(inner, ast.If) and _is_not_use_mock(inner.test)
                            and inner.lineno < before_line
                            and any(isinstance(b, ast.Return) for b in inner.body)):
                        return True
    return False


def not_supported_actions(trees: dict[str, ast.AST]) -> set[str]:
    """`WRITE_NOT_SUPPORTED_ACTIONS = frozenset({...})` 的元素（字串常數取值、名稱取名稱）。"""
    tree = trees.get(str(CONFIRM_PY.relative_to(ROOT)))
    if tree is None:
        raise ToolBroken(f"找不到 {CONFIRM_PY}")
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WRITE_NOT_SUPPORTED_ACTIONS"
                                                  for t in node.targets)):
            call = node.value
            if isinstance(call, ast.Call) and call.args and isinstance(call.args[0], ast.Set):
                out = set()
                for el in call.args[0].elts:
                    if isinstance(el, ast.Constant):
                        out.add(str(el.value))
                    elif isinstance(el, ast.Name):
                        out.add(el.id)
                return out
    raise ToolBroken("confirm.py 找不到 WRITE_NOT_SUPPORTED_ACTIONS = frozenset({...})")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jgb2", default=os.environ.get("JGB2_CHECKOUT", str(DEFAULT_JGB2)),
                    help="jgb2 checkout 路徑（只用 git show 讀，⛔ 修改）")
    ap.add_argument("--ref", default=DEFAULT_REF)
    ap.add_argument("--extra-send", action="append", default=[], metavar='"METHOD /path"',
                    help="自我測試：把這條假路徑當成 AIChatbot 會送出的，確認腳本會抓到")
    args = ap.parse_args(argv)

    try:
        jgb = load_jgb_routes(Path(args.jgb2).expanduser(), args.ref)
        sends, unresolved, trees = collect_sends()
        extra_actions = not_supported_actions(trees)
    except ToolBroken as exc:
        print(f"工具壞了：{exc}", file=sys.stderr)
        return 2

    for spec in args.extra_send:
        method, _, path = spec.partition(" ")
        sends.append({"method": method.upper(), "path": canon(path.strip()), "guard_fn": "<--extra-send>",
                      "rel": "<--extra-send>", "lineno": 0})

    ours = {(s["method"], s["path"]) for s in sends}
    print(f"JGB external/v1 路由（{args.ref}）：{len(jgb)} 條")
    print(f"AIChatbot 可送出的 方法＋路徑：{len(ours)} 組（掃描 {len(trees)} 個檔）")

    if POSITIVE_CONTROL not in jgb or POSITIVE_CONTROL not in ours:
        print(f"工具壞了：正對照 {POSITIVE_CONTROL[0]} {POSITIVE_CONTROL[1]} 沒命中"
              f"（JGB 有={POSITIVE_CONTROL in jgb}，我們送={POSITIVE_CONTROL in ours}）", file=sys.stderr)
        return 2
    print(f"正對照 {POSITIVE_CONTROL[0]} {POSITIVE_CONTROL[1]}：兩邊都有")

    if unresolved:
        print("工具壞了：以下呼叫的路徑算不出來（不是字串常數／f-string），無法比對：", file=sys.stderr)
        for u in unresolved:
            print(f"  {u}", file=sys.stderr)
        return 2

    in_jgb = sorted(ours & jgb)
    missing = sorted(ours - jgb)
    print(f"在 JGB：{len(in_jgb)} 組")
    bad: list[str] = []
    guarded_ok: list[str] = []
    for method, path in missing:
        label = f"{method} {path}"
        spec = GUARDED.get((method, path))
        if spec is None:
            where = ", ".join(f"{s['rel']}:{s['lineno']}" for s in sends
                              if (s["method"], s["path"]) == (method, path))
            bad.append(f"{label}（{where}）：JGB 沒有這條路由，也不在 GUARDED")
            continue
        guard_fn, action = spec
        sites = [s for s in sends if (s["method"], s["path"]) == (method, path)]
        for s in sites:
            if not has_real_jgb_guard(trees, guard_fn, s["lineno"]) and guard_fn != "_assistant_write":
                bad.append(f"{label}（{s['rel']}:{s['lineno']}）：{guard_fn}() 沒有 `if not self.use_mock: return`")
        if guard_fn == "_assistant_write":
            # 送出點在包裝函式內（路徑是變數），守衛要在 `_assistant_write` 裡、`_post_request` 之前
            post_line = _post_request_line(trees, "_assistant_write")
            if post_line is None or not has_real_jgb_guard(trees, "_assistant_write", post_line):
                bad.append(f"{label}：_assistant_write() 沒有在 _post_request 之前 `if not self.use_mock: return`")
        if action not in extra_actions:
            bad.append(f"{label}：WRITE_NOT_SUPPORTED_ACTIONS 缺 {action}（使用者會先看到確認卡才失敗）")
        if not bad or not bad[-1].startswith(label):
            guarded_ok.append(label)

    print(f"不在 JGB、已守衛：{len(guarded_ok)} 組")
    for g in guarded_ok:
        print(f"  守衛 OK  {g}")
    print(f"不在 JGB、沒守衛：{len(bad)} 條")
    for b in bad:
        print(f"  ✗ {b}")
    if bad:
        print("結果：不通過")
        return 1
    print("結果：通過")
    return 0


def _post_request_line(trees: dict[str, ast.AST], func_name: str) -> Optional[int]:
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                lines = [c.lineno for c in ast.walk(node)
                         if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                         and c.func.attr == "_post_request"]
                if lines:
                    return min(lines)
    return None


if __name__ == "__main__":
    sys.exit(main())
