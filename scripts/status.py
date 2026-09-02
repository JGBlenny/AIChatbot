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


# ── b2b 答題面：型別分布與面向覆蓋 ────────────────────────────────────
#: ⚠️ 型別由系統自己編碼，逐筆機械可算（⛔ 不靠印象、⛔ 不手寫清單）：
#:   表單型  action_type='form_fill' 或 form_id 非空
#:   T2 API  action_type='api_call'，或 categories 命中的面向 grounding_scope.select='api'
#:   T3 對話 categories 命中面向但該面向非 api 型（純引導）
#:   T1 直答 以上皆非
#: ⛔ 四型的「對」不是同一件事 ⇒ ⛔ 一批一型，混批的率讀不出意義
#:   （判準見 .claude/skills/retrieval-improvement-loop/rules/型別分批.md）
#: ⛔ **答題母體定義的正本**（2026-09-02 業主指出後收斂；同日獨立驗證再修正標籤）。
#:
#: ⚠️ **這不是「b2b 可見」** —— 是「**b2b 可見且有 answer**」。
#:   retriever 實際撈得到的是 **354** 筆；本常數是 293，差的 61 筆是
#:   **空 answer 的面向進場錨點**，而它們 `embedding IS NOT NULL`、確實會被撈進候選池。
#:   ⇒ 下方「面向覆蓋」的知識數把錨點整批排除（狀態判斷 −9／繳費金流排障 −5／
#:     合約異動 −4／續約 −3／帳單異常 −3…），⚠️ 那些 ⚠️／⛔ 警訊是在**答題母體**上算的，
#:     ⛔ 不等於「候選池裡沒有東西」。
#: ⚠️ 本常數也**無法表達兩條檢索路母體不同**（向量路 293／詞面路 264）——
#:   扁平 where 在結構上做不到。要判「這一筆這個角色看不看得到」請用
#:   `rag-orchestrator/scripts/backtest/contract_enrich.py` 的 `visibility()`（兩路取聯集）。
#:   ⇒ 兩者何為正本已登記 **DSP-002**，⛔ 未裁前不得互相取代。
#: ⚠️ 本常數只涵蓋 `property_manager`；retriever 的 `is_b2b_mode` 還認 `system_admin`
#:   （該身分僅 8 筆可見）⇒ 窄化是刻意的，但此前**未宣告**。
#: ⚠️ 那天同一個 session 用過**四個**不同母體、產出四組數字，沒有一次對齊：
#:   772 全庫適格（ELIGIBLE）／381 只濾 business_types／320 少了 target_user 與 id<>4253／
#:   **293 才是對的**。之後每一句「業者池 N 筆中…」的母體都偏大。
#: ⇒ 任何腳本要用 b2b 母體，**逐條複製本常數並註明出處**，⛔ 不得自己重寫一個 where。
#: ⇒ 改本常數＝改全專案的分母，⛔ 改之前先確認 retriever 的過濾邏輯真的變了。
_B2B = ("is_active AND business_types && ARRAY['system_provider']::text[] "
        "AND (target_user IS NULL OR 'property_manager' = ANY(target_user)) "
        "AND COALESCE(category,'') NOT IN ('系統脈絡','對話規則') AND id <> 4253 "
        "AND answer IS NOT NULL AND btrim(answer) <> ''")


