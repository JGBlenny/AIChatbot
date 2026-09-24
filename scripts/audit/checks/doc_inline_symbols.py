#!/usr/bin/env python3
"""不變量 41：**架構正本用反引號寫出的識別字必須在程式碼庫找得到**。

源起（2026-09-12 對抗性演練）：`AGENTIC_MCP_ARCHITECTURE.md` 寫「逐字重播，
`llc_calls=0`」——全 repo `llc_calls` **0 命中**，真正的欄位是 `llm_calls`。
而同一份文件的另一節寫的是對的 `llm_calls=0` ⇒ **同檔內部不一致**。

⚠️ **為什麼不變量 36 抓不到**：36 只跑文件裡**標為「查證」的 grep 指令**，
而這個錯的符號寫在**敘述內文**裡，不在任何查證指令中。⇒ 尺有覆蓋盲區，
本檔補的就是那一塊：凡是被反引號括起來、形狀像識別字的東西，都得真的存在。

## 不變量陳述

> `docs/architecture/**` 的敘述裡，形如 `` `snake_case_name` `` 或 `` `UPPER_SNAKE` ``
> （**必須含至少一個底線**——單字太容易撞到一般名詞）的反引號內容，
> 必須在 `rag-orchestrator/**` 的 `.py`／`.sql`／`.json`／`.yml` 裡以**完整詞**出現，
> 否則 FAIL 並印出檔名與行號。

⚠️ 例外走 `scripts/audit/data/doc_symbols_absent_ok.txt`，每筆**必須寫理由**。
   目前 17 筆：16 筆是 §4「19 張執行期零引用表」的成員（0 命中正是那張表的定義），
   1 筆是 nginx 指令。⛔ 例外表不得用來塞「查不到所以先擋起來」。

⚠️ **刻意只掃 `docs/architecture/**`**：那是現況正本，錯一個符號讀者就 grep 不到。
   其餘目錄（帳本／changelog／spec）會寫已刪符號，是本分，⛔ 不進這把尺。

用法：python3 scripts/audit/checks/doc_inline_symbols.py [--self-test]
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOC_ROOT = os.path.join(REPO, "docs", "architecture")
SRC_ROOT = os.path.join(REPO, "rag-orchestrator")
EXC_FILE = os.path.join(REPO, "scripts", "audit", "data", "doc_symbols_absent_ok.txt")
SRC_EXT = (".py", ".sql", ".json", ".yml", ".yaml")
SKIP_DIRS = {"__pycache__", ".venv", "node_modules", ".git"}

#: 必須含至少一個底線——單字（`answer`／`kind`）會撞到一般名詞，誤殺遠多於命中。
IDENT = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)`")
#: ⚠️ 有日期的紀錄是當時快照（與不變量 38／39／40 同一排除法）。
SNAPSHOT = ("/archive/", "/changelog/", "/inputs/", "/reviews/")


def exceptions():
    out = {}
    if not os.path.exists(EXC_FILE):
        return out
    with open(EXC_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            name, _, why = line.partition("\t")
            out[name.strip()] = why.strip()
    return out


def docs():
    out = []
    for dirpath, dirnames, files in os.walk(DOC_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), REPO)
            if any(s in "/" + rel for s in SNAPSHOT):
                continue
            out.append(rel)
    return sorted(out)


_BLOB = None


def blob():
    """整個程式碼庫串成一坨——逐檔 grep 會慢 100 倍且結果相同。"""
    global _BLOB
    if _BLOB is None:
        parts = []
        for dirpath, dirnames, files in os.walk(SRC_ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in files:
                if fn.endswith(SRC_EXT):
                    try:
                        with open(os.path.join(dirpath, fn), encoding="utf-8",
                                  errors="ignore") as fh:
                            parts.append(fh.read())
                    except OSError:
                        pass
        _BLOB = "\n".join(parts)
    return _BLOB


def present(name):
    return re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", blob()) is not None


def scan():
    exc = exceptions()
    found, bad = {}, []
    doc_list = docs()
    for rel in doc_list:
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                for m in IDENT.finditer(line):
                    found.setdefault(m.group(1), (rel, i))
    for name, (rel, i) in sorted(found.items()):
        if name in exc or present(name):
            continue
        bad.append((rel, i, name))
    return doc_list, len(found), bad


def self_test():
    fails = []
    doc_list = docs()
    if len(doc_list) < 5:
        fails.append(f"① 只掃到 {len(doc_list)} 份架構文，走訪壞了")
    # ② 正對照：已知必然存在的符號必須判成 present
    if not present("split_sentences"):
        fails.append("② 正對照 split_sentences 判成不存在（語料或比對壞了）")
    # ③ 反向正對照：已知不存在的錯字必須判成 absent
    if present("llc_calls"):
        fails.append("③ 已知錯字 llc_calls 被判成存在（完整詞比對壞了）")
    # ④ 那個錯字 ⛔ 不得被例外表放行——它正是本尺的立案理由
    if "llc_calls" in exceptions():
        fails.append("④ llc_calls 被塞進例外表（例外表被用來掩蓋病灶）")
    # ⑤ 正則必須抓得到含底線的識別字、且 ⛔ 不抓單字
    hits = [m.group(1) for m in IDENT.finditer("`llm_calls` 與 `answer` 與 `MAX_N`")]
    if hits != ["llm_calls", "MAX_N"]:
        fails.append(f"⑤ 正則行為不符（實得 {hits}）")
    # ⑥ 例外表每筆都要有理由
    noreason = [k for k, v in exceptions().items() if not v]
    if noreason:
        fails.append(f"⑥ 例外表有 {len(noreason)} 筆沒寫理由：{noreason[:3]}")
    # ⑦ 語料非空（拿不到一律 FAIL，⛔ 不靜默通過）
    if len(blob()) < 100_000:
        fails.append(f"⑦ 程式語料只有 {len(blob())} 字元，讀取壞了")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（7 個正對照；掃 {len(doc_list)} 份架構文、"
          f"例外表 {len(exceptions())} 筆皆有理由）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    doc_list, n, bad = scan()
    if not doc_list:
        print("❌ FAIL：掃不到架構文，掃描器壞了")
        return 1
    if bad:
        print(f"❌ FAIL：{len(bad)} 個反引號識別字在程式碼庫 0 命中（讀者照它 grep 會撲空）")
        for rel, i, name in bad:
            print(f"   {rel}:{i}  `{name}`")
        print(f"   確定 0 命中是對的 ⇒ 連同理由加進 {os.path.relpath(EXC_FILE, REPO)}")
        return 1
    print(f"✅ PASS（{len(doc_list)} 份架構文、{n} 個反引號識別字逐個實查，"
          f"皆在程式碼庫找得到或已登記例外）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
