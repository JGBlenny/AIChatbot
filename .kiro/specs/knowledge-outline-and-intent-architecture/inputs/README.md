# inputs/ 索引（2026-09-10 文件整理）

> 每檔一行，標分類：**Plan**／**審核單**／**帳本**／**契約**／**探針**。
> 探針類（一次性報告／中間量測）優先歸檔到 `archive/`；但凡在 `tasks.md`／`HANDOFF-*.md`／
> `.claude/DECISIONS.md`／`.claude/MAP.md`／使用中的 `eval/*.json`／workflow 程式碼中被引用的，
> **一律不動**（帳本引用不搬）——本輪逐檔 `grep -rn` 過，只有零引用的兩檔實際搬移，見下方「本輪已歸檔」。

## Plan

| 檔案 | 說明 |
|---|---|
| plan-2.6-coverage-map-20260907.md | 2.6 覆蓋地圖階段 Plan |
| plan-3.1-review-state-20260907.md | 3.1 審核狀態機 Plan |
| plan-3.2-canon-assembler-20260907.md | 3.2 正本組裝器 Plan |
| plan-3.3-fine-index-selector-20260907.md | 3.3 細目選取器 Plan |
| plan-3.4-index-eval-20260907.md | 3.4 索引評測 Plan |
| plan-3.7-fine-index-content-keys-20260907.md | 3.7 細目內容鍵 Plan |
| plan-4.4a-outline-probe-definition-20260907.md | 4.4a 大綱探針定義 Plan |
| plan-5.1-policy-definitions-20260907.md | 5.1 政策定義 Plan（第 3 稿 READY） |
| plan-agent-write-tools-demo-20260908.md | agent 寫入工具示範 Plan |
| plan-clarify-on-reject-20260907.md | reject 時澄清流程 Plan |
| plan-cut1-verifier-ruler-measure-20260907.md | cut1 verifier 量尺量測 Plan |
| plan-document-summary-demo-20260909.md | 文件摘要示範 Plan |
| plan-m-d-runtime-wiring-20260907.md | M-D runtime 接線 Plan |
| plan-mcp-demo-key-and-flag-20260907.md | MCP demo key／旗標 Plan |
| plan-structural-refactor-20260910.md | 結構重構 Plan |
| plan-walkthrough-fixes-20260909.md | walkthrough 修正 Plan（首批） |
| plan-walkthrough-fixes-batch2-20260909.md | walkthrough 修正 Plan（第 2 批） |
| plan-walkthrough-fixes-batch3-20260909.md | walkthrough 修正 Plan（第 3 批） |
| plan-walkthrough-fixes-batch4-20260909.md | walkthrough 修正 Plan（第 4 批） |
| plan-walkthrough-fixes-batch6-20260910.md | walkthrough 修正 Plan（第 6 批） |

## 審核單

| 檔案 | 說明 |
|---|---|
| review-sheet-property_manager-20260907.md | property_manager 大綱審核單（初版） |
| review-sheet-property_manager-delta-20260908.md | 同審核單差異批（delta） |
| review-sheet-property_manager-delta2-20260908.md | 同審核單差異批（delta2） |
| review-sheet-property_manager-delta3-20260908.md | 同審核單差異批（delta3） |
| review-sheet-property_manager-delta5-20260909.md | 同審核單差異批（delta5） |
| review-sheet-property_manager-delta6-20260909.md | 同審核單差異批（delta6） |
| review-sheet-property_manager-delta7-20260909.md | 同審核單差異批（delta7） |
| security-review-mcp-demo-key-20260907.md | MCP demo key 安全審核 |
| verifier-1.2-20260906.md | 1.2 階段 verifier 審核紀錄 |

## 帳本

| 檔案 | 說明 |
|---|---|
| demo-ledger-line-oa-20260907.md | LINE OA demo 帳本 |
| source-audit-20260907.json | 來源稽核帳本 |
| source-audit-v3-20260907.json | 來源稽核帳本 v3 |
| source-audit-worklist-20260907.json | 來源稽核待辦清單 |
| source-audit-worklist-v3-20260907.json | 來源稽核待辦清單 v3 |

## 契約

