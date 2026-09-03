# 實作任務：documind-ocr-mapping（DocuMind OCR 結果 → JGB 欄位映射）

> 建立時間：2026-09-03
> 需求：requirements.md v3（R1–R10）｜設計：design.md（9 元件、6 決策）｜落差：validation_gap.md（7 缺口）｜研究：research.md
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後的補充測試
> ⚠️ 規則／模板缺席：`.kiro/settings/rules/tasks-*.md` 與 `templates/specs/tasks.md` 不存在，格式沿用 `conversational-repair/tasks.md`。
> 鐵律：**AI 不碰數字**（金額、日期、月數只能來自 OCR 文字或決定性換算）；**押金二選一 ⛔ 不推算**；**未映射條款 ⛔ 不丟**；**`needs_review=true` 恆為 `draft`**；TDD 先紅後綠、每條需求正反例各一；⛔ 不呼叫 DocuMind、⛔ 不碰檔案、⛔ 不寫 JGB；測試一律容器內（Python 3.11）＋ `@pytest.mark.req("documind-ocr-mapping:N.M")`；日誌與 `usage_events` ⛔ 不落個資。

## 1. 契約與測資底座（兩項平行）

- [x] 1.1 (P) 契約模型（TDD）：`services/ocr_mapping/models.py`——DocuMind 輸入模型（`DocuMindPage`／`OcrMappingRequest`，頂層 `field_confidences`／`consensus` 皆 Optional、`llm_postprocessed` 可為 null）、`FieldValue`（`value／jgb_value／confidence／confidence_source／source／raw／page／conflicts`）、`MappingResult`、`Provenance`、`TRANSCRIPT_FIELDS`／`CONTRACT_FIELDS`／`REQUIRED_FOR_WRITE` 常數；unit 比照 `tests/unit/api/test_api_request_contract_req.py` 直接以 Pydantic 驗契約：缺 `pages` 拒收、`source` 值域封閉、同型 `fields` 鍵集合恆定。新領域目錄 `tests/unit/ocr_mapping/`。
  - 需求：1.1, 3.5, 4.3, 7.4, 9.1, 9.2
  - **收案註記（2026-09-03）**：RED→GREEN 11 測試（`tests/unit/ocr_mapping/test_models_contract_req.py`），全套 unit 2023 過、無回歸（既有紅 `test_verdict_ruler_req` 不計）；`services/ocr_mapping/models.py` 落 `TRANSCRIPT_FIELDS`／`CONTRACT_FIELDS`／`REQUIRED_FOR_WRITE`＋`MappingResult` 鍵集合 validator＋`empty_fields()`。
- [x] 1.2 (P) 測資 fixture：把 DocuMind 串接文件的謄本 4 頁樣本落成去識別化 JSON（所有權人改假名）；依文件 `contract` 型 schema 手構一份合約樣本並**明標「非真實回應」**；兩份放 `tests/unit/ocr_mapping/fixtures/`。⚠️ 真實回應待 line-bot 提供（Q2），到位後以同名覆蓋、⛔ 不改測試。
  - 需求：10.2
  - **收案註記（2026-09-03）**：`tests/unit/ocr_mapping/fixtures/documind_transcript_sample.json`（4 頁，去識別化、含空頁與 null llm_postprocessed）、`documind_contract_sample.json`（3 頁，⚠️ 明標非真實、含民國／西元跨頁衝突）；`test_fixtures_req.py` 2 測試驗形狀合法。

## 2. 決定性換算器（兩項平行；⛔ 無 LLM、⛔ 無猜測）

- [x] 2.1 (P) 日期換算（TDD）：`field_normalizer.normalize_date`——民國三格式（`中華民國NNN年M月D日`／`NNN/M/D`／七碼 `NNNMMDD`）與西元三格式（`YYYY/M/D`／`YYYY-MM-DD`／`YYYY年M月D日`）→ `NormalizedDate(iso, ymd, raw, calendar)`；每格式正例＋一組不可解析反例（回 None）；`raw` 必含原文全段。
  - 需求：5.1, 5.2, 5.6
