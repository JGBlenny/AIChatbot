#!/usr/bin/env python3
"""不變量 8（AST 版）：決策層門檻唯一讀值點（retrieval-decision-layer R7.4／D-20）。

**為什麼是 AST 不是 grep**（D-20 實證）：grep 版對 8 種寫法只擋 1 種——
`os.environ[...]`、`os.environ.get(...)`、`from os import getenv`、字串拼接、
變數間接、**甚至多一個空格**全都能繞過；常數檢查也對 `_SOP_MIN = 0.6`、
型別註記、dict 形式、內聯字面量無感。字面比對防不住無意的重構或排版。

檢查兩件事（掃描範圍見 SCAN_DIRS，唯一豁免 ALLOWED_FILE）：
1. **門檻 env 讀值**：任何形式讀 KB_SIMILARITY_THRESHOLD／FORM_TRIGGER_THRESHOLD——
   含 os.getenv／os.environ[]／os.environ.get／別名 import／變數間接／字串拼接。
2. **六 case 門檻常數**：模組層或函式內把 0.55／0.6／0.15 綁到門檻語義的名稱上
   （含型別註記與 dict 值）。

用法：python3 scripts/audit/checks/decision_threshold_ast.py [--self-test]
退出碼：0＝PASS，1＝FAIL（違規清單印到 stdout）。
"""
import ast
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
# 掃描範圍比 grep 版更廣（D-20：原版漏 tools/、scripts/、knowledge-admin/）
SCAN_DIRS = [
    "rag-orchestrator/app.py", "rag-orchestrator/routers", "rag-orchestrator/services",
    "rag-orchestrator/tools", "rag-orchestrator/scripts", "knowledge-admin",
]
ALLOWED_FILE = "rag-orchestrator/services/decision_layer.py"   # 唯一讀值點
THRESHOLD_ENVS = {"KB_SIMILARITY_THRESHOLD", "FORM_TRIGGER_THRESHOLD"}
# 六 case 門檻常數的語義名稱（大小寫不敏感、底線前綴不論）
CONST_HINTS = ("sop_min", "knowledge_min", "score_gap")


class _Visitor(ast.NodeVisitor):
    """追蹤字串常數在變數間的流動，攔截間接讀取。"""

    def __init__(self, path):
        self.path = path
        self.viol = []
        self.str_vars = {}            # 變數名 → 字串值（含拼接結果）
        self.env_aliases = {"getenv"}  # from os import getenv 之類

    # ── 工具 ──
    def _const_str(self, node):
        """求值成字串（含字面量、變數、+ 拼接、.join），求不出回 None。"""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return self.str_vars.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            l, r = self._const_str(node.left), self._const_str(node.right)
            return (l + r) if (l is not None and r is not None) else None
        if isinstance(node, ast.JoinedStr):          # f-string 全常數段
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                else:
                    return None
            return "".join(parts)
        return None

    def _hit(self, node, kind, detail):
        self.viol.append(f"{self.path}:{node.lineno}  [{kind}] {detail}")

    # ── import 別名 ──
    def visit_ImportFrom(self, node):
        if node.module == "os":
            for a in node.names:
                if a.name in ("getenv", "environ"):
                    self.env_aliases.add(a.asname or a.name)
        self.generic_visit(node)

    # ── 變數追蹤 ＋ 常數定義檢查 ──
    def visit_Assign(self, node):
        val = self._const_str(node.value)
        for t in node.targets:
            if isinstance(t, ast.Name) and val is not None:
                self.str_vars[t.id] = val
        self._check_threshold_const(node.targets, node.value, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):                  # SOP_MIN_THRESHOLD: float = 0.6
        if node.value is not None:
            self._check_threshold_const([node.target], node.value, node)
        self.generic_visit(node)

    def _is_hint(self, name):
        n = name.lower().lstrip("_")
        return any(h in n for h in CONST_HINTS)

    def _check_threshold_const(self, targets, value, node):
        for t in targets:
            name = t.id if isinstance(t, ast.Name) else (t.attr if isinstance(t, ast.Attribute) else None)
            if name and self._is_hint(name) and isinstance(value, ast.Constant) \
                    and isinstance(value.value, (int, float)):
                self._hit(node, "六case常數", f"{name} = {value.value}")
        # dict 形式：{"sop_min": 0.55, ...}
        if isinstance(value, ast.Dict):
            for k, v in zip(value.keys, value.values):
                ks = self._const_str(k) if k is not None else None
                if ks and self._is_hint(ks) and isinstance(v, ast.Constant) \
                        and isinstance(v.value, (int, float)):
                    self._hit(node, "六case常數(dict)", f'"{ks}": {v.value}')

    # ── env 讀取 ──
    def visit_Call(self, node):
        f = node.func
        is_env_call = False
        if isinstance(f, ast.Attribute) and f.attr in ("getenv", "get"):
            base = f.value
            if isinstance(base, ast.Name) and base.id == "os":
                is_env_call = f.attr == "getenv"
            elif isinstance(base, ast.Attribute) and base.attr == "environ":
                is_env_call = True                    # os.environ.get(...)
            elif isinstance(base, ast.Name) and base.id in self.env_aliases:
                is_env_call = True                    # environ.get(...)
        elif isinstance(f, ast.Name) and f.id in self.env_aliases:
            is_env_call = True                        # getenv(...)
        if is_env_call and node.args:
            key = self._const_str(node.args[0])
            if key in THRESHOLD_ENVS:
                self._hit(node, "env讀值", key)
            elif key is None:
                pass                                  # 動態鍵無從判定，交給人工
        self.generic_visit(node)

    def visit_Subscript(self, node):                  # os.environ["KB_..."]
        v = node.value
        if (isinstance(v, ast.Attribute) and v.attr == "environ") or \
           (isinstance(v, ast.Name) and v.id in self.env_aliases and v.id != "getenv"):
            key = self._const_str(node.slice)
            if key in THRESHOLD_ENVS:
                self._hit(node, "env讀值(subscript)", key)
        self.generic_visit(node)


