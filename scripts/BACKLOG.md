# BACKLOG — 危害、待裁決、待辦

> 由 `scripts/status.py` 讀取並**置頂印出**。⛔ 別把這些寫成交接檔中段的散文——
> 檔案幾千行，下一個 session 不會讀到那裡。
>
> 格式：`- [ ] (級別) YYYY-MM-DD 一句話 — 說明`
> 結案改成 `- [x]`，⛔ 不要刪除（刪掉就沒人知道它曾經是問題）。
>
> 三級的差別在**球在誰手上**，那決定了「擱置很久」是不是正常：
>   · `P1–P3` 球在我們 → 開單久是正常的（資源分配問題）
>   · `⛔`     球在我們 → **現在不能做什麼**，置頂印，擱著就是危險還在
>   · `❓`     球在**業主** → 擱置**一定是壞的**：不是他不想決定，是它沒被端到面前
>
> ⛔ 刻意不另開 HAZARDS.md：同一個 bug 的「不要跑」與「要修」同生同滅，
> 分兩個檔就是同一件事寫兩遍，漏改的那一處會變成假警訊。

- [x] (P2) 2026-09-01 向量索引 IVFFlat lists=100 — repo DDL 六處已改 HNSW、本機已重建、不變量 26 已加。⚠️ **降級**：原判「靜默丟答案影響生產」**是錯的**（生產 ORDER BY 寫法用不上索引，35 題修前後逐筆相同）；實為**潛在地雷**——有人把 ORDER BY 改成正規寫法就會引爆。⛔ **線上尚未重建**，見 `ivfflat-index-defect.md` runbook
- [ ] (⛔) 2026-09-01 **架構母圖 §3 的修正只在工作樹、未 commit** — 三條過濾公式已逐行對碼改好（`git diff docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` 可見 +25/-7），但**沒進版控**。⛔ **勿跑 `git checkout .` / `git stash` / `git reset --hard`**，那會讓一整天查證出來的修正無聲消失。⇒ 收成 commit 後才可把本條打勾。⚠️ 在那之前，若有人重新 clone 或還原工作樹，母圖 §3 仍是錯的（照它給 b2b 補 IS NULL 會打穿池隔離；以 `b2b-ground-truth.md` 為準）
- [ ] (⛔) 2026-09-01 Reranker 可用性判定會靜默永久停用 — `semantic_reranker._check_service` 建構期只探測一次（原 timeout=2）失敗即整個 process 停用；rerank 佔最終分數 **90%**，一停就落到詞面分支、純詞面命中得 1.0 壓過正解 ⇒ 使用者收到「請撥打客服專線」。⚠️ 容器 healthy、`/api/v1/system/pipeline-health` 都會回綠（該健檢自己重探測，⛔ 不反映正在服務的物件）。**B 已修**（每 60 秒自動重試、probe timeout 5s、base_retriever 改用 `available()`），⛔ **線上要重 build image 才生效**
- [ ] (⛔) 2026-09-01 semantic-model CPU 推論撐不住 — 實測延遲 >90 秒、CPU 600%+（老毛病，`.kiro/issues/reranker-returning-zero.md` 2026-04-17 已有 hotfix）。B 只讓它能復原，⛔ 沒治產能。加資源／換模型／改 GPU 待裁
- [ ] (P1) 2026-09-01 `include_debug_info` 對面向進場路徑無效 — `_conversational_to_response` 組回應時硬編碼不傳 `debug_info`，不論旗標為何恆 None；`processing_path='conversational'` 佔實測流量 **23%（59/261）** ⇒ 那些題的候選與分數**無法觀測**，回測會誤讀成「沒有候選」。⚠️ 這是**觀測性缺陷**，不影響使用者，但會讓量測失真
- [ ] (P2) 2026-09-01 兩個死開關 — `ENABLE_KNOWLEDGE_RERANKER`／`USE_SEMANTIC_RERANK` 在 compose 與容器都設 true，**serving 程式碼零命中**（只有已知會炸的回測腳本引用）；改它們不會改變任何行為
- [ ] (P3) 2026-09-01 `test_verdict_domain_matches_design_enum` 路徑失效 — 找 `.kiro/specs/retrieval-decision-layer/design.md`，該 spec 已封存進 `archive/`；且 `dr.REPO` 解析成 `/`。屬已封存 spec 的殘留
- [ ] (❓) 2026-09-01 b2b 35 題的「該命中哪筆」待確認 — 未確認前所有命中率只是診斷，不是收案證據
- [ ] (❓) 2026-09-01 80 筆宣告給租客卻在 b2b 池的知識是否誤置 — 取決於「平台操作知識該不該由業者 SOP 承接」的產品意圖
- [x] (✅) 2026-09-01 文件處置**已執行** — 架構母圖 §3 的三條過濾公式與兩處門檻敘述**逐行對碼修正**（非只加警語）；`KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md` 已移入 `docs/archive/2026-09/` 並自標退休
- [ ] (P1) 2026-09-01 D-1：id 4253 分類錯誤致帳單診斷面向領域脈絡從未載入 — 業主裁「先不動」，排在 P1 基準之後
- [ ] (P2) 2026-09-01 不變量 4 與生產程式判準不同源 — 4253 讓它變綠但功能是壞的；需改成與 `system_context.py` 同源
- [ ] (P2) 2026-09-01 D-2：tenant_repair 面向從未寫過系統脈絡列 — 是否刻意設計尚未查證
