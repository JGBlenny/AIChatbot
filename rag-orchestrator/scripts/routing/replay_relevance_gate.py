#!/usr/bin/env python3
"""Q2 offline replay 第 3 步：**首次**執行 `_top1_relevance_gate` 的判定並與盲標對照。

⚠️ 逐字複用 production 的 `_GATE_SYSTEM_PROMPT` 與 user message 組法、同一 `chat_completion`、
   同一模型解析、`temperature=0`、`max_tokens=32`——任何一項自寫都會讓結論失真。

⚠️ **與 production 迴圈的差異（必須揭露）**：production gate 是**序列迴圈**
   （top1 判 YES 就停，不會判 top2）；本 replay **逐 pair 獨立判定**。
   本輪要量的是**分類器的鑑別力**，不是迴圈行為。
"""
import argparse, asyncio, json, os, sys
sys.path.insert(0, "/app"); sys.path.insert(0, "/app/services")

E = "/.kiro/specs/routing-authority-model/evidence/"


async def main(out):
    from routers.chat import _GATE_SYSTEM_PROMPT
    from services.llm_provider import chat_completion

    pairs = json.load(open(E + "q2-gate-pairs-frozen.json", encoding="utf-8"))
    labels = json.load(open(E + "q2-blind-labels.json", encoding="utf-8"))
    lab = {l["pair_id"]: l for l in labels["labels"]}
    model = (os.getenv("RELEVANCE_GATE_MODEL") or os.getenv("LLM_MODEL")
             or os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    rows = []
    for p in pairs["pairs"]:
        if p["gate_exempt"]:
            continue
        resp = await asyncio.to_thread(
            chat_completion, model=model,
            messages=[{"role": "system", "content": _GATE_SYSTEM_PROMPT},
                      {"role": "user",
                       "content": f"問題：{p['utterance']}\n知識標題：{p['kb_question_summary']}\n"
                                  f"知識內容（節錄）：{p['kb_answer_excerpt']}"}],
            temperature=0, max_tokens=32)
        raw = (resp.get("content") or "").strip()
        gate = "YES" if raw.upper().startswith("YES") else "NO"
        l = lab[p["pair_id"]]
        rows.append({"pair_id": p["pair_id"], "utterance": p["utterance"],
                     "kb": p["kb_question_summary"], "similarity": p["similarity"],
                     "human": l["judgement"], "human_reason": l["reason"],
                     "human_confidence": l["confidence"],
                     "gate": gate, "gate_raw": raw[:60],
                     "agree": (l["judgement"] == gate) if l["judgement"] != "UNDECIDABLE" else None})

    scored = [r for r in rows if r["agree"] is not None]
    tp = [r for r in scored if r["human"] == "YES" and r["gate"] == "YES"]
    tn = [r for r in scored if r["human"] == "NO" and r["gate"] == "NO"]
    fp = [r for r in scored if r["human"] == "NO" and r["gate"] == "YES"]
    fn = [r for r in scored if r["human"] == "YES" and r["gate"] == "NO"]
    out_obj = {
        "task": "Q2 offline replay — step 3: first gate execution",
        "frozen_inputs": {"pairs_digest": pairs["pairs_digest"],
                          "labels_digest": labels["labels_digest"]},
        "model": model,
        "replay_fidelity": {
            "prompt": "逐字複用 production `_GATE_SYSTEM_PROMPT`",
            "user_message": "與 production 同格式（問題／知識標題／知識內容節錄 answer[:180]）",
            "params": "temperature=0, max_tokens=32, 同一 chat_completion",
            "difference_from_production": ("production gate 為序列迴圈（top1 判 YES 即停）；"
                                           "本 replay 逐 pair 獨立判定——量分類器鑑別力，非迴圈行為"),
        },
        "evidence_limitation": labels["evidence_limitation"],
        "denominators": {"pairs_judged": len(rows), "scored": len(scored),
                         "excluded_undecidable": len(rows) - len(scored)},
        "confusion": {"true_positive": len(tp), "true_negative": len(tn),
                      "false_positive_let_through": len(fp), "false_negative_over_blocked": len(fn)},
        "agreement": f"{len(tp)+len(tn)}/{len(scored)}",
        "false_positives": fp, "false_negatives": fn, "rows": rows,
    }
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n")
    c = out_obj["confusion"]
    print(f"[gate replay] agreement {out_obj['agreement']}｜TP {c['true_positive']} "
          f"TN {c['true_negative']} FP(放行錯位) {c['false_positive_let_through']} "
          f"FN(誤殺) {c['false_negative_over_blocked']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="/app/gate_replay.json")
    asyncio.run(main(ap.parse_args().out))
