# 任務 9 落實紀錄：`repair_create` 進場點（需求 5.3, 6.6）

> 2026-08-26｜語言 zh-TW｜零 OpenAI 呼叫、未碰 staging／production
> **9.1 前提已過期（不需新增知識）；9.2／9.3 完成；9.4 上線受 6.3 CLOSED gate 約束。**

## 一、9.1 的前提**已經過期**——不是照做，是查證後改判

spec 記載：「`修繕報修` 目前 **0 個知識進場點**」。
實查 dev DB（業主裁定本地≡線上）：**已有 5 筆**，且正是設計決策 3 的**選項 C**
（新增語義正確的租客向觸發知識，`categories={修繕報修}`、`target_user={tenant}`，
未替 3365／4249 加標）。

```text
來源   conversational-repair 任務 3.3，commit 646743a0（2026-07-12）
工具   rag-orchestrator/tools/seed_repair_facet_knowledge.py（冪等、走既有 embedding 路徑）
⇒ 本任務**不再新增知識**，改為釘住既有進場點並驗證不誤進場。
```

⚠️ 教訓：spec 的「實查 DB」結論有保鮮期。**寫下時為真，執行時要重查**——
本次若照字面補知識，會多出重複的進場點。

## 二、EntryPointChange（① 明確記錄的 Face entry points）

```python
EntryPointChange(
    knowledge_ids=[4416, 4418, 4420, 4421, 4422],
    facet_key="repair_create",
    added_categories=["修繕報修"],
    declared_entry_points=[
        "報修 修繕 東西壞了 想報修",          # 4416 direct_answer（意圖錨點）
        "馬桶不通 排水堵塞 水管堵住",          # 4418 direct_answer
        "修繕進度 報修單 修得怎樣了 處理到哪",  # 4420 api_call → jgb_repairs（查進度）
        "漏水 滲水 天花板漏水 水管漏水",        # 4421 direct_answer
        "冷氣壞了 電器壞了 家電故障",          # 4422 direct_answer
    ],
    regression_baseline="tests/integration/conversational/test_repair_entry_points_req.py（10 passed）",
    misroute_probe_cases=["租金怎麼繳", "合約什麼時候到期", "押金什麼時候退", "電費怎麼算"],
    gate_passed=False,      # ④ 受 6.3 的 production-facing gate CLOSED 約束
)
```

## 三、② 以現行 production routing 規則回歸

驅動的是 production seam（決定性、零 LLM）：
`retrieve_knowledge_hybrid(top1)` → `routers.chat._diagnosis_config_for_knowledge`，
門檻取自唯一讀值點 `DecisionConfig.load()`，**不在測試內複刻**。
角色維度為 **tenant／b2c**（與帳務／合約面向的 property_manager／b2b 不同）。

```text
config_for_category('修繕報修') → repair_create（enabled，persona=tenant_repair）✅
「我房間的冷氣壞了想報修」「馬桶不通可以幫我處理嗎」「天花板在漏水」「東西壞了要怎麼報修」
  → 皆進 repair_create ✅
```

進場點本身也被釘住：5 筆逐筆檢查 `is_active`、`target_user == ['tenant']`，
且**不得出現未宣告的第 6 筆**——新增掛 `修繕報修` 的知識即新增 Face entry point，
必須走 R6.6 回歸，測試會因此變紅。

## 四、③ misroute probe

```text
租金怎麼繳／合約什麼時候到期／押金什麼時候退／電費怎麼算 → **皆未進** repair_create ✅
```

⚠️ 這條的後果不是「答錯」而是**替錯的人開報修單**——交易面向的誤進場成本高於資訊面向。

## 五、`make audit` 不變量對照（設計已預先補正過位置）

```text
不變量 1（動作知識必有面向接管）  ✅ PASS
    掛帳 3 筆：3514（租客管理）＋ **3365／1558（修繕）** —— 與 spec 記載一致，未變動
不變量 4（面向 category 必有系統脈絡知識）  ⚠️ WARN：修繕報修
    ⚠️ **這是既有且已被裁定的豁免**：conversational-repair tasks.md:57 明載
      「不變量 4 對『修繕報修』WARN 屬預期（交易面向不需系統脈絡長文）」。
      故本任務**不補系統脈絡知識**——補了反而違反該裁定。
不變量 3／7 的 FAIL 與本任務無關（3＝容器與本地不同步，屬部署；
    7＝`services/jgb/fixtures.py` 直讀 final_total，屬 C4a fixture 的既有債）。
```

## 六、9.4：上線狀態

```text
9.1  ✅ 前提過期，查證後改判為「已滿足」
9.2  ✅ 進場點記錄＋production routing 回歸（10 passed）
9.3  ✅ misroute probe 全綠；不變量狀態與預期一致
9.4  ⛔ 受 6.3 的 production-facing gate **CLOSED** 約束（gate 擋 deploy，不擋 development）
```
