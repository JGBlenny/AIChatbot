#!/usr/bin/env python3
"""protocol v1 驗收 runner（spec routing-disambiguation 任務 5.1／5.3｜R6.1, R3.1）。

驅動 **production seam**（`routers.chat._diagnosis_config_for_knowledge`），
以凍結量尺 `scripts.routing.protocol_v1` 評分。**不得在本檔重演 routing 語義。**

⚠️ **synthetic authorization 的邊界**——本檔只替換「授權前提」，其餘全走 production：

```text
允許：注入 synthetic matching-PASS manifest，讓 production authorization check 通過
      （＝假設 Task 6 最終給了合法 PASS，現在這個 candidate 本身過不過得了凍結驗收）
禁止：mock gate verdict／mock suppression 結果／直接把 route 改成預期答案／
      改動 current_manifest() 的真實 not_run／把 synthetic PASS 寫回正式 manifest
```

> **Candidate technical acceptance under synthetic authorization
> ≠ Candidate authorized for release.**

⚠️ 分母：**20 筆有驗收角色**（RULE 4＋INSTANCE 4＋CONTROL 5＋BLAST 7）
＋ **2 筆只觀察**（UNDECIDED，不進 bilateral／pass 分母）。

用法（容器內）：
    python3 scripts/routing/run_protocol_v1.py --label baseline > out.json
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/services")

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
PRODUCTION_TOP_K = 5
TARGET_USER = "property_manager"
MODE = "b2b"
SCORED_SETS = ("RULE", "INSTANCE", "CONTROL", "BLAST")
OBSERVED_ONLY = ("UNDECIDED",)


def _conn_kwargs():
    return dict(host=os.getenv("DB_HOST", "postgres"), port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"))


def authorize(*, corrupt_digit=False):
    """注入 synthetic matching-PASS；`corrupt_digit=True` 則刻意讓 ruleset digest 差一位。

    ⚠️ corrupt 版是 **Task 5 自己的 negative control**：證明本 harness 真的經過
    production authorization seam，而不是 fixture 直接把 gate 打開。
    """
    from services import instance_reference_gate as m
    base = m.current_manifest()
    rs = base.digest
    if corrupt_digit:
        last = rs[-1]
        rs = rs[:-1] + ("0" if last != "0" else "1")
    m.current_manifest = lambda: m.RulesetManifest(
        version=base.version, positive_patterns=dict(base.positive_patterns),
        counter_patterns=dict(base.counter_patterns), digest=base.digest,
        holdout=m.HoldoutRecord(status="passed", ruleset_digest=rs,
                                protocol_digest=m.ACTIVE_PROTOCOL_DIGEST,
                                dataset_id="synthetic-task5", dataset_digest="ds-synthetic"))
    return m


async def observe(pool, retriever, question):
    """回一筆觀測：route／facet／decision_margin／gate verdict。"""
    from routers.chat import _diagnosis_config_for_knowledge
    from services.decision_layer import DecisionConfig
    from services.instance_evidence import InstanceEvidenceExtractor
    from services.instance_reference_gate import instance_reference_gate

    cfg_thresholds = DecisionConfig.load()
    rows = await retriever.retrieve_knowledge_hybrid(
        query=question, vendor_id=VENDOR_ID, top_k=PRODUCTION_TOP_K,
        similarity_threshold=cfg_thresholds.kb_threshold, target_user=TARGET_USER, mode=MODE)
    best = rows[0] if rows else None
    # decision_margin：**只記錄**（R3.1／3.4）——用於證明判別不靠邊際，不設門檻
    margin = None
    if len(rows) >= 2:
        margin = round(float(rows[0].get("similarity", 0)) - float(rows[1].get("similarity", 0)), 4)

    decision = instance_reference_gate(InstanceEvidenceExtractor().extract(question),
                                       face_requires_instance=True)
    if best is None:
        return {"kind": "single", "facet": None, "top1": None, "decision_margin": margin,
                "gate_verdict": decision.verdict, "gate_reason": decision.reason}
    cfg = await _diagnosis_config_for_knowledge(pool, best, cfg_thresholds, user_message=question)
    facet = None if cfg is None else ((getattr(cfg, "topic_scope", None) or {}).get("category")
                                      or getattr(cfg, "key", "?"))
    return {"kind": "single" if cfg is None else "dialog", "facet": facet,
            "top1": (best.get("question_summary") or "")[:40],
            "top1_similarity": round(float(best.get("similarity", 0)), 4),
            "decision_margin": margin,
            "gate_verdict": decision.verdict, "gate_reason": decision.reason}


async def main(label):
    import asyncpg
    from scripts.routing import protocol_v1 as ruler
    from services import conversational_config as cc
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    protocol = ruler.load_protocol()
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cc.reset_cache()
    retriever = VendorKnowledgeRetrieverV2()

    os.environ["INSTANCE_REFERENCE_GATE"] = "true"
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "false"

    # ── negative control：digest 差一位 → 必須完全不 active ──
    m = authorize(corrupt_digit=True)
    nc = {"gate_active_with_corrupt_digest": m.gate_active()}
    nc_routes = {q: (await observe(pool, retriever, q))["kind"]
                 for q in protocol["case_sets"]["RULE"]["cases"]}
    nc["rule_routes_when_unauthorized"] = nc_routes

    # ── 正式量測：synthetic matching PASS ──
    m = authorize()
    assert m.gate_active() is True, "synthetic 授權未生效——量測無意義"

    results, observed = [], []
    for name in SCORED_SETS:
        for q in protocol["case_sets"][name]["cases"]:
            row = await observe(pool, retriever, q)
            results.append({"case_set": name, "question": q, **row})
    for name in OBSERVED_ONLY:
        for q in protocol["case_sets"][name]["cases"]:
            observed.append({"case_set": name, "question": q,
                             **(await observe(pool, retriever, q))})

    scored = ruler.score_run([{**r, "kind": r["kind"], "facet": r["facet"]} for r in results
                              if r["case_set"] in ("RULE", "INSTANCE")])
    bilateral = ruler.bilateral_pass([{**r} for r in results if r["case_set"] in ("RULE", "INSTANCE")])
    control = [r for r in results if r["case_set"] == "CONTROL"]

    out = {
        "label": label,
        "protocol_version": protocol["protocol_version"],
        "protocol_digest": protocol["protocol_digest"],
        "ruleset_digest": m.current_manifest().digest,
        "ruleset_version": m.current_manifest().version,
        "authorization": {
            "mode": "synthetic matching PASS",
            "production_manifest_status": "not_run",
            "disclaimer": ("Candidate technical acceptance under synthetic authorization "
                           "!= Candidate authorized for release"),
        },
        "negative_control": nc,
        "denominator": {"scored": len(results), "observed_only": len(observed),
                        "bilateral": "RULE 4 + INSTANCE 4 = 8"},
        "bilateral_pass": bilateral,
        "scored_verdicts": scored,
        "control_group": control,
        "blast_group": [r for r in results if r["case_set"] == "BLAST"],
        "observed_only": observed,
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if OUT_PATH:
        # ⚠️ 寫檔而非 stdout：production 模組在 import 期就會印初始化訊息，
        #    混進 stdout 會讓輸出不是合法 JSON（已踩過）。
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        print(f"[protocol-v1] 已寫出 {OUT_PATH}")
    else:
        print(payload)
    await pool.close()


OUT_PATH = None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="baseline")
    ap.add_argument("--out", default=None, help="輸出 JSON 路徑（不給則印到 stdout）")
    args = ap.parse_args()
    OUT_PATH = args.out
    asyncio.run(main(args.label))
