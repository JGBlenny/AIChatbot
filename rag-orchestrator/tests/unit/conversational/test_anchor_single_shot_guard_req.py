"""unit:錨點單發防呆（五域抽驗 A3/電費題逼出的 P0）。

answer 空的知識＝面向進場錨點，只供進場判定；落回單發答題前必須濾除——
否則 question_summary 被當回答原文輸出（實例：3873「我想改合約 內容要修改」）。
過濾點在分類路由出口之後（進場判定不受影響——錨點仍以 top1 身分驅動進面向）。
"""
import pytest

pytestmark = pytest.mark.unit


def _rows():
    return [
        {"id": 3873, "question_summary": "我想改合約 內容要修改", "answer": "", "similarity": 0.71},
        {"id": 1, "question_summary": "正常知識", "answer": "有內容的答案", "similarity": 0.69},
        {"id": 2, "question_summary": "空白答案", "answer": "   ", "similarity": 0.68},
        {"id": 3, "question_summary": "None 答案", "answer": None, "similarity": 0.67},
    ]


def test_drop_empty_answer_rows_filters_anchors():
    from routers.chat import _drop_empty_answer_rows
    out = _drop_empty_answer_rows(_rows())
    assert [k["id"] for k in out] == [1]          # 空/空白/None 全濾，正常知識晉位 top1


def test_drop_empty_answer_rows_tolerates_none_and_empty():
    from routers.chat import _drop_empty_answer_rows
    assert _drop_empty_answer_rows(None) == []
    assert _drop_empty_answer_rows([]) == []


def test_all_anchors_filtered_leaves_empty_list():
    """全錨點 → 空列（下游 _build_knowledge_response 有 if knowledge_list 防呆走 fallback）。"""
    from routers.chat import _drop_empty_answer_rows
    out = _drop_empty_answer_rows([{"id": 9, "question_summary": "錨", "answer": ""}])
    assert out == []
