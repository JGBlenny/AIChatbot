# 知識批次（prod 部署重放依賴）

runbook §2/§3 引用的知識匯入批次（均經人工閘門審核後定稿）。原開發位置在 `.kiro/specs/<spec>/`
（開發史，不進版控），**定稿副本收於此處供部署重放**——修改批次請兩處同步或以此處為準。

用法：`python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/<batch>.json [--dry-run]`
（冪等；需本機 postgres 5432 與 embedding-api 5001。）`tune_routing.py` 為 §3 進場路由微調工具。

## 欄位契約（2026-09-04 起，工具強制）

- `knowledge[]`／`anchors[]` 每筆**必填** `instance_applicability` ∈ `instance`／`general`（steering knowledge.md「instance applicability 必填契約」，P1d 2026-08-30 生效）。缺或寫錯字 ⇒ 工具整批不寫、exit 2。`general` 必須是正面宣告（不依賴使用者自己的資料也能完整回答），⛔ 不得因「沒有 API／表單」就填 general。
- `updates[]` 可帶 `answer`（不重算向量）與／或 `question`（改 question_summary，**重算 embedding**——S 類「講法」修法）。目標列若尚未宣告 `instance_applicability`，批次必須一併補，否則該筆拒絕（更新會把舊列的 updated_at 推過生效日，不變量 10 會抓）。
- `business_types` 可逐筆指定，未給沿用 `["system_provider"]`（b2b 池）；錨點 `target_user` 未給沿用 `["property_manager"]`。
- 本目錄既有批次皆為 2026-08-30 前定稿、未帶宣告：重放要加 `--allow-legacy-undeclared`，且重放出來的列會被不變量 10 列為未宣告——這是既有債，⛔ 不是工具放水的理由。
- 工具只建 **T1 直答與錨點**；T2（api_endpoints／面向 grounding_scope）、T3（對話規則列 conversational_config）、表單（form_schemas）不走這支，見各面向 spec。
