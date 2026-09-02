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
⛔ 不並行。⚠️ **原本寫的理由被實測推翻**（2026-09-03）：舊理由「semantic-model 併發會
   逾時（>90s、CPU 600%+）」——那組數字出自 2026-09-01 的**靜默永久停用事件**
   （建構期單次探測失敗），⛔ 不是併發實測。實測 `/rerank` 20 筆候選：
   併發 5 最壞 6.33s、併發 10 最壞 6.15s，而 RERANKER_HTTP_TIMEOUT 預設 **60s**。
   ⇒ 不並行的正確理由是**可重現性**：同 HEAD 重跑變異已達 13%，
     ⛔ 不該再加一個不可控變因
⚠️ session_id 前綴決定 usage_events.is_internal（backtest_／loop_／kcl_／smoke_ 為內部）
   ⇒ 診斷輪用內部前綴，⛔ 不汙染真實流量統計
⛔ 前綴**必須**以 `backtest_session_` 起頭——⚠️ 兩個豁免的前綴**不一樣**（見 _REQUIRED_PREFIX）
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

#: ⛔ session_id 必須以此起頭。⚠️ **兩個豁免用的前綴不一樣，這是血證**（2026-09-02）：
#:   `usage_metering.INTERNAL_RULES`    比對 `backtest_`        → 標成內部流量
#:   `chat._record_no_knowledge_scenario` 比對 `backtest_session_` → 不寫生產題庫
#: 首跑用了 `backtest_smoke0902_`：內部標記有生效，**題庫豁免沒有** ⇒
#: 那輪 11 題查無各把 `suggested_intents` 的頻率推高了一次（實測 id 1084／1399 被遞增）。
#: ⇒ 兩個都要吃到，只能用較長的那個當前綴。⛔ 不得為了好看而縮短。
_REQUIRED_PREFIX = "backtest_session_"


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
                    help=f"session_id 前綴，⛔ 必須以 {_REQUIRED_PREFIX} 起頭")
    ap.add_argument("--vendor-id", type=int, required=True)
    ap.add_argument("--role-id", required=True)
    ap.add_argument("--mode", default="b2b")
    ap.add_argument("--target-user", default="property_manager")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    # ⚠️ 大聲失敗，⛔ 不自動改寫前綴——改寫會讓報告裡的 session_id 與實際打出去的不符。
    if not args.prefix.startswith(_REQUIRED_PREFIX):
        print(f"⛔ --prefix 必須以 {_REQUIRED_PREFIX!r} 起頭，實得 {args.prefix!r}。\n"
              f"   理由：`_record_no_knowledge_scenario` 的回測豁免比對的是這個較長的前綴；"
              f"只用 'backtest_' 會被標成內部流量，但**仍會寫生產題庫與 suggested_intents**。")
        return 1

    with open(args.batch, encoding="utf-8") as f:
        batch = json.load(f)
    if not batch:
        print(f"⛔ {args.batch} 是空的——這不是『沒有題目』，是檔案或路徑錯了")
        return 1

    seen = {}
    for it in batch:
        seen.setdefault(it.get("q"), []).append(it.get("ts"))
    dupes = {q: t for q, t in seen.items() if len(t) > 1}
    if dupes:
        # ⚠️ 相異問句數 < 題數 ⇒ 任何比率的分母含重複，⛔ 引用比率時必須註明。
        print(f"⚠️ 批次含重複問句 {len(dupes)} 組：{[t for t in dupes.values()]}"
              f"　⇒ 題數 {len(batch)}、相異問句 {len(seen)}；⛔ 報比率時分母須註明")

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
