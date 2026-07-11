"""靜態契約測試：知識 dict 欄位鏈不變量（spec trigger-vocabulary-debt・元件 5・R4.1）。

防回歸目標——把「消費欄位 ⊆ 產出欄位 ⊆ SELECT 欄位」變成機器把關的靜態不變量，
使檢索斷鏈（如觸發配置三欄未 SELECT／未透傳而消費層 .get() 恆得 None）這類 bug
不再無聲發生。任務 1.1 已補齊三欄透傳，故本測試現況為綠；其價值在未來防回歸。

三個集合（皆以原始碼靜態解析，零 DB 依賴、離線可跑）：
- consumed：chat.py 對 `best_knowledge` 的硬性欄位存取
  （`best_knowledge.get('k')` 單參 + `best_knowledge['k']` 下標；見下方 SOFT/BENIGN 說明）
- produced：`_format_result` return dict 的 key 字面量（AST 解析）
- selected_vector / selected_keyword：兩條 SQL SELECT 的欄位名（`kb.<col>` 與 alias）

斷言：
- consumed ⊆ produced
- db_backed(produced) ⊆ selected_vector （intent_id 豁免——僅 keyword 路徑 JOIN）
- db_backed(produced) ⊆ selected_keyword

解析範圍刻意「對現在的碼穩健」而非通用解析器；但以 AST/容忍空白的正則為主，
不脆到改個空白就爆。
"""
import ast
import os
import re

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


# ---------------------------------------------------------------------------
# 豁免清單（皆有註解說明理由）
# ---------------------------------------------------------------------------

# produced 中「非 DB 欄位」——由 _format_result 計算/預設產生，不來自 SELECT，
# 因此不納入 db_backed(produced) ⊆ selected 的比對。
_COMPUTED_FIELDS = frozenset({
    "similarity",           # 由 _finalize_scores 依公式重算
    "vector_similarity",    # vector path 讀 SQL alias；keyword path 預設 0.0（非 kb 直欄）
    "keyword_score",        # keyword 路徑計算分數（預設 None）
    "keyword_boost",        # 預設 1.0
    "rerank_score",         # reranker 寫入（預設 None）
    "score_source",         # _finalize_scores 標記分數來源
    "keyword_matches",      # keyword 路徑匹配詞列表（預設空）
    "original_similarity",  # 向後相容 alias（= vector_similarity）
    "search_method",        # metadata（'vector'/'keyword'），非 kb 直欄
})

# intent_id 僅存在於 keyword 路徑的 SELECT（LEFT JOIN knowledge_intent_mapping kim）；
# vector 路徑不 JOIN、無此欄。故 db_backed(produced) ⊆ selected_vector 時豁免 intent_id。
# （keyword 路徑仍須涵蓋，不豁免。）
_VECTOR_EXEMPT = frozenset({"intent_id"})

# consumed 中「良性/防禦性讀取」——read 有安全預設或屬 API-call sources 區塊的
# 非契約 metadata，欄位缺失只會得到 None/預設而不會靜默破壞觸發鏈，
# 因此不納入 consumed ⊆ produced 的契約比對：
#   - intent_name  : _handle_api_call 回應的 intent_name，best_knowledge.get('intent_name','API查詢')
#                    有預設；retriever 契約無此欄（意圖名另由 intent mapping 提供）。
#   - vendor_id    : _handle_api_call sources[] 的 informational 欄位；retriever 產出的是
#                    vendor_ids（複數陣列），單數 vendor_id 恆得 None，屬既有 benign 死讀。
#   - target_users : 同上 sources[] informational；retriever 產出 target_user（單數），
#                    複數 target_users 恆得 None，屬既有 benign 死讀。
# 三者皆與本 spec 的觸發/檢索契約無關，且屬 _handle_api_call 回應組裝的既有慣性，
# 納入會使不變量失焦。此為顯式碳排除——任何「新」的孤兒 consumed key 仍會觸發斷言。
_CONSUMED_BENIGN = frozenset({"intent_name", "vendor_id", "target_users"})


# ---------------------------------------------------------------------------
# consumed：解析 chat.py 對 best_knowledge 的硬性欄位存取
# ---------------------------------------------------------------------------

