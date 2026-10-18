# D4 待裁表（2026-10-18）

> 計畫 `plan-20261018.md` §4 D4-1。來源規則：`HANDOFF-20261017.md` §1.3「待業主決定」每一列、`.claude/DECISIONS.md` 中來源＝代理且未標 ✅ 的爭議、本線發現，全部入表；已解決或已併入的寫一行處置附證據。建議依使用者效果，⛔ 依實作難易。
> 撈 DECISIONS 未裁爭議的指令：`python3 -c "import sys;[print(c[1],c[2][:80]) for l in open('.claude/DECISIONS.md') for c in [[x.strip() for x in l.split('|')]] if len(c)>5 and c[1].startswith(('DSP','D-')) and c[3].startswith('代理') and '✅' not in c[2]]"`

## A. 已解決或已併入（只列處置）

| 來源 | 事項 | 處置與證據 |
|---|---|---|
| HANDOFF §1.3 | 第二片計畫（補充鐵則＋截斷處置＋程式觸發 confirm.request） | 已拆開處理：程式觸發 confirm.request＝W1 已完成（commit `f117be32`、DSP-085）；補充鐵則＝R1 業主撤回（`plan-supplement-rule-r1-20261018.md` §8）；截斷處置＝W2 草稿（見 C-5） |

## B. HANDOFF §1.3 仍待裁

| # | 事項 | 選項 | 建議 | 證據 |
|---|---|---|---|---|
| B-1 | 視覺模型 IAM | 請 IAM 管理者在 `app-jgb-ai-cs-bedrock` 加開源視覺模型（Gemma 3 27B 為主、Ministral 3 14B 可選）／暫不處理 | 加開 Gemma 3 27B：gpt-oss 不收圖片，照片與收據在 Bedrock 方向下目前沒有模型可用 | HANDOFF §2.3；`~/jgb-archive/bedrock-eval-20261017/evidence/iam_scope.txt` |
| B-2 | 講法核可（與本線發現「講法全為 proposed、未進索引」合併） | (a) 1,740 條判定「掛對」改 `approved`、13 條不動；(b) 維持 proposed | (a)：講法目前 0 條進索引（`fine_index.INDEXED_PHRASING_STATUS = "approved"`；`canon/jgb.json` 1,753 條皆 proposed；R3 95 回合勝出鍵講法 0 次），使用者換說法問時只靠標題與內容比對；HANDOFF 記 40 題效果測試無差異，核可後須另量「換說法」題型 | HANDOFF §3.2；`grep -n INDEXED_PHRASING_STATUS rag-orchestrator/services/agent/canon/fine_index.py` |
| B-3 | 「合約到期前通知」 | 正本照 jgb2 程式現況寫「到期當天通知」並回報疑似 bug／先問 JGB | 先問 JGB：正本寫的是對客戶的承諾，現況疑似 bug 時照寫會把 bug 當規格 | HANDOFF §3.3 |
| B-4 | 工具參數塞身分鍵 | 接測清單改寫成「剝除」（照程式現況：`registry.call` 剝除並記 `IDENTITY_KEY:`）／改程式回 INVALID_INPUT | 改寫接測清單：程式註解明定不回 INVALID_INPUT 以免洩漏守門規則 | 接口 A §6；`grep -n "IDENTITY_KEY" rag-orchestrator/services/agent/tools/registry.py` |
| B-5 | 照片附進修繕單 | (a) 直接送 JGB 網址陣列；(b) JGB 上傳識別碼 | 需 JGB 端能力確認後再選；無足夠證據給建議 | `.kiro/specs/agentic-mcp-orchestration/jgb-api-spec-for-jgb-20261015.md` §4 #22（`grep -n "照片" .kiro/specs/agentic-mcp-orchestration/jgb2-api-requests.md`） |
| B-6 | 是否在 www 真建測試修繕單 | 重試一次／不重試 | 重試一次：400 已於 `19c38d14` 修正但未實證，正式寫入路徑未驗 | HANDOFF §3.1 A10 |
| B-7 | 9 條長期紅燈 | 另開單逐條修或退役／維持 | 另開單：每次全量測試都要扣這 9 條基線，會掩蓋新失敗 | `~/jgb-archive/bedrock-eval-20261017/w1/baseline_red.txt`（9 條） |

## C. 本線發現

