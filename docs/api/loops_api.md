# 知識完善迴圈 API（查詢面）

**最後對碼：2026-09-12**（逐支實測，見下方狀態欄）

## 概述

🔴 **執行面已於 2026-09 移除，本檔只剩查詢端點。**
`coordinator.execute_iteration` 每次迭代都會走 `backtest_client.execute_batch_backtest`，
它打的 `POST /api/v1/message` 隨舊 REST 對話鏈於 2026-09-11 刪除（DSP-046）——
迴圈自那之後一次也跑不完。查證：`head -20 rag-orchestrator/routers/loops.py`。

**想跑一輪檢索改善**：走 `.claude/skills/retrieval-improvement-loop/`（打 `/mcp` 的
`agent.turn`），⛔ 不再有 repo 內的 Python 回測框架。

prefix：`/api/v1/loops`（`app.py` 的 `include_router(loops.router, prefix="/api/v1/loops")`）

## 端點清單

| 路徑 | 方法 | 說明 | 2026-09-12 實測 |
|------|------|------|------|
| `/` | GET | 列出迴圈（`vendor_id`／`status` 篩選、`limit`／`offset` 分頁、更新時間倒序） | 200 |
| `/coverage-stats` | GET | 覆蓋率統計 | 200 |
| `/{loop_id}` | GET | 單一迴圈狀態（`LoopStatusResponse`） | 200 |
| `/{loop_id}/iterations` | GET | 該迴圈的迭代紀錄 | 200 |
| `/{loop_id}/iterations/{iteration}/backtest-results` | GET | 某次迭代的回測結果 | 200 |

⛔ **以下端點不存在**（實測：`/start` → 405、`/{id}/execute-iteration` → 404）：
`start`、`execute-iteration`、`validate`、`complete-batch`、`pause`、`resume`、
`cancel`、`start-next-batch`。前端若仍有這些按鈕，按下去會失敗。

## 資料模型

```python
class LoopStatusResponse(BaseModel):
    loop_id: int
    loop_name: str
    vendor_id: int
    status: str
    current_iteration: int
    current_pass_rate: Optional[float]
    target_pass_rate: float
    scenario_ids: List[int]
    total_scenarios: int
    progress: Dict          # {phase: str, percentage: float, message: str}
    created_at: str
    updated_at: str
    completed_at: Optional[str]
```

正本：`rag-orchestrator/routers/loops.py::LoopStatusResponse`。

## 現況資料量（2026-09-12 實查）

- `knowledge_completion_loops`：27 筆歷史迴圈
- `loop_generated_knowledge`：915 筆，**全部已審**（469 approved／446 rejected），0 筆待審

## 審核端點（另一支 router）

審核走 `routers/loop_knowledge.py`，同 prefix：

| 路徑 | 方法 | 說明 |
|------|------|------|
| `/loop-knowledge/pending` | GET | 待審知識（目前 0 筆） |
| `/loop-knowledge/{knowledge_id}/review` | POST | 單筆審核 |
| `/loop-knowledge/batch-review` | POST | 批次審核 |

詳見 [`loop_knowledge_api.md`](./loop_knowledge_api.md)。

---

⛔ 本檔 2026-09-12 由 995 行刪至此——被刪的是 8 支不存在的 POST 端點的請求／回應格式、
四個使用場景範例與前端輪詢建議。要看舊版：`git show HEAD:docs/api/loops_api.md`。
