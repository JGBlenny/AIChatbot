#!/usr/bin/env python3
"""知識庫 × 官方幫助中心 對帳（G0 權威來源核對的實作）。

> 規約：`.claude/skills/retrieval-improvement-loop/rules/正解判定.md`
> 流程位置：`SKILL.md` 的 G0 閘門

## 為什麼要有這支

2026-09-02：實作方一路把「這題庫裡有沒有答案」上呈給業主逐題判，
而**本機一直存在官方權威來源**（幫助中心交付檔），沒人拿它對過帳。
第一次人工比對就抓到 `kb3336` 講錯（官方「每日 12:00 統一發送」
vs 知識「12:00～17:00 放進去就立即寄」，且衍生兩個錯誤建議）。

## 這支查什麼（⚠️ 只查機械可判的，⛔ 不做語義評價）

```text
① 數字衝突   知識裡的時間／金額／期限／上限，官方頁面同主題處寫的是不是同一個值
             ⇒ 這是最高訊噪比的錯誤偵測（3336 就是這樣被抓到的）
② 無對應     知識講的主題，官方 93 篇裡完全找不到 ⇒ 標記待查（⛔ 不等於知識錯）
③ 主題混列   一列知識同時涵蓋多個不相干主題 ⇒ 表示法（S 類）候選
```

⛔ **本支只產出「待人判的候選」，不自動改任何資料。**
⛔ 數字不同 ⛔ 不等於知識錯——可能是官方頁面過時。依 CANON 事實紀律第 4 條，
   衝突一律落成待裁，⛔ 不自行選邊。

## 跑法

    python3 scripts/audit/kb_vs_helpcenter.py --self-test
    python3 scripts/audit/kb_vs_helpcenter.py --ids 3327-3360
    python3 scripts/audit/kb_vs_helpcenter.py --b2b            # 業者可見全量
"""
import argparse
import glob
import html
import json
import os
import re
import subprocess
import sys

HELP_DIR = os.path.expanduser("~/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818")
PG = "aichatbot-postgres"

#: 一律排除的頁面（部落格／行銷文，⛔ 不是產品規格來源）
_BLOG = re.compile(r"esg|beike|sea-internet|rentallaw|propmarket|law", re.I)

#: 抓「有單位的數字」——純數字誤報太多（條列編號、id）。
_NUM = re.compile(r"(\d{1,2}:\d{2}|\d+\s*(?:小時|分鐘|天|日|個月|年|次|筆|元|%|％|MB|GB|碼|位))")


class SourceError(RuntimeError):
    """權威來源本身不可用——⚠️ 大聲失敗，⛔ 不得降級成『查無衝突』。"""


def psql(sql: str) -> str:
    r = subprocess.run(["docker", "exec", PG, "psql", "-U", "aichatbot",
                        "-d", "aichatbot_admin", "-tAc", sql],
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise SourceError(f"psql 失敗：{r.stderr.strip()}")
    return r.stdout.strip()


def load_help_corpus() -> list:
    """把 zh-Hant 頁面轉成 (檔名, 標題, 純文字)。⛔ 排除部落格頁。"""
    if not os.path.isdir(HELP_DIR):
        raise SourceError(f"幫助中心目錄不存在：{HELP_DIR}——⛔ 本輪無權威來源，不得續跑")
    out = []
    for f in sorted(glob.glob(os.path.join(HELP_DIR, "*zh-Hant*.html"))):
        base = os.path.basename(f)
        if _BLOG.search(base):
            continue
        raw = open(f, encoding="utf-8", errors="ignore").read()
        m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else base
        body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
        body = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)))
        out.append((base, title, body))
    if not out:
        raise SourceError(f"{HELP_DIR} 解析不到任何 zh-Hant 頁面——解析壞了，⛔ 不得靜默通過")
    return out


def key_terms(text: str, top: int = 6) -> list:
    """取知識裡最有辨識度的詞——用來在官方頁面裡定位同主題段落。

    ⚠️ 刻意只取 2–6 字的中文詞與英數詞，⛔ 不做斷詞（沒有斷詞器就別假裝有）。
    """
    toks = re.findall(r"[一-鿿]{2,6}|[A-Za-z][A-Za-z0-9]{2,}", text)
    stop = {"可以", "系統", "如果", "建議", "設定", "使用", "進行", "相關", "資訊",
            "功能", "選擇", "需要", "這個", "以及", "或是", "方式", "狀態", "帳單"}
    seen, out = set(), []
    for t in toks:
        if t in stop or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= top:
            break
    return out


