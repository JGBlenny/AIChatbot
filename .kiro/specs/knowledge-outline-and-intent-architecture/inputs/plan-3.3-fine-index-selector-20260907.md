# Plan 切片 KOIA-3.3：`fine_index.py`＋`candidate_selector.py`——細目索引、記憶體可見性子集、候選選取（2026-09-07）

> 狀態：**收案（2026-09-07）**：3.3a verifier CONFIRMED（三態／決定性／≤8／無外洩，含負對照）；3.3b verifier CONFIRMED（15×3＋4 身分零分歧、突變控制、失敗只收窄、無 `ph:`）；unit 985／integration 210；`make audit` PASS。P4 債：`import_facet_knowledge.py` 空 business_types 預設 system_provider（7.1／3.5 對齊）；`tests/unit/backtest/test_verdict_ruler_req.py` 讀已封存的 retrieval-decision-layer design（別線既有）。前史：第 1 輪 REVISE 3 條 FIX，第 2 輪 READY。分兩段：**3.3a** `FineIndex`（IO／快取／三態／health；**`security-executor`**——tasks 3.3 執行欄對整條指定，且文字外洩控制在此）→ **3.3b** `visible_subset`＋`CandidateSelector`＋SQL 等價測試（`security-executor`）；各自 fresh `verifier`。security-reviewer 唯讀分析已完成（§7）。核准前 ⛔ 不寫碼。對應 tasks 3.3、design 元件 6、R5.1／5.2／5.3／5.6／5.10。前置：3.2（`canon_visible`）已收案 `f17bf5ab`；189 講法已 approved（`b755e685`）。

## 0. 結論先講

啟動時把每細目的「標題向量＋approved 講法向量」建成記憶體索引（決定性、三態、失敗不服務）；每回合先用 3.2 的 `canon_visible` 切可見子集，再在子集內以 `max(cos 標題, max cos 講法)` 取 top-K=5；索引不可用／sha 不符／embedding 失敗一律回 `None`（runtime 退回整份正本）。trace 只記 `winning_key_kind ∈ {title, phrasing}`，⛔ 不記講法 id、⛔ 不 log 查詢。runtime 接線是 4.1，本片只交元件＋health＋測試。

## 1. 結果（outcome）

### 3.3a `services/agent/canon/fine_index.py`
1. `EmbeddingBackend`（Protocol）：`async embed(texts: list[str]) -> list[list[float] | None]`。預設實作 `EmbeddingUtilsBackend` 包既有 `services/embedding_utils.py::get_embedding_client()`（`verbose=False` 固定）：**自行分批 ≤8**、每批 `asyncio.wait_for(timeout)`（`PREPARE_EMBED_TIMEOUT_S=30`）、任何例外／逾時 ⇒ 該批全 `None`（⛔ 不 raise 出 `prepare`）；⛔ 不印任何文字內容（既有 client `verbose` 會 print `text[:50]`，本片固定關）。
2. `FineIndex(backend, *, batch=8)`：`await prepare(doc)`——鍵集合＝每細目 `title` ＋ `status == "approved"` 的講法（`ph:<sha8>` 只作**內部**鍵，⛔ 不出現在任何回傳／trace）；向量 L2 正規化；**任一 None／NaN／零範數 ⇒ `state="not_ready"`、丟棄整份**（⛔ 不以殘缺集合服務）；成功 ⇒ `ready`，`prepared_key=(canon_sha256, phrasing_set_sha256)`、`prepared_sha=canon_sha256`；未曾 prepare ⇒ `absent`。同 key 重複 `prepare` 不重打 embedding（快取）。
3. `fine_index.py` 模組層註冊點 `register_index(audience, index)`／`get_index(audience) -> FineIndex | None`／`reset_index_registry()`（比照 `canon_assembler.register_canon`）；`health.py::_canon_state` 加 `index: {audience: {state, prepared_sha, entries, dim}}`，取不到 ⇒ `absent`、不致紅（沿 `_canon_state` 語義，⛔ 不 monkeypatch health 內部即可構造三態）。**4.1 只呼叫此註冊點，⛔ 不改介面**。
4. 決定性：同 doc＋同 backend 回值 ⇒ 索引逐位元相同；鍵順序＝細目序＋講法序。

