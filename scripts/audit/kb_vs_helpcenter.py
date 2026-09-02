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

#: ⛔ **b2b 答題母體**（⛔ **不是**「可見」）——與 `scripts/status.py` 的 `_B2B` 逐條同源。
#: ⚠️ 它 = 「業態／角色／類別過濾 ∧ answer 非空」，**沒有** embedding／keywords／vendor_ids
#:   任何一條 ⇒ ⛔ 不模型任何一條檢索路。retriever 實撈：向量路 354／詞面路 320。
#:   今天它恰好等於「向量路 ∧ answer」是**資料巧合**（池內 embedding 恰好全非空）。
#: ⚠️ 本檔 `--b2b` 初版少了 `target_user` 與 `id <> 4253` ⇒ 母體 320（正本 **293**）；
#: 而我同一天還用過另外兩種寫法（381／772）⇒ **一天四個母體、四組數字，沒有一次對齊**。
#: ⛔ **報數字**用的母體只能有一份：改這裡之前先改 `status.py`，再同步過來。
#: ⛔ 但 ⛔ 不得拿本常數當可見性——那要用 `contract_enrich.visibility()`（兩路分開報）。
B2B_VISIBLE = ("is_active AND business_types && ARRAY['system_provider']::text[] "
               "AND (target_user IS NULL OR 'property_manager' = ANY(target_user)) "
               "AND COALESCE(category,'') NOT IN ('系統脈絡','對話規則') AND id <> 4253 "
               "AND answer IS NOT NULL AND btrim(answer) <> ''")

#: 一律排除的頁面（部落格／行銷文，⛔ 不是產品規格來源）
_BLOG = re.compile(r"esg|beike|sea-internet|rentallaw|propmarket|law", re.I)

#: 抓「有單位的數字」——純數字誤報太多（條列編號、id）。
#: ⚠️ **邊界必須吃完整數字**（含小數點與千分位），否則會從「1.6%」切出「6%」、
#: 從「20,000 元」切出「000 元」當成獨立主張（2026-09-02 代理實測各抓到一例）。
#: `(?<![\d.,])` 確保左邊不是數字/小數點/逗號。
_NUM = re.compile(
    r"(?<![\d.,])(\d{1,2}:\d{2}|\d[\d,]*(?:\.\d+)?\s*(?:小時|分鐘|天|日|個月|年|次|筆|元|%|％|MB|GB|碼|位))")

#: ⚠️ 這些詞之後的數值是**示意值不是事實主張**（例如／舉例／設為…）⇒ 降級不比對。
_ILLUSTRATIVE = re.compile(r"(例如|舉例|如：|設為|常見是|假設|比方)")


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


def _tokenize(text: str) -> list:
    """中文斷詞。

    ⚠️ **初版是壞的**（2026-09-02 全庫首跑當場發現）：用 `[一-鿿]{2,6}` 正則，
    對連續中文會**貪婪切出固定長度的窗**——實際產出如 `租客收不到通`、`合約簽署分兩`、
    `房東建立點交`，那些**不是詞**，在官方頁面裡當然找不到。
    後果：320 筆裡 216 筆（67.5%）被判 `NO_MATCHING_PAGE`，
    ⛔ 而那是工具的錯，不是「官方沒寫」。差一點就把 216 筆丟給代理去查一個假問題。

    ⇒ 改用 jieba（容器內已有 0.42.1）。⚠️ host 沒裝 ⇒ 走 `docker exec` 借用。
    """
    return _tokenize_batch([text])[0]


#: 批次斷詞的分隔符——⚠️ 必須是不會出現在知識內容裡的字串。
_SEP = "\x1e@@KBSEP@@\x1e"


