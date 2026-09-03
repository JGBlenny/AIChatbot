# 實作落差分析：documind-ocr-mapping

> 建立時間：2026-09-03　依據：requirements.md（requirements-generated，尚未核可）
> ⚠️ `.kiro/settings/rules/gap-analysis.md` 不存在，本檔以「現況→缺口→方案→待研究」四段自成框架。
> 所有「現況」皆為本日 grep／read 實查，附可 grep 的符號；行號不當事實。

## 一、現況：能直接沿用的東西

| 能力 | 現況 | 證據（符號） | 對本案的意義 |
| --- | --- | --- | --- |
| 新 router 掛法 | `APIRouter(prefix="/api/v1/…")` ＋ `app.include_router` | `routers/document_converter.py` 符號 `router = APIRouter(prefix=…)`；`app.py` 符號 `app.include_router` | R9 端點照抄即可 |
| API key 認證 | 全域 middleware，`auth_enforced()` 時除豁免路徑外一律驗 `X-API-Key` | `app.py` 符號 `is_exempt, auth_enforced, verify_api_key`；`services/api_key_auth.py` | R1.6 **零改動**即滿足 |
| LLM JSON 抽取 | 既有 `response_format={"type":"json_object"}` 慣例；`LLMProvider.chat_completion(model, messages, temperature, max_tokens)` 抽象 | `services/image_recognition_service.py`、`services/knowledge_generator.py`、`services/llm_provider.py` 符號 `chat_completion` | R8（若 D1 選 B）有現成骨架 |
| 大小上限與 413 | `HTTPException(413)`、`MAX_SIZE` 常數 | `routers/images.py`、`routers/videos.py` | R1.5 照抄 |
| 合約欄位名 | mock fixture 已用 JGB 原名 `rent／deposit_amount／date_start／date_end` | `services/jgb/contract_fixtures.py` 符號 `project_contract` | R4 鍵名有先例，⛔ 不另創 |
| 請求契約單測 | 不用 TestClient，直接建構 Pydantic 模型驗證 | `tests/unit/api/test_api_request_contract_req.py` 符號 `VendorChatRequest(` | R10 契約測試照此模式 |
| 分層測試與 marker | unit／integration／e2e 三層、`@pytest.mark.req` | `.kiro/steering/testing-code.md` | R10.1／10.5 |

## 二、缺口：本案必須新建或改動的

### 缺口 1｜計量 middleware 只認 `/api/v1/message`　`R9.3`

```python
# app.py 符號 usage_metering_middleware
metered = (request.url.path == "/api/v1/message" and request.method == "POST" and _um.is_enabled())
```

⇒ 新端點**不會**被計量。R9.3 要求每次呼叫落 `usage_events`（含 R8 的 LLM 用量）。

| 方案 | 做法 | 代價 |
| --- | --- | --- |
| A 擴 middleware 路徑集合 | 把 `== "/api/v1/message"` 改成 `in METERED_PATHS` | 動到 usage-metering spec 的既有行為；需補該 spec 的測試；⚠️ middleware 讀 body 後回灌 `_receive` 的技巧要沿用 |
| B 端點內自行 `begin()`／`finalize()` | 不動 middleware，在 handler 內呼叫 `_um.begin(fields)`＋出場落事件 | 與既有「其餘路徑零觸碰」註解一致；但兩處落點語意要對齊（finalize 冪等） |

⚠️ 待研究：`usage_metering.begin()` 讀的 `fields` 是請求體的哪些鍵（`session_id` 前綴決定 `is_internal`）——本案請求沒有 `session_id`，內部標記如何判？

### 缺口 2｜沒有民國年／中文數字換算工具　`R5`

grep `民國|壹|貳|cn2an|roc_year|to_gregorian` 於 `services/`、`routers/` ＝ **0 檔**（正對照 `datetime` 36 檔）；`requirements.txt` 無 `cn2an`（正對照 `openai` 1 行）。

| 方案 | 做法 | 代價 |
| --- | --- | --- |
| A 自寫決定性換算器 | `services/document_field_normalizer.py`：民國三格式、大寫數字（壹～玖拾佰仟萬）、千分位、租期詞 | 全在掌控內、零依賴；要寫完整測試（R5 每條正反例） |
| B 引入 `cn2an` | 中文數字交給套件，日期仍自寫 | 多一個依賴進正式 image；套件對「壹萬參仟捌佰元整」的「元整」尾綴處理要驗 |

建議 A：詞彙集封閉（合約用字固定），自寫比引依賴可控，且 R5.6 要求 `raw` 可逆對照，自寫容易保證。

### 缺口 3｜日期輸出格式與 JGB 不同　`R5 vs JGB`

需求書 R5 定 `YYYY-MM-DD`；chatai 送 JGB 的既有先例是 **`Ymd` 整數**（`jgb_system_api.py` mock：`"date_start": 20260401`），line-bot 建約規格 §2 也寫 `date_start: 20250121`。

