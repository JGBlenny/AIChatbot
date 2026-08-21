#!/usr/bin/env python3
"""關卡報告的證據收錄閘門（任務 0.4｜D-22）。

`_run_meta.json` 原本沒有任何消費者——一份標了「本輪結論不具回歸效力」的輸出，
沒有機制阻止它被當成正式證據。本工具是那個消費者：關卡報告引用任何 run 目錄前，
先用它判定該目錄是否夠格。

用法：python3 check_evidence_grade.py <run_dir> [<run_dir> ...]
退出碼：0＝全部可收錄；1＝有目錄不具回歸效力（清單印出）。
"""
import json
import os
import sys


def grade(run_dir):
    meta_p = os.path.join(run_dir, "_run_meta.json")
    if not os.path.exists(meta_p):
        return "no_meta", ["缺 _run_meta.json（來歷不明，不得收錄）"]
    with open(meta_p, encoding="utf-8") as f:
        m = json.load(f)
    g = m.get("evidence_grade")
    if g is None:                       # 舊格式：由閘門欄位回推
        gates = m.get("gates") or {}
        reasons = []
        if not (gates.get("container") or {}).get("checked"):
            reasons.append("容器一致性未驗")
        if not (gates.get("external_anchor") or {}).get("verified"):
            reasons.append("完整性未經外部錨點驗證（該輪早於 D-21 修復）")
        return ("valid" if not reasons else "invalid_for_regression"), reasons
    return g, m.get("degraded_reasons") or []


def main(argv):
    if not argv:
        print(__doc__); return 2
    bad = 0
    for d in argv:
        g, reasons = grade(d)
        mark = "✅" if g == "valid" else "❌"
        print(f"{mark} {os.path.basename(d)}: {g}" + (f" — {'；'.join(reasons)}" if reasons else ""))
        if g != "valid":
            bad = 1
    print("\n" + ("🎉 全部可收錄為回歸證據" if not bad
                  else "💥 上列目錄不具回歸效力，關卡報告不得引用其數字"))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