def _tokenize_batch(texts: list) -> list:
    """一次把所有文字送進容器斷詞。

    ⚠️ **為什麼是批次**：逐筆 `docker exec` 每次約 0.8 秒，320 筆跑超過 10 分鐘而逾時。
    ⛔ 不是把逾時調長就好——那只是把等待藏起來。
    """
    if not texts:
        return []
    payload = _SEP.join(texts)
    script = (
        "import sys,jieba\n"
        f"SEP={_SEP!r}\n"
        "parts=sys.stdin.read().split(SEP)\n"
        "print(SEP.join(' '.join(jieba.cut(p)) for p in parts), end='')\n"
    )
    out = subprocess.run(
        ["docker", "exec", "-i", "aichatbot-rag-orchestrator", "python3", "-c", script],
        input=payload, capture_output=True, text=True, timeout=600)
    if out.returncode:
        raise SourceError(f"斷詞失敗（容器內 jieba）：{out.stderr.strip()[:200]}")
    got = out.stdout.split(_SEP)
    if len(got) != len(texts):
        # ⚠️ 大聲失敗：分隔符若被內容撞到，對位會整批錯，⛔ 不得靜默截斷
        raise SourceError(f"斷詞回傳段數不符：送 {len(texts)} 段、回 {len(got)} 段")
    return [[t for t in seg.split(" ") if t.strip()] for seg in got]


def key_terms_from_tokens(toks: list, top: int = 6) -> list:
    """從已斷好的詞取最有辨識度的幾個——用來在官方頁面裡定位同主題段落。"""
    toks = [t for t in toks
            if (len(t) >= 2 and re.fullmatch(r"[一-鿿]+", t))
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9]{2,}", t)]
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


def _norm(v: str) -> str:
    """比對用正規化：去空白。

    ⚠️ HC **同一份文件裡**「30天」與「30 天」混用，知識固定寫「30 天」
    ⇒ 不正規化會把明明寫著的值判成查無（2026-09-02 代理實測 kb3848 即是）。
    """
    return re.sub(r"\s+", "", v)


def numbers_with_context(text: str, width: int = 45) -> list:
    out = []
    for m in _NUM.finditer(text):
        s = max(0, m.start() - width)
        ctx = text[s:m.end() + width].strip()
        # ⚠️ 示意值（例如／舉例／設為…之後）⛔ 不是事實主張，不納入比對
        lead = text[max(0, m.start() - 12):m.start()]
        if _ILLUSTRATIVE.search(lead):
            continue
        out.append((m.group(0), ctx))
    return out


#: 全語料的數值集合（正規化後）——只算一次。
_CORPUS_NUMS: set = set()


def _corpus_numbers(corpus: list) -> set:
    """官方 84 篇的所有數值（正規化後）。⚠️ 全掃，⛔ 不限 top-3。"""
    global _CORPUS_NUMS
    if not _CORPUS_NUMS:
        for _b, _t, body in corpus:
            _CORPUS_NUMS |= {_norm(n) for n, _ in numbers_with_context(body)}
        if not _CORPUS_NUMS:
            raise SourceError("官方語料抽不到任何數值——解析壞了，⛔ 不得靜默通過")
    return _CORPUS_NUMS



