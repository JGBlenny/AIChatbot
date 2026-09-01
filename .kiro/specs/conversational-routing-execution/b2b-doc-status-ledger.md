# b2b 檢索相關文件：可信度分流帳本

> 2026-09-01｜25 份文件、約 14,000 行，四組唯讀盤查交叉查證
> **判定的尺＝`b2b-ground-truth.md`（實查程式碼＋容器 env＋DB），⛔ 不以文件驗文件**
> ⚠️ 本帳本只判「b2b／檢索過濾／門檻」這個主題，⛔ 不代表該檔其他主題的可信度

---

## 一、⛔ 不可依據（照它改碼／改資料會出事）

```text
docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md  §3（433-436）＋:383
  :433 業者隔離寫成 vendor_ids @> ARRAY[...]
       實際 `array_length(vendor_ids,1) IS NULL OR vendor_ids && %s::int[]`
       ⇒ 運算子錯（&& 非 @>），且**漏掉「vendor_ids 空＝全業者共用」放行**
  :434 角色隔離寫成 target_user @> ARRAY[...]
       實際 `target_user IS NULL OR target_user && %s`，且 b2c 另放行 'all_users'
  :435 業態過濾只給一條含 IS NULL 的公式
       ⇒ **漏掉 b2b 嚴格分支**：b2b 是 `business_types && {system_provider}`、**無 IS NULL**
       ⛔ 照這份文件給 b2b 補 IS NULL，會打穿刻意的池隔離
  :383 把 0.6 標成「已過時」、宣稱正確值 0.65
       ⇒ **兩處都錯**，見下方「錯誤熱點①」
  ✅ 決策樹本體（380-429）與 decision_layer.decide_arbitration 逐條相符，**這節可信**

docs/guides/migration/KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md
  引用 vendor_knowledge_retriever.py 與 rag_engine.py ——**兩個檔案都不存在**
  （已實查；正對照 vendor_knowledge_retriever_v2.py 存在）
  且仍主張「可見性僅由 vendor_id 決定」——現行是 business_types／target_user／vendor_ids 三軸
  ⇒ 2026-02-09 的遷移指南，已被 v2 取代
```

## 二、部分過時（可用，但指定段落要跳過）

```text
docs/retrieval-parameters.md            ⚠️ 仍是參數的最佳單一入口，但混寫兩種值
  問題  把「部署實際值」與「程式碼 fallback」寫成同一個數字，不註明來源
        KB_SIMILARITY_THRESHOLD：文件 0.65＝部署值；程式 fallback 其實是 0.55
        ENABLE_QUERY_REWRITE_B2B：文件 false＝部署值；程式 fallback 其實是 true
  ✅ 已實查容器 env 補齊，見 b2b-ground-truth.md「容器實際環境值」

docs/chat-architecture-overview.md
  :92  行號漂移（機制在 chat.py 的 `is_b2b` 附近，非文件所指行）
  :132 「向量檢索 ≥0.6」——現行找不到這個數字的出處，⛔ 別引用

docs/architecture/conversation-flow-evidence.md
  內容判定多屬實，但**行號索引全面漂移**，⛔ 別照行號對碼

docs/api/API_REFERENCE_PHASE1.md
  :184 回應範例仍留 `"mode": "tenant"`（舊值）
       ⚠️ 同檔 :1357 自己寫「已修正為 b2c」——**文件內部自相矛盾**
  ✅ :58 mode 預設 b2c 與 `VendorChatRequest` 一致

docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md
  :87-88 排序依據「Scope 權重 > 相似度 > 人工優先級」——scope_weight 已移除
  :95／:899 RAG Fallback ——**功能已移除**（compose:179 明文「已廢棄」）
  :229 system_admin 只講 target_user，漏掉它同時觸發 b2b 的 system_provider 過濾
  :890／:231 引用不存在的 vendor_knowledge_retriever.py
  ✅ :231-234 的 target_user SQL **語意本身仍正確**

docs/retrieval-recall-audit-20260822.md
  第六、七節量化結果**文件自己已標作廢**
  ✅ 第一~四節與附錄的**機制性斷言全部 CURRENT**（含 0.1/0.9 合成、20／0.3 兩道 reranker 前置）
```

## 三、可依據

