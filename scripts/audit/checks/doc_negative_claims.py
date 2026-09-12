#!/usr/bin/env python3
"""不變量 39：**文件說「這東西沒有了」時，那件事必須是真的**。

源起（2026-09-12）：前五把尺**全部只找「把死的說成活的」**，於是反方向累積了四次：

① `AGENTIC_MCP_ARCHITECTURE.md` 寫 `agent_session.py`「規劃中，**對碼查無此檔**」
   ——該檔 347 行，`AgentSession()` 以 AST 數有 13 處呼叫。
② `SYSTEM_ARCHITECTURE.md` §3「已經沒有的（**全部零消費者**）」九條**全都有**
   非測試消費者（`config_for_category` 被 `tools/audit_config.py` 用，等等）。
③ 同檔說 `test_to_openai_tools_strict_req.py` 釘住參數列含 `ctx` ——沒有 `ctx`，
   且那支測的是假 spec。
④ `decision_layer.py` docstring 說「`knowledge_min` 仍被 `tools/kb.py` 讀」
   ——`kb.py` 讀的是 `kb_threshold`，`.knowledge_min` 非測試讀取為 0。

**為什麼這個方向更難發現**：把死的說成活的，讀者照做會撞牆、會回報；
把活的說成死的，讀者只會**繞開它**——沒有人會回報「我沒用那個東西」。

## 不變量陳述

> 現況敘述型文件裡，形如「`X` 不存在／已刪／查無／零讀者／零呼叫端」的斷言，
> 必須逐條為真。三類可機械驗證：
>   (a) `X.py` ＋不存在類詞 ⇒ 該檔確實不在工作樹
>   (b) `SOME_ENV_KEY` ＋零讀者類詞 ⇒ 非測試 `.py` 確實 0 命中
>   (c) `func_name` ＋零呼叫端／只有測試呼叫 ⇒ AST 數 `ast.Call` 在非測試中為 0

⚠️ **(c) 一定要用 AST**：`grep "f("` 會把 docstring 算進來。2026-09-12 就因此
差點把 `build_toc`（真實呼叫 0）誤判成還活著。

⚠️ 排除有日期的紀錄（`archive/`／`changelog/`／`maintenance/`／`research/`／
`inputs/`／`reviews/`）——那些是當時快照。

用法：python3 scripts/audit/checks/doc_negative_claims.py [--self-test]
"""
import ast
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SRC = os.path.join(REPO, "rag-orchestrator")

SKIP = ("/.git/", "/node_modules/", "/.venv/", "/.agents/", "/.codex/", "/archive/",
        "/changelog/", "/maintenance/", "/research/", "/inputs/", "/reviews/", "/journal/", "/dist/")

GONE = ("不存在", "已刪", "查無此檔", "查無此模組", "已砍除", "已移除", "對碼查無")
NOREAD = ("零讀者", "無程式讀取", "零命中", "0 命中", "零引用")
NOCALL = ("零呼叫端", "零生產呼叫端", "只有測試呼叫", "零消費者", "沒有消費者",
          "無呼叫端", "零 production 呼叫", "無人呼叫")

