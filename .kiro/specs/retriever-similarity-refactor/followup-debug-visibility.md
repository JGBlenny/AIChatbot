# Followup：retrieve() threshold 過濾造成 debug 可觀察性損失

> 建立時間：2026-04-16T17:10:00Z
> 來源：retriever-similarity-refactor 重構後的 chat-test 手測盤查
> 狀態：待決策（選項 A / B / C）
> 相關 spec：`.kiro/specs/retriever-similarity-refactor/` 本體已完成，此為補丁追蹤

---

## 1. 背景

重構完成 tasks 0.1–10.2 後，使用者在 chat-test 以「合約簽署」查詢，觀察到知識候選全部顯示 `base_similarity = 0.000`，懷疑是重構 bug。

盤查經過：
1. 原以為是「純 keyword_fallback 命中項目 vector_similarity=0」的設計行為
2. 實際呼叫 API 發現 `score_source=None`、`[Finalize]` log 完全缺席
3. 檢查後發現 `UVICORN_RELOAD=false` → **服務跑的是舊 code**，docker cp 沒觸發重載
4. `docker restart aichatbot-rag-orchestrator` 後，新 code 才生效

重啟後真實行為如下：

```
KB 路徑（閾值 0.65）:
  向量檢索: 找到 56 個結果
  Reranker: 已重排序（top_k=5）
  [Finalize] 計算 5 筆，分數來源: rerank=5, keyword=0, vector=0
  閾值過濾: 5 → 0 筆 (>= 0.65)
  最終結果: 0 個
```

`retrieve()` 末端的 application threshold 過濾器把全部 5 筆擋下（都 < 0.65），`knowledge_list = []` 回到 chat.py。

---

## 2. 缺口定義

| 行為 | 舊 code（pre-refactor） | 新 code（post-refactor） |
|------|-----------------------|------------------------|
| 低分 KB 候選留在 retrieve 回傳 | ✅ 保留（threshold 行為不同）| ❌ 被過濾 |
| chat-test 可見度 | ⚠️ 可見但 `base_similarity=0` 誤導 | ❌ 完全不可見（`knowledge_candidates: []`）|
| 產線答案品質 | ⚠️ 低分答案可能被誤用 | ✅ 低分一律擋下 |

**新 code 在答案正確性上贏了**（符合設計意圖），但 **debug 可觀察性退步**：
- 使用者無法在 chat-test 看到「為什麼沒命中」
- 也無法校準 `KB_SIMILARITY_THRESHOLD`（看不到臨界候選分數分布）
- 對 Task 7.5 手動驗證「純 keyword 路徑命中的項目顯示 base_similarity = 0」反而無從觀察（因為被過濾）

---

## 3. 根因

`base_retriever.retrieve()` Step 7：

```python
# Step 7: application 端 threshold 過濾（比對 final similarity）
before_filter = len(results)
results = [r for r in results if r.get('similarity', 0) >= similarity_threshold]
```

此過濾同時服務兩種目的：
1. **產線答案**：確保 LLM 只收到達標候選
2. **debug 顯示**：`retrieve()` 的 return value 也是 chat.py debug_info 的來源

重構前兩者合一沒問題（低分候選本來就留在 SQL 層），重構後 SQL 不再過濾改由 application 過濾，兩種目的的需求就分叉了。

---

## 4. 選項比較

### 選項 A：debug 旁路

**做法**：
- `retrieve()` 新增選參 `return_unfiltered: bool = False`
- chat.py 發現 `include_debug_info=True` 時呼叫第二次 `retrieve(..., return_unfiltered=True)` 拿到過濾前候選
- 兩個 list 都送到 debug_info

**優點**：
- `retrieve()` 語意不變（產線呼叫維持過濾行為）
- 變更侷限在 chat.py + base_retriever

**缺點**：
- 同一查詢跑兩次 retrieve，增加延遲（約 +500ms，含 rerank HTTP）
- 快取 key 需區分兩種模式
- 手段粗糙

**影響範圍**：base_retriever.py（1 個參數）、chat.py（兩處 debug 構建點）

---

### 選項 B：過濾移到 application 層（推薦）

**做法**：
- `retrieve()` 移除 Step 7 的 threshold 過濾，只保留 `_finalize_scores` + 排序 + top_k
- chat.py 在 `_retrieve_sop` / `_retrieve_knowledge` 後自己做 threshold 過濾
- debug_info 直接用過濾前的完整候選，`is_selected` 標記哪些達標

**優點**：
- `retrieve()` 職責更單一（檢索與排序，不做業務過濾）
- debug 自然得到完整候選，零額外成本
- 符合重構 design.md 決策 3 的「application 端過濾」精神

**缺點**：
- 所有 `retrieve()` 的既有呼叫方都要檢查是否依賴 threshold 過濾行為
- 單元測試 `test_base_retriever_pipeline.py::test_retrieve_filters_by_final_similarity_threshold` 要改
- 向後相容考量：回測腳本、knowledge_orchestrator 等消費者

**影響範圍**：
- `base_retriever.retrieve()`（移除 Step 7）
- `chat.py._retrieve_knowledge` / `_retrieve_sop`（加過濾）
- `sop_orchestrator.py`（確認是否依賴 retrieve 的過濾）
- 測試：調整 4 個相關 test case

---

### 選項 C：維持現狀 + 前端文案

**做法**：
- `retrieve()` 行為不變
- chat-test UI 加說明：「KB 無達標候選」時顯示提示
- 另開 `/api/v1/message/debug` 路徑回傳無過濾結果，供 chat-test 呼叫