| # | 事項 | 選項 | 建議 | 證據 |
|---|---|---|---|---|
| C-1 | 業者端敏感題無程式防線 | 加程式閘（敏感樣式命中即轉人）／維持只靠模型自報 | 加程式閘：R3 基準 gpt-oss 在 S2「合約範本的條款內容有哪些？」3 回合皆直接作答未轉人 | `~/jgb-archive/bedrock-eval-20261017/r3/baseline_S2_B.json` |
| C-2 | 物件記憶可能把短詞誤補成物件 | 收緊比對規則／維持並觀察 | 先量：W1 列為已知風險但無實測頻率 | `plan-write-flow-program-owned-20261017.md` §4 已知風險 |
| C-3 | 正本完全沒有相關章節時不說缺什麼 | 出口句引用使用者原話（需處理 R2 安全審查 F1、F2）／維持 | 另開片照設計方法先查業界 | `.kiro/specs/agentic-mcp-orchestration/acceptance-partial-answer-gap-r3-20261018.md` 收窄段（`grep -n "收窄" <該檔>`；業主「接受收窄，這片不處理」） |
| C-4 | 只改政策文擋不住推論有無 | 程式強制（如 Verifier 對「只有／沒有 X」句型檢查）／維持 | 另開片先查業界防推論做法：R3 #1 gpt-oss 仍 1 回合「只支援…沒有 LINE Pay」，verifier 抽驗又見「包含日文等語系」 | `plan-partial-answer-gap-r3-20261018.md` §9 |
| C-5 | W2 截斷處置、W3 查詢改由程式主導 | 依新設計方法補業界做法後送審／暫緩 | W2 先：gpt-oss 截斷 54 回合中 10 回合、8 回合最後轉人 | `plan-truncation-w2-20261017.md` §0 |
| C-6 | 正本定期維護 | 另開新計畫（先查業界維護客服知識庫的做法）／暫緩 | 業主 2026-10-18 已「同意」另開；待定時程 | `outline-curation/SKILL.md`（新建／重切用重流程）；細目 `sources` 指向程式檔、有 `reviewed_at` |
| C-7 | 判分員驗證（人工標註集） | 另案／不做 | 有懷疑判分員判錯的具體事件時再開 | 計畫 §8.5 |
| C-8 | 盲判探針批誘餌組成（R3 verifier P3） | — | 已由 D1 固定為 6 則（`eval-harness/decoys/probe.json`），僅記錄 | D1 verifier CONFIRMED |

## D. DECISIONS 未裁爭議（來源＝代理）

| # | ID | 爭議 | 現況初判 | 證據 |
|---|---|---|---|---|
| D-1 | DSP-081 | `outcome.expects` 值域：需求書四值封閉 vs 程式六值 | 待裁（需求正本過時或程式擴張） | `grep -n '^OUTCOME_EXPECTS' rag-orchestrator/services/agent/turn_context.py` |
| D-2 | DSP-082 | 修繕問題描述可否為空 | 待裁 | `grep -n 'REPAIR_CREATE_SPEC' rag-orchestrator/services/agent/tools/action.py` |
| D-3 | DSP-083 | Verifier 模式值域：DSP-040 vs 程式 enforce／grounding_observe／observe_only | 待裁（多半是 DSP-040 文字過時） | `grep -n 'observe_only' rag-orchestrator/services/agent/health.py` |
| D-4 | DSP-084 | 延期繳費期別是否必填 | 待裁 | `grep -n 'BILL_DUE_EXTEND_SPEC' rag-orchestrator/services/agent/tools/action.py` |
| D-5 | DSP-032 | DSP-033 列標題「提案 v6」vs commit 訊息稱 v7；另有被 `dispute.py` 誤併累加的計數（D3 已修工具、⛔ 改既有列） | 待裁：改標題或註明 | `grep -n '^| DSP-032' .claude/DECISIONS.md` |
| D-6 | DSP-010 | 合約範本數（幫助中心「五種」vs 其他來源） | 待裁 | DECISIONS DSP-010 列 |
| D-7 | DSP-005 | OCR 端點形狀：`POST /api/v1/ocr-mapping/{document_type}`（A，已實作）vs 掛 `/api/v1/message`（B） | **疑似已失效**：`/api/v1/message` 已於 2026-09-11 刪除，B 已不可能 | `ls rag-orchestrator/routers/ocr_mapping.py` |
| D-8 | DSP-003 | 回測 session_id 前綴（量測層級.md vs `run_batch.py`） | **疑似已失效**：repo 內找不到 `run_batch.py`（`find . -name run_batch.py` 無結果；正對照 `find . -name ocr_mapping.py` 有結果） | 同左 |
| D-9 | DSP-006 | 承租方姓名切姓／名 vs 整串交 LIFF | 待裁 | DECISIONS DSP-006 列 |
| D-10 | DSP-001 | `requires_instance_reference=true` 是否構成 instance 證據 | 待裁 | DECISIONS DSP-001 列 |
| D-11 | D-007 | IVFFlat 缺陷降級為潛在地雷 | 待裁是否結案（已有實測結論：生產查詢用不上向量索引） | DECISIONS D-007 列 |

## E. D5 盤點留下的外部事實（本 repo 無法核對）

| # | 事項 | 選項 | 建議 | 證據 |
|---|---|---|---|---|
| E-1 | `docs/api/jgb_external_api_spec.md` 是否與 jgb2 現行路由一致（文件列 14 支、client 實呼叫者部分未列） | 在 jgb2 checkout 對 `routes/api.php` 逐支核對後更正／維持 | 核對：client 實際呼叫 `/meters`、`/estates`、`POST /repairs`、`/tenants/registration-status`、`/repairs/categories`（`rag-orchestrator/services/jgb/transport.py` 的 ROUTES）而本 spec 未列 | `d5-docs-deepcheck.md` 仍判不出段 |
| E-2 | `docs/knowledge/jgb-product-facts.md` 的 jgb2 事實 | 在 jgb2 checkout 釘住 commit `b2ee2ac382ce` 逐條核對／維持 | 核對：正本知識依它撰寫，錯了會進客服回答 | 同上 |
