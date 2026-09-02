"""靜態契約測試：可見性尺與 retriever 過濾條件同源（P0-1 回測輸出契約 §B③）。

## 防的是什麼

`scripts/backtest/contract_enrich.visibility()` 是**手抄**的三軸過濾謂詞，
用來回答「這題的正解，這個角色到底看不看得到」（成因 V 類）。
它跟正本——`services/vendor_knowledge_retriever_v2` 的兩條 SQL WHERE——是**兩份**。

⚠️ 正本加一條過濾（例如 `AND kb.status = 'published'`）而尺沒跟上時：

    retriever  從此撈不到未發布的知識
    尺         照樣判「這列看得到」
    報表       說「正解可見卻沒被選中」⇒ 有人去調門檻／調排序
    真相       它結構上根本撈不到 ⇒ **怎麼調都沒用**

這正是 `成因分類.md` 白紙黑字列的既有白工：「把 V 誤判成 N／T」。

⚠️ `contract_enrich.py --self-test` **擋不住這件事**：它拿固定幾列已知答案的資料驗，
新增的第四軸不會改變那幾列的結論 ⇒ 尺照樣全綠。
資料層自證證明「現有的軸沒寫錯」，⛔ 不證明「現有的軸就是全部」。本檔補的是後者。

## 判準

把兩條 WHERE 讀到的 `kb.<欄位>` 抽出來，與尺宣告實作的 `FILTER_COLUMNS_*` 對帳。
不相等即紅——逼人當場決定：在尺裡補上判斷，或在此明寫豁免理由。
⛔ 不得只為了讓測試變綠而改宣告卻不實作對應判斷。
"""
import ast
import importlib.util
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
_RETRIEVER_PY = os.path.join(_ROOT, "services", "vendor_knowledge_retriever_v2.py")
_ENRICH_PY = os.path.join(_ROOT, "scripts", "backtest", "contract_enrich.py")

#: 出現在 WHERE 裡、但**不是**可見性判準的欄位——每一項都必須寫明理由。
#: （目前為空：兩條 WHERE 的每個欄位都是真過濾。保留此機制供未來明示豁免。）
_NOT_A_VISIBILITY_AXIS = frozenset()


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _sql_literals(fn_node) -> list:
    """取函式內所有字串常量（含 f-string 的字面片段）。"""
    out = []
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            out.append("".join(v.value for v in node.values
                               if isinstance(v, ast.Constant) and isinstance(v.value, str)))
    return out


_WHERE_RE = re.compile(r"\bWHERE\b(.*?)(?:\bORDER\s+BY\b|\Z)", re.IGNORECASE | re.DOTALL)
_KB_COL_RE = re.compile(r"\bkb\.([a-zA-Z_]\w*)")
_ORDER_BY_RE = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)


def _strip_order_by(sql: str) -> str:
    """砍掉 ORDER BY 之後——排序鍵不是過濾條件。"""
    m = _ORDER_BY_RE.search(sql)
    return sql[:m.start()] if m else sql


def _where_columns(fn_node) -> set:
    """抽出該函式 SQL 的 WHERE 區塊所讀的 `kb.<欄位>`。

    ⚠️ 兩條 WHERE 都把業態／角色過濾放在 f-string 佔位符裡
    （`{business_type_filter_sql}` / `{target_user_filter_sql}`），
    佔位符展開後才看得到欄位 ⇒ 另外掃描函式內所有 `*_filter_sql` 字串常量。
    """
    cols = set()
    found_where = False
    for lit in _sql_literals(fn_node):
        m = _WHERE_RE.search(lit)
        if m:
            found_where = True
            cols |= set(_KB_COL_RE.findall(m.group(1)))
    assert found_where, "解析不到 WHERE 區塊——SQL 結構已變，本測試的假設需同步更新"

    # 佔位符／追加片段：形如 "AND kb.business_types && %s::text[]"、
    # 或 " AND kb.keywords && %s::text[] ORDER BY kb.priority DESC …" 的獨立字串常量。
    # ⚠️ 必須先砍掉 ORDER BY 之後——那裡的 kb.priority／kb.id 是**排序**不是過濾，
    #    抓進來會讓這條不變量對著噪音報警（2026-09-02 第一次跑就踩到）。
    for lit in _sql_literals(fn_node):
        if _WHERE_RE.search(lit):
            continue                      # 主 SQL 已處理
        if "kb." in lit and ("&&" in lit or "IS NULL" in lit):
            cols |= set(_KB_COL_RE.findall(_strip_order_by(lit)))

    assert cols, "WHERE 區塊抽不到任何 kb.<欄位>——解析壞了，⛔ 不得靜默通過"
    return cols - _NOT_A_VISIBILITY_AXIS


