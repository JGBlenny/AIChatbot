# Research：quota-management

> 產出：2026-07-06　方法：codebase 實查（usage-metering 剛收案，整合點皆為熱知識）

## 摘要

輕量 discovery（Extension，疊在 usage-metering 上）。四個開放問題全裁決；兩個實查發現直接約束設計：攔截回應形狀與 status 欄寬。

## Research Log

### 1. 攔截回應的形狀約束
- jgb2 前台 `useChat.ts` 只讀 `data.answer`（＋選配 quick_replies/progress）；`/message` 的 response_model=`VendorChatResponse`（chat.py:3721）必填 answer/mode/timestamp/source_count。
- **定案**：middleware 短路回 `JSONResponse`，帶 answer/mode/session_id/timestamp/source_count=0/action_type='quota_blocked'——前端零改動可渲染。

### 2. status 欄寬（攔截事件標記）
- `usage_events.status VARCHAR(10)`（實查）——`quota_blocked`（13 字）放不下。
- **定案**：status＝**`blocked`**（7 字，值域 success|error|blocked）；報表 errors 之外另列 blocked 計數。

### 3. 警示提示的附加點
- 回答出口多（5+ returns）——再走逐出口插必漏（usage-metering 已證）。
- **定案**：**middleware 出場改寫回應 body**（非串流 JSON：parse→answer 尾端 append→re-serialize，Content-Length 同步更新）；串流不附警示（生產非串流，documented 限制）。chat.py 零侵入。

### 4. 開放問題裁決

| # | 問題 | 裁決 |
|---|---|---|
| 1 | 閾值段數 | 單段可設（`warn_threshold_pct` 1–99，預設 80）；多段留欄位擴充不做 |
| 2 | 攔截 status | `blocked`（見 §2）；攔截事件 llm_calls=0、不計入額度（count 時排除 status='blocked'） |
| 3 | 提示頻率 | ~~每則都附~~ → **改判（2026-07-06）：警示不進對話、改寄信**（每月首次跨閾值一次，QUOTA_WARN_IN_CHAT 旗標保留對話附註能力預設關） |
| 4 | UI 位置 | 額度進度條＋設定同放「使用量統計」頁（新增「額度管理」卡；不另建頁） |

### 5. 檢查快取與月界
- 本月 count 走 `idx_usage_date_vendor`（Index Only Scan 實測）；程序內 dict 快取 TTL 60 秒（單 worker 架構足夠；多 worker 時每 worker 各自快取、誤差受 R2.4 寬鬆原則涵蓋）。
- 月界沿 usage-metering `date_tpe`（Asia/Taipei）——count 條件 `date_tpe >= 本月一日`，額度自然月重置**零程式**（查詢窗口自動滾動，R1.5 免排程）。
- fail-open：quota 查詢任何例外 → 放行＋log（R5.2）。

## 風險

1. **快取邊界誤差**：60 秒窗內可能多放行數則——R2.4 明訂寬鬆不誤殺，可接受。
2. **body 改寫與 Content-Length**：改寫後必須重算 header，漏了會截斷回應——unit 必測。
3. **b2b 判定口徑**：警示/攔截文案分流沿 usage_metering 的 user_type（property_manager→b2b 文案；tenant/prospect/unknown→中性文案）——與計量同源，不另判。