- [x] 2.2 (P) 金額／面積／租期／繳費日換算（TDD）：`normalize_amount`（壹～玖拾佰仟萬＋元整、千分位；含「約」「以上」→ None）、`normalize_area`（去千分位與單位）、`normalize_lease_months`（壹年→12、貳年→24、N個月→N；其他→None）、`normalize_cycle_date`（「每月五日前」→5；1–31 外→None）；每函式正反例各 ≥2。
  - 需求：3.2, 4.1, 5.4, 5.5
  - **收案註記（2026-09-03，2.1＋2.2）**：`services/ocr_mapping/field_normalizer.py`；RED→GREEN 57 測試（`test_field_normalizer_req.py`：民國三格式＋西元三格式＋八碼、5 種中文大寫金額、面積、租期年＋月、繳費日；反例 22 組全回 None）；全套 unit 2080 過、無回歸。中文數字採封閉詞彙自寫（`_cn_to_int`），⛔ 未引入 cn2an。

## 3. 多頁合併

- [x] 3.1 `page_merger.merge_pages`（TDD，1.1 完成後）：單頁非空採用並記 `page`；多頁相同取 `confidence=max`、`page=首見`；多頁不同取 `field_confidences` 最高者、其餘進 `conflicts`；`llm_postprocessed=None` 的頁照常參與；各頁 `needs_confirmation` 取聯集；頂層 `consensus` 有該欄位時優先且不再頁級合併（unit 斷言「不做兩次合併」）。
  - 需求：2.1, 2.2, 2.3, 2.4, 2.5, 2.6
  - **收案註記（2026-09-03）**：`services/ocr_mapping/page_merger.py`（`merge_pages`／`collect_needs_confirmation`／`MergedField`，支援點路徑與葉名信心度）；RED→GREEN 11 測試（含同分取首頁、consensus 優先不再合併、page_level 補位）。

## 4. 謄本映射

- [x] 4.1 `transcript_mapper.map_transcript`（TDD，2.2、3.1 完成後）：五欄原名映射；`area` 走 `normalize_area`（`source=derived`）；`building_number` 空且 `land_number` 非空 → `provenance.notes` 記「可能為土地謄本」、⛔ 不把地號填建號；`owner` 多人（「、」「及」）→ `owners[]`＋`raw` 保留；缺 `field_confidences` 者以 `extraction_confidence` 補位並標 `confidence_source=page_level`；以 1.2 謄本 fixture 跑通。
  - 需求：3.1, 3.2, 3.3, 3.4, 3.5
  - **收案註記（2026-09-03）**：`services/ocr_mapping/transcript_mapper.py`；**10** 測試（fixture 端到端、面積 derived、土地謄本註記不填建號、多所有權人陣列、page_level 信心度、衝突透傳）。

## 5. 合約映射（5.1／5.2 平行，5.3 收斂）

- [x] 5.1 (P) 押金二選一規則＋突變控制（TDD，2.2 完成後）：`deposit_rule.decide_deposit`——金額原文→`deposit_type=1`＋`deposit_amount`、`deposit` absent；月數原文→`deposit_type=0`＋`deposit`、`deposit_amount` absent；兩者並存→以金額為準、月數進 `raw`、列 `needs_confirmation`；判不出→三欄 absent、`deposit_type` 列 `needs_confirmation`；三欄各自標 `source`。**突變控制**：測試檔內含一支把 `deposit_amount ÷ rent` 寫回 `deposit` 的注入版本，斷言 6.5 的測試在注入後必紅（比照 `scripts/audit/checks/*.py --self-test` 精神）。
  - 需求：6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 10.3
  - **收案註記（2026-09-03）**：`services/ocr_mapping/deposit_rule.py`（`decide_deposit`＋不變式 `assert_deposit_exclusive`）；15 測試，含**突變控制兩向**（÷rent 回填月數、×rent 回填金額皆被不變式擋下）＋正對照。
- [x] 5.2 (P) 承租方姓名切分（TDD）：`name_splitter.split_name(full, policy)`——`NamePolicy.split`：複姓表（歐陽／司徒／張簡／范姜／…可配置）命中取兩字否則首字，兩欄**恆**進 `needs_confirmation`；`NamePolicy.keep_full`：只回 `party_b_full_name`；兩策略皆保留全名。⚠️ 複姓表待 JGB 慣例（Q5），先以常見表落地、可配置。
  - 需求：4.1
  - **收案註記（2026-09-03）**：`services/ocr_mapping/name_splitter.py`（`NamePolicy.split／keep_full`、複姓表 20 組可配置）；**10** 測試。全套 unit 2128 過、無回歸。
