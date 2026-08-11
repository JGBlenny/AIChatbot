# 實作任務：retrieval-decision-layer（對話與檢索決策層韌性）

> 建立時間：2026-08-10
> 需求：requirements.md（R1–R10，含 R7.1 證據修訂）｜設計：design.md（C1–C8，含審查修訂 1–3）｜落差：gap-analysis.md｜研究：research.md（六實驗＋反證覆核）
> 標記：`(P)` = 可與同層其他 `(P)` 平行
> 鐵律：**病灶不可降級清單七項不得縮水**（縮水須業主顯式裁決）；每機制實作前藥效紀錄已備或於任務內補 pilot（R2）；TDD 先紅後綠；每元件獨立 env 開關；**margin 訊號禁止復活**（EXP-1/1b 證偽）；裸 RRF 禁用；封存分支撿件無藥效紀錄不合入（R-c）；每階段末凍結語料全量＋fresh 代理 CONFIRMED 才進下一階段（R9.1）；凍結語料只讀不改。

## 1. P0｜評測基礎與決策快照（量尺先行）

- [ ] 1.1 (P) 評測 harness 入 repo（TDD）：`scripts/backtest/decision_replay.py`（源自 corpus-20260810/replay_harness.py）＋`classify_routing()` 版本化（unit：五類別判定矩陣＋version 戳）＋`corpus-20260810/noise_manifest.json`（37 案雜訊標記，機器可讀，獨立 review 防 R-f）＋前置容器閘門（audit 不變量 3 未過→abort）＋`cache_mode=on/off` 雙軌參數。
  - 需求：1.1, 1.2, 1.3, 1.4, 1.7
- [ ] 1.2 (P) 決策快照埋點（TDD）：usage_events 加 `decision_snapshot JSONB`、`facet_event VARCHAR(30)`（ADD COLUMN IF NOT EXISTS，沿 20260720 慣例）＋usage_metering `set_decision()` hook（比照 set_facet 房式：ctx None/finalized 靜默）；unit 矩陣＋欄位未建降級。
  - 需求：8.3
- [ ] 1.3 DecisionConfig 集中讀值＋行為等價搬移（1.1、1.2 完成後）：`services/decision_layer.py` 建 `DecisionConfig.load()`（唯一讀值點）與 `decide()`（六 case＋面向進場邏輯原樣搬入）；chat.py 4 處＋engine.py:428＋FORM_TRIGGER_THRESHOLD 兩處改經 DecisionConfig；**等價驗證照審查修訂 1 雙層**：①決定性子決策（門檻比對/分類路由/識別碼規則）unit 嚴格等價；②凍結語料搬移前後各 ≥3 輪，逐輪多數決類別不一致率 ≤ 基線重跑變異（run2 vs run3 基準）。散讀值點=0 入 `make audit` 新不變量。
  - 需求：7.4, 8.3
- [ ] 1.4 R8.1 歸因實驗（1.1、1.2 完成後；產物=報告非程式）：三組受控分離 E-5 變異來源——①固定檢索重跑 LLM 環節②rewriter/意圖分類同輸入 ×N 輸出變異③快照灰帶密度分佈；產出歸因報告＋**E-5 目標上限提案報業主核定**（核定後寫入 design.md 不得放寬）。
  - 需求：8.1, 8.2

## 2. P1｜決策層調參與逃生門（主病灶）

- [ ] 2.1 (P) 識別碼訊號（TDD）：`IdentifierSignal` 決定性規則（合約/帳單/物件號正則同表同權重＋query_type 疑問詞表判定「查實值 vs 問機制」）；`decide()` 接線——knowledge 型帶編號→偏向直答（#18T2 判準）、data_query 型→識別碼感知進場（帳單號合約號對稱）；unit 矩陣含凍結語料實句。
  - 需求：4.4, 4.5
- [ ] 2.2 逃生門（2.1 完成後，TDD）：`EscapeState`（id_ask_count/zero_row_count/escape_events/exited_facets）＋`check_escape()`——拒絕/主題不符詞表（沿 _CANCEL_WORDS 擴充）＋詞表未中輕量 LLM 兜底；`id_ask_count≥2`→通則知識（top-1 分類反查）；`zero_row_count≥2`→通則＋權限圈提示、禁逐字重播；exit_requery 當輪原句回 C1；**再進場抑制照審查修訂 2**（帶識別碼或主題詞變更才解除，事件落快照）。unit：三事件矩陣＋RV-3 情境（三輪明說沒編號→上限內退出）＋旋轉門反例（退出後不帶新資訊不得再進同面向）。
  - 需求：4.1, 4.2, 4.3, 4.6
- [ ] 2.3 (P) 快取修正（1.3 完成後，TDD）：enter_facet/form 回應不 cache；DecisionConfig 雜湊納入 `_generate_config_version()`；**record_turn 落 dispatcher 統一出口含快取命中路徑**（審查修訂 3；順手修掉 save_conversation 幽靈呼叫）。integration：快取開組態下面向進場輪二次請求仍建會話（R1.7 斷言）。
  - 需求：1.7, 7.6
