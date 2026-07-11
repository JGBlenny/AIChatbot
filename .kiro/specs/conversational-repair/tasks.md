# 實作任務：conversational-repair（對話式修繕）

> 建立時間：2026-07-11
> 需求：requirements.md（R1–R8）｜設計：design.md（7 元件）｜落差：gap-analysis.md｜研究：research.md（6 決策）
> 標記：`(P)` = 可與同層其他 `(P)` 平行
> 鐵律：**北極星腳本不得妥協**（requirements.md 目標形態）；TDD 先紅後綠；**execute 必過確認 gate 且冪等**（收齊≠送出、executed 後不重複建單）；brain 失敗絕不建單（降級一般流程）；M2（停 SOP）可逆且 prod 由使用者執行；不碰 embedding 完整性；JGB API 以 mock 驗流程（E1 真 API＝上線 gate）；交易語義全配置驅動（下一個交易面向零改引擎為目標）。

## 1. 資料底座（三項平行）

- [x] 1.1 (P) migration M1＋回復檔：`form_schemas.jgb_repair_create` vendor_id 2→NULL；dev 套用後驗證四業者 vendor_id 均可解析該表單（含 vendor 4——修復「觸發後表單載入失敗」）。
  - 需求：6.1
  - **收案註記（2026-07-11）**：目標態已達成——dev DB 與 prod dump（aichatbot_full_20260707.dump）雙查證 vendor_id 均已為 NULL（spec 前提「綁 vendor 2」過時）；四業者解析驗證通過（1/2/3/4 皆命中 vendor_id=NULL 列）。M1 migration 不需要，部署 runbook 對應步驟移除。
- [x] 1.2 (P) migration M3（加性冪等）＋`set_facet` hook（TDD）：usage_events 加 `facet_key VARCHAR(60)`、`turn_number SMALLINT`（IF NOT EXISTS）；usage_metering 新增 `set_facet(facet_key, turn_number)` 比照 set_path 房式（ctx None/finalized 靜默、截斷）＋沿用 P0 欄位偵測降級（欄位未建事件本體不受波及）；unit 矩陣。
  - 需求：7.1
- [x] 1.3 (P) `get_tenant_contracts(role_id, user_id)` mock 方法（TDD）：契約＝research 決策 1（雙證進、租約物件清單出）；mock 覆蓋 1/N/0 筆三形狀；J 清單記錄真端點需求（與 E1 一併談）。
  - 需求：2.1, 2.2

## 2. 引擎交易語義（核心）

- [x] 2.1 (P) Brain 交易範本＋schema 擴充（TDD）：conversational_step 輸出加 `action='confirm'`＋`inline_answer`（岔題即答）；conversational_rules 新增交易面向規則範本（收齊→confirm、否定→更新重確認、岔題先答再接）；unit：BrainStep 解析與驗證（含新值拒絕舊格式回退）。
  - 需求：3.1, 4.1
- [x] 2.2 引擎 confirm/execute 分支（TDD，2.1 完成後）：`SlotValue` 分型（prefill/inferred/user/candidate_pick＋confirmed）與 `TransactionState`（executed/user_turns）；confirm＝配置 `confirm_template` 組摘要＋quick_replies（✅送出/✏️修改/❌取消）；同意判定＝按鈕 value 或明確同意（引擎層非 brain）；execute 重用 `_ground_by_api` 呼 `grounding_scope.execute_endpoint`、slots→params 映射；成功回執（單號＋追蹤指引）＋`executed=true`；失敗誠實告知＋重試 quick reply（executed 不設）；冪等（executed 後同意詞回單號不重執行）；修改→brain 帶否定語境重確認；取消→既有 `_close` 丟棄槽位。unit 矩陣：冪等／失敗不設標記／修改局部重確認／取消不留殘單。
  - 需求：4.1, 4.2, 4.3, 4.4, 4.5, 3.2, 3.3, 3.4
- [x] 2.3 (P) Prefill 模組（TDD，1.3 完成後、可與 2.2 平行）：面向啟動時執行——租約 1 筆→estate 推斷槽位／N 筆→插點 A 候選／0 筆→降級文案；Vision suggested_* `confidence≥inference_confidence`（配置，預設 0.7）→分類三槽＋急迫性推斷槽位、不足→2-3 候選（插點 A 退化，不退下拉）；unit 分型矩陣（租約×信心×無圖）。
  - 需求：2.1, 2.2, 2.3, 2.4, 2.5
- [x] 2.4 image 通道（2.3 完成後）：面向進場與 `handle_conversational_session` 續跑路徑把 `image_urls`→辨識→suggested_* 依門檻併入 slots/候選（對話中補圖不中斷）；integration：續跑傳圖案。
  - 需求：2.6

## 3. 進場三路與資料 seeds

- [x] 3.1 (P) `trigger_facet_key` 參數＋`repair_enabled` gate（2.2 完成後）：chat API 選填參數（命中 config registry 且 enabled→直接 seed 面向；未命中照常管線不報錯）；gate helper 三路共用（vendor_configs 讀值預設 true，false→降級文案＋客服管道參數）；unit＋integration。
  - 需求：1.3, 1.5
