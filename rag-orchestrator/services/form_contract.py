"""舊鏈隔離 S3（Plan 第 5 稿 D 案）：從 `conversational_engine.py` 抽出的純常數。

新線（`services/agent/**`）只需要這幾個穩定字面量本身，⛔ 不需要引擎其餘 1,581 行。
砍舊鏈（`conversational_engine.py`／`api_call_handler.py` 等）前，先把新線仍在用的
常數搬到這個獨立、不依賴引擎其餘部分的模組——消費端（`services/agent/tools/confirm.py`、
`services/agent/tools/session.py`）改指這裡。

⛔ **值一個都不准改**：
  - `CONVERSATIONAL_FORM_ID` 是寫進 DB 的 `form_sessions.form_id`，改了舊資料列讀不到。
  - `QR_SUBMIT`／`QR_EDIT`／`QR_CANCEL` 是送給呼叫端（前端）的按鈕機器值，
    改了使用者按下舊按鈕會對不上新後端。
  - `DEFAULT_QR_LABELS` 是預設顯示文字，行為契約的一部分。

原始出處：`services/conversational_engine.py`（搬移前版本，2026-09-10 之前）行 33、55-58。
"""
from __future__ import annotations

#: `form_sessions.form_id` 的固定值——對話式回答引擎用「偽表單」的方式借用
#: form_sessions 這張表存多輪對話狀態（非真表單，但共用同一張表／同一組欄位）。
CONVERSATIONAL_FORM_ID = "conversational"

#: 三顆確認 quick reply 的穩定機器值（前後端契約；label 可由配置覆寫，value 不變）。
#: 原名 `_QR_SUBMIT`／`_QR_EDIT`／`_QR_CANCEL`（底線開頭）——搬到本檔後改公開名，
#: 因為本檔存在的目的就是給其他模組 import。
QR_SUBMIT = "confirm_submit"
QR_EDIT = "confirm_edit"
QR_CANCEL = "confirm_cancel"

#: 原名 `_DEFAULT_QR_LABELS`。
DEFAULT_QR_LABELS = {
    QR_SUBMIT: "✅ 確認送出",
    QR_EDIT: "✏️ 我要修改",
    QR_CANCEL: "❌ 取消",
}

__all__ = [
    "CONVERSATIONAL_FORM_ID",
    "QR_SUBMIT",
    "QR_EDIT",
    "QR_CANCEL",
    "DEFAULT_QR_LABELS",
]