- [x] 5.3 `contract_mapper.map_contract`（TDD，2.1、3.1、5.1、5.2 完成後）：依需求 4.1 表映射（`effective_date→date_start`、`signing_date→lease_signing_date`、`contract_amount→rent`、`currency` 原值⛔不預設 TWD、`payment_deadline→cycle_date` 僅可決定性解析時、`party_a*` 不映射）；`date_end` 缺而 `ocr_raw.text` 有租期 → `date_start＋月數` 推算、`source=derived`、列 `needs_confirmation`；`CONTRACT_FIELDS` 每欄都回物件（absent 亦然）；`REQUIRED_FOR_WRITE` 任一 absent → 列 `needs_confirmation`；`payment_method` 非空原樣進 `unmapped_clauses`；民國／西元同文件不一致 → 高信心者為值、其餘 `conflicts`、列 `needs_confirmation`；回傳 `absorbed_raws` 供第 6 節去重。以 1.2 合約 fixture 跑通。
  - 需求：4.1, 4.2, 4.3, 4.4, 4.5, 5.3
  - **收案註記（2026-09-03）**：`services/ocr_mapping/contract_mapper.py`（`CONTRACT_SOURCE_MAP`、租期視窗→`date_end`、押金視窗→二選一、同日期不同曆法不算衝突）；11 測試。⚠️ 順帶抓到 `_VAGUE` 把「簽**約**時」誤判為模糊量詞 ⇒ 押金整欄 absent，已修（約 只在後接數字／幣別且非簽約／契約／合約一部分時才算）。

## 6. 未映射條款

- [x] 6.1 `clause_splitter.split_clauses`（TDD，5.3 完成後）：以「第N條」「一、」「（一）」與換行**粗切**；保留含金額／期間／義務語（不得／應／須）者；片段出現在任一 `absorbed_raws` 中者剔除；⛔ 不摘要、不改寫、不翻譯；寵物／吸菸／訪客類一律進陣列、⛔ 不映射到 `smoke_detector`。unit：三類正例＋「已被 rent 的 raw 吸收」反例。
  - 需求：7.1, 7.2, 7.3
  - **收案註記（2026-09-03）**：`services/ocr_mapping/clause_splitter.py`（換行／第N條／N、／（N）粗切，金額／期間／義務語三類保留，absorbed 去重，逐字子串）；10 測試。

## 7. 編排與草稿語意

- [x] 7.1 `mapper.run_mapping`（TDD，3–6 完成後）：依 `document_type` 分派 4.1／5.3；彙整 `needs_confirmation` ＝ DocuMind 聯集 ∪ 衝突欄位 ∪ 必填缺漏 ∪ 押金待選，去重且順序穩定；`status`：`needs_review=true` 或任一 `REQUIRED_FOR_WRITE` absent → `draft`，否則 `ready`；`Provenance` 透傳 `review_item_id`／`documind_estimated_cost`／`mapping_version`；空 `pages` 或全空 `structured_data` → 200 `draft`、全欄 absent、`needs_confirmation` 列全部必填（⛔ 不 500）。unit：謄本與合約各一條端到端純函式測試＋空頁測試。
  - 需求：1.4, 7.5, 7.6, 9.1, 9.2
  - **收案註記（2026-09-03）**：`services/ocr_mapping/mapper.py`（同步、無 I/O；needs_confirmation 四來源聯集去重；status 規則；謄本五欄任一 absent 亦 draft）；9 測試含兩份 fixture 端到端與空頁／全空 structured_data。

## 8. 端點、認證與計量（兩項；8.2 需 8.1）

