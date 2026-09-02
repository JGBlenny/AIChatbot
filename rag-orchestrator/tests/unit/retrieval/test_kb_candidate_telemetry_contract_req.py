"""靜態契約測試：候選遙測的剝欄清單不變量（P0-1 回測輸出契約 §B②）。

## 防的是什麼

`chat._retrieve_knowledge` 為了把候選分數落進 `usage_events.decision_snapshot`，
**恆以 `return_debug_info=True`** 呼叫 `retrieve_knowledge_hybrid`（分數欄不能在遙測前被剝掉），
遙測完再自己把內部欄位剝回去，讓沒要求 debug 的呼叫端拿到與改動前逐欄相同的 dict。

於是同一份「內部欄位清單」存在**兩個地方**：

    vendor_knowledge_retriever_v2.retrieve_knowledge_hybrid  尾端 result.pop(...) 五項
    chat._KB_DEBUG_ONLY_KEYS                                  同五項

⚠️ 兩份不同步時**沒有任何既有機制會紅**：`make audit` 不管，2005 條單元測試也不覆蓋。
症狀是下游突然收到一個它從來沒看過的欄位——**靜默的行為變更**，可以跑很久沒人發現。
本檔把這個隱性耦合變成機器把關的靜態不變量。

形狀沿用同目錄 `test_knowledge_dict_contract_req.py`（trigger-vocabulary-debt 元件 5）：
AST 靜態解析、零 DB 依賴、離線可跑、隨 `make test-unit` 執行。

## ⛔ 解析不到就大聲失敗

每個解析器都先斷言「有解到東西」。⛔ 不得讓「抽不到 ⇒ 兩個空集合相等」變成假綠——
那正是這類靜態測試最常見的死法（否定結論必須有正對照組）。
"""
import ast
import os

import pytest

pytestmark = pytest.mark.unit

_ROOT = os.path.dirname(  # rag-orchestrator/
    os.path.dirname(  # tests/
        os.path.dirname(  # tests/unit/
            os.path.dirname(os.path.abspath(__file__))  # tests/unit/retrieval/
        )
    )
)
_CHAT_PY = os.path.join(_ROOT, "routers", "chat.py")
_RETRIEVER_PY = os.path.join(_ROOT, "services", "vendor_knowledge_retriever_v2.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _find_function(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


# ---------------------------------------------------------------------------
# retriever 側：`if not return_debug_info:` 區塊裡的 result.pop('<key>', None)
# ---------------------------------------------------------------------------

def _parse_retriever_pop_keys(source: str) -> set:
    """抽出 `retrieve_knowledge_hybrid` 內 `if not return_debug_info:` 區塊的 pop 欄位。"""
    fn = _find_function(ast.parse(source), "retrieve_knowledge_hybrid")
    assert fn is not None, "找不到 retrieve_knowledge_hybrid 定義——解析假設已失效"

    target_if = None
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        # 形狀：not return_debug_info
        if (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
                and isinstance(test.operand, ast.Name)
                and test.operand.id == "return_debug_info"):
            target_if = node
            break
    assert target_if is not None, (
        "找不到 `if not return_debug_info:` 區塊——剝欄邏輯可能已改寫，"
        "本測試的解析假設需同步更新（⛔ 不得直接刪掉本測試）"
    )

    keys = set()
    for node in ast.walk(target_if):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop" and node.args):
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.add(arg.value)
    assert keys, "解析到 pop 區塊但抽不到任何欄位名——解析壞了，⛔ 不得靜默通過"
    return keys


# ---------------------------------------------------------------------------
# chat 側：模組層常數 _KB_DEBUG_ONLY_KEYS
# ---------------------------------------------------------------------------

def _parse_chat_debug_only_keys(source: str) -> set:
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_KB_DEBUG_ONLY_KEYS"
                   for t in node.targets):
            continue
        assert isinstance(node.value, (ast.Tuple, ast.List, ast.Set)), (
            "_KB_DEBUG_ONLY_KEYS 不是字面量序列——本測試無法靜態解析，需同步更新"
        )
        keys = set()
        for elt in node.value.elts:
            assert isinstance(elt, ast.Constant) and isinstance(elt.value, str), (
                "_KB_DEBUG_ONLY_KEYS 含非字串常量元素"
            )
            keys.add(elt.value)
        assert keys, "_KB_DEBUG_ONLY_KEYS 為空——⛔ 剝欄會整組失效"
        return keys
    raise AssertionError("找不到 _KB_DEBUG_ONLY_KEYS 定義")


