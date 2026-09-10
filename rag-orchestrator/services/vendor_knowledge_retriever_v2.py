"""
業者知識庫檢索服務 V2 - 統一架構版本
繼承 BaseRetriever，使用統一的檢索策略
Date: 2026-02-11
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
from .base_retriever import BaseRetriever
from .vendor_parameter_resolver import VendorParameterResolver as VendorParamResolver
from .retrieval_types import make_default_result
from .agent.identity import Identity


class VendorKnowledgeRetrieverV2(BaseRetriever):
    """業者知識庫檢索器 - 統一架構版本"""

    # 可信 target_user 角色（對齊 target_user_config + 售前 prospect）。
    # 非此集合（None / 空字串 / 未知角色）一律正規化為 tenant（最公開、最小權限的安全預設）。
    KNOWN_TARGET_USERS = {'tenant', 'landlord', 'property_manager', 'system_admin', 'prospect'}

    # 保留分類：掛此 category 的列為「系統注入用文件」（系統脈絡 md / 對話規則），
    # 一律排除於檢索之外，永不被當答案回傳（決策 11 / R19）。
    SYSTEM_DOC_CATEGORY = '系統脈絡'
    RULES_DOC_CATEGORY = '對話規則'

    @classmethod
    def _effective_target_user(cls, target_user) -> str:
        """將任意 target_user 輸入正規化為可信角色；非可信（None/空/未知）→ tenant。"""
        if isinstance(target_user, list):
            target_user = target_user[0] if target_user else None
        return target_user if target_user in cls.KNOWN_TARGET_USERS else 'tenant'

    def __init__(self):
        """初始化知識庫檢索器"""
        super().__init__()  # 調用基類初始化

        # 參數解析器
        self.param_resolver = VendorParamResolver()

        print("ℹ️  知識庫檢索器 V2 已初始化（支援關鍵字備選）")

    async def _vector_search(
        self,
        query_embedding: List[float],
        vendor_id: int,
        top_k: int,
        similarity_threshold: float,
        **kwargs
    ) -> List[Dict]:
        """
        知識庫向量檢索

        - SQL 不在 WHERE 端用 `>= threshold` 過濾（保留低分候選供 debug 顯示）
        - SELECT alias 為 `as vector_similarity`（純向量分數）
        - LIMIT 預設 20（可由 kwargs['vector_limit'] 覆寫）
        """
        # 獲取額外參數
        target_user = kwargs.get('target_user', 'tenant')
        mode = kwargs.get('mode', 'b2c')
        vector_limit = kwargs.get('vector_limit', 20)

        # 可見性隔離：業者／業態／角色／保留分類／is_active ——
        # ⛔ **不在此內嵌字面 SQL**，一律取自單一來源 build_visibility_predicate（不變量 20）。
        # ⚠️ `embedding IS NOT NULL` 是本路徑自己的相關性條件，故留在下方 WHERE。
        visibility_sql, visibility_params = build_visibility_predicate(
            Identity(vendor_id=vendor_id, target_user=target_user, mode=mode),
            param_resolver=self.param_resolver,
        )

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            vector_str = str(query_embedding)

            # 建構 SQL 查詢（不在 SQL 端 threshold 過濾）
            sql_query = f"""
                SELECT
                    kb.id,
                    kb.question_summary,
                    kb.answer,
                    kb.scope,
                    kb.priority,
                    kb.vendor_ids,
                    kb.business_types,
                    kb.target_user,
                    kb.keywords,
                    kb.video_url,
                    kb.form_id,
                    kb.action_type,
                    kb.api_config,
                    kb.category,
                    kb.categories,
                    -- ⚠️ **routing authority 的 transport 欄位**（A03 逼出，業主裁定 2026-08-29）：
                    --    P1f 的 gate 讀 knowledge applicability 宣告來決定是否抑制面向進場，
                    --    但本 projection 過去**沒有帶出它** ⇒ gate 一律讀到 UNKNOWN、一律 suppress。
                    --    contract 已存在、consumer 已接線，斷的是 **transport shape**。
                    -- ⚠️ 這**不是第二份 authority source**：唯一權威仍是
                    --    `knowledge_base.generation_metadata.instance_applicability`，
                    --    此處只是 projection ⇒ 無 cache 與 DB truth 不一致的問題。
                    -- ⛔ **只帶這一個最小欄位，不帶整包 generation_metadata**——
                    --    那包還有其他 authoring/runtime metadata，為一個三態值把整個 JSONB
                    --    帶過 hot path 會把 transport contract 擴得沒有必要。
                    -- ⛔ **retriever 只負責原值搬運**：不得在此做 "INSTANCE"→instance、
                    --    true→instance、missing→general 之類的 normalization；
                    --    值域封閉與 UNKNOWN 語義一律由 services/instance_applicability.py 負責。
                    kb.generation_metadata->>'instance_applicability'
                        AS knowledge_instance_applicability,
                    -- ⚠️ **retrieval semantic contract 的 transport 欄位**（D1，2026-08-29）：
                    --    scoring surface 由 services/retrieval_representation.scoring_surface()
                    --    決定，該函式讀的就是這兩欄；不投影＝所有 row 永遠落 legacy 分支。
                    -- ⚠️ **兩欄必須成對投影**：只投影文字不投影 provenance，consumer 就分不出
                    --    reviewed declaration 與 proposal ⇒ 未經審查的文字會直接進 scoring，
                    --    那正是 D3 要擋的事。
                    -- ⛔ **只帶這兩個最小欄位**，比照上方 applicability 的理由。
                    -- ⛔ **retriever 只負責原值搬運**：不得在此做 fallback 到 question_summary、
                    --    不得在此判 provenance 是否合格——值域與授權一律由
                    --    services/retrieval_representation.py 負責。
                    kb.generation_metadata->>'retrieval_representation'
                        AS retrieval_representation,
                    kb.generation_metadata->'retrieval_representation_provenance'->>'source'
                        AS retrieval_representation_source,
                    kb.trigger_mode,
                    kb.trigger_keywords,
                    kb.immediate_prompt,
                    1 - (kb.embedding <=> %s::vector) as vector_similarity
                FROM knowledge_base kb
                WHERE
                    kb.embedding IS NOT NULL
                    {visibility_sql}
                ORDER BY
                    (1 - (kb.embedding <=> %s::vector)) DESC,
                    kb.priority DESC
                LIMIT %s
            """

            # 構建參數列表：SELECT 的 vector_str → 可見性謂詞參數（順序由謂詞決定）
            # → ORDER BY 的 vector_str → LIMIT。⛔ 謂詞參數不得拆開或重排。
            query_params = [vector_str]
            query_params += visibility_params
            query_params += [
                vector_str,
                vector_limit
            ]

            cursor.execute(sql_query, tuple(query_params))
            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                results.append(self._format_result(dict(row)))

            return results

        finally:
            conn.close()

    async def _keyword_search(
        self,
        query: str,
        vendor_id: int,
        limit: int,
        **kwargs
    ) -> List[Dict]:
        """
        知識庫關鍵字檢索實作
        """
        import jieba

        # 分詞處理查詢
        query_tokens = set(jieba.cut(query.lower()))
        # 過濾空白與單字（單字 noise 太多）
        query_tokens_for_sql = [t for t in query_tokens if t.strip() and len(t) > 1]

        # 獲取額外參數
        target_user = kwargs.get('target_user', 'tenant')
        mode = kwargs.get('mode', 'b2c')

        # 可見性隔離：與 _vector_search **同一份**謂詞（⛔ 不再各抄一份；不變量 20）。
        # ⚠️ `keywords IS NOT NULL AND array_length(...) > 0` 是本路徑自己的相關性條件，
        #    兩條路的 WHERE 本來就不一樣，故留在下方 WHERE。
        visibility_sql, visibility_params = build_visibility_predicate(
            Identity(vendor_id=vendor_id, target_user=target_user, mode=mode),
            param_resolver=self.param_resolver,
        )

        # 安全上限
        max_rows = 1000

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 通用 SELECT 與 WHERE
            base_sql = f"""
                SELECT
                    kb.id,
                    kb.question_summary,
                    kb.answer,
                    kb.scope,
                    kb.priority,
                    kb.vendor_ids,
                    kb.business_types,
                    kb.target_user,
                    kb.keywords,
                    kb.video_url,
                    kb.form_id,
                    kb.action_type,
                    kb.api_config,
                    kb.category,
                    kb.categories,
                    -- ⚠️ **routing authority 的 transport 欄位**（A03 逼出，業主裁定 2026-08-29）：
                    --    P1f 的 gate 讀 knowledge applicability 宣告來決定是否抑制面向進場，
                    --    但本 projection 過去**沒有帶出它** ⇒ gate 一律讀到 UNKNOWN、一律 suppress。
                    --    contract 已存在、consumer 已接線，斷的是 **transport shape**。
                    -- ⚠️ 這**不是第二份 authority source**：唯一權威仍是
                    --    `knowledge_base.generation_metadata.instance_applicability`，
                    --    此處只是 projection ⇒ 無 cache 與 DB truth 不一致的問題。
                    -- ⛔ **只帶這一個最小欄位，不帶整包 generation_metadata**——
                    --    那包還有其他 authoring/runtime metadata，為一個三態值把整個 JSONB
                    --    帶過 hot path 會把 transport contract 擴得沒有必要。
                    -- ⛔ **retriever 只負責原值搬運**：不得在此做 "INSTANCE"→instance、
                    --    true→instance、missing→general 之類的 normalization；
                    --    值域封閉與 UNKNOWN 語義一律由 services/instance_applicability.py 負責。
                    kb.generation_metadata->>'instance_applicability'
                        AS knowledge_instance_applicability,
                    -- ⚠️ **retrieval semantic contract 的 transport 欄位**（D1，2026-08-29）：
                    --    scoring surface 由 services/retrieval_representation.scoring_surface()
                    --    決定，該函式讀的就是這兩欄；不投影＝所有 row 永遠落 legacy 分支。
                    -- ⚠️ **兩欄必須成對投影**：只投影文字不投影 provenance，consumer 就分不出
                    --    reviewed declaration 與 proposal ⇒ 未經審查的文字會直接進 scoring，
                    --    那正是 D3 要擋的事。
                    -- ⛔ **只帶這兩個最小欄位**，比照上方 applicability 的理由。
                    -- ⛔ **retriever 只負責原值搬運**：不得在此做 fallback 到 question_summary、
                    --    不得在此判 provenance 是否合格——值域與授權一律由
                    --    services/retrieval_representation.py 負責。
                    kb.generation_metadata->>'retrieval_representation'
                        AS retrieval_representation,
                    kb.generation_metadata->'retrieval_representation_provenance'->>'source'
                        AS retrieval_representation_source,
                    kb.trigger_mode,
                    kb.trigger_keywords,
                    kb.immediate_prompt,
                    kim.intent_id
                FROM knowledge_base kb
                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                WHERE
                    kb.keywords IS NOT NULL
                    AND array_length(kb.keywords, 1) > 0
                    {visibility_sql}
            """

            # 構建基本參數列表：順序完全由可見性謂詞決定，⛔ 不得拆開或重排
            base_params = list(visibility_params)

            all_rows = []

            # 快速路徑：SQL 用 keywords && query_tokens 過濾（精確配對）
            if query_tokens_for_sql:
                cursor.execute(
                    base_sql + " AND kb.keywords && %s::text[] ORDER BY kb.priority DESC, kb.id DESC LIMIT %s",
                    tuple(base_params + [query_tokens_for_sql, max_rows])
                )
                all_rows = cursor.fetchall()

            # Fallback：精確配對 0 結果時撈全部，讓 Python jieba 處理多字詞 keyword
            if not all_rows:
                cursor.execute(
                    base_sql + " ORDER BY kb.priority DESC, kb.id DESC LIMIT %s",
                    tuple(base_params + [max_rows])
                )
                all_rows = cursor.fetchall()

            cursor.close()

            # 篩選包含匹配關鍵字的知識
            keyword_matched_knowledge = []

            for row in all_rows:
                keywords = row.get('keywords', [])
                if not keywords:
                    continue

                # 計算關鍵字匹配
                matched_keywords = []
                match_score = 0.0

                for keyword in keywords:
                    keyword_tokens = set(jieba.cut(keyword.lower()))
                    intersection = query_tokens & keyword_tokens

                    if intersection:
                        matched_keywords.append(keyword)
                        match_score += len(intersection) / len(keyword_tokens)

                # 如果有匹配，加入結果
                if matched_keywords:
                    item = dict(row)
                    normalized_score = min(1.0, match_score / max(1, len(matched_keywords)))

                    result = self._format_result(item)
                    # task 3.2：keyword 路徑寫入獨立欄位
                    # vector_similarity 預設 0.0（代表「向量沒命中、純靠 keyword 找到」）
                    result['keyword_score'] = normalized_score
                    result['vector_similarity'] = 0.0
                    result['original_similarity'] = 0.0  # alias 同步
                    result['similarity'] = 0.0  # 待 _finalize_scores 重算
                    result['keyword_matches'] = matched_keywords
                    result['search_method'] = 'keyword'

                    keyword_matched_knowledge.append(result)

            # 按 keyword_score 排序，取前 limit 個（final similarity 由 _finalize_scores 算）
            keyword_matched_knowledge.sort(key=lambda x: x.get('keyword_score') or 0, reverse=True)
            return keyword_matched_knowledge[:limit]

        finally:
            conn.close()

    def _format_result(self, row: Dict) -> Dict:
        """
        格式化知識庫檢索結果（task 3.3）

        欄位來源（與 SOP retriever 對稱）：
        - vector_similarity：vector path 從 row['vector_similarity']（SQL alias）讀；
          keyword path（row 無此欄位）預設 0.0
        - keyword_score / rerank_score：預設 None
        - keyword_boost：預設 1.0
        - similarity：暫時 = vector_similarity，由 _finalize_scores 依公式重算
        - original_similarity：向後相容 alias = vector_similarity
        """
        defaults = make_default_result()
        vector_similarity = row.get('vector_similarity', defaults['vector_similarity'])

        return {
            'id': row['id'],
            'question_summary': row.get('question_summary'),
            'answer': row.get('answer'),
            'scope': row.get('scope'),
            'priority': row.get('priority'),
            'vendor_ids': row.get('vendor_ids'),
            'business_types': row.get('business_types'),
            'target_user': row.get('target_user'),
            'keywords': row.get('keywords', []),
            'video_url': row.get('video_url'),
            'form_id': row.get('form_id'),
            'action_type': row.get('action_type'),
            'api_config': row.get('api_config'),
            # 分類（conversational-diagnosis 元件 5：分類路由用）；category 單值、categories 多值
            'category': row.get('category'),
            'categories': row.get('categories'),
            # ⚠️ Knowledge 軸的 applicability 宣告（原值搬運；⛔ 不在此 normalize）。
            #    命名刻意帶 `knowledge_` 前綴——downstream 一眼分得出這是 Knowledge 軸，
            #    ⛔ 不會與 Face 的 `requires_instance_reference` 混。
            'knowledge_instance_applicability': row.get('knowledge_instance_applicability'),
            # ⚠️ Retrieval semantic contract（D1）＋其 provenance（D3）。
            #    ⛔ 兩欄一起搬或一起不搬；⛔ 不在此 fallback、不在此判授權。
            'retrieval_representation': row.get('retrieval_representation'),
            'retrieval_representation_source': row.get('retrieval_representation_source'),
            'intent_id': row.get('intent_id'),
            # ─── 觸發配置（spec trigger-vocabulary-debt 元件 1：修檢索斷鏈，透傳至消費層 chat.py:2948）───
            # trigger_mode=varchar／immediate_prompt=text → str|None；trigger_keywords=text[] → list|None（比照 keywords）
            'trigger_mode': row.get('trigger_mode'),
            'trigger_keywords': row.get('trigger_keywords'),
            'immediate_prompt': row.get('immediate_prompt'),
            # ─── 分數欄位（task 3.3） ───
            'vector_similarity': vector_similarity,
            'keyword_score': defaults['keyword_score'],
            'keyword_boost': defaults['keyword_boost'],
            'rerank_score': defaults['rerank_score'],
            'similarity': vector_similarity,  # 暫時值，由 _finalize_scores 重算
            'score_source': defaults['score_source'],
            'keyword_matches': list(defaults['keyword_matches']),
            'original_similarity': vector_similarity,  # 向後相容 alias
            # ─── 既有 metadata ───
            'search_method': row.get('search_method', 'vector'),
        }

    # 便利方法：保持向後相容
    async def retrieve_knowledge_hybrid(
        self,
        query: str,
        vendor_id: int,
        top_k: int = 3,
        similarity_threshold: float = 0.6,
        target_user: str = 'tenant',
        mode: str = 'b2c',
        return_debug_info: bool = False,
        return_unfiltered: bool = False,
        unfiltered_sink: List[Dict] = None,
        precomputed_embedding=None,
        precomputed_rewrites=None,
        **kwargs
    ) -> List[Dict]:
        """
        向後相容的介面
        調用統一的 retrieve 方法
        """
        results = await self.retrieve(
            query=query,
            vendor_id=vendor_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            enable_keyword_fallback=True,
            enable_keyword_boost=True,
            return_unfiltered=return_unfiltered,
            unfiltered_sink=unfiltered_sink,
            target_user=target_user,
            mode=mode,
            precomputed_embedding=precomputed_embedding,
            precomputed_rewrites=precomputed_rewrites
        )

        # 如果不需要 debug info，移除內部欄位
        # ⚠️ **2026-09-11 舊鏈退役：這份剝欄清單失去了對帳夥伴。**
        # 原本 `routers/chat.py:_retrieve_knowledge` 恆以 `return_debug_info=True` 取值後
        # 自行剝同一組欄位，`tests/unit/retrieval/test_kb_candidate_telemetry_contract_req.py`
        # 逐項比對兩份清單，任一邊漂移即紅（P0-1 回測輸出契約 §B②）。
        # `chat.py` 已刪 ⇒ 該測試整檔失去受測對象、一併移除。
        # ⛔ **失去的保護**：清單漂移不再有機器把關；改動下面五個 pop 之前，
        #    要自己確認沒有呼叫端依賴被剝掉的欄位（新線走 `services/agent/tools/kb.py`）。
        if not return_debug_info:
            for result in results:
                result.pop('search_method', None)
                result.pop('keyword_matches', None)
                result.pop('keyword_boost', None)
                result.pop('original_similarity', None)
                result.pop('rerank_score', None)

        return results


# ══════════════════════════════════════════════════════════════════════════
# 知識池可見性謂詞 —— **單一來源**（spec agentic-mcp-orchestration・任務 1.1）
# ══════════════════════════════════════════════════════════════════════════
#
# 為什麼要抽出來：security-reviewer 2026-09-04 實查，這組隔離條件在 repo 內
# **手抄了 4 份且各不相同**（`_grounding_by_ids` 只有 is_active、
# `_grounding_by_category`／`system_context._fetch_base` 無 vendor_ids）。
# 手抄會漏掉的 9 條：①保留分類 ②`vendor_ids IS NULL OR &&` ③`is_active`
# ④`_effective_target_user` fail-safe ⑤`is_b2b` 兩條件 OR ⑥**b2b 無 IS NULL
# 放行**（D-002）⑦b2c 追加 `all_users` ⑧查無業者 `[]` fail-closed
# ⑨`embedding`／`keywords` NOT NULL 的路徑差異。
#
# ⛔ **新增可見性條件一律加在這裡**，不得在任何消費點內嵌第二份字面 SQL
#    （design 不變量 20）。


def build_visibility_predicate(identity, param_resolver=None):
    """依身分產出知識池可見性的 SQL 片段與參數。

    Args:
        identity: `services.agent.identity.Identity`（vendor_id／target_user／mode）。
        param_resolver: `VendorParameterResolver` 替身；省略時建一個共用實例。
            b2c 分支才會用到（查業者業態）。

    Returns:
        `(sql, params)`：`sql` 以 `AND ` 起首、可直接拼進既有 WHERE；
        `params` 依佔位符順序為 `[[vendor_id], business_types, target_user]`
        （psycopg2 `%s` 風格，⛔ 不混用 `$n`）。

    ⚠️ **不含** `embedding IS NOT NULL`／`keywords IS NOT NULL` ——
       那是各檢索路徑自己的相關性條件，兩條路徑不一樣（向量要 embedding、
       詞面要 keywords），留在各搜尋函式內。
    """
    target_user = identity.target_user
    mode = identity.mode
    vendor_id = identity.vendor_id

    # 條件 5：is_b2b 兩條件 OR。⚠️ 讀 **原值** target_user，不讀正規化後的值——
    #   正規化只作用於參數側（條件 4），拿它判 b2b 會把未知角色一律降成 b2c。
    is_b2b_mode = (target_user in ['property_manager', 'system_admin']) or (mode == 'b2b')

    # 條件 4：角色隔離（b2b 與 b2c 皆過濾；target_user IS NULL 一律放行；retrieval-fixes #5）
    target_user_param = [VendorKnowledgeRetrieverV2._effective_target_user(target_user)]
    if is_b2b_mode:
        # 條件 6a／7：b2b 業態嚴格 system_provider。
        # ⛔ **無 `IS NULL` 放行**——這是刻意的跨業者隔離（D-002，業主 2026-09-01 逐行對碼）。
        #    `COMPLETE_CONVERSATION_ARCHITECTURE.md` §3 曾漏掉這條分支，照它補 IS NULL 會打穿隔離。
        vendor_business_types = ['system_provider']
        business_type_filter_sql = "kb.business_types && %s::text[]"
    else:
        resolver = param_resolver if param_resolver is not None else _shared_param_resolver()
        vendor_info = resolver.get_vendor_info(vendor_id)
        # 條件 7：vendor_id 查無業者 ⇒ 空業態（只剩 IS NULL 列，fail-closed）。
        # 修正(retrieval-fixes #4)：get_vendor_info 回 None 時 None.get() 會 AttributeError 使請求 500。
        vendor_business_types = (vendor_info or {}).get('business_types', [])
        # 條件 6b：b2c 業態寬鬆（IS NULL 放行）。
        business_type_filter_sql = "(kb.business_types IS NULL OR kb.business_types && %s::text[])"
        # 修正(retrieval-fixes #5)：b2c 也過濾 target_user（預設 tenant），避免租客↔房東知識互漏；
        #   'all_users' 為通用標記須一併放行（否則原本對 b2c 可見的通用知識會被擋掉）。
        target_user_param = [
            VendorKnowledgeRetrieverV2._effective_target_user(target_user), 'all_users'
        ]

    target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && %s::text[])"

    # 條件 1／2／3 ＋ 6 ＋ 4，順序即參數順序（⛔ 調整順序必須同步 params）
    conditions = [
        "AND (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])",
        "AND kb.is_active = TRUE",
        f"AND kb.category IS DISTINCT FROM '{VendorKnowledgeRetrieverV2.SYSTEM_DOC_CATEGORY}'",
        f"AND kb.category IS DISTINCT FROM '{VendorKnowledgeRetrieverV2.RULES_DOC_CATEGORY}'",
        f"AND {business_type_filter_sql}",
        f"AND {target_user_filter_sql}",
    ]
    sql = ("\n" + " " * 20).join(conditions)
    params = [
        [vendor_id],              # kb.vendor_ids && %s::int[]
        vendor_business_types,    # business_type_filter_sql
        target_user_param,        # target_user_filter_sql
    ]
    return sql, params


#: b2c 分支查業態用的共用 resolver（呼叫端通常傳自己的，見 `_vector_search`）。
_SHARED_PARAM_RESOLVER = None


def _shared_param_resolver():
    global _SHARED_PARAM_RESOLVER
    if _SHARED_PARAM_RESOLVER is None:
        _SHARED_PARAM_RESOLVER = VendorParamResolver()
    return _SHARED_PARAM_RESOLVER