- [x] 8.1 Router（TDD，7.1 完成後）：`routers/ocr_mapping.py`——`POST /api/v1/ocr-mapping/{document_type}`；路徑與請求體 `document_type` 不一致 → 400 `DOCUMENT_TYPE_MISMATCH`；不在 `{transcript, contract}` → 400 `UNSUPPORTED_DOCUMENT_TYPE`；請求體 > `OCR_MAPPING_MAX_BODY_MB`（預設 2）→ 413 `BODY_TOO_LARGE`（比照 `routers/images.py`）；Pydantic 失敗 → 422 `INVALID_DOCUMIND_PAYLOAD`；`app.py` `include_router` 一行；⛔ 不加入 `api_key_auth` 豁免（unit 斷言 `is_exempt("/api/v1/ocr-mapping/contract") is False`）。
  - 需求：1.2, 1.3, 1.5, 1.6
  - **收案註記（2026-09-03）**：`routers/ocr_mapping.py`（path 參數刻意用 str 讓不支援型別走 400 而非 FastAPI 422；四種錯誤碼；`OCR_MAPPING_MAX_BODY_MB`／`OCR_NAME_POLICY` env）＋ `app.py` import／include_router 各一行；8 測試（TestClient 最小 app，含 is_exempt 正對照與 app.py 掛載檢查）。
- [x] 8.2 計量與無個資日誌（TDD＋integration，8.1 完成後）：端點內 `usage_metering.begin({mode, role_id, target_user, vendor_id, session_id})` → `set_path("ocr_mapping")` → `finalize(status, http_status, db_pool)`；400／413／422 亦 `finalize(status="rejected")`；`session_id` 前綴命中 `INTERNAL_RULES` 者 `is_internal=true`、未帶者外部；日誌只印欄位名／`source`／`confidence`（unit 以 capsys 斷言 `ocr_raw.text` 與 `value` 不出現）；integration（`RUN_INTEGRATION=1`）：呼叫一次後 `usage_events` 出現 `processing_path='ocr_mapping'` 且 `decision_snapshot` 無欄位值。⛔ middleware 不動（雙落點反例測試：同一請求只落一列）。
  - 需求：9.3, 9.3a, 9.5
  - **收案註記（2026-09-03）**：端點內 `begin→set_path("ocr_mapping")→finalize`（拒絕路徑 `rejected`＋對應 http_status），⛔ middleware 未動（有反例測試）；摘要日誌只印欄位名／source／confidence；8 unit（spy＋真 `begin` 驗 is_internal＋capsys 六組個資字串不出現）＋1 integration（真 DB 落列）。

## 9. 第二段抽取（⛔ **作廢**——D1 於 2026-09-04 定案 A，改由第 12 節供給）

- [x] 9.1 ⛔ **作廢（不做）**。原任務：`second_pass_extractor`（TDD，7.1 完成後）：`ENABLE_OCR_SECOND_PASS`（預設 false）守門；只對 `cycle_date／cycle／deposit_type／early_termination_days` 缺漏欄位、只送含「押金／繳／解約」關鍵詞的頁；`get_llm_provider(service_name="ocr_second_pass")`、`OCR_SECOND_PASS_MODEL` 跟隨 `OPENAI_MODEL`（⛔ fallback 不得更弱）、temperature ≤ 0.3、`json_object`；LLM 只回 `evidence_span`，正規化空白／全半形後須能在 `ocr_raw.text` 定位，否則 absent；數值一律交第 2 節換算；`confidence=min(LLM 自評, 頁 `ocr_raw.confidence`)`；逾時 `OCR_SECOND_PASS_TIMEOUT`（8 s）或例外 → 略過並記 `provenance.notes`、⛔ 不 500；`add_llm_usage` 計入。unit（mock provider）：定位失敗→absent、數值欄位只收片段、逾時降級。
  - 需求：8.1, 8.2, 8.3, 8.4, 8.5, 8.6

## 10. 收案（10.1 暫掛；10.2／10.3 平行）

- [ ] 10.1 真實回應 e2e（`RUN_E2E=1`；**暫掛至 Q2 fixture 到位**）：真實謄本與合約回應各一份經正式端點（`backtest_session_` 前綴），逐欄與人工判讀對照，`needs_confirmation` 命中率與漏報數落 `.kiro/specs/documind-ocr-mapping/e2e-<date>.md`；⛔ 不得以 1.2 的手構合約樣本充當。
  - 需求：10.4
