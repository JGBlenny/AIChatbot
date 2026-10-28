#!/usr/bin/env python3
"""不變量 46：**驗收廣度表結構**（GOV-4；全域規則「驗收廣度」第 1 條）。

只驗結構，不判斷內容好壞：
  範圍：`.kiro/specs/**/acceptance*.md`，git 首次加入的 commit 時間 >= SINCE（GOV-4 核可時刻），加上尚未追蹤的同名樣式檔。
  每份須有：
   ① `## 廣度` 標題；
   ② 其後的 markdown 表，表頭恰為七欄（依序）：項目｜類型｜資料組（用／可用）｜不同輸入數｜重複次數｜輸入撰寫者｜改前對照
      （「類型」欄可寫「類型」或「類型（使用者層／機制項）」，「改前對照」欄可寫「改前對照」或「改前對照（哪批題、哪個改前版本）」，容許空白）；
   ③ 每個「使用者層」列的「不同輸入數」以整數開頭且 >= 5（業主 Q2(a) 下限；資料組不做數值檢查）；「機制項」列免；
   ④ 表後有一行以「上位驗收方式：」開頭（值可為「無」）。
退出碼：0 通過；1 FAIL；2 前置條件失敗（不是 git repo／git 不可用，⛔ 靜默跳過）。
用法：acceptance_breadth.py [--root <repo>] [--self-test]
"""
import os
import re
from datetime import datetime
import subprocess
import sys

DEFAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
# GOV-4 核可時刻（2026-10-21 01:40 +08:00）；首次加入的 commit 時間早於此者不受檢。
SINCE = "2026-10-21T01:40:00+08:00"
MIN_INPUTS = 5
HEADERS = ["項目", "類型", "資料組（用／可用）", "不同輸入數", "重複次數", "輸入撰寫者", "改前對照"]
# 照全域條文第 1 條逐字寫的表頭（含括號說明）也算合規。
HEADER_ALT = {1: {"類型（使用者層／機制項）"}, 6: {"改前對照（哪批題、哪個改前版本）"}}


def _norm(s):
    s = re.sub(r"\s+", "", s)
    return s.replace("(", "（").replace(")", "）").replace("/", "／")


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def check_text(text):
    """回傳錯誤原因清單；空清單＝通過。"""
    lines = text.splitlines()
    idx = next((i for i, l in enumerate(lines) if l.startswith("## 廣度")), None)
    if idx is None:
        return ["缺「## 廣度」標題"]
    i = idx + 1
    while i < len(lines) and not lines[i].strip().startswith("|"):
        if lines[i].startswith("## "):
            break
        i += 1
    if i >= len(lines) or not lines[i].strip().startswith("|"):
        return ["「## 廣度」之後沒有 markdown 表"]
    tbl = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        tbl.append(lines[i])
        i += 1
    errs = []
    head = [_norm(c) for c in _cells(tbl[0])]
    want = [_norm(h) for h in HEADERS]
    alt = {k: {_norm(t) for t in v} for k, v in HEADER_ALT.items()}
    ok_head = len(head) == 7 and all(
        (head[k] == want[k]) or (head[k] in alt.get(k, ())) for k in range(7))
    if not ok_head:
        return ["表頭不是規定的七欄（%s）；實際：%s" % ("｜".join(HEADERS), "｜".join(_cells(tbl[0])))]
    rows = tbl[2:]
    if len(tbl) < 2 or not re.fullmatch(r"[\s|:\-]+", tbl[1]):
        errs.append("表頭下一行不是分隔線")
        rows = tbl[1:]
    if not rows:
        errs.append("表內沒有資料列")
    for r in rows:
        c = _cells(r)
        if len(c) != 7:
            errs.append("列欄數不是 7：%s" % r.strip()[:60])
            continue
        typ = c[1]
        if "使用者層" in typ:
            m = re.match(r"\s*(\d+)", c[3])
            if not m:
                errs.append("使用者層項目「%s」的不同輸入數不是整數開頭：「%s」" % (c[0], c[3]))
            elif int(m.group(1)) < MIN_INPUTS:
                errs.append("使用者層項目「%s」的不同輸入數 %s 低於下限 %d" % (c[0], m.group(1), MIN_INPUTS))
        elif "機制項" not in typ:
            errs.append("項目「%s」的類型須為「使用者層」或「機制項」：「%s」" % (c[0], typ))
    if not any(l.startswith("上位驗收方式：") for l in lines[i:]):
        errs.append("表後缺「上位驗收方式：」行（沒有就寫「上位驗收方式：無」）")
    return errs


