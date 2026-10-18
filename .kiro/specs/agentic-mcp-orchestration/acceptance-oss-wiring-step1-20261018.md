# 驗收清單：主線第 1 步「正式接線（本地替換 gpt-oss）」（2026-10-18 第 4 稿：#8 依 security-reviewer 改寫；#4、#5、#6、#7、#9 依 plan-verifier 第 1、2 輪修正；2026-10-18 業主核可，已凍結）

計畫：`plan-oss-wiring-step1-20261018.md`
業主原話：「我要調整成 Amazon Bedrock 的使用方式」「我有 ai-cs-bedrock-api-key.txt 所以是替換 並不是評估」「先暫定 gpt-oss 去處理問題」「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應」「正式接線 是本地都處理好 才線上換吧」；本次「金鑰處置先過 security-reviewer」「任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock」。

觀察點：本機常駐服務 `aichatbot-rag-orchestrator`（port 8100，業主以 `docker-compose.prod.yml`＋`docker-compose.bedrock-local.yml` 重建），經 eval-harness `--target resident` 打真實 `/mcp` `agent.turn`，**不掛評估 shim**；資料庫 `aichatbot_admin`。證據放 `~/jgb-archive/oss-wiring-20261018/`（題目與回答原文不進 git）。

| # | 對應業主字句 | 宣稱 | 觀察點 | 證據類型 | 通過條件 |
|---|---|---|---|---|---|
| 0 | 「任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock」 | 實打前常駐服務是 mock | `docker exec -w /app aichatbot-rag-orchestrator python -c "from services.agent.health import _use_mock_jgb_api; print(_use_mock_jgb_api())"`；harness `--target resident` 開頭自檢 | 指令輸出 | 回 `True`；非 `True` 時 harness 非 0 退出（另以假設定測一次證明會擋） |
| 1 | 「我要調整成 Amazon Bedrock 的使用方式」「替換 並不是評估」 | 常駐服務的對話真的走 Bedrock gpt-oss、未經 shim | #2 全部回合的計量紀錄（`usage_events` 等計量表的模型欄）；容器掛載與啟動訊息 | DB 查詢輸出、`docker inspect` 掛載清單、啟動日誌一行 | 所有對話模型呼叫的模型名＝`openai.gpt-oss-120b-1:0`；容器無 `/shim` 掛載；啟動訊息顯示對話端點＝Bedrock |
| 2 | 「確保 回應品質都能符合 有效的回應」（本步範圍：接線不外洩推理） | 推理原文不出現在答案與留存紀錄 | v2 知識題 30 題 ×1、W1 腳本 R、D 各 ×1、敏感題 S1 ×1 的 answer 全文；這些回合在 `aichatbot_admin` 的對話紀錄與 trace | harness 存檔＋DB 查詢（只印計數） | `<reasoning`、`</reasoning>` 命中 0；正對照：同一查法對答案中已知存在的字（如「轉接」或各回合 answer 首字）命中 >0 |
| 3 | 同上（本步範圍：接線不讓答不出變多） | 最終輸出能被解析，不因推理段而固定轉人 | #2 的 30 題知識題 | `decision_snapshot`／trace 的 `handoff_reason` 與 violations | `budget_exhausted` ≤ 2／30（依據：2026-10-17 實測約 5% 呼叫灌空白至上限，截斷屬第 3 步）；`llm_output_reasoning_stripped` 命中 >0（證明清理器真的在跑） |
| 4 | 「替換 並不是評估」（HANDOFF §3：照搬 shim 並以存下的模型原文做等價測試） | 新清理器不比評估 shim 差 | 已存 Bedrock 原始輸出（eval-harness `runs/*/shim_raw.jsonl`、bedrock-eval-20261017）全部 AgentOutput 最終輸出 | repo 外等價測試輸出 | 比較單位＝每則原文經「shim 處理→`json.loads`→`AgentOutput.model_validate`」與「新清理器（開關開啟）→解析→`model_validate`」各自的結果：舊路徑通過 `model_validate` 者，新路徑 100% 通過且 `model_dump()` 相等；舊路徑 `json.loads` 成功但 `model_validate` 失敗者，兩邊皆失敗；舊路徑失敗者逐筆列出新路徑結果（可多救回，不可少）。通過數即終點指標（預期 ≥12／15） |
| 5 | 「正式接線 是本地都處理好 才線上換吧」 | 未設兩個新變數時行為逐位不變（正式機現況），含「解析失敗但可擷取」「可解析且含字面 `<reasoning>`」兩種輸入 | 黃金測試、單元測試、全量 | `scripts/run-tests.sh` 輸出、`git diff tests/fixtures/agent/pipeline_golden.json` | 既有 28 情境 fixture 逐位不變（diff 只見新增 1 鍵）；開關關閉的兩種輸入測試證明 messages、輸出、violations 與現行相同；新測試全過；全量失敗 ⊆ 第 0 步 HEAD 基線 |
| 6 | （HANDOFF §1.2：照片／文件等待期間維持現行 OpenAI 視覺模型） | 照片與文件仍走 OpenAI，只有對話走 Bedrock | 重建後的常駐服務容器內：`docker exec -w /app aichatbot-rag-orchestrator python -c …` 建 `ImageRecognitionService`、`DocumentExtractionService` 的 client 與 `build_agent_provider_from_env()`，只印各自 `base_url` 的主機名；環境變數名稱清單 | 指令輸出（只有主機名與變數名稱） | 照片、文件 client 主機＝`api.openai.com`；對話 provider 主機＝`bedrock-runtime.ap-northeast-1.amazonaws.com`；環境變數名稱無 `OPENAI_BASE_URL`；正對照：同一指令印出的對話 provider 主機確為 Bedrock（證明指令真的讀到新設定） |
| 7 | 「我要調整成 Amazon Bedrock 的使用方式」（看得到花多少） | gpt-oss 呼叫記得到用量與成本 | #2 回合的 `usage_events.model_breakdown`；`usage_metering._compute_cost` 單元測試 | DB 查詢、單元測試輸出 | `model_breakdown` 含 `openai.gpt-oss-120b-1:0` 鍵且 token 非 0；單元測試證明該鍵依 Q6 單價算得成本；`est_cost_usd` 非空——若為空，須列出 `model_breakdown` 中缺價的其他模型鍵（不是 gpt-oss 缺價即算過）。**Q6 查不到官方單價 ⇒ 本項收窄為「token 有記、成本留空」**並回報 |
| 8 | 「金鑰處置先過 security-reviewer」 | Bedrock 金鑰不進環境變數、日誌、計量、答案、探測與量測紀錄；OpenAI 金鑰不被導向 Bedrock | 全部以 `grep -c -F -f <金鑰檔>` 只印計數（金鑰只當樣式檔，⛔ 進 argv、⛔ 印出），比對：完整 `docker inspect aichatbot-rag-orchestrator` 輸出、`docker logs`、`aichatbot_admin` 以 `pg_dump` 串流（⛔ 落地成檔）、`~/jgb-archive/oss-wiring-20261018/` 全目錄（`grep -r`）、`AGENT_ATTEMPT_LOG_PATH` 有設時該檔；環境變數**名稱**清單（`docker inspect --format` 只印 `=` 前） | 指令輸出（只有計數與名稱） | **前置（不過即停）**：金鑰檔 `test -s` 成立、`grep -c '' <檔>`＝1、`grep -c $'\r' <檔>`＝0；**同檔正對照**：`{ printf x; cat <檔>; printf 'y\n'; } \| grep -c -F -f <檔>`＝1。通過：上列各來源命中皆 0；環境變數名稱無 `OPENAI_BASE_URL`、`AGENT_LLM_API_KEY`、`AWS_BEARER_TOKEN_BEDROCK`（只有 `AGENT_LLM_API_KEY_FILE`）；`docker exec … stat -c '%a %U' /run/secrets/agent_llm_api_key` 只印權限與擁有者並記錄 |
| 9 | （收尾稽核） | 健康與不變量 | `curl localhost:8100/api/v1/health`；`curl localhost:8100/api/v1/system/pipeline-health`；`make audit` | 指令輸出 | `/api/v1/health` 200；`pipeline-health` 回應 `components` 中 `name`＝`Agent LLM Endpoint` 那項的 `status`＝`healthy`；`make audit` OVERALL: PASS（容器與工作樹一致後） |
| 10 | — | 獨立驗證 | fresh `verifier`（業主原話＋本清單＋計畫宣稱） | 驗證報告 | CONFIRMED |

收窄（附理由）：
- **「回應品質都能符合有效的回應」本步只驗「接線不讓品質變差」（#2～#4）**：品質定義與門檻依 DSP-087 屬第 2 步量測、第 3 步修（HANDOFF §1.4）；本步不跑盲判、不設正確率門檻。
- **截斷不處置**：#3 容許 ≤2／30 固定轉人，截斷屬第 3 步。
- **正式機不切換、不改 `docker-compose.prod.yml`**：業主「本地都處理好 才線上換」。
- **#7 視 Q6 而定**：官方單價查不到時不填價（⛔ 從記憶或文件補值）。
- **#6 不做照片端到端回合**：`/mcp` 照片網址須在 `IMAGE_URL_ALLOWLIST`（預設只有 JGB 主機 `relay.jgbsmart.com`）且帶 `exp`，mock 管不到、本機圖送不進去；本步只證明組態未把照片導向 Bedrock，端到端照片回合留第 2 步以 S3-live 程式內驅動做（plan-verifier 第 2 輪 #1）。
