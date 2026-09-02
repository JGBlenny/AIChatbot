#!/usr/bin/env python3
"""回測輸出契約 §B③④ 的報表層（P0-1）。

> 契約正本：`.claude/skills/retrieval-improvement-loop/steps/03-回測輸出契約.md`
> 成因七類：`.claude/skills/retrieval-improvement-loop/rules/成因分類.md`

## 這支負責哪兩格

```text
③ 可見性    對 expected_kb_id 機械算三軸過濾（business_types／target_user／vendor_ids）
            ⇒ 直接標「正解存在，但這個角色結構上看不到」（成因 V 類）
④ 面向職責  該面向「對話規則」列的 topic_scope／grounding_scope／responsibility
            ⇒ 判 E 類（進場提名錯）時「該不該由它接」有客觀依據，⛔ 不靠印象
```

①（走了哪條路）與②（候選與分數）**不在這裡**——它們是生產路徑上的無條件遙測，
由 `chat._meter_kb_candidates` 等落進 `usage_events.decision_snapshot`。
本支只做「跑完之後、對每一題算出來」的兩格，⛔ 不改任何生產行為。

## ⛔ 三軸謂詞的來源紀律

謂詞**逐條抄自 `services/vendor_knowledge_retriever_v2.py` 的 `_vector_search`**，
⛔ 不得抄文件。理由：`docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` §3
就曾漏掉 b2b 嚴格分支，照它補 `IS NULL` 會打穿刻意設計的跨業者隔離。
⇒ 改動 retriever 過濾邏輯時，本檔的 `visibility()` 必須同步（有測試把關）。

## ⛔ 尺自證

`--self-test` 用**已知答案**的真實資料列驗這把尺看不看得見病灶：
kb:3336 對 b2b 必須判 INVISIBLE（血證：它是 ts9885 的正解卻不含 system_provider），
kb:4217 對 b2b 必須判 VISIBLE。任一判錯 ⇒ 尺是瞎的，⛔ 不得拿它的輸出下任何結論。

## 跑法

    python3 rag-orchestrator/scripts/backtest/contract_enrich.py --self-test
    python3 ... --session-prefix vrf0902_            # ④：把面向職責併進每題
    python3 ... --session-prefix vrf0902_ --frozen a.json   # ③＋④（需凍結檔）

⚠️ `--frozen` 是契約 §A 的兩格（expected_owner／expected_kb_id），**跑前人裁、進版控**。
⛔ 沒有它時本支只輸出 ④，③ 一律標 `NO_FROZEN_EXPECTATION`——
⛔ 不得以任何方式自行猜測正解（那會讓量測變成自我實現）。
"""
import argparse
import json
import os
import subprocess
import sys

PG_CONTAINER = os.environ.get("CONTRACT_ENRICH_PG", "aichatbot-postgres")
PG_USER = "aichatbot"
PG_DB = "aichatbot_admin"

#: 對齊 `VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS`（⛔ 不得各自定義）。
KNOWN_TARGET_USERS = {"tenant", "landlord", "property_manager", "system_admin", "prospect"}

#: 對齊 `SYSTEM_DOC_CATEGORY` / `RULES_DOC_CATEGORY`——這兩類是系統注入用文件，
#: 檢索一律排除，永不被當答案回傳。
EXCLUDED_CATEGORIES = {"系統脈絡", "對話規則"}

#: b2b 的業態值（retriever 在 b2b 分支寫死）。
B2B_BUSINESS_TYPES = ["system_provider"]

FACET_CONFIG_CATEGORY = "對話規則"


class DataError(RuntimeError):
    """查不到該有的資料——⚠️ **大聲失敗**，⛔ 不得靜默跳過核心判斷。"""


# ---------------------------------------------------------------------------
# DB（沿 scripts/status.py 房式：docker exec psql；⛔ 不讀 .env、⛔ 不印憑證）
# ---------------------------------------------------------------------------

