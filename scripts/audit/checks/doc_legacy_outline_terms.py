#!/usr/bin/env python3
"""不變量 42：**現況文件 ⛔ 不得用「一受眾一份正本」時代的舊詞描述知識正本**。

源起（2026-09-16，業主）：DSP-058 已把正本改成「九架一份、受眾＝細目屬性 `target_user`」，
但程式殘留符號（`build_audience_outline`／`agent_outlines[audience]`／`_STATIC_TOC_IDENTITY`）
帶著舊模型的詞，我照著程式講就一路說「pm 視圖／prospect 視圖／受眾正本」——業主連問三次
「pm 不是被廢棄的規格嗎」，並說「只要你一直沿用舊名稱，我就無法判斷你是否在做新架構」。
靠人「注意用詞」不可靠，改成 `make audit` 機械擋。

## 不變量陳述

> 現況文件（`docs/**`、`.claude/MAP.md`、`.claude/DECISIONS.md`、`.kiro/specs/*/design.md`、
> `rag-orchestrator/canon/README.md`）的敘述行 ⛔ 不得出現舊詞：
>   受眾正本／受眾視圖／pm 視圖／prospect 視圖／受眾各自正本／`canon/prospect.md`／`canon/property_manager.md`
> 除非該行是三種位置之一：
>   (a) **詞彙表／改名對照**——行內含「舊詞」「舊名」「詞彙表」「→ 現行」
>   (b) **封存指引**——行內含「封存」「⛔ 不是現況」「docs/archive/」「canon-pre-」
>   (c) **裁決紀錄**——`.claude/DECISIONS.md` 的 DSP-047～DSP-057 列（2026-09-14 一受眾一檔時期的裁決，歷史紀錄）
> 其餘一律 FAIL 並印行號。

現行詞（寫文件用這些）：**九架正本 `canon/jgb/`**、**細目屬性 `target_user`**、
**售前身分／業者身分的篩選結果**（＝該身分依 `canon_visible` 從一份正本篩出的細目集合；不是檔、不是規格）、
**每回合注入＝K=5 候選＋目錄（toc）**。

⚠️ 快照目錄（archive／inputs／reviews／changelog／research／maintenance）排除——那是當時紀錄，不是現況。
⚠️ `tasks.md`／briefs／plan 檔不掃：它們是歷史帳，且含舊詞是為了記錄改名前後。

用法：python3 scripts/audit/checks/doc_legacy_outline_terms.py [--self-test]
"""
import glob
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOC_ROOTS = ("docs",)
DOC_FILES = (
    ".claude/MAP.md",
    ".claude/DECISIONS.md",
    "rag-orchestrator/canon/README.md",
)
DESIGN_GLOB = ".kiro/specs/*/design.md"

#: 舊詞（一受眾一份正本時代）。⛔ 現行詞 ⛔ 不得進來（self-test ⑤ 釘住）。
LEGACY_TERMS = (
    r"受眾正本",
    r"受眾視圖",
    r"受眾各自",
    r"pm\s*視圖",
    r"prospect\s*視圖",
    r"canon/prospect\.md",
    r"canon/property_manager\.md",
)
#: 規則 (a)：詞彙表／改名對照。
GLOSSARY_WORDS = ("舊詞", "舊名", "詞彙表", "→ 現行", "→現行")
#: 規則 (b)：封存指引。
ARCHIVE_WORDS = ("封存", "⛔ 不是現況", "docs/archive/", "canon-pre-")
#: 規則 (c)：一受眾一檔時期的裁決列（歷史紀錄，只在 DECISIONS.md 生效）。
HISTORIC_DSP = re.compile(r"^\|\s*DSP-0(4[7-9]|5[0-7])\s*\|")

SNAPSHOT_DIRS = ("/archive/", "/changelog/", "/maintenance/", "/research/",
                 "/inputs/", "/reviews/")

#: 現行詞——⛔ 不得被詞表抓到（self-test ⑤）。
CURRENT_TERMS_PROBE = (
    "九架正本 canon/jgb/ 的細目屬性 target_user",
    "業者身分的篩選結果（依 canon_visible 篩出）",
    "每回合注入＝K=5 候選＋目錄",
)


