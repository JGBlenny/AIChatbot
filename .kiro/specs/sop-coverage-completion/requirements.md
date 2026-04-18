# 需求規格：sop-coverage-completion

> **功能名稱**：包租/代管業 SOP 知識庫覆蓋率補齊
> **建立時間**：2026-04-17T00:00:00+08:00
> **語言**：Traditional Chinese (zh-TW)

---

## 簡介

包租/代管業 AI 客服的 SOP 知識庫目前僅 19 筆，集中在寵物飼養與設備維修，覆蓋率約 56.7%。租客常見問題涵蓋租賃契約、租金費用、押金、入退住、提前解約、修繕、居住規範、社區管理、安全保險、稅務、爭議處理等 13 大類約 80 個子題。本規格的目標是盤點完整流程清單、比對缺口、批量生成缺少的 SOP、審核同步，最後跑回測驗證覆蓋率並以聚焦 LLM 判定確認答案是否回答到租客問題。

## 範圍

- **包含**：
  - 包租/代管業 SOP 流程清單盤點（13 大類，~80 子題）
  - 現有 SOP 缺口比對與分類
  - 缺口 SOP 的批量生成與品質驗證
  - 生成 SOP 的人工審核與同步到正式庫
  - 回測驗證覆蓋率改善
  - 聚焦 LLM 判定：「答案是否回答到租客的問題」

- **不包含**：
  - 修改 retriever pipeline 分數機制（屬於 retriever-similarity-refactor）
  - 知識完善迴圈的流程架構變更（沿用 backtest-knowledge-refinement）
  - 前端管理介面新功能開發
  - 非流程類知識（系統配置查詢、API 查詢類問題）

- **相鄰期望**：
  - SOPGenerator（gpt-4o-mini）已可運作，能接收主題輸入並產出 SOP
  - 回測框架（AsyncBacktestFramework）已可運作，可批量執行回測
  - Embedding 服務已可運作，生成的 SOP 可自動產生向量

---

## 需求

### Requirement 1：SOP 流程清單盤點

**Objective:** As a 知識庫管理者, I want 一份包租/代管業的完整 SOP 流程清單, so that 知道需要建立哪些 SOP 項目。

#### Acceptance Criteria

1. The 系統 shall 提供一份流程清單，涵蓋以下 13 大類：
   - 制度與法規總覽
   - 租賃契約
   - 租金與費用
   - 押金（保證金）
   - 入住與退租
   - 提前解約與違約
   - 修繕與維護
   - 居住使用規範
   - 社區管理與管委會
   - 安全與保險
   - 稅務相關
   - 爭議處理與申訴
   - 戶籍與居住證明
2. The 流程清單 shall 在每個大類下列出具體子題，每個子題對應一個可獨立回答的租客問題
3. The 流程清單 shall 參考現有資料來源（`data/20250305 租管業 SOP_1 客戶常見QA.xlsx`、`data/20250305 租管業 SOP_2 管理模式 基礎-改.xlsx`）確保涵蓋實務常見問題
4. The 流程清單 shall 標註每個子題適用的業態類型（包租業 / 代管業 / 兩者皆適用）

### Requirement 2：清除現有 SOP 並重新盤點

**Objective:** As a 知識庫管理者, I want 先清除現有不完整的 SOP 再從頭盤點, so that 新建的 SOP 是一套完整一致的知識庫，不受舊資料干擾。

#### Acceptance Criteria

1. When 流程清單建立完成後, the 系統 shall 先將目標業者的現有 SOP 項目全數停用（標記為 `is_active = false`），而非直接刪除（保留歷史紀錄）
2. The 系統 shall 記錄被停用的 SOP 清單（ID、item_name、停用時間），供日後比對或回溯
3. When 現有 SOP 停用完成後, the 系統 shall 將所有流程清單子題視為 `missing`，進入全量生成流程
4. If 管理者需要保留特定 SOP（例如已經過多次人工校正的項目）, the 系統 shall 支援逐筆排除，被排除的 SOP 維持 `is_active = true`

### Requirement 3：SOP 批量生成

**Objective:** As a 知識庫管理者, I want 系統能批量為缺口子題生成 SOP, so that 能快速補齊知識庫。

#### Acceptance Criteria