def psql(sql: str) -> str:
    r = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-tAc", sql],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode:
        raise DataError(f"psql 失敗：{r.stderr.strip()}")
    return r.stdout.strip()


def psql_json(sql: str):
    """要求 SQL 回單一 json 值；空結果回 None。"""
    out = psql(sql)
    return json.loads(out) if out else None


# ---------------------------------------------------------------------------
# ③ 可見性：三軸過濾的機械重算
# ---------------------------------------------------------------------------

def effective_target_user(target_user):
    """對齊 `VendorKnowledgeRetrieverV2._effective_target_user`。

    ⚠️ 未知角色**靜默正規化為 tenant**——測試打錯角色名不會報錯，
    只會安靜地測到別的池。本函式照抄該行為，好讓報表能重現同一個坑。
    """
    if isinstance(target_user, list):
        target_user = target_user[0] if target_user else None
    return target_user if target_user in KNOWN_TARGET_USERS else "tenant"


def is_b2b_mode(target_user, mode) -> bool:
    """對齊 retriever：角色屬 b2b 兩者之一，或 mode 明寫 b2b。"""
    return target_user in ("property_manager", "system_admin") or mode == "b2b"


#: 本尺實作了 SQL 過濾**讀到的哪些欄位**——與 retriever 的兩條 WHERE 對帳用。
#: ⚠️ retriever 若新增一條讀新欄位的過濾條件，靜態不變量測試會紅，
#: 逼人當場決定「在尺裡補上」或「明寫豁免理由」。
#: ⛔ 不得為了讓測試變綠而把新欄位塞進來卻不實作對應判斷。
FILTER_COLUMNS_VECTOR = frozenset({
    "vendor_ids", "embedding", "is_active", "category", "business_types", "target_user",
})
FILTER_COLUMNS_KEYWORD = frozenset({
    "vendor_ids", "is_active", "category", "keywords", "business_types", "target_user",
})