| 檔案 | 說明 |
|---|---|
| mcp-client-contract-line-bot-20260907.md | LINE bot MCP client 契約 |
| line-bot-integration-sheet-20260908.md | LINE bot 整合規格單 |
| line-bot-scenarios-delta-20260908.md | LINE bot 情境差異批 |
| line-bot-worklist-demo-20260908.md | LINE bot demo 待辦清單 |
| jgb-api-needs-line-oa-demo-20260907.md | LINE OA demo 所需 JGB API 清單 |
| demo-data-sheet-line-oa-20260908.md | LINE OA demo 資料規格單 |
| outline-probe-selection-rule.json | 大綱探針取樣規則（仍被 tasks.md／eval 引用，非一次性） |
| phrasing-selection-rule-20260906.json | 講法取樣規則 |
| id-map-20260907.json | ID 對照表 |
| index-eval-20260907.json | 索引評測資料 |
| line-phrasings-20260907.json | LINE 講法資料 |
| koyu-article-map.json | koyu 文章對照表 |
| outline-paragraphs-proxy-20260906.json | 大綱段落代理資料 |
| prospect-kb-rows-20260906.json | prospect KB 列資料 |
| kb3645-presales-dialogue-rules-20260906.md | kb3645 售前對話規則草稿 |
| dsp-draft-agent-turn-stage-pm-20260907.md | agent turn stage（property_manager）DSP 草稿 |
| identity-reask-patterns-draft-20260907.md | 身分重問模式草稿 |
| liff-28-scenarios-gap-map-20260908.md | LIFF 28 情境缺口對照 |
| prospect.draft.review-20260907.md | prospect 正本草稿審閱 |
| prospect.draft.v3-20260907.md | prospect 正本草稿 v3 |

## 探針（一次性報告／中間量測，未歸檔者因仍被帳本引用）

| 檔案 | 說明 | 引用方 |
|---|---|---|
| coverage-map-20260907.json | 覆蓋地圖量測輸出 | plan-2.6、m-b-reweigh、`.claude/MAP.md` |
| coverage-map-v3-20260907.json | 覆蓋地圖量測輸出 v3 | m-b-reweigh |
| cut1-verifier-ruler-measure-20260907.md | cut1 verifier 量尺量測 | HANDOFF-20260907、tasks.md |
| cut1b-semantic-ruler-measure-20260907.md | cut1b 語意量尺量測 | HANDOFF-20260907、tasks.md |
| hook-probe-20260906.md | hook 探針 | tasks.md、m-a-trial |
| m-a-dryrun-20260906.md | M-a 步驟乾跑 | `.claude/workflows/outline-curation.js`（程式引用） |
| m-a-trial-20260906.md | M-a 步驟試跑 | design.md、tasks.md |
| m-b-answerability-20260907.md | M-b 可答性量測 | tasks.md、plan-2.6-coverage-map |
| m-b-reweigh-20260907.md | M-b 重權量測 | tasks.md |
| m-c-index-eval-20260907.md | M-c 索引評測 | plan-3.4、design.md、tasks.md |
| object-under-test.md | 受測物清單（核可欄） | tasks.md、design.md，及下列 probe 系列 |
| object-under-test-outline-probe-20260907.md | 受測物清單（大綱探針版） | tasks.md、plan-4.4a、probe-report-20260907 |
| object-under-test-outline-probe-51-20260907.md | 受測物清單（探針 51） | probe-report-51 |
| object-under-test-outline-probe-52-20260907.md | 受測物清單（探針 52） | probe-report-52 |
| object-under-test-outline-probe-53-20260907.md | 受測物清單（探針 53） | probe-report-53 |
| object-under-test-outline-probe-55-20260907.md | 受測物清單（探針 55） | tasks.md、probe-report-55 |
| outline-probe-scenario-gold-20260907.json | 大綱探針 gold 情境 | outline-probe-selection-rule、`.kiro/specs/agentic-mcp-orchestration/eval/` |
| outline-probe-sub-map-20260907.json | 大綱探針子題對照 | outline-probe-selection-rule、`.kiro/specs/agentic-mcp-orchestration/eval/` |
| probe-h7-three-arm-20260907.json | H7 三臂探針數據 | probe-report-20260907 |
| probe-report-20260907.md | 4.4b 探針報告 | tasks.md、object-under-test-outline-probe-51、plan-5.1、probe-report-51 |
| probe-report-51-20260907.md | 探針報告 51 | tasks.md、probe-report-52、plan-5.1、object-under-test-outline-probe-52 |
| probe-report-52-20260907.md | 探針報告 52 | tasks.md、probe-report-53、object-under-test-outline-probe-53 |
| probe-report-53-20260907.md | 探針報告 53 | HANDOFF-20260907、tasks.md |
| probe-report-55-20260907.md | 探針報告 55 | HANDOFF-20260907、tasks.md、`.claude/DECISIONS.md` |

## 本輪已歸檔（`archive/`，零活引用，已實查 `grep -rn`）

| 檔案 | 原因 |
|---|---|
| archive/m-b-structure-20260906.md | 全 repo 零引用（結構提議首跑紀錄，已被後續 delta 取代） |
| archive/outline-probe-gold-review-20260907.md | 全 repo 零引用（gold 表草稿，已被凍結版 outline-probe-scenario-gold-20260907.json 取代） |
