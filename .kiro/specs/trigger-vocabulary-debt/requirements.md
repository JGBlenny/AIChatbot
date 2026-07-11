# 需求規格：trigger-vocabulary-debt（觸發語彙還債 P0）

> 建立時間：2026-07-11　階段：requirements-generated　語言：zh-TW
> 定位：docs/conversation-first-architecture-assessment.md 定案混合骨架 C 後的第一階段（P0）。問題盤點見 docs/chat-architecture-overview.md §3。
> 現況盤查（2026-07-10/11 對碼＋獨立查核，14 條斷言全數 CONFIRMED）：
> - **斷鏈**：`vendor_knowledge_retriever_v2.py` 的 SELECT（L89-106）不含 `trigger_mode`/`trigger_keywords`/`immediate_prompt`，`chat.py:2948/2976` 的消費邏輯永遠回退預設 `'auto'`——admin 在後台設的知識觸發配置**線上正被靜默忽略**（線上與本地同版本）。
> - **死欄位**：`knowledge_base.trigger_form_condition`/`trigger_conditions`/`auto_keywords`（add_knowledge_form_auto_option.sql 建立）全庫零程式碼讀取；C 定案不投資 auto 機制。
> - **無分數紀錄**：檢索仲裁分數（SOP/知識 similarity、decision case）沒有任何表在存，0.6–0.75 灰帶占比無法量測——該數據是 P2 意圖路由設計的關鍵輸入。

## 簡介

本案還三筆觸發語彙的債，讓「知識層觸發」從半失效恢復為可信賴的機制，並開始累積骨架反轉（P2）所需的決策數據：

1. **修斷鏈**——檢索層把觸發配置欄位帶出來，讓既有消費邏輯真正生效。
2. **清死欄位**——移除三個零讀取的欄位，觸發語彙以「SOP 側活的那套」為基準收斂，不再殘留第二套未完成的觸發機制混淆建置者。
3. **分數埋點**——每則訊息的仲裁分數落入使用事件，灰帶占比從此可以用 SQL 直接回答。

核心立場：**本案不改變任何觸發行為的語義**——仲裁邏輯、門檻（0.55/0.6/0.75）、Case 分支全部不動（那是 P2 的事）。修斷鏈的效果是「配置了 manual/immediate 的知識開始照配置走」，未配置者行為不變。

## 名詞定義

- **觸發語彙**：語義命中後，決定「要不要／怎麼執行動作」的配置因子總稱（trigger_mode、trigger_keywords、門檻等）。
- **斷鏈**：DB 欄位存在、消費程式碼存在，但中間的檢索層沒把欄位帶出來，導致配置永遠不生效。
- **trigger_mode**：知識/SOP 的觸發模式——`auto`（直接觸發表單）／`manual`（等待關鍵詞確認）／`immediate`（立即詢問＋確認詞）。SOP 側此機制完整運作（sop_trigger_handler.py），知識側因斷鏈全部退化為 auto。
- **死欄位**：`trigger_form_condition`（always/auto/never/conditional）、`trigger_conditions`（JSONB 條件）、`auto_keywords`（action_words/query_words）——設計完成度 0%，零程式碼讀取。
- **仲裁分數**：一則訊息經 SOP／知識並行檢索後的 top 相似度（sop_score、knowledge_score）與判定結果（decision case）。
- **灰帶**：知識分數落在 0.6（仲裁勝出線）與 0.75（表單觸發線）之間的流量——目前會靜默降級為其他知識直答。

## 範圍

### 範圍內
- `vendor_knowledge_retriever_v2.py` 檢索 SELECT 補齊觸發配置欄位（向量與關鍵詞兩條查詢路徑）。
- 知識觸發配置生效的 e2e 驗證（manual/immediate＋trigger_keywords 全流程）。
- 死欄位移除 migration（含 rollback 檔）＋全庫引用清理（後端/admin 前端/匯入匯出如有涉及）。
- `usage_events` 檢索分數欄位（純加性 migration）＋落點寫入（沿用 fire-and-forget 原則）。
- 防回歸不變量：檢索層選取欄位必須涵蓋消費層讀取欄位（納入 `make audit` 或等效 unit 斷言）。
- 部署段落併入統一 runbook（`docs/deployment-runbook.md`）；prod 破壞性 migration（刪欄）指令交使用者自行執行。

### 範圍外
- 仲裁邏輯與任何門檻值的調整（P2 意圖路由的事）。
- SOP 側觸發機制（本已健全，不動）。
- 通用修繕觸發知識條目的建置（另案：修繕通用化）。
- 灰帶數據的分析與後續決策（本案只負責讓數據開始累積）。
- admin 後台的新編輯 UI（若既有欄位編輯介面引用死欄位，僅做移除性清理）。

## 需求

### Requirement 1：知識層觸發配置修復（修斷鏈）

**使用者故事**：作為知識建置者，我在後台為知識設定的觸發模式與觸發詞必須真正生效，而不是被系統靜默忽略後永遠直接觸發表單。

