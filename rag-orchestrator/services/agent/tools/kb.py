"""`kb.get`／`kb.search` 工具（spec agentic-mcp-orchestration・任務 1.4）。

見 `.kiro/specs/agentic-mcp-orchestration/design.md` 元件 3 條件表。

**`kb.get`**：兩種 `kb_id`——`outline:*` 交 `outline_resolver`（任務 3.2 供給，
自有命名空間，⛔ 不查 `knowledge_base`）；純數字字串走 `fetch_visible_row`，
唯一可見性謂詞來自 `vendor_knowledge_retriever_v2.build_visibility_predicate`
（**不變量 20**：本檔 ⛔ 不得自行寫出 `vendor_ids`／`business_types` 字面條件，
只能拼該函式的回傳，理由與 `build_visibility_predicate` docstring 同——
單一謂詞來源，避免四份手抄各自漂移）。查無或落在池外（保留分類、跨業者、
跨角色…）⇒ 同一個 `NO_MATCH`，⛔ 不對模型區分「不存在」與「無權限」。
⚠️ 2026-09-07 起 `fetch_visible_row` 另有**第二道**閘門：內容已審謂詞
`services/agent/canon/review_state.py:content_reviewed_predicate`（spec
knowledge-outline-and-intent-architecture 任務 3.1，不變量 32）——未審列
同樣回那個 `NO_MATCH`。可見性與審核狀態是兩條獨立閘門，各有各的單一來源。

**`kb.search`**：薄包一層 `retriever.retrieve()`（含 reranker，照現況，
design 決策 7），只回摘要（`id`／`question_summary`／`similarity`），
⛔ 不回 `answer` 全文——避免模型繞過 `kb.get` 直接拿到完整答案內容，
`kb.search` 的用途是「找到後再用 kb.get 取用」，故其 provenance 一律
`citable=False`（DSP-029 r13 #5）。retriever 例外一律
`NO_MATCH`（design：fail-closed，⛔ 不降級到別的池／別的檢索路徑）。

**佔位符風格（⛔ 硬約束）**：`build_visibility_predicate` 回傳 psycopg2
`%s` 風格 SQL 片段，其 docstring 明寫「⛔ 不混用 `$n`」——因此
`fetch_visible_row` 走同步 psycopg2 連線（`db_pool.getconn()`／
`putconn()`，與既有 `services/db_utils.py` 慣例同構），⛔ 不用
asyncpg 的 `$1`／`fetchrow` 直接執行這段 SQL（會整段語法錯）。
"""
from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Optional, Union

from services.agent.canon.review_state import content_reviewed_predicate
from services.agent.identity import Identity
from services.agent.tools.registry import Provenance, ToolResult, ToolSpec
from services.decision_layer import DecisionConfig
from services.vendor_knowledge_retriever_v2 import build_visibility_predicate

OutlineResolver = Callable[[Identity, str], Union[ToolResult, Awaitable[ToolResult]]]

KB_GET_SPEC: ToolSpec = {
    "name": "kb.get",
    "description": "依 id 取回單一知識列的完整內容（整數 id）或大綱章節（outline:*）。",
    "input_schema": {
        "type": "object",
        "properties": {"kb_id": {"type": "string"}},
        "required": ["kb_id"],
        "additionalProperties": False,
    },
    "scope": "read",
    "stage": {"prospect": "M0", "property_manager": "M0", "tenant": "M0"},
}

KB_SEARCH_SPEC: ToolSpec = {
    "name": "kb.search",
    "description": "以查詢字串搜尋知識庫，回傳最多 k 筆摘要（不含答案全文）。",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["query", "k"],
        "additionalProperties": False,
    },
    "scope": "read",
    # prospect 缺鍵＝永不可見（design 決策 3：prospect 不用向量檢索）。
    "stage": {"property_manager": "M0", "tenant": "M0"},
}


