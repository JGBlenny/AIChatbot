# 需求規格：conversational-repair（對話式修繕）

> 建立時間：2026-07-11　階段：requirements-generated　語言：zh-TW
> 定位：target-first 路線的主線正案（docs/conversation-first-architecture-assessment.md §6.6 拍板）——引擎交易能力＋修繕作為第一個交易面向。
> 對碼前提（已於架構評估階段查實）：引擎 grounding 已重用 `api_call_handler.execute_api_call`（通道存在一半）；引擎無表單調用與確認語義；`jgb_repair_create` 表單綁 vendor 2 且表單解析帶 vendor 過濾（vendor 4 觸發後疑似載入失敗）；修繕 SOP 分佈 vendor 2/4 各 75 條、vendor 1/3 零觸發。

## 目標形態（拍板基準，2026-07-11——本 spec 的北極星，不得被實作妥協）

```
租客：「冷氣壞了」（附照片）
系統：認出報修意圖＋照片辨識損壞
     「幫您報修 XX 路 5 樓的冷氣——照片看起來是不製冷，發生多久了？急嗎？」
租客：「昨天開始，蠻急的，這要自己出錢嗎」
系統：（先答費用政策）「牆內管線與設備由業者負責…
      確認送出：XX路5F／冷氣不製冷／昨天起／緊急——送出嗎？」
租客：「好」
系統：已建單 #R2071，之後隨時問「修得怎樣」可查進度。
```

設計判斷：**物件不問**（租約帶入）、**分類不下拉**（推斷＋確認）、**岔題是常態**（答完回流）、**寫入必過確認 gate**。

## 已拍板決策（2026-07-11）

1. 綁定優先：身份先於對話，引擎不支援無身份槽位暫存（本案 Web 驗收下身份恆存在）
2. 全業者同步切換：上線即停用 vendor 2/4 修繕 SOP（is_active=false 可逆），棄灰度
3. 輪數驗收：情境 A 類 e2e ≤3 輪；上線後 P50≤4／P90≤6（含岔題）；輪數埋點進計量
4. 推斷失敗退化：給 2-3 候選讓使用者選一輪，不退回三層下拉
5. 範圍：Web 通道驗收、通道無關設計；LINE gateway 另案，於 LINE 上線會合

## 名詞定義

- **修繕面向**：對話引擎的第一個「交易面向」——與既有診斷面向（查詢唯讀）的差異在於收斂動作是**執行寫入**（create_repair）而非回答。
- **確認型槽位**：系統能推斷出值的槽位（物件、分類），以「陳述＋允許否定」呈現，不主動開口問；推不出的才是**詢問型槽位**（急迫性）。
- **確認 gate**：全部槽位收齊後、寫入前的一次性摘要確認——使用者明確同意才執行，收齊≠送出。
- **岔題回流**：對話中的問題（費用、時程）即時以知識/lookup 回答後，自動接回槽位收集，不中斷面向會話。
- **輪數**：使用者送出訊息的次數（開場陳述算第 1 輪）；岔題輪計入 P50/P90 統計、不計入 e2e ≤3 判準（e2e A 類為無岔題腳本）。

## 範圍

### 範圍內
- 引擎交易語義：確認 gate、image 槽位（對話中收照片）、執行結果回傳處理（成功回執／失敗誠實告知）。
- 槽位預填：身份→租約→物件；照片/描述→分類/項目/原因推斷；確認型槽位機制。
- 修繕交易面向配置（資料驅動，沿用面向配置機制）＋通用意圖錨點知識（vendor_ids 空）＋查進度知識（api_call→jgb_repairs）。
- 隨行 bug 修：`jgb_repair_create` 表單 vendor_id 2→NULL（migration）＋`vendor_configs.repair_enabled` 開關。
- 切換：停用 vendor 2/4 修繕 SOP 的 migration（is_active=false，可逆）。
- 輪數與面向遙測埋點；四業者驗收矩陣；e2e 情境 A–F。

### 範圍外
- LINE gateway 與綁定機制（既有另案，E0 官方文件核實前置）；本案僅要求對話邏輯通道無關。
- SOP 全面退役與 404 條遷移（另案，本案僅停用修繕子集）。
- 其他交易面向（退租、帳務操作——複製本案形態，後續案）。
- 舊表單機制的改動（表單機保留原樣，僅 schema 供欄位契約引用）。
- JGB 真實 API 切換（E1，上線 gate，開發以 mock 驗流程）。