### 3.3b `visible_subset`＋`services/agent/canon/candidate_selector.py`
5. `FineIndex.visible_subset(identity, doc, *, vendor_business_types) -> frozenset[str]`＝`{f.id for f in doc.fines() if canon_visible(identity, f, vendor_business_types=…)}`——**薄集合包裝，⛔ 不寫第二套規則**（3.2 已驗 `canon_visible` 與 SQL 17 案零分歧）。
6. `CandidateSelector(index)`：`K=5`、`QUERY_EMBED_TIMEOUT_S=3.0`；`await select(doc, identity, query, *, vendor_business_types=frozenset()) -> Selection | None`：
   - 首行 `doc.canon_sha256 != index.prepared_sha` ⇒ `None`；`index.state != "ready"` ⇒ `None`（`index_unavailable` 由 runtime 以 `None` 判讀，⛔ 不另回半成品）。
   - `query` 由呼叫端組（當前＋上一則 user 訊息，程式規則，4.1 負責）；本片只收字串。查詢向量 `asyncio.wait_for(backend.embed([query]), 3.0)`，失敗／逾時／None ⇒ `None`。
   - `visible = visible_subset(...)`；空 ⇒ `Selection(candidate_ids=[], winning_key_kind={}, scores={}, miss_kind="none_visible")`。
   - 每個可見細目 `score = max(cos(q, title), max_i cos(q, ph_i))`；排序 `(-score, fine_id)`；取前 K；`winning_key_kind[fine_id] ∈ {"title","phrasing"}`（哪個鍵給出最大值；同分取 `title`）；`miss_kind="hit"`。**不設分數門檻、不定義 `MIN_SCORE` 常數**（cos 可為負；design：K 內全給，由模型與 Verifier 守；命名常數會誘導 `score >= MIN_SCORE`）⇒ `no_candidate` 定義為「visible 非空但無任何細目有索引項」，在 `ready` 狀態下不可達，保留於列舉並以測試釘住「不可達」。
   - `Selection` 欄位：`candidate_ids: list[str]`、`winning_key_kind: dict[str, Literal["title","phrasing"]]`、`scores: dict[str, float]`、`miss_kind`。**⛔ 無 `winning_key`／`ph:*`**（§8.1）。
   - ⛔ 不 log 查詢字串、不 print；模組內不得有 `logging`／`print` 帶入 `query`。
7. 等價驗收（R5.3；tasks「集合相等」）：合成正本（細目覆蓋 `target_user ∈ {[prospect],[property_manager],[tenant],[all_users],[]}` × `business_types ∈ {[system_provider],[rental],[]}`，**全部帶 `reviewed: {by: test, at: 2026-09-07}`**——`canon_visible` 首行以 `reviewed_by` 閘門、而 `build_visibility_predicate` 刻意不含審核謂詞；另加**一列未審細目作單向正對照**：記憶體不可見、SQL 可見，記為刻意不對稱，⛔ 不得以放寬記憶體側收斂），DB 側在交易內插入等價列（`generation_metadata->>'canon_ref'`＝細目 id；**空陣列一律寫 NULL**，見 §8.2；`is_active=true`、`vendor_ids NULL`），對身分 b2b pm、b2b prospect、b2c tenant（vendor bt `{rental}`；SQL 側以 `param_resolver` 替身注入業態，樣式見 `test_visibility_predicate_equiv.py::_refactored_where`）三組比 `visible_subset` 與 `build_visibility_predicate` 回傳的 id 集合**相等**（比對集合＝已審細目）；**突變控制**：翻一列 `business_types` ⇒ 兩側同步變動；prospect 真正本上的 b2b pm 案是空集合＝空集合（不具鑑別力），⛔ 不得作為唯一證據。

## 2. 現況事實（security-reviewer 2026-09-07 實查）

