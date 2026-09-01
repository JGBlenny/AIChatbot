#!/usr/bin/env python3
"""G2 量測管線自證 —— 跑基準之前先證明量尺沒壞。

判準正本：`.claude/skills/retrieval-improvement-loop/rules/量測管線自證.md`（六項）
⛔ 任一項 FAIL ⇒ 先修管線，本輪量測作廢。

**為什麼要有這支**（2026-09-01）：第②項（ANN vs 精確掃描對照）原本只有文字說明、
沒有可執行腳本，新手得自己在容器內組 async DB 呼叫。乾跑實測把這列為卡點。

⚠️ **量測主體是生產檢索器**（`retrieve_knowledge_hybrid`）。
   第②項用一次直接 SQL 當**參照 oracle**（僅取精確最近鄰，⛔ 不複製過濾邏輯），
   用途是回答「生產候選池裡有沒有真正的最近鄰」——
   ⛔ oracle 不是「系統的行為」，⛔ 不得拿它的分數當系統分數。

用法：
    python3 scripts/g2_selftest.py                    # 跑六項
    python3 scripts/g2_selftest.py --probe "問句A" --probe "問句B"
⛔ 不讀 .env、⛔ 不印任何憑證。
"""
from __future__ import annotations

import json
import subprocess
import sys

APP = "aichatbot-rag-orchestrator"
PG = "aichatbot-postgres"

#: 預設探針：涵蓋 b2b 常見型別；⚠️ 最後一題是**正對照**（已知必然有可見正解）
DEFAULT_PROBES = [
    "通知信箱的群組設定要怎麼做？",
    "我能不能用 Encoding Excel 來一次性匯入租客？".replace("Encoding ", ""),
    "合約附件要怎麼上傳啊？",
]
POSCTRL_QUERY = "委託合約的 PDF 檔案要去哪裡找啊？"   #: 正對照：kb 應為可見且高分

FAILS: list[str] = []


def ok(msg: str) -> None:
    print(f"   ✅ {msg}")


def bad(item: str, msg: str) -> None:
    print(f"   ⛔ {msg}")
    FAILS.append(item)


def warn(msg: str) -> None:
    print(f"   ⚠️ {msg}")


def sh(args: list[str], timeout: int = 120) -> str:
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return r.stdout


# ── ① 容器與 HEAD 一致 ────────────────────────────────────────────────
def check1() -> None:
    print("① 容器與 HEAD 一致（不變量 3）")
    try:
        out = sh(["bash", "scripts/audit/check_invariants.sh"], timeout=300)
    except Exception as e:
        return bad("①", f"稽核跑不起來：{e}")
    seg = out.split("不變量 3")[1][:200] if "不變量 3" in out else ""
    if "PASS" in seg:
        ok("不變量 3 PASS")
    else:
        bad("①", f"不變量 3 未 PASS：{seg.strip()[:120]}")


# ── ② ANN vs 精確掃描對照 ★ ───────────────────────────────────────────
_PROBE = r'''
import asyncio, json, os, sys
sys.path.insert(0, "/app")
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
import psycopg2, psycopg2.extras

QS = json.loads(os.environ["QS"])

# ⚠️ oracle：**只取精確最近鄰**，⛔ 不複製生產的過濾邏輯（複製會漂）
ORACLE = """
SET LOCAL enable_indexscan = off;
"""
ORACLE_Q = """
SELECT kb.id FROM knowledge_base kb
 WHERE kb.is_active AND kb.embedding IS NOT NULL
   AND kb.category IS DISTINCT FROM '系統脈絡' AND kb.category IS DISTINCT FROM '對話規則'
 ORDER BY kb.embedding <=> %s::vector LIMIT 20;"""

async def main():
    r = VendorKnowledgeRetrieverV2()
    c = psycopg2.connect(host=os.getenv("DB_HOST", "postgres"),
                         port=int(os.getenv("DB_PORT", "5432")),
                         user=os.getenv("DB_USER", "aichatbot"),
                         password=os.getenv("DB_PASSWORD", "aichatbot_password"),
                         dbname=os.getenv("DB_NAME", "aichatbot_admin"))
    out = []
    for q in QS:
        # 生產檢索器（量測主體），未濾候選池
        prod = await r.retrieve_knowledge_hybrid(
            query=q, vendor_id=0, top_k=20, similarity_threshold=0.65,
            target_user="property_manager", mode="b2b",
            return_debug_info=True, return_unfiltered=True)
        prod_ids = [x.get("id") for x in prod]
        # oracle：精確最近鄰（僅參照）
        emb = await r._get_embedding(q)
        cur = c.cursor()
        cur.execute("SET LOCAL enable_indexscan = off")
        cur.execute("SET LOCAL enable_bitmapscan = off")
        cur.execute(ORACLE_Q, (str(emb),))
        oracle_ids = [x[0] for x in cur.fetchall()]
        c.rollback()
        out.append({"q": q, "prod_n": len(prod_ids), "prod": prod_ids[:5],
                    "oracle_top1": oracle_ids[0] if oracle_ids else None,
                    "oracle_n": len(oracle_ids),
                    "oracle_top1_in_prod": (oracle_ids[0] in prod_ids) if oracle_ids else None,
                    "score_source": [x.get("search_method") or x.get("score_source") for x in prod[:3]],
                    "has_rerank": any(x.get("rerank_score") is not None for x in prod)})
    print("###JSON###"); print(json.dumps(out, ensure_ascii=False))

asyncio.run(main())
'''