def _load_enrich():
    spec = importlib.util.spec_from_file_location("contract_enrich", _ENRICH_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def _ctx():
    tree = ast.parse(_read(_RETRIEVER_PY))
    vec = _find_function(tree, "_vector_search")
    kw = _find_function(tree, "_keyword_search")
    assert vec is not None and kw is not None, (
        "找不到 _vector_search／_keyword_search——⛔ 檢索入口已改名，本測試假設失效"
    )
    return {
        "sql_vector": _where_columns(vec),
        "sql_keyword": _where_columns(kw),
        "enrich": _load_enrich(),
    }


@pytest.mark.req("conversational-routing-execution:P0-1")
def test_vector_filter_columns_declared(_ctx):
    sql, declared = _ctx["sql_vector"], set(_ctx["enrich"].FILTER_COLUMNS_VECTOR)
    assert sql == declared, (
        "可見性尺與 _vector_search 的過濾條件脫鉤。\n"
        f"  SQL 讀到的欄位              ：{sorted(sql)}\n"
        f"  尺宣告實作的 FILTER_COLUMNS_VECTOR：{sorted(declared)}\n"
        f"  ⚠️ SQL 有而尺沒實作（會誤判成可見 ⇒ V 類被當成 T／N）：{sorted(sql - declared)}\n"
        f"  尺多宣告但 SQL 沒有（可能已移除）：{sorted(declared - sql)}\n"
        "→ 在 contract_enrich.visibility() 補上對應判斷，"
        "或加入 _NOT_A_VISIBILITY_AXIS 並寫明理由。⛔ 不得只改宣告不改判斷。"
    )


@pytest.mark.req("conversational-routing-execution:P0-1")
def test_keyword_filter_columns_declared(_ctx):
    sql, declared = _ctx["sql_keyword"], set(_ctx["enrich"].FILTER_COLUMNS_KEYWORD)
    assert sql == declared, (
        "可見性尺與 _keyword_search 的過濾條件脫鉤。\n"
        f"  SQL 讀到的欄位               ：{sorted(sql)}\n"
        f"  尺宣告實作的 FILTER_COLUMNS_KEYWORD：{sorted(declared)}\n"
        f"  ⚠️ SQL 有而尺沒實作：{sorted(sql - declared)}\n"
        f"  尺多宣告但 SQL 沒有：{sorted(declared - sql)}\n"
        "→ 同上。⚠️ 詞面路與向量路的 WHERE **不一樣**（前者要 keywords、不要 embedding），"
        "⛔ 不得只模型單一路徑。"
    )


@pytest.mark.req("conversational-routing-execution:P0-1")
def test_two_paths_have_different_filters(_ctx):
    """釘住「兩條路不同」這件事本身——它是尺必須算兩次的理由。

    ⚠️ 若哪天兩條真的統一了，本測試會紅：那時該做的是確認統一屬實、
    再簡化 visibility()，⛔ 不是把這條刪掉了事。
    """
    vec, kw = _ctx["sql_vector"], _ctx["sql_keyword"]
    assert "embedding" in vec and "embedding" not in kw, (
        f"向量路應要求 embedding、詞面路不應要求。實得 vector={sorted(vec)} keyword={sorted(kw)}"
    )
    assert "keywords" in kw and "keywords" not in vec, (
        f"詞面路應要求 keywords、向量路不應要求。實得 vector={sorted(vec)} keyword={sorted(kw)}"
    )


@pytest.mark.req("conversational-routing-execution:P0-1")
def test_b2b_business_type_filter_has_no_null_pass(_ctx):
    """b2b 業態嚴格分支（無 IS NULL 放行）＝刻意的跨業者隔離，釘死。

    ⛔ `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` §3 曾漏掉這條分支，
    照它補 `IS NULL` 會打穿隔離。本斷言讓那個改動一定要先讓這條測試變紅。
    """
    src = _read(_RETRIEVER_PY)
    b2b_frag = "kb.business_types && %s::text[]"
    b2c_frag = "(kb.business_types IS NULL OR kb.business_types && %s::text[])"
    assert b2b_frag in src, f"找不到 b2b 業態謂詞 {b2b_frag!r}——過濾寫法已變，需同步本測試"
    assert b2c_frag in src, f"找不到 b2c 業態謂詞 {b2c_frag!r}——過濾寫法已變，需同步本測試"
    # b2b 那條**不得**出現在被 IS NULL 包住的形式裡（正對照組即 b2c 那條）
    assert f'"{b2b_frag}"' in src or f"'{b2b_frag}'" in src, (
        "b2b 業態謂詞不再是獨立字串常量——⛔ 可能已被併進含 IS NULL 的分支，請人工確認"
    )
