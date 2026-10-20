"""DSP-091 分工防偏離片（DG-2）：已知偏離登記＋分工表程式列對照（資料檔，⛔ 放邏輯）。

KD 清單必須與目標正本 `.kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md` §3.1 表
一致（ID 集合與接手片）；不變量 45（`scripts/audit/checks/division_guard.py`）核對。
偏離被修掉時：對應現況探針（`test_dsp091_division_contract_req.py`）失敗 ⇒ 把該筆移出這裡與
目標正本 §3.1、改寫成必過契約、更新程式註解。

欄位：
- `id`／`row`／`desc`／`takeover`：同目錄正本 §3.1 表的「ID | 偏離 | 分工表列 | 接手片」。
- `anchors`：(檔名, 可 grep 符號)，檔在 `rag-orchestrator/services/agent/`；探針會確認符號仍在。
- `has_comment`：程式內有「過渡修正」註解掛在這個偏離上（註解需含 `id` 與 `comment_token`）。
- `comment_token`：註解裡寫接手片的字樣。
"""
from __future__ import annotations

TEST_FILE = "test_dsp091_division_contract_req.py"

KNOWN_DEVIATIONS = (
    {"id": "KD-1", "row": "寫入全程、已選定的那筆紀錄", "takeover": "A-2", "comment_token": "A-2",
     "desc": "點選範圍、唯讀檢視回合：模型自呼 confirm.request 的參數照舊執行出卡",
     "anchors": (("runtime.py", "SELECT_SCOPE_KEY"), ("runtime.py", "_write_draft_merge_model_confirm")),
     "has_comment": True},
    {"id": "KD-2", "row": "寫入全程", "takeover": "文件回合", "comment_token": "文件回合",
     "desc": "文件回合、文件暫存有效回合：模型參數出卡；文件程式發卡的非終結結果交回模型",
     "anchors": (("runtime.py", "_document_carry_of"), ("runtime.py", "_document_program_message")),
     "has_comment": True},
    {"id": "KD-5", "row": "轉人規則（含收尾）", "takeover": "E", "comment_token": "E 片",
     "desc": "轉人由模型輸出決定，出口閘只在模型選了轉人後介入；無收尾規則",
     "anchors": (("exit_gates.py", "_apply_handoff_data_exits"),),
     "has_comment": False},
    {"id": "KD-6", "row": "知識完全查無的出口", "takeover": "D", "comment_token": "D 片",
     "desc": "知識完全查無沒有程式先發的出口",
     "anchors": (("runtime.py", "candidate_none_visible"),),
     "has_comment": False},
    {"id": "KD-7", "row": "唯讀查詢的查詢與篩選", "takeover": "G", "comment_token": "G 片",
     "desc": "唯讀查詢的參數由模型自呼工具決定",
     "anchors": (("runtime.py", "_pre_lookup_trigger"), ("runtime.py", "_enforce_tool_scope")),
     "has_comment": False},
    {"id": "KD-8", "row": "已選定的那筆紀錄", "takeover": "A-2", "comment_token": "A-2",
     "desc": "打字挑選候選無程式路徑",
     "anchors": (("runtime.py", "_SELECT_VALUE_RE"),),
     "has_comment": False},
)

#: DSP-091 分工表「程式」列 R1～R6：每列至少一支必過測試（`TEST_FILE` 內的函式名）或一筆 KD。
DIVISION_ROWS = {
    "R1": {"name": "寫入全程與確認",
           "tests": ("test_c1_model_confirm_never_executes_with_model_args",
                     "test_c2_missing_fields_ask_is_the_program_text",
                     "test_c3_confirm_button_turns_never_call_the_model",
                     "test_c7_unissued_proposal_reply_is_the_program_state_reply"),
           "kds": ("KD-1", "KD-2")},
    "R2": {"name": "已選定的那筆紀錄",
           "tests": ("test_c4_select_button_turn_never_calls_the_model",),
           "kds": ("KD-1", "KD-8")},
    "R3": {"name": "帶狀態的句子與確認卡、按鈕",
           "tests": ("test_c5_card_answer_is_the_formatter_text",
                     "test_c6_buttons_come_only_from_the_program",
                     "test_c8_model_confirm_prose_is_replaced_by_the_program_reply",
                     "test_c9_model_field_ask_is_replaced_by_the_program_reply"),
           "kds": ()},
    "R4": {"name": "轉人規則（含收尾）", "tests": (), "kds": ("KD-5",)},
    "R5": {"name": "知識完全查無的出口", "tests": (), "kds": ("KD-6",)},
    "R6": {"name": "唯讀查詢的查詢與篩選", "tests": (), "kds": ("KD-7",)},
}
