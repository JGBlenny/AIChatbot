# -*- coding: utf-8 -*-
"""知識列可見性謂詞——**唯一正本**。

⚠️ 2026-09-11：本模組自 `scripts/backtest/contract_enrich.py` 抽出。
該檔隨回測 harness 於 `36e24651` 刪除，但 `visibility()` **不是回測附屬品**：
- `.claude/DECISIONS.md` 的 **DSP-002（業主 2026-09-02 已裁）** 以它為判準；
- `.claude/skills/retrieval-improvement-loop/` 明訂「可見性必須用它，⛔ 不得用 `_B2B` 代替」；
- `scripts/audit/kb_vs_helpcenter.py`、`scripts/status.py` 的註解同樣指向它。

⛔ **刪掉它等於用刪檔單方面消解一條已登記的業主裁決**——故獨立保留。

⚠️ **b2b 業態過濾是 `business_types && ARRAY['system_provider']`、⛔ 無 `IS NULL` 放行**。
補上 `IS NULL` 會打穿刻意設計的跨業者隔離（專案既有鐵則）。

⛔ 本檔只保留謂詞，⛔ 不含原檔的 psql／enrich／self_test——那些是回測流程，已隨回測退役。
"""
from __future__ import annotations


KNOWN_TARGET_USERS = {"tenant", "landlord", "property_manager", "system_admin", "prospect"}

#: 對齊 `SYSTEM_DOC_CATEGORY` / `RULES_DOC_CATEGORY`——這兩類是系統注入用文件，
#: 檢索一律排除，永不被當答案回傳。
EXCLUDED_CATEGORIES = {"系統脈絡", "對話規則"}

#: b2b 的業態值（retriever 在 b2b 分支寫死）。
B2B_BUSINESS_TYPES = ["system_provider"]


FILTER_COLUMNS_VECTOR = frozenset({
    "vendor_ids", "embedding", "is_active", "category", "business_types", "target_user",
})
FILTER_COLUMNS_KEYWORD = frozenset({
    "vendor_ids", "is_active", "category", "keywords", "business_types", "target_user",
})



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