- [ ] 2.4 校準與 P1 收案（2.1–2.3 完成後）：灰帶定界（校準集＝D-3 灰帶＋凍結語料邊界輪，**與驗收集分離且切分凍結**）；分數平移穩定性驗證（模擬整體分數 +0.05 平移，路由類別變動輪次低於預宣告上限）；凍結語料全量（快取 off/on 雙軌）＋既有回歸三件（無 ID 泛問直答/IoT/b2b 隔離）＋fresh 代理 CONFIRMED。
  - 需求：7.1, 7.2, 7.3, 7.5, 1.5, 1.6, 9.1

## 3. P2｜承接機制（補全器與變體表）

- [ ] 3.1 (P) 對話歷史層（TDD）：cache_service `append_turn/get_recent_turns`（Redis 滾動清單，TTL 2h，n=6）＋topic_terms 抽取（決定性：jieba 名詞＋既有實體詞表）；unit：滾動覆蓋/TTL/跨 session 隔離。
  - 需求：3.1
- [ ] 3.2 省略補全（3.1 完成後，TDD）：省略判定決定性規則（長度＋代詞表＋無實體名詞）→補全句與原句雙路聯集（重用 precomputed_rewrites 通道）→final 比較裁決；防黏連（完整主語＋主題詞零重疊→passthrough）。驗收：EXP-5 A 案（rank 10→top-3）＋凍結語料 A 組省略輪＋換主題輪回歸；新 session 對照（R3.4）。
  - 需求：3.1, 3.2, 3.3, 3.4
- [ ] 3.3 複合拆解（3.2 完成後，TDD）：多意圖偵測（長度＋多疑問結構）→核心子句抽取→分別檢索→final 最高者主答；驗收：M1 原句（#33）拆解後 3926 進 top-3（EXP-3 P1 的反面驗證）。
  - 需求：3.1（複合型分支）
- [ ] 3.4 變體表底座（(P) 可與 3.1 平行；TDD）：`knowledge_variants` migration（欄位照 design C4）＋K_MAX=5 DB trigger 硬擋＋歸戶檢索 SQL（GREATEST 版；EXPLAIN 驗效能，不足換 UNION+GROUP BY）＋`hit_via_variant` 透傳＋命中統計更新；**補償公式 pilot**：三案（不補償/線性懲罰/顯著超越才採）在凍結語料＋EXP-3 案例對比，判準先寫入 research.md 再跑；**rerank 輸入 A/B**（變體文本 vs summary）同場 pilot。
  - 需求：6.1, 6.2, 6.3, 6.4, 2.1
- [ ] 3.5 錨點分型遷移（3.4 完成後）：98 筆錨點**逐筆映射清單先產出**（歸戶知識＋預期路由行為；照審查修訂 3——換講法型遷、面向進場型保留、映射不出保留）；遷移 migration（冪等）＋**路由行為回歸**（原觸發句全量，判準=仍進原面向/仍直答，防 T-1 退化）。
  - 需求：6.5
- [ ] 3.6 變體治理（3.4 完成後）：入庫搶答檢查（新變體 top-3 含他知識→標衝突待裁決）入 `make audit` 不變量；來源標記強制（source_type/source_ref 非空約束）；MISS 分型三問判別法寫入 `assistant-report-workflow.md`（落變體/歸 E-2/歸拆解，取代摘要補詞為默認路徑）；P2 收案：凍結語料＋30 題變形集雙雙不退步＋fresh CONFIRMED。
  - 需求：6.6, 6.7, 6.8, 9.1

## 4. P3｜輔助通道與維運雷達

- [ ] 4.1 詞面通道（閘門式；撿件逐件過藥效門）：封存分支 `lexical_channel/lexical_segmenter/userdict/backfill` 逐件裁決（直接用/改後用/重寫，各附藥效紀錄）；先驗舊回填 vs 現分詞一致性（不一致重跑 backfill）；**閘門融合**（vector top1 final < GRAY_UPPER 才參與 RRF，否則只落快照）；tsv 維護 trigger＋audit 不變量（R-d）。驗收：30 題集持平以上＋強命中零劣化（M2 案斷言 rank 不退）＋0 胡編下限。
  - 需求：5.1, 5.2, 5.3, 5.4
- [ ] 4.2 (P) 偏差雷達：`tools/drift_radar.py` 離線批次（四訊號：殭屍/無主聚類/灰帶擁擠/零貢獻變體）＋逐筆證據連結＋兩次結果 diff；不自動刪除。以現有 usage_events＋variants 統計實跑一輪產首份報告。
  - 需求：10.1, 10.2, 10.3, 10.4

## 5. 收案（雙軌＋保留驗收題）

- [ ] 5.1 保留驗收題補齊（P3 完成後）：#21T3／#23／#33 正解覆蓋／R-39（若客服已補說明）以「MISS 分型三問」走新路徑補上（預期：#21T3/#23 落變體或既有知識命中、#33 走拆解）；端到端驗證含面向/直答路由正確。
  - 需求：9.5
- [ ] 5.2 雙軌收案與報告（5.1 完成後）：①凍結語料全量 ≥3 輪（快取雙軌）＋E-5 不一致率對業主核定上限；②fresh 代理自創未見過情境多輪扮演（同 session、口語、直指矛盾）；收案報告**逐 R1–R10 給證據連結**，任何縮水顯式標示報業主裁決；`make audit` 全綠；runbook 增補部署節（含 semantic-model 重建註記、變體補嵌、prod 由使用者執行）。
  - 需求：9.1, 9.2, 9.3, 9.4, 8.4, 1.6
