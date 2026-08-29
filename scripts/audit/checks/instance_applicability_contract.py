#!/usr/bin/env python3
"""不變量 10：instance applicability 的三態資料契約（U1／P1a）。

**源起**（2026-08-29 U1 第一刀）：決定「該不該由 Face 擁有」的屬性——
「回答這一題需不需要使用者自己的資料」——**沒有被任何欄位記錄**。
架構早就為它留了位置（`grounding_scope.requires_instance_reference`），
但實查宣告數 ＝ 0 ⇒ instance gate 的條件 C 恆為 False
⇒ **授權機制是在一個授權輸入結構性缺席的系統上被評估的**。

本不變量守兩件事：

```text
① 值域封閉：DB 內的宣告只能是 'instance' / 'general'
   ⛔ 不接受 'Instance'／'true'／'是' —— 容忍變體＝讓資料品質問題靜默通過
② 讀取唯一化：宣告鍵只能經 services/instance_applicability.py 讀
   ⛔ 別處直接讀 → 遲早出現「缺宣告就當 general」或「用 form_id 推導」的 fallback，
     而那正是本輪要修掉的病灶（3509 是反證：direct_answer 卻需要實值）
```

⚠️ **本不變量不要求 coverage**：P1a 只建立契約，population 是 P1b。
   未宣告的 row 一律是 UNKNOWN，且 UNKNOWN **不得**取得正向授權含義。

用法：python3 scripts/audit/checks/instance_applicability_contract.py [--self-test]
退出碼：0＝PASS，1＝FAIL。
"""
import json
import os
import re
import subprocess
import sys
import ast
import warnings

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CONTRACT_MODULE = "rag-orchestrator/services/instance_applicability.py"
#: Face 層的鍵早於本模組存在，其現役讀取點是 gate 自身（P1c 才會改它）
FACE_KEY_ALLOWED = {CONTRACT_MODULE, "rag-orchestrator/services/instance_reference_gate.py"}
SCAN_DIRS = ["rag-orchestrator/services", "rag-orchestrator/routers", "rag-orchestrator/tools"]
LEGAL_VALUES = {"instance", "general"}

KNOWLEDGE_KEY = "instance_applicability"
FACE_KEY = "requires_instance_reference"


def _key_reads(path):
    """回傳 [(行號, 出現的鍵)]——**只看非 docstring 的字串常量**。

    ⚠️ 兩次踩坑的結論：
      ① 只剝 `#` 註解 → **docstring** 提到鍵名被誤判成越權讀取。
      ② 改用 tokenize 剝掉所有 STRING → **把要偵測的目標一起剝掉了**，
         因為鍵在程式碼裡本來就是字串常量（`meta.get("instance_applicability")`）。
    ⇒ 正解是 AST：精確排除 docstring 與 import，其餘字串常量照查。
    """
    try:
        with warnings.catch_warnings():   # 被掃檔案自身的 SyntaxWarning 不屬本不變量
            warnings.simplefilter("ignore")
            tree = ast.parse(open(path, encoding="utf-8").read())
    except (SyntaxError, UnicodeDecodeError):
        return []
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings:
            for key in (KNOWLEDGE_KEY, FACE_KEY):
                if key in node.value:
                    hits.append((getattr(node, "lineno", 0), key))
    return hits


def scan_unauthorized_key_reads(root=None):
    """回傳 [(相對路徑, 行號, 鍵)]——在契約模組之外直接讀宣告鍵的地方。"""
    root = root or REPO
    out = []
    for d in SCAN_DIRS:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                for line_no, key in _key_reads(os.path.join(dirpath, fn)):
                    if key == KNOWLEDGE_KEY and rel == CONTRACT_MODULE:
                        continue
                    if key == FACE_KEY and rel in FACE_KEY_ALLOWED:
                        continue
                    out.append((rel, line_no, key))
    return out


def illegal_values(rows):
    """回傳值域違規清單。⚠️ 純函式，供 --self-test 離線驗。"""
    return [r for r in rows
            if r.get("value") is not None and r.get("value") not in LEGAL_VALUES]


SQL = r"""
SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)::text FROM (
  SELECT id, generation_metadata->>'instance_applicability' AS value
  FROM knowledge_base
  WHERE is_active AND generation_metadata ? 'instance_applicability'
) t;
"""


def fetch_rows():
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", SQL],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "[]")


def self_test() -> int:
    cases = []
    cases.append(("合法值不得誤報",
                  illegal_values([{"id": 1, "value": "instance"},
                                  {"id": 2, "value": "general"}]) == []))
    bad = illegal_values([{"id": 3, "value": "Instance"}, {"id": 4, "value": "true"},
                          {"id": 5, "value": "是"}])
    cases.append(("大小寫／布林字面／中文變體必須紅", len(bad) == 3))
    cases.append(("未宣告（value=None）不進值域檢查",
                  illegal_values([{"id": 6, "value": None}]) == []))
    # 讀取唯一化的正控制：對一棵植入違規的假樹掃描必須紅
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "rag-orchestrator", "services")
        os.makedirs(d)
        with open(os.path.join(d, "rogue.py"), "w", encoding="utf-8") as fh:
            fh.write('x = meta.get("instance_applicability")\n')
        planted = scan_unauthorized_key_reads(tmp)
        cases.append(("植入的越權讀取必須被抓到", len(planted) == 1))
        # 突變：註解裡提到鍵名不得誤報
        with open(os.path.join(d, "rogue.py"), "w", encoding="utf-8") as fh:
            fh.write('# 說明：instance_applicability 由契約模組負責\n')
        cases.append(("註解提及鍵名不得誤報", scan_unauthorized_key_reads(tmp) == []))
        # 突變：**docstring** 提及鍵名亦不得誤報（第一版栽在這裡）
        with open(os.path.join(d, "rogue.py"), "w", encoding="utf-8") as fh:
            fh.write('def f():\n    """真值來源已移到 instance_applicability。"""\n    return 1\n')
        cases.append(("docstring 提及鍵名不得誤報", scan_unauthorized_key_reads(tmp) == []))
        # 正控制再確認：剝除不得把真正的讀取一起吃掉
        with open(os.path.join(d, "rogue.py"), "w", encoding="utf-8") as fh:
            fh.write('def f(meta):\n    """說明。"""\n    return meta.get("instance_applicability")\n')
        cases.append(("剝除後真正的讀取仍必須被抓到",
                      len(scan_unauthorized_key_reads(tmp)) == 1))
    for name, ok in cases:
        print(f"{'✅' if ok else '❌'} {name}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    fail = 0
    if not os.path.isfile(os.path.join(REPO, CONTRACT_MODULE)):
        print(f"❌ FAIL：契約模組不存在 {CONTRACT_MODULE}")
        return 1
    hits = scan_unauthorized_key_reads()
    if hits:
        print("❌ FAIL：以下位置繞過契約模組直接讀宣告鍵：")
        for rel, line, key in hits:
            print(f"   {rel}:{line}  {key}")
        fail = 1
    rows = fetch_rows()
    bad = illegal_values(rows)
    if bad:
        print("❌ FAIL：以下宣告值不在合法值域（instance／general）：")
        for r in bad:
            print(f"   知識 {r['id']}：{r['value']!r}")
        fail = 1
    if not fail:
        print(f"（已宣告 {len(rows)} 筆；未宣告＝UNKNOWN，⛔ 不得取得正向授權含義）")
    return fail


if __name__ == "__main__":
    sys.exit(main())
