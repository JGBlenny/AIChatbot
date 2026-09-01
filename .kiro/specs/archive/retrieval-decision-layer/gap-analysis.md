# 差距分析：retrieval-decision-layer

> 2026-08-10｜方法：現碼與 DB 實查（決策層門檻散佈／快取／詞面資產）＋封存分支資產盤點＋前身 spec 差距分析覆核更新。
> 本文件提供事實與選項，不做最終選型（設計階段決）。前身 `conversation-retrieval-resilience` 的差距分析（封存分支 `21db05e`）大半仍有效，本文件標注「沿用」與「已變」。

## 0. 查證事實（相對前身差距分析的變化）

1. **詞面通道的 schema 與回填已在 DB 裡**：撤案 migration 殘留 `knowledge_base.question_tsv`（tsvector）＋`idx_kb_question_tsv`（GIN），且 **921/921 active 列已回填、`tsv_segmented` 全 true**。main 的程式碼零引用（`grep question_tsv` 無 hit）。→ R5 不是從零建，是「接回被拔掉的線」；但回填內容基於撤案時的分詞器，重啟時需驗新舊分詞一致性。
2. **封存分支是大型零件庫**（`archive/conversation-retrieval-resilience-failed`，tip `6dccc5b`）：`lexical_channel.py`（308 行）＋`lexical_segmenter.py`＋`config/lexical_userdict.txt`＋維運文件；`query_bundle.py`（原句+改寫雙路）；escape 偵測三支 unit 測試（matrix/false_positive/detection）；holdout 基礎設施（`run_holdout.py`＋`check_contamination.py`＋baseline）；`backfill_question_tsv.py`。**撤案定性是執行紀律失敗，非零件失效**——變體機制對純檢索病 6/6 有效有預註冊數據。cherry-pick 候選，但每件需按 R2 重跑藥效實驗後才准入。
3. **DB 擴充現況不變**：`pg_trgm`＋`vector`＋`plpgsql`；zhparser/PGroonga 仍不在（要換 postgres image）。Python 端有 jieba。（沿用前身 G5 結論：jieba 應用層分詞＋`to_tsvector('simple')` 路線的前提仍成立。）
4. **門檻散佈實況（R7.4 的立案證據）**：`os.getenv("KB_SIMILARITY_THRESHOLD")` 在 `chat.py` 至少 4 處＋`conversational_engine.py:428` 各自讀取；六 case 仲裁硬編碼 0.55/0.6/0.15（`chat.py:2275,2297` 一帶）；面向進場 `FORM_TRIGGER_THRESHOLD` 0.75 另一處；`_diagnosis_config_for_knowledge` 拿 final `similarity` 對門檻單點比對。**同一個決策層至少 6 個分散讀值點。**
5. **E-5 量測時快取是關的**（本機 `.env` `CACHE_ENABLED=false`）→ 13% 路由變異**不是快取造成**，是決策層本身。
6. **快取在 prod 預設開（`docker-compose.prod.yml` default true），且鍵不含 role_id/session**（`vendor_id+question+target_user+config_version`，`cache_service.py:73,93`）。已對碼證實：**面向實值回答走 `_finalize_response` 不進共用快取**（無個資外洩之虞）；但**面向進場輪（ASK_ID 反問）可能經 `_build_knowledge_response` 進快取**——若命中，第二個使用者拿到反問文案卻沒有面向會話被建立，回覆編號後走的是無會話路徑。**這是 prod-only 的 E-5 變型，凍結語料（快取關）測不到**，需在 R1 評測基礎設施中補「快取開」組態的驗證軌。
7. **前身差距分析仍有效的查證**（抽驗未變）：direct 路徑對話歷史「從未存成功」（`save_conversation` 不存在，每輪靜默 AttributeError）；`0.1×vector+0.9×rerank` 已是 final 公式；引擎有 `asked_count/MAX_ASKS`、`_CANCEL_WORDS`、滾動 dialog 6 輪、0-row 清槽路徑；`digression_detector*` 存在但未接線。
8. **20260810 凍結語料已入 repo**（`docs/backtest/corpus-20260810/`，run2/run3 有效基準＋harness）；路由類別判定目前只存在於本次回測的 ad-hoc 腳本（ANSWER/ASK_ID/FACET_EMPTY/FORM/FALLBACK 字串規則），未版本化。

## 1. 重用資產