def _parse_consumed(source: str) -> set:
    """抽出對名為 best_knowledge 的變數之欄位存取字面量。

    納入（硬性依賴，欄位缺失會回 None/KeyError 而可能破壞下游）：
      - best_knowledge.get('<key>')          單參 .get（無安全預設）
      - best_knowledge['<key>']              下標存取
    排除：
      - best_knowledge.get('<key>', <默認>)  雙參 .get——有預設、良性降級
      - _CONSUMED_BENIGN                     顯式良性/非契約 metadata（見上）
    """
    tree = ast.parse(source)
    consumed = set()

    for node in ast.walk(tree):
        # best_knowledge['<key>'] 下標
        if isinstance(node, ast.Subscript):
            if _is_best_knowledge(node.value):
                key = _const_str(_subscript_key(node))
                if key is not None:
                    consumed.add(key)
        # best_knowledge.get('<key>')  —— 僅單參（無安全預設）視為硬依賴
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and _is_best_knowledge(func.value)
                and len(node.args) == 1
                and not node.keywords
            ):
                key = _const_str(node.args[0])
                if key is not None:
                    consumed.add(key)

    return consumed - _CONSUMED_BENIGN


def _is_best_knowledge(node) -> bool:
    return isinstance(node, ast.Name) and node.id == "best_knowledge"


def _subscript_key(node: ast.Subscript):
    # Py3.9+：node.slice 直接是運算式節點
    return node.slice


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


# ---------------------------------------------------------------------------
# produced：解析 _format_result return dict 的 key 字面量（AST）
# ---------------------------------------------------------------------------

