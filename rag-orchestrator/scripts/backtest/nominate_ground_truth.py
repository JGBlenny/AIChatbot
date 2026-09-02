#!/usr/bin/env python3
"""正解候選提名（契約 §A｜P0-2）——**我機械抽候選，業主逐題勾**。

> 契約正本：`.claude/skills/retrieval-improvement-loop/steps/03-回測輸出契約.md` §A
> 量測層級：`.claude/skills/retrieval-improvement-loop/rules/量測層級.md`

## 三條紀律（每一條都有血證）

```text
⛔ 候選 **不得**用被驗系統自己的排序
   理由：正解若由被驗方提名，量測就是自我實現。
   ⇒ 本支用**精確最近鄰**（enable_indexscan/bitmapscan 關掉）當獨立 oracle，
     ⛔ 不呼叫 retrieve_knowledge_hybrid、⛔ 不套 reranker、⛔ 不套加成。

⛔ 候選 **不得**先套可見性過濾
   理由：正解「存在但這角色看不到」正是 V 類。先濾掉，V 類就從構造上消失了。
   ⇒ 全母體撈，可見性只**標記**不排除（標記由 contract_enrich.visibility 算）。

⛔ 提名 **不是**裁定
   輸出是待勾選清單；業主勾完才由 --emit-frozen 落成凍結檔。
   ⛔ 本支不得自行寫出任何 expected_kb_id 值。
```

## 母體

`scripts/status.py` 的**適格母體**同一式（⛔ 不各自定義）：
active、扣掉設定列（系統脈絡／對話規則）、扣掉 id 4253、扣掉空 answer 錨點。
⚠️ 空 answer 錨點不可能是正解（沒有答案本體），故排除；
若某題的真正歸屬是錨點，正確做法是勾 `NO_COVERAGE` 並在 why 註明。

## 跑法

    python3 rag-orchestrator/scripts/backtest/nominate_ground_truth.py --self-test
    python3 ... --batch .kiro/specs/conversational-routing-execution/b2b-e2e-run1.json \
                --out /tmp/b2b-ground-truth-review.md

⚠️ `--self-test` 先跑：拿已知知識列的 question_summary 當查詢，該列必須是精確最近鄰 top-1。
⛔ 這個對照不過 ⇒ embedding 或掃描壞了，任何候選清單都不可用。
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

PG_CONTAINER = os.environ.get("NOMINATE_PG", "aichatbot-postgres")
PG_USER = "aichatbot"
PG_DB = "aichatbot_admin"
EMBED_API = os.environ.get("EMBEDDING_API_URL", "http://localhost:5001/api/v1/embeddings")

#: ⛔ 與 `scripts/status.py` 的 ELIGIBLE 同一式——改一處要同步。
ELIGIBLE = ("is_active AND COALESCE(category,'') NOT IN ('系統脈絡','對話規則') "
            "AND id <> 4253 AND answer IS NOT NULL AND btrim(answer) <> ''")

TOP_N = 8

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contract_enrich import fetch_kb_rows, visibility  # noqa: E402


class OracleError(RuntimeError):
    """oracle 自身壞了——⚠️ 大聲失敗，⛔ 不得降級續跑產出清單。"""


def psql(sql: str) -> str:
    r = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-tAc", sql],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode:
        raise OracleError(f"psql 失敗：{r.stderr.strip()}")
    return r.stdout.strip()


def embed(text: str) -> list:
    """呼叫 embedding 服務。⛔ 不從 .env 讀任何憑證、⛔ 不把內容放進 argv。"""
    req = urllib.request.Request(
        EMBED_API,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        vec = json.loads(resp.read().decode("utf-8")).get("embedding")
    if not vec:
        raise OracleError(f"embedding 服務沒有回向量：{text[:30]}…")
    return vec


def exact_neighbours(vec: list, limit: int = TOP_N) -> list:
    """精確最近鄰——**獨立 oracle**。

    ⚠️ `SET LOCAL enable_indexscan/bitmapscan = off` 是重點：
    ANN 近似會漏掉正解（2026-09-01 實測 top-20 候選池召回率僅 31%），
    用它提名等於把索引缺陷寫進 ground truth。
    ⚠️ 這裡刻意用**正規寫法** `ORDER BY embedding <=> v`（距離升冪），
    ⛔ 不模仿生產的 `(1 - dist) DESC`——本支量的不是系統行為，是語義最近鄰。
    """
    v = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
    sql = (
        "BEGIN; SET LOCAL enable_indexscan = off; SET LOCAL enable_bitmapscan = off; "
        "SELECT coalesce(json_agg(row_to_json(t) ORDER BY t.dist),'[]'::json) FROM ("
        "  SELECT id, question_summary, category, categories, "
        # ⚠️ 帶內容摘要：判「庫裡有沒有這題的答案」必須看 answer，
        #    光看標題會誤判（標題是短關鍵字，⛔ 不是答案本體）
        "        left(regexp_replace(answer, E'\\\\s+', ' ', 'g'), 150) AS answer_head, "
        f"        (embedding <=> '{v}'::vector) AS dist "
        f"  FROM knowledge_base WHERE {ELIGIBLE} AND embedding IS NOT NULL "
        f"  ORDER BY embedding <=> '{v}'::vector LIMIT {limit}"
        ") t; COMMIT;"
    )
    out = psql(sql)
    # psql 會把 BEGIN/SET/COMMIT 的回應一起印出，取唯一那行 JSON
    line = next((l for l in out.splitlines() if l.startswith("[")), None)
    if line is None:
        raise OracleError(f"精確掃描沒有回 JSON：{out[:200]}")
    return json.loads(line)


def self_test() -> int:
    """⛔ 先證明 oracle 沒壞，再拿它提名。

    做法：抽三筆真實知識，各拿自己的 `question_summary` 當查詢，
    該筆必須是精確最近鄰 **top-1**。抓不到 ⇒ embedding 模型不一致或掃描壞了。
    """
    rows = json.loads(psql(
        "select coalesce(json_agg(row_to_json(t)),'[]'::json) from ("
        f"  select id, question_summary from knowledge_base where {ELIGIBLE} "
        "   and embedding is not null and btrim(coalesce(question_summary,'')) <> '' "
        "   order by id limit 3"
        ") t"
    ))
    if len(rows) < 3:
        print("⛔ 抽不到三筆有 question_summary 的知識——⛔ 母體或查詢壞了")
        return 1

    ok = True
    for r in rows:
        cands = exact_neighbours(embed(r["question_summary"]), limit=3)
        top1 = cands[0]["id"] if cands else None
        hit = top1 == r["id"]
        print(f"{'✅' if hit else '⛔'} kb:{r['id']} 自我檢索 top-1={top1}"
              f"（dist={cands[0]['dist']:.4f}）" if cands else f"⛔ kb:{r['id']} 無候選")
        ok = ok and hit

    # 負對照：亂碼查詢的 top-1 距離必須明顯大於自我檢索（否則等於什麼都相似）
    noise = exact_neighbours(embed("zzqq xxyy 無意義字串 9f3k2"), limit=1)
    print(f"ℹ️  負對照：亂碼查詢 top-1 dist={noise[0]['dist']:.4f}"
          f"（自我檢索應遠小於此）" if noise else "⛔ 負對照無候選")
    if noise and noise[0]["dist"] < 0.2:
        print("⛔ 亂碼查詢也高度相似 ⇒ 向量空間或模型不對，oracle 不可用")
        ok = False

    print("\n結論：", "oracle 可用" if ok else "⛔ oracle 壞了，候選清單一律作廢")
    return 0 if ok else 1


def build_sheet(batch_path: str, out_path: str) -> int:
    with open(batch_path, encoding="utf-8") as f:
        batch = json.load(f)
    if not batch:
        raise OracleError(f"{batch_path} 是空的——⛔ 這不是『沒有題目』，是檔案或路徑錯了")

    lines = [
        "# b2b 正解候選（待業主逐題勾選）",
        "",
        f"> 來源批次：`{os.path.relpath(batch_path)}`｜共 {len(batch)} 題",
        "> 候選由**精確最近鄰**提名（獨立 oracle），"
        "⛔ 非被驗系統的排序、⛔ 未套可見性過濾、⛔ 未經 reranker。",
        "> ⚠️ 標 `b2b看不到` 的列**仍可能是正解**——那正是 V 類（改資料歸屬，不是寫新知識）。",
        "",
        "## 怎麼勾",
        "",
        "```text",
        "每題勾一個或多個 [x]；庫裡真的沒有 ⇒ 勾 NO_COVERAGE（合法且有價值）",
        "需要組合多筆才算完整回答 ⇒ 全部勾起來",
        "勾完把本檔交回，我落成 frozen.json 並 commit",
        "```",
        "",
    ]

    for i, item in enumerate(batch, 1):
        ts, q = item.get("ts"), item.get("q", "")
        cands = exact_neighbours(embed(q))
        kb_rows = fetch_kb_rows([c["id"] for c in cands])
        lines.append(f"## {i}. ts{ts}")
        lines.append("")
        lines.append(f"**{q}**")
        lines.append("")
        for c in cands:
            kb = kb_rows.get(c["id"])
            vis = visibility(kb, mode="b2b", target_user="property_manager",
                             vendor_id=0) if kb else None
            mark = ""
            if vis and not vis["visible"]:
                mark = f"　⚠️ b2b看不到（{'／'.join(vis['blocked_by'])}）"
            cats = c.get("categories") or []
            cat_mark = "　⚠️ categories 空" if not cats else ""
            summary = (c.get("question_summary") or "").replace("\n", " ")[:46]
            lines.append(f"- [ ] `{c['id']}` dist={c['dist']:.4f}　**{summary}**{cat_mark}{mark}")
            # ⚠️ 內容必附：標題是短關鍵字，⛔ 光看標題判不出「這是不是答案」
            lines.append(f"      {(c.get('answer_head') or '(無內容)').strip()}")
        lines.append("- [ ] `NO_COVERAGE`　**庫裡沒有這題的答案**（合法且有價值的答案）")
        lines.append("")
        lines.append("  why: ")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ {len(batch)} 題 × top-{TOP_N} 候選 → {out_path}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="正解候選提名（契約 §A）")
    ap.add_argument("--self-test", action="store_true", help="先驗 oracle（⛔ 第一次必跑）")
    ap.add_argument("--batch", help="批次檔（含 ts／q 的 JSON 陣列）")
    ap.add_argument("--out", help="輸出的待勾選清單（markdown）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not (args.batch and args.out):
        ap.error("需要 --batch 與 --out（或 --self-test）")
    return build_sheet(args.batch, args.out)


if __name__ == "__main__":
    sys.exit(main())