#### 驗收標準（EARS）
1. WHEN 檢索層回傳知識候選，THE SYSTEM SHALL 一併帶出該知識的 `trigger_mode`、`trigger_keywords`、`immediate_prompt` 欄位值（向量檢索與關鍵詞檢索兩條路徑一致）。
2. WHEN 命中知識的 `trigger_mode` 為 `manual` 或 `immediate` 且達表單觸發門檻，THE SYSTEM SHALL 依既有消費邏輯（chat.py 借道 sop_orchestrator 的知識觸發處理）走關鍵詞確認流程，而非直接觸發表單。
3. WHEN 命中知識的 `trigger_mode` 為 NULL 或 `auto`，THE SYSTEM SHALL 維持現行直接觸發行為（回溯相容：未配置者行為零改變）。
4. THE SYSTEM SHALL 不因本修復改變 direct_answer、api_call、對話面向分類路由的任何行為（觸發配置只影響 form_fill 路徑）。
5. WHERE 現有知識資料中 `trigger_mode` 已有非 auto 值（修復後將「開始生效」），THE SYSTEM SHALL 於實作前盤點這些資料列並逐筆確認生效後的行為符合建置意圖〔盤點結果記入設計文件；若有意圖不明者，修復前先改回 auto〕。

### Requirement 2：死欄位清理

**使用者故事**：作為系統維護者，我要移除三個「建了表但永遠沒人讀」的欄位，讓觸發語彙只剩一套可信的機制，不再誤導未來的建置與盤查。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 以 migration 移除 `knowledge_base` 的 `trigger_form_condition`、`trigger_conditions`、`auto_keywords` 三欄，並提供對應 rollback 檔。
2. WHEN 移除完成，全庫（後端 Python／admin 前端／匯入匯出流程）SHALL 不存在對三欄位的任何引用（含 SELECT *、序列化、表單欄位）。
3. WHEN 移除前，THE SYSTEM SHALL 先盤點三欄位於 prod 資料的實際值分佈；WHERE 有非預設值存在，SHALL 於設計文件記錄其內容與棄置理由後再移除。
4. WHEN 移除完成，既有全部測試 SHALL 維持綠燈（含 unit／integration／e2e）。
5. THE SYSTEM SHALL 將刪欄 migration 與加性 migration 分檔：破壞性部分（刪欄）之 prod 執行由使用者自行操作，系統僅提供指令與 runbook 段落。

### Requirement 3：檢索分數埋點

**使用者故事**：作為架構決策者，我要每則訊息的仲裁分數都被記錄，讓「0.6–0.75 灰帶占多少流量」這類 P2 前置問題可以用一句 SQL 回答，而不是猜。

#### 驗收標準（EARS）
1. WHEN 任一 `/message` 請求經過 SOP／知識檢索仲裁，THE SYSTEM SHALL 於該筆使用事件記錄：knowledge top1 相似度、SOP top1 相似度、仲裁判定結果（decision case 識別字串）。
2. WHEN 請求未經檢索仲裁（表單會話續填、對話偽會話續跑、快取命中、圖片直觸發等短路路徑），THE SYSTEM SHALL 使分數欄位留空（NULL），不記錄無意義的零值。
3. THE SYSTEM SHALL 沿用計量層 fire-and-forget 原則：分數記錄失敗 SHALL NOT 影響回應內容、延遲或成功率。
4. THE SYSTEM SHALL 使灰帶占比可直接以 SQL 查得（例：`knowledge_score >= 0.6 AND knowledge_score < 0.75` 的事件占比），無需 join 其他表。
5. THE SYSTEM SHALL 以純加性 migration 擴充使用事件表；WHEN 欄位不存在（尚未跑 migration 的環境），計量寫入 SHALL 降級為不含分數的既有行為而非報錯。

### Requirement 4：防回歸與驗證

**使用者故事**：作為系統維護者，我要「檢索層帶欄位」與「消費層讀欄位」的一致性從此有機器把關，同類斷鏈不再無聲發生。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 新增一條不變量檢查（納入 `make audit` 或等效自動化）：chat 消費層讀取的知識欄位集合 SHALL 為檢索層 SELECT 欄位集合的子集。
2. WHEN 執行 e2e 驗證，THE SYSTEM SHALL 通過完整觸發流程：建一筆 `trigger_mode=manual`＋`trigger_keywords` 的表單知識 → 問句命中 → 系統等待確認 → 回覆關鍵詞 → 表單觸發 → 回覆非關鍵詞 → 不觸發。
3. THE SYSTEM SHALL 通過回歸驗證：修復前後，`auto` 知識表單觸發、direct_answer、api_call（lookup／jgb_*）、對話面向進場的行為完全一致。
4. THE SYSTEM SHALL 不觸碰 `question_summary`、embedding 相關欄位與流程（embedding 完整性保護）。
5. WHEN 部署至任一環境，THE SYSTEM SHALL 通過煙囪驗證（觸發配置生效＋新事件帶分數），驗證步驟記入 runbook。

## 依賴與假設

- 依賴既有機制：sop_orchestrator 的 `handle_knowledge_trigger`（知識借道 SOP 觸發處理，chat.py:2983）已存在且健全——本案只是讓它終於收到真實配置值。
- 假設：三個死欄位在 prod 資料中無業務方依賴（依全庫零讀取推定）；R2.3 的資料盤點為此假設的最後防線。
- 部署紀律：跟隨統一 runbook；semantic-model 不受本案影響（不動 embedding）；破壞性 migration 由使用者執行（既定規矩）。
