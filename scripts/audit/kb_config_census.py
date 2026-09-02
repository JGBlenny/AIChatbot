#!/usr/bin/env python3
"""知識庫設定欄位盤查（唯讀，⛔ 一筆都不改）。

## 為什麼

2026-09-02：一題失敗一路追進去，才碰巧發現 34 筆平台操作知識的
`business_types` 被標成租屋業知識 ⇒ 業者結構上搜不到。
**沒有人知道還有幾筆這樣。** 這支把全庫的設定欄位一次查完，列出疑似設錯的。

## ⛔ 紀律

```text
⛔ 一筆都不改，只列
⛔ 應然規則從**程式**推導（retriever 的過濾邏輯、面向設定的載入），⛔ 不從文件
⚠️ 「疑似」就是疑似——詞面訊號會誤判，⛔ 不得直接當成缺陷清單去改
⚠️ 否定結論（某類 0 筆）必須有正對照組，見 --self-test
```

## 六項檢查

```text
C1 業態疑似標錯（平台）   內容講平台操作，卻不含 system_provider ⇒ 業者搜不到
C2 業態疑似標錯（租屋業） 內容是租客生活建議，卻含 system_provider ⇒ 污染業者池
C3 categories 空          面向進場對它靜默失效
C4 target_user 值域       非可信角色集合的值（retriever 會靜默正規化成 tenant）
C5 vendor_ids 非空        業者專屬知識（跨業者隔離的例外）
C6 instance_applicability 缺宣告（不變量 10 的母體）
```

## 跑法

    python3 scripts/audit/kb_config_census.py --self-test
    python3 scripts/audit/kb_config_census.py            # 全庫適格母體
    python3 scripts/audit/kb_config_census.py --samples 5
"""
import argparse
import json
import subprocess
import sys

PG = "aichatbot-postgres"

#: ⛔ 與 `scripts/status.py` 的 ELIGIBLE 同一式——適格母體＝active 扣設定列與空 answer 錨點。
ELIGIBLE = ("is_active AND COALESCE(category,'') NOT IN ('系統脈絡','對話規則') "
            "AND id <> 4253 AND answer IS NOT NULL AND btrim(answer) <> ''")

#: 對齊 `VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS`（⛔ 不各自定義）。
KNOWN_TARGET_USERS = ("tenant", "landlord", "property_manager", "system_admin", "prospect")

#: 平台操作的詞面訊號（⚠️ 訊號不是判定）。取自實際誤標樣本 3327-3360 的共同語彙。
PLATFORM_RE = r"團隊設定|團隊資訊|團隊管理|後台|收款設置|合約總表|帳單總表|物件總表|進階設定|批次匯入|排定發送|系統會自動|點選「|至「|進入【"
#: 租客生活建議的詞面訊號（第二人稱對租客說話）。
TENANT_RE = r"您的管理師|聯繫管理師|作為房客|作為租客|您可以享有|建議您向|您有權"


class DataError(RuntimeError):
    """查不到該有的資料——⚠️ 大聲失敗，⛔ 不得靜默回 0 筆。"""