def visibility(kb_row: dict, *, mode: str, target_user, vendor_id: int,
               vendor_business_types=None) -> dict:
    """這一列知識，對「本輪 mode × 角色 × 業者」是否可見。

    ⚠️ **兩條檢索路的 WHERE 不一樣**，所以可見性是「兩條之中有一條進得去」：

        共同   array_length(kb.vendor_ids,1) IS NULL OR kb.vendor_ids && ARRAY[vendor_id]
               kb.is_active = TRUE
               kb.category IS DISTINCT FROM '系統脈絡' / '對話規則'
               業態  b2b：kb.business_types && ARRAY['system_provider']  ⛔ **無 IS NULL 放行**
                     b2c：kb.business_types IS NULL OR ... && ARRAY[業者業態]
               角色  kb.target_user IS NULL OR kb.target_user && ARRAY[角色]
                     （b2c 另放行 'all_users'）
        向量路 kb.embedding IS NOT NULL
        詞面路 kb.keywords IS NOT NULL AND array_length(kb.keywords,1) > 0

    ⚠️ **這裡曾經是錯的**（2026-09-02 寫靜態不變量時發現）：初版把「沒有 embedding」
    當成一律不可見，但那只擋得住向量路——有 keywords 的列仍可經詞面路撈到。
    ⛔ 不得只模型單一路徑。

    ⚠️ b2b 業態那條沒有 `IS NULL` 放行是**刻意的跨業者隔離**
    （`docs/retrieval-recall-audit-20260822.md`）。
    ⛔ 判為不可見時的修法是改**那筆資料的歸屬**，⛔ 不是放寬過濾器。

    ## ⚠️ 這把尺量的是**結構可見性的上界**，⛔ 不是「這一題撈得到」

    詞面路除了上列條件，實際查詢還會多一條**與問句相關**的過濾：
    `AND kb.keywords && %s::text[]`（知識的 keywords 要與該問句的斷詞有交集）。
    本尺不模型它——它逐題不同，不是這一列的靜態屬性。
    ⇒ 判 `visible=True` 的意思是「結構上沒有任何一軸擋住它」，
      ⛔ **不保證**該問句實際會把它撈進候選池。
    ⇒ 反過來 `visible=False` 是硬結論：任何問句都撈不到（V 類成立）。

    回傳 `{visible, blocked_by, paths:{vector:…, keyword:…}}`；
    `blocked_by` ＝兩條路都擋下時的共同原因（空＝可見）。
    """
    common = []

    if not kb_row.get("is_active"):
        common.append("is_active")
    if kb_row.get("category") in EXCLUDED_CATEGORIES:
        common.append("category_excluded")

    vendor_ids = kb_row.get("vendor_ids")
    # ⚠️ `array_length(x,1) IS NULL` 對 NULL **與空陣列**皆為真＝全業者共用，放行。
    if vendor_ids and vendor_id not in vendor_ids:
        common.append("vendor_ids")

    b2b = is_b2b_mode(target_user, mode)
    bt = kb_row.get("business_types")
    if b2b:
        if not (bt and set(bt) & set(B2B_BUSINESS_TYPES)):
            common.append("business_types")   # ⛔ b2b 無 IS NULL 放行
    else:
        want = list(vendor_business_types or [])
        if bt is not None and not (set(bt) & set(want)):
            common.append("business_types")

    tu = kb_row.get("target_user")
    if tu is not None:
        allowed = {effective_target_user(target_user)}
        if not b2b:
            allowed.add("all_users")
        if not (set(tu) & allowed):
            common.append("target_user")

    vector_blocked = list(common)
    if not kb_row.get("has_embedding"):
        vector_blocked.append("embedding")

    keyword_blocked = list(common)
    if not kb_row.get("keywords"):            # NULL 或空陣列皆進不去詞面路
        keyword_blocked.append("keywords")

    visible = (not vector_blocked) or (not keyword_blocked)
    return {
        "visible": visible,
        "blocked_by": [] if visible else sorted(set(vector_blocked) & set(keyword_blocked)) or common,
        "paths": {
            "vector": {"visible": not vector_blocked, "blocked_by": vector_blocked},
            "keyword": {"visible": not keyword_blocked, "blocked_by": keyword_blocked},
        },
    }


def fetch_kb_rows(ids) -> dict:
    """取三軸判定所需的欄位。⚠️ 查不到的 id 由呼叫端標成懸空，⛔ 不得靜默略過。"""
    ids = [int(i) for i in ids]
    if not ids:
        return {}
    id_list = ",".join(str(i) for i in ids)
    rows = psql_json(
        "select coalesce(json_agg(row_to_json(t)),'[]'::json) from ("
        "  select id, is_active, category, business_types, target_user, vendor_ids,"
        "         keywords, (embedding is not null) as has_embedding"
        f"  from knowledge_base where id in ({id_list})"
        ") t"
    )
    return {r["id"]: r for r in (rows or [])}


# ---------------------------------------------------------------------------
# ④ 面向職責：對話規則列的三個宣告
# ---------------------------------------------------------------------------