- `services/embedding_utils.py::EmbeddingClient`：async；`get_embeddings_batch` 對全部文字 `asyncio.gather`（無 ≤8 批次、無並行上限）；`httpx.AsyncClient(timeout=30.0)` 寫死、無 timeout 參數；失敗走 `print()` 不是 `logging`；`verbose=True` 會印 `text[:50]`；無快取；單例 `get_embedding_client()`。
- 正本講法現況：189 條 **approved**（業主 2026-09-07 批核，`b755e685`）；`canon_sha256` 涵蓋整份 `.md` ⇒ 講法狀態翻轉必變 sha，`phrasing_set_sha256` 在快取鍵中是冗餘但無害（保留，design 明列）。
- `canon_assembler.canon_visible(identity, fine, *, vendor_business_types)` 已存在、與 SQL 零分歧（3.2 verifier）；`VendorParameterResolver.get_vendor_info` 存在但**同步 psycopg2**（4.1 呼叫點的事件迴圈阻塞問題，不在本片）。
- 既有假 embedding 測試樣式：`tests/unit/conversational/test_s1b_responsibility_telemetry_req.py::_FakeEmbeddingClient`（建構子注入）；等價測試樣式：`tests/integration/agent/test_visibility_predicate_equiv.py`（`BASE_ID=9_000_000`、`finally: DELETE`、避開 `updated_at` trigger 陷阱）。
- `tools/import_facet_knowledge.py`：拒絕空 `target_user`、空 `business_types` **預設寫 `["system_provider"]`** ⇒ 與記憶體規則「b2b 空 ⇒ 不可見」方向相反（§8.2）。
- 3.2 P3 債：`build_outline` 未套 `canon_visible` ⇒ `select()` 回 `None` 的退路是「整份正本（未依可見性過濾）」——在單一受眾正本下無害，**4.1 必須先套**（tasks 4.1 已記）。
- design 元件 6 `Selection.winning_key: dict[str,str]`（`ph:<sha8>`）與 tasks 3.3／F18「只記 `winning_key_kind`」衝突（§8.1）。

## 3. 非目標

- 不接 runtime／`run_turn`／`CandidateOutlineDoc`（4.1）；不做 `index_eval.py`（3.4）；不做不變量 33／34（3.5）；不接 reranker（R5.11）；不做內文向量臂（3.4 對照）；不改 `embedding_utils.py` 本體（只包）；不動 `canon_visible`／`build_visibility_predicate`；不解 4.1 的 `get_vendor_info` 同步阻塞。

## 4. 驗收（容器內）

**3.3a**
1. `prepare` 對合成 doc（3 細目、含 approved／proposed／retired 講法各一）：鍵數＝細目數＋approved 講法數（proposed／retired 不進）；分批 ≤8（假 backend 記錄每次呼叫長度，最大 ≤8）；決定性（兩次 prepare 索引相等）。
2. 三態：未 prepare ⇒ `absent`；假 backend 對任一文字回 None ⇒ `not_ready` 且無殘缺索引；全 None／raise／逾時（假 backend sleep > timeout）⇒ `not_ready`，`prepare` 不 raise；正常 ⇒ `ready`、`prepared_key` 正確。
3. 快取：同 doc 二次 `prepare` ⇒ backend 呼叫數不增；改一條講法狀態（sha 變）⇒ 重建。
4. health：經 `register_index` 註冊三種狀態的索引各一案、未註冊 ⇒ `absent`，皆不致紅（正對照：既有 `_canon_state` 測）。
5. 隱私：`caplog`＋`capsys` 都無任何細目標題／講法／查詢文字（正對照：先故意 log 一個標記字串證明兩個擷取器都活著）。

**3.3b**
6. `visible_subset` 對合成 doc × 三組身分＝逐細目 `canon_visible` 的集合（薄包裝證明）；SQL 等價 integration（§1.7）三組集合相等＋突變控制兩側同動＋未審列只出現在 SQL 側的單向斷言；prospect 真正本：b2b prospect ⇒ 全 38、b2b pm ⇒ ∅（記錄為不具鑑別力）。
7. `select`：sha 不符 ⇒ `None`；`absent`／`not_ready` ⇒ `None`；查詢 embedding None／raise／逾時 ⇒ `None`（⛔ 不變寬：三者皆不得回任何 candidate）；visible 空 ⇒ `none_visible`；正常 ⇒ `hit`、`len ≤ 5`、排序 `(-score, id)`、同分 id 字典序（假向量刻意同分）；`winning_key_kind` 值域只有 `title`／`phrasing`，回傳結構序列化後**不含 `ph:`**；**不可見細目不出現在 candidate_ids**（假向量讓不可見者分數最高，仍被排除）。
8. 隱私：`select` 全流程 `caplog`＋`capsys` 無查詢字串（正對照同 §4.5）。
9. `scripts/run-tests.sh unit tests/unit/agent/ tests/unit/_meta/`＋`integration tests/integration/agent/` 綠；`make audit` 27–32 不變。
10. fresh verifier：3.3a 主張「三態＋決定性＋不殘缺服務＋無文字外洩」；3.3b 主張「可見子集＝SQL 集合（含突變控制）＋失敗只會回 None 不會變寬＋trace 無講法 id」。