- **前身差距分析 §1 全表沿用**（檢索管線候選/過濾/改寫聯集/reranker HTTP、keyword_fallback＋keywords 陣列、面向引擎掛點、埋點與 env 開關慣例）。
- **新增（本輪）**：`question_tsv` schema＋回填＋GIN（DB 側現成）；封存分支零件庫（§0.2 清單）；凍結語料＋重播 harness；`make audit` 不變量框架（R1.2 容器閘門直接掛現成不變量 3）；SOP `GREATEST(primary,fallback)` 雙向量先例（R6 max-pooling 的 SQL 形態）；20260803 D-3 灰帶案例＋30 題變形集（R7.3 校準集素材）。

## 2. 真缺口（按 Requirement）

- **G1（R1）評測基礎設施三件缺**：①路由類別判定未版本化（ad-hoc 腳本→需入 repo 帶測試）；②雜訊分層標記只存在登錄簿文字，未機器可讀；③「快取開」組態驗證軌不存在（§0.6 的 prod-only 風險完全無覆蓋）。holdout 底座可從封存分支撿。
- **G2（R3）E-2 歷史層**：沿用前身 G1/G2——歷史層全新建＋補全觸發判定與改寫模式缺席。
- **G3（R4）逃生門**：沿用前身 G3/G4——失敗語義與計數（zero_row_count、拒給識別碼偵測、分級話術、查無≠5xx）缺席；岔題回流無確定性機制。識別碼感知：現有 keywords 陣列不含識別碼型態判定，帳單號/合約號進場不對稱的機轉未歸因（§4 待決 5）。
- **G4（R5）詞面通道**：schema 在、程式線全斷（main 零引用）；分詞一致性驗證缺（§0.1）；RRF 融合層不存在。
- **G5（R6）變體表——全新**：無變體儲存結構；檢索 SQL 是單向量 `kb.embedding <=>` 單路；無歸戶/去重；無極值偏誤補償先例（SOP 雙向量固定 k=2 不需要，開放 k 就需要）；rerank 輸入文本規則未定；錨點收編遷移（現有空答案錨點散在 kb 正表）；來源標記欄位不存在（可仿 `source`/`generation_metadata` 慣例）。
- **G6（R7）門檻解耦——全新且比前身 G6 範圍大**：前身只聚焦面向進場 0.75 單點；本 spec 要求整層集中（§0.4 的 6 個散讀點收斂）＋校準信心/margin 訊號（現碼完全沒有 top1−top2 概念）＋「分數平移下路由穩定」的驗收工具。
- **G7（R8）E-5 歸因與決定性——全新**：路由關鍵訊號記錄缺（usage_events 有 knowledge_score/sop_score/decision_case，但無 margin、無面向進出事件、無 per-turn 判定快照）；變異來源分離實驗（LLM 環節 vs 門檻擺盪 vs 脈絡累積）無工具。
- **G8（R2/R9）流程資產**：藥效實驗的記錄格式與存放位置未定（前身 research.md 有先例）；fresh 代理雙軌收案在撤案後首次要走全程。

## 3. 實作路線選項

**G2 歷史層**：沿用前身選項（A. Redis 滾動清單／B. PG session_turns 表）。**本輪新增考量**：R8.3 要求路由訊號可歸因，若選 A，訊號記錄仍需落 usage_events（Redis 不可審計）；兩案在「歷史」與「訊號」分開存放下皆可行，傾向不變（A）。

**G4 詞面通道**：沿用前身傾向（jieba＋`to_tsvector('simple')`＋GIN，pg_trgm 兜底；zhparser 換 image 列 P2）。**本輪新增**：先跑「舊回填 vs 新分詞」一致性比對，不一致就重跑 backfill（腳本在封存分支）。

**G5 變體表（新，三個子決策）**
- 儲存：A. 獨立表 `knowledge_variants(knowledge_id, variant_text, embedding, source, hit stats)`＋檢索 SQL JOIN 歸戶——乾淨、統計好掛；B. kb 表加 `variant_embeddings vector[]`——省 JOIN 但統計與回收難。傾向 A。
- 極值偏誤補償：A. margin 門檻天然免疫（若 R7 選 margin，R6 補償可簡化為排序層固定懲罰 `f(k)`）；B. 對 max 分數做 k 校正（需藥效實驗定函數）；C. 限制每知識變體上限（Azure 實證 5-10 條飽和）。可組合，實驗定。
- rerank 輸入：A. 命中變體文本（語意最貼近 query）；B. 知識本體 question_summary（穩定但丟失變體優勢）。藥效實驗二選一（R6.4）。
- 歸戶衝突：新增變體時跑 top-K 搶答回歸（現成先例：20260803「新知識與既有錨點語義相近時必測搶答回歸」流程化）。