@pytest.fixture(scope="module")
def _keys():
    return {
        "retriever": _parse_retriever_pop_keys(_read(_RETRIEVER_PY)),
        "chat": _parse_chat_debug_only_keys(_read(_CHAT_PY)),
    }


# ---------------------------------------------------------------------------
# 測試
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-routing-execution:P0-1")
def test_debug_only_keys_match_retriever_pop_list(_keys):
    """兩份清單必須逐項相同——少一項就是下游多看到一個欄位（靜默行為變更）。"""
    retriever, chat = _keys["retriever"], _keys["chat"]
    assert retriever == chat, (
        "剝欄清單不同步：`chat._retrieve_knowledge` 恆以 return_debug_info=True 取值後自行剝欄，\n"
        "兩份清單一旦分岔，沒要求 debug 的呼叫端就會收到本來看不到的欄位。\n"
        f"  retriever pop（vendor_knowledge_retriever_v2）：{sorted(retriever)}\n"
        f"  _KB_DEBUG_ONLY_KEYS（chat.py）              ：{sorted(chat)}\n"
        f"  retriever 有而 chat 沒剝（⚠️ 會洩漏給下游）：{sorted(retriever - chat)}\n"
        f"  chat 剝了但 retriever 沒有（多剝，可能刪到真欄位）：{sorted(chat - retriever)}\n"
        "→ 在 retriever 增減 debug 欄位時，請同步 _KB_DEBUG_ONLY_KEYS。"
    )


@pytest.mark.req("conversational-routing-execution:P0-1")
def test_retrieve_knowledge_requests_debug_unconditionally(_keys):
    """產線那次檢索必須恆帶 `return_debug_info=True`，否則分數欄在遙測前就沒了。

    ⚠️ 這條與上一條互為前提：若改回 `return_debug_info=request.include_debug_info`，
    剝欄邏輯就變成多餘且有害（會剝掉 debug 請求本來要的欄位）。
    """
    fn = _find_function(ast.parse(_read(_CHAT_PY)), "_retrieve_knowledge")
    assert fn is not None, "找不到 _retrieve_knowledge 定義——解析假設已失效"

    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "retrieve_knowledge_hybrid"]
    assert calls, "_retrieve_knowledge 內找不到 retrieve_knowledge_hybrid 呼叫"

    def _kw(call, name):
        for k in call.keywords:
            if k.arg == name:
                return k.value
        return None

    # 產線那次＝**沒有** return_unfiltered=True 的那次（debug 旁路是另一次）
    prod = [c for c in calls if _kw(c, "return_unfiltered") is None]
    assert prod, "找不到產線路徑的 retrieve_knowledge_hybrid 呼叫（皆帶 return_unfiltered？）"

    for call in prod:
        node = _kw(call, "return_debug_info")
        assert isinstance(node, ast.Constant) and node.value is True, (
            "產線檢索未恆帶 return_debug_info=True ⇒ 分數欄會在候選遙測之前被剝掉，"
            "kb_candidates 的 rerank_score 會變成 None。"
        )
        assert _kw(call, "unfiltered_sink") is not None, (
            "產線檢索未傳 unfiltered_sink ⇒ 門檻把候選砍到 0 筆時遙測拿不到任何東西，"
            "而那正是 T 類（門檻）歸因的目標事件。"
        )


@pytest.mark.req("conversational-routing-execution:P0-1")
def test_metering_happens_before_stripping(_keys):
    """遙測必須早於剝欄——順序反了，落盤的分數欄會全是 None。

    ⚠️ `unfiltered_sink` 收的是**同一批 dict 參考**（非複本），所以剝欄會就地改到
    sink 裡那些列。這條順序是 kb_candidates 有沒有分數的唯一保障。
    """
    fn = _find_function(ast.parse(_read(_CHAT_PY)), "_retrieve_knowledge")
    assert fn is not None, "找不到 _retrieve_knowledge 定義——解析假設已失效"

    meter_lines = [n.lineno for n in ast.walk(fn)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "_meter_kb_candidates"]
    assert meter_lines, "_retrieve_knowledge 內找不到 _meter_kb_candidates 呼叫"

    pop_lines = [n.lineno for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "pop"]
    assert pop_lines, "_retrieve_knowledge 內找不到剝欄的 pop 呼叫"

    assert max(meter_lines) < min(pop_lines), (
        "順序錯誤：候選遙測必須在剝欄**之前**。\n"
        f"  _meter_kb_candidates 於 line {sorted(meter_lines)}\n"
        f"  pop 於 line {sorted(pop_lines)}\n"
        "→ 剝欄會就地改到 unfiltered_sink 共用的同一批 dict，順序反了分數就沒了。"
    )
