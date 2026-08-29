#!/usr/bin/env python3
"""不變量 14：**late-fee instance ownership 單一化**（業主定案 2026-08-29）。

源起（T1 決定性雙引擎比對）：`bill_diagnosis._diagnose_late_fee`（A）與
`滯納金 face.build_late_fee_facts`（B）曾同時承接「這一筆的滯納金診斷」。
A 經實測為 **partial implementation**，且在合約列／滯納金帳單列會輸出**錯誤語義**。
⇒ 收斂為單一 owner B，`precedence` **REJECTED**。

## 不變量陳述

> **① late-fee instance intent ⛔ 不得由 `bill_diagnosis` 收斂作答
> （含 generic path —— 只刪 dispatch 而落 generic 是「錯誤綠燈」）；
> ② `_DIAG_KEYWORDS` 必須保持不變（它是 generic discriminator，
> 動它會誤傷發送／取消／手動到帳三種診斷）。**

用法：python3 scripts/audit/checks/late_fee_ownership.py [--self-test]
"""
import os
import sys

# ⚠️ **必須在 import 專案模組之前關閉 bytecode 寫入**：
#    本檢查器是唯一一個從 host 直接 import `services.jgb.bills` 的稽核項，
#    它產生的 `__pycache__/bills.cpython-*.pyc` 會被**不變量 7** 的原始碼掃描
#    當成「直接讀 final_total」的違規（.pyc 內含原始字串）。
#    ⇒ 一條不變量不得因為另一條不變量的副產物而變紅。
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "rag-orchestrator"))

LATE_FEE_QUERIES = ("這筆帳單為什麼被收滯納金", "這筆延遲金怎麼算",
                    "我這筆為什麼有逾期費", "late fee 多少")
OTHER_QUERIES = ("這張帳單為什麼發不出去", "帳單取消不了", "手動到帳失敗")
#: `_DIAG_KEYWORDS` 必須維持的成員（⛔ 少一個都代表有人動了 generic discriminator）
REQUIRED_DIAG_KEYWORDS = ("發不出", "取消", "到帳", "收據", "虛擬帳號",
                          "逾期", "延遲金", "滯納金", "late fee")


def _row():
    return {"id": 901, "title": "2026年8月租金", "status": 2, "total": 25000,
            "date_expire": 20260805,
            "details": [{"active": True, "label": "租金", "total_price": 25000}]}


def violations():
    from services.jgb import bills as m                       # noqa: PLC0415
    bad = []
    excl = m.late_fee_exclusion_facts()
    for q in LATE_FEE_QUERIES:
        out = m.build_bill_diagnosis_facts(_row(), q)
        if out != excl:
            bad.append(f"late-fee intent「{q}」仍由 bill_diagnosis 作答"
                       f"（前 40 字：{out[:40]}）")
    for q in OTHER_QUERIES:
        row = dict(_row(), status=1, details=[]) if "發不出" in q else dict(_row(), status=64)
        if m.build_bill_diagnosis_facts(row, q) == excl:
            bad.append(f"⚠️ 誤傷：「{q}」被 late-fee 排除規則吸走")
    missing = [k for k in REQUIRED_DIAG_KEYWORDS if k not in m._DIAG_KEYWORDS]
    if missing:
        bad.append(f"`_DIAG_KEYWORDS` 被動過，缺 {missing}"
                   f"（它是 generic discriminator，⛔ 非 late-fee 宣告）")
    return bad


def self_test() -> int:
    from services.jgb import bills as m                       # noqa: PLC0415
    cases = [("現況乾淨", violations() == [])]
    # 正對照 1：關掉 intent 判定（等同恢復舊 dispatch）必須紅
    orig = m.is_late_fee_intent
    m.is_late_fee_intent = lambda q: False
    cases.append(("關掉 intent 判定必須紅", violations() != []))
    m.is_late_fee_intent = orig
    # 正對照 2：讓排除吸走其他診斷必須紅
    m.is_late_fee_intent = lambda q: True
    cases.append(("誤傷其他診斷必須紅", any("誤傷" in v for v in violations())))
    m.is_late_fee_intent = orig
    # 正對照 3：動 `_DIAG_KEYWORDS` 必須紅
    orig_kw = m._DIAG_KEYWORDS
    m._DIAG_KEYWORDS = tuple(k for k in orig_kw if k != "滯納金")
    cases.append(("動 _DIAG_KEYWORDS 必須紅",
                  any("_DIAG_KEYWORDS" in v for v in violations())))
    m._DIAG_KEYWORDS = orig_kw
    cases.append(("還原後乾淨", violations() == []))
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        bad = violations()
    except Exception as e:                                    # noqa: BLE001
        print(f"❌ FAIL：檢查無法執行（{e}）——大聲失敗，⛔ 不當成「沒有違規」")
        return 1
    if bad:
        print("❌ FAIL：late-fee ownership 違規：")
        for b in bad:
            print(f"   {b}")
        return 1
    print(f"（late-fee intent {len(LATE_FEE_QUERIES)} 種提法全部轉交唯一 owner；"
          f"其他 {len(OTHER_QUERIES)} 種診斷未受影響；`_DIAG_KEYWORDS` 未變）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