def load_facet_contracts() -> dict:
    """讀 `knowledge_base` 中 `category='對話規則'` 每列的 conversational_config。

    ⚠️ 設定本體在 `generation_metadata.conversational_config`（見
    `services/conversational_config.py` 的模組 docstring），⛔ 不是獨立資料表。
    """
    rows = psql_json(
        "select coalesce(json_agg(row_to_json(t)),'[]'::json) from ("
        "  select id, generation_metadata->'conversational_config' as cfg"
        f"  from knowledge_base where category='{FACET_CONFIG_CATEGORY}'"
        "     and generation_metadata->'conversational_config' is not null"
        ") t"
    ) or []
    out = {}
    for r in rows:
        cfg = r["cfg"] or {}
        key = cfg.get("key")
        if not key:
            continue                          # 無 key 的列無法對應面向，跳過（下方會統計）
        gs = cfg.get("grounding_scope") or {}
        out[key] = {
            "kb_row_id": r["id"],
            "enabled": cfg.get("enabled", True),
            "persona_role": cfg.get("persona_role"),
            "topic_scope": cfg.get("topic_scope") or {"mode": "all"},
            "grounding_scope": gs,
            "responsibility": cfg.get("responsibility") or {},
            # ⚠️ 已知坑：多數面向的 grounding_scope 沒有 target_user。
            #    判「該不該由它接」時 ⛔ 不得假設這個鍵存在。
            "grounding_target_user_missing": "target_user" not in gs,
        }
    if not out:
        raise DataError(
            f"讀不到任何 category='{FACET_CONFIG_CATEGORY}' 的面向設定——"
            "⛔ 這不是『沒有面向』，是查詢或資料壞了（正對照組：該分類應有 20+ 列）"
        )
    return out


# ---------------------------------------------------------------------------
# 事件讀取（①② 已由生產遙測落盤，這裡只是把它們接回每一題）
# ---------------------------------------------------------------------------

def fetch_events(session_prefix: str) -> list:
    rows = psql_json(
        "select coalesce(json_agg(row_to_json(t) order by t.ts),'[]'::json) from ("
        "  select id, ts, session_id, mode, target_user, role_id, vendor_id,"
        "         processing_path, answer_source, facet_key, facet_event,"
        "         decision_snapshot"
        "  from usage_events"
        f"  where session_id like '{session_prefix}%'"
        ") t"
    )
    return rows or []


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------

def enrich(events: list, facets: dict, frozen: dict = None) -> list:
    """每題一列：① ② 直接取自事件；④ 由 facet_key 併入；③ 需凍結檔才算。"""
    frozen = frozen or {}
    kb_cache = {}
    if frozen:
        wanted = {int(i) for v in frozen.values()
                  for i in (v.get("expected_kb_id") or []) if str(i).isdigit()}
        kb_cache = fetch_kb_rows(wanted)

    out = []
    for ev in events:
        snap = ev.get("decision_snapshot") or {}
        row = {
            "session_id": ev["session_id"],
            "mode": ev["mode"],
            "target_user": ev["target_user"],
            "role_id": ev["role_id"],
            # ① 走了哪條路
            "processing_path": ev["processing_path"],
            "answer_source": ev["answer_source"],
            "facet_key": ev["facet_key"],
            "facet_event": ev["facet_event"],
            "decision_case": snap.get("decision_case"),
            "routing_verdict": snap.get("routing_verdict"),
            # ② 候選與分數
            "kb_candidates": snap.get("kb_candidates"),
            "kb_candidates_scope": snap.get("kb_candidates_scope"),
            "kb_candidates_total": snap.get("kb_candidates_total"),
        }
        if snap.get("kb_candidates") is None:
            # ⚠️ 缺席可能是「這輪沒走檢索」（早退 handler／快取），⛔ 不是「沒有候選」。
            row["kb_candidates_status"] = "NOT_OBSERVED"

        # ④ 面向職責
        fk = ev.get("facet_key")
        if fk:
            fc = facets.get(fk)
            if fc is None:
                row["facet_contract_status"] = "FACET_KEY_NOT_IN_CONFIG"  # ⛔ 大聲失敗
            else:
                row["facet_contract"] = fc
        else:
            row["facet_contract_status"] = "NO_FACET_THIS_TURN"

        # ③ 可見性
        exp = frozen.get(ev["session_id"])
        if not exp:
            row["visibility_status"] = "NO_FROZEN_EXPECTATION"
        else:
            ids = exp.get("expected_kb_id") or []
            if ids == ["NO_COVERAGE"]:
                row["visibility_status"] = "EXPECTED_NO_COVERAGE"
            else:
                vis = []
                for kid in ids:
                    kb = kb_cache.get(int(kid)) if str(kid).isdigit() else None
                    if kb is None:
                        vis.append({"kb_id": kid, "status": "DANGLING_ID"})  # ⛔ 不當成不可見
                        continue
                    v = visibility(kb, mode=ev["mode"], target_user=ev["target_user"],
                                   vendor_id=ev["vendor_id"])
                    vis.append({"kb_id": kid, **v})
                row["expected_kb_id"] = ids
                row["expected_owner"] = exp.get("expected_owner")
                row["visibility"] = vis
                row["visibility_status"] = "COMPUTED"
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# 尺自證
# ---------------------------------------------------------------------------

