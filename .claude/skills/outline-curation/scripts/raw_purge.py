#!/usr/bin/env python3
"""`raw/` 保存期限清理（knowledge-outline-and-intent-architecture 任務 2.2｜design D3）。

D3：真流量原句只落 `raw/`（gitignored）並 **90 天後刪**。本腳本依**檔名裡的日期**判定，
⛔ 不看 mtime（mtime 會被 checkout／rsync／備份還原重置，不能當保存期限的依據）。

判定：`raw/` 下的檔案／目錄，名稱含 `YYYYMMDD` 或 `YYYY-MM-DD` 且該日期早於 `--today` 減 `--days`
⇒ 列為待刪；**名稱裡沒有可解析日期的一律不動**（⛔ 不猜、⛔ 不遞迴刪整個 raw/）。
目錄命中即整棵刪除、不再往下走；沒命中的目錄才往下遞迴。

預設乾跑（只列出）；`--apply` 才真的刪。⛔ 無 `datetime.now()`——今天由 `--today` 傳入。
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys

DATE_COMPACT_RE = re.compile(r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)')
DATE_DASHED_RE = re.compile(r'(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)')
DEFAULT_DAYS = 90


def parse_date_in_name(name: str):
    """名稱中第一個可解析的日期（先試 `YYYY-MM-DD`，再試 `YYYYMMDD`）；沒有則回 None。"""
    for rx in (DATE_DASHED_RE, DATE_COMPACT_RE):
        for m in rx.finditer(name):
            try:
                return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def plan(raw_dir: str, today: "datetime.date", days: int = DEFAULT_DAYS):
    """回 (待刪清單, 保留清單)；每項＝(路徑, 日期或 None, 原因)。"""
    cutoff = today - datetime.timedelta(days=days)
    doomed = []
    kept = []

    def walk(d: str):
        for name in sorted(os.listdir(d)):
            path = os.path.join(d, name)
            dt = parse_date_in_name(name)
            if dt is None:
                kept.append((path, None, "名稱無可解析日期 ⇒ ⛔ 不動"))
                if os.path.isdir(path) and not os.path.islink(path):
                    walk(path)
                continue
            if dt < cutoff:
                doomed.append((path, dt, f"{dt.isoformat()} 早於保存期限 {cutoff.isoformat()}"))
                continue                     # 命中的目錄整棵刪，⛔ 不再往下走
            kept.append((path, dt, f"{dt.isoformat()} 仍在 {days} 天保存期限內"))
            if os.path.isdir(path) and not os.path.islink(path):
                walk(path)

    if os.path.isdir(raw_dir):
        walk(raw_dir)
    return doomed, kept


def apply_plan(doomed) -> int:
    n = 0
    for path, _, _ in doomed:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        elif os.path.exists(path) or os.path.islink(path):
            os.remove(path)
        else:
            continue
        n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raw-dir", required=True, help=".claude/skills/outline-curation/raw/")
    p.add_argument("--today", required=True, help="YYYY-MM-DD，⛔ 不用 datetime.now()")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"保存天數，預設 {DEFAULT_DAYS}")
    p.add_argument("--apply", action="store_true", help="真的刪除（預設只乾跑列出）")
    a = p.parse_args()

    y, m, d = (int(x) for x in a.today.split("-"))
    today = datetime.date(y, m, d)
    doomed, kept = plan(a.raw_dir, today, a.days)

    verb = "已刪除" if a.apply else "將刪除（乾跑）"
    for path, dt, why in doomed:
        print(f"{verb}：{path}｜{why}")
    for path, dt, why in kept:
        if dt is not None:
            print(f"保留：{path}｜{why}")
    no_date = sum(1 for _, dt, _ in kept if dt is None)
    n = apply_plan(doomed) if a.apply else 0
    print(f"raw-purge：待刪 {len(doomed)}｜{'實刪 ' + str(n) if a.apply else '乾跑（加 --apply 才刪）'}"
          f"｜保留（在期限內）{sum(1 for _, dt, _ in kept if dt is not None)}｜無日期不動 {no_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
