#!/usr/bin/env python3
"""不變量 12：**retrieval semantic contract 與 scoring surface 的單一實作**（D1/D2/D3）。

**源起**（2026-08-29，R8 已證的結構性缺口）：系統宣告某 row 能承接的責任
（Face／downstream capability）**比** 拿去 scoring 的文字（question_summary）**更寬**。
4656 的 capability 是「該筆帳單完整現況」，scoring surface 卻連
「已繳／未繳・已寄出／草稿」一個字都沒有 ⇒ A03 中 I2-explicit 僅 3/10。

⚠️ 更深一層：**scoring surface 過去沒有單一實作點**。embedding 產生端與
reranker 端各自寫一份 `question_summary or answer` 的優先序，
⇒ 兩份實作＝**兩個 semantic universe**，且會各自漂移。

## 不變量陳述（產品層，與欄位名解耦）

> **① retrieval scoring 看到的文字，必須由唯一一個契約函式決定；
> ② 該契約的「宣告讀取」⛔ 不得 fallback 猜測；
> ③ 任何 stage-specific divergence 必須在登記簿上明示（D2）。**

## 機器判定（四項，⛔ 全部要有正對照）

```text
A  reranker payload 端必須呼叫 scoring_surface() 並送出 surface 欄位
B  api_server 必須**優先**採用 scoring_surface（早於 legacy 優先序）
C  所有 embedding surface 產生點必須在登記簿上（新增未登記＝紅）
D  retrieval_representation() 讀取器內 ⛔ 不得出現 summary／answer／keywords
```

用法：python3 scripts/audit/checks/retrieval_representation_contract.py [--self-test]
"""
import ast
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

CONTRACT = "rag-orchestrator/services/retrieval_representation.py"
PAYLOAD = "rag-orchestrator/services/semantic_reranker.py"
SERVER = "semantic_model/scripts/api_server.py"

SURFACE_FUNC = "scoring_surface"
SURFACE_KEY = "scoring_surface"
READER_FUNC = "retrieval_representation"
#: ⛔ 讀取器內不得出現的「偷偷補齊」來源
FORBIDDEN_IN_READER = ("question_summary", "answer", "keywords")

#: ── D2 divergence register ────────────────────────────────────────────────
#: embedding surface 的**每一個**產生點都要在這裡，且標明狀態。
#: `uses_contract`        已改走 scoring_surface()
#: `divergent_pending`    已知與契約不一致，**待業主裁定**，⛔ 不得默默沿用
EMBEDDING_SITES = {
    ("knowledge-admin/backend/app.py", "text_for_embedding"): "divergent_pending",
    ("rag-orchestrator/services/knowledge_import_service.py", "text"): "divergent_pending",
    ("scripts/regenerate_all_embeddings.py", "text"): "divergent_pending",
}
#: 會被視為 embedding surface 賦值的變數名
SURFACE_VAR_NAMES = {"text", "text_for_embedding", "embedding_text"}
#: 掃描範圍（⛔ 不掃 tests／backtest：那是量測程式，不是 production surface）
SCAN_DIRS = ("rag-orchestrator/services", "knowledge-admin/backend", "scripts")
SCAN_EXCLUDE = ("/tests/", "/test_", "/backtest", "/node_modules/", "/.venv/")