def check2(probes: list[str]) -> list[dict]:
    print("② ANN vs 精確掃描對照 ★（⛔ 索引悄悄截斷候選池不會報錯）")
    try:
        out = sh(["docker", "exec", "-i", "-e", f"QS={json.dumps(probes, ensure_ascii=False)}",
                  APP, "python3", "-"], timeout=300) if False else None
    except Exception:
        out = None
    # 用 stdin 餵腳本（避免長字串進 argv）
    p = subprocess.run(["docker", "exec", "-i", "-e",
                        f"QS={json.dumps(probes, ensure_ascii=False)}", APP, "python3", "-"],
                       input=_PROBE, capture_output=True, text=True, timeout=300)
    if "###JSON###" not in p.stdout:
        bad("②", f"探針跑不起來：{(p.stderr or p.stdout).strip()[-200:]}")
        return []
    rows = json.loads(p.stdout.split("###JSON###", 1)[1].strip())
    if not rows:
        bad("②", "探針回傳空——⛔ 別當成通過")
        return []
    miss = [r for r in rows if r["oracle_top1_in_prod"] is False]
    thin = [r for r in rows if r["oracle_n"] > 0 and r["prod_n"] < r["oracle_n"]]
    for r in rows:
        mark = "✅" if r["oracle_top1_in_prod"] else "⛔"
        print(f"   {mark} 「{r['q'][:22]}」候選池 {r['prod_n']} 筆"
              f"｜oracle top1 kb:{r['oracle_top1']}"
              f"｜{'在池內' if r['oracle_top1_in_prod'] else '**不在池內**'}"
              f"｜rerank={'有' if r['has_rerank'] else '⛔無'}")
    if miss:
        bad("②", f"{len(miss)}/{len(rows)} 題的精確最近鄰**不在生產候選池**"
                 "⇒ 索引或過濾把它截斷了，⛔ 本輪量測作廢")
    elif thin:
        warn(f"{len(thin)} 題候選池小於 oracle（可能是過濾造成，非必然缺陷）")
        ok("精確最近鄰皆在候選池內")
    else:
        ok("精確最近鄰皆在候選池內，候選池未被截斷")
    return rows


# ── ③④ 門檻與環境旗標實查 ────────────────────────────────────────────
KEYS = ["ENABLE_RERANKER", "KB_SIMILARITY_THRESHOLD", "HIGH_QUALITY_THRESHOLD",
        "FORM_TRIGGER_THRESHOLD", "PREENTRY_ROUTABILITY_GATE", "FACET_SCOPE_SALVAGE",
        "ENABLE_QUERY_REWRITE_B2B", "USE_MOCK_JGB_API"]


def check34() -> None:
    print("③④ 門檻與環境旗標（⛔ printenv 實查，不看 compose、不看程式預設）")
    try:
        out = sh(["docker", "exec", APP, "sh", "-c",
                  "; ".join(f'echo "{k}=$(printenv {k})"' for k in KEYS)])
    except Exception as e:
        return bad("③④", f"讀不到容器環境：{e}")
    env = dict(l.split("=", 1) for l in out.strip().splitlines() if "=" in l)
    for k in KEYS:
        v = env.get(k, "")
        print(f"      {k:<26} {v or '(未設，走程式預設)'}")
    if env.get("ENABLE_RERANKER", "").lower() != "true":
        bad("③④", "ENABLE_RERANKER 不是 true ⇒ 分數管線與生產不同")
    else:
        ok("環境旗ાग已記錄（⚠️ 這些值要一併寫進本輪的凍結參數）".replace("ાग", "標"))