def _parse_produced(source: str) -> set:
    tree = ast.parse(source)

    format_fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_format_result":
            format_fn = node
            break
    assert format_fn is not None, "找不到 _format_result 函式定義"

    # 取函式體內 return 的 dict 常量 key
    produced = set()
    found_return_dict = False
    for node in ast.walk(format_fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            found_return_dict = True
            for key_node in node.value.keys:
                key = _const_str(key_node)
                assert key is not None, "_format_result return dict 含非字串常量 key"
                produced.add(key)
    assert found_return_dict, "_format_result 未找到 return dict 字面量"
    return produced


# ---------------------------------------------------------------------------
# selected：解析兩條 SQL SELECT 的欄位名（kb.<col> 與 alias）
# ---------------------------------------------------------------------------

# 匹配「真正的 SQL SELECT」欄位清單片段：SELECT 後緊接 `kb.` 限定欄
# （排除 docstring 中提及 "SELECT alias" 等散文；本檔兩條 SQL 皆以 kb.id 起首），
# 非貪婪擷取至第一個 `FROM knowledge_base`（兩條查詢的主表，避免子查詢/散文 FROM 誤配）。
_SELECT_RE = re.compile(
    r"SELECT\s+(kb\..*?)\s+FROM\s+knowledge_base",
    re.IGNORECASE | re.DOTALL,
)
# 表.欄 形式（kb.xxx / kim.xxx），欄名為識別字。
_QUALIFIED_COL_RE = re.compile(r"\b[a-zA-Z_]\w*\.([a-zA-Z_]\w*)")
# `as <alias>` 形式（例：... as vector_similarity）。
_ALIAS_RE = re.compile(r"\bas\s+([a-zA-Z_]\w*)", re.IGNORECASE)


def _parse_select_columns(select_body: str) -> set:
    """把一段 SELECT 欄位清單解析為欄位名集合。

    規則（對現行兩條 SQL 穩健）：
      - 逗號切分欄位項。
      - 含 alias（`... as name`）→ 取 alias（涵蓋計算欄位如 vector_similarity）。
      - 否則取 `表.欄` 的欄名（kb.form_id → form_id、kim.intent_id → intent_id）。
    """
    cols = set()
    for item in select_body.split(","):
        item = item.strip()
        if not item:
            continue
        alias_m = _ALIAS_RE.search(item)
        if alias_m:
            cols.add(alias_m.group(1))
            continue
        qual = _QUALIFIED_COL_RE.findall(item)
        if qual:
            # 取最後一個 表.欄 的欄名（避免函式參數中的 表.欄 誤取；現行 SQL 每項單欄）
            cols.add(qual[-1])
    return cols


def _parse_selects(source: str) -> list:
    """回傳原始碼中每一段 SELECT..FROM 的欄位集合（依出現順序）。"""
    return [_parse_select_columns(m.group(1)) for m in _SELECT_RE.finditer(source)]


# ---------------------------------------------------------------------------
# 測試
# ---------------------------------------------------------------------------

def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def _sets():
    chat_src = _read(_CHAT_PY)
    retr_src = _read(_RETRIEVER_PY)

    consumed = _parse_consumed(chat_src)
    produced = _parse_produced(retr_src)
    selects = _parse_selects(retr_src)

    # 現行檔案有兩條主 SELECT（_vector_search、_keyword_search），依出現順序。
    assert len(selects) >= 2, (
        f"預期解析到 >=2 條 SELECT（vector + keyword），實得 {len(selects)}；"
        "SQL 結構可能已變，需更新解析假設。"
    )
    selected_vector, selected_keyword = selects[0], selects[1]
    return {
        "consumed": consumed,
        "produced": produced,
        "selected_vector": selected_vector,
        "selected_keyword": selected_keyword,
    }


@pytest.mark.req("trigger-vocabulary-debt:4.1")
def test_consumed_subset_of_produced(_sets):
    consumed, produced = _sets["consumed"], _sets["produced"]
    missing = consumed - produced
    assert not missing, (
        "檢索斷鏈：chat.py 消費了 _format_result 未產出的欄位。\n"
        f"  缺於 produced（_format_result）：{sorted(missing)}\n"
        f"  consumed（chat.py best_knowledge 硬存取）：{sorted(consumed)}\n"
        f"  produced（_format_result keys）：{sorted(produced)}\n"
        "→ 若為新契約欄位：請於 _format_result 補透傳；"
        "若為良性非契約讀取：加入 _CONSUMED_BENIGN 並註明理由。"
    )


@pytest.mark.req("trigger-vocabulary-debt:4.1")
def test_db_backed_produced_subset_of_vector_select(_sets):
    produced = _sets["produced"]
    selected_vector = _sets["selected_vector"]
    db_backed = (produced - _COMPUTED_FIELDS) - _VECTOR_EXEMPT
    missing = db_backed - selected_vector
    assert not missing, (
        "檢索斷鏈：_format_result 產出的 DB 欄位未出現在 _vector_search SELECT。\n"
        f"  缺於 selected_vector：{sorted(missing)}\n"
        f"  db_backed(produced)（扣計算欄+vector 豁免）：{sorted(db_backed)}\n"
        f"  selected_vector（SELECT 欄位）：{sorted(selected_vector)}\n"
        "→ 請於 _vector_search 的 SELECT 補上對應 kb.<欄位>。"
    )


@pytest.mark.req("trigger-vocabulary-debt:4.1")
def test_db_backed_produced_subset_of_keyword_select(_sets):
    produced = _sets["produced"]
    selected_keyword = _sets["selected_keyword"]
    # keyword 路徑有 JOIN，涵蓋 intent_id → 不豁免。
    db_backed = produced - _COMPUTED_FIELDS
    missing = db_backed - selected_keyword
    assert not missing, (
        "檢索斷鏈：_format_result 產出的 DB 欄位未出現在 _keyword_search SELECT。\n"
        f"  缺於 selected_keyword：{sorted(missing)}\n"
        f"  db_backed(produced)（扣計算欄）：{sorted(db_backed)}\n"
        f"  selected_keyword（SELECT 欄位）：{sorted(selected_keyword)}\n"
        "→ 請於 _keyword_search 的 SELECT 補上對應 kb.<欄位>。"
    )


@pytest.mark.req("trigger-vocabulary-debt:4.1")
def test_trigger_config_fields_in_all_three_sets(_sets):
    """具名鎖定：本 spec 修復的觸發配置三欄須貫穿 consumed→produced→兩條 SELECT。

    （通用子集斷言已涵蓋，此為對本案核心欄位的可讀性回歸鎖，便於未來定位。）
    """
    trigger_fields = {"trigger_mode", "trigger_keywords", "immediate_prompt"}
    for name in ("produced", "selected_vector", "selected_keyword"):
        missing = trigger_fields - _sets[name]
        assert not missing, f"觸發配置欄位缺於 {name}：{sorted(missing)}"
