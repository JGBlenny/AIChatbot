#!/usr/bin/env python3
"""回合軌跡 CLI（spec agentic-mcp-orchestration・任務 2.7）。

把 `usage_events.decision_snapshot.agent` 印成回合敘事：訊息類型 → 工具序列
（名稱、face、有無 ref／keyword、筆數、狀態、耗時）→ Verifier 每次判定與拒因
→ 最終 kind／轉人原因／是否重播。渲染邏輯與 HTTP 端點**共用**
`services/agent/trace_view.py`，⛔ 不在這裡另寫一份遮罩。

用法：
  python3 rag-orchestrator/tools/agent_trace.py <trace_id> --vendor 1
  python3 rag-orchestrator/tools/agent_trace.py --session <session_id> --vendor 1 --days 3
  ... --json          # 機器可讀（同一份 view，不是另一種投影）

退出碼：0 找到；2 查無（時間窗內、該業者範圍內找不到）；1 參數／連線錯誤。

## 憑證與越權
- **憑證只走 `services/db_utils.get_db_config()`**（讀 `DB_HOST`／`DB_USER`／
  `DB_PASSWORD`… 環境變數）。⛔ 不接受任何密碼類參數：`argv` 會進 `ps`、
  shell history 與這支腳本的呼叫紀錄，明文金鑰不該落在那裡。
- **`--vendor` 必填**——這支工具是直連 DB 的，沒有 API key 的 `vendor_ids` 幫忙
  收範圍，所以由呼叫者明講要看哪個業者，查詢一律帶 `vendor_id = %s`。⛔ 沒有
  「全業者」模式：真要跨業者比對就跑兩次，讓每一次都在紀錄上寫明看了誰。
- 查詢帶時間窗（`--days`，預設 `AGENT_TRACE_WINDOW_DAYS` 或 7）＋`LIMIT`：
  `decision_snapshot->'agent'->>'trace_id'` 沒有索引，無窗查詢是全表掃。

⚠️ 時間欄是 `usage_events.ts`，本表**沒有** `created_at`
（`database/migrations/add_usage_events.sql`）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agent import trace_view  # noqa: E402
from services.db_utils import get_db_config  # noqa: E402

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2

_SELECT = "SELECT ts, session_id, vendor_id, decision_snapshot FROM usage_events"

_BY_ID_SQL = (
    f"{_SELECT}"
    " WHERE decision_snapshot->'agent'->>'trace_id' = %s"
    "   AND vendor_id = %s"
    "   AND ts > now() - (%s || ' days')::interval"
    " LIMIT 1"
)

_BY_SESSION_SQL = (
    f"{_SELECT}"
    " WHERE session_id = %s"
    "   AND vendor_id = %s"
    "   AND decision_snapshot->'agent'->>'trace_id' IS NOT NULL"
    "   AND ts > now() - (%s || ' days')::interval"
    " ORDER BY ts ASC"
    f" LIMIT {trace_view.SESSION_TIMELINE_LIMIT}"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_trace.py",
        description="讀 usage_events.decision_snapshot.agent，印回合軌跡（⛔ 無原文）",
    )
    parser.add_argument("trace_id", nargs="?", help="要看的 trace_id（與 --session 二選一）")
    parser.add_argument("--session", dest="session_id", help="改看整段 session 的時間軸")
    parser.add_argument(
        "--vendor", dest="vendor_id", type=int, required=True,
        help="業者 id（必填：直連 DB 沒有 key 範圍可依，範圍由呼叫者明講）",
    )
    parser.add_argument(
        "--days", dest="days", type=int, default=None,
        help=f"時間窗天數（預設讀 {trace_view.TRACE_WINDOW_ENV}，再預設 {trace_view.DEFAULT_WINDOW_DAYS}）",
    )
    parser.add_argument("--json", action="store_true", help="輸出 JSON（同一份 view）")
    return parser


def fetch_rows(sql: str, params: tuple) -> list:
    """唯讀查詢。憑證來自 `get_db_config()`，⛔ 不從 argv 取。"""
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(**get_db_config())
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
    finally:
        conn.close()


def main(argv: "list[str] | None" = None) -> int:
    args = build_parser().parse_args(argv)

    if bool(args.trace_id) == bool(args.session_id):
        print("用法錯誤：<trace_id> 與 --session 恰好擇一", file=sys.stderr)
        return EXIT_USAGE

    days = args.days if args.days and args.days > 0 else trace_view.window_days()

    if args.trace_id:
        sql, params = _BY_ID_SQL, (args.trace_id, args.vendor_id, str(days))
        target = f"trace_id={args.trace_id}"
    else:
        sql, params = _BY_SESSION_SQL, (args.session_id, args.vendor_id, str(days))
        target = f"session={trace_view.mask_session(args.session_id)}"

    try:
        rows = fetch_rows(sql, params)
    except Exception as e:  # noqa: BLE001
        print(f"DB 連線／查詢失敗（{type(e).__name__}）：{e}", file=sys.stderr)
        return EXIT_USAGE

    if not rows:
        print(
            f"查無軌跡：{target}　vendor={args.vendor_id}　最近 {days} 天內。\n"
            "（可能原因：trace 不在這個業者名下、超出時間窗、或這回合沒落 decision_snapshot.agent）",
            file=sys.stderr,
        )
        return EXIT_NOT_FOUND

    views = [trace_view.render_trace(r) for r in rows]

    if args.json:
        print(json.dumps(views if args.session_id else views[0], ensure_ascii=False, indent=2))
        return EXIT_OK

    print(f"■ {target}　vendor={args.vendor_id}　窗={days} 天　共 {len(views)} 回合")
    for i, view in enumerate(views, 1):
        print(f"\n── 回合 {i}/{len(views)} " + "─" * 40)
        print(trace_view.render_text(view))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