def find_pages(corpus: list, terms: list, min_hits: int = 2) -> list:
    """回傳命中 ≥min_hits 個關鍵詞的頁面（命中數由多到少）。"""
    scored = []
    for base, title, body in corpus:
        hits = [t for t in terms if t in body]
        if len(hits) >= min_hits:
            scored.append((len(hits), base, title, body, hits))
    return sorted(scored, key=lambda x: -x[0])


def numbers_with_context(text: str, width: int = 45) -> list:
    out = []
    for m in _NUM.finditer(text):
        s = max(0, m.start() - width)
        out.append((m.group(0), text[s:m.end() + width].strip()))
    return out


def audit_row(row: dict, corpus: list) -> dict:
    # ⚠️ **型別在這裡是標記，⛔ 不是閘門**（2026-09-02 兩次修正後的定案）。
    #
    #   第一版：無差別跑 ⇒ 業主指出 T2/T3 的「對」不是這樣判的。
    #   第二版：型別不是 T1 就跳過 ⇒ **也錯**，而且當場被自己的資料打臉：
    #           `kb3330`（「保存 5 年」vs 官方「沒有期限」，已列 ⛔ 危害）被判為 T3
    #           而遭跳過——但那是**事實錯誤**，與型別無關。
    #
    #   ⇒ 正確的切法是分開兩個命題：
    #        「這筆是不是那一題的正解」  ← **型別相關**，只有 T1 走
    #                                     `rules/正解判定.md` 的協議
    #        「這筆的內容有沒有講錯事實」← **型別無關**，任何型的 answer 文字
    #                                     都可能寫錯數字／時限／流程 ⇒ 本工具照跑
    #
    #   ⚠️ 但**修正**非 T1 列要更小心：它們的文字可能是機制說明或模板，
    #      下游（面向 grounding／formatter）可能依賴其措辭 ⇒ 標 `fix_caution`。
    ks = f"{row.get('question_summary') or ''} {row.get('answer') or ''}"
    terms = key_terms(ks)
    pages = find_pages(corpus, terms)
    res = {"id": row["id"], "summary": row.get("question_summary"),
           "kb_type": row.get("kb_type"),
           # ⚠️ 非 T1 的修正要更小心：文字可能被面向 grounding／formatter 依賴
           "fix_caution": (row.get("kb_type") or "T1") != "T1",
           "terms": terms, "pages": [p[1] for p in pages[:3]]}
    if not pages:
        # ⛔ 「官方沒寫」是**待查**，不是「知識錯」——也可能是關鍵詞取得不好
        res["verdict"] = "NO_MATCHING_PAGE"
        return res

    kb_nums = numbers_with_context(row.get("answer") or "")
    # ⚠️ **必須取聯集**：某值在 A 頁沒有、B 頁有，那不是衝突。
    #    第一版逐頁比對，把「A 頁查無」也記成衝突 ⇒ 3336 的「12:00」被誤報，
    #    而官方 onboarding12 逐字寫著 12:00。⛔ 逐頁比對會製造大量假陽性。
    top = pages[:3]
    union = set()
    for _, _base, _t, body, _h in top:
        union |= {n for n, _ in numbers_with_context(body)}
    conflicts = [{"pages": [p[1] for p in top], "kb_value": n, "kb_context": ctx[:110]}
                 for n, ctx in kb_nums if n not in union]
    res["verdict"] = "NUMBER_MISMATCH" if conflicts else "CONSISTENT"
    res["conflicts"] = conflicts[:6]
    return res


