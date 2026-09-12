#!/usr/bin/env python3
"""不變量 38：**現況敘述型文件不得把已刪除的模組當現況提**。

源起（2026-09-12）：2026-09-11 刪掉 31 個舊 REST 對話鏈模組後，文件面清了六輪，
每一輪都還有殘留——而且最後一輪是在**我自己剛重寫過的 `.kiro/steering/structure.md`**
裡抓到 `deduplication_config.py`／`backtest_framework_async.py`（目錄樹的另外兩節沒跟著改）。
⇒ 人工逐份掃不可靠，且這件事**完全機械**：清單可以從 git 導。

## 不變量陳述

> 對「現況敘述型」文件（steering／MAP／各 README／`docs/architecture`／`docs/api`／
> `docs/guides`／`docs/features`／`docs/user-guides`／`docs/design`／INDEX／runbook），
> 每一行若提到一個**曾被刪除且現在確實不存在**的 `.py` 檔名，
> 其上下文（前 4 行至後 2 行）必須帶否定標記，否則判紅。

**關鍵字清單完全由 git 導出，⛔ 無人工詞表**：
`git log --diff-filter=D --name-only -- rag-orchestrator` 取所有曾刪除的 `.py`，
① 過濾掉現在還存在的路徑（刪了又加回來的）、
② 過濾掉 basename 與任一現存檔相同的（`models.py`／`__init__.py` 這類會誤殺）。
2026-09-12 建立時得 378 個關鍵字，掃 127 份文件命中 8 行，其中 7 行是真缺陷。

⚠️ **排除有日期的紀錄**（`archive/`／`changelog/`／`maintenance/`／`research/`／
`inputs/`／`reviews/`）：那些是當時快照，模組後來被刪不算它們的錯。

⚠️ **否定標記清單刻意寬**（⛔／已刪／退役／不存在／查無／404／…）：
寧可漏抓也不要逼人把「這東西已經沒了」寫成特定句型——
本不變量要擋的是「**把死的當活的列出來**」，不是管文風。

用法：python3 scripts/audit/checks/doc_dead_module_names.py [--self-test]
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

SKIP_DIRS = ("/.git/", "/node_modules/", "/.venv/", "/.agents/", "/.codex/",
             "/archive/", "/changelog/", "/maintenance/", "/research/",
             "/inputs/", "/reviews/", "/journal/", "/dist/")

NEG = ("⛔", "已刪", "退役", "不存在", "零讀取", "🔴", "已拆", "不再", "已移除", "砍除",
       "歷史", "當時", "不會", "沒有", "無法", "失效", "不影響", "查無", "刪除",
       "已死", "不讀", "停用", "404", "405", "更正", "無存活範例", "已於 2026-09")

CURRENT_PREFIXES = (".kiro/steering/", "docs/architecture/", "docs/api/",
                    "docs/guides/", "docs/features/", "docs/user-guides/", "docs/design/")
CURRENT_EXACT = ("docs/INDEX.md", "README.md", "CLAUDE.md",
                 "docs/deployment-runbook.md", ".claude/MAP.md")


def is_current(rel):
    return (rel.startswith(CURRENT_PREFIXES) or rel in CURRENT_EXACT
            or rel.endswith("README.md"))


def dead_names():
    """從 git 導出：曾刪除、現在不存在、且 basename 不與現存檔衝突的 .py。"""
    r = subprocess.run(
        ["git", "log", "--diff-filter=D", "--name-only", "--format=", "--", "rag-orchestrator"],
        cwd=REPO, capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    gone = {x for x in r.stdout.split()
            if x.endswith(".py") and not os.path.exists(os.path.join(REPO, x))}
    alive = set()
    for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, "rag-orchestrator")):
        if "__pycache__" in dirpath:
            continue
        alive.update(f for f in filenames if f.endswith(".py"))
    return sorted({os.path.basename(x) for x in gone} - alive)


def iter_current_docs():
    for dirpath, dirnames, filenames in os.walk(REPO):
        rel_dir = "/" + os.path.relpath(dirpath, REPO).replace(os.sep, "/") + "/"
        if any(x in rel_dir for x in SKIP_DIRS):
            dirnames[:] = []
            continue
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), REPO).replace(os.sep, "/")
            if is_current(rel):
                yield rel


def scan(names):
    bad = []
    n_docs = 0
    pats = [(d, re.compile(r"(?<![\w/])" + re.escape(d))) for d in names]
    for rel in iter_current_docs():
        n_docs += 1
        with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        for i, line in enumerate(lines, 1):
            hit = [d for d, p in pats if p.search(line)]
            if not hit:
                continue
            ctx = "".join(lines[max(0, i - 5):i + 2])
            if any(m in ctx for m in NEG):
                continue
            bad.append((rel, i, hit, line.strip()[:88]))
    return n_docs, bad


def self_test():
    fails = []
    names = dead_names()
    if names is None:
        fails.append("① git log 取不到刪除清單")
    else:
        # 正對照：chat.py 必在清單（已知刪除）
        if "chat.py" not in names:
            fails.append("② 正對照 chat.py 不在死檔清單（導出法壞了）")
        # 負對照：runtime.py ⛔ 不得在清單（現存）
        if "runtime.py" in names:
            fails.append("③ 現存的 runtime.py 被列進死檔清單")
        # 負對照：basename 衝突的不得入列
        if "__init__.py" in names or "models.py" in names:
            fails.append("④ basename 與現存檔衝突的未被剔除（會大量誤殺）")
        if len(names) < 50:
            fails.append(f"⑤ 只導出 {len(names)} 個關鍵字，清單可能不完整")
    n_docs, _ = scan(names or [])
    if n_docs < 50:
        fails.append(f"⑥ 只掃到 {n_docs} 份現況文件，掃描器可能壞了")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（6 個正對照；git 導出 {len(names)} 個死檔名、掃 {n_docs} 份文件）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    names = dead_names()
    if names is None:
        print("❌ FAIL：git log 取不到刪除清單——⛔ 不得因此判通過")
        return 1
    n_docs, bad = scan(names)
    if n_docs == 0:
        print("❌ FAIL：掃不到任何現況文件，掃描器壞了")
        return 1
    if bad:
        print(f"❌ FAIL：{n_docs} 份現況文件中 {len(bad)} 行把已刪模組當現況提")
        for rel, i, hit, line in bad:
            print(f"   {rel}:{i} {hit} :: {line}")
        print("   ⇒ 刪掉那一行，或在上下文寫明它已不存在（⛔ 不要只加標記留著清單）")
        return 1
    print(f"✅ PASS（{len(names)} 個死檔名 × {n_docs} 份現況文件，無當現況提的）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