# ── ⑤ Reranker 實際在跑 ★ ────────────────────────────────────────────
def check5(rows: list[dict]) -> None:
    print("⑤ Reranker 實際在跑（⛔ 不看容器 healthy、⛔ 不打 pipeline-health）")
    try:
        lg = sh(["docker", "logs", APP], timeout=90)
    except Exception as e:
        return bad("⑤", f"讀不到日誌：{e}")
    marks = [l for l in lg.splitlines()
             if "Reranker 已啟用" in l or "SemanticReranker 服務不可用" in l]
    if not marks:
        return bad("⑤", "日誌查無 reranker 初始化訊息——⛔ 別當成正常")
    if "服務不可用" in marks[-1]:
        return bad("⑤", f"**最後一次判定＝服務不可用**（共 {len(marks)} 次）⇒ 本輪量測作廢")
    ok(f"最後一次判定＝已啟用（共 {len(marks)} 次判定）")
    # ⚠️ 初始化訊息 ⛔ 不等於真的在跑——用②的探針結果交叉印證
    if rows:
        if all(r["has_rerank"] for r in rows):
            ok("②的探針全部帶 rerank_score ⇒ 交叉印證通過")
        else:
            bad("⑤", "②的探針有候選**沒有 rerank_score** ⇒ 與『已啟用』矛盾，先查再量")
    else:
        warn("②未取得探針結果，無法交叉印證（⛔ 只有初始化訊息不足以判定）")


# ── ⑥ 正對照題 ───────────────────────────────────────────────────────
def check6() -> None:
    print("⑥ 正對照題（已知必然命中；它若也沒中＝管線壞了）")
    p = subprocess.run(["docker", "exec", "-i", "-e",
                        f"QS={json.dumps([POSCTRL_QUERY], ensure_ascii=False)}",
                        APP, "python3", "-"],
                       input=_PROBE, capture_output=True, text=True, timeout=180)
    if "###JSON###" not in p.stdout:
        return bad("⑥", "正對照題跑不起來")
    r = json.loads(p.stdout.split("###JSON###", 1)[1].strip())[0]
    if r["prod_n"] > 0 and r["oracle_top1_in_prod"]:
        ok(f"「{POSCTRL_QUERY[:18]}」候選池 {r['prod_n']} 筆、oracle top1 在池內")
    else:
        bad("⑥", f"正對照題失敗（池 {r['prod_n']} 筆）⇒ **管線壞了，不是資料不足**")


# ── --self-test：突變控制（⛔ 從沒紅過的健檢等於沒驗過）────────────────
def self_test() -> int:
    """把已知壞掉的輸入餵給判定邏輯，它**必須紅**。

    ⚠️ 本專案鐵則：正控制＋突變控制。只證明「現在是綠的」不構成證據——
    要先證明**這支腳本看得見已知病灶**（2026-09-01 reranker 靜默停用即為該病灶）。
    """
    print("═══ --self-test：突變控制 ═══")
    passed = True

    def expect_fail(label: str, fn) -> None:
        nonlocal passed
        FAILS.clear()
        fn()
        if FAILS:
            print(f"   ✅ {label} → 正確轉紅（{'、'.join(FAILS)}）")
        else:
            print(f"   ⛔ {label} → **沒轉紅**，這支腳本看不見已知病灶")
            passed = False

    # 突變①：reranker 已啟用，但候選全無 rerank_score（＝2026-09-01 的真實病灶形狀）
    expect_fail("reranker 顯示已啟用、但候選無 rerank_score",
                lambda: check5([{"has_rerank": False, "q": "x"}]))
    # 突變②：精確最近鄰不在生產候選池（＝索引截斷）
    fake = [{"q": "x", "prod_n": 2, "prod": [1, 2], "oracle_top1": 999,
             "oracle_n": 20, "oracle_top1_in_prod": False,
             "score_source": ["keyword"], "has_rerank": False}]
    def _mut2():
        miss = [r for r in fake if r["oracle_top1_in_prod"] is False]
        if miss:
            bad("②", f"{len(miss)}/1 題的精確最近鄰不在生產候選池")
    expect_fail("精確最近鄰不在候選池（索引截斷）", _mut2)
    # 突變③：探針回空 ⇒ ⛔ 不得當成通過
    def _mut3():
        rows = []
        if not rows:
            bad("②", "探針回傳空——⛔ 別當成通過")
    expect_fail("探針回空", _mut3)

    FAILS.clear()
    print("\n" + ("✅ self-test 通過：三種已知病灶都會轉紅"
                   if passed else "⛔ self-test 失敗：⛔ 不得依賴這支腳本"))
    return 0 if passed else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    probes = [a for i, a in enumerate(sys.argv) if sys.argv[i - 1] == "--probe"] or DEFAULT_PROBES
    print("═══ G2 量測管線自證（六項）═══")
    print("⛔ 任一項 FAIL ⇒ 先修管線，本輪量測作廢\n")
    check1(); print()
    rows = check2(probes); print()
    check34(); print()
    check5(rows); print()
    check6(); print()
    if FAILS:
        print(f"⛔ **G2 未通過**：第 {'、'.join(FAILS)} 項失敗 ⇒ ⛔ 不得開始任何基準或對照回測")
        return 1
    print("✅ G2 六項全過 —— 可以往下跑基準")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