#: 已知答案的真實資料列。⛔ 改這張表之前先確認 DB 現值，⛔ 不得為了讓測試變綠而改期望值。
_SELF_TEST_CASES = [
    # kb:3336 是 ts9885 的正解，business_types 不含 system_provider
    #   ⇒ b2b 業者結構上看不到（2026-09-01 血證，契約 §B③ 實例）
    (3336, {"mode": "b2b", "target_user": "property_manager", "vendor_id": 2},
     False, "business_types"),
    # kb:4217 業態＝system_provider、角色含 property_manager、vendor_ids 空陣列（全業者共用）
    #   ⇒ b2b 看得到（2026-09-02 實測命中，boosted 0.9596）
    (4217, {"mode": "b2b", "target_user": "property_manager", "vendor_id": 2},
     True, None),
    # 同一列換 b2c 租客：target_user 不含 tenant ⇒ 被角色軸擋下
    (4217, {"mode": "b2c", "target_user": "tenant", "vendor_id": 2},
     False, "target_user"),
]


def self_test() -> int:
    """⛔ 從沒紅過的健檢等於沒驗過——先證明這把尺看得見已知病灶。"""
    ok = True
    facets = load_facet_contracts()
    print(f"✅ ④ 面向設定讀到 {len(facets)} 個面向"
          f"（缺 grounding_scope.target_user 的："
          f"{sum(1 for f in facets.values() if f['grounding_target_user_missing'])} 個）")

    rows = fetch_kb_rows([c[0] for c in _SELF_TEST_CASES])
    for kid, ctx, want_visible, want_axis in _SELF_TEST_CASES:
        kb = rows.get(kid)
        if kb is None:
            print(f"⛔ kb:{kid} 查無此列——⛔ 尺無法自證（資料或查詢壞了）")
            ok = False
            continue
        got = visibility(kb, vendor_business_types=["system_provider"], **ctx)
        hit = (got["visible"] == want_visible
               and (want_axis is None or want_axis in got["blocked_by"]))
        label = "可見" if want_visible else f"不可見（{want_axis}）"
        print(f"{'✅' if hit else '⛔'} kb:{kid} × {ctx['mode']}/{ctx['target_user']}"
              f" 期望{label}，實得 visible={got['visible']} blocked_by={got['blocked_by']}")
        ok = ok and hit

    # ── 突變控制 ─────────────────────────────────────────────────────────
    # ⚠️ **第一版的控制組是錯的**（2026-09-02 自證當場抓到）：原本把資料的
    #    business_types 改成 NULL，期望翻成可見。但 b2b 本來就**沒有** IS NULL 放行，
    #    NULL 維持不可見是正確行為 ⇒ 那個控制組驗不到任何東西。
    #    母圖 §3 的錯法是改**謂詞**（多一個 IS NULL 放行），不是改資料。
    kb3336 = rows.get(3336)
    kb4217 = rows.get(4217)

    # C1：這把尺真的有在讀業態軸嗎——把已知可見那列的業態換掉，必須翻成不可見。
    if kb4217:
        mutated = dict(kb4217, business_types=["full_service"])
        got = visibility(mutated, mode="b2b", target_user="property_manager", vendor_id=2)
        flipped = got["visible"] is False and "business_types" in got["blocked_by"]
        print(f"{'✅' if flipped else '⛔'} 突變控制 C1：kb:4217 業態換成 full_service"
              f" ⇒ 期望翻成不可見，實得 visible={got['visible']} {got['blocked_by']}")
        ok = ok and flipped

    # C2：b2b 的「無 IS NULL 放行」是不是真的在**這把尺裡**起作用。
    #
    # ⚠️ **第一版的 C2 是假的**（2026-09-02 獨立驗證抓到）：它拿 kb:3336
    #    （business_types 非 NULL）跑 strict 臂，另一臂是函式內自己寫的
    #    `_wrong_doc_predicate`——**從來沒有把 NULL 那種列餵進 visibility()**。
    #    結果是：把母圖 §3 的錯法直接寫進 visibility() 的 b2b 分支，C2 仍然全綠。
    #    ⇒ 它量的是「retriever 與一個 local 常數」，不是這把尺。
    #    影響面不小：適格母體 773 列中有 253 列 business_types IS NULL，
    #    真發生此回歸會被整批誤判為 b2b 可見（V 類被當成 T／N）。
    #
    # 正確做法：直接把 business_types=NULL 的列餵進 visibility()，b2b 必須判不可見。
    _null_bt_row = {
        "id": -1, "is_active": True, "category": None,
        "business_types": None, "target_user": None, "vendor_ids": None,
        "keywords": ["x"], "has_embedding": True,
    }
    got_b2b = visibility(_null_bt_row, mode="b2b",
                         target_user="property_manager", vendor_id=2)
    strict_ok = got_b2b["visible"] is False and "business_types" in got_b2b["blocked_by"]
    print(f"{'✅' if strict_ok else '⛔'} 突變控制 C2：business_types=NULL 的列 × b2b"
          f" ⇒ 期望不可見（無 IS NULL 放行），實得 visible={got_b2b['visible']}"
          f" {got_b2b['blocked_by']}")
    ok = ok and strict_ok

    # C3：同一列換 b2c 必須翻成可見——證明擋它的是 b2b 的嚴格分支本身，
    #     ⛔ 而不是「這把尺對 NULL 業態一律說不」。
    got_b2c = visibility(_null_bt_row, mode="b2c", target_user="tenant",
                         vendor_id=2, vendor_business_types=["full_service"])
    b2c_ok = got_b2c["visible"] is True
    print(f"{'✅' if b2c_ok else '⛔'} 突變控制 C3：同一列 × b2c"
          f" ⇒ 期望可見（b2c 有 IS NULL 放行），實得 visible={got_b2c['visible']}"
          f" {got_b2c['blocked_by']}")
    ok = ok and b2c_ok

    print("\n結論：", "尺可用" if ok else "⛔ 尺是瞎的，本輪任何 ③ 結論作廢")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="回測輸出契約 §B③④ 報表層")
    ap.add_argument("--self-test", action="store_true",
                    help="用已知答案的真實資料列驗這把尺（⛔ 第一次用必跑）")
    ap.add_argument("--session-prefix", help="要併的那一輪 session_id 前綴")
    ap.add_argument("--frozen", help="契約 §A 凍結檔（expected_owner／expected_kb_id）")
    ap.add_argument("--out", help="輸出 JSON 路徑（預設印到 stdout）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.session_prefix:
        ap.error("需要 --session-prefix（或 --self-test）")

    facets = load_facet_contracts()
    events = fetch_events(args.session_prefix)
    if not events:
        raise DataError(
            f"session_id like '{args.session_prefix}%' 查無事件——"
            "⛔ 這是查不到，不是『那一輪沒有題目』"
        )
    frozen = None
    if args.frozen:
        with open(args.frozen, encoding="utf-8") as f:
            frozen = json.load(f)

    rows = enrich(events, facets, frozen)
    payload = json.dumps(rows, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"✅ {len(rows)} 列 → {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
