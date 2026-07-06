# 落差分析：contract-conversational-facets

> 建立時間：2026-07-02　依據：requirements.md（R1–R11）× 現行碼盤查（rag-orchestrator）× research.md（jgb2 ground truth）
> 結論先講：**底座幾乎全現成**——面向掛載、換面向、候選辨識、API grounding、決定性 formatter 骨架都在；真正的程式落差集中在**一處**（formatter 的面向感知），其餘是資料與知識工程。

## 一、現況元件盤點（可重用）

| 元件 | 位置 | 對本 spec 的支持 |
|---|---|---|
| 三層系統脈絡疊加 | `services/system_context.py` | `_fetch_category_chain` 沿 category_config 父鏈載母/子列——**加面向＝加資料列**（R1.3） |
| 面向集合自動衍生 | `conversational_engine.py::_domain_faces:128` | 未明列 faces 時取**母分類全部子分類**——5 個新子分類建好即自動進入換面向集合（R8.1），零設定 |
| 中途換面向 | `prepare:410-415`（護欄4） | `state.face` 切換＋換脈絡；`collected_fields` 在 state 上**跨面向自然保留**——R8.2 免改程式 |
| 候選辨識/指涉補識別 | 插點A `prepare:322-349`、確定性識別 `prepare:351-385` | 鎖定合約機制全現成（R2.1/R7.3），slot 讀設定零硬編 |
| API grounding 三態 | `_ground_by_api:508-608` | 1/0/N 分路、0 筆清槽、N 筆候選、facts 餵 LLM 不餵原始碼（R7） |
| 決定性 decode/可否操作 | `services/jgb/contracts.py`（536 行） | `ContractBit`、`get_current_stage`、`check_can_invite/move_in/move_out/early_termination/renew` ——**退租收尾/簽署排障的原料大半已在**（R3.1/R6.1） |
| 進場路由 | `chat.py::config_for_category`＋知識掛面向分類 | 每面向一個 config（topic_scope.category=面向值）＋錨點知識即通（R1.2），前 spec 已驗證 |
| 後台設定頁 | `ConversationalConfigView.vue` | api grounding 欄位已支援，新 config 可後台維護 |
| 測試分層 | conftest 集中、unit/int/e2e（合約診斷 327/24/12 全綠） | 新面向照抄測試型態（R11.3） |

## 二、逐需求落差與實作選項

### R1 資料驅動底座 — 落差＝純資料
5 個 category_config 子分類（parent=`系統合約`）＋每面向系統脈絡列＋5 個對話 config＋錨點知識。零程式。4500 字上限：母『系統合約』994 字現況，每個子面向脈絡估 300–600 字，逐面向載入不疊加，安全。

### R2/R3/R6 三個診斷樹 — **主程式落差：formatter 的面向感知**
現況鏈路：`_ground_by_api → execute_api_call(api_config, session_data, form_data)`——**`user_message`/`state.face` 都沒傳進 formatter**（`prepare` 有、`_ground_by_api:541` 沒帶），`jgb/contracts.py::_build_response` 靠 user_question 關鍵字路由操作意圖，在對話路徑上實際拿到空問句 → 走 `_format_status_response` 預設。狀態判斷面向恰好夠用；**異動三出口/收尾下一步/簽署排障需要 formatter 知道當前面向**才能產對的 fact 集。選項：

- **選項 A（建議）：傳 face ＋ user_message 進 formatter，face→fact-builder 註冊表**。`_ground_by_api` 把 `state.face`、`user_message` 帶入 `execute_api_call`（handler 已有 `user_input` 參數通道）；`jgb/contracts.py` 加 face 對應的 fact-builder（`合約異動`→can_edit 三出口 facts、`退租收尾`→步驟鏈 facts、`簽署排障`→簽署進度 facts）。面向字面寫在 **JGB 專屬 formatter**——「零硬編」原則管的是通用引擎，JGB formatter 本就是領域檔（feedback_jgb_separate_file），不違反。
  - 代價：engine 改 1 個呼叫點＋contracts.py 加 3 個 builder；風險低。
- **選項 B：formatter 產超集 facts（狀態＋全部 can_*＋簽署＋收尾），LLM 按面向脈絡自選**。零路由改動，但 grounding 變長、雜訊多，違背「決定性選材」精神，且簽署/收尾 facts 常態多餘。
- **選項 C：每面向各自 endpoint 包裝**。過度設計——同一 status-overview 資料，不該複製端點。

### R2 異動申請書出口 — 落差小（persona＋知識，程式零改）
「異動項目/異動前→後」由 brain `extracted_fields` 收進 `collected_fields`（persona 規則宣告槽位即可，機制現成）；收斂時 LLM 按系統脈絡模板產可抄錄文字，範本/提交指引/擁有者提醒放面向系統脈絡或知識。**待決（設計）**：可抄錄文字要不要 formatter 級的決定性模板（穩定格式）vs LLM 合成（口語彈性）——建議脈絡內給定格式骨架、LLM 填值，收斂後 e2e 驗格式。

### R3 退租收尾的帳單封存步驟 — **結構性缺口：單 config 單 endpoint**
`grounding_scope` 一個 config 只宣告一個 endpoint；收尾要 contracts（旗標）＋ bills（封存，G3）。選項：
- **選項 A（建議，分兩階）**：G3 未上線前照 R3.3 降級（通用封存指引）；G3 上線後於 **fact-builder 內做第二次 bills 查詢**（formatter 層 composite，engine 不改多 endpoint 機制）。
- 選項 B：grounding_scope 支援 endpoints 陣列（engine 通用化）。改動大、其他面向用不到，暫不。
- 選項 C：請 jgb2 出 close-out summary 端點。依賴外部時程，列 G 清單以外的未來項。