- [x] 10.2 (P) 覆蓋與效能收案：`make test-unit` 全綠且每條 R1–R9 需求至少一組正反例帶 `req` 標記（`make trace` 追溯矩陣無孤兒需求）；5.1 突變控制實跑一次確認會紅；20 頁 fixture 連打 20 次量 P95（純規則 < 2 s；開旗標 < 10 s）落檔；驗收矩陣第 1、2、5 項打勾。
  - 需求：9.4, 10.1, 10.3, 10.5
  - **收案註記（2026-09-03，⚠️ 部分收案）**：⛔ 「無孤兒需求」**尚未成立**——獨立驗證抓到掃描器對全部 19 個 spec 都讀到 0 條需求，48 個 `documind-ocr-mapping:` ID 全落在 `gaps.dangling_refs`（「需求不存在」），我用 grep 全文找到 ID 就當涵蓋是**看錯節**（BACKLOG N1）。ID 集合本身正確（56−48＝R8 六條＋10.1＋10.4）。`make trace` 在 host 壞（路徑）另記。5.1 突變控制兩向實跑轉紅；P95 進程內 20 頁 ×20 次＝**6.4 ms**（`perf-20260903.md`）＋ `test_nfr_req.py` 守 500 ms；驗收矩陣 1、2、5 打勾。
- [x] 10.3 (P) 裁決落帳與交接：D1／D2／D3 三個裁決以 `python3 "$HOME/.claude/canon/dispute.py"` 落 `.claude/DECISIONS.md`（DSP 編號）；回覆 line-bot：更新 `~/jgb/line-bot-platform/docs/chatai-integration-scenario.md` 的 Q8–Q11 答案（Q8 用本端點、Q9 逐欄信心度由 DocuMind `field_confidences` 透傳、Q10 PDF 由 line-bot 送 DocuMind、Q11 押金不推算已落規則）；驗收矩陣第 6 項打勾。
  - 需求：驗收矩陣 6（對應 D1、D2、D3）
  - **收案註記（2026-09-03）**：D1／D2／D3 以 `dispute.py` 登記為 **DSP-004／005／006**（來源＝代理，待業主）；line-bot `chatai-integration-scenario.md` → v5.1，新增 §7.7 回覆 Q8–Q11＋回應格式範例＋三件待決；驗收矩陣 6 打勾。

## 11. 獨立驗證回修（2026-09-03，兩個 verifier 各一角度，共 REFUTED 7 條＋清單外 8 條）

- [x] 11.1 對抗性輸入抓到的 5 條 P2 ＋ 流程追蹤自抓的 2 條，全數 **FIX**（`tests/unit/ocr_mapping/test_adversarial_req.py` 13 函式／24 案例釘住，機械計數）：
  ②-1 租期視窗遇標點即停、「押金三個月」不再混入、「一年半」→18｜②-2 條款只在「拿掉已吸收片段後仍無條款訊號」才刪（滯納金不再遺失）｜②-3 巢狀葉值字串化、未預期例外 500 `MAPPING_ERROR` 且仍 `finalize(error)`｜②-4 押金月數不限順序｜②-5 `OCR_MAPPING_MAX_BODY_MB` 壞值／≤0 回預設｜⑧(a) 明文「至…止」到期日優先、與月數推算不一致才反白｜⑧(b)「N 日／天前」→ `early_termination_days`（derived、反白）
  ＋ 實打 :8100 追加抓到 1 條：視窗把「115年1月20日」切成「115年1月2」，裸「1月」被當 +1 個月 ⇒ 誤標衝突；修為「無『個』的裸 N月緊接『年』一律視為日期」（`_LEASE_MONTHS_GE`／`_LEASE_MONTHS_BARE`），釘 3 測試。收案（13:2x，最終）：ocr_mapping 188/188、全套 2200。
  - 需求：1.1, 1.5, 4.1, 4.2, 5.4, 6.3, 7.1, 9.3
