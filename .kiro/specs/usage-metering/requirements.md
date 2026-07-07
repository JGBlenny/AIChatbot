# 需求規格：usage-metering（AI 客服使用量計量與流量統計）

> 建立時間：2026-07-06　階段：requirements-generated　語言：zh-TW
> 目的：為未來對業者計費提供可信的使用量依據。**本 spec 不做計費金額計算與帳單開立**，只建計量事實。
> 現況盤查（2026-07-06 實測）：`conversation_logs` 為空表（0 筆）且 schema 無 vendor/身分維度；`chat.py` 對該表只讀不寫（feedback 端點）——今天生產環境完全沒有使用量痕跡，任何回溯統計都不可能，需從零建立。

## 簡介

AI 客服的每次對話請求都帶著完整身分維度（vendor_id、mode b2b/b2c、target_user、role_id、user_id、session_id），但目前用完即棄。本功能建立三層計量體系：

1. **記錄層**——每次訊息請求落一筆不可否認的使用事件，維度齊全、含成本要素（LLM token）。
2. **彙總層**——日粒度 rollup，支撐「任意計費模型事後套用」：按訊息數、按對話（session）數、按 token 成本三種單位都算得出來。
3. **呈現層**——後台報表：各業者（vendor）底下使用者類型（租客/業者用戶/潛在客戶）與 JGB 內部使用的頻率統計，供營運與計費決策。

核心設計立場（立案時已定）：
- **三種計費單位一次抓齊**——計費模型未定，原始事件記全，之後不回頭補資料。
- **內部流量必須可區分**——回測/迴圈/煙囪驗證的機器流量遠大於真人流量（單輪迴圈即 60 題×多輪），不標記排除則統計全廢。
- **fire-and-forget**——計量失敗絕不影響線上回答。

## 名詞定義

- **使用事件（usage event）**：一次 `/message`（或串流）請求的計量紀錄，一問一答為一筆。
- **對話（session）**：同一 session_id 串起的連續事件；對話數＝獨立 session_id 數。
- **使用者類型（user_type）**：tenant／property_manager／prospect／internal（內部流量）。
- **內部流量（internal traffic）**：非真人使用——回測、知識補齊迴圈、煙囪驗證、開發 probe。
- **token 成本估算**：以各 LLM 呼叫回報的 usage（prompt/completion tokens）×模型單價表估算的參考成本；單價表為設定資料〔單價與幣別於設計定案〕。
- **通路（channel）**：請求入口別（AI 客服 web、未來 LINE 等）〔現階段單一通路，欄位預留〕。

## 範圍

### 範圍內
- 使用事件表（migration，冪等）＋ chat 路徑寫入（含串流路徑）。
- 每請求 LLM token 用量累計（貫穿主答、改寫、相關性把關、對話 brain、評審不算——評審屬回測內部流量本身）。
- 內部流量標記規則與排除機制。
- 日粒度彙總（排程或查詢時聚合，設計定案）＋歷史重算冪等。
- admin 統計 API＋後台報表頁（期間/業者/使用者類型篩選、CSV 匯出）。
- 個資最小化落地。
- 部署併統一 runbook（`docs/deployment-runbook.md`）。

### 範圍外
- 計費金額計算、費率設定、帳單/發票開立（未來另案，以本 spec 的彙總資料為輸入）。
- 既有 chat 回應行為的任何改變。
- jgb2 側的任何改動。
- 舊資料回補（現況無痕跡，統計自上線日起算）。

## 需求

### Requirement 1：使用事件記錄層

**使用者故事**：作為 JGB 營運方，我要每一次 AI 客服請求都留下一筆完整維度的使用事件，讓未來任何計費或用量分析都有不可否認的原始依據。

