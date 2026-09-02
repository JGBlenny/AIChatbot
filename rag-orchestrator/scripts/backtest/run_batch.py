#!/usr/bin/env python3
"""批次打正式入口（P0-1）——**療效只在 `POST /api/v1/message` 這一層成立**。

> 量測層級：`.claude/skills/retrieval-improvement-loop/rules/量測層級.md`
> 輸出契約：`.claude/skills/retrieval-improvement-loop/steps/03-回測輸出契約.md`

## 為什麼另寫一支

`scripts/backtest/backtest_framework_async.py:1304` 呼叫不存在的 `load_test_scenarios`，
`__main__` 一跑就炸（PLAN §5 工具地雷）；`decision_replay.py` 綁 corpus-20260810 逐字稿。
本支只做一件事：把一個「ts／q」批次逐題打正式入口，把 session_id 記下來，
後續 ①②③④ 由 `contract_enrich.py` 從 `usage_events` 併回——⛔ 不事後撈 log。

## ⛔ 紀律

```text
⛔ 不走元件層（retrieve_knowledge_hybrid 等）——那量到的是工具不是系統
⛔ 不自寫 SQL 當系統行為
⛔ 不並行——semantic-model 是 CPU 推論（實測延遲 >90s、CPU 600%+），
   併發會讓 reranker 逾時而靜默落到詞面分支，整輪數字作廢
⚠️ session_id 前綴決定 usage_events.is_internal（backtest_／loop_／kcl_／smoke_ 為內部）
   ⇒ 診斷輪用內部前綴，⛔ 不汙染真實流量統計
```

## 跑法

    python3 rag-orchestrator/scripts/backtest/run_batch.py \
        --batch .kiro/specs/conversational-routing-execution/b2b-e2e-run1.json \
        --prefix backtest_smoke0902_ --role-id 37305 --vendor-id 2 \
        --out /tmp/run.json
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("RUN_BATCH_API", "http://localhost:8100/api/v1/message")


def ask(question: str, session_id: str, *, vendor_id: int, role_id: str,
        mode: str, target_user: str, timeout: int = 180) -> dict:
    body = {
        "vendor_id": vendor_id, "mode": mode, "target_user": target_user,
        "role_id": role_id, "session_id": session_id,
        "user_id": session_id, "message": question,
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        status = resp.status
    except urllib.error.HTTPError as e:                  # ⚠️ 大聲失敗，⛔ 不靜默跳過
        return {"http": e.code, "error": e.read().decode("utf-8")[:300],
                "elapsed": round(time.time() - t0, 1)}
    except Exception as e:                               # noqa: BLE001
        return {"http": None, "error": f"{type(e).__name__}: {e}",
                "elapsed": round(time.time() - t0, 1)}
    return {
        "http": status,
        "elapsed": round(time.time() - t0, 1),
        "answer": data.get("answer"),
        "action_type": data.get("action_type"),
        "intent_type": data.get("intent_type"),
        "form_id": data.get("form_id"),
        "sources": [s.get("id") for s in (data.get("sources") or []) if isinstance(s, dict)],
        "confidence": data.get("confidence"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="批次打正式入口")
    ap.add_argument("--batch", required=True, help="含 ts／q 的 JSON 陣列")
    ap.add_argument("--prefix", required=True,
                    help="session_id 前綴（⚠️ backtest_／loop_／smoke_ 會被標成內部流量）")
    ap.add_argument("--vendor-id", type=int, required=True)
    ap.add_argument("--role-id", required=True)
    ap.add_argument("--mode", default="b2b")
    ap.add_argument("--target-user", default="property_manager")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    with open(args.batch, encoding="utf-8") as f:
        batch = json.load(f)
    if not batch:
        print(f"⛔ {args.batch} 是空的——這不是『沒有題目』，是檔案或路徑錯了")
        return 1

    results, t0 = [], time.time()
    for i, item in enumerate(batch, 1):
        ts, q = item.get("ts"), item.get("q", "")
        sid = f"{args.prefix}{ts}"
        r = ask(q, sid, vendor_id=args.vendor_id, role_id=args.role_id,
                mode=args.mode, target_user=args.target_user)
        r.update({"ts": ts, "q": q, "session_id": sid})
        results.append(r)
        flag = "✅" if r.get("http") == 200 else "⛔"
        print(f"{flag} [{i:2d}/{len(batch)}] ts{ts} {r['elapsed']:5.1f}s "
              f"{r.get('action_type') or r.get('error','')[:40]}", flush=True)

    payload = {
        "meta": {
            "batch": os.path.relpath(args.batch),
            "prefix": args.prefix, "mode": args.mode,
            "target_user": args.target_user, "vendor_id": args.vendor_id,
            "role_id": args.role_id, "rounds": 1,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)),
            "total_sec": round(time.time() - t0, 1),
        },
        "results": results,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    bad = [r for r in results if r.get("http") != 200]
    print(f"\n完成 {len(results)} 題／{payload['meta']['total_sec']}s → {args.out}")
    if bad:
        print(f"⛔ {len(bad)} 題非 200 ⇒ 本輪不完整，⛔ 不得當成完整批次")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
