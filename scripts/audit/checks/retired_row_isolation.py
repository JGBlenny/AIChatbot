#!/usr/bin/env python3
"""不變量 15：**退役 row 不得回到 active 路徑**（T2／3498 停用逼出）。

源起（2026-08-29）：3498 判定 `K1 FULLY_SUBSUMED + UNDER_QUALIFIED_DUPLICATE` 後停用。
實測 mutation 證實：把它改回 active，三個 late-fee 查詢中**兩個**它會回到 **rank 1**，
與真正的 owner（3939／3940）直接競爭排序——正是「保留重複 knowledge 會重新製造
ranking competition」的實證。

## 不變量陳述

> **① 任何被標記 `retirement` 的 row，`is_active` 必須為 false；
> ② 知識檢索的每一個 SELECT 都必須以 `is_active` 過濾
> （少一個，退役 row 就會從那條路徑回到候選）。**

⚠️ 「失效不失憶」：⛔ 本不變量**不要求**刪除宣告或 provenance——
歷史宣告必須保留，否則 A04 等舊證據無法解讀（見不變量 13 的 V1 immutability）。

用法：python3 scripts/audit/checks/retired_row_isolation.py [--self-test]
"""
import ast
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
RETRIEVER = "rag-orchestrator/services/vendor_knowledge_retriever_v2.py"

#: 隔離謂詞的**單一來源**（spec agentic-mcp-orchestration 任務 1.1，2026-09-04）。
#: ⚠️ 自此 `is_active` 不再逐條寫在兩條 SELECT 裡，而是由此函式產出後拼進 WHERE。
#: 本檢查因此要跳過那一層間接——⛔ 但**不放寬**：SELECT 既沒有字面 is_active、
#: 又沒有引用謂詞，或謂詞本身丟了 is_active，一律照紅。
PREDICATE_FUNC = "build_visibility_predicate"
PREDICATE_PLACEHOLDER = "{visibility_sql}"

SQL = ("SELECT COALESCE(string_agg(id::text || ':' || is_active::text, ','), '') "
       "FROM knowledge_base WHERE generation_metadata ? 'retirement';")


def retired_rows():
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", SQL],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    raw = out.stdout.strip()
    return [] if not raw else [p.split(":") for p in raw.split(",")]


def select_blocks(src):
    """取出對 knowledge_base 的 SELECT 區塊（以 FROM knowledge_base 為錨）。

    ⚠️ `SELECT` 後**必須緊接 `kb.`**（2026-09-04 修）：原本的裸 `SELECT` 會錨到
    docstring 裡的散文（`- SELECT alias 為 …`），把整段函式本文吞進區塊 ——
    於是**註解裡出現 `is_active` 這個字就足以讓檢查通過**，是一條靜默假綠燈。
    兩條真 SQL 皆為 `SELECT\\n  kb.id, …`，此錨點對它們無損。
    """
    return [m for m in re.findall(
        r"SELECT\s+kb\..{0,4000}?FROM\s+knowledge_base\s+kb.{0,2000}?(?=\"\"\")",
        src, re.S)]


def predicate_filters_is_active(src):
    """單一來源謂詞是否真的產出 `is_active` 過濾。

    回傳 (found_func: bool, filters: bool)——函式不存在時 found_func=False，
    呼叫端必須大聲失敗，⛔ 不得當成「有過濾」。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False, False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == PREDICATE_FUNC:
            seg = ast.get_source_segment(src, node) or ""
            return True, "kb.is_active" in seg
    return False, False


def violations(src=None, rows=None):
    bad = []
    rows = retired_rows() if rows is None else rows
    for kid, active in rows:
        if active == "t":
            bad.append(f"row {kid} 標記為 retirement 卻仍 `is_active = true`"
                       f"——退役 row 會回到檢索候選並與真正 owner 競爭排序")
    src = src if src is not None else open(os.path.join(REPO, RETRIEVER), encoding="utf-8").read()
    blocks = select_blocks(src)
    if not blocks:
        bad.append(f"{RETRIEVER} 找不到任何對 knowledge_base 的 SELECT——大聲失敗")
    found_pred, pred_ok = predicate_filters_is_active(src)
    if not found_pred:
        bad.append(f"{RETRIEVER} 找不到 {PREDICATE_FUNC}()——隔離謂詞的單一來源已改名或搬家，"
                   f"⛔ 本檢查無從跳過那層間接，大聲失敗")
    elif not pred_ok:
        bad.append(f"{PREDICATE_FUNC}() **未以 is_active 過濾**"
                   f"——所有引用它的檢索路徑都會讓退役 row 回到候選")
    for i, b in enumerate(blocks, 1):
        # 覆蓋方式二選一：字面寫在 SELECT 裡，或引用單一來源謂詞（且該謂詞真的有這條）
        if "is_active" in b:
            continue
        if PREDICATE_PLACEHOLDER in b and found_pred and pred_ok:
            continue
        bad.append(f"{RETRIEVER} 第 {i} 個 knowledge SELECT **未以 is_active 過濾**"
                   f"（既無字面條件，也未引用 {PREDICATE_FUNC}）"
                   f"——退役 row 會從這條路徑回到候選")
    return bad


def self_test() -> int:
    src = open(os.path.join(REPO, RETRIEVER), encoding="utf-8").read()
    cases = [
        ("現況乾淨", violations() == []),
        ("退役 row 仍 active 必須紅", violations(src, [["3498", "t"]]) != []),
        ("退役 row 已停用不得誤報", violations(src, [["3498", "f"]]) == []),
        ("謂詞少了 is_active 必須紅（單一來源版）",
         violations(src.replace("AND kb.is_active = TRUE", "", 1), []) != []),
        ("SELECT 不再引用謂詞必須紅",
         violations(src.replace(PREDICATE_PLACEHOLDER, "", 1), []) != []),
        ("謂詞函式改名／搬家必須紅",
         violations(src.replace(f"def {PREDICATE_FUNC}", "def _moved_away", 1), []) != []),
        ("兩個 SELECT 都抓得到（否則掃描器壞了）", len(select_blocks(src)) == 2),
        ("正對照：謂詞現況真的有 is_active", predicate_filters_is_active(src) == (True, True)),
    ]
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        rows = retired_rows()
        bad = violations(rows=rows)
    except Exception as e:                                    # noqa: BLE001
        print(f"❌ FAIL：檢查無法執行（{e}）——大聲失敗，⛔ 不當成「沒有違規」")
        return 1
    if bad:
        print("❌ FAIL：退役 row 隔離違規：")
        for b in bad:
            print(f"   {b}")
        return 1
    print(f"（退役 row {len(rows)} 筆全部 inactive；knowledge SELECT "
          f"{len(select_blocks(open(os.path.join(REPO, RETRIEVER), encoding='utf-8').read()))} "
          f"個皆有 is_active 過濾；⚠️ 宣告與 provenance **保留**＝失效不失憶）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