def print_b2b_surface() -> None:
    print("🎯 b2b 答題面（⛔ 一批一型；四型的『對』不是同一件事）")
    rs = rows(f"""
      WITH b2b AS (SELECT * FROM knowledge_base WHERE {_B2B}),
       fac AS (SELECT generation_metadata->'conversational_config'->'topic_scope'->>'category' cat,
               COALESCE(generation_metadata->'conversational_config'->'grounding_scope'->>'select','none') sel
               FROM knowledge_base WHERE is_active AND category='對話規則'
               AND generation_metadata->'conversational_config'->'topic_scope'->>'mode'='category'),
       t AS (SELECT b.id, b.action_type, b.form_id,
             (SELECT max(f.sel) FROM fac f WHERE f.cat = ANY(b.categories)) sel FROM b2b b)
      SELECT CASE
        WHEN action_type='form_fill' OR form_id IS NOT NULL THEN '表單型'
        WHEN action_type='api_call' OR sel='api'            THEN 'T2 對話＋API'
        WHEN sel IS NOT NULL                                THEN 'T3 對話引導'
        ELSE 'T1 單一知識直答' END, count(*)
      FROM t GROUP BY 1 ORDER BY 2 DESC;""")
    tot = sum(int(n) for _, n in rs)
    for k, n in rs:
        print(f"   {k:<16}{int(n):>4}  {bar(int(n)/tot if tot else 0)}")
    print(f"   {'合計':<16}{tot:>4}")

    nocat = one(f"SELECT count(*) FROM knowledge_base WHERE {_B2B} "
                "AND cardinality(COALESCE(categories,'{}')) = 0;")
    if nocat:
        print(f"   ⛔ {nocat} 筆 categories 空 ⇒ **面向進場對它們靜默失效**（知識已寫好，只是沒掛分類）")
        print("      ⚠️ 補分類是**行為變更**（繞過適用性把關）⇒ ⛔ 不得一次全掛，分批補、每批補完立刻回測")

    print("\n   面向覆蓋（知識數由少到多；⚠️ 薄 ⛔ 不等於缺，要對照真實問句）")
    fr = rows(f"""
      WITH b2b AS (SELECT * FROM knowledge_base WHERE {_B2B})
      SELECT gm->'topic_scope'->>'category',
             COALESCE(gm->'grounding_scope'->>'select','引導'),
             COALESCE(gm->'grounding_scope'->>'required_slots','-'),
             (SELECT count(*) FROM b2b WHERE gm->'topic_scope'->>'category' = ANY(b2b.categories))
      FROM (SELECT generation_metadata->'conversational_config' gm FROM knowledge_base
            WHERE is_active AND category='對話規則'
            AND generation_metadata->'conversational_config'->'topic_scope'->>'mode'='category') f
      ORDER BY 4, 1;""")
    for cat, sel, slots, n in fr[:8]:
        flag = "⛔" if int(n) == 0 else ("⚠️" if int(n) <= 3 else "  ")
        print(f"   {flag} {cat:<14} {sel:<9} 知識 {int(n):>2}  槽位 {slots[:34]}")
    print(f"   …共 {len(fr)} 個面向（完整清單見本節查詢條件）")
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

    # ── Reranker 實際狀態（2026-09-01 血證：整天的結論因它作廢）──────────────
    # ⛔ 不看容器 healthy、⛔ 不打 /api/v1/system/pipeline-health：
    #    那支健檢**自己另外重新探測一次**，與正在服務請求的物件狀態無關 ⇒ 會給假綠。
    # 唯一可靠的外部證據是 app 自己印的那兩行，取**最後一行**為準。
    # 成因：semantic_reranker.__init__ 只在建構當下打一次 GET /（timeout=2），
    #      失敗即 is_available=False 且整個 process 生命週期不再重查。
    print("\n   Reranker（佔最終分數 90%：0.1×vector + 0.9×rerank）")
    try:
        lg = subprocess.run(["docker", "logs", APP], capture_output=True, text=True,
                            timeout=60).stderr or ""
        lg += subprocess.run(["docker", "logs", APP], capture_output=True, text=True,
                             timeout=60).stdout or ""
        marks = [ln for ln in lg.splitlines()
                 if "Reranker 已啟用" in ln or "SemanticReranker 服務不可用" in ln]
        fin = [ln for ln in lg.splitlines() if "[Finalize]" in ln][-3:]
        if not marks:
            print("   ⚠️ 日誌查無 reranker 初始化訊息——⛔ 別當成正常，去看 app 啟動日誌")
        elif "服務不可用" in marks[-1]:
            print(f"   ⛔ **最後一次判定＝服務不可用，reranker 沒在跑**（共 {len(marks)} 次判定）")
            print("      ⇒ 分數落到 max(vector,keyword)×boost 分支，純詞面命中得 1.0 壓過正解")
            print("      ⇒ ⛔ 本輪任何檢索/回測數字作廢，先修 reranker")
        else:
            print(f"   ✅ 最後一次判定＝已啟用（共 {len(marks)} 次判定）")
        for ln in fin:
            rr = ln.split("rerank=")[1].split(",")[0] if "rerank=" in ln else "?"
            flag = "⛔" if rr == "0" else "✅"
            print(f"   {flag} 最近 Finalize：rerank={rr}  {ln.strip()[:60]}")
        if not fin:
            print("   ⚠️ 近期無 Finalize 記錄——沒有流量，無法確認實際有沒有在用")
    except Exception as e:
        print(f"   ⛔ 讀不到 app 日誌：{e}")

    # 向量索引健檢：IVFFlat 的 lists 相對於資料量是否合理
    # pgvector 建議：<1M 筆用 lists ≈ 筆數/1000。lists 過大 ⇒ probes=1 只掃到極小片段。
    print("\n   向量索引（IVFFlat 的 lists 過大 ⇒ 靜默漏召回，且不會報錯；HNSW 無此問題）")
    # ⚠️ 表與欄位一律**從 indexdef 解析**，⛔ 不寫死清單——寫死的那幾張會變成
    #    「筆數未查」而靜默跳過，那正是這支要防的事（漏檢與檢查通過長得一樣）。
    # ⚠️ 一律比對 `USING <method>`，⛔ 不比對索引**名稱**——
    #    `idx_vendor_sop_items_primary_embedding_ivfflat` 已改建為 HNSW 但名稱沿用，
    #    用名稱比對會產生假警訊（2026-09-01 實際踩到）。
    # ⚠️ 同時列出 HNSW，⛔ 別讓這一節在修好後變成空白——空白的健檢等於沒有健檢。
    idx = rows("""SELECT i.tablename,
                    COALESCE((regexp_match(i.indexdef, 'USING (ivfflat|hnsw) \\(([a-z_]+)'))[1],'-'),
                    COALESCE((regexp_match(i.indexdef, 'USING (ivfflat|hnsw) \\(([a-z_]+)'))[2],'-'),
                    COALESCE((regexp_match(i.indexdef, 'lists\\s*=\\s*''?(\\d+)'))[1],'-')
                  FROM pg_indexes i
                 WHERE i.indexdef LIKE '%USING ivfflat%' OR i.indexdef LIKE '%USING hnsw%'
                 ORDER BY 1;""")
    bad = unknown = 0
    for tbl, method, col, lists in idx:
        if col == "-" or method == "-":
            print(f"   ?  {tbl:<26} ⛔ 解析不出索引方法或向量欄位，未檢查")
            unknown += 1
            continue
        n = one(f"SELECT count(*) FROM {tbl} WHERE {col} IS NOT NULL;")
        if method == "hnsw":
            # HNSW ⛔ 沒有 lists／probes 可以配錯 ⇒ 不屬於本檢查要防的那一類
            print(f"   ✅ {tbl:<26} HNSW        向量 {n}")
            continue
        if lists == "-":
            print(f"   ⚠️ {tbl:<26} IVFFlat 未指定 lists（走預設）  向量 {n}")
            continue
        li = int(lists)
        per = n / li if li else 0
        ok = li <= max(1, n // 1000) * 4 or per >= 100
        if n == 0:
            # ⚠️ 無資料 ⇒ 現在不會出事，但參數留著，有資料的那天就會靜默漏召回。
            #    ⛔ 不併入 bad（避免警訊疲勞），但也 ⛔ 不印成 ✅（那是假綠）。
            print(f"   ⚠️ {tbl:<26} IVFFlat lists={li:<4} 向量 0  目前無資料；⛔ 有資料時會致命")
            continue
        bad += 0 if ok else 1
        print(f"   {'✅' if ok else '⛔'} {tbl:<26} IVFFlat lists={li:<4} 向量 {n:<5} "
              f"每 list 約 {per:.0f} 筆{'' if ok else '  ← 建議 lists ≈ 筆數/1000'}")
    if bad:
        print(f"   ⛔ {bad} 個索引參數不合理 ⇒ **本輪任何檢索數字都不可信**，先修索引")
    if unknown:
        print(f"   ⛔ {unknown} 個索引無法檢查——⛔ 別當成通過")
    print()


def print_worktree() -> None:
    """⛔ 未 commit 的改動置頂警告。

    **為什麼**（2026-09-01 收線驗證抓到）：那一天最重要的一項成果
    （架構母圖 §3 過濾機制逐行對碼修正）只存在工作樹、未進版控。
    下一個 session 若跑 `git checkout .`／`git stash`／`git reset --hard`
    清理工作樹，**那份修正會無聲消失**，而 BACKLOG 不會提醒任何人。
    ⇒ 讓它每次開工都被印出來。
    """
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return
    print(f"⚠️ **工作樹有 {len(lines)} 項未 commit 的改動** —— ⛔ 清理工作樹前務必先看")
    for l in lines[:8]:
        print(f"   {l}")
    if len(lines) > 8:
        print(f"   …另 {len(lines)-8} 項")
    print("   ⛔ `git checkout .` / `git stash` / `git reset --hard` 會讓它們無聲消失")
    print("   ⇒ 先 `git diff` 看清楚是什麼；不確定就**先 commit 再說**\n")


def main() -> int:
    brief = "--brief" in sys.argv
    print_worktree()
    print_backlog()
    if brief:
        return 0
    try:
        print_kb()
        print_b2b_surface()
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
