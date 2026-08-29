# A03 執行結果（2026-08-29）

```text
A03-LABELS    = **PASS**（L1 98.0%／κ 0.969，四類 raw）
A03-SEMANTIC  = **FAIL ／ RETRIEVAL_SEMANTIC_MISALIGNMENT**
A03-AUTHORITY = **INCONCLUSIVE**
  primary precondition : ELLIPTICAL_AUTHORITY_NOT_SUFFICIENTLY_EXERCISED
  additional confirmed defect : **AUTHORITY_INPUT_TRANSPORT_MISSING**
  ⚠️ ⛔ **不得**把 109 筆 UNKNOWN 當成 authority accuracy failure——
     候選 implementation 根本沒收到 frozen truth。
     「未 exercised／input absent」與「做錯」必須分開。
corpus authorization-2026Q3-A03（digest 4de39adfb5cb8ab3）＝ **BURNED**
```

---

# ⚠️⚠️ 最重要的不是 verdict，是這個 CONFIRMED DEFECT

## P1f 的 authority 在 production 上**結構性失效**

```text
109 筆 Level-A 案例，observed_reason **全部**是
  `applicability_unknown_not_authorized`
⇒ gate **從來沒有看到過** knowledge 的 applicability 宣告
```

### 根因（已對碼確認）

```text
`_applicability_suppressed(best_knowledge, cfg)`
  → knowledge_instance_applicability(row) 讀 row["generation_metadata"]

但 `VendorKnowledgeRetrieverV2` 回傳的知識列**沒有 generation_metadata**：
  id／question_summary／answer／scope／priority／vendor_ids／business_types／
  target_user／keywords／video_url／form_id／action_type／api_config／
  category／categories／intent_id／trigger_* …  ⛔ **無 generation_metadata**

⇒ 宣告永遠讀不到 → 一律 UNKNOWN → 一律 suppress
```

### ⚠️ 為什麼 23 條 P1f 單元測試全過卻沒抓到

```text
測試餵的是  {"generation_metadata": {...}}     ← **production 從不產生的形狀**
production 餵的是 retriever 的列               ← **沒有那個欄位**
⇒ 單元測試在一個**現實中不存在的輸入形狀**上驗證了正確性
```

⚠️ 這正是本條線反覆出現的同一個病灶，而這次**是我自己犯的**：

```text
nomination ≠ authority｜select=api ≠ capability equivalence｜有資料流 ≠ 流到正確語義槽位
                    **fixture 有資料 ≠ production 有資料**
共同形狀：**形式上有接線，不等於語義上接對。**
```

### ⚠️ 22 筆「一致」是**巧合**，不是正確

```text
那 22 筆的 expected_suppress=True（general）、observed=True
但 observed_reason 同樣是 `applicability_unknown_not_authorized`
⇒ **對的動作、錯的理由**
若只比對布林值，它們會被算成「正確」
```

⇒ **業主堅持「UNKNOWN 的 reason 必須與 general 分得開」的設計，正是它把這個缺陷曝光出來的。**
⛔ 若當初把兩者壓成同一格，這輪會得到一個看起來部分成功的假結果。

---

## 【5】Layer A —— FAIL（6/10 units 未達 80%）

```text
G1            8/19 =  42.1%  ❌      I1-explicit  10/10 = 100.0% ✅
G2            3/20 =  15.0%  ❌      I4-explicit   8/10 =  80.0% ✅
G3            6/18 =  33.3%  ❌      I5-explicit   8/ 9 =  88.9% ✅
I2-explicit   3/10 =  30.0%  ❌      I7-explicit  10/10 = 100.0% ✅
I3-explicit   7/10 =  70.0%  ❌
I6-explicit   5/10 =  50.0%  ❌
```

⚠️ 判 **FAIL 而非 INCONCLUSIVE**（協議明定）：第【3】關已保證每個 unit 有足夠可判資料，
資料足夠仍低於預登記門檻 ⇒ 就是**被測 semantic retrieval 沒達標**。

