"""unit 層：售前閘門純函式（design.md 元件 1／services/presales_gate.py）。需求 1.2、1.3、2.2、3.2、4.1、4.2。

⛔ 無 I/O、無 LLM；門檻讀值是唯一讀值點；enum 非法一律 other（不猜變體）；三詞掃描是封閉集合。
"""
import pytest

from services import presales_gate as pg
from services.presales_gate import FactClass, Handoff, HandoffReason

pytestmark = pytest.mark.unit


# ── 門檻讀值（R1.2／1.3）──────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:1.2")
def test_threshold_defaults_to_decision_config_kb_threshold(monkeypatch):
    monkeypatch.delenv("PRESALES_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.57")
    assert pg.presales_threshold() == pytest.approx(0.57)


@pytest.mark.req("presales-grounding-gate:1.2")
def test_threshold_env_override_wins(monkeypatch):
    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.55")
    monkeypatch.setenv("PRESALES_GROUNDING_THRESHOLD", "0.65")
    assert pg.presales_threshold() == pytest.approx(0.65)


@pytest.mark.req("presales-grounding-gate:1.2")
@pytest.mark.parametrize("bad", ["abc", "", "1.5", "-0.1", "nan"])
def test_threshold_bad_env_falls_back_and_never_zero(monkeypatch, capsys, bad):
    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.55")
    monkeypatch.setenv("PRESALES_GROUNDING_THRESHOLD", bad)
    t = pg.presales_threshold()
    assert t == pytest.approx(0.55)                                   # ⛔ 不得靜默放寬為 0、不得 raise
    if bad != "":
        assert "PRESALES_GROUNDING_THRESHOLD" in capsys.readouterr().out   # 壞值要大聲


@pytest.mark.req("presales-grounding-gate:1.3")
def test_threshold_is_the_single_read_point():
    """唯一讀值點：程式其他地方 ⛔ 不得自己 getenv 這兩個鍵（此處以符號存在＋回傳型別守；grep 守門在 7.1 突變控制）。"""
    assert callable(pg.presales_threshold) and isinstance(pg.presales_threshold(), float)


# ── fact_class（R3.2）───────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:3.2")
@pytest.mark.parametrize("raw", ["customer_reference", "pricing", "contract_sla", "compliance", "security", "feature", "other"])
def test_parse_fact_class_accepts_exact_enum(raw):
    assert pg.parse_fact_class(raw) is FactClass(raw)


@pytest.mark.req("presales-grounding-gate:3.2")
@pytest.mark.parametrize("raw", ["Pricing", "price", " pricing ", "PRICING", None, 3, {"x": 1}, "", "unknown"])
def test_parse_fact_class_rejects_variants_to_other(raw):
    assert pg.parse_fact_class(raw) is FactClass.other                 # ⛔ 不容忍變體、不做正規化


@pytest.mark.req("presales-grounding-gate:2.2")
def test_sensitive_set_is_exactly_the_five_audit_classes():
    assert pg.SENSITIVE == frozenset({FactClass.customer_reference, FactClass.pricing, FactClass.contract_sla,
                                      FactClass.compliance, FactClass.security})
    assert FactClass.feature not in pg.SENSITIVE and FactClass.other not in pg.SENSITIVE


# ── handoff 建構（R2.2／4.1）────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:4.1")
@pytest.mark.parametrize("fc,reason", [
    (FactClass.customer_reference, HandoffReason.sensitive_no_grounding),
    (FactClass.security, HandoffReason.sensitive_no_grounding),
    (FactClass.feature, HandoffReason.no_grounding),
    (FactClass.other, HandoffReason.no_grounding),
])
def test_build_handoff_reason_follows_sensitivity(fc, reason):
    h = pg.build_handoff(fc, channel="line_official", message="固定句")
    assert isinstance(h, Handoff) and h.reason is reason and h.fact_class is fc
    assert h.channel == "line_official" and h.message == "固定句"


@pytest.mark.req("presales-grounding-gate:2.2")
def test_handoff_message_is_not_rewritten_by_class():
    """固定句一致——⛔ 不因類別改寫成推測性肯定句。"""
    a = pg.build_handoff(FactClass.pricing, channel="c", message="M")
    b = pg.build_handoff(FactClass.feature, channel="c", message="M")
    assert a.message == b.message == "M"


@pytest.mark.req("presales-grounding-gate:4.1")
def test_handoff_to_dict_shape_matches_contract():
    d = pg.build_handoff(FactClass.pricing, channel="c", message="M").to_dict()
    assert set(d) == {"reason", "fact_class", "channel", "message"}
    assert d["reason"] == "sensitive_no_grounding" and d["fact_class"] == "pricing"


# ── 封閉三詞掃描（R4.2）─────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:4.2")
@pytest.mark.parametrize("text", ["建議您直接與我們的專人聯繫", "點下方找真人", "請洽客服處理", "合約的部分這部分我沒有資料。"])
def test_scan_detects_each_closed_word(text):
    assert pg.scan_handoff_mentions(text) is True


@pytest.mark.req("presales-grounding-gate:4.2")
@pytest.mark.parametrize("text", ["", "我們支援電子發票自動開立。", "專業的物業管理", None])
def test_scan_ignores_non_matches_including_near_misses(text):
    assert pg.scan_handoff_mentions(text) is False                      # 「專業」≠「專人」；None 不崩


@pytest.mark.req("presales-grounding-gate:4.2")
def test_handoff_words_are_a_closed_set():
    assert pg.HANDOFF_WORDS == ("專人", "真人", "客服", "沒有資料")       # 改這裡＝改需求，⛔ 不擴成開放語義（第 4 詞是我們自己 prompt 要求的句式）
