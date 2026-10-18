# 盤查報告：本地替換 gpt-oss 前的現況、衝突與任務安排（2026-10-18）

> 業主原話：「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應 並把某些部分邏輯參考業界做法去調整」「前面做了什麼 跟接下來做有什麼衝突 任務要怎麼安排 你不用盤查嗎」。
> 方法：`/canon-audit agentic-mcp` 應讀 22 份整檔讀完（`audit.py status` 22/22）；3 位唯讀 scout 分讀核心程式、門面與架構文件、決策與測試；主會話補查 commit、`llm_provider.py`、`usage_metering.py`、`app.py`。行號只作定位，以下引用皆為可 grep 的符號。

## A. 已做過的（10-15～10-18，皆已 commit、未 push）

| commit | 內容 | 動到的正式程式 | 前提／備註 |
|---|---|---|---|
| `1bbab7a7`～`19c38d14`（10-15～16） | 站內幫手 10 項上線與上線後修正（A1～A3、A9、修繕細項） | runtime、mcp_facade、confirm、action、document_extract、image_recognition 等 | 已上正式機（gpt-6-luna） |
| `81f42ea3` | 第一片：每次模型呼叫輸出上限 2000＋截斷旗標＋`ask_target` 值域說明 | runtime.py、docker-compose.prod.yml | #1 截斷、#3 `ask_target` 偶漏未過 |
| `f117be32` | W1 寫入流程由程式掌握 | runtime.py（+908）、write_forms.py（新）、agent_session、confirm_card、output_schema、tools/confirm、turn_context | gpt-oss 3/3 是經評估 shim 測得 |
| `a6df614c` | R3 說缺什麼（只改政策文） | agent_rules.py | 同上，經 shim |
| `ff0fb6f4`、`f1dc4c5b`、`28409785` | 開發阻礙 D1～D5（評估骨架、接點清單、工具坑、待裁表、文件整理） | 無正式程式 | eval-harness 在 repo 外 |

## B. 換 gpt-oss 的實際接點（程式現況）

1. **連線只靠設定，不用改程式**：`app.py` 以 `services.llm_provider.get_llm_provider()` 建 provider 交 `bootstrap.build_runtime`；`OpenAIProvider` 沒有 base_url 參數，但 OpenAI SDK 會讀環境變數 `OPENAI_BASE_URL`（評估容器即以此接上 Bedrock）；模型 `AGENT_MODEL` → `OPENAI_MODEL` → `gpt-4o-mini`；推理強度 `AGENT_REASONING_EFFORT` 以 `extra_body` 送，`REASONING_EFFORT_VALUES` 含 `low`。
2. **主迴圈解析會壞**：模型輸出唯一來源 `AgentRuntime._next_model_message`；唯一解析點 `_run_model_loop` 的 `json.loads(content)` → `AgentOutput.model_validate`。content 夾 `<reasoning>`、JSON 前後有雜字、或灌滿空白，都會失敗 → 走 SCHEMA 改寫（`acc.counters.rewrites`），改寫用完 → `build_fixed("budget_exhausted")` 固定轉人句；而且**原始 content（含 reasoning）會原樣 append 進 messages**。主迴圈 7 檔內 `<reasoning`、`raw_decode` 皆 0 命中（正對照：`json.loads(content)`、`finish_reason` 有命中）。寫入意圖路徑另有 `write_forms.parse_write_intent_content` 已能處理 reasoning。
   ⇒ 修正落點：`_next_model_message` 回傳前清理一次，並確保之後 append 進 messages 的是清理後內容。
3. **截斷沒有處置**：`finish_reason == "length"` 只記 `LLM_OUTPUT_TRUNCATED`，沒有分支讀它；空白內容照樣進 messages（下一次 prompt 變大）；模型呼叫沒有 `timeout=`，期限只在迴圈頂端檢查。
4. **業者端敏感題沒有獨立於模型自報的程式防線**：主要靠模型自報 `fact_class`；答案端 `sensitive_patterns` 只在受眾列於規則檔 `sensitive_patterns_audiences` 時才跑（pm 是否在內未查）；問句端 `question_sensitive` 只能把模型自報的敏感降級成固定句，不能把非敏感升級成轉人。
5. **照片與文件是另一條路**：`mcp_facade` 的 `_image_recognize_batch`（`IMAGE_RECOGNITION_MODEL`）、`_document_extract_pages`（`DOCUMENT_EXTRACTION_MODEL`）各自呼叫 vision 模型；參數分支 `REASONING_EFFORT_BY_PREFIX`／`_completion_params` 只認 gpt-5／gpt-6 前綴。gpt-oss 不收圖片 ⇒ 照片與文件需另一個視覺模型（IAM 只開 gpt-oss），或過渡期維持現行 OpenAI 視覺模型。
6. **成本記不到**：`usage_metering.DEFAULT_PRICING` 只有 gpt-4o-mini、gpt-4o、gpt-3.5-turbo、gpt-4.1(-mini)、gpt-5-mini；沒有 gpt-oss，也沒有 gpt-6-luna；文件擷取缺價目時退回平頭 5.0 USD／百萬 token。
7. **本機兩套服務**：評估容器 `bedrock-eval-svc`（dev compose、mock JGB、`aichatbot_test`）有接 gpt-oss，但靠評估 shim；常駐服務 `aichatbot-rag-orchestrator`（prod compose、`aichatbot_admin`）未接（最後一筆對話紀錄 2026-09-10，`gpt-5.6-luna`）。eval-harness 目前只打評估容器（port 18101）。

