---
version: "0.1.0"
status: draft_pending_owner_approval
---

# 可答性判準（answerability rubric）

判者只看：本格代表問句、候選內容、本檔定義。⛔ 不看分數、排序、系統判定欄位。

## 四值定義

- **answerable**：候選細目內容有至少一句可直接回答該格代表問句，且不需要使用者提供任何實值（如姓名、房號、金額、日期等具體資料）。
- **partial**：候選內容只答得了代表問句的一部分子問題。子問題定義為代表問句可拆解出的獨立問點；判者於 `evidence_unit` 註記候選內容中答到的是哪一句。
- **no_source**：所有候選內容中沒有任何一句可以回答該格代表問句。
- **deliberate_no**：本格的 `policy` 為 `deliberate_no`，且帶有 `policy_ref`。

## 輸出

依上列定義，對每一格輸出：`label`（四值之一）、`fine_id`（`answerable`／`partial` 時為正解候選 id，其餘為 null）、`evidence_unit`（候選內容第幾句可答，無則為 null）、`confidence`（`high`／`medium`／`low`）。
