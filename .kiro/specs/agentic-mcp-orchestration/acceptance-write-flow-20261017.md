# 驗收清單：寫入流程由程式掌握 W1（2026-10-17，r9＝W1c 增列單元測試，8 項原條件不變、未收窄）

計畫：`plan-write-flow-program-owned-20261017.md`
業主原話：「修繕 不能延續處理了嗎」「像是品質是不參考 要寫規則 這會不會也是類似問題」「但是需要通用處理 不能局部補丁」；方向選擇「程式掌握流程」（選項說明：換模型不影響流程；需 gpt-6-luna 重跑不退步）。

觀察點一律是本機評估容器的真實 `/mcp` `agent.turn`（`~/jgb-archive/bedrock-eval-20261017/start_eval_svc.sh A|B`；A＝gpt-6-luna effort none、B＝gpt-oss-120b effort low；`USE_MOCK_JGB_API=true`、fixture `assistant_demo_vendor4.json`；`AGENT_BUDGET_TOOL_CALLS=3`），讀回傳的 `outcome.state`、`answer` 與 `usage_events.decision_snapshot->'agent'`（tool_calls、violations）。每輪一個新 `session_id`。證據檔放 `~/jgb-archive/bedrock-eval-20261017/w1/`。

## 凍結腳本

- **R（報修）**：「能幫我新增一張修繕單嗎」→「學生獨立套房可租補」→「冷氣不冷」
- **D（延期繳費）**：「我想把一張帳單延後繳」→「基隆溫馨一人宅套房 11月那期」→「延 7 天」（fixture 帳單 709744，2026-11）
- **C（建合約，D 前置查不到帳單時的備案）**：「幫我建立一份新合約」→「物件是學生獨立套房可租補」→「2026年11月1日到2027年10月31日，月租12000元，承租人信箱 w1-test@example.com」
- **T（改談別的）**：「能幫我新增一張修繕單嗎」→「租金可以設定自動扣款嗎」→「學生獨立套房可租補」
- **P（知識題）**：v2 題庫 `~/jgb-archive/bedrock-eval-20261017/v2/questions.json` 30 題 ×1

## 項目

