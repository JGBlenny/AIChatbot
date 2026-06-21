# 落差分析：option-routing（選項層決策樹路由）

> 建立時間：2026-06-20
> 修訂：2026-06-20 依需求補入 G1–G5（URL 葉出口、不報價合規、競品分支、方案分級、起手式兩題）
> 對象：requirements.md（R1–R10）
> 性質：擴充型（Extension）——建立於既有 form-chaining 之上，整合導向探索。

## 分析摘要

- **絕大多數機制已存在**：串接引擎、葉答案、合併呈現、會話切換、深度/循環防護、取消、容錯皆由 form-chaining 提供，可直接重用。
- **核心機制落差只有一處**：「後續路由的來源」目前綁在**表單層**（`source_form_schema['next_form_id']`），需改為讀「**被選中的選項**」。
- **關鍵整合阻點**：`_maybe_chain_next_form(form_schema, session_state)` 呼叫時**未帶 `collected_data`**，而被選中選項值正在其中——需把選項值傳進路由判斷。
- **葉出口新增第三型（URL/公開頁）**：`VendorChatResponse` 無專屬連結欄位，需設計如何承載（answer 內嵌連結 / quick_reply 帶 URL / 新欄位）。
- **R9/R10 多屬資料與既有路徑、非新機制**：不報價是「內容紀律 + 導向 URL」；競品比較是「被問才回」的知識答案（走既有檢索/答案路徑），**不是選單選項路由**。
- **presales 場景為純資料落差**：售前知識（C1–C6/B1/B2/E1–E3）與 CTA 表單（`trial_form`/`demo_form`）DB 內不存在，需新增資料（不需新表、不改 mode）。

## 現有元件與重用對照

| 需求 | 既有元件（可重用） | 位置 |
|------|------------------|------|
| 串接後續表單、深度/循環防護、容錯 | `_maybe_chain_next_form` | `form_manager.py:~491` |
| 第一欄呈現契約 | `_present_first_field` | `form_manager.py:~455` |
| 完成後串接整合、合併呈現、旗標契約 | `_complete_form`（串接段 ~2331） | `form_manager.py:~2334` |
| 葉答案（選項→知識） | `branch_answer`（`_handle_branch_answer`） | `api_call_handler.py:496` |
| select 選項解析（數字/標籤→value） | `collect_field_data`（~1187） | `form_manager.py` |
| 取消、最新列更新（Fix #1） | 取消守衛（~745）、`_update_session_state_sync`（WHERE 最新 id） | `form_manager.py` |
| 會話切換（同 session_id 取最新） | `get_session_state`（`ORDER BY id DESC`） | `form_manager.py:136` |
| 競品/模組/合規回覆 | 既有知識檢索 + 答案路徑（b2b scope） | `vendor_knowledge_retriever_v2.py`、`llm_answer_optimizer.py` |

→ **R2/R5/R6/R7 的「執行面」幾乎零落差**，只差「路由來源」這一個輸入。

## 核心機制落差與整合阻點

### 落差 1：路由來源——表單層 → 選項層
`_maybe_chain_next_form` 現況：
```python
next_form_id = source_form_schema.get('next_form_id')   # 表單層、與選項無關
```
需改為：找出**終端 select 欄位** → 從被選中值找到對應 option → 讀該 option 的路由（`next_form_id` / 葉出口）；無選項層路由時 **fallback 回表單層 `next_form_id`**（R3）。

### 落差 2（阻點）：被選中選項值未傳入路由判斷
`_complete_form` 呼叫 `_maybe_chain_next_form(form_schema, session_state)`（`form_manager.py:2334`）——**沒帶 `collected_data`**。而 `session_state['collected_data']` 可能是完成前快照，不可靠。
- **影響**：要讀「被選中選項」，路由函式必須拿到**新鮮的 `collected_data`**（或預先解出的 selected option）。
- **取值路徑**：終端欄位 `fields[-1]`（或 `current_field_index` 對應欄位）若為 select → `field_name` → `collected_data[field_name]` = 被選 value → 在該欄位 `options` 找到對應 option → 讀其路由。
- **向後相容**：簽章新增參數需給預設值，避免影響既有 form-chaining 呼叫。

### 落差 3：選項資料模型 + 葉出口三型（含新增 URL 型）
`form_schemas.fields[].options` 目前每項僅 `{label, value}`。需新增**可選**欄位承載路由，葉出口共三型：
```json
{"label":"個人房東","value":"individual","next_form_id":"presales_individual_units"}   // 後續子樹
{"label":"手續費誰負擔","value":"fee","answer_kb":3551}                                  // 知識答案
{"label":"想看定價","value":"pricing","link":"/pricing"}                                 // 導向連結（新型）
```
- 純 JSONB 加欄位，**不需 migration / 不需新表**（向後相容：沒帶就沿用舊行為）。
- **URL 葉出口無專屬回應欄位**（`VendorChatResponse` 只有 `answer` / `quick_replies` / `video_url`）。落地選項：
  1. **answer 內嵌 markdown 連結**（最省事，等於收斂回「一筆含連結的知識答案」，可能根本不需 `link` 欄位）；
  2. **`quick_replies` 帶 URL**（需確認 `QuickReply` 結構是否支援連結動作）；
  3. **新增回應欄位**（`cta_link` 之類，schema 變更）。
- 與既有 `branch_answer` mapping（`api_config.params.mapping`）的關係需設計定案：選項內嵌 `answer_kb` vs 沿用 api_config mapping，語意重疊需擇一或定優先序。

