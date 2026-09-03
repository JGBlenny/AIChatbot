# 研究記錄：documind-ocr-mapping

> 建立時間：2026-09-03
> 目的：記錄設計階段的技術調查、架構決策與相依性分析
> 發現流程：**light**（擴充既有 FastAPI 服務、單一新端點、無新第三方套件）；整合點大半已於 `validation_gap.md` 實查，本檔補設計所需的五項現況並落決策。

## 摘要

### 調查範圍
chatai 現有的路由／認證／計量／LLM 注入／型別慣例，以及 DocuMind 回應契約；目標是讓新端點**零改動**沿用既有機制，並把全部領域規則放進可離線測試的純函式。

### 關鍵發現
- `X-API-Key` 是全域 middleware（`app.py` 符號 `auth_enforced`），新 router **自動受保護**；計量 middleware 卻只認 `/api/v1/message`（符號 `usage_metering_middleware`）⇒ 計量必須在端點內自行 `begin`／`finalize`。
- 既有「值＋出處」物件先例：`services/jgb/repair_prefill.py` 的 slots `{value, source, confirmed}`（SlotValue）⇒ 本案 `FieldValue` 沿用命名語意並擴充 `jgb_value／confidence／raw／page`。
- repo **沒有**民國年／中文數字換算器（grep 0 檔，正對照 `datetime` 36 檔），也無 `cn2an` ⇒ 自寫封閉詞彙的決定性換算器。
- LLM 取得走 `get_llm_provider(service_name=…)` 工廠；JSON 抽取慣例 `response_format={"type":"json_object"}`（`image_recognition_service`、`knowledge_generator`）。
- 內部流量規則 `INTERNAL_RULES` 以 `session_id` 前綴（`backtest_`／`loop_`／`kcl_`／`smoke_`）判定；`begin(fields)` 只讀 `mode／role_id／target_user／vendor_id` ⇒ 本端點請求體須攜帶這些鍵才能正確落 `user_type` 與 `is_internal`。

## 研究主題

### 主題 1：計量落點——擴 middleware 還是端點內自記

**調查問題**：R9.3 要每次呼叫落 `usage_events`，但既有 middleware 只對 `/api/v1/message` 建 context。

**研究方法**：
- [x] 現有程式碼分析（`app.py` 符號 `usage_metering_middleware`；`services/usage_metering.py` 符號 `begin／set_path／add_llm_usage／finalize`）

**發現**：middleware 讀 body 後需回灌 `request._receive`（註解自陳實測會卡死），擴路徑集合等於把這段技巧套到第二條路徑；而 `begin()`／`finalize()` 是純函式＋contextvar，端點內呼叫即可，且 `finalize` 冪等。

**結論與建議**：採**端點內自記**（gap 分析方案 B）。⛔ 不動 middleware；⛔ 不得兩處都記（雙落點）。

### 主題 2：DocuMind 回應契約的可依賴面

**調查問題**：哪些欄位可信、哪些只是佔位。

**研究方法**：
- [x] 官方文件閱讀（業主提供的串接文件）
- [x] 唯讀探測（`/api/v1/usage` 200；`/api/v1/review` **404** 與文件不符；`/openapi.json` 不存在）

**發現**：頁級 `structured_data`、`field_confidences`、`needs_confirmation`、`extraction_confidence` 有值；頂層 `field_confidences` 與 `consensus` 在樣本中為空／null；`llm_postprocessed` 未觸發時為 `null` 非空物件；`contract` 型 `structured_data` 為通用三組（`contract_metadata／parties／financial_terms`），**無租約特有欄位**。

**結論與建議**：輸入模型對頂層兩鍵一律 `Optional`，R2.6 以「頂層非空優先」防未來重工；`/review` 端點不可依賴。

### 主題 3：租約特有欄位的來源（D1）

**調查問題**：`deposit_type／cycle_date／cycle／early_termination_*` 從哪來。

**發現**：DocuMind 現有型抽不到；`ocr_raw.text` 有全文可二段抽取；業主偏好「AI 不碰數字」。