| # | 對應業主字句 | 宣稱 | 觀察點 | 證據 | 通過條件 |
|---|---|---|---|---|---|
| 1 | 「修繕 不能延續處理了嗎」 | gpt-oss 報修三步接到確認卡 | B，腳本 R ×3 輪 | `w1/R_B.json` | 3/3 輪第三句 `outcome.state=confirm_pending`，卡上物件＝學生獨立套房可租補、問題描述含「冷氣不冷」；3/3 輪第二句回覆不含「物件」追問（只追問問題描述）；3/3 輪第一句 violations 含 `confirm_missing_fields_ask`（程式追問，非模型自寫） |
| 2 | 「通用處理 不能局部補丁」 | 同一機制套用到第二支寫入動作 | B，腳本 D ×3 輪（備案 C） | `w1/D_B.json`（或 `w1/C_B.json`）；改動前現值 `w1/D_B_before.json` | 3/3 輪第三句 `confirm_pending`，卡上延後 7 天、帳單編號＝709744（fixture 中屬基隆溫馨一人宅套房、2026-11；卡面只印編號，以編號對 fixture 判）（C：卡上物件、起迄、租金、信箱與腳本一致） |
| 3 | 「通用處理 不能局部補丁」 | 缺欄計算與追問由同一張表驅動，無動作專屬字面 | 程式＋單元測試 | `grep -rn '"物件" in _missing\|REPAIR_MISSING_LABELS' rag-orchestrator/services/agent/` 輸出；正對照 `grep -rln 'CLOSED_ACTION_FIELDS' rag-orchestrator/services/agent/`；pytest 輸出 | grep 目標零命中（改動前實測有命中：`runtime.py` 的 `"物件" in _missing`、`tools/confirm.py` 的 `REPAIR_MISSING_LABELS`；正對照有命中）；單元測試對 5 支動作各缺一個必填欄，皆斷言回 `missing_fields`、程式追問句與 `ask_target` 由表導出；`bill_due_extend` 另有「缺 days」「缺 bill_id 且缺 estate_name」兩題皆得程式追問句（後者標籤含物件與期別、`ask_target=estate`）；封閉三動作缺欄標籤與改動前逐字相同；修繕與封閉三動作各缺欄組合（至少：只缺物件、缺物件＋其他、只缺問題描述、只缺非物件的單一欄、缺多個非物件欄）的 `ask_target` 與改動前逐位相同；`contract_create` 從真的程式缺欄追問回合開始（缺物件 ⇒ `ask_target=estate` 寫入 `LAST_ASK_TARGET_KEY`），下一句為唯一命中物件名 ⇒ 名稱寫進 `estate_name`、`contract_ref` 不寫（⛔ 由測試直接設狀態）；`bill_due_extend` 模型自呼缺 `days` ⇒ 回 `missing_fields`、程式追問（明列行為變更）；草稿 `{"days":"7","estate_name":"基隆溫馨一人宅套房","period":"11月那期"}` 經程式觸發得 `confirm_pending`（`to_payload` 轉型），腳本 C 欄位組合同一條；模型自己呼叫 `confirm.request` 帶 `description:""` ⇒ 改動前後皆得程式追問「問題描述」；`write_intent` 帶分類樹外的值 ⇒ 不進草稿，下一次觸發照常出卡或追問；只表態意圖（`fields` 空）⇒ 程式追問句＋表導出 ask_target，下一句名稱經前置查詢唯一命中寫進草稿；草稿 `{"estate_name":"學生獨立套房可租補","description":"冷氣不冷","emergency_status":"2"}` 經程式觸發得 `confirm_pending`、卡上急迫程度為「緊急」；使用者原話用腳本 C 第三句、`write_intent` 帶 `date_end`=2027-10-31 與 `to_user_email`=`w1-test@example.com` ⇒ 兩者進草稿、觸發後卡上到期日 2027-10-31、信箱 `w1-test@example.com`；模型自己呼叫 `confirm.request` 帶 `{action: bill_due_extend, days: 7, estate_name: <fixture 中只有一張帳單的物件>}`（不帶期別）⇒ 改動前後結果逐位相同 |
| 4 | 「程式掌握流程」→換模型不影響流程 | gpt-6-luna 不退步、知識題不誤觸發 | A：腳本 R、D（或 C）各 ×3；A、B：腳本 P ×1 盲判（blind-judge，判準沿用 `v2/SPEC.md` 修正參考） | `w1/R_A.json`、`w1/D_A.json`、`w1/P_A.json`、`w1/P_B.json`、判分輸出 | A 的 R、D 皆 3/3 `confirm_pending`；P 中出卡或寫入追問（violations 含 `write_draft_program_confirm` 或 `confirm_missing_fields_ask`）的回合 A、B 各 0；盲判錯誤數：A ≤1/30（基準 0/90，`v2/RESULT.md` 修正參考）、B ≤3/30（基準 6/90＝6.7%，期望約 2/30，容許 +1）；盲判正確數：A ≥22/30（基準 74/90＝82.2%，期望約 24.7，容許 −2.7）、B ≥24/30（基準 80/90＝88.9%，期望約 26.7，容許 −2.7） |
| 5 | 「修繕 不能延續處理了嗎」（要能用） | 延遲不惡化到不可用 | #1、#2、#4 每回合秒數 | 同上 JSON 的 `s` 欄 | 腳本 R、D 回合：兩模型各自中位數 ≤ 3 秒、最大 ≤ 20 秒（基準：`s1/s1_A.json` 報修回合中位 1.8／最大 2.1 秒；`s1/s1_B.json` 中位 1.3／最大 17.5 秒） |
| 6 | 「程式掌握流程」（可回退） | `AGENT_WRITE_DRAFT=off` 時與現行相同 | 單元測試 | pytest 輸出 | （宣稱範圍：off 撤回意圖呼叫、草稿、程式觸發；缺欄統一不隨開關回退，見計畫 §2.5）W1b：on 與 off 的 `_agent_output_response_format()` 產出皆與改動前逐位相同；off 時不發意圖判斷呼叫；不帶 `write_intent` 的既有假輸出在 on 與 off 下皆通過 `AgentOutput.model_validate`；off 時不寫 `write_draft`、不觸發程式 `confirm.request`；golden 測試在 off 下全部通過；`AGENT_WRITE_DRAFT` 未設與空字串皆為 on、值 `xyz` 啟動失敗並印原因；W1b：意圖判斷呼叫的 schema description 含表單導出的動作名與鍵名 |
| 7 | 「通用處理」（不打壞別處） | 全量單元測試無新失敗；不變量通過 | `cd rag-orchestrator && python -m pytest tests/unit -q`；`make audit` | `w1/pytest.txt`、`w1/audit.txt`、`w1/baseline_red.txt` | 失敗皆在基線名單內且數量 ≤ 基線；`make audit` OVERALL: PASS |
| 8 | 「但是需要通用處理」（流程要分得清） | 改談別的不污染草稿；捏造值進不了草稿 | B、A：腳本 T 各 ×2；單元測試 | `w1/T_B.json`、`w1/T_A.json`；pytest 輸出 | T 第二句不出卡、不出寫入追問；第三句回覆追問問題描述（⛔ 出卡、⛔ 卡上問題描述＝第二句）；單元測試：模型 `write_intent` 填使用者沒講的文字／數字、值域外的 `emergency_status`（例 "3"），以及模型 `confirm.request` payload 帶使用者沒講的文字，皆不進草稿並記 violation（值域內的 enum 捏造不在本項宣稱內，見計畫 §4）；意圖呼叫假回應帶值域外的 `action`／`key` ⇒ 主回合 `answer` 照常出、草稿不建、記 `write_intent_out_of_domain`；草稿值不出現在 `decision_snapshot`；W1b：問句（句末「？」「?」或末字「嗎」「呢」）在程式追問後不填進草稿、草稿保留、主模型照常回答；非問句的續答填入上回合追問的第一個文字欄位；草稿缺物件時當句唯一命中物件即補（不需上回合追問物件）；意圖呼叫回傳前綴殘缺時以 raw_decode 解出、全無法解析記 `write_intent_unparsed` 並視為 none；意圖呼叫逾時不影響主回合；W1b r2：模型自寫追問（`ask_target=description`）之後的下一句不被整句填入；`bill_due_extend` 缺 `days` 的程式追問（`ask_target=None`）之後 `asked` 仍讀得到並可接收；缺 [物件, 問題描述] 後輸入物件名 ⇒ `description` 不被填入、程式追問問題描述；缺 [物件, 期別, 延後天數] 後輸入腳本 D 第二句 ⇒ `period` 不是整句原文；同欄衝突時意圖呼叫值（通過值閘）優先於整句值；程式追問後送「冷氣不冷嗎」且意圖假回應帶 `repair_create`／`description` ⇒ 草稿不變、不觸發、answer 為主模型輸出；意圖假回應帶另一動作 ⇒ 草稿不被換；模型先呼叫 `confirm.request` 得缺欄（提前出口）⇒ 意圖 task 被取消或已計量、無殘留 pending task，`prompt_tokens`／`completion_tokens` 含已完成的意圖呼叫（以 `result.trace` 斷言）；W1b 安全：程式追問描述→「幫我延後帳單七天」（意圖＝`bill_due_extend`）⇒ `description` 不被填；換草稿清 `asked`；「程式追問→問句→陳述」第三句不被整句填入；追問描述→答「頂樓」且替身唯一命中 ⇒ 不寫 `estate_name`；追問後答「A棟呢」且替身唯一命中 ⇒ 草稿不變；`confirm_submit`／`select:` 回合不建立意圖 task；回應含多個內容不同的 action 物件 ⇒ none；文件回合不寫 `asked`；W1c：程式優先且程式路徑終結 ⇒ 主模型未被呼叫；意圖等待逾時 ⇒ 照常呼叫主模型、輸出後觸發點仍可用；程式優先遇非終結結果 ⇒ 主模型被呼叫一次並帶回填結果；使用者當句命中敏感樣式 ⇒ 不走程式優先；程式優先與輸出後觸發共用同一判斷函式；意圖延遲 >3 秒且 `asked=[description]`、非問句 ⇒ 主模型呼叫前無 `write_draft_answer_filled`、輸出後觸發點仍套用 1a；上回合 `asked=[description]`、意圖回 none、非問句 ⇒ 走程式優先且主模型未被呼叫；verifier 無 rules ⇒ 不走程式優先；安全審查 F1～F4 各一條：prospect 身分＋`write_intent` ⇒ 不寫 token、不建草稿；模型先用滿工具預算再作答 ⇒ 答案不變成 `budget_exhausted`；照片回合模型自己呼叫 `confirm.request` ⇒ 照片辨識描述不進草稿、不進下一回合 messages；草稿注入段 `citable=False`、id 在 `ReservedCallIds` 內、模型偽造同 id 記 `tool_call_id_collides_with_reserved` |

## 收窄（附理由）

- 只實測兩支寫入動作：物件建立、建合約、手動帳單在真 JGB 為 `WRITE_NOT_SUPPORTED_ACTIONS`（備案腳本 C 的 `contract_create` 只在評估容器的 mock 下能出卡），且缺欄與觸發走同一路徑；#3 以程式與測試證明 5 支共用。
- 不量正式機：部署由業主另裁。