**G6 門檻解耦（新，範圍取捨）**
- A. **集中決策模組＋margin 訊號、六 case 結構不動**：新建單一 `decision_layer` 讀值點（設定表或 config 模組），六 case 仲裁與面向進場都改從它取門檻；margin 作為新增訊號先只進面向進場判定（脆弱點集中處），答題六 case 維持——改動面小，171 條整合測試護欄有效。
- B. 六 case 全面重構為校準信心單一決策器——乾淨但動熱路徑最大，風險/收益比差（前身已判過一次）。
- 傾向 A；margin 進答題決策列 P2 觀察項。
- 校準集：30 題變形集＋D-3 灰帶＋凍結語料邊界輪次，校準/驗收分離（R7.3）——需在設計期先切分並凍結切分。

**G7 E-5 歸因（新）**
- 訊號記錄：usage_events 加欄（margin、facet_entry_signal、decision_snapshot jsonb）——沿 ADD COLUMN IF NOT EXISTS 慣例。
- 分離實驗：三組受控——①同輪重放固定檢索結果只重跑 LLM（量 LLM 貢獻）②固定 LLM 輸出重跑檢索（量檢索抖動）③逐輪快照 margin 分佈（量門檻邊界密度）。工具可基於凍結語料 harness 延伸。

**G1 快取開組態軌（新）**：凍結語料抽子集在 `CACHE_ENABLED=true` 下重播，斷言：①面向進場輪不得因快取命中而跳過會話建立（§0.6 病灶），或②修法把進場輪排除出快取。修法本身屬設計決策（排除 vs 鍵加維度），先立驗證軌。

## 4. 設計階段待決清單

1. 沿用前身待決 1/2/3/4/6/7（歷史層選型與輪數、省略句觸發規則、RRF 參數與詞庫維運、中信心帶行為、逃生門偵測方式、p50 延遲基線）。
2. 變體表三子決策（儲存形態／偏誤補償／rerank 輸入）＋變體上限值。
3. margin 門檻的校準方法（分位數？ROC？）與 E-5 目標上限值（現況 13%，寫入設計後不得放寬）。
4. 快取進場輪修法（排除 vs 鍵加維度）；連帶檢視 config_version 是否涵蓋決策層新設定。
5. 帳單號/合約號進場不對稱的機轉歸因（錨點分佈差？觸發詞表差？）——資料查證，設計前做完。
6. 撿件清單逐件裁決：lexical_channel/segmenter/query_bundle/escape 測試/holdout 工具——每件標「直接用/改後用/重寫」，且一律過 R2 藥效門。
7. 路由類別判定規則的歸屬（評測工具 vs 產品碼共用 enum）。

## 5. 風險登記

- **R-a（沿用）檢索熱路徑改動**：六 case 隱性行為易被融合分數擾動；每機制獨立 env 開關可逐項回退。
- **R-b（沿用）補全誤觸**：省略句判定過寬→黏連；過窄→E-2 沒修到。凍結語料 A 組＋換主題反向案雙向卡。
- **R-c（新）撿件即繞過藥效門的誘惑**：封存分支零件「看起來能用」會誘使跳過 R2 實驗直接接線——撤案的直接死因就是驗收紀律失守。裁決規則：**無藥效實驗紀錄的零件不得合入**。
- **R-d（沿用+變化）詞面回填維護**：question_tsv 已回填但 main 無維護線——新增知識不更新 tsv 會靜默劣化；接回時 trigger/應用層擇一並入 audit 不變量。
- **R-e（新）快取語義與決策層互動**：config_version 未涵蓋新決策設定時，調參後舊快取殘留舊路由行為——設計期把決策層設定納入 config_version 計算。
- **R-f（新）凍結語料的雜訊分層若實作錯誤**，指標會系統性偏移（例：把客服轉述句計入口語命中率）——分層標記需獨立 review。
- **R-g（沿用）J-2 遮蔽**：preview 合約端點 500 未解前，合約鏈驗收只能驗行為不能驗資料正確性。