⚠️ **2026-09-03 晚更正（查 `~/jgb/DocuMind` 原碼）**：「抽不到」只對了一半。`contract_field_extractor.py` 符號 `rental_fields` 已抽 14 個租約欄位（`date_start／date_end／monthly_rent／deposit／rental_address／management_fee／parking_fee／payment_day／tenant_*／landlord_*`），任一命中就在 `structured_data` 多掛一組 **`rental_terms`**；`types.py` 沒宣告它、DocuMind 測試也沒測它、chatai 從未消費它（`CONTRACT_SOURCE_MAP` 無 `rental_terms.*`）。樣本裡看不到是因為 `contract_patterns.py` 76 條樣式有 63 條要求「標籤：值」制式寫法（`押金：`、`租期：`）。仍缺：押金金額／月數分欄（同一 `deposit` 鍵兩種樣式混收）、繳費週期 `cycle`、`early_termination_*`、「壹年」型租期。`lease` 在 `document_types.py` 只是 `contract` 的別名（`LEGACY_TYPE_ALIASES`）。

**結論與建議**：設計同時容納兩條路——主路徑等 DocuMind `lease` 型（映射表可配置），次路徑 `SecondPassExtractor` 以 `ENABLE_OCR_SECOND_PASS` 旗標守門、預設關；LLM 只回原文片段（`evidence_span`），數值一律交決定性換算器。✅ **2026-09-04 業主定案 A**：chatai 消費 `rental_terms`（`CONTRACT_RENTAL_MAP`），次路徑作廢。

### 主題 4：承租方姓名切分（D3）

**發現**：JGB `to_user_last_name／to_user_first_name` 分欄；DocuMind 只回 `party_b` 全名；台灣複姓有限（歐陽、司徒、張簡、范姜…）。

**結論與建議**：自寫 `NameSplitter`：命中複姓表取兩字為姓，否則取首字；**一律**把兩欄加入 `needs_confirmation`（切分屬猜測），並保留 `party_b_full_name` 原串。⚠️ 待 JGB 團隊確認複姓慣例（Q5）。

## 技術選型

### 選型 1：中文數字／民國年換算

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| A 自寫 `FieldNormalizer` | 零依賴、詞彙封閉、`raw` 可逆對照易保證 | 要自己寫完整測試 | 合約用字固定 |
| B `cn2an` 套件 | 覆蓋廣 | 多一個正式 image 依賴；「元整」尾綴處理需驗 | 開放文本 |

**最終選擇**：A。**理由**：合約與謄本的數字詞彙是封閉集合（壹～玖、拾佰仟萬、元整、個月、年），自寫 200 行內可完成且每條規則對應 R5 一組正反例。

### 選型 2：端點形狀（D2）

| 方案 | 優點 | 缺點 |
|------|------|------|
| A 新資源 `POST /api/v1/ocr-mapping/{document_type}` | 契約獨立、不污染 `/message`、計量與測試邊界清楚 | 多一支 router |
| B `/api/v1/message` 加 `action` | 呼叫端只記一個 URL | `/message` 已 5,000 行、圖片 3 張上限與 vision 路徑會干擾；計量語意混雜 |

**最終選擇**：A（待業主確認）。

## 相依性分析

### 外部 API 與服務

| 服務名稱 | 版本 | 用途 | 文件連結 | 注意事項 |
|---------|------|------|---------|---------|
| DocuMind `POST /api/v1/analyze` | 未版本化 | 本案**不呼叫**；只消費其回應 JSON | 業主提供的串接文件（`http://54.248.201.66:8085/docs` 為前端頁面，非 OpenAPI） | 無認證、公網、單 worker、36 s/頁、`needs_review` 幾乎恆 true；`/api/v1/review` 實測 404 |
| OpenAI gpt-4o-mini | 依 `OPENAI_MODEL` | R8 第二段抽取（旗標守門） | 既有 `llm_provider` | temperature ≤ 0.3、`json_object`、逾時 8 s |

### 函式庫與套件

無新增。⛔ 不引入 `cn2an`。

## 現有程式碼分析

**檔案位置與符號**：
- `routers/document_converter.py` 符號 `router = APIRouter(prefix=…)` — router 骨架先例
- `routers/images.py` 符號 `HTTPException(status_code=413` — 大小上限先例
- `services/usage_metering.py` 符號 `begin／set_path／add_llm_usage／finalize／INTERNAL_RULES`
- `services/jgb/repair_prefill.py` 符號 `SlotValue` — 值＋出處物件先例
- `services/llm_provider.py` 符號 `get_llm_provider` — LLM 注入
- `routers/chat.py` 符號 `VendorChatResponse` — Pydantic `Field(..., description=)` 慣例
- `tests/unit/api/test_api_request_contract_req.py` — 以 Pydantic 直接驗契約、不用 TestClient
- `tests/unit/` 既有領域：`_meta api backtest category chat_flow conversational decision forms retrieval security sop usage` ⇒ 新增 `ocr_mapping/`