def current_docs():
    out = []
    for root in DOC_ROOTS:
        base = os.path.join(REPO, root)
        for dirpath, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), REPO)
                if any(s in "/" + rel for s in SNAPSHOT_DIRS):
                    continue
                out.append(rel)
    for rel in DOC_FILES:
        if os.path.isfile(os.path.join(REPO, rel)):
            out.append(rel)
    for full in glob.glob(os.path.join(REPO, DESIGN_GLOB)):
        out.append(os.path.relpath(full, REPO))
    return sorted(set(out))


def line_allowed(rel, line):
    if any(w in line for w in GLOSSARY_WORDS):
        return "詞彙表"
    if any(w in line for w in ARCHIVE_WORDS):
        return "封存指引"
    if rel.endswith(".claude/DECISIONS.md") and HISTORIC_DSP.search(line):
        return "歷史裁決列"
    return None


def scan():
    bad, n_hits = [], 0
    docs = current_docs()
    for rel in docs:
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if not any(re.search(p, line) for p in LEGACY_TERMS):
                    continue
                n_hits += 1
                if line_allowed(rel, line) is None:
                    bad.append((rel, i, line.rstrip()))
    return docs, n_hits, bad


def self_test():
    fails = []
    docs = current_docs()
    if len(docs) < 10:
        fails.append(f"① 只掃到 {len(docs)} 份現況文件，走訪壞了")
    for must in (".claude/MAP.md", "rag-orchestrator/canon/README.md"):
        if must not in docs:
            fails.append(f"② {must} 不在掃描清單（走訪漏了）")
    if not any(rel.endswith("/design.md") for rel in docs):
        fails.append("② 沒掃到任何 spec design.md（glob 壞了）")
    probe = "prospect 視圖與 pm 視圖各自讀 canon/prospect.md"
    if not any(re.search(p, probe) for p in LEGACY_TERMS):
        fails.append("③ 詞表對已知舊詞樣本沒中（詞表壞了）")
    if line_allowed("docs/architecture/X.md", probe) is not None:
        fails.append("④ 已知違規樣本被放行（放行規則太寬）")
    for cur in CURRENT_TERMS_PROBE:
        if any(re.search(p, cur) for p in LEGACY_TERMS):
            fails.append(f"⑤ 現行詞被詞表抓到（詞表汙染）：{cur}")
    if line_allowed("docs/architecture/X.md", "舊詞「pm 視圖」→ 現行「業者身分的篩選結果」") is None:
        fails.append("⑥ 詞彙表行被判違規（會逼人刪掉對照表本身）")
    if line_allowed("rag-orchestrator/canon/README.md", "舊版 canon/prospect.md 封存於 docs/archive/2026-09/canon-pre-library/") is None:
        fails.append("⑦ 封存指引行被判違規")
    if line_allowed(".claude/DECISIONS.md", "| DSP-052 | 受眾模型維持 A：受眾各自正本 |") is None:
        fails.append("⑧ DECISIONS 歷史裁決列被判違規")
    if line_allowed("docs/architecture/X.md", "| DSP-052 | 受眾各自正本 |") is not None:
        fails.append("⑨ 歷史裁決放行規則外溢到 DECISIONS.md 以外的檔")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（9 個正對照；掃 {len(docs)} 份現況文件）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    docs, n_hits, bad = scan()
    if bad:
        print(f"❌ FAIL：{len(bad)} 行在現況文件裡用了一受眾一檔時代的舊詞（受眾正本／pm 視圖／canon/prospect.md…），"
              f"讀者會以為還在做舊架構；改用「九架正本／細目屬性 target_user／<身分>的篩選結果」，或標明封存／詞彙表")
        for rel, i, line in bad[:40]:
            print(f"  - {rel}:{i}: {line[:120]}")
        if len(bad) > 40:
            print(f"  …另 {len(bad) - 40} 行")
        return 1
    print(f"✅ 不變量 42：現況文件無舊詞——掃 {len(docs)} 份、舊詞出現 {n_hits} 次皆在詞彙表／封存／歷史裁決位置")
    return 0


if __name__ == "__main__":
    sys.exit(main())
