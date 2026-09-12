#!/usr/bin/env python3
"""不變量 36：**文件裡的「查證」指令必須真的跑得出東西**。

⚠️ 編號 35 由「舊鏈隔離 Plan」（`inputs/plan-legacy-isolation-20260910.md` 第 5 稿就緒、
尚未實作）預留給「新線集合 ∩ legacy_only.txt = ∅」，⛔ 不得佔用。

源起（2026-09-12）：CLAUDE.md 的事實紀律明寫「回報事實一律附可重跑的查證指令
（檔案路徑＋可 grep 的符號）」，但**從來沒有任何機制驗過那些指令跑不跑得動**。
一輪實跑逼出四類錯，且三類是同一個成因（路徑寫錯或符號搬家）：

① `docs/deployment-runbook.md` 的 `grep -n "LIMITS" services/agent/limits.py`
   **少了 `rag-orchestrator/` 前綴** ⇒ 照著跑回 "No such file"。
② `docs/api/API_REFERENCE_KNOWLEDGE_ADMIN.md` 同樣少前綴，且它引用的
   `routers/knowledge.py` 本身已刪。
③ `AGENTIC_MCP_ARCHITECTURE.md` 兩條指 `runtime.py`，但
   `_apply_scope_exit`／`_apply_handoff_without_lookup` 定義在 `exit_gates.py`
   （runtime 只是 import）⇒ 字面 `def ...` grep 回 0。
④ `docs/api/mcp-facade.md` 寫「容器內逐支讀」——那是**兩容器陷阱**：長駐容器跑
   映像、落後工作樹。

## 不變量陳述

> 現況敘述型文件裡，每一條 `grep ... "<pattern>" <path>` 形式的查證指令，
> **`<path>` 必須存在，且 `<pattern>` 至少命中一次**。

⚠️ **兩個刻意的例外**（白名單，⛔ 不得用來藏真錯）：
- 論點本身就是「查無」的（例：`grep -c "@router.post" routers/loops.py` 為 0
  正是 `knowledge-loop-status.md` 要證明的事）。
- 退役符號帳本（`agent-path-retired-symbols.md`）——它整份的用途就是記已消失的符號。

⚠️ **掃描範圍刻意排除有日期的紀錄**（`.kiro/specs/**/inputs/`、`reviews/`、
`docs/archive/`、`docs/changelog/`、`docs/maintenance/`、`docs/research/`）：
那些是「當時盤查」的快照，符號後來搬家不算它們的錯。⛔ 但 HANDOFF 與現況
文件不在豁免內——那些是要被照著做的。

⚠️ **BRE 不是 ERE**：文件寫的是 `grep -n "a\\|b" f`（預設 BRE），檢查器必須用
同樣的 `grep -c`（⛔ 不加 `-E`）跑，否則交替語法會被誤判成 0 命中。
2026-09-12 第一版就踩過這個，整輪結果作廢重跑。

用法：python3 scripts/audit/checks/doc_grep_citations.py [--self-test]
"""
import os
import re
import shlex
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

#: 有日期的紀錄型目錄——符號搬家不算它們的錯，⛔ 但不含 HANDOFF
EXCLUDE_DIRS = (
    "/.git/", "/node_modules/", "/.venv/", "/.agents/", "/.codex/",
    "/docs/archive/", "/docs/changelog/", "/docs/maintenance/", "/docs/research/",
    "/inputs/", "/reviews/", "/journal/",
)

#: 論點本身就是「查無」的檔——⛔ 只放整份用途就是記錄消失物的
ZERO_HIT_BY_DESIGN = (
    "docs/architecture/agent-path-retired-symbols.md",
    "docs/user-guides/knowledge-loop-status.md",
)

#: `grep [-flags] "<pattern>" <path>`；`<path>` 可含 glob（用 shell 展開驗）
CITATION = re.compile(
    r'grep\s+((?:-[a-zA-Z]+\s+)*)["\']([^"\']+)["\']\s+((?!--)[^\s`）)|]+\.(?:py|md|json|sh|yml))'
)

#: 該行自陳「預期就是 0 命中」的寫法——那是論點不是錯（⛔ 只認這幾種明示）
ZERO_EXPECTED = ("＝0", "＝ 0", "=0", "= 0", "為 0", "回 0", "零命中", "0 命中", "查無", "並不存在")


def _iter_docs(root):
    for dirpath, dirnames, filenames in os.walk(root):
        rel = "/" + os.path.relpath(dirpath, root).replace(os.sep, "/") + "/"
        if any(x in rel for x in EXCLUDE_DIRS):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.endswith(".md"):
                yield os.path.join(dirpath, fn)