## 【6】elliptical authority exercise —— 5/7 未達 8/10

```text
I1-elliptical 10/10 ✅   I3-elliptical 8/10 ✅
I2 2/10 ❌  I4 4/10 ❌  I5 2/10 ❌  I6 4/10 ❌  I7 7/10 ❌
```

⇒ 依協議 A03-AUTHORITY = INCONCLUSIVE，
⛔ **不得**寫成 RETRIEVAL_INSUFFICIENT（context-dependent query 本就沒有唯一 retrieval oracle）。

## 【7】Layer B

```text
母體 109｜不一致 **87**（全部同一方向：expected=retain、observed=suppress）
```

⚠️ 形式上 A03-AUTHORITY 已在第【6】關停於 INCONCLUSIVE；
但上述 defect 是**獨立於 verdict 的確證事實**，⛔ 不因 verdict 是 INCONCLUSIVE 而被淡化。

---

## 業主裁定與修復（2026-08-29）——採**甲的最小投影版**

```text
✅ retriever 在原 transport 中明示帶出 `knowledge_instance_applicability`
⛔ **不帶**整包 generation_metadata（那包還有其他 authoring/runtime metadata；
   為一個三態值把整個 JSONB 帶過 hot path，會把 transport contract 擴得沒必要）
⛔ **不讓 gate 依 knowledge id 反查**（那會把 retrieval layer 的契約缺失
   補成「consumer 自己去找」，ownership 變差：日後每個 downstream 缺欄位都可能自行反查）
⚠️ 這**不是新 authority source**：唯一權威仍是
   `knowledge_base.generation_metadata.instance_applicability`，retriever 只是 projection
   ⇒ 無 cache 與 DB truth 不一致的問題
⛔ retriever **只搬運原值**：不得做 "INSTANCE"→instance／true→instance／missing→general
   —— 值域封閉與 UNKNOWN 語義一律由 services/instance_applicability.py 負責
命名採 `knowledge_instance_applicability`：downstream 一眼分得出這是 Knowledge 軸，
⛔ 不會與 Face 的 requires_instance_reference 混
```

### 驗證方式已升級（⛔ 不得再用手寫 dict 當 wiring proof）

```text
① production-shape contract  producer row keys ⊇ gate required keys（AST 取真實投影）
② 三態 transport matrix       用 **production shape**（扁平欄位、⛔ 無 generation_metadata）
③ mutation 打 transport seam  移除欄位 → 契約不成立；投影回 null → instance/general 分不開
④ 正對照（真實 retriever path，本地 DB）
     3503→instance｜3402→general｜3406→general｜4640→instance  **全部 OK**
     且確認 production row **不含** generation_metadata
⑤ **不變量 11**（新增）：consumer 從知識列讀取的鍵（含常數間接）⊆ producer 提供的鍵
     ⚠️ 自我測試含「植入缺漏必須被抓到」的正對照——第一版就是因為漏解常數間接而失敗
```

## 原修法選項（保留紀錄）

```text
【甲】retriever 回傳列加上 `generation_metadata`（或只加 applicability 宣告欄）
     ⚠️ 影響面：所有消費該列的路徑；且 generation_metadata 可能很大（含 conversational_config）
【乙】`_applicability_suppressed` 以 knowledge id 反查宣告
     ⚠️ 影響面：在 routing 熱路徑加一次查詢／需快取
```

### ⚠️ 無論選哪個，驗證方式**必須改**

```text
⛔ 單元測試不得再用手寫 dict 當輸入形狀
✅ 必須有一條測試以**retriever 實際回傳的欄位集合**為輸入
   （或直接斷言「retriever 回傳的鍵集合 ⊇ gate 所需的鍵」）
⇒ 否則同一個坑會再踩一次
```

## 未變動

```text
⏸ gate enable｜⏸ 3.4｜⏸ 擴 scope｜⏸ release
Level-A population 與 A03 之前的 implementation SHA 維持凍結
A03 corpus 已 BURNED，⛔ 不得再作 holdout
```
