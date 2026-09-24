#!/usr/bin/env python3
"""不變量 40：**架構正本的敘述段落 ⛔ 不得把呼叫端寫成本系統的一部分**。

源起（2026-09-12）：三份架構文各自寫了一段措辭不同的「外部串接不屬於本系統」宣告，
但沒有**判準**，於是每遇到一個詞就要重新想一次它算哪邊：

- `quick_replies` 名字來自通路平台，但它是 `TurnResult` 的欄位、是本系統的對外契約
  ——曾被當成「外部名詞」差點清掉，那會清掉本系統自己的契約。
- `relay.jgbsmart.com` 是外部主機，但**是本系統自己的程式**決定要去打它
  （`IMAGE_URL_ALLOWLIST`），屬於本系統的安全邊界，該寫。
- 「pm 在 LINE 說」「清單點選（LIFF）」則是純粹的呼叫端畫面，⛔ 不該寫。

三者形狀不同，用「本系統／外部」兩分法判不動。判準與歸屬表在
`docs/architecture/BOUNDARY.md`（三個桶：本系統／呼叫端／外部相依）。本檔機械檢查桶 ②。

## 不變量陳述

> `docs/architecture/**`＋`docs/api/**` 的敘述行裡，桶 ②（呼叫端專有名詞）
> 只允許出現在三種位置：
>   (a) **讀者／對象聲明**——「讀者：…」「對象：…」「適用：…」起頭的行
>   (b) **邊界宣告**——行內同時帶邊界關鍵詞（不屬於本系統／⛔ 不進架構／BOUNDARY.md…）
>   (c) **外部文件連結**——行內含指向 `.kiro/specs/**` 或 `docs/jgb2-*` 的路徑
> 其餘一律 FAIL 並印出行號。

⚠️ **桶 ② 的詞表必須只含呼叫端專有名詞**。⛔ 不得放 `quick_replies`、
`line_official`、`confirm_qr_labels`——那些是本系統自己的符號（桶 ①），
放進來會反過來逼人刪掉真正的契約。詞表逐條對應 BOUNDARY.md §2 判給桶 ② 的列。

⚠️ **`docs/api/mcp-facade.md` 的「讀者」段落點名呼叫端是對的**——讀者聲明不是
架構敘述，由規則 (a) 放行；把它算成違規會逼人刪掉串接文件該有的讀者說明。

用法：python3 scripts/audit/checks/doc_system_boundary.py [--self-test]
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOC_ROOTS = ("docs/architecture", "docs/api")

#: 桶 ②：呼叫端專有名詞。⛔ 逐條對應 BOUNDARY.md §2 判給桶 ② 的列，⛔ 不得混入桶 ①／③。
CALLER_TERMS = (
    r"LIFF",
    r"LINE\s*(?:OA|bot|Bot|官方帳號)",
    r"line-bot",
    r"jgb2\s*(?:Web|網站|後端)",
)
#: 規則 (a)：讀者／對象聲明起頭。
READER_DECL = re.compile(r"^[>\s*]*(?:讀者|對象|適用|使用者角色)[:：]")
#: 規則 (b)：行內邊界關鍵詞。
BOUNDARY_WORDS = (
    "不屬於本系統", "⛔ 不進架構", "不進架構敘述", "BOUNDARY.md",
    "部署時接上來的消費者", "方向更正", "呼叫端專有名詞",
)
#: 規則 (c)：外部文件連結。
EXT_LINK = re.compile(r"\.kiro/specs/|docs/jgb2-")

#: ⚠️ 有日期的紀錄是當時快照，⛔ 不當現況敘述（與不變量 38／39 同一排除法）。
SNAPSHOT_DIRS = ("/archive/", "/changelog/", "/maintenance/", "/research/",
                 "/inputs/", "/reviews/")


def current_docs():
    out = []
    for root in DOC_ROOTS:
        base = os.path.join(REPO, root)
        for dirpath, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, REPO)
                if any(s in "/" + rel for s in SNAPSHOT_DIRS):
                    continue
                out.append(rel)
    return sorted(out)


def line_allowed(line):
    """這一行雖然帶桶 ② 的詞，但是否落在三種允許位置之一。"""
    if READER_DECL.search(line):
        return "讀者聲明"
    if any(w in line for w in BOUNDARY_WORDS):
        return "邊界宣告"
    if EXT_LINK.search(line):
        return "外部文件連結"
    return None


def scan():
    bad, n_hits = [], 0
    docs = current_docs()
    for rel in docs:
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if not any(re.search(p, line) for p in CALLER_TERMS):
                    continue
                n_hits += 1
                if line_allowed(line) is None:
                    bad.append((rel, i, line.rstrip()))
    return docs, n_hits, bad


def self_test():
    fails = []
    docs = current_docs()
    # ① 掃得到檔（掃不到＝路徑壞了，⛔ 不靜默通過）
    if len(docs) < 5:
        fails.append(f"① 只掃到 {len(docs)} 份架構／API 文件，走訪壞了")
    # ② 正對照：BOUNDARY.md 本身必在清單裡
    if "docs/architecture/BOUNDARY.md" not in docs:
        fails.append("② BOUNDARY.md 不在掃描清單（走訪漏了）")
    # ③ 正對照：詞表必須抓得到一個已知必然存在的字樣
    probe = "pm 在 LINE OA 上點了 LIFF 清單"
    if not any(re.search(p, probe) for p in CALLER_TERMS):
        fails.append("③ 詞表對已知違規樣本沒中（詞表壞了）")
    # ④ 該樣本沒有任何允許位置關鍵詞 ⇒ 必須被判違規
    if line_allowed(probe) is not None:
        fails.append("④ 已知違規樣本被放行（放行規則太寬）")
    # ⑤ 反向正對照：帶邊界關鍵詞的同一句必須被放行
    if line_allowed("jgb2 Web、LINE OA demo 不屬於本系統") is None:
        fails.append("⑤ 邊界宣告句被判違規（放行規則太緊，會逼人刪掉宣告本身）")
    # ⑥ 讀者聲明必須被放行（mcp-facade.md 的真實形狀）
    if line_allowed("> 讀者：要從**伺服器端**接上的工程（jgb2 後端、LINE bot 後端）") is None:
        fails.append("⑥ 讀者聲明被判違規（會逼人刪掉串接文件的讀者說明）")
    # ⑦ 桶 ① 的符號 ⛔ 不得進詞表（進了會逼人刪掉本系統自己的契約）
    for own in ("quick_replies", "line_official", "confirm_qr_labels"):
        if any(re.search(p, own) for p in CALLER_TERMS):
            fails.append(f"⑦ 本系統自己的符號 {own} 被詞表抓到（詞表汙染）")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（7 個正對照；掃 {len(docs)} 份架構／API 文件）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    docs, n_hits, bad = scan()
    if not docs:
        print("❌ FAIL：掃不到架構／API 文件，掃描器壞了")
        return 1
    if bad:
        print(f"❌ FAIL：{len(bad)} 行把呼叫端寫進了架構敘述")
        print("   判準與歸屬表見 docs/architecture/BOUNDARY.md")
        for rel, i, line in bad:
            print(f"   {rel}:{i}")
            print(f"      {line[:150]}")
        return 1
    print(f"✅ PASS（{len(docs)} 份架構／API 文件、{n_hits} 處呼叫端字樣"
          f"全部落在讀者聲明／邊界宣告／外部連結三種允許位置）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
