# 知識完善迴圈：現在還剩什麼

**最後對碼：2026-09-12**

## 一句話

**迴圈的執行面已經拆掉，只剩查詢與審核。** 後台看得到 27 筆歷史迴圈與
915 筆已審完的生成知識，但**沒有任何端點可以啟動新迴圈或執行迭代**。

## 為什麼

`coordinator.execute_iteration` 每次迭代都會走 `backtest_client.execute_batch_backtest`，
它打的是 `POST /api/v1/message`——那條端點隨舊 REST 對話鏈於 2026-09-11 刪除（DSP-046）。
迴圈自那之後一次也跑不完，執行機制已於 2026-09 移除。
`services/knowledge_completion_loop/` 的程式現在只剩 `embedding_client.py`（目錄另有 `__init__.py`、`create_missing_indexes.sql`）。

查證：`head -20 rag-orchestrator/routers/loops.py`；
`ls rag-orchestrator/services/knowledge_completion_loop/`。

## 現在還能做什麼

| 動作 | 端點 | 狀態 |
|---|---|---|
| 看歷史迴圈清單 | `GET /api/v1/loops/` | ✅ |
| 看某個迴圈的迭代紀錄 | `GET /api/v1/loops/{loop_id}/iterations` | ✅ |
| 看某次迭代的回測結果 | `GET /api/v1/loops/{loop_id}/iterations/{iteration}/backtest-results` | ✅ |
| 看覆蓋率統計 | `GET /api/v1/loops/coverage-stats` | ✅ |
| 看待審知識 | `GET /api/v1/loops/loop-knowledge/pending` | ✅ 端點在，但**目前 0 筆待審**（915 筆全已審：469 核准／446 退回） |
| 審核／批次審核 | `POST /api/v1/loops/loop-knowledge/{id}/review`、`/batch-review` | ✅ 端點在 |
| **啟動新迴圈／執行迭代／驗證／暫停／恢復／取消** | — | ⛔ **不存在**（`grep -n "@router.post" rag-orchestrator/routers/loops.py` 零命中） |

## 想跑一輪檢索改善怎麼辦

走 `.claude/skills/retrieval-improvement-loop/`——它打 `/mcp` 的 `agent.turn`，
不經過這套 Python 回測框架。流程與五道閘門見該 skill 的 `SKILL.md`。

---

⛔ 原本的三份操作手冊（`quick_start.md`／`knowledge_loop_workflow.md`／
`knowledge_completion_loop.md`，共 1,698 行）已於 2026-09-12 歸檔至
`docs/archive/2026-09/`：它們逐步教人點「啟動新迴圈」「執行迭代」，
而那些按鈕背後的端點已經不存在。