## 需求

### Requirement 1：意圖進場

**使用者故事**：作為租客，我用自然的方式表達報修（一句話、一張照片、或點按鈕），系統就進入報修對話；表達模糊時系統先弄清楚我要什麼，不硬開流程。

#### 驗收標準（EARS）
1. WHEN 已識別身份的 b2c 使用者以明確報修語句（含常見說法：報修/壞了/漏水/不通等）或損傷照片進場，THE SYSTEM SHALL 進入修繕交易面向並以目標形態應答（情境 A）。
2. WHEN 使用者敘述模糊（如「房子有點問題」），THE SYSTEM SHALL 先澄清意圖而非開啟流程；澄清後意圖明確 SHALL 進入面向（情境 C）。
3. WHEN 使用者經按鈕/直達參數進場，THE SYSTEM SHALL 進入同一修繕面向（同一槽位邏輯，跳過意圖辨識），而非舊逐欄位表單流程（情境 F）。
4. WHEN 使用者訊息為一般資訊問答（非交易意圖），THE SYSTEM SHALL 走既有檢索快路徑，行為與現狀完全一致。
5. WHERE 業者之 `repair_enabled` 為關閉，THE SYSTEM SHALL 不進入面向，回降級文案並提供該業者客服管道（configs 參數）。

### Requirement 2：槽位預填與確認型槽位

**使用者故事**：作為租客，系統知道的事不要再問我——我的住處系統本來就知道，照片和描述已經說明了壞什麼，讓我確認就好。

#### 驗收標準（EARS）
1. WHEN 面向啟動且使用者身份含有效租約，THE SYSTEM SHALL 自動帶入物件（estate）為確認型槽位，不開口詢問。
2. WHEN 使用者名下有多筆有效租約，THE SYSTEM SHALL 將物件轉為選擇項（列出讓使用者選一輪）。
3. WHEN 使用者提供照片或文字描述，THE SYSTEM SHALL 推斷分類/項目/原因並以確認型槽位呈現於回覆或確認摘要中。
4. WHEN 分類推斷信心不足，THE SYSTEM SHALL 退化為給出 2–3 個候選讓使用者選一輪；SHALL NOT 退回三層下拉逐級選擇。
5. THE SYSTEM SHALL 僅對推斷不出且必要的槽位開口詢問（如急迫性），使情境 A 類（明確陳述＋照片、單一租約、無岔題）以 ≤3 輪完成。
6. WHEN 使用者在對話中補充照片，THE SYSTEM SHALL 將其納入當前面向會話的槽位（image 槽位），不中斷流程。

### Requirement 3：對話進行——岔題、修改、取消

**使用者故事**：作為租客，我在報修過程中想到什麼就問什麼、說錯了就改，系統要跟得上，而不是把我當跑偏的表單填寫者。

#### 驗收標準（EARS）
1. WHEN 使用者在面向進行中提出問題（費用/時程/規定），THE SYSTEM SHALL 以知識/lookup/參數即時回答，並於同一回覆自然接回槽位收集（情境 B）。
2. WHEN 使用者在任一階段（含確認 gate）修改先前提供的資訊，THE SYSTEM SHALL 更新對應槽位並重新呈現受影響的確認內容（情境 D）。
3. WHEN 使用者表達取消（不報了/取消），THE SYSTEM SHALL 結束面向會話、丟棄已收集槽位、不留殘單，並禮貌收尾。
4. WHEN 引擎決策失敗（brain 異常），THE SYSTEM SHALL 安全降級至既有一般流程；SHALL NOT 在未經確認 gate 的情況下建單。

### Requirement 4：確認 gate 與交易執行

**使用者故事**：作為租客，送出前我要看到完整摘要並親自同意；系統也不能因為我多說一次「好」就建兩張單。

