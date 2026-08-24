# 任務 7：`skip_refine` 語義定案

> 2026-08-25｜語言 zh-TW｜**零 OpenAI、零 DB 寫入**（讀碼 ＋ unit 重現）
> 依賴：任務 4 已完成（不得在其之前動刀——那會在錯誤的症狀上開藥）
> 重現：`tests/unit/conversational/test_skip_refine_semantics_req.py`（2 passed）

## 0. 結論（先講）

```text
問題          skip_refine 是 optimization flag、semantic decision，還是兩種責任混在同一旗標？
答案          **效果上是 dialogue-turn policy；承載的卻是一個 domain fact。兩種責任混在一個布林裡。**
行為是否需改   **不需要**——重查後確實收斂單筆，宣告與行為一致（7.2 的第一個分支）
處置          **文件與命名**：配置鍵註解 ＋ steering 明寫「跳過補識別輪，非跳過重查」
```

## 1. producer → semantics → consumer → observable effect

```text
producer          面向配置 grounding_scope.result_mapping.skip_refine（DB「對話規則」列，
                  布林，預設關）。目前宣告為 true 者：bill_diagnosis、billing_flow。
consumer          **唯一一處**：conversational_engine._ground_by_api() 的
                  「N 筆 ＋ len(candidates) > candidate_cap」分支
                  → `if not mapping.get("skip_refine") and not state.get("_refine_requested")`
semantics（實作）  只決定**要不要多問一輪「請提供更明確的識別」**。
                  它**不**影響：候選集合、cap 截斷、選定後的重查、收斂結果。
observable effect true  → N>cap 時直接列前 cap 筆候選供選序號（少一輪）
                  false → 先要求補識別（設 `_refine_requested`），下一輪仍 >cap 才列候選
```

## 2. 重現結果（7.1）

`test_over_cap_then_pick_then_requery_converges_to_single_row`：

```text
26 筆 > cap=8 ＋ skip_refine=true → 直接列 8 筆候選（未進補識別輪）
使用者回「3」 → prepare 的**插點 A**（pre-LLM，brain 未被呼叫）
→ 選定值填入 required_slots[0]（bill_ref）→ 清除 pending_candidates
→ **重查 → 收斂單筆 → kind=converge**，grounding 帶該筆識別與名稱
```

`test_skip_refine_does_not_change_the_result_set`：

```text
skip_refine=true 直接列出的候選　==　legacy 先補識別、補不動後列出的候選（逐 id 相同）
⇒ 兩條路徑**只差一輪對話**，候選集合完全相同
```

## 3. 語義定位（本題的正面回答）

```text
① 它**不是**單純 optimization flag
   ——省下的那一輪並非「比較慢」，而是**問了使用者答不出來的問題**：
   同母體多期資料（同一合約的 26 期帳單）無法用物件名稱／租期縮小，
   補識別輪在該資料形狀下是**語義上錯誤的提問**。

② 它也**不是** result-mapping 的一部分
   ——它住在 `result_mapping`（該結構其餘鍵皆為 id_field／label_field／list_path
   這類「怎麼讀 API 回應」），但它管的是**對話政策**。位置屬 category error。

③ 因此：**一個布林同時承載兩件事**
   domain fact      「此實體集合無法以關鍵字縮小」
   dialogue policy  「跳過補識別輪」
   前者是資料形狀的事實，後者是由該事實推導出的行為。旗標只表達了後者。
```

## 4. 命名危害（本題最實際的風險）

```text
`skip_refine` 讀起來像「跳過 refine」，而 refine 在本檔脈絡下有兩個可能所指：
  ① 補識別輪（ask for a more specific identifier）   ← **實際跳過的是這個**
  ② 選定候選後的重查（re-query）                     ← **從未被跳過，且已證實會收斂**
```

⚠️ 誤讀成 ② 的後果是有人會「修好」一個不存在的缺陷——例如在選定後略過重查、
直接拿候選列裡的欄位當 grounding。那會讓 grounding 失去 API 權威來源。

## 5. 處置（依 7.2 的第一個分支）

```text
✅ 不改行為、不改旗標名（改鍵名＝改 DB 既有配置列，屬 production 資料變更，
   成本與風險都高於本題的實際危害）
✅ 在 consumer 處的註解明寫「跳過的是補識別輪，不是重查」
✅ 在 .kiro/steering/dialogue.md 加入候選分流速查，載明同一句話
✅ unit 測試鎖住兩端語義（7.3）：>cap 不追問直接列候選／選定後重查收斂單筆
```

## 6. 本檔**未**做

```text
❌ 未改 skip_refine 的實作或預設值
❌ 未替其他面向新增／移除 skip_refine 宣告（那是各面向的資料形狀判斷）
❌ 未處理 candidate_cap 的取值是否合理（不在 Req 5.1 範圍）
```
