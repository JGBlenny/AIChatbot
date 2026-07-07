"""unit:售前合成規則抽出——鐵則/CTA 塊從共用 optimizer 硬編移到售前設定（資料驅動）。

問題（與合約鐵則同一把尺）：PRESALES_SYNTH_RULES（不報價/競品/demo 網址/口吻）硬編在共用
`_build_presales_synth` 且**每次合成都附加→合約診斷收斂也吃到售前規則**（反向污染）；
cta_mode=force 的 CTA/排版塊（業務網址）也硬編在程式碼。
修法：①鐵則→售前 config.answer_rules（收斂附加，機制既有）②CTA 塊→config.cta_rules
（新欄位，cta_mode=force 才附加，保留程式決定時機）③code fallback 放 PRESALES_CONFIG
（比照 conversational_rules DB優先+code保底）④optimizer 變真通用。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc
from services.conversational_config import ConversationalConfig, PRESALES_CONFIG
from services.conversational_engine import ConversationalEngine, _synth_context
from services.llm_answer_optimizer import LLMAnswerOptimizer

pytestmark = pytest.mark.unit


# ── 設定解析：metadata.cta_rules → config.cta_rules（未設 None）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_config_parses_cta_rules():
    md = {"conversational_config": {"key": "k", "cta_rules": "CTA 塊"}}
    assert cc._config_from_row(["prospect"], md).cta_rules == "CTA 塊"
    assert cc._config_from_row(["prospect"], {"conversational_config": {"key": "k"}}).cta_rules is None


# ── code fallback：PRESALES_CONFIG 承載售前鐵則與 CTA 塊（DB 未設仍可用）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_presales_code_default_carries_rules():
    ar = PRESALES_CONFIG.answer_rules or ""
    assert "不報價" in ar and "jgbsmart.com/pricing" in ar     # 合成鐵則
    assert "競品" in ar and "demo" in ar
    cr = PRESALES_CONFIG.cta_rules or ""
    assert "下一步" in cr and "jgbsmart.com/demo-form" in cr   # CTA/排版塊


# ── optimizer 變真通用：不再硬編售前鐵則/CTA 塊/業務網址（任何 cta_mode）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_build_presales_synth_is_generic_now():
    opt = LLMAnswerOptimizer(config={}, llm_provider=MagicMock())
    for mode in ("auto", "force", "suppress"):
        messages, _m, _t = opt._build_presales_synth(
            grounding_knowledge="知識", accumulated_context=None,
            system_context_md="SYS", user_question="Q", cta_mode=mode)
        p = "\n".join(m["content"] for m in messages)
        assert "jgbsmart.com" not in p          # 業務網址不再硬編
        assert "合成鐵則" not in p               # 售前鐵則已外移
        assert "不報價" not in p


# ── _synth_context：cta_mode=force 才附加 cta_rules（answer_rules 一律附加）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_synth_context_appends_cta_rules_only_on_force():
    cfg = ConversationalConfig(key="k", answer_rules="AR", cta_rules="CTA")
    assert _synth_context("MD", cfg, cta_mode="force") == "MD\n\nAR\n\nCTA"
    assert _synth_context("MD", cfg, cta_mode="suppress") == "MD\n\nAR"
    assert _synth_context("MD", cfg) == "MD\n\nAR"
    assert _synth_context("MD", ConversationalConfig(key="k")) == "MD"   # 皆未設 → 原樣


# ── 引擎推薦型收斂（cta_mode=force）：decision.system_md 含 cta_rules ──
@pytest.mark.req("domain-conversational-facets:3.2")
async def test_engine_recommend_converge_carries_cta_rules(monkeypatch):
    cfg = ConversationalConfig(key="presales", persona_role="prospect",
                               grounding_scope={"select": "vector", "target_user": "prospect"},
                               answer_rules="AR", cta_rules="CTA")
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="MD"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._converge_grounding = AsyncMock(return_value=("G", [{"field_label": "身分", "selected_label": "房東"}], "force"))
    eng.optimizer.conversational_step = MagicMock(return_value={
        "action": "converge", "converge_kind": "recommend",
        "extracted_fields": {}, "scope": "stay"})
    eng.get_state = AsyncMock(return_value={
        "config_key": "presales", "asked_count": 2,
        "collected_fields": {"identity": "房東", "scale": "30"}})
    import services.conversational_engine as ce
    monkeypatch.setattr(ce, "_domain_faces", AsyncMock(return_value=[]))
    d = await eng.prepare("s", "u", 7, "推薦一下", config=cfg)
    assert d["kind"] == "converge" and d["cta_mode"] == "force"
    assert d["system_md"].endswith("AR\n\nCTA")               # 鐵則+CTA 都附加

    # 事實型（suppress）→ 只附鐵則
    eng._converge_grounding = AsyncMock(return_value=("G", None, "suppress"))
    eng.optimizer.conversational_step = MagicMock(return_value={
        "action": "converge", "converge_kind": "answer", "extracted_fields": {}, "scope": "stay"})
    d2 = await eng.prepare("s", "u", 7, "IoT 怎麼算", config=cfg)
    assert d2["system_md"].endswith("AR") and "CTA" not in d2["system_md"]