def scan_source(src, path):
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"{path}: 解析失敗 {e}"]
    v = _Visitor(path)
    v.visit(tree)
    return v.viol


def iter_files():
    for rel in SCAN_DIRS:
        p = os.path.join(REPO, rel)
        if os.path.isfile(p) and p.endswith(".py"):
            yield p
        for root, dirs, names in os.walk(p):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".venv", "tests")]
            for n in names:
                if n.endswith(".py"):
                    yield os.path.join(root, n)


# ── 規避測試（D-20 要求：每條不變量須附規避測試）──
EVASIONS = [
    ('os.getenv("KB_SIMILARITY_THRESHOLD", "0.55")', "直接呼叫"),
    ('os.getenv(  "KB_SIMILARITY_THRESHOLD"  )', "多餘空白"),
    ("os.environ['KB_SIMILARITY_THRESHOLD']", "environ 下標"),
    ('os.environ.get("FORM_TRIGGER_THRESHOLD", "0.75")', "environ.get"),
    ('from os import getenv\ngetenv("KB_SIMILARITY_THRESHOLD")', "別名 import"),
    ('os.getenv("KB_" + "SIMILARITY_THRESHOLD")', "字串拼接"),
    ('k = "FORM_TRIGGER_THRESHOLD"\nos.getenv(k)', "變數間接"),
    ("_SOP_MIN = 0.6", "底線前綴常數"),
    ("SOP_MIN_THRESHOLD: float = 0.55", "型別註記"),
    ('THRESHOLDS = {"sop_min": 0.55, "score_gap": 0.15}', "dict 形式"),
]
CLEAN = ['x = os.getenv("SOME_OTHER_ENV")', "cfg = DecisionConfig.load()", "n = 0.55"]


def self_test():
    bad = []
    for src, name in EVASIONS:
        if not scan_source(src, "<evasion>"):
            bad.append(f"❌ 規避未被攔截：{name}  ——  {src.splitlines()[-1]}")
    for src in CLEAN:
        if scan_source(src, "<clean>"):
            bad.append(f"❌ 誤報：{src}")
    if bad:
        print("\n".join(bad)); return 1
    print(f"✅ 規避測試：{len(EVASIONS)} 種寫法全數攔截、{len(CLEAN)} 個乾淨樣本零誤報")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    viol = []
    for f in iter_files():
        if os.path.relpath(f, REPO) == ALLOWED_FILE:
            continue
        with open(f, encoding="utf-8", errors="replace") as fh:
            viol += scan_source(fh.read(), os.path.relpath(f, REPO))
    if viol:
        print("❌ FAIL：決策層門檻在唯一讀值點之外被讀取/定義：")
        print("\n".join("  " + v for v in viol))
        return 1
    print("✅ PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