```text
docs/jgb2-chat-integration.md          ✅ 契約層與程式一致，b2b 的**正本**
                                       （§8 兩個待補齊項 A/B 仍未補，屬已知缺口非錯誤）
docs/architecture/DATABASE_SCHEMA.md   ✅ 三個過濾欄位的描述與實際 SQL 一致
docs/deployment-runbook.md             ✅ 查證到的兩項一致（⚠️ 全文未提 ENABLE_RERANKER）
docs/features/conversational-presales.md ✅
docs/architecture-overview.md          ✅
docs/testing/multiturn-smoke-scripts.md ✅（§4 身分形狀合法）
docs/features/RERANKER_FEATURE.md      ✅ **檔頭已自標歷史文件並指向現行文件**
                                       ⇒ 內文公式（0.3/0.7、本機 CrossEncoder）已過時但不誤導
```

## 四、與本主題無關（⛔ 別再拿它們查檢索）

```text
docs/design/PERMISSION_SYSTEM_DESIGN.md｜docs/features/PERMISSION_SYSTEM_README.md
docs/guides/getting-started/PERMISSION_QUICK_START.md
  ⚠️ 這三份的 business_types／target_user 是**選單權限碼**，與檢索過濾同名不同用途
docs/guides/features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md   （匯出入欄位表）
docs/architecture/SYSTEM_ARCHITECTURE.md                （只有檔案路徑列表）
```

---

## 錯誤熱點①：三個「0.6 系」門檻被混為一談

```text
① KB_SIMILARITY_THRESHOLD    檢索過濾／Brain kb_search
   程式 fallback 0.55｜compose **硬編 0.65**（:177 不是 ${VAR:-} 格式 ⇒ .env 蓋不掉）
② knowledge_min = 0.6        六 case 答題仲裁，**硬編碼、無 env、刻意不開旋鈕**
③ default_similarity_threshold = 0.6   base_retriever.retrieve() 的預設
```

⇒ 「0.6 已過時、正確是 0.65」**錯兩次**：0.6 仍活在②③；0.65 是①的部署值，
   是另一顆常數，不是 0.6 的後繼。**三顆各有各的工作，⛔ 不可互相取代。**

⚠️ 連帶陷阱：`retrieve()` 用 `threshold or default`，傳 `0.0` 會被當 falsy
   **靜默換成 0.6**——想關門檻不能傳 0。

## 錯誤熱點②：引用已不存在的檔案

```text
vendor_knowledge_retriever.py   ⛔ 不存在（現行是 _v2）
rag_engine.py                   ⛔ 不存在
出現於  KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md、USER_MANUAL_NON_TECHNICAL.md
```

## 錯誤熱點③：已移除的功能仍被當現行描述

```text
RAG Fallback（降低門檻再搜一次）  已移除，compose:179 明文「已廢棄」
scope_weight 排序                 已於 2026-02-09 移除
出現於  USER_MANUAL_NON_TECHNICAL.md
```

---

## 建議處置（⛔ 未經業主核可不執行）

```text
A 立即加警語     COMPLETE_CONVERSATION_ARCHITECTURE.md §3 開頭加「⛔ 過濾機制五處錯，
                 以 b2b-ground-truth.md 為準；決策樹本體可信」
                 ⚠️ 這份是**架構母圖**，被引用頻率最高，錯誤的殺傷力也最大
B 退休           KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md ⇒ 移入 docs/archive/
                 （引用檔已不存在、過濾模型已被取代，留著只會誤導）
C 修一行         API_REFERENCE_PHASE1.md:184 的 "mode": "tenant" 改 "b2c"
                 （同檔自己已宣稱修正過，這是漏網的範例）
D 拆兩欄         retrieval-parameters.md 每個參數分「程式 fallback／部署實際值」兩欄
E 不動           行號漂移類（chat-architecture-overview、conversation-flow-evidence）
                 ⇒ 行號本來就會漂，加「⛔ 行號僅供參考，以符號名 grep」即可
```

⚠️ CANON 已於 2026-08-22 判定為**快照**的檔（過時是預期，⛔ 不算缺陷）：
`docs/features/*_FEATURE.md`、`KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md`、
`assistant-report-regression.md`、`assistant-report-workflow.md`、
`research/account-conversational-facets-research.md`
