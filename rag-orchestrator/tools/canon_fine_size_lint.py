"""正本細目大小 lint（spec knowledge-outline-and-intent-architecture・DSP-059a）。

用途：K 上界從 2,500 拉高到 12,000（DSP-059a）之後，「單條細目多大」失去了原本
2,500 這道天然警戒線。這支工具把每條細目的 token 數印出來，>阈值 的標成 WARN，
提醒審核時把過長的細目拆回「一細目一命題」（鐵則見 `canon/jgb/README.md`）。

⛔ 不是 gate：exit code 恆為 0，不擋任何流程、不接 CI 失敗。單純給人看的建議清單。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.agent.canon.canon_assembler import _axes_visible, load_canon_or_die
from services.agent.outline import _count_tokens

DEFAULT_CANON_DIR = "/app/canon"
DEFAULT_THRESHOLD = 1500

#: 跟 `check_turn_budget` 同款靜態身分（審核用途，⛔ 不含 vendor 業態過濾）：
#: b2b 模式、業態 frozenset()（正本細目無 vendor 欄，見 canon_assembler 模組 docstring）。
_AUDIENCES = ("prospect", "property_manager")


def _fine_tokens(fine) -> int:
    text = f"【{fine.id}】{fine.title}\n" + "\n".join(fine.content_units)
    tokens, _approx = _count_tokens(text)
    return tokens


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canon-dir", default=DEFAULT_CANON_DIR)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    doc = load_canon_or_die(args.canon_dir)
    fines = doc.fines()

    rows = [(fid, title, tok) for fid, title, tok in (
        (fine.id, fine.title, _fine_tokens(fine)) for fine in fines
    )]
    over = sorted((r for r in rows if r[2] > args.threshold), key=lambda r: r[2], reverse=True)
    for fid, title, tok in over:
        print(f"WARN {tok} {fid} {title}")

    print(f"{len(over)}/{len(rows)} fines over {args.threshold} tokens")

    for audience in _AUDIENCES:
        visible = [
            _fine_tokens(fine)
            for fine in fines
            if _axes_visible(audience, "b2b", fine, frozenset())
        ]
        top5_sum = sum(sorted(visible, reverse=True)[:5])
        print(f"top-5 sum ({audience}): {top5_sum}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