#### 驗收標準（EARS）
1. WHEN 任一 `/message` 請求（含串流模式）完成回應，THE SYSTEM SHALL 落一筆使用事件，至少含：vendor_id、mode、target_user、role_id、user_id、session_id、通路、processing_path／回應來源、處理耗時 ms、發生時間。
2. WHEN 請求以錯誤收場（5xx／逾時），THE SYSTEM SHALL 仍落事件並標記結果狀態（成功/失敗），失敗請求是否計費由計費模型層決定，計量層不預作排除。
3. THE SYSTEM SHALL 以 fire-and-forget 方式寫入：寫入失敗或延遲 SHALL NOT 影響回應內容、延遲或成功率（失敗僅記 log 供對帳）。
4. THE SYSTEM SHALL 不在使用事件中儲存answer 全文；問題原文之儲存與否及脫敏方案於設計定案〔個資最小化：預設傾向僅存長度與分類特徵〕。
5. THE SYSTEM SHALL 使事件寫入對主請求增加的延遲中位數 < 5ms（非同步化後量測）。

### Requirement 2：計費單位三軌捕捉

**使用者故事**：作為 JGB 營運方，計費模型還沒定案（按訊息、按對話、或按成本加成），我要現在就把三種單位的原料都抓齊，未來套用任何模型都不需回補資料。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 使「訊息數」可由事件直接 count 得出（每事件一則訊息）。
2. THE SYSTEM SHALL 使「對話數」可由事件的 session_id 去重得出，且同一 session 跨日時歸屬規則明確〔設計定案：以 session 首事件日歸屬〕。
3. WHEN 一次請求過程中發生任何 LLM 呼叫（主答合成、查詢改寫、相關性把關、對話 brain、使用者模擬——凡經統一 LLM 出口者），THE SYSTEM SHALL 累計其 prompt/completion tokens 至該筆使用事件，並記模型別。
4. THE SYSTEM SHALL 以模型單價設定表估算每事件參考成本；WHEN 單價表缺某模型，THE SYSTEM SHALL 記 token 數而成本欄留空（不臆造單價）。
5. THE SYSTEM SHALL 使 token 累計覆蓋率可驗證：對一筆已知路徑的請求，事件之 token 合計與各 LLM 呼叫回報 usage 總和一致（unit 可斷言）。

### Requirement 3：內部流量標記與排除

**使用者故事**：作為 JGB 營運方，我要機器流量（回測/迴圈/驗證）與真人流量嚴格分離，否則統計與計費依據全部失真。

#### 驗收標準（EARS）
1. WHEN 請求屬內部流量，THE SYSTEM SHALL 於事件標記 `is_internal=true` 及內部類別（backtest／loop／smoke／dev）。
2. THE SYSTEM SHALL 至少以下列規則識別內部流量：session_id 具已知內部前綴（如 `backtest_`）、請求帶內部標頭/參數〔識別規則清單於設計定案，並允許後續增補而不改程式〕。
3. THE SYSTEM SHALL 使報表與彙總預設排除內部流量，並提供顯示內部流量的切換（供成本觀測）。
4. WHERE 內部流量誤標或漏標被人工發現，THE SYSTEM SHALL 支援以規則回溯重標（更新既有事件的標記），且重標操作冪等。

### Requirement 4：彙總層（日粒度 rollup）

**使用者故事**：作為 JGB 營運方，我要日粒度的彙總數據（業者×使用者類型×通路），月結時直接取用，不需每次掃全量事件。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 提供日粒度彙總：維度含日期、vendor_id、user_type、通路、is_internal；量值含訊息數、對話數、token 合計（prompt/completion 分列）、估算成本、失敗數。
2. WHEN 彙總被重算（任意日期區間），THE SYSTEM SHALL 產出與事件層一致的結果且重算冪等（可覆蓋重跑）。
3. THE SYSTEM SHALL 使彙總查詢不影響線上服務效能〔實作方式（排程物化/查詢時聚合/物化視圖）於設計以資料量評估定案〕。
4. WHEN 某日尚無事件，THE SYSTEM SHALL 於報表呈現零值而非缺列錯誤。

### Requirement 5：統計 API