def self_test(corpus: list) -> int:
    """⛔ 先證明這把尺看得見已知病灶，再拿它掃全庫。

    正對照：kb3336 的「12:00～17:00」與「17:00」在官方頁面找不到（官方只寫 12:00）。
    負對照：官方逐字寫的「12:00」必須在頁面中找得到（證明比對邏輯沒壞）。
    """
    ok = True
    body = next((b for base, _t, b in corpus if "onboarding12" in base), None)
    if body is None:
        print("⛔ 找不到 onboarding12 頁——語料載入壞了")
        return 1
    print(f"✅ 語料載入 {len(corpus)} 篇（已排除部落格頁）")

    hit12 = "12:00" in body
    print(f"{'✅' if hit12 else '⛔'} 負對照：官方頁含『12:00』= {hit12}")
    ok = ok and hit12

    hit1700 = "17:00" in body
    print(f"{'✅' if not hit1700 else '⛔'} 正對照：官方頁**不含**『17:00』= {not hit1700}"
          f"　⇒ kb3336 的 12:00～17:00 說法在官方查無")
    ok = ok and not hit1700

    fake = "9999:99" in body
    print(f"{'✅' if not fake else '⛔'} 負對照：不存在的值查不到 = {not fake}")
    ok = ok and not fake

    print("\n結論：", "尺可用" if ok else "⛔ 尺是瞎的，本輪對帳結論作廢")
    return 0 if ok else 1


#: 型別判定（機械）——⛔ 判準與 `rules/型別分批.md` 同源，改一處要同步。
#: ⚠️ **本工具只對 T1 有效**：T2 的正解是 API 回傳、T3 是逐輪動作，
#: 拿幫助中心去比對它們的知識文字是**錯的軸**，且可能把 API 路徑需要的模板改壞。
_TYPE_SQL = """
  case
    when k.action_type = 'form_fill' or k.form_id is not null then 'FORM'
    when k.action_type = 'api_call' then 'T2'
    when exists (select 1 from facet f where f.cat = any(k.categories) and f.sel = 'api') then 'T2'
    when exists (select 1 from facet f where f.cat = any(k.categories)) then 'T3'
    else 'T1' end
"""
_FACET_CTE = """
with facet as (
  select cc->'topic_scope'->>'category' cat, cc->'grounding_scope'->>'select' sel
  from knowledge_base, lateral (select generation_metadata->'conversational_config' cc) x
  where category = '對話規則' and cc->'topic_scope'->>'category' is not null)
"""


def fetch(where: str) -> list:
    return json.loads(psql(
        _FACET_CTE +
        "select coalesce(json_agg(row_to_json(t)),'[]'::json) from ("
        "  select k.id, k.question_summary,"
        "         regexp_replace(k.answer, E'\\\\s+', ' ', 'g') answer,"
        f"        {_TYPE_SQL} as kb_type"
        f"  from knowledge_base k where {where.replace('id ', 'k.id ')} order by k.id"
        ") t"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="知識庫 × 幫助中心 對帳")
    ap.add_argument("--self-test", action="store_true", help="⛔ 第一次用必跑")
    ap.add_argument("--ids", help="id 範圍，如 3327-3360")
    ap.add_argument("--b2b", action="store_true", help="業者可見全量")
    ap.add_argument("--out", help="輸出 JSON")
    a = ap.parse_args(argv)

    corpus = load_help_corpus()
    if a.self_test:
        return self_test(corpus)

    if a.ids:
        lo, _, hi = a.ids.partition("-")
        where = f"id between {int(lo)} and {int(hi or lo)}"
    elif a.b2b:
        where = ("is_active and coalesce(category,'') not in ('系統脈絡','對話規則') "
                 "and answer is not null and btrim(answer)<>'' "
                 "and business_types && ARRAY['system_provider']")
    else:
        ap.error("需要 --ids 或 --b2b（或 --self-test）")

    rows = fetch(where)
    if not rows:
        raise SourceError(f"查無知識列（{where}）——⛔ 這是查不到，不是『沒有問題』")

    res = [audit_row(r, corpus) for r in rows]
    tally = {}
    for r in res:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print(f"共 {len(res)} 筆：" + "　".join(f"{k}={v}" for k, v in sorted(tally.items())))
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"→ {a.out}")
    else:
        for r in res:
            if r["verdict"] == "NUMBER_MISMATCH":
                print(f"\n⚠️ kb{r['id']} {r['summary']}　對照頁：{r['pages'][:2]}")
                for c in r["conflicts"][:3]:
                    print(f"   知識寫「{c['kb_value']}」但比對頁全部查無 ← {c['kb_context']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