def psql(sql: str) -> str:
    r = subprocess.run(["docker", "exec", PG, "psql", "-U", "aichatbot",
                        "-d", "aichatbot_admin", "-tAc", sql],
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise DataError(f"psql 失敗：{r.stderr.strip()}")
    return r.stdout.strip()


def rows(sql: str) -> list:
    out = psql("select coalesce(json_agg(row_to_json(t)),'[]'::json) from (" + sql + ") t")
    return json.loads(out or "[]")


CHECKS = {
    "C1 業態疑似標錯：內容像平台操作，卻不含 system_provider（業者搜不到）": f"""
        select id, question_summary, coalesce(source,'-') source,
               coalesce(array_to_string(business_types,','),'(NULL)') bt
        from knowledge_base
        where {ELIGIBLE}
          and not (business_types && ARRAY['system_provider'])
          and answer ~ '{PLATFORM_RE}'
        order by id""",

    "C2 業態疑似標錯：內容像租客生活建議，卻含 system_provider（污染業者池）": f"""
        select id, question_summary, coalesce(source,'-') source,
               coalesce(array_to_string(business_types,','),'(NULL)') bt
        from knowledge_base
        where {ELIGIBLE}
          and business_types && ARRAY['system_provider']
          and answer ~ '{TENANT_RE}'
        order by id""",

    "C3 categories 空（面向進場對它靜默失效）": f"""
        select id, question_summary, coalesce(array_to_string(business_types,','),'(NULL)') bt
        from knowledge_base
        where {ELIGIBLE} and (categories is null or cardinality(categories) = 0)
        order by id""",

    "C4 target_user 含不可信角色（retriever 會靜默正規化成 tenant）": f"""
        select id, question_summary, array_to_string(target_user,',') tu
        from knowledge_base
        where {ELIGIBLE} and target_user is not null
          and exists (select 1 from unnest(target_user) u
                      where u not in {KNOWN_TARGET_USERS} and u <> 'all_users')
        order by id""",

    "C5 vendor_ids 非空（業者專屬，跨業者隔離的例外）": f"""
        select id, question_summary, array_to_string(vendor_ids,',') vi
        from knowledge_base
        where {ELIGIBLE} and array_length(vendor_ids, 1) is not null
        order by id""",

    "C6 缺 instance_applicability 宣告（不變量 10 的母體）": f"""
        select id, question_summary,
               coalesce(generation_metadata->>'instance_applicability','(未設)') ia
        from knowledge_base
        where {ELIGIBLE} and generation_metadata->>'instance_applicability' is null
        order by id""",
}


def self_test() -> int:
    """⛔ 先證明查詢管線沒壞，再拿它下否定結論。"""
    ok = True
    n = int(psql(f"select count(*) from knowledge_base where {ELIGIBLE}"))
    print(f"{'✅' if n > 500 else '⛔'} 適格母體 = {n}（正對照：應為數百筆，與 status.py 同式）")
    ok = ok and n > 500

    # 正對照：已知必然命中的一筆（3358 內容含「團隊設定」）
    hit = int(psql(f"select count(*) from knowledge_base where id=3358 and answer ~ '{PLATFORM_RE}'"))
    print(f"{'✅' if hit == 1 else '⛔'} 平台訊號正對照：kb3358 命中 = {hit}（應為 1）")
    ok = ok and hit == 1

    # 正對照：已知必然命中的租客訊號（3084 含「作為房客」）
    hit2 = int(psql(f"select count(*) from knowledge_base where id=3084 and answer ~ '{TENANT_RE}'"))
    print(f"{'✅' if hit2 == 1 else '⛔'} 租客訊號正對照：kb3084 命中 = {hit2}（應為 1）")
    ok = ok and hit2 == 1

    # 負對照：不存在的詞面應命中 0
    miss = int(psql(f"select count(*) from knowledge_base where {ELIGIBLE} and answer ~ 'zzqq無此詞面9f3k'"))
    print(f"{'✅' if miss == 0 else '⛔'} 負對照：不存在的詞面命中 = {miss}（應為 0）")
    ok = ok and miss == 0

    print("\n結論：", "查詢管線可用" if ok else "⛔ 管線壞了，本輪任何『幾筆』都不可信")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="知識庫設定欄位盤查（唯讀）")
    ap.add_argument("--self-test", action="store_true", help="⛔ 第一次用必跑")
    ap.add_argument("--samples", type=int, default=3, help="每項印幾筆樣本")
    ap.add_argument("--out", help="輸出 JSON")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    total = int(psql(f"select count(*) from knowledge_base where {ELIGIBLE}"))
    print(f"適格母體 {total} 筆（active 扣設定列與空 answer 錨點）\n")

    result = {"eligible_total": total, "checks": {}}
    for name, sql in CHECKS.items():
        got = rows(sql)
        result["checks"][name] = {"count": len(got), "ids": [r["id"] for r in got]}
        pct = f"{100*len(got)/total:.1f}%" if total else "-"
        print(f"■ {name}\n   {len(got)} 筆（{pct}）")
        for r in got[:a.samples]:
            extra = " ".join(f"{k}={v}" for k, v in r.items() if k not in ("id", "question_summary"))
            print(f"     {r['id']}  {(r.get('question_summary') or '')[:34]:36} {extra}")
        print()

    if a.out:
        json.dump(result, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"→ {a.out}")
    print("⚠️ 「疑似」就是疑似——詞面訊號會誤判。⛔ 不得直接當缺陷清單去改。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
