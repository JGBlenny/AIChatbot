# 差距分析：trigger-vocabulary-debt

> 產生時間：2026-07-11　方法：三路對碼盤查（死欄位全引用掃描／知識 dict 生產路徑／計量落點）＋ dev DB 實查（dev＝prod 7/7 鏡像）
> 前置：需求盤查事實已於架構評估階段經獨立查核（14 條 CONFIRMED），本分析只補「需求裡標示待盤」與「實作面未知」的缺口。

## 0. 重大發現：修復的回歸風險趨近零

dev DB（＝prod 資料鏡像）實查 `knowledge_base` 觸發配置值分佈：

| 欄位 | 值分佈 |
|---|---|
| `trigger_mode` | `none`=983、`auto`=23、NULL=3——**`manual`/`immediate` 為 0 筆** |
| `trigger_keywords` | 有值＝**0 筆** |
| `immediate_prompt` | 有值＝**0 筆** |
| （參考）`form_id` | 有值＝49 筆 |

**含義**：修復斷鏈後**沒有任何一筆既有知識會改變行為**——`none`/`auto`/NULL 在消費邏輯（chat.py:2948 `if trigger_mode in ['manual','immediate']`）全部落 else 分支＝現行直觸發行為。R1.5 的「盤點既有非 auto 資料」已完成，結論是**無需逐筆確認、無需先改回 auto**。本案從「修復＋行為遷移」降級為「純修復」：把壞掉的機制修好，供未來配置使用。

同時注意值域現況：知識層 `trigger_mode` 實際用 `none`（983 筆）而消費邏輯的語彙是 `auto`/`manual`/`immediate`——`none` 靠 else 分支「碰巧」等同 auto。〔設計待決：是否正規化值域（none→auto 或 CHECK 約束），或維持寬鬆 else〕

## 1. R1 修斷鏈——差距與實作面

**要改的地方（經盤查確認全清單）**：
1. `vendor_knowledge_retriever_v2.py` **向量檢索 SELECT**（L89-106，`_vector_search`）——補 `kb.trigger_mode, kb.trigger_keywords, kb.immediate_prompt`
2. `vendor_knowledge_retriever_v2.py` **關鍵詞檢索 SELECT**（L196-215，`_keyword_search`）——同上
3. **row→dict 映射 `_format_result`**（L297-341）——補三個 key

**確認不用改的地方**：
- reranker（base_retriever.py `_apply_semantic_reranker`）只寫入 rerank_score、不重建 dict——欄位會透傳 ✓
- b2b 模式走同一個 `retrieve_knowledge_hybrid`（chat.py:1749 不分流）——一次修兩模式 ✓
- 無其他知識 dict 生產者（無 rag_engine 獨立檢索、快取是 Response 層級回放、form_manager/api_call_handler 只消費不生產）✓
- 消費邏輯（chat.py:2948-2989 借道 sop_orchestrator.handle_knowledge_trigger）已存在且健全，零改動 ✓

**結論**：實作面＝2 處 SQL＋1 處映射，無選項分歧。

## 2. R2 清死欄位——DROP 安全性雙重確認

**程式面（全引用掃描，讀＋寫）**：後端 Python（含全部知識 INSERT：coordinator.py:1066、knowledge_import_service.py:1798/1844、knowledge_generation.py:1342、loop_knowledge.py:1103；全部 UPDATE 語句）、admin 前端 src、SQL（init/migrations/fixes/seeds、排除建欄檔本身）、測試——**零引用**。知識 INSERT 均明列欄位、不含三欄，刪欄後不爆。

**資料面（dev DB 實查）**：`trigger_form_condition` 全部 'always'（建欄預設）、`trigger_conditions` 全 NULL、`auto_keywords` 全為預設 JSON——**零資訊內容**，無業務資料損失。

**連帶清理項**：`check_trigger_form_condition` CHECK 約束、`idx_kb_trigger_form_condition` 索引（add_knowledge_form_auto_option.sql:24/68 建立）需隨欄位一併 DROP。

