# 對話與檢索韌性——業界實作覆核調研

日期：2026-08-03｜方法：三路並行網路調研（多輪與流程路由／檢索決策與中文混合檢索／知識變體管理），來源以 2024-2026 官方文件與實證為主，關鍵連結附於各節。
用途：覆核回報批次修正後擬定的 P0→P1→P2 改造順序（見 `docs/backtest/assistant-report-regression.md` 設計結論節），供「對話與檢索韌性」spec 引用。

---

## 一、多輪追問處理（對應 E-2）

- **Condense question（歷史補全）仍是現行標配**：LangChain 官方替代 API 即 `create_history_aware_retriever`；LlamaIndex `condense_plus_context` 仍是 stable API。客服場景被官方歸在 2-Step/Hybrid RAG（延遲可預測），不需要 agentic 檢索。（LangChain retrieval docs、LlamaIndex chat engine docs）
- 實務統計：**60%+ 的多輪追問含未消解指代**，不補全直接檢索必失敗（alhena.ai）——正是我們 A 組 5/5 第二輪全滅的機理。
- **實作鐵則（SemEval 2026 實證）**：只改寫最後一輪、僅消解指代/省略、保留領域術語、禁止加料；**原句＋改寫句串接使用**（只用改寫句不穩，改壞時原句是保險）；「關鍵字化/HyDE 擴寫式改寫」實證普遍有害。（arXiv 2606.28352、2602.09552）
- 延遲：補全是額外一次 LLM 呼叫（+150ms 起），用小模型；首輪或已長且具體的 query 跳過。

### 一之補：現況程式碼查證與防黏連設計（2026-08-03 定案）

- **現況查證**：對話歷史「有存、檢索沒讀」——`cache_service.save_conversation` 以 session_id 存每輪 Q/A（chat.py:3594，只寫不讀）；`QueryRewriter.rewrite(query: str)` 只收當前句（query_rewriter.py:72），embedding 也只算當前句。行為對照實驗（同句在有前文 session vs 全新 session 回覆逐字相同）與程式碼一致。面向引擎另有自己的 session 狀態（面向內多輪正常），缺口僅在 direct_answer 路徑。
- **補全範圍**：同 session_id 最近 1-2 輪，不跨 session、不做長期記憶。
- **防「話題切換黏連」五道防線**（設計約束，進 spec acceptance）：
  1. 原句永遠參戰——補全句是加一路候選、不取代原句（最壞＝退回現行為）；
  2. 有條件觸發——完整獨立句（有主語/夠長/帶編號）跳過，只補短省略句；
  3. 窗口鎖最近 1-2 輪；
  4. 改寫 prompt 含「與前文無關則原樣輸出」條款；
  5. reranker 以原句對知識配對打分，歪候選壓不過正解。
- **驗收雙向**：①追問接得住（A 組 5 案）＋②話題切換不受污染（前輪帳單、本輪突問報修，斷言無殘影）——兩組全綠才過。

## 二、流程路由的進出設計（對應 E-1/E-3）

- 我們面向機制的業界同類是 Rasa forms/CALM flows、Dialogflow CX pages——**「卡在流程出不來」是有整套現成模式的已解問題**：
  - **Rasa CALM conversation repair patterns**：`pattern_cancel_flow`（取消）、`pattern_skip_question`（拒答槽位）、`pattern_clarification`（進場模糊→列選項，**自訂計數器超閾值轉 human handoff**）、`pattern_continue_interrupted`（岔題回流）、`pattern_search`（**流程中知識問題→查 KB 回答**＝我們 E-1 查無降級的現成形）。（rasa.com patterns/conversation-repair docs）
  - **Dialogflow CX**：參數層級 `sys.no-match-1~6` 分級 handler（每級話術不同、第 N 級轉真人）；**Google 官方準則：no-match 上限 3 次即升級**。generative fallback＋data store 掛在 start page＝任何頁面查無先試 KB 回答再回流程。（cloud.google.com dialogflow docs）
- 對我們的三個直接可抄設計：①追問失敗用**分級 handler**（每級話術不同）而非單一計數；②**拒答槽位、取消、查無是三種不同事件**分開處理；③KB 岔題答完**顯式問「要繼續嗎」**（文字客服較穩）。

## 三、檢索決策與門檻（對應 D-3 門檻脆弱、fallback 設計）

- **業界主流不是「向量原始分硬門檻決定答/不答」**，而是級聯：寬召回（top-k 大）→ cross-encoder rerank → 生成層 grounding 把關。Microsoft 官方基準：hybrid＋semantic ranking 全面優於純向量；無 rerank 時最佳結果常掉在第 7-8 位。（Azure AI Search 官方評測）
- **門檻脆弱有公開同構踩坑**：Archon #689——多詞/口語查詢 embedding 分數系統性偏低、整批落檻回 0 筆，短查詢正常。與我們 D-3（差 0.01 行為劇變）、變形掃描 12 題 fallback 同一病。
- 門檻的正確位置與定法：後移到 **rerank 分數**；用 **30-50 個領域邊界查詢校準**（Cohere 官方方法）或 conformal prediction 統計校準（CONFLARE）——「0.55/0.75 手拍值」被明確認定為現存弱點。
- **CRAG 三檔分級**（高信心→直答；中信心→補充檢索/混合；低信心→fallback 轉客服）是消除門檻懸崖的標準形狀；fallback 觸發建議多信號（rerank 分＋grounding/relevance 檢查＋覆蓋度），AWS Bedrock Guardrails 已把 grounding/relevance 產品化為兩個獨立參數。
- 「cosine 高分≠能回答」：主題相近但答不到點的 chunk 可打 0.78——不要把向量原始分當 confidence。