#### 驗收標準（EARS）
1. WHEN 必要槽位全部收齊，THE SYSTEM SHALL 呈現一次性確認摘要（物件/設備/狀況/急迫性）並等待明確同意；收齊 SHALL NOT 等同送出。
2. WHEN 使用者明確同意，THE SYSTEM SHALL 呼叫建單 API（create_repair）並回覆回執：單號、後續處理說明、追蹤方式（情境 A 收尾）。
3. WHEN 建單 API 失敗，THE SYSTEM SHALL 誠實告知失敗並提供重試或替代管道；SHALL NOT 假裝成功。
4. THE SYSTEM SHALL 使同一會話中重複的同意訊息不重複建單（冪等）。
5. WHEN 使用者於確認摘要否定某項推斷（「不是客廳是臥室的」），THE SYSTEM SHALL 更新後重新確認，不重跑整個流程。

### Requirement 5：完成後追蹤

**使用者故事**：作為租客，報修後我隨時想知道進度，一句「修得怎樣了」就要有答案。

#### 驗收標準（EARS）
1. WHEN 使用者詢問修繕進度（自然問法），THE SYSTEM SHALL 以其身份查詢（jgb_repairs）並回覆工單狀態列表或指定單狀態（情境 E）。
2. WHEN 使用者名下無工單，THE SYSTEM SHALL 誠實告知並引導報修。

### Requirement 6：業者維度與切換

**使用者故事**：作為平台營運方，四個業者的租客要在同一天獲得一致的新報修體驗，而現在壞著的（vendor 4）與缺著的（vendor 1/3）一次補齊。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 以 migration 將 `jgb_repair_create` 表單升為通用（vendor_id=NULL）——修復 vendor 4「觸發後表單載入失敗」並使欄位契約全業者可用。
2. THE SYSTEM SHALL 新增 `repair_enabled` 業者開關（預設開啟），關閉行為見 R1.5。
3. THE SYSTEM SHALL 以 migration 停用 vendor 2/4 之修繕 SOP（is_active=false，附回復 migration）——上線即全業者走新形態。
4. WHEN 四業者各以其租客身份走情境 A，THE SYSTEM SHALL 呈現一致體驗（驗收矩陣：vendor 1/3 從無到有、vendor 2/4 從舊表單切新形態），並以檢索遙測（decision_case）佐證修繕 SOP 不再攔截。
5. THE SYSTEM SHALL 不影響 vendor 2 其餘非修繕 SOP（250 條）之行為。

### Requirement 7：可觀測性

**使用者故事**：作為架構決策者，輪數承諾要可測量，之後的交易面向複製要有數據依據。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 於使用事件記錄面向對話的輪數與面向識別（沿用計量 fire-and-forget 原則）。
2. THE SYSTEM SHALL 使「修繕對話 P50/P90 輪數」可直接以 SQL 查得。
3. WHEN 部署完成，情境 A 類 e2e SHALL ≤3 輪；上線後統計目標 P50≤4、P90≤6（含岔題），未達標 SHALL 觸發設計覆核而非默默接受。

### Requirement 8：回歸與品質約束

**使用者故事**：作為系統維護者，新形態上線不能弄壞任何現有能力。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 使 FAQ 檢索快路徑、既有診斷面向、prospect 對話、非修繕表單流程的行為與現狀完全一致（回歸驗證）。
2. THE SYSTEM SHALL 不觸碰 embedding 完整性（question_summary/embedding 欄位與流程）；新增知識條目走既有 embedding 生成。
3. THE SYSTEM SHALL 使對話邏輯通道無關（身份與訊息經同一 chat API 契約），LINE 接入時不需修改面向邏輯。
4. WHEN 全部測試執行，既有 unit/integration/e2e SHALL 全綠；新增 e2e 覆蓋情境 A–F 與 R6.4 驗收矩陣。

## 依賴與假設

- 依賴既有機制：面向配置（資料驅動）、grounding→execute_api_call 通道、Step 0.5 損傷辨識、雙證身份、P0 觸發透傳與分數埋點。
- 假設：租約→物件可由既有 JGB API（jgb_estates/contracts）以身份查得〔design 階段確認端點與欄位〕；分類推斷以描述＋照片＋修繕分類樹為輸入〔推斷方法 design 定案：LLM 分類 vs 辨識結果映射〕。
- E1（JGB 真 API）為上線 gate，開發以 mock 驗流程；部署與 prod 操作照既定紀律（runbook、破壞性 migration 使用者執行）。