**結論**：R2.3 的資料盤點已完成，DROP 完全安全。維持「刪欄 migration 獨立分檔＋prod 由使用者執行」的既定紀律。

## 3. R3 分數埋點——落點與選項

**現況流向（盤查確認）**：`decision['comparison']`（sop_score/knowledge_score/gap/decision_case）於 chat.py:1859-1925 各決策分叉構建 → 傳入 `_build_knowledge_response` → 轉入 `_build_debug_info(comparison_metadata=)`——**目前只進 debug_info，不進計量**。計量側已有中央賦值前例：`_um_set_path(processing_path)` 於 `_build_debug_info` 內（chat.py:1523-1524），各終局路徑都會經過。

**實作選項**：

| 選項 | 做法 | 取捨 |
|---|---|---|
| **a. 新增 `set_comparison()` hook（建議）** | usage_metering.py 加一個與 `set_path` 平行的 setter，在 `_build_debug_info` 既有中央點順手呼叫（comparison_metadata 已在手上） | 落點唯一、改動最小、與既有 `_um_set_path` 模式一致；短路路徑不經過此點→分數自然留 NULL（滿足 R3.2） |
| b. 擴充 `set_path()` 簽名 | 同一落點，參數加進既有函式 | 少一個函式但簽名混雜兩種語義 |
| c. 分數塞 JSONB 欄 | 一欄裝整包 comparison | 違反 R3.4（灰帶要一句 SQL 直查，JSON 要解析）——不建議 |

**欄位設計**（獨立欄、純加性，沿用 `ADD COLUMN IF NOT EXISTS` 前例如 add_vendor_quotas.sql）：`knowledge_score NUMERIC(4,3)`、`sop_score NUMERIC(4,3)`、`decision_case VARCHAR(60)`〔精度與命名於設計定案〕。R3.5 的降級要求（欄位未建時不報錯）需在寫入層容錯——與計量 fire-and-forget 既有原則一致。

## 4. R4 防回歸不變量——實作面

「消費層讀取欄位 ⊆ 檢索層 SELECT 欄位」的機器把關，兩個可行形態：
- **unit 斷言（建議起手）**：測試中以正則/AST 抽取 chat.py 對 best_knowledge 的 `.get()` key 集合與 retriever SELECT 欄位集合比對——離線可跑、無 DB 依賴
- make audit 不變量：若 audit 框架偏好 SQL/執行期檢查，改為「以一筆含全部觸發配置的測試知識走真實檢索，斷言 dict key 齊全」

〔形態於設計定案；兩者不互斥〕

## 5. 風險與遺留

| # | 風險 | 緩解 |
|---|---|---|
| 1 | e2e（R4.2）需要一筆 manual＋keywords 的測試知識——目前 DB 沒有這種資料，測試要自建自清 | 測試 fixture 建立＋afterEach 清理；沿用既有 e2e 慣例（G-gated） |
| 2 | `trigger_mode` 值域混亂（none vs auto 語義重疊） | 設計階段決定：正規化 or 文件化寬鬆 else；不影響本案行為 |
| 3 | 分數欄位上線前後的事件不可比（舊事件無分數） | 灰帶分析起算日＝埋點上線日，NULL 天然區隔；無需回補 |
| 4 | admin 後台目前**沒有** trigger_mode/keywords 的編輯 UI（前端零引用三死欄位的掃描順帶確認觸發配置編輯介面現況）〔待設計確認：知識編輯頁有無這三欄輸入；若無，修復後配置只能靠 SQL/匯入設定〕 | 設計階段確認；若無 UI，記為已知限制（本案範圍外，機制先通） |

## 6. 建議

- 三個工作項全部走 **extend 路線**（改既有檔案），無新元件、無新服務；整案預估改動集中在 4 個檔案＋2 個 migration。
- R1 因「零既有配置」發現，實作順序可以 R1→R3→R2（先修再埋再清），單一 PR 可容納。
- 設計階段的待決事項只剩三件：trigger_mode 值域正規化與否、分數欄位命名/精度、不變量形態。