**優點**：
- 後端完全不動
- 職責清晰：產線 API 歸產線、debug API 歸 debug

**缺點**：
- 前端需改動
- 新增 API 表面積
- 實作成本最高

**影響範圍**：knowledge-admin-web（新畫面）、rag-orchestrator（新 endpoint）

---

## 5. 決策

**採用選項 A**（使用者於 2026-04-16 確認），理由：

1. **影響範圍最小**：不動既有消費者對 `retrieve()` 過濾行為的依賴（sop_orchestrator、backtest、knowledge_list 下游消費者都假設 retrieve 已過濾）
2. **產線路徑零變化**：`include_debug_info=False` 的請求完全走原流程，不引入回歸風險
3. **debug 成本只在 debug 時付**：正式產線流量不多跑一次 retrieve
4. **重構本體剛完成，再動 retrieve 核心過濾邏輯風險過高**：選項 B 需檢查所有消費者的過濾假設，選項 A 是增量式改動

**代價接受**：debug mode 延遲 +500ms 左右（多一次 rerank HTTP）；chat-test 手測可接受。

---

## 6. 實作計畫（選項 A）

### Step 1：`base_retriever.retrieve()` 新增選參 `return_unfiltered`

```python
async def retrieve(
    self,
    ...,
    return_unfiltered: bool = False,  # 新增
    **kwargs
) -> List[Dict]:
    ...
    # Step 6: _finalize_scores（不變）
    results = self._finalize_scores(results)

    # Step 7: application 端 threshold 過濾（僅 return_unfiltered=False 時執行）
    if not return_unfiltered:
        before_filter = len(results)
        results = [r for r in results if r.get('similarity', 0) >= similarity_threshold]
        if before_filter != len(results):
            print(f"   閾值過濾: {before_filter} → {len(results)} 筆 (>= {similarity_threshold})")

    # Step 8: 排序 + top_k（不變）
    results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    results = results[:top_k]
    return results
```

產線路徑 `return_unfiltered=False`（預設）→ 行為完全不變。

### Step 2：便利方法透傳參數

`vendor_knowledge_retriever_v2.retrieve_knowledge_hybrid`、`vendor_sop_retriever_v2.retrieve_sop_by_query` 兩個 wrapper 都加 `return_unfiltered: bool = False` 並透傳給 `retrieve()`。

### Step 3：chat.py 在 debug 模式下跑第二次

`_retrieve_knowledge` 簽章改為回傳 tuple：

```python
async def _retrieve_knowledge(request, intent_id, intent_result):
    retriever = _get_knowledge_retriever()

    # 產線用（過濾後）
    knowledge_list = await retriever.retrieve_knowledge_hybrid(
        ...,
        return_debug_info=request.include_debug_info,
    )

    # debug 用（過濾前）
    unfiltered = None
    if request.include_debug_info:
        unfiltered = await retriever.retrieve_knowledge_hybrid(
            ...,
            return_debug_info=True,
            return_unfiltered=True,
        )

    return knowledge_list, unfiltered
```

`decision` 物件同步新增 `knowledge_list_unfiltered` / `sop_list_unfiltered` 欄位供 debug 路徑讀取。

### Step 4：debug_info 顯示用 unfiltered

原本：
```python
for k in decision['knowledge_list']:  # 過濾後
    knowledge_candidates_debug.append({...})
```

改為：
```python
source_list = decision.get('knowledge_list_unfiltered') or decision.get('knowledge_list') or []
passing_ids = {k['id'] for k in (decision.get('knowledge_list') or [])}
for k in source_list:
    knowledge_candidates_debug.append({
        ...,
        'is_selected': k['id'] in passing_ids,  # 標記是否通過 threshold
    })
```

chat.py 中所有 knowledge_candidates_debug / sop_candidates_debug 構建點（約 8 處）都要同步改。

### Step 5：測試

- **新增**：`test_retrieve_return_unfiltered_skips_threshold_filter`（驗證 `return_unfiltered=True` 時所有候選回傳，不過濾）
- **不動既有**：`test_retrieve_filters_by_final_similarity_threshold` 維持（驗證 default 行為）
- **新增**：chat.py debug response 包含 threshold 之下候選的整合測試

### Step 6：手動驗證

重跑「合約簽署」查詢，預期：
- `debug_info.knowledge_candidates` 有 5 筆（而非目前的 0 筆）
- `base_similarity` 顯示真實 `vector_similarity`（非 0）
- `is_selected=false` 因為 final similarity < 0.65
- `[Finalize]` log 出現兩次（一次產線、一次 debug）

---

## 7. 未決事項

- [x] 使用者最終選擇 → **選項 A**
- [ ] 前端 chat-test 是否需要同步加「is_selected=false」視覺標示（例如淡色字）？
- [ ] `return_unfiltered=True` 是否走獨立 Redis 快取 key？（避免污染產線快取）
- [ ] 回測腳本 `backtest_framework_async.py` 目前讀 `debug_info.knowledge_candidates`，語意變更（現在會含低分候選）是否影響回測結果解釋？→ 需確認後端回測使用的是 `sources` 欄位還是 `debug_info.knowledge_candidates`

---

## 8. 變更歷史

| 日期 | 變更 |
|------|------|
| 2026-04-16 | 初版建立（盤查發現記錄、三選項分析）|
| 2026-04-16 | 使用者決策採選項 A，實作計畫改寫為 return_unfiltered 旁路方案 |
| 2026-04-17 | 實作完成並手動驗證通過：knowledge_candidates 5 筆顯示真實 vector_similarity（0.3–0.5），is_selected 正確標記未達 threshold 候選 |