| 方案 | 做法 | 代價 |
| --- | --- | --- |
| A 只回 ISO | LIFF 送 JGB 前自己轉 | 轉換責任外移；兩端各寫一次 |
| B 只回 `Ymd` 整數 | 與 JGB 同形 | 房東在 LIFF 看到 `20250121` 不友善 |
| C 兩者都回：`value`（ISO，給人看）＋ `jgb_value`（`Ymd` int，給 JGB） | 一個欄位值物件多一鍵 | 契約稍胖，但零轉換責任外移 |

建議 C；需回頭修 R5.1／5.2 與 R9.1 的欄位值物件定義。

### 缺口 4｜多頁合併與衝突標記　`R2`

現有程式沒有任何「跨頁欄位合併」邏輯（DocuMind 回應是逐頁 `structured_data`）。全新。
⚠️ 待研究：DocuMind 頂層 `field_confidences` 與 `consensus` 兩鍵在樣本裡皆為空／null——若 DocuMind 未來自己做跨頁共識，R2 可退為 fallback。設計時要以「頂層有值優先、頁級合併為 fallback」防止重工。

### 缺口 5｜`unmapped_clauses` 的條款切分　`R7.1`

要從 `ocr_raw.text` 切出「條款句段」。純規則（以「第N條」「一、」「（一）」「\n」切）可做到粗切；「已被欄位吸收」的判定需要對照 R4 映射到的 `raw` 片段做去重。
⚠️ 風險：OCR 全文的斷行與噪音（信心度 0.16–0.70）會讓切分不穩。建議 R7.1 在 design 明訂為「粗切＋去重，⛔ 不求精」，並讓 LIFF 顯示為可編輯清單。

### 缺口 6｜R8 第二段抽取的成本與延遲（僅 D1 選 B）

12 頁合約 `ocr_raw.text` 約 12 × 1–2K 字 ⇒ 單次 prompt 15–25K tokens（gpt-4o-mini ≈ $0.004）；延遲 3–8 s。R9.4 的 P95 < 10 s 勉強可達，需限制只送含關鍵詞（押金／繳／解約）的頁。
⚠️ 待研究：`evidence_span` 驗證（R8.3）對 OCR 噪音的容忍度——原文片段可能因 OCR 錯字而 exact-match 失敗，需定義模糊比對門檻。

### 缺口 7｜沒有真實 DocuMind 回應可當 fixture　`R10.2`

手上只有 DocuMind 文件裡的一頁樣本（謄本）。合約型**一份都沒有**。
⚠️ 阻擋 design 的驗收設計：需 line-bot 團隊提供 ≥1 份謄本、≥1 份合約的真實回應（去識別化）。⛔ 本分析未呼叫 DocuMind（單 worker、無認證、要付費，且無測試 PDF）。

## 三、實作路線比較

| 路線 | 內容 | 適合 | 不適合 |
| --- | --- | --- | --- |
| **新建**（建議） | `routers/ocr_mapping.py` ＋ `services/ocr_mapping/`（`transcript_mapper.py`、`contract_mapper.py`、`field_normalizer.py`、`page_merger.py`、`clause_splitter.py`） | 與既有圖片路徑零耦合；純函式好測；符合 `structure.md` 命名 | — |
| 擴充 `image_recognition_service` | 把 OCR 映射塞進既有服務 | — | 該服務是 vision 分類器、綁 `/message` 與 3 張上限；語義不同、會污染修繕路徑 |
| 擴充 `document_converter` | 沿用其 job 模型 | 若未來要做非同步 | 本案已拍板同步無狀態；job 表是多餘的 |

## 四、待研究清單（進 design 前解）

| # | 問題 | 誰能答 |
| --- | --- | --- |
| Q1 | D1：DocuMind 能否開 `lease` 型？若能，`structured_data` 鍵集合為何？ | DocuMind 維護者 |
| Q2 | 真實謄本／合約回應各一份（去識別化）作 fixture | line-bot 團隊 |
| Q3 | `usage_metering.begin(fields)` 對無 `session_id` 請求的 `is_internal` 判定 | chatai（讀 `usage_metering.py` 符號 `INTERNAL_RULES`） |
| Q4 | DocuMind 頂層 `field_confidences`／`consensus` 何時會有值 | DocuMind 維護者 |
| Q5 | 承租人姓名切分（D3）：JGB `to_user_last_name` 對複姓的實際慣例 | JGB 團隊 |
| Q6 | 日期輸出格式（缺口 3 方案 C）需回修 R5／R9 | 業主核可需求時一併定 |

## 五、對需求書的回修建議（核可前）

- R5.1／5.2、R9.1：欄位值物件加 `jgb_value`（缺口 3）。
- R2：加「DocuMind 頂層 `field_confidences`／`consensus` 非空時優先採用」（缺口 4）。
- R7.1：改為「粗切＋去重，⛔ 不求精；LIFF 端可編輯」（缺口 5）。
- R9.3：明訂採缺口 1 的方案 A 或 B（影響 usage-metering spec）。
- R10.2：加註「fixture 由 line-bot 提供，取得前 e2e 項目暫掛」（缺口 7）。
