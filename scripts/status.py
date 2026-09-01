#!/usr/bin/env python3
"""一行看完檢索產線現況——**開工第一件事跑這支**。

**為什麼要有這支**（2026-09-01）：本專案的進度與現況散在 `HANDOFF-*.md` 與
`PLAN-*.md` 裡**手寫**，於是同一輪裡出現三處對不上的數字：
以 913 當覆蓋率分母（真值 773）、「有 24 筆命中標註」（實際可用 **0**，全懸空）、
以及一個查無來源的基準 `62.8%` 被引用了整個 session。

原則：**進度一律由查詢產生，不手寫。** 寫死的數字會過期，
而**過期的數字比沒有數字更傷**——它長得像證據。

⛔ 本檔不做任何寫入。⛔ 不讀 .env、不印任何憑證。

用法：
    python3 scripts/status.py            # 完整
    python3 scripts/status.py --brief    # 只印危害與待裁決
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "scripts" / "BACKLOG.md"
PG = "aichatbot-postgres"
APP = "aichatbot-rag-orchestrator"

#: `- [ ] (⛔|❓|P1) 2026-09-01 一句話 — 說明`
_ITEM = re.compile(r"^-\s*\[ \]\s*\((P\d|⛔|❓)\)\s*(\d{4}-\d{2}-\d{2})\s+(.+?)\s*(?:—|$)")

#: 適格母體＝active 扣掉「設定列」與「空 answer 錨點」。⚠️ 兩者交集為 0（已驗）。
#: ⛔ 不得改用 active-9 當分母——那把設定列與錨點都算進去了（毛數字 913）。
ELIGIBLE = ("is_active AND COALESCE(category,'') NOT IN ('系統脈絡','對話規則') "
            "AND id <> 4253 AND answer IS NOT NULL AND btrim(answer) <> ''")


def psql(sql: str) -> str:
    r = subprocess.run(["docker", "exec", PG, "psql", "-U", "aichatbot",
                        "-d", "aichatbot_admin", "-tAc", sql],
                       capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise RuntimeError(f"psql 失敗：{r.stderr.strip()}")
    return r.stdout.strip()


def rows(sql: str) -> list[list[str]]:
    out = psql(sql)
    return [ln.split("|") for ln in out.splitlines() if ln.strip()]


def one(sql: str) -> int:
    return int(psql(sql) or 0)


def bar(pct: float, width: int = 18) -> str:
    return "█" * round(pct * width) + "·" * (width - round(pct * width))


# ── 危害與待裁決：置頂，在任何進度數字之前 ────────────────────────────
def print_backlog() -> None:
    if not BACKLOG.exists():
        print(f"⚠️ 找不到 {BACKLOG.relative_to(ROOT)}——危害與待裁決無人看管\n")
        return
    items: dict[str, list[tuple[str, str]]] = {}
    for ln in BACKLOG.read_text("utf-8").splitlines():
        m = _ITEM.match(ln)
        if m:
            items.setdefault(m.group(1), []).append((m.group(2), m.group(3)))
    for lv, title in (("⛔", "活躍危害（現在不能做什麼）"), ("❓", "待業主裁決")):
        if lv in items:
            print(f"{lv} {title}：{len(items[lv])} 條")
            for d, t in items[lv]:
                print(f"   {d}  {t}")
            print()
    todo = sum(len(v) for k, v in items.items() if k.startswith("P"))
    if todo:
        print(f"📌 待辦 {todo} 條（P1–P3，球在我們，開單久是正常的）\n")


# ── 知識庫 ────────────────────────────────────────────────────────────
def print_kb() -> None:
    print("📚 知識庫")
    active = one("SELECT count(*) FROM knowledge_base WHERE is_active;")
    # 正對照：generation_metadata 本身有資料 ⇒「只有 n 筆有 representation」不是查詢假象
    posctrl = one("SELECT count(*) FROM knowledge_base WHERE is_active "
                  "AND generation_metadata IS NOT NULL;")
    if posctrl == 0:
        sys.exit("⛔ 正對照失敗：generation_metadata 全空，查詢路徑可疑，拒絕輸出數字")
    elig = one(f"SELECT count(*) FROM knowledge_base WHERE {ELIGIBLE};")
    repr_ = one(f"SELECT count(*) FROM knowledge_base WHERE {ELIGIBLE} AND "
                "NULLIF(TRIM(COALESCE(generation_metadata->>'retrieval_representation','')),'') "
                "IS NOT NULL;")
    cfg = one("SELECT count(*) FROM knowledge_base WHERE is_active AND "
              "(category IN ('系統脈絡','對話規則') OR id = 4253);")
    anchor = one("SELECT count(*) FROM knowledge_base WHERE is_active AND "
                 "(answer IS NULL OR btrim(answer) = '');")
    overlap = one("SELECT count(*) FROM knowledge_base WHERE is_active AND "
                  "(category IN ('系統脈絡','對話規則') OR id = 4253) AND "
                  "(answer IS NULL OR btrim(answer) = '');")
    print(f"   active {active}  −設定列 {cfg}  −空answer錨點 {anchor}"
          f"{'  ⚠️ 兩者交集 %d，扣重了' % overlap if overlap else ''}"
          f"  ⇒ **適格母體 {elig}**")
    pct = repr_ / elig if elig else 0
    print(f"   retrieval_representation  {repr_}/{elig}  {bar(pct)} {pct:6.2%}")
    print("   ⛔ 分母是適格母體，不是 active、不是 913（毛數字）")

    b2b = one(f"SELECT count(*) FROM knowledge_base WHERE {ELIGIBLE} AND "
              "business_types && ARRAY['system_provider']::text[] AND "
              "(target_user IS NULL OR 'property_manager' = ANY(target_user));")
    pros = one(f"SELECT count(*) FROM knowledge_base WHERE {ELIGIBLE} AND "
               "business_types && ARRAY['system_provider']::text[] AND "
               "(target_user IS NULL OR 'prospect' = ANY(target_user));")
    b2c = one(f"SELECT count(*) FROM knowledge_base WHERE {ELIGIBLE} AND "
              "(business_types IS NULL OR business_types && "
              "ARRAY['property_management','full_service']::text[]) AND "
              "(target_user IS NULL OR target_user && ARRAY['tenant','all_users']::text[]);")
    misfiled = one(f"SELECT count(*) FROM knowledge_base WHERE {ELIGIBLE} AND "
                   "'tenant' = ANY(target_user) AND "
                   "business_types && ARRAY['system_provider']::text[] AND NOT "
                   "(business_types && ARRAY['property_management','full_service']::text[]);")
    print(f"   各池可見  b2b業者 {b2b}  ｜ b2c租客 {b2c}  ｜ prospect {pros}")
    if misfiled:
        print(f"   ⚠️ {misfiled} 筆 target_user 含 tenant 卻只在 system_provider 池 ⇒ 租客搜不到")
    print()


# ── 測試資料 ──────────────────────────────────────────────────────────
def print_scenarios() -> None:
    print("🧪 測試資料（test_scenarios）")
    tot = one("SELECT count(*) FROM test_scenarios WHERE is_active;")
    cat = one("SELECT count(*) FROM test_scenarios WHERE is_active "
              "AND expected_category IS NOT NULL;")
    cat_uq = one("SELECT count(*) FROM test_scenarios WHERE is_active "
                 "AND expected_category IS NOT NULL AND source='user_question';")
    ans = one("SELECT count(*) FROM test_scenarios WHERE is_active "
              "AND expected_answer IS NOT NULL AND btrim(expected_answer) <> '';")
    kid = one("SELECT count(*) FROM test_scenarios WHERE is_active "
              "AND array_length(related_knowledge_ids,1) > 0;")
    # ⚠️ 這一步是 2026-09-01 的教訓：帳面 24 筆標註，實際可用 0（引用的 id 全不存在）
    live = one("""WITH ids AS (SELECT DISTINCT unnest(related_knowledge_ids) kid
                    FROM test_scenarios WHERE is_active
                     AND array_length(related_knowledge_ids,1) > 0)
                  SELECT count(*) FROM ids JOIN knowledge_base kb ON kb.id = ids.kid;""")
    refd = one("""SELECT count(*) FROM (SELECT DISTINCT unnest(related_knowledge_ids) kid
                    FROM test_scenarios WHERE is_active
                     AND array_length(related_knowledge_ids,1) > 0) t;""")
    print(f"   總數 {tot}   expected_category {cat}"
          f"（其中真實使用者問句 {cat_uq}{'  ⚠️ 佔 0 ⇒ 路由率不代表真實流量' if cat_uq == 0 else ''}）")
    print(f"   expected_answer {ans}"
          f"{'  ⚠️ 全 0 ⇒ 答案正確性只能走接受範圍 rubric' if ans == 0 else ''}")
    dangling = refd - live
    print(f"   related_knowledge_ids {kid} 筆標註 → 引用 {refd} 個知識 id，"
          f"**實際存在 {live}**"
          f"{'  ⛔ %d 個懸空，命中真相實際可用 0' % dangling if dangling else ''}")
    print()


# ── 實際流量 ──────────────────────────────────────────────────────────
def print_traffic() -> None:
    print("📈 實際流量（usage_events，非內部）")
    rs = rows("SELECT COALESCE(mode,'(null)'), COALESCE(target_user,'(null)'), count(*) "
              "FROM usage_events WHERE NOT is_internal GROUP BY 1,2 "
              "ORDER BY 3 DESC LIMIT 6;")
    if not rs:
        print("   ⚠️ 查無非內部事件——確認 is_internal 標記是否正確")
    for m, tu, n in rs:
        print(f"   {m:<6} / {tu:<18} {int(n):>6}")
    print()


# ── 環境與管線健檢 ────────────────────────────────────────────────────
def print_env() -> None:
    print("🔧 環境與管線健檢（⛔ 實查，不看 compose、不看程式預設）")
    keys = ["ENABLE_RERANKER", "KB_SIMILARITY_THRESHOLD", "FORM_TRIGGER_THRESHOLD",
            "ENABLE_QUERY_REWRITE_B2B", "RERANKER_INPUT_LIMIT", "USE_MOCK_JGB_API"]
    try:
        r = subprocess.run(["docker", "exec", APP, "sh", "-c",
                            "; ".join(f'echo "{k}=$(printenv {k})"' for k in keys)],
                           capture_output=True, text=True, timeout=30)
        if r.returncode:
            raise RuntimeError(r.stderr.strip())
        for ln in r.stdout.strip().splitlines():
            k, _, v = ln.partition("=")
            print(f"   {k:<26} {v or '(未設，走程式預設)'}")
    except Exception as e:
        print(f"   ⛔ 讀不到容器環境：{e}")

    # 向量索引健檢：IVFFlat 的 lists 相對於資料量是否合理
    # pgvector 建議：<1M 筆用 lists ≈ 筆數/1000。lists 過大 ⇒ probes=1 只掃到極小片段。
    print("\n   向量索引（lists 過大 ⇒ 靜默漏召回，且不會報錯）")
    # ⚠️ 表與欄位一律**從 indexdef 解析**，⛔ 不寫死清單——寫死的那幾張會變成
    #    「筆數未查」而靜默跳過，那正是這支要防的事（漏檢與檢查通過長得一樣）。
    idx = rows("""SELECT i.tablename,
                    COALESCE((regexp_match(i.indexdef, 'ivfflat \\(([a-z_]+)'))[1],'-'),
                    COALESCE((regexp_match(i.indexdef, 'lists\\s*=\\s*''?(\\d+)'))[1],'-')
                  FROM pg_indexes i WHERE i.indexdef LIKE '%ivfflat%' ORDER BY 1;""")
    bad = unknown = 0
    for tbl, col, lists in idx:
        if col == "-":
            print(f"   ?  {tbl:<26} ⛔ 解析不出向量欄位，未檢查")
            unknown += 1
            continue
        n = one(f"SELECT count(*) FROM {tbl} WHERE {col} IS NOT NULL;")
        if lists == "-":
            print(f"   ✅ {tbl:<26} 未指定 lists（走預設）  向量 {n}")
            continue
        li = int(lists)
        per = n / li if li else 0
        ok = li <= max(1, n // 1000) * 4 or per >= 100
        if n == 0:
            # ⚠️ 無資料 ⇒ 現在不會出事，但參數留著，有資料的那天就會靜默漏召回。
            #    ⛔ 不併入 bad（避免警訊疲勞），但也 ⛔ 不印成 ✅（那是假綠）。
            print(f"   ⚠️ {tbl:<26} lists={li:<4} 向量 0     目前無資料；⛔ 有資料時會致命")
            continue
        bad += 0 if ok else 1
        print(f"   {'✅' if ok else '⛔'} {tbl:<26} lists={li:<4} 向量 {n:<5} "
              f"每 list 約 {per:.0f} 筆{'' if ok else '  ← 建議 lists ≈ 筆數/1000'}")
    if bad:
        print(f"   ⛔ {bad} 個索引參數不合理 ⇒ **本輪任何檢索數字都不可信**，先修索引")
    if unknown:
        print(f"   ⛔ {unknown} 個索引無法檢查——⛔ 別當成通過")
    print()


def main() -> int:
    brief = "--brief" in sys.argv
    print_backlog()
    if brief:
        return 0
    try:
        print_kb()
        print_scenarios()
        print_traffic()
        print_env()
    except Exception as e:            # 大聲失敗：⛔ 不靜默跳過核心判斷
        print(f"\n⛔ 查詢失敗，本次輸出不完整：{e}")
        return 1
    print("⚠️ 以上皆為當下查詢結果。⛔ 不要把這些數字抄進文件——抄了就開始腐化。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