- [x] 3.2 (P) Step 0.5 改道（2.3 完成後）：`is_damage` 且信心足→不打 SOP 檢索、直接 seed 修繕面向攜帶 suggested_*；非損傷/信心不足維持現行降級；非租約標的損傷由面向對話處理（決策 6，不另設分支）；unit＋既有 handle_image 測試調整。
  - 需求：1.1
- [x] 3.3 面向配置＋知識 seeds（2.2 完成後）——收案時如實回報三整合缺口（estate dict 槽位映射／Vision 名稱→ID／quick_replies 未浮出），已由缺口修復輪全數修復（prefill 扁平標量槽＋分類樹名稱→ID 解析＋回應契約透傳，834 unit 綠）：①修繕面向對話規則列（jsonb 全鍵：execute_endpoint/required_slots/confirm_template/inference_confidence/prefill_api/degraded_messages/candidate_max）②修繕意圖錨點知識（vendor_ids 空、掛「修繕報修」分類、question 主題關鍵字式）③查進度知識（action_type=api_call→jgb_repairs）——均走既有 embedding 生成；煙囪：常見問法命中分數（P0 埋點觀測 ≥0.75）＋分類路由進面向＋模糊敘述不硬開（先澄清）。
  - 需求：1.1, 1.2, 1.4, 5.1, 5.2, 8.2

## 4. 切換與四業者矩陣

- [x] 4.1 migration M2（可逆）＋停用驗證（3.3 完成後）：`vendor_sop_items` 停用 `vendor_id IN (2,4) AND next_form_id='jgb_repair_create'`（is_active=false）＋rollback（回 true）；dev 套用；驗證 vendor 2 其餘非修繕 SOP（250 條）行為不變。
  - 需求：6.3, 6.5
- [x] 4.2 四業者驗收矩陣 e2e（4.1 完成後，G-gated）：四業者各以其租客身份走情境 A——vendor 1/3 從無到有、vendor 2/4 從舊表單切新形態；decision_case 遙測佐證修繕 SOP 不再攔截；體驗一致斷言。
  - 需求：6.2, 6.4

## 5. 情境 e2e 與收案

- [x] 5.1 目標形態情境 e2e（G-gated、fixture 自建自清、臨時容器法沿用）——A 案誠實分層：文字推斷版穩定綠；帶圖 ≤3 輪版需真實圖片 URL，無圖時 skip（不假綠）：A 明確報修＋照片 **≤3 輪建單**／B 岔題先答回流／C 模糊先澄清／D 確認階段改資料重確認／E 查進度／F 直達參數進面向；每案斷言輪數與 facet 埋點入庫。
  - 需求：7.3（含 R1–R5 全情境）
- [x] 5.2 回歸與收案：既有全測試綠（FAQ 快路徑/既有診斷面向/prospect/非修繕表單零回歸）；`make audit` 全綠；P50/P90 SQL 實跑驗證（design 元件 7 查詢）；runbook 增補本案節（部署順序：M1/M3→seeds＋配置→推程式→煙囪→**M2 切換由使用者執行**→矩陣驗收；semantic-model 免重建註記；E1 真 API 上線 gate 註記）。
  - 需求：8.1, 8.3, 8.4, 7.2

---
## 實作收案註記（2026-07-12）

- **M1 免辦**：dev＋prod dump（20260707）雙查證 form_schemas.jgb_repair_create vendor_id 已為 NULL；runbook 已註記。
- **migration 位置**：M2/M3（＋rollback）落 `rag-orchestrator/database/migrations/`（根目錄 database/migrations/ 被 .gitignore `*.sql` 排除，不進版控）。
- **audit 現況**：不變量 1/2/5/6 PASS；不變量 3 FAIL 為既有 baked-image drift（app.py 等三檔本 spec 未改），部署 rebuild 後自解；不變量 4 對「修繕報修」WARN 屬預期（交易面向不需系統脈絡長文）。
- **integration 5 failed 皆本 spec 外**：4×usage_event_live（常駐容器不記帳，既有部署層問題，值得另案）＋1×帳務面向 seed 敏感度（billing spec 範疇）。
- **e2e 真跑證據**：14 passed／1 skip（帶圖 ≤3 輪版需真實圖片 URL）；e2e 輪根修 3 缺陷（confirm gate 收齊保底、rules target_user=tenant_repair、execute_result_path=data.id）。
- **prod 部署提醒**：業者 4 缺 vendor_configs `service_hotline` 鍵（gate 降級文案引用）；redis 檢索快取要清（reranker 為 stateless cross-encoder 不需重建——已查證推翻任務原假設）；M2 由使用者親自執行。

掛帳（不阻塞本 spec）：G1 真端點與 E1 一併向 jgb2 提出（J 清單）；LINE 接入（另案，E0 核實前置，本案通道無關設計即其前置）；下一個交易面向複製（驗證「零改引擎」目標）；SOP 其餘 404 條遷移（另案）；上線後 30 天 P50/P90 實測 vs 目標（R7.3 未達標觸發設計覆核）。