**使用者故事**：作為後台使用者，我要以 API 取得指定期間、指定業者的使用統計，作為報表與未來計費系統的資料介面。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 提供統計查詢 API：參數含期間（起迄日）、vendor_id（可多選/全部）、user_type、是否含內部流量、分組粒度（日/月）。
2. THE SYSTEM SHALL 於回應提供分組明細與總計（訊息數/對話數/token/估算成本）。
3. THE SYSTEM SHALL 要求後台認證始可存取（沿既有 admin 認證機制），且不回傳任何個資欄位〔2026-07-06 使用者改判：**提供 per-user 明細**（/api/usage/users，Top N 依訊息數）——user_id 為 JGB 系統編號非姓名（jgb2 呼叫必帶），仍受後台認證保護；被遺忘權 SQL 照舊適用〕。
4. WHEN 查詢期間超過保留上限或參數非法，THE SYSTEM SHALL 回 4xx 與明確錯誤訊息。

### Requirement 6：後台報表頁

**使用者故事**：作為 JGB 營運方，我要在後台一頁看到各業者的使用頻率——誰用得多、租客端還是業者端在用、內部消耗多少——並能匯出給財務。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 提供報表頁：期間選擇（預設本月）、業者篩選、使用者類型分列、日/月粒度切換。
2. THE SYSTEM SHALL 呈現：各業者訊息數/對話數/估算成本的排行與趨勢、使用者類型佔比、內部流量開關。
3. WHEN 使用者匯出，THE SYSTEM SHALL 產出 CSV（維度＋量值齊全，UTF-8 BOM 供 Excel 開啟）。
4. THE SYSTEM SHALL 沿後台既有版面與認證慣例，不另建入口。

### Requirement 7：個資與資料治理

**使用者故事**：作為 JGB 營運方，計量資料會長期保存並用於對外計費爭議舉證，我要它從第一天就符合個資最小化。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 不於使用事件儲存：回答全文、地址／經緯度等既有個資紅線欄位。
2. THE SYSTEM SHALL 於設計定案問題原文的處理（不存／截斷／脫敏存），並在報表層永不呈現原文。
3. THE SYSTEM SHALL 定義事件層保留期與過期處理〔設計定案；彙總層長存〕。
4. WHERE 未來需刪除特定使用者之個資（被遺忘權），THE SYSTEM SHALL 支援按 user_id 清除事件層個資欄位而不破壞彙總計數。

### Requirement 8：可靠性、回歸與部署

**使用者故事**：作為維護者，我要計量體系上線不影響任何既有行為，且部署程序與現行慣例一致。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 使既有 chat 回應行為零回歸（既有 unit/e2e 全綠；計量開關關閉時系統行為與現狀完全一致）。
2. THE SYSTEM SHALL 提供計量總開關（env），預設開；關閉時不寫事件、不影響任何請求。
3. THE SYSTEM SHALL 以冪等 migration 建表與索引，併入統一部署 runbook（`docs/deployment-runbook.md`）。
4. THE SYSTEM SHALL 為記錄層與彙總層提供 unit 測試（先紅後綠），並將「evaluation 形狀」同款不變量加入 `make audit`（事件表關鍵欄位非空率／內部流量佔比異常警示）〔稽核條目於設計定案〕。
5. WHEN 回測/迴圈在部署後執行，THE SYSTEM SHALL 使其流量出現於內部流量統計（作為標記機制的持續驗證）。

## 開放問題（設計階段定案）

1. 問題原文：不存／截斷 N 字／hash？（R1.4、R7.2）
2. 彙總實作：排程物化 vs 查詢時聚合（預估量：真人流量低頻，機器流量大——傾向查詢時聚合＋內部流量分表或分區）（R4.3）
3. 模型單價表的維護介面（設定檔 vs DB）（R2.4）
4. per-user 明細是否提供（計費通常只需 vendor 層）（R5.3）
5. 事件保留期（R7.3）
6. 通路欄位的值域（web 之外預留 LINE）（名詞定義）