def audit_row(row: dict, corpus: list, toks: list) -> dict:
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
    terms = key_terms_from_tokens(toks)
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
    # ⚠️ **數值查證用全語料，⛔ 不沿用檢索的 top-3**（2026-09-02 代理實測）：
    #    kb4053 的「4 天」白紙黑字在 billexpired 頁，但 top-3 選到的是別的頁；
    #    kb3484 的「72 小時」在 slug13/48/73，top-3 一個都沒選到。
    #    ⇒ 定位頁面用檢索（給人看上下文），**判有沒有這個值用全掃**。
    # ⚠️ **⛔ 機械層不做抑制，只給兩個訊號**（2026-09-02 兩次過頭後的定案）：
    #   只看 top-3      ⇒ 假陽性 71%（值寫在別頁就誤報）
    #   改看全語料      ⇒ 假**陰**性：某無關頁剛好有那個數字就把真衝突吞掉（實測吞 4 筆）
    #   剝數字查 jgb2   ⇒ 「7 天」變 grep `7`，整個 codebase 都中 ⇒ 38 筆全吞
    # ⇒ 字串比對**分不出「這頁在講永豐 7 天」與「別頁剛好提到 7 天」**——那需要語義。
    #   定案：判定沿用 top-3（保召回），另附 `found_in` 讓代理**一眼刷掉**假陽性。
    #   ⛔ 機械層只是粗篩，⛔ 不是判定。
    top = pages[:3]
    top_nums = set()
    for _, _b, _t, body, _h in top:
        top_nums |= {_norm(n) for n, _ in numbers_with_context(body)}
    conflicts = []
    for n, ctx in kb_nums:
        if _norm(n) in top_nums:
            continue
        elsewhere = [b for b, _t, body in corpus
                     if _norm(n) in {_norm(x) for x, _ in numbers_with_context(body)}]
        conflicts.append({"pages": [p[1] for p in top], "kb_value": n,
                          "kb_context": ctx[:110],
                          # ⚠️ 非空 ⇒ 這個值官方其他頁有寫，多半是假陽性（代理先刷這批）
                          "found_in": elsewhere[:3]})
    # ⚠️ 幫助中心查無 ⛔ 不等於憑空——**大量事實只存在於 jgb2 原始碼**
    #    （2026-09-02 代理實測：38 筆中 14 筆是這個成因）。
    # ⛔ **但機械層不做這個判斷**：程式碼寫的是 `+30 days`、`$verCodeExpireSec = 300`，
    #    與知識的「30 天」「5 分鐘」字面不同，機械比對必然失準。
    #    ⚠️ 我試過「剝成純數字去 grep」——「7 天」變成 grep `7`，整個 codebase 都中
    #    ⇒ NUMBER_MISMATCH 從 38 變 **0**，27 個誤報清掉的同時**11 個真問題也全被吞**。
    #    那是把假陽性換成假陰性，⛔ 比原本更糟。
    # ⇒ 定案：機械層只回報「**官方幫助中心**查無」，jgb2 那一層**交代理判**（需要語義）。
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

    # ⛔ 斷詞自證：初版用正則貪婪切窗，產出「租客收不到通」這種**非詞**，
    #    導致全庫 320 筆裡 216 筆（67.5%）被誤判為 NO_MATCHING_PAGE。
    #    ⚠️ 差一點就把 216 筆假問題丟給代理去查。
    toks = _tokenize("合約點交流程 搬入：房東建立點交清單並發送給租客")
    good = [t for t in toks if t in ("合約", "點交", "流程", "搬入", "房東", "建立", "清單", "租客")]
    junk = [t for t in toks if len(t) >= 5 and re.fullmatch(r"[一-鿿]+", t)]
    tok_ok = len(good) >= 4 and not junk
    print(f"{'✅' if tok_ok else '⛔'} 斷詞自證：切出可用詞 {len(good)} 個"
          + (f"；⛔ 出現長度≥5 的可疑片段 {junk}" if junk else ""))
    ok = ok and tok_ok

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


#: 型別判定（機械）——⛔ 判準與 `rules/型別分批.md` 的「型別判定（機械）」節同源。
#:
#: ⚠️ **本工具跑全型，型別只是標記** ——⛔ 別在這裡加「非 T1 就跳過」的閘門。
#: 這行是被獨立驗證抓出來的：同一個 commit 裡曾殘留第二版的舊註解
#: 「本工具只對 T1 有效」，就掛在本常數上方，而那正是該 commit 要廢掉的規則
#: （它會讓 `kb3330` 這種**事實錯誤**因為型別是 T3 而被跳過）。
#: ⇒ 判「這筆是不是那題的正解」才分型（只有 T1）；判「內容有沒有講錯事實」不分型。
#: 詳見 `audit_row` 的說明與 `rules/正解判定.md` §零。
#:
#: ⚠️ **已知歧異（P2，尚未收斂）**：`scripts/status.py` 的 `print_b2b_surface`
#: 對「一列命中多個面向」用 `max(f.sel)`（字典序 ⇒ 取到非 api），本常數用
#: EXISTS 順序 ⇒ **api 優先**。全庫實測差 2 筆（kb3861／kb4216：本處 T2、status.py T3）。
#: ⛔ 兩者未同源之前，⛔ 不得把本工具的型別統計與 status.py 的相互引用。
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
        where = B2B_VISIBLE
    else:
        ap.error("需要 --ids 或 --b2b（或 --self-test）")

    rows = fetch(where)
    if not rows:
        raise SourceError(f"查無知識列（{where}）——⛔ 這是查不到，不是『沒有問題』")

    # ⚠️ 一次批次斷詞（逐筆 docker exec 320 筆會超過 10 分鐘）
    all_toks = _tokenize_batch(
        [f"{r.get('question_summary') or ''} {r.get('answer') or ''}" for r in rows])
    res = [audit_row(r, corpus, t) for r, t in zip(rows, all_toks)]
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