### R4 續約 — 落差＝資料＋知識修正
`check_can_renew` 已在；facts 補 `date_end` 剩餘天數、`father_id`/`is_newest`（G4 存在性驅動）。知識兩處照程式版（配額真因、免註冊不重簽）——**產製時以 research.md 為準**（R9.4）。

### R5 建約引導 — 落差＝純資料（無 grounding）
config `select` 用既有知識 grounding（category/vector），不走 api——engine 現成分支（`prepare:451-453`）。兩輪分流由 persona 規則實現（售前同型態已驗證）。轉面向（R5.3/R5.4）走既有 face switch。

### R6 簽署排障 — 落差＝formatter builder＋G1/G2 存在性驅動
現況欄位（bit 4/8、to_user_email/phone、to_user_connect）可出「誰沒簽＋發送通道＋綁定」三 facts；G1/G2 欄位**存在才輸出**對應 facts（builder 內 `if field in row`，R10.3 天然滿足）。標準自助排查步驟（瀏覽器/簡訊攔截）＝知識，不進 formatter。

### R7 決定性計算 — 現成原則的延伸
新增 builder 全走 check_* 模式（回 `{ok, missing, facts}`）；點交點退互不相依已在 `check_can_move_out` 講死，收尾 builder 重用即不回歸（R3.2）。

### R8 面向路由 — 落差≈0
faces 自動衍生＋state 保留已證。**一個注意點**：換面向只換脈絡**不換 config**——進場 config 的 grounding_scope 沿用。合約 6 面向同用 status-overview，無礙；唯「建約引導」（無 api）進場後切到「合約異動」（要 api）時，config 的 select 仍是知識型 → 異動樹拿不到 API grounding。**待決（設計）**：(a) 接受降級（引導使用者換句重進，錨點會路由到異動 config）；(b) face 切換時同步換 config（機制改動，波及售前護欄）。建議 (a)＋錨點涵蓋度補強，設計階段定案。

### R9 知識產製 — 工程流程（無程式落差）
help API 抓取（getGroups/post 已實測）→ 理解情境改寫（不搬運）→ 掛面向分類＋target_user → 人工審核。工具腳本一次性、不 commit（feedback_no_commit_scripts）。量體：官方 45 篇＋Excel 合約 137 筆聚類 → 估每面向 8–15 筆知識＋1 列脈絡。

### R10 G1–G4 — 外部依賴，契約已定義（research.md §四）
AIChatbot 端一律存在性驅動，兩端可獨立部署（R10.2/R10.3 由選項 A builder 寫法直接滿足）。

### R11 回歸 — 現成防護網＋一個測試層要求
狀態判斷 363 測試全綠為基線；80% 檢索基準集重跑；錨點 e2e 型態照 d33f995。
**e2e 必走正常管線**（R11.4/R11.5）：進場（口語第一句 → 意圖分類 → 檢索 → reranker → config_for_category）與收斂後/scope=switch 的重路由，都依賴真實檢索＋reranker 排序——直呼引擎的測試驗不到「錨點知識排得上來」這件事。既有 e2e 12 案即此型態，新面向照抄；integration 環境需 reranker 服務可用（檢索測試覆蓋現況已知 reranker 只在 integration 層可驗）。
**部署綁定**：新錨點知識/系統脈絡列上線時 reranker semantic model 必須重建（既有部署慣例），列入 tasks 的部署步驟。

## 三、整合點與風險

| 風險 | 等級 | 緩解 |
|---|---|---|
| formatter 面向感知改動波及狀態判斷（同檔案） | 中 | 選項 A 以「新增 builder＋預設 fallback 現行為」寫法；狀態判斷測試矩陣先綠再動 |
| 建約/續約錨點與售前知識搶路由（prospect vs property_manager） | 中 | target_user 隔離＋回測 80% 基準；錨點知識掛 property_manager |
| 換面向不換 config 的 grounding 錯配（R8 待決） | 中 | 設計階段定案；先以錨點涵蓋補強 |
| 異動申請書產出格式漂移 | 低 | 脈絡給格式骨架＋e2e 斷言關鍵段落 |
| G1–G4 時程不可控 | 低 | 存在性驅動，缺欄位分支自動降級（R7.4） |

## 四、需研究／待決（設計階段）

1. formatter 面向感知的傳遞介面（選項 A 的參數形狀：face 直傳 vs 併入 user_input）。
2. 退租收尾 bills 二次查詢的位置（builder 內 vs handler 層）與快取。
3. R8 換面向不換 config 的定案（接受降級 vs 換 config）。
4. 異動申請書可抄錄文字的格式骨架與驗證斷言。
5. 5 個 config 的 persona 規則分工：一份母規則＋面向差異段 vs 五份獨立（維護成本 vs 精準度）。

## 五、建議策略（供設計參考，非定案）

**擴充（extend）為主**：engine 僅 `_ground_by_api` 一個呼叫點加參數；`jgb/contracts.py` 加 3 個 face fact-builder（異動/收尾/簽署）＋續約 facts 補欄位；其餘全是資料（category_config、系統脈絡列、config、知識）與知識工程。不新建服務、不動 schema、不動檢索。實作順序照 research.md §七 優先序：異動 → 收尾 → 續約 → 建約 → 簽署（G1/G2 到位前先出降級分支）。

## 下一步

```bash
/kiro:spec-design contract-conversational-facets        # 需求已審視後進設計
/kiro:spec-design contract-conversational-facets -y     # 快速通道（自動核准需求）
```
