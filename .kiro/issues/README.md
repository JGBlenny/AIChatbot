# Issues 追蹤目錄

> 存放非 feature 性質的 bug / 調查記錄。正式 feature 開發請走 `.kiro/specs/` 流程。

## 結構

每個 issue 一個 markdown 檔，檔名 kebab-case 描述症狀。內含：
- **症狀**：觀察到的行為
- **程式碼位置**：可能相關的程式位置
- **疑似根因**：待驗證假設
- **重現步驟**：穩定重現方法
- **調查建議**：下一步 action items
- **暫行解法**：若有 workaround
- **關聯**：相關 specs 或其他 issues

## 當前追蹤中

| Issue | 優先級 | 狀態 |
|-------|-------|------|
| [sop-candidates-intermittent-empty.md](sop-candidates-intermittent-empty.md) | 低 | reranker hotfix 後應已消失，待重新觀察確認 |

## 處理完成

| Issue | 狀態 |
|-------|------|
| [reranker-returning-zero.md](reranker-returning-zero.md) | Hotfix 上線並驗證（2026-04-17）：timeout 15→60s + 候選數截斷到 20 |

## 處理完成

（目前無）
