"""unit：抽取器的**不變量**（spec routing-disambiguation 任務 2.5｜R2.3, R3.1, R3.4）。

鎖六件事：零 LLM／零 IO／**不讀相似度**／決定性／`InstanceEvidence` 真 immutable／
`spans` 只保存命中片段。

⚠️ **與相似度正交是本元件存在的唯一理由**（R3.1）。
若它偷讀分數，整個方案退化成「換個地方做相似度競爭」（R2.3）——
那正是前案 3.4 被獨立 verifier REFUTED 的形態（兩側靠 0.003～0.005 分差維持）。

⚠️ 另鎖 **identifier 同步守門**：`instance_evidence` 為維持零相依而**逐字複製**
`conversational_engine._ID_TOKEN_RE`，兩份表示**不得漂移**。
本檔以 **behavioral equivalence** 鎖定，**不比 regex 字串**——
真正的契約還包含 flags、token 邊界、與日期相鄰時的排除、整句純數字的上下限，
比字串只證明「兩行字一樣」，不證明「兩者同判」。
"""
import ast
import dataclasses
import os

import pytest

pytestmark = pytest.mark.unit

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "services", "instance_evidence.py")

#: 允許的 import——全部是純標準函式庫且無 IO
ALLOWED_IMPORTS = {"re", "dataclasses", "typing"}

#: 相似度相關字樣一律不得出現於本模組
FORBIDDEN_TOKENS = ["similarity", "score", "rerank", "embedding", "llm", "openai"]

#: identifier 行為等價矩陣（同時餵兩側，要求逐筆同判）
IDENTIFIER_MATRIX = [
    ("12345", "純數字整句"),
    ("12", "邊界下限：2 位"),
    ("1", "低於下限：1 位"),
    ("123456789012345", "邊界上限：15 位"),
    ("1234567890123456", "超過整句上限：16 位"),
    ("我要查帳單 編號 12345", "句中 id-like token"),
    ("租期 2026/12/30 到期", "日期（斜線）：結構性特徵，不得算識別"),
    ("租期 2026-12-30 到期", "日期（連字號）"),
    ("金額 1200 元", "四位數：結構上仍是 token"),
    ("AB1234 這張", "中英混合 token"),
    ("價格 12.50", "小數：不得算識別"),
    ("編號 123", "三位數且非整句：低於 token 下限"),
    ("我的這張帳單", "無數字"),
    ("", "空字串"),
    (None, "None"),
]


def _x():
    from services.instance_evidence import InstanceEvidenceExtractor
    return InstanceEvidenceExtractor()


def _source():
    with open(_MODULE_PATH, encoding="utf-8") as f:
        return f.read()


# ── 零相依／零 IO／不讀相似度 ─────────────────────────────
@pytest.mark.req("routing-disambiguation:3.1")
def test_module_imports_are_pure_stdlib_only():
    tree = ast.parse(_source())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= ALLOWED_IMPORTS, \
        f"抽取器引入了 {imported - ALLOWED_IMPORTS}——零相依零 IO 的宣稱不再成立"


@pytest.mark.req("routing-disambiguation:2.3")
def test_module_never_mentions_similarity():
    # 註解中說明「不讀相似度」是允許的，故只檢查**程式碼識別字**（AST，不含字串與註解）
    tree = ast.parse(_source())
    code_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    code_names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    hits = [t for t in FORBIDDEN_TOKENS if any(t in name.lower() for name in code_names)]
    assert not hits, f"程式碼識別字中出現相似度相關字樣 {hits}——與相似度正交的宣稱破了"
    # ⚠️ 延後 import（函式內 import）不另設檢查：上一條的 AST walk 已涵蓋任意位置的 import。


@pytest.mark.req("routing-disambiguation:3.1")
def test_extract_performs_no_io(monkeypatch):
    """把 IO 入口全部改成拋出，抽取器仍須正常運作。"""
    import builtins
    import socket

    monkeypatch.setattr(builtins, "open", lambda *a, **k: pytest.fail("抽取器讀了檔案"))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("抽取器開了 socket"))
    e = _x().extract("我的這張點退帳單金額怎麼算出來的")
    assert e.positive


@pytest.mark.req("routing-disambiguation:3.4")
def test_extract_signature_takes_only_the_question():
    """抽取器**只**吃問句——沒有參數可以把分數餵進來。"""
    import inspect
    from services.instance_evidence import InstanceEvidenceExtractor
    params = list(inspect.signature(InstanceEvidenceExtractor.extract).parameters)
    assert params == ["self", "question"], f"extract 的參數為 {params}——多出來的參數就是分數的入口"


# ── 決定性 ────────────────────────────────────────────
@pytest.mark.req("routing-disambiguation:3.1")
@pytest.mark.parametrize("q", ["我的這張點退帳單金額怎麼算出來的", "點退帳單的金額是怎麼算的",
                               "我要查帳單 編號 12345", ""])
def test_extract_is_deterministic_across_runs_and_instances(q):
    first = _x().extract(q)
    for _ in range(20):
        assert _x().extract(q) == first


# ── immutability ─────────────────────────────────────
@pytest.mark.req("routing-disambiguation:2.1")
def test_evidence_is_truly_immutable():
    e = _x().extract("我的這張帳單 編號 12345")
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.positive = frozenset()
    assert isinstance(e.spans, tuple) and isinstance(e.positive, frozenset) \
        and isinstance(e.counter, frozenset)
    with pytest.raises(TypeError):
        e.spans[0] = ("x", "y")          # ⚠️ frozen=True 只凍欄位綁定，容器本身也必須不可變


@pytest.mark.req("routing-disambiguation:2.1")
def test_spans_only_hold_matched_substrings():
    q = "我的這張點退帳單 編號 12345 怎麼算的"
    e = _x().extract(q)
    assert e.spans, "有證據卻沒有 spans——可稽核性沒有落地"
    for kind, span in e.spans:
        assert span in q, f"span {span!r} 不在原文中——spans 不是命中片段而是別的東西"
        assert kind in (e.positive | e.counter), f"span 標的 {kind} 不在證據集合內"


# ── identifier 同步守門：behavioral equivalence ──────────
def _ie_identifier(text):
    for kind, span in _x().extract(text).spans:
        if kind == "identifier":
            return span
    return None


@pytest.mark.req("routing-disambiguation:2.1")
@pytest.mark.parametrize("text,why", IDENTIFIER_MATRIX,
                         ids=[w for _, w in IDENTIFIER_MATRIX])
def test_identifier_extraction_matches_the_engine_convention(text, why):
    """兩側對「是不是 identifier、抽到哪一段」**逐筆同判**。

    ⚠️ 比的是**行為**不是 regex 字串：字串相等只證明兩行字一樣，
    證明不了 flags／邊界／日期排除／整句上下限在兩邊同樣生效。
    """
    from services.conversational_engine import _extract_identifier
    assert _ie_identifier(text) == _extract_identifier(text), \
        f"identifier 判定漂移（{why}）：輸入 {text!r}"