def collect(root):
    """回傳 [(doc_rel, lineno, pattern, path)]。"""
    out = []
    for doc in _iter_docs(root):
        rel = os.path.relpath(doc, root).replace(os.sep, "/")
        if rel in ZERO_HIT_BY_DESIGN:
            continue
        with open(doc, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                for m in CITATION.finditer(line):
                    if any(z in line for z in ZERO_EXPECTED):
                        continue  # 該行自陳預期 0 命中 ⇒ 那是論點
                    out.append((rel, i, m.group(2), m.group(3), "E" in m.group(1)))
    return out


def check_one(pattern, path, root, ere=False):
    """回傳 None＝通過，否則回傳失敗原因字串。

    ⚠️ 路徑可含 glob：`rag-orchestrator/routers/*.py` 是合法的查證寫法，
    ⛔ 不得因為 `os.path.exists` 對 glob 回 False 就判成「檔不存在」。

    ⚠️ **`ere` 必須照文件寫的 flag 帶**：文件若寫 `grep -nE`，檢查器就得用 `-E`；
    一律用 BRE 會把所有 ERE 查證誤判成 0 命中（反之亦然）。
    """
    flag = "-cE" if ere else "-c"
    lflag = "-lE" if ere else "-l"
    if any(ch in path for ch in "*?["):
        # ⛔ 不加 -E（BRE）；-l 只問「有沒有任一檔命中」
        # ⛔ 不用 f"{pattern!r}"——Python repr 會把 `\|` 再 escape 成 `\\|`，
        #    BRE 交替就失效、整條誤判成 0 命中（2026-09-12 踩過）。
        r = subprocess.run(
            "grep %s %s %s 2>/dev/null | head -1" % (lflag, shlex.quote(pattern), path),
            shell=True, cwd=root, capture_output=True, text=True,
        )
        if not r.stdout.strip():
            return "glob 展開後 0 命中"
        return None
    full = os.path.join(root, path)
    if not os.path.exists(full):
        return "檔不存在"
    # ⛔ 不加 -E：文件寫的是 BRE，加 -E 會把 `\|` 誤判成 0 命中
    r = subprocess.run(["grep", flag, pattern, full], capture_output=True, text=True)
    if r.stdout.strip() in ("", "0"):
        return "0 命中"
    return None


def run(root=REPO):
    rows = collect(root)
    bad = []
    for doc, ln, pat, path, ere in rows:
        why = check_one(pat, path, root, ere)
        if why:
            bad.append((doc, ln, pat, path, why, ere))
    return rows, bad


def self_test():
    """檢查器自身的規避測試：三個正對照，缺一即檢查器失效。"""
    fails = []
    # ① exists 那一步真的會判 False
    if check_one("x", "no/such/file.py", REPO) != "檔不存在":
        fails.append("① 不存在的檔沒被判出來")
    # ② 命中時必須回 None（且要用 BRE 交替，證明沒誤加 -E）
    if check_one(
        r"def _no_match\|def _identity_gate_ok",
        "rag-orchestrator/services/agent/tools/jgb2.py", REPO,
    ) is not None:
        fails.append("② BRE 交替被誤判成 0 命中（是不是加了 -E？）")
    # ③ 真的 0 命中時必須判出來
    if check_one(
        "class ThisSymbolDoesNotExistXYZ",
        "rag-orchestrator/services/agent/runtime.py", REPO,
    ) != "0 命中":
        fails.append("③ 0 命中沒被判出來")
    # ④ glob 路徑不得被誤判成「檔不存在」
    if check_one("_FACE_BUILDERS", "rag-orchestrator/services/jgb/*.py", REPO) is not None:
        fails.append("④ glob 路徑被誤判（os.path.exists 對 glob 回 False）")
    # ⑤ ERE 旗標必須被照用（BRE 跑 ERE 語法會 0 命中）
    if check_one(r"^- \[( |x)\] [0-9]+", ".kiro/specs/knowledge-outline-and-intent-architecture/tasks.md",
                 REPO, ere=True) is not None:
        fails.append("⑤ ERE 查證被當 BRE 跑")
    # ⑥ 掃描器真的掃得到東西（⛔ 空集合不得算通過）
    rows = collect(REPO)
    if len(rows) < 20:
        fails.append(f"⑥ 只掃到 {len(rows)} 條查證指令，掃描器可能壞了")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（6 個正對照；掃到 {len(rows)} 條查證指令）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    rows, bad = run()
    if not rows:
        print("❌ FAIL：掃不到任何查證指令——掃描器壞了，⛔ 不得當通過")
        return 1
    if bad:
        print(f"❌ FAIL：{len(rows)} 條查證指令中 {len(bad)} 條跑不出東西")
        for doc, ln, pat, path, why, ere in bad:
            print(f"   [{why}] {doc}:{ln} → grep {'-E ' if ere else ''}'{pat}' {path}")
        return 1
    print(f"✅ PASS（{len(rows)} 條查證指令逐條實跑，路徑存在且皆有命中）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