- [x] 11.2 宣稱驗證抓到的 2 條 P2 **FIX**：⑤ 追溯「無孤兒」是真空成立（掃描器對全 spec 讀 0 需求，BACKLOG N1）⇒ 10.2 降為部分收案；⑥ 4.1／5.2 測試數寫錯（11→10、9→10）與「13/15」實為 15/17 ⇒ 改為機械計數。
- [x] 11.3 清單外：N3 R9.1／9.2 形狀對齊實作（requirements v3）**FIX**；N2 押金不變式擋不住洗白 **DEFER**（BACKLOG P3，真正守門是 `decide_deposit` 無除法）；N4 併入 ⑧(a) **FIX**；N1／N8 **DEFER**（工具層，BACKLOG）；N5–N7 **DEFER**（P4）。
  - 收案（12:4x 快照，早於 11.1 的實打追加，故數字較小）：ocr_mapping 185/185；全套 unit 2197 過（＋21），既有紅不變。:8100 已於 13:26 rebuild 並由第三輪 verifier 實打 CONFIRMED。
- [x] 11.4 第三輪（文件對齊後）：verifier 實跑六類宣稱全 CONFIRMED（188/188、2200、perf p95 5.17 ms、計量列、日誌無個資）；plan-verifier 文件↔程式 REVISE 3 P2＋3 P3 **全 FIX（文件面）**：R5.4「半年」→「N年半」（獨立半年不解析列 BACKLOG P4）、design 元件 9 簽名對齊實作、元件 3 補字串化、安全節補「回應體 `raw` 帶個資」（§7.7 同步）、tasks 標頭 v3、21→13 函式／24 案例（機械計數）、11.1／11.3 加時間點。⛔ 未動程式，實跑結論仍有效。收尾 fresh review 再抓 1 條 P2（design 三處對「誰呼叫元件 8」不一致）⇒ 定案 router 接入、mapper 不碰 LLM（design 1.2），**此條僅主 session grep 自檢、未再獨立複審**（兩輪 REVISE 上限）。

## 覆蓋對照（R → 任務）

## 12. D1 定案 A：消費 DocuMind `rental_terms`（2026-09-04）

- [x] 12.1 `rental_terms` 映射與來源優先序（TDD）：`CONTRACT_RENTAL_MAP`（date_start／date_end／monthly_rent／payment_day／tenant_name）、`_prefer()`（租約優先、通用進 conflicts、解析不了退回）、`date_end` 三來源擇一、`_rental_rent_field`／`_payment_day_field`／`_ROC_SPACED`；⛔ `rental_terms.deposit` 不消費。`test_rental_terms_req.py` 17 函式／24 案例；ocr_mapping 212/212。
  - 需求：4.1, 4.6, 5.1
- [x] 12.2 spec 收尾：requirements v4（R4.6、R8 作廢、D1 定案）、design 1.3（元件 6／8、決策 3、環境變數）、research 主題 3 更正、DSP-004 結案、line-bot §7.7 ①、perf R8 節作廢。
- [ ] 12.3 DocuMind 側待辦（外部 repo `~/jgb/DocuMind`，業主）：`deposit` 拆 `deposit_amount`／`deposit_months`；新增 `payment_cycle`、`early_termination_days`；樣式放寬到不帶冒號的敘述句；`types.py` 宣告 `RentalTerms`＋測試；多捕獲組改回正規化日期而非空白 join。完成後 chatai 只改 `CONTRACT_RENTAL_MAP`。
- [ ] 12.4 rebuild `:8100` → 以真實合約打 DocuMind `:8085` 取 `rental_terms` 樣本（兼作 10.1 的 Q2 fixture）→ 實打 chatai → fresh verifier。

| 需求 | 任務 |
| --- | --- |
| 1.1–1.6 | 1.1、7.1、8.1 |
| 2.1–2.6 | 3.1 |
| 3.1–3.5 | 2.2、4.1 |
| 4.1–4.6 | 2.2、5.2、5.3、12.1 |
| 5.1–5.6 | 2.1、2.2、5.3、12.1 |
| 6.1–6.6 | 5.1 |
| 7.1–7.6 | 6.1、7.1 |
| 8.1–8.6 | ⛔ 作廢（D1 定案 A） |
| 9.1–9.5 | 1.1、7.1、8.2、9.1、10.2 |
| 10.1–10.5 | 1.2、5.1、10.1、10.2 |