### 落差 4：presales 場景資料（純資料、無程式落差）
- **知識**：售前 C1–C6（模組）/ B1（分流）/ B2（痛點對照）/ **E1–E3（競品事實/優勢/準則）** → `knowledge_base` 新增列，掛 b2b（`business_types` 含 `system_provider`）。
- **表單**：起手式分流（個人/團隊 + 戶數）、痛點選單、各子樹 → `form_schemas` 新增 select 表單。
- **CTA**：`trial_form`（`POST /api2/trial_form`）、`demo_form`（`POST /api2/demo_form`）→ `form_schemas` 新增 `call_api` 表單（對齊既有 demoForm 欄位）。
- **方案分級邏輯**（R8.2/8.3）：個人方案 10/20/30 戶、50 戶象徵分界、31–49 依「有無團隊」——因起手式已先問個人/團隊，戶數子樹可在「個人」分支下表達，分界由身分問題先行解決。
- **不存在於 DB**：以本 session 查證，售前/試用/demo 知識 0 筆、trial/demo 表單不存在。

### 落差 5：R9/R10 多屬內容紀律與既有路徑（非選項路由機制）
- **R9 不報價 / IoT 不主動**：主要靠**知識內容紀律**（方案/IoT 知識不寫價格）+ 「問價格」選項採 **URL 葉出口**（`/pricing`，見落差 3）。**機制面幾無新增**，落在資料與內容審核。
- **R10 競品比較**：「**被問才回**」屬使用者主動提問 → 走**既有知識檢索 + 答案路徑**（KB-E1/E2/E3 以 b2b scope 建好即可），**不是選單選項路由**。本需求對 option-routing 機制**無落差**，落在資料 + 既有檢索行為（中立陳述靠知識內容與答案優化提示）。
- → R9/R10 主要是**資料與內容**工作，設計時應明示「不靠新機制、靠資料」，避免誤把它們當路由功能。

## 實作取向評估

### 取向 A：在 `_maybe_chain_next_form` 內擴充選項層解析（推薦）
- 在現有函式開頭加「解出被選中選項路由」邏輯：有 → 用選項路由（依葉出口型別分派：子樹 / 知識 / URL）；無 → 沿用現有表單層 `next_form_id`。
- 需調整呼叫簽章把 `collected_data` 傳入（落差 2，預設參數保相容）。
- **優點**：單一收斂點、最小改動、自然向後相容、三型葉出口 + 子樹皆可在此分派。
- **缺點**：函式職責略增（可抽 `_resolve_selected_route` helper 維持可讀）。

### 取向 B：在 `_complete_form` 串接段前先解出 route，再傳給串接
- `_complete_form` 算出 selected option route → 傳路由結果給（精簡版）串接函式。
- **優點**：`_complete_form` 已有 `collected_data`，取值最直接。
- **缺點**：路由邏輯散到 `_complete_form`，與串接判斷分離。

### 取向 C：葉答案沿用 api_config，子樹/URL 用選項層
- 葉答案完全沿用既有 `branch_answer`（api_config mapping），選項層只新增 `next_form_id`（子樹）與 `link`（URL）。
- **優點**：不與既有 mapping 語意衝突，落差最小。
- **缺點**：葉答案與子樹/URL 設定分處兩地，設定者心智負擔。

> 取向 A + C 可組合：路由來源在選項上、知識葉答案沿用 api_config、URL 視落差 3 結論決定是否需 `link` 欄位——設計階段定案。

## 風險與待研究

| 項目 | 說明 | 階段 |
|------|------|------|
| URL 葉出口承載方式 | 無專屬回應欄位；answer 內嵌連結 vs quick_reply vs 新欄位 | 設計 |
| 選項層 vs api_config 葉答案語意重疊 | 兩處都能定義「選項→知識」，需定優先序或擇一 | 設計 |
| `collected_data` 傳入路徑 | 改 `_maybe_chain_next_form` 簽章影響既有呼叫 → 預設參數保相容 | 設計/實作 |
| 終端 select 的判定 | 多欄位表單中「哪個 select 決定路由」（最後一欄？特定欄位？） | 設計 |
| 擴充共存最終定案 | R3 已採「選項優先、表單層 fallback」，設計需明確 precedence 與非-select 情形 | 設計 |
| R9 不報價落地 | 靠內容紀律 + URL 葉出口；需內容審核確保方案/IoT 知識不含價格 | 實作/資料 |
| R10 競品為知識答案非路由 | 確認「被問才回」走既有檢索；中立性靠知識內容與答案優化，非機制 | 設計/資料 |
| 方案分級表達 | 戶數 + 有無團隊兩維；確認用「個人分支下的戶數子樹」表達 | 設計 |
| presales 知識內容撰寫 | 內容品質（依 steering knowledge.md 標準）非機制問題，量大 | 實作/資料 |
| 入口觸發 | 範圍外；b2b mode 已驗證可觸發（金流 0.975），presales 觸發知識需建好 | 範圍外 |

## 結論與下一步

- **機制落差小且集中**：核心只有「路由來源下放選項層」+「把選項值傳進路由判斷」+「葉出口新增 URL 型」三點，其餘重用 form-chaining。
- **R9/R10 不是機制、是資料**：不報價靠內容紀律 + URL 葉出口；競品靠既有知識檢索——設計需明示，避免膨脹機制範圍。
- **資料落差大但單純**：presales 樹是純資料新增（知識含競品 + 選單/CTA 表單），不需新表、不改 mode。
- 建議設計階段定案：① 選項路由 schema（三型葉出口 + 子樹；`answer_kb` vs api_config）② URL 葉出口承載方式 ③ 終端 select 判定 ④ `collected_data` 傳入方式 ⑤ 擴充共存 precedence ⑥ 方案分級的樹表達。

下一步：`/kiro:spec-design option-routing`