1. When 現有 SOP 清除完成後, the 系統 shall 能對流程清單中所有子題（扣除排除保留的項目）批量生成 SOP
2. The 生成的每筆 SOP shall 包含：
   - 簡短標題（15 字以內）
   - 客服回答內容（200-500 字）
   - 搜尋關鍵字
   - 觸發模式（auto / manual / immediate）
   - 後續動作類型（form_fill / api_call / none）
3. The 生成的 SOP 內容 shall 從租客（房客）角度撰寫，直接回答租客的問題，提供具體步驟或指引
4. The 生成的 SOP shall 不得包含捏造的電話號碼、Email、網址、具體金額或百分比
5. The 系統 shall 對每筆生成的 SOP 執行品質驗證：
   - 內容不得少於 100 字
   - 不得包含模糊敷衍語句（如僅回答「請洽管理師」而無具體說明）
   - 不得使用「SOP」「流程」「規範」等行話
6. When 生成 SOP 時偵測到高相似度的現有知識（相似度 >= 0.85）, the 系統 shall 標記重複警告，避免產出重複內容

### Requirement 4：SOP 分類與歸屬

**Objective:** As a 知識庫管理者, I want 生成的 SOP 自動歸入正確的分類, so that 知識庫結構清晰易於管理。

#### Acceptance Criteria

1. The 系統 shall 為 13 大類中尚未存在的類別自動建立 SOP 分類（category）
2. The 生成的每筆 SOP shall 歸入對應的分類與群組
3. When 一個子題涉及金流操作（如繳租金、退押金）時, the 系統 shall 標註適用的金流模式（公司代收 / 房東直收）
4. The 系統 shall 確保同一分類下的 SOP 項目彼此不重疊，每筆 SOP 只回答一個具體面向

### Requirement 5：人工審核與同步

**Objective:** As a 審核者, I want 所有生成的 SOP 經過人工審核後才進入正式庫, so that 確保知識品質。

#### Acceptance Criteria

1. The 系統 shall 將所有生成的 SOP 標記為待審核狀態（`pending`）
2. The 審核者 shall 能對每筆 SOP 執行以下操作：批准、拒絕、或修改後批准
3. When 審核者批准一筆 SOP 時, the 系統 shall 立即同步到正式 SOP 庫並自動產生向量嵌入
4. The 系統 shall 支援批量審核（一次審核多筆 SOP）
5. When 審核者修改 SOP 內容後批准時, the 系統 shall 使用修改後的內容同步，而非原始生成內容

### Requirement 6：回測驗證覆蓋率

**Objective:** As a 品質負責人, I want 用回測驗證 SOP 補齊後的覆蓋率改善幅度, so that 確認知識庫補齊有效。

#### Acceptance Criteria

1. When SOP 審核同步完成後, the 系統 shall 能執行一輪完整回測（使用與先前相同的測試集）
2. The 回測結果 shall 提供補齊前後的比較：
   - pass_rate 變化
   - 各失敗原因（NO_MATCH / LOW_CONFIDENCE / SEMANTIC_MISMATCH）的數量變化
   - 新覆蓋的子題數量
3. The 回測 shall 目標 pass_rate 達到 75% 以上（從目前 ~57% 提升）
4. When 回測中仍有 fail 案例時, the 系統 shall 將失敗案例依原因分類，識別出「仍缺 SOP」vs「有 SOP 但答案品質不佳」的區別

### Requirement 7：聚焦 LLM 答案品質判定

**Objective:** As a 品質負責人, I want 回測中加入 LLM 判定「答案是否回答到租客問題」, so that 能找出有知識但答非所問的案例。

#### Acceptance Criteria

1. When 回測執行完成後, the 系統 shall 對每筆回測結果額外執行一次 LLM 判定
2. The LLM 判定 shall 回答一個核心問題：「這個答案是否從租客角度回答了租客的問題？」
3. The LLM 判定結果 shall 為三級制：
   - `yes`：答案有回答到租客問題
   - `partial`：答案部分回答，但有遺漏或偏離
   - `no`：答案沒有回答到租客問題
4. The LLM 判定結果 shall 附帶一句理由說明（50 字以內）
5. When LLM 判定結果為 `no` 時, the 系統 shall 將該案例的最終判定改為 fail，即使 confidence 分數通過
6. The 回測結果摘要 shall 包含 LLM 判定的統計：`yes` / `partial` / `no` 的數量與比例

---

## 下一步

需求審核通過後執行：

```bash
# 選擇性：盤查現有實作差距
/kiro-validate-gap sop-coverage-completion

# 進入設計階段
/kiro-spec-design sop-coverage-completion
```
