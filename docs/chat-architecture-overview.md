# Chat 對話系統：觸發語彙盤點與設計方向判定

**最後對碼：2026-09-12**

> 2026-09-12 刪掉全景架構圖、§0 入口矩陣、§1 決策管線、§2 機制總表——
> 它們描述的 `routers/chat.py`／`conversational_engine.py`／`api_call_handler.py`／
> `form_manager.py`／`sop_orchestrator.py` 已於 2026-09-11 刪除（DSP-046），
> 且每個斷言都以 `chat.py:<行號>` 為據，指向不存在的檔。
> ⛔ 不留「已退役」標記——實測證明沒人看。要看舊設計請 `git log`。
>
> 保留的是**診斷與裁決**：§3 觸發語彙碎片化的盤點（另有 spec
> `trigger-vocabulary-debt`）、§4 關係規則、§5 應然 vs 實然差距、
> §6 2026-07-10 的設計方向判定。
>
> 現況架構見 [`architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md)。

## 3. 觸發語彙盤點（碎片化診斷）

語義命中後「要不要/怎麼執行動作」的決策因子，分佈在三套機制中，活度不一：

| 因子 | 所屬 | 生效位置 | 活度 |
|---|---|---|---|
| SOP trigger_mode（none/manual/immediate） | SOP | sop_trigger_handler.py:148-276 | 🟢 活 |
| SOP trigger_keywords（關鍵詞確認/等待） | SOP | sop_orchestrator.py:209-278 | 🟢 活 |
| FORM_TRIGGER_THRESHOLD（0.75，env） | 知識 | chat.py:2852 | 🟢 活 |
| action_type＋form_id | 知識 | chat.py:2944-3031 | 🟢 活 |
| form_schemas.trigger_intents | 表單 | 離題偵測用（digression_detector.py:165）＋find_form_by_intent | 🟢 活 |
| 知識 trigger_mode/trigger_keywords/immediate_prompt | 知識 | chat.py:2948/2976 有讀，**但 retriever SELECT 未查這些欄**（vendor_knowledge_retriever_v2.py:89-106）→ 永遠回退預設 'auto' | 🟡 **半失效（P0）** |
| 知識 trigger_form_condition/trigger_conditions/auto_keywords | 知識 | **無任何程式碼讀取** | 🔴 死欄位 |

**診斷**：SOP 側觸發機制完整；知識側觸發配置「欄位建了、chat.py 也寫了消費邏輯，但檢索層沒把欄位帶出來」——中間斷鏈，使用者在 admin 設的知識觸發詞實際被忽略。另有三個死欄位（auto 判斷機制設計完成度 0%）。這是把交易觸發放到知識層（通用化方向）前**必須先修**的債。

**門檻不對稱**（設計影響）：SOP 觸發表單的有效門檻是 0.55＋關鍵詞確認；知識觸發表單是 0.6 勝出＋0.75 才觸發，0.6–0.75 灰帶會**靜默降級**成其他知識直答（chat.py:2912）。交易觸發從 SOP 遷往知識層時，錨點問法品質必須把常見句式推過 0.75，或重新檢視雙門檻。

## 4. 關係規則

**攔截順序**：進行中會話（對話優先於表單）> 損傷圖片 > prospect 引擎 > 快取 > 檢索仲裁。
**覆蓋規則**：業者 SOP 覆蓋通用知識＝仲裁 Case 3.1（分數接近且 SOP 有動作）；邊角：KB 高出 0.15 以上時知識勝——客製 SOP 錨點需對齊通用問法。
**交棒關係**（單向）：知識/SOP --form_fill--> 表單 --完成--> API／chaining／option-routing 決策樹；知識 --api_call--> lookup/jgb_*；知識 --分類路由--> 對話面向 --facts--> JGB API。
**資料歸屬**（歸屬×形狀）：業者參數單值→vendor_configs；業者資料多列→lookup_tables；平台動態個資→JGB API（雙證）；靜態文本→knowledge_base.answer。

## 5. 應然 vs 實然差距

| # | 應然 | 實然 | 處置 |
|---|---|---|---|
| 1 | 知識層觸發配置生效 | **retriever SELECT 缺欄致半失效（P0）**；三死欄位 | 補 SELECT；死欄位先定標準再啟用或清除 |
| 2 | 交易觸發門檻一致可預期 | SOP 0.55 vs 知識 0.6+0.75 雙門檻，灰帶靜默降級 | 通用化交易觸發前重新檢視；錨點品質實測把關 |
| 3 | 平台交易觸發坐通用知識錨點 | 修繕觸發只在 vendor 2 SOP | 建全域觸發＋查詢知識；先修 #1 |
| 4 | 通用表單 vendor_id=NULL | jgb_repair_create 綁 vendor 2 | migration |
| 5 | 同 form_id 可有業者變體 | UNIQUE(form_id) 擋死 vs 解析層 NULLS LAST 已備（form_manager.py:102） | 需求出現時改複合唯一鍵 |
| 6 | 明確入口決定性觸發 | 無 trigger_form_id，按鈕缺直達路徑 | chat API 小擴充（LINE Phase 1） |
| 7 | 交易意圖有獨立分類層 | 意圖＝檢索兼職 | 現規模合理，交易意圖成長後再抽 |
| 8 | 業者能力就緒度統一管理 | 開關/lookup 就緒/SOP 建置散落 | 上架 checklist 統一 |
| 9 | 記錄與碼一致 | option-routing 索引記錄為「待實作」實已實作（ed36fdb 起）；pending_question 已修（fix 檔在 database/fixes/，gitignore 不進版控，dev 已套、prod 待套） | 本文件為準；prod 套用由使用者執行 |

## 6. 設計方向判定（2026-07-10 確認）

> **升級**：本節驗的是「分層一致性」（機制各歸其位）。更根本的「骨架重心」評估——檢索問答骨架 vs 對話優先重心——另立 **docs/conversation-first-architecture-assessment.md**：結論為混合骨架（對話脈絡與交易/診斷意圖由引擎擁有回合、冷資訊問答保留檢索快路徑），四階段遷移，prospect engine-first 為已驗證的目標形狀。

**方向正確的證據**（系統的實際演化與四層應然一致）：
1. 對話面向已全配置驅動（加面向＝加 DB 配置），語義層薄的方向已在面向引擎實現
2. facts 決定性 grounding＋formatter 解碼、LLM 只組話——「決定性優先」已是面向引擎的內建紀律
3. option-routing 已實作、快取排除動作類、偽會話統一在 form_sessions——流程機器承重的基座就位
4. 仲裁 Case 3.1 實現業者覆蓋語義——通用/客製分層有碼支撐

**方向對但有前置債**：語義層的觸發語彙是目前最大架構債（§3）：碎片化＋半失效＋死欄位。任何「觸發通用化」工作（修繕、未來帳單/合約交易）都建立在知識層觸發之上，**P0 先修 retriever 斷鏈，再動觸發搬遷**。

**演化原則**（定案）：
1. 語義層保持薄：錨點只做認出與路由，不承載流程與資料
2. 流程機器承重：多步驟進表單/chaining/決策樹/面向；判準＝有沒有「下一步」
3. 通用 vs 客製就近落位：平台語義→通用知識；業者差異按強度→configs/業者知識/SOP/表單變體
4. 決定性優先：明確場景 template/formatter，模糊場景才 LLM
5. 入口越明確越早攔截：按鈕→入口層；明確句式→語義錨點；模糊→檢索兜底＋澄清
6. 觸發語彙收斂：以 SOP 側（活的那套）為基準統一觸發語義，知識側修斷鏈、死欄位定生死——不再新增第四套觸發機制