def _tree(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return ast.parse(f.read())


def _func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _strings(node):
    """節點下所有字串字面值（⚠️ **排除 docstring**——註解提到 ≠ 使用）。"""
    out = []
    doc_nodes = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(n, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc_nodes.add(id(body[0].value))
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes:
            out.append(n.value)
    return out


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | \
           {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


# ── A：payload 端 ──────────────────────────────────────────────────────────
def check_payload(tree):
    """回傳 violation 字串 list。"""
    bad = []
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == SURFACE_FUNC]
    if not calls:
        bad.append(f"{PAYLOAD} 未呼叫 {SURFACE_FUNC}()——scoring surface 仍是本地自寫優先序")
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
    keys = set()
    for d in [n for n in ast.walk(tree) if isinstance(n, ast.Dict)]:
        for k in d.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                keys.add(k.value)
            elif isinstance(k, ast.Name):
                keys.add(consts.get(k.id, ""))
    # 常數可能來自 import（不在本模組 body）；此時以 import 名稱視為已解析
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    if SURFACE_KEY not in keys and "SURFACE_FIELD" not in imported:
        bad.append(f"{PAYLOAD} 的候選 dict 未帶 {SURFACE_KEY} 欄位——server 端收不到")
    return bad


# ── B：server 端優先序 ─────────────────────────────────────────────────────
def check_server_precedence(tree):
    fn = _func(tree, "rerank")
    if fn is None:
        return [f"{SERVER} 找不到 rerank()——大聲失敗，⛔ 不當作沒有違規"]
    first = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            first.setdefault(n.value, n.lineno)
    if SURFACE_KEY not in first:
        return [f"{SERVER}::rerank 未讀取 {SURFACE_KEY}"]
    if "question_summary" in first and first[SURFACE_KEY] > first["question_summary"]:
        return [f"{SERVER}::rerank 讀 {SURFACE_KEY} 晚於 question_summary——優先序錯"]
    return []


# ── C：embedding surface 登記簿 ────────────────────────────────────────────
def scan_embedding_sites(root=None):
    """回傳 {(relpath, varname)} —— 疑似 embedding surface 的賦值點。"""
    root = root or REPO
    found = set()
    for d in SCAN_DIRS:
        base = os.path.join(root, d)
        for dirpath, _dn, fns in os.walk(base):
            for fn in fns:
                if not fn.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                if any(x in "/" + rel for x in SCAN_EXCLUDE):
                    continue
                try:
                    with open(full, encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                except (SyntaxError, UnicodeDecodeError):
                    continue
                # ⚠️ **需要一層 alias 傳遞**：`question = row['question_summary']`
                #    再 `text = question` 是真實存在的寫法
                #    （scripts/regenerate_all_embeddings.py 就是這樣）。
                #    只看 RHS 有沒有直接出現 question_summary 會整個漏掉
                #    ——本檢查器第一版的自我測試就是這樣紅的。
                tainted = set()
                for n in ast.walk(tree):
                    if not isinstance(n, ast.Assign):
                        continue
                    refs = _names(n.value) | set(_strings(n.value))
                    is_surface = ("question_summary" in refs) or bool(refs & tainted)
                    tgts = [t.id for t in n.targets if isinstance(t, ast.Name)]
                    if not is_surface:
                        continue
                    tainted.update(tgts)
                    for t in tgts:
                        if t in SURFACE_VAR_NAMES:
                            found.add((rel, t))
    return found


def check_register(found):
    bad = []
    for site in sorted(found):
        if site not in EMBEDDING_SITES:
            bad.append(f"未登記的 embedding surface 產生點：{site[0]} 的 `{site[1]}` "
                       f"⇒ D2 要求 divergence 必須明示，⛔ 不得默默新增第二個 semantic universe")
    return bad


# ── D：讀取器不得 fallback ────────────────────────────────────────────────
def check_reader_no_fallback(tree):
    fn = _func(tree, READER_FUNC)
    if fn is None:
        return [f"{CONTRACT} 找不到 {READER_FUNC}()——大聲失敗"]
    used = set(_strings(fn)) | _names(fn)
    hit = [w for w in FORBIDDEN_IN_READER if w in used]
    if hit:
        return [f"{READER_FUNC}() 出現 {hit}——宣告讀取器⛔不得 fallback 猜測"]
    return []


def self_test():
    cases = []
    # A 正對照：拿掉 scoring_surface 呼叫必須被抓到
    src = open(os.path.join(REPO, PAYLOAD), encoding="utf-8").read()
    cases.append(("A 現況乾淨", check_payload(ast.parse(src)) == []))
    planted = src.replace("scoring_surface(c)", "(c.get('question_summary',''), 'x')")
    cases.append(("A 移除契約呼叫必須紅", check_payload(ast.parse(planted)) != []))
    planted2 = src.replace("SURFACE_FIELD: surface,", "").replace(
        "        SURFACE_FIELD,\n", "")
    cases.append(("A 移除 surface 欄位必須紅", check_payload(ast.parse(planted2)) != []))
    # B 正對照：把 scoring_surface 讀取搬到 question_summary 之後
    ssrc = open(os.path.join(REPO, SERVER), encoding="utf-8").read()
    cases.append(("B 現況乾淨", check_server_precedence(ast.parse(ssrc)) == []))
    bad_order = ssrc.replace('surface = candidate.get("scoring_surface")',
                             'question = candidate.get("question_summary", "")')
    cases.append(("B 移除優先讀取必須紅", check_server_precedence(ast.parse(bad_order)) != []))
    # C 正對照：現況全部登記；植入一個未登記站點必須紅
    found = scan_embedding_sites()
    cases.append(("C 現況全部已登記", check_register(found) == []))
    cases.append(("C 掃描器抓得到已知站點（否則是掃描器壞了）",
                  len(found) >= len(EMBEDDING_SITES)))
    cases.append(("C 未登記站點必須紅",
                  check_register(found | {("x/y.py", "text")}) != []))
    # D 正對照
    csrc = open(os.path.join(REPO, CONTRACT), encoding="utf-8").read()
    cases.append(("D 現況乾淨", check_reader_no_fallback(ast.parse(csrc)) == []))
    bad_reader = csrc.replace('    row = knowledge or {}\n    value = row.get(TRANSPORT_FIELD)',
                              '    row = knowledge or {}\n    value = row.get("question_summary")')
    cases.append(("D 植入 fallback 必須紅", check_reader_no_fallback(ast.parse(bad_reader)) != []))
    # ⚠️ docstring 提到禁詞**不得**誤報（前四次踩過的「說明 vs 使用」量尺失效）
    doc_only = csrc.replace('    row = knowledge or {}\n    value = row.get(TRANSPORT_FIELD)',
                            '    """提到 question_summary 只是說明"""\n'
                            '    row = knowledge or {}\n    value = row.get(TRANSPORT_FIELD)')
    cases.append(("D 註解提到禁詞不得誤報", check_reader_no_fallback(ast.parse(doc_only)) == []))
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    bad = []
    bad += check_payload(_tree(PAYLOAD))
    bad += check_server_precedence(_tree(SERVER))
    found = scan_embedding_sites()
    if not found:
        print("❌ FAIL：embedding surface 掃描結果為空——掃描器失效，⛔ 不當成「沒有違規」")
        return 1
    bad += check_register(found)
    bad += check_reader_no_fallback(_tree(CONTRACT))
    if bad:
        print("❌ FAIL：retrieval semantic contract 違規：")
        for b in bad:
            print(f"   {b}")
        return 1
    pending = [k for k, v in EMBEDDING_SITES.items() if v == "divergent_pending"]
    print(f"（scoring surface 單一實作點 {SURFACE_FUNC}()；embedding 產生點 {len(found)} 個全部已登記）")
    if pending:
        print(f"⚠️  登記在案的 **待裁定 divergence** {len(pending)} 處（⛔ 非 PASS 的一部分，是明示欠債）：")
        for rel, var in sorted(pending):
            print(f"   {rel} 的 `{var}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