FILE_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_/]*\.py)`")
ENV_RE = re.compile(r"`([A-Z][A-Z0-9_]{4,})`")
FUNC_RE = re.compile(r"`([a-z_][a-z0-9_]{2,})(?:\(\))?`")

#: 同一行出現這些字 ⇒ 該行是在**推翻**否定、或在對照，⛔ 不得判紅
COUNTER = ("仍在", "已落地", "只剩", "是假的", "更正", "正對照", "但它在", "仍然", "還在",
           "例外", "反例", "改成", "現在是", "⇒ 正確")

#: 否定詞必須**緊接在識別子之後**（同一子句），否則是抓到同行別的東西
PROXIMITY = 28


#: 子句邊界——跨過它就換主詞了（「未掛載於 `app.py`，**此路由**不存在」不算對 app.py 的斷言）
CLAUSE_END = "，。、；）)｜|"


def _claims_about(line, ident, words):
    """`ident` 之後、**同一子句內**（不跨標點）出現 words 之一，才算對它的斷言。

    ⚠️ 2026-09-12 兩次收緊：先加鄰近度（否則抓到同行別的識別子），
    再加子句邊界（否則「`app.py`，此路由不存在」會被判成說 app.py 不存在）。
    """
    for m in re.finditer(r"`" + re.escape(ident) + r"`", line):
        rest = line[m.end():]
        # ⚠️ 識別子後面若緊接括號，整個括號都算同一個斷言
        #    （`agent_session.py`（規劃中，Plan R R3，對碼查無此檔） 的「查無此檔」是在說它）
        if rest[:1] in "（(":
            close = rest.find("）") if "）" in rest else rest.find(")")
            window = rest[: close + 1] if close > 0 else rest[:PROXIMITY]
        else:
            tail = rest[:PROXIMITY]
            cut = min([tail.find(c) for c in CLAUSE_END if c in tail] or [len(tail)])
            window = tail[:cut]
        if any(w in window for w in words):
            return True
    return False

CUR_PREFIX = (".kiro/steering/", "docs/architecture/", "docs/api/",
              "docs/guides/", "docs/features/", "docs/user-guides/", "docs/design/")
CUR_EXACT = ("docs/INDEX.md", "README.md", "CLAUDE.md",
             "docs/deployment-runbook.md", ".claude/MAP.md")


def is_current(rel):
    return rel.startswith(CUR_PREFIX) or rel in CUR_EXACT or rel.endswith("README.md")


def _src_files():
    for dirpath, dirnames, filenames in os.walk(SRC):
        if "__pycache__" in dirpath or "/tests/" in dirpath + "/":
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


_BLOB = None


def blob():
    global _BLOB
    if _BLOB is None:
        parts = []
        for f in _src_files():
            with open(f, encoding="utf-8", errors="replace") as fh:
                parts.append(fh.read())
        _BLOB = "\n".join(parts)
    return _BLOB


_CALLS = None


def call_counts():
    """非測試 .py 裡每個被呼叫的名字 → 次數（AST，⛔ 不用 grep）。"""
    global _CALLS
    if _CALLS is None:
        c = {}
        for f in _src_files():
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    tree = ast.parse(fh.read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    fn = node.func
                    nm = fn.id if isinstance(fn, ast.Name) else (
                        fn.attr if isinstance(fn, ast.Attribute) else None)
                    if nm:
                        c[nm] = c.get(nm, 0) + 1
        _CALLS = c
    return _CALLS


def file_exists(rel_py):
    for base in (REPO, SRC):
        if os.path.exists(os.path.join(base, rel_py)):
            return True
    # 只給了 basename 時，全樹找
    if "/" not in rel_py:
        for f in _src_files():
            if os.path.basename(f) == rel_py:
                return True
    return False


def iter_docs():
    for dirpath, dirnames, filenames in os.walk(REPO):
        rel_dir = "/" + os.path.relpath(dirpath, REPO).replace(os.sep, "/") + "/"
        if any(x in rel_dir for x in SKIP):
            dirnames[:] = []
            continue
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), REPO).replace(os.sep, "/")
            if is_current(rel):
                yield rel


def scan():
    bad = []
    n_docs = n_claims = 0
    for rel in iter_docs():
        n_docs += 1
        with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        for i, line in enumerate(lines, 1):
            if any(w in line for w in COUNTER):
                continue  # 該行在推翻否定或做正對照
            for m in set(FILE_RE.findall(line)):
                if not _claims_about(line, m, GONE):
                    continue
                n_claims += 1
                if file_exists(m):
                    bad.append((rel, i, f"說 `{m}` 不存在，但它在", line.strip()[:70]))
            for m in set(ENV_RE.findall(line)):
                if not _claims_about(line, m, NOREAD):
                    continue
                n_claims += 1
                if re.search(r"(?<![\w])" + re.escape(m) + r"(?![\w])", blob()):
                    bad.append((rel, i, f"說 `{m}` 零讀者，但非測試 .py 有", line.strip()[:70]))
            for m in set(FUNC_RE.findall(line)):
                if m in ("py", "md", "json") or not _claims_about(line, m, NOCALL):
                    continue
                n_claims += 1
                n = call_counts().get(m, 0)
                if n:
                    bad.append((rel, i, f"說 `{m}` 零呼叫端，但 AST 數到 {n} 處", line.strip()[:70]))
    return n_docs, n_claims, bad


def self_test():
    fails = []
    # ① 已知不存在的檔 ⇒ file_exists 必 False
    if file_exists("routers/chat.py"):
        fails.append("① 已刪的 routers/chat.py 被判成存在")
    # ② 已知存在的檔 ⇒ 必 True（正對照）
    if not file_exists("services/agent/runtime.py"):
        fails.append("② 現存的 runtime.py 被判成不存在（比對法壞了）")
    # ③ AST 呼叫數：已知有呼叫的函式
    if call_counts().get("build_canon_toc", 0) == 0:
        fails.append("③ build_canon_toc 的 AST 呼叫數為 0（AST 掃描壞了）")
    # ④ AST 呼叫數：已知零呼叫的函式 ⇒ 必 0
    if call_counts().get("build_toc", 0) != 0:
        fails.append("④ build_toc 應為 0 呼叫（grep 才會誤判，AST 不該）")
    # ⑤ env 命中：已知有讀者
    if not re.search(r"(?<![\w])KB_SIMILARITY_THRESHOLD(?![\w])", blob()):
        fails.append("⑤ 正對照 KB_SIMILARITY_THRESHOLD 在非測試 .py 找不到")
    n_docs, n_claims, _ = scan()
    if n_docs < 50:
        fails.append(f"⑥ 只掃到 {n_docs} 份現況文件")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（6 個正對照；掃 {n_docs} 份文件、{n_claims} 條否定斷言）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    n_docs, n_claims, bad = scan()
    if n_docs == 0:
        print("❌ FAIL：掃不到現況文件，掃描器壞了")
        return 1
    if bad:
        print(f"❌ FAIL：{n_claims} 條否定斷言中 {len(bad)} 條不成立（把活的說成死的）")
        for rel, i, why, line in bad:
            print(f"   {rel}:{i} {why}")
            print(f"      {line}")
        return 1
    print(f"✅ PASS（{n_docs} 份文件、{n_claims} 條「這東西沒有了」的斷言逐條實驗證，全部成立）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