def fetch_visible_row(db_pool, identity: Identity, kb_id: int) -> Optional[tuple]:
    """`SELECT id, question_summary, answer` 加**兩道**謂詞；查無回 `None`。

    回傳欄位順序固定為 `(id, question_summary, answer)`（與 SELECT 列表同序）。

    兩道謂詞各有各的單一來源，⛔ 不合併（spec
    knowledge-outline-and-intent-architecture 任務 3.1，票 D／R8.4）：

    1. **可見性**＝`build_visibility_predicate`（不變量 29）——這一列屬於
       哪個業者／業態／角色的池。
    2. **內容已審**＝`content_reviewed_predicate`（不變量 32）——這一列的
       內容有沒有人核可過。

    ⚠️ 兩者都是 fail-closed 的 AND：未審列一律回 `None` ⇒ `kb_get` 回同一個
    `NO_MATCH`（⛔ 不對模型區分「不存在」／「無權限」／「未審核」）。
    ⛔ 這裡**不包 try/except、不依欄位存在與否切換**——那是唯一會造成
    fail-open 的寫法；欄位不存在時 psycopg2 丟 `UndefinedColumn`，由
    `registry.py` 轉成 `NO_MATCH`（既有 fail-closed 路徑）。
    """
    predicate_sql, predicate_params = build_visibility_predicate(identity)
    reviewed_sql, reviewed_params = content_reviewed_predicate()
    sql = (
        "SELECT id, question_summary, answer FROM knowledge_base kb "
        f"WHERE kb.id = %s {predicate_sql}{reviewed_sql}"
    )
    params = [kb_id] + list(predicate_params) + list(reviewed_params)
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        return row
    finally:
        db_pool.putconn(conn)


async def kb_get(
    identity: Identity,
    args: dict,
    *,
    db_pool,
    outline_resolver: Optional[OutlineResolver] = None,
) -> ToolResult:
    kb_id = args.get("kb_id")
    if not isinstance(kb_id, str):
        return ToolResult(ok=False, error="INVALID_INPUT")

    if kb_id.startswith("outline:"):
        if outline_resolver is None:
            return ToolResult(ok=False, error="NO_MATCH")
        result = outline_resolver(identity, kb_id)
        if inspect.isawaitable(result):
            result = await result
        return result

    if not kb_id.isdigit():
        return ToolResult(ok=False, error="INVALID_INPUT")

    row = fetch_visible_row(db_pool, identity, int(kb_id))
    if row is None:
        return ToolResult(ok=False, error="NO_MATCH")

    row_id, question_summary, answer = row
    return ToolResult(
        ok=True,
        data={"id": row_id, "question_summary": question_summary, "answer": answer},
        provenance=[Provenance(source=f"kb:{row_id}", text=answer, citable=True)],
        text_for_model=answer,
    )


async def kb_search(
    identity: Identity,
    args: dict,
    *,
    retriever,
    threshold: Optional[float] = None,
) -> ToolResult:
    query = args.get("query")
    k = args.get("k")
    if not isinstance(query, str) or not isinstance(k, int) or isinstance(k, bool):
        return ToolResult(ok=False, error="INVALID_INPUT")
    if not (1 <= k <= 5):
        return ToolResult(ok=False, error="INVALID_INPUT")

    effective_threshold = (
        threshold if threshold is not None else DecisionConfig.load().kb_threshold
    )

    try:
        results = await retriever.retrieve(
            query,
            vendor_id=identity.vendor_id,
            top_k=k,
            similarity_threshold=effective_threshold,
            target_user=identity.target_user,
            mode=identity.mode,
        )
    except Exception:  # noqa: BLE001 — fail-closed（design：⛔ 不降級到別的池）
        return ToolResult(ok=False, error="NO_MATCH")

    if not results:
        return ToolResult(ok=False, error="NO_MATCH")

    items = [
        {
            "id": r.get("id"),
            "question_summary": r.get("question_summary"),
            "similarity": r.get("similarity"),
        }
        for r in results
    ]
    # DSP-029 r13 #5：`kb.search` 的 provenance 一律 `citable=False`——它回的是
    # **摘要**（`question_summary`），只用來導航「找到後再 kb.get 取用」。
    # ⚠️ 摘要是可引用的話，模型就能拿一行關鍵字串當事實依據，繞過 `kb.get` 的
    # 完整答案；DSP-029 把引文改成由系統從 provenance 解析之後這個出口更順手
    # （摘要短、覆蓋門檻容易過），故在來源端關掉。
    provenance = [
        Provenance(source=f"kb:{it['id']}", text=it["question_summary"] or "", citable=False)
        for it in items
    ]
    text_for_model = "\n".join(
        f"{i + 1}. {it['question_summary']}" for i, it in enumerate(items)
    )
    return ToolResult(
        ok=True,
        data={"items": items},
        provenance=provenance,
        text_for_model=text_for_model,
    )