**整合點**：
1. `app.py`：`include_router(ocr_mapping.router)` 一行。
2. 端點內：`usage_metering.begin({...})` → `set_path("ocr_mapping")` → （R8）`add_llm_usage` → `finalize(status, http_status, db_pool)`。
3. `get_llm_provider(service_name="ocr_second_pass")`（僅 R8）。

## 效能考量

| 指標 | 目標值 | 測試方法 | 備註 |
|------|--------|---------|------|
| 純規則路徑 P95 | < 2 s | 20 頁 fixture 連打 20 次 | 全在記憶體，實際預期 < 200 ms |
| R8 路徑 P95 | < 10 s | 同上，開旗標 | 受 OpenAI 延遲主導；只送含關鍵詞頁 |
| 請求體上限 | 2 MB | 超過回 413 | env `OCR_MAPPING_MAX_BODY_MB` |

## 安全性考量

### 威脅模型
- 個資（所有權人、承租人姓名／電話／地址）流經本端點。
- 呼叫端偽造：無 key 的第三方直接打端點。
- 日誌洩漏：`print()` 把 `ocr_raw.text` 印進容器日誌。

### 緩解措施
- 沿用 `X-API-Key` middleware（`RAG_API_AUTH_ENFORCE`）；本端點 ⛔ 不列入豁免。
- 日誌只記欄位名、`source`、`confidence`；⛔ 不記 `value／raw／ocr_raw.text`。
- `usage_events` 不落任何欄位值。
- R8 只把 `ocr_raw.text` 送往既有 OpenAI 通道，⛔ 不新增第三方。

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|------|------|------|------|---------|------|
| DocuMind `contract` 型抽不到租約欄位 | 技術 | 高 | 高 | D1 定案 A：消費 `rental_terms`；缺欄由 DocuMind 補樣式 | 已緩解（2026-09-04） |
| 沒有真實 fixture | 時程 | 高 | 高 | 單測用文件樣本；e2e 暫掛至 line-bot 提供 | 開放 |
| OCR 噪音讓 `evidence_span` 比對失敗 | 技術 | 中 | 中 | 正規化空白／全半形後比對；失敗降 `absent` | 已緩解（設計） |
| 條款粗切不穩 | 技術 | 低 | 高 | R7.1 已降級為粗切＋LIFF 可編輯 | 已緩解（需求） |
| 計量雙落點 | 技術 | 中 | 低 | 只在端點內記；middleware 路徑不變 | 已緩解（設計） |

## 開放問題

### Q1 DocuMind 能否開 `lease` 型？
**影響範圍**：`contract_mapper` 映射表。**決策狀態**：✅ 已解——`lease` 只是 `contract` 的別名，`rental_terms` 早已存在；剩「補樣式」（tasks 12.3）。

### Q2 真實謄本／合約回應各一份
**影響範圍**：R10.2／10.4、驗收矩陣 3–4。**決策狀態**：待 line-bot 團隊。

### Q5 JGB 複姓慣例
**影響範圍**：`NameSplitter` 複姓表。**決策狀態**：待 JGB 團隊。

## 時間軸

| 日期 | 活動 | 結果 | 後續行動 |
|------|------|------|---------|
| 2026-09-03 | 需求 v2、gap 分析、light discovery | 五項現況落檔、四個決策成形 | 業主核可 design；Q1／Q2／Q5 外部答覆 |
| 2026-09-04 | 查 `~/jgb/DocuMind` 原碼；D1 定案 A；12.1 TDD 24 案例、212/212 | `rental_terms` 早已存在但 chatai 未消費；R8 作廢 | rebuild、真實合約取樣、DocuMind 補樣式（12.3／12.4） |
| 2026-09-03 | 實作 1.1–8.2、10.2、10.3；兩輪獨立驗證（宣稱＋對抗）＋ :8100 實打 | REFUTED 9 條（P2×7）全處置：8 條 FIX、N2 DEFER；發現「單元綠、實打紅」兩次（視窗偏移） | 收案標準改為「改完必 rebuild 實打」；D1 建議選 A（DocuMind 開 lease 型）；等 Q2 真實 fixture |

## 參考資源

- 需求：`requirements.md`；落差：`validation_gap.md`
- line-bot：`~/jgb/line-bot-platform/docs/chatai-integration-scenario.md` v5 §7、`jgb-contract-api-spec.md` §2／§2.5
- chatai steering：`.kiro/steering/tech.md`（非同步優先、env 預設值、`print()` 日誌）、`testing-code.md`（分層與 marker）