def _git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True)
    except FileNotFoundError:
        print("❌ 前置條件失敗：git 不可用")
        sys.exit(2)
    if p.returncode != 0:
        print("❌ 前置條件失敗：git %s 失敗（%s）— root=%s" % (" ".join(args), p.stderr.strip(), root))
        sys.exit(2)
    return p.stdout


def scope(root):
    _git(root, "rev-parse", "--is-inside-work-tree")
    tracked = [f for f in _git(root, "ls-files", "-z").split("\0") if f]
    untracked = [f for f in _git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0") if f]

    def match(f):
        return f.startswith(".kiro/specs/") and re.fullmatch(r"acceptance[^/]*\.md", os.path.basename(f))

    out = []
    for f in sorted(filter(match, tracked)):
        dates = [d for d in _git(root, "log", "--diff-filter=A", "--format=%cI", "--", f).split() if d]
        if not dates:
            print("❌ 前置條件失敗：%s 已追蹤但查不到首次加入日（淺層 clone？）" % f)
            sys.exit(2)
        if min(datetime.fromisoformat(d) for d in dates) >= datetime.fromisoformat(SINCE):
            out.append(f)
    out += sorted(f for f in untracked if match(f))
    return out


SAMPLE_OK = """# x
## 廣度
| 項目 | 類型（使用者層／機制項） | 資料組（用／可用） | 不同輸入數 | 重複次數 | 輸入撰寫者 | 改前對照 |
|---|---|---|---|---|---|---|
| V3 | 使用者層 | 8／79 | 8 題 | 每題 2 次 | fresh 代理 | de7f4653 |

上位驗收方式：目標正本 §1
"""
ROW = "| V3 | 使用者層 | 8／79 | 8 題 | 每題 2 次 | fresh 代理 | de7f4653 |"
# 只照全域條文第 1 條寫成的表（GOV-4 清單 #6 片段的形狀：表頭逐字照條文、含括號說明）。
SAMPLE_RULE_TEXT = """## 廣度

| 項目 | 類型（使用者層／機制項） | 資料組（用／可用） | 不同輸入數 | 重複次數 | 輸入撰寫者 | 改前對照（哪批題、哪個改前版本） |
|---|---|---|---|---|---|---|
| U1 | 使用者層 | 5／5 | 8 | 3 | 不讀程式的模擬客人代理 | 同一批 5 組 × 8 輸入；改前＝merge-base |
| M1 | 機制項 | — | — | — | — | — |

上位驗收方式：無
"""


def self_test():
    cases = [
        ("缺廣度表", "# x\n## 廣度\n\n上位驗收方式：無\n", False),
        ("表頭缺欄", SAMPLE_OK.replace(" | 改前對照 |", " |").replace(" | de7f4653 |", " |"), False),
        ("使用者層輸入數 4", SAMPLE_OK.replace("8 題", "4 題"), False),
        ("缺上位驗收方式行", SAMPLE_OK.replace("上位驗收方式：目標正本 §1\n", ""), False),
        ("合規樣本", SAMPLE_OK, True),
        ("上位驗收方式：無", SAMPLE_OK.replace("目標正本 §1", "無"), True),
        ("機制項其餘欄「—」", SAMPLE_OK.replace(ROW, "| M1 | 機制項 | — | — | — | — | — |"), True),
        ("表頭逐字照條文第 1 條", SAMPLE_RULE_TEXT, True),
        ("表頭逐字照條文、輸入數 4", SAMPLE_RULE_TEXT.replace("| 5／5 | 8 | 3 |", "| 5／5 | 4 | 3 |"), False),
    ]
    bad = 0
    for name, text, want in cases:
        errs = check_text(text)
        got = not errs
        if got != want:
            bad += 1
        print("[%s] %s：預期 %s／實際 %s%s" % ("OK" if got == want else "MISMATCH", name,
                                            "PASS" if want else "FAIL", "PASS" if got else "FAIL",
                                            "" if got else "（%s）" % errs[0]))
    if bad:
        print("❌ 自我測試 %d 項不符" % bad)
        return 1
    print("自我測試 %d 項全符" % len(cases))
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = DEFAULT_ROOT
    if "--root" in argv:
        root = os.path.abspath(argv[argv.index("--root") + 1])
    files = scope(root)
    print("驗收廣度表結構（GOV-4，首次加入時間 >= %s 或未追蹤）：受檢 %d 份" % (SINCE, len(files)))
    for f in files:
        print("  - " + f)
    if not files:
        print("0 份")
        print("✅ PASS")
        return 0
    fails = 0
    for f in files:
        with open(os.path.join(root, f), encoding="utf-8") as fh:
            errs = check_text(fh.read())
        for e in errs:
            print("❌ %s：%s" % (f, e))
        fails += bool(errs)
    if fails:
        return 1
    print("✅ PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