## C. 與既有做法的衝突與依賴

| # | 衝突／依賴 | 證據 | 影響 |
|---|---|---|---|
| C1 | W1 的「輸出後觸發」只有主輸出 JSON 解析成功才會到；不清理 reasoning 時 gpt-oss 常解析失敗 ⇒ 寫入的這條補救路徑失效（程式優先路徑走意圖呼叫，不受影響） | `_write_draft_after_output` 只在 `model_validate` 成功後到達 | W1 的 3/3 依賴 shim；接線後須重驗 |
| C2 | 第一片的輸出上限與截斷：截斷後空白進 messages，改寫時 prompt 變大、更慢 | B3 | W2 草稿的前提要依此重寫 |
| C3 | DSP-080 的切換條件寫「第二片驗收通過＋業主核可部署」，但「第二片」已拆成 W1（完成）、R1（撤回）、W2（草稿） | DECISIONS DSP-080 列 | 切換條件文字過時，需業主改定 |
| C4 | Verifier 模式值域文件與程式不一致（DSP-083 未裁）；正式為 `grounding_observe`，引用類只記錄不擋（DSP-040），依據是 gpt-5-mini 樣本 | DSP-040、DSP-083 | gpt-oss 的失敗型態不同，觀察模式下引用問題不會被擋 |
| C5 | 黃金測試 `test_pipeline_golden_req.py` 逐位鎖住回應形狀、handoff 字串等（用 FakeProvider）；清理邏輯不可改變這些形狀 | 該測試 `SCENARIOS` 28 情境 | 接線片的回歸網 |
| C6 | `requirements.md` 是 2026-09-04 快照：模型 gpt-4o-mini、SSE 串流、`expects` 四值，與程式不符 | requirements.md R1.4、R3.7 vs `mcp_facade` | 不能拿它當品質依據，需另定 |
| C7 | eval-harness 只打評估容器；要驗常駐服務需改指向 8100 並處理身分金鑰 | `harness/runner.py` 的 `M.URL` | 驗收工具要小改 |

## D.「有效回答」：專案裡找得到的候選（皆非業主定義，且互相不一致）

1. requirements.md D2：「敏感五類 0 漏；功能邊界漏 ≤ 現行第五輪（1/15）；邊界題不硬答 ≥ 90%；p95 延遲 ≤ 12 秒；答到率 ≥ 現行同尺（41%）＋15 點」（未定義「答到」的分子分母與判分人）。
2. DSP-036：「翻轉門不再作收案門」——56% 改記為已知水準。
3. demo 帳本 §1c R5：「W6 通過標準待裁（建議：可答題轉人率 ≤20%、資料事實答錯 0、明確 ref 反問率 ≤10%、p50 ≤20 s）」——始終待裁。
4. demo 帳本 §1f：「有沒有答到使用者的問題」五類：答到／部分／正確處理未答／答錯／沒處理。
5. 本線盲判標籤：正確／部分／無據／矛盾／沒作答。

## E. 任務安排（待業主確認）

**先要業主決定的三件事**：
1. 「有效回答」的定義與門檻（從 D 的候選挑、或先查業界定義給業主挑）。
2. 照片與文件：過渡期維持現行 OpenAI 視覺模型，或等 IAM 開 Bedrock 視覺模型（B5）。
3. 其他呼叫點（`knowledge_generator.py`、`pipeline_health_service.py`、`tools/agent_eval.py`）要不要一起換。

**依賴順序**：
1. 正式接線（本地替換）：`_next_model_message` 清理 reasoning 與 JSON 前後雜字、messages 存清理後內容；價目表補 gpt-oss；常駐服務設定改 Bedrock（金鑰放法需安全審查）；黃金測試與單元測試不退步；eval-harness 改能打常駐服務。
2. 依決定 1 寫驗收清單，在常駐服務上（不加 shim）跑全量基準，含 W1、R3 重驗（C1）。
3. 只修沒過的項目，每項先查業界做法：已知候選為截斷處置（B3）、業者端敏感題防線（B4）、推論有無、`ask_target` 漏填。
4. 全部過 ⇒ 業主改定 DSP-080 切換條件（C3）並切換正式機。

**不做（本主線外）**：講法核可（待裁表 B-2）、正本定期維護、W3——屬對話品質支線，業主另排。