## 四、中文混合檢索（對應口語具體詞斷層）

- 中文直接證據：**EasyRAG（CCF AIOps 中文運維問答）以稀疏檢索＋BGE reranker 奪冠**（免微調）；阿里雲/Zilliz 官方實踐皆為 BM25(jieba)＋向量＋RRF＋重排。（arXiv 2410.10315）
- 詞面通道存在的理由：向量系統性低估短字面 token（產品碼、品項名、口語量詞）——「馬桶」「單子」這型 MISS 的正解通道。
- **pgvector 環境的實作階梯**：
  1. 零外掛：`tsvector`(GIN)＋pgvector(HNSW)＋RRF 純 SQL（Supabase 官方範例；一實測 62%→84%）。中文需換 parser：**zhparser** 或 **PGroonga**（CJK 免配置）。
  2. 真 BM25 排序：ParadeDB `pg_search`（中文社群評為目前生產級首選）。
  3. 免分詞兜底：`pg_trgm`（口語變形/錯字容錯通道）。
- 注意：原生 `ts_rank` 無 IDF，排序弱——但我們已有 reranker，「詞面通道只管召回、排序交給 RRF＋reranker」正好是我們的形狀。**自定義詞庫收品項名/業務專名是中文 BM25 成敗關鍵**。

## 五、知識變體管理（對應「一知識多問法」）

- **方向有強背書**：
  - Azure QnA Maker「alternate questions」與提案完全同構，官方經驗值：**前 5-10 條語義互異即近飽和、之後報酬遞減；只在實測未命中時回填，不預先窮舉**。
  - **HyPE 論文（索引期假想問句，即我們的變體表自動化版）**：六資料集 precision 平均 +20pp、**單一領域語料（最像單產品客服 KB）+40pp**。
  - LangChain `MultiVectorRetriever` 的 hypothetical questions 策略＝「多向量→歸戶 parent→去重後回傳」，**歸戶去重是框架內建標準，不是待發明的難題**。
- **治理有據**：Rasa 實測語句量差 >3 倍小意圖被吃掉（變體不均的實錘）；跨知識變體衝突偵測可用 embedding 相似度掃描（QBox/Botium 已把此工具化）；自動生成問句必配人審抽查（~5%）。
- 商用客服的知識維運迴圈（Intercom Fin/Zendesk/Decagon）共同模式：**未解決對話→自動 clustering→按量排序→人審→補知識，週節奏**——沒有一家預先窮舉問法，全部從真實未命中回填。與我們的回報 SOP 同構，可加 clustering 強化。

## 六、評測方法（對應變形評測集）

- **本次 30 題掃描 43%→80% 屬污染數字**（補詞來源即考題）——業界明確做法：held-out 集以**線上真實提問為主體**（「50 條真實 production query 勝過 500 條合成題」）、contamination rate 目標 0%、用 validation−holdout 分數差偵測過擬合。修正用集與驗收保留集分離，保留集每輪換血。

---

## 七、P0-P2 覆核結論

| 項目 | 覆核 | 依據與修訂 |
|---|---|---|
| P0-① E-2 追問補全 | **支持** | 現行標配（LangChain/LlamaIndex 官方 API）。實作照鐵則：只改最後一輪、原句＋改寫句串接、小模型、首輪/長句跳過 |
| P0-② E-3 逃生門 | **支持，且有現成模式可抄** | 照 Rasa CALM patterns＋Dialogflow 分級 handler：拒答/取消/查無三事件分開、失敗分級（上限 3 次轉人工話術）、查無先試 KB 再回流程（兼修 E-1）、岔題答完顯式問是否繼續 |
| P1-③ 識別碼感知路由 | **方向支持，形狀調整** | 不自製孤立 heuristic——併入「門檻後移＋CRAG 三檔」重構：進面向/直答/fallback 的決策信號改為 rerank 分＋識別碼特徵，門檻用 30-50 個邊界案例校準，消除 0.75 懸崖 |
| P1-④ E-4 改寫器口語正規化 | **有保留，主力換人** | 實證警告：檢索導向改寫（塞詞彙表/關鍵字化）普遍有害。口語具體詞的正解是 **P1 新增：中文混合檢索**（zhparser 或 PGroonga＋RRF 純 SQL 起步，pg_trgm 兜底，自定義詞庫收品項名）；改寫器只保守做指代消解（併入 E-2），不做詞彙正規化 |
| P1-⑤ 評測制度化 | **支持並強化** | held-out 以真實回報提問為主體、每輪換血、contamination 0%、ratchet 進 make audit |
| P2-⑥ 變體表 | **支持度上調，順序維持** | HyPE +20~40pp＋MultiVector 歸戶去重內建＝可行性比預估高；但 P1 混合檢索可能先吃掉大半增益，維持「P1 後用乾淨保留集重測再決定」。若上：每知識上限 5-10 條語義互異、只回填實測未命中、跨知識衝突用 embedding 掃描做 audit 不變量 |

**修訂後路線圖**：
P0＝E-2 追問補全＋E-3/E-1 面向逃生門（照 CALM/CX 模式）
P1＝中文混合檢索（取代原「改寫器正規化」主力）＋檢索決策重構（門檻後移 rerank＋三檔分級＋邊界案例校準，內含識別碼感知）＋評測雙軌制度化
P2＝變體表（P1 後以乾淨保留集重測，殘餘 MISS 集中領域黑話才做；設計照 MultiVector＋Azure 準則）

三路調研原始筆記（含全部來源連結）由本檔彙編；開 spec 時本檔為 research 依據。
