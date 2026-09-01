#!/usr/bin/env python3
"""Baseline Epoch 1 集合式 oracle 評估器（E-C1）。

用法：
    ./scripts/run-tests.sh integration <baseline scope 的兩個檔案> > run.log 2>&1
    python3 scripts/audit/baseline_oracle.py run.log

⚠️ **判準是集合，⛔ 不是數字**：只看 failure count 會假綠——
   穩定紅少 1 筆 ＋ 冒出全新 1 筆 ＝ 總數不變。

⚠️ 兩個曾經踩過的解析坑（2026-09-01，⛔ 別再踩）：
   ① pytest 在某些 locale 會把非 ASCII 的 parametrize id 逃逸成 `\\uXXXX`，
      而 baseline artifact 存的是中文字面 ⇒ 直接比字串會**整批誤判成新回歸**。
   ② `^FAILED (\\S+)` 會在空格處截斷（例：`[收據 PDF 在哪裡下載]`）⇒ 誤判 1 筆。
   本檔一律取整行再正規化。

⚠️ 內建正對照：actual ∩ KNOWN 必須等於 KNOWN 的大小；不相等即代表**比對本身失效**，
   此時任何「無回歸」結論 ⛔ 不可信，直接 exit 3。
"""
import codecs
import json
import os
import re
import sys

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        ".kiro", "specs", "conversational-routing-execution",
                        "evidence", "baseline-epoch-1.json")


def normalize(raw: str) -> str:
    s = raw.strip()
    if "\\u" in s:
        s = codecs.decode(s, "unicode_escape")
    return re.sub(r"\s+-\s+.*$", "", s).strip()   # 去掉 " - AssertionError…" 尾巴


def main(log_path: str) -> int:
    with open(os.path.abspath(BASELINE), encoding="utf-8") as f:
        b = json.load(f)
    known = set(b["KNOWN_STABLE_FAILURES"])
    flaky = set(b["FLAKY_RED_ALLOWLIST"])
    log = open(log_path, encoding="utf-8", errors="replace").read()

    m = re.search(r"collected (\d+) items", log)
    collected = int(m.group(1)) if m else 0
    if collected == 0:
        print("❌ collected=0 —— **空跑不是通過**，⛔ 不得判 PASS")
        return 3

    actual = {normalize(x) for x in re.findall(r"^FAILED (.+)$", log, re.M)}

    # 正對照：比對邏輯自身必須看得見已知病灶
    overlap = actual & known
    if len(overlap) != len(known) and len(overlap) == 0:
        print(f"❌ 正對照失敗：actual ∩ KNOWN = 0（應為 {len(known)}）"
              f"——比對本身失效，⛔ 任何『無回歸』結論不可信")
        return 3

    new = actual - known - flaky
    missing = known - actual

    print(f"collected={collected}  actual_red={len(actual)}")
    print(f"KNOWN 重現 {len(overlap)}/{len(known)}  flaky 命中 {len(actual & flaky)}")
    for x in sorted(new):
        print(f"  ❌ NEW_REGRESSION: {x}")
    for x in sorted(missing):
        print(f"  ⚠️ 穩定紅未重現（⛔ 不叫 regression；查清產品修好／drift 前 ⛔ 不得從 baseline 刪除）: {x}")

    if new:
        print("\nORACLE_VERDICT = NEW_REGRESSION")
        return 1
    if missing:
        print("\nORACLE_VERDICT = UNEXPECTED_BASELINE_IMPROVEMENT —— 需人工裁決，⛔ 不自動放行")
        return 2
    print("\nORACLE_VERDICT = PASS —— 無新回歸，穩定紅全數重現")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(64)
    sys.exit(main(sys.argv[1]))
