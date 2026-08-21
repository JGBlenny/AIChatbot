"""unit：分數平移探針（R7.2 量測工具｜D-13）。

**為什麼需要真的注入而不是離線重放**：D-01(d) 已規定路由分支不得直讀分數
（AST 不變量釘死），所以「把快照分數 +0.10 再跑一次 decide()」**結構上恆為 0**——
那是假關卡（D-24 記載的作廢教訓：平移不變性驗收對任何分數單調函數恆成立）。
R7.2 必須端到端實跑，把偏移注入**檢索融合出口**（`_finalize_scores`），
讓面向進場 gate 0.75、KB 過濾 0.65、六 case 的 0.15 gap、相關性把關全部看得到。

契約：
- 預設關閉；`shift=0` 必須是**精確 no-op**（否則對照臂資料作廢）；
- 只動 `similarity`（融合出口），不動 vector/keyword/rerank 原始分數；
- 夾在 [0,1]；
- 開啟時必須留下明顯痕跡（防止忘了關而汙染 prod）。
"""
import pytest

from services.base_retriever import BaseRetriever

pytestmark = pytest.mark.unit


class _R(BaseRetriever):
    """最小具體子類：只為取用 _finalize_scores，抽象方法全部留空。"""
    def __init__(self):
        pass
    def retrieve(self, *a, **k):
        return []
    def _vector_search(self, *a, **k):
        return []
    def _keyword_search(self, *a, **k):
        return []
    def _format_result(self, *a, **k):
        return {}


def _rows():
    return [{"vector_similarity": 0.80, "rerank_score": 0.90},
            {"vector_similarity": 0.60, "keyword_score": 0.70, "keyword_boost": 1.0},
            {"vector_similarity": 0.50}]


# ── 預設關閉：shift 未設時分數與原公式逐一相同 ──
@pytest.mark.req("retrieval-decision-layer:7.2")
def test_default_is_exact_noop(monkeypatch):
    monkeypatch.delenv("SCORE_SHIFT_PROBE", raising=False)
    got = _R()._finalize_scores(_rows())
    assert [round(r["similarity"], 10) for r in got] == [0.89, 0.70, 0.50]


# ── shift=0 明設也必須是精確 no-op（對照臂資料的效力靠這條）──
@pytest.mark.req("retrieval-decision-layer:7.2")
def test_explicit_zero_is_exact_noop(monkeypatch):
    monkeypatch.setenv("SCORE_SHIFT_PROBE", "0")
    a = _R()._finalize_scores(_rows())
    monkeypatch.delenv("SCORE_SHIFT_PROBE")
    b = _R()._finalize_scores(_rows())
    assert [r["similarity"] for r in a] == [r["similarity"] for r in b]


# ── 正向平移：只加在 similarity，且夾 1.0 ──
@pytest.mark.req("retrieval-decision-layer:7.2")
def test_positive_shift_applies_and_clamps(monkeypatch):
    monkeypatch.setenv("SCORE_SHIFT_PROBE", "0.10")
    got = _R()._finalize_scores(_rows())
    assert round(got[0]["similarity"], 10) == 0.99
    assert round(got[1]["similarity"], 10) == 0.80
    assert round(got[2]["similarity"], 10) == 0.60
    # 原始分數欄位不得被動到
    assert got[0]["vector_similarity"] == 0.80 and got[0]["rerank_score"] == 0.90


@pytest.mark.req("retrieval-decision-layer:7.2")
def test_shift_clamps_at_one(monkeypatch):
    monkeypatch.setenv("SCORE_SHIFT_PROBE", "0.50")
    got = _R()._finalize_scores([{"vector_similarity": 0.9, "rerank_score": 0.95}])
    assert got[0]["similarity"] == 1.0


# ── 負向平移：夾 0.0 ──
@pytest.mark.req("retrieval-decision-layer:7.2")
def test_negative_shift_clamps_at_zero(monkeypatch):
    monkeypatch.setenv("SCORE_SHIFT_PROBE", "-0.10")
    got = _R()._finalize_scores(_rows())
    assert round(got[0]["similarity"], 10) == 0.79
    assert round(got[2]["similarity"], 10) == 0.40
    got2 = _R()._finalize_scores([{"vector_similarity": 0.05}])
    assert got2[0]["similarity"] == 0.0


# ── 壞值不得靜默生效（避免打錯字變成沒平移卻以為平移了）──
@pytest.mark.req("retrieval-decision-layer:7.2")
@pytest.mark.parametrize("bad", ["abc", "", "0.1x"])
def test_malformed_shift_raises(monkeypatch, bad):
    monkeypatch.setenv("SCORE_SHIFT_PROBE", bad)
    with pytest.raises(ValueError):
        _R()._finalize_scores(_rows())


# ── 開啟時留痕（防忘了關）──
@pytest.mark.req("retrieval-decision-layer:7.2")
def test_enabled_probe_is_loud(monkeypatch, capsys):
    monkeypatch.setenv("SCORE_SHIFT_PROBE", "0.10")
    _R()._finalize_scores(_rows())
    out = capsys.readouterr().out
    assert "SCORE_SHIFT_PROBE" in out and "量測探針" in out