## 5. 回滾／預算／停損

- 回滾：刪兩個新模組與測試、還原 `health.py`。$0（embedding 只在測試用假 backend；integration 等價測試不打 embedding）。
- 停損：等價測試任一組不相等 ⇒ 停下列差異交裁，⛔ 不改規則遷就 SQL 或反之；verifier REFUTED 兩次即停。

## 6. 對 design 的偏離（待回寫）

- `Selection` 去掉 `winning_key`（`ph:<sha8>`）、只留 `winning_key_kind`（§8.1）。
- `EmbeddingBackend` Protocol 取代 design 假設的 `EmbeddingClient` 形狀（既有 client 無批次／timeout）。
- `no_candidate` 定義為「visible 非空但無索引項」（ready 下不可達）；不定義 `MIN_SCORE` 常數。
- 3.3a 與 3.3b 皆 `security-executor`（tasks 3.3 執行欄原意）。
- 3.3a 實作判讀（主 session 採納，2026-09-07）：**失敗的 `prepare` 不進快取**（快取鍵只在成功時設，暫時斷線不會把索引永遠釘在 `not_ready`；`not_ready` 本就不服務，重試不會變寬）；`batch` 上限 `MAX_BATCH=8` 建構子不可放寬（是對 embedding API 的保護不是調校旋鈕）；零鍵正本 ⇒ `not_ready` 而非 `ready` 空索引；`register_index` 對非法 audience raise `ValueError`（不 import `canon_assembler` 以免拉進 DB 棧）；health 三受眾恆列、未註冊 `absent`。殘留：既有 `EmbeddingClient` 失敗時 `print` 例外（不含文字），改它要動 `embedding_utils.py`，本片不動。

## 7. security-reviewer findings 處置

| # | 級 | 內容 | 處置 |
|---|---|---|---|
| 1 | P1 | 既有 `EmbeddingClient` 無 ≤8 批次、無 timeout、失敗 print、verbose 印文字 | FIX：`EmbeddingBackend` 包裝自行分批＋`wait_for`＋`verbose=False` |
| 2 | P1 | 只用 `caplog` 看不到 print | FIX：`caplog`＋`capsys`＋正對照 |
| 3 | P1 | `None` 退路＝整份正本未過濾（3.2 P3 債） | 記 §2、4.1 前置（tasks 4.1 已記）；本片 `select` 對不可見細目仍排除 |
| 4 | P2 | b2b pm 等價案在 prospect 正本上空＝空 | FIX：合成細目＋突變控制（§1.7） |
| 5 | P2 | 空陣列 vs NULL：匯入預設 `system_provider` | **交業主（§8.2）** |
| 6 | P2 | 講法全 proposed ⇒ 索引只有標題 | 已解：業主批核 189 條 approved |
| 7 | P2 | design `winning_key`（ph id）vs tasks `winning_key_kind` | **交業主（§8.1）**，建議照 tasks／F18 |
| 8 | P3 | 決定性：NaN／零範數／同分 | FIX：not_ready＋`(-score,id)` |
| 9 | P3 | `get_vendor_info` 同步阻塞 | 4.1 議題，記錄不動 |

## 8. 待業主核

1. **trace 記不記講法 id**：design 元件 6 `Selection.winning_key` 含 `ph:<sha8>`，tasks 3.3 與 F18 說只記 `winning_key_kind`（講法對照表在 repo，記 id 等於可還原問句）。建議照 tasks／F18：不記，回寫 design。
2. **空陣列語義與匯入契約**：記憶體規則「空＝不設限」（b2c）／「b2b 空 business_types ⇒ 不可見」；SQL 用 `IS NULL` 放行；匯入工具卻把空 `business_types` 預設成 `["system_provider"]`（會讓 b2b 看見）。建議：**7.1 export／7.2 import 契約改為「正本空清單 ⇒ 寫 NULL，⛔ 不預設」**，並在不變量 33（3.5）加對帳；本片等價測試依此假設插 NULL。
