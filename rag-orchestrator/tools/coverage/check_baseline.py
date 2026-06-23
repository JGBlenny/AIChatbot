#!/usr/bin/env python3
"""覆蓋率 ratchet 守門（spec testing-traceability 元件 4・R3.3/3.4）。

CI 端「只讀比對、不寫回」：實測 < 基準 → 非 0 退出（擋合併）；實測 ≥ 基準 → 0。
升基準由人工：覆蓋率提升後，開發者本地重量測、手動更新 coverage-baseline.json 並 commit。

用法：
  python3 tools/coverage/check_baseline.py \
    [--coverage tests/.coverage.json] [--baseline tests/coverage-baseline.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # rag-orchestrator/


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _module_pct(cov: dict, module: str) -> float | None:
    """從 pytest-cov JSON 取某模組的覆蓋率（fraction 0–1）。"""
    files = cov.get("files", {})
    for key, val in files.items():
        norm = key.replace("\\", "/")
        if norm == module or norm.endswith("/" + module):
            return val["summary"]["percent_covered"] / 100.0
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", default=str(_ROOT / "tests/.coverage.json"))
    ap.add_argument("--baseline", default=str(_ROOT / "tests/coverage-baseline.json"))
    # 浮點/取整容差：實測略低於基準但在容差內不算倒退
    ap.add_argument("--tolerance", type=float, default=0.005)
    args = ap.parse_args(argv)

    cov_path = Path(args.coverage)
    base_path = Path(args.baseline)
    if not cov_path.exists():
        print(f"❌ 找不到覆蓋率報告：{cov_path}（請先以 --cov 跑測試）", file=sys.stderr)
        return 2
    if not base_path.exists():
        print(f"❌ 找不到基準：{base_path}", file=sys.stderr)
        return 2

    cov = _load(cov_path)
    base = _load(base_path)
    tol = args.tolerance

    failures = []
    rows = []

    actual_overall = cov["totals"]["percent_covered"] / 100.0
    base_overall = float(base.get("overall", 0.0))
    ok = actual_overall >= base_overall - tol
    rows.append(("overall", base_overall, actual_overall, ok))
    if not ok:
        failures.append(f"overall {actual_overall:.2%} < 基準 {base_overall:.2%}")

    for module, base_pct in base.get("modules", {}).items():
        actual = _module_pct(cov, module)
        if actual is None:
            rows.append((module, float(base_pct), None, False))
            failures.append(f"{module}：覆蓋率報告中找不到此模組")
            continue
        ok = actual >= float(base_pct) - tol
        rows.append((module, float(base_pct), actual, ok))
        if not ok:
            failures.append(f"{module} {actual:.2%} < 基準 {float(base_pct):.2%}")

    width = max(len(r[0]) for r in rows)
    print(f"{'module'.ljust(width)}  {'baseline':>9}  {'actual':>9}  status")
    for name, b, a, ok in rows:
        a_s = "—" if a is None else f"{a:.2%}"
        print(f"{name.ljust(width)}  {b:>8.2%}  {a_s:>9}  {'✅' if ok else '❌'}")

    if failures:
        print("\n❌ 覆蓋率倒退（ratchet 違反）：", file=sys.stderr)
        for f in failures:
            print(f"   - {f}", file=sys.stderr)
        print("\n提示：若為刻意調整，請人工重量測並更新 coverage-baseline.json 後再 commit。",
              file=sys.stderr)
        return 1

    print("\n✅ 覆蓋率未倒退（≥ 基準）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
