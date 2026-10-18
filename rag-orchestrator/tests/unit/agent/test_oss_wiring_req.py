"""unit：主線第 1 步「正式接線（本地替換 gpt-oss）」（`plan-oss-wiring-step1-20261018.md` §3.4）。

覆蓋：
- `services.agent.llm_output` 清理器：合成樣本形狀取自第 0 步 Q5 與已存 Bedrock 原始輸出
  （推理段＋JSON、前綴「以下」、後綴雜字、多段推理、未閉合推理、去標籤後為空、灌空白、
  推理段內含 JSON 樣字串）——⛔ 原文（題目與回答不進 git）。
- 開關關閉（`clean_llm_output=False`＝正式機現況）：「解析失敗但可擷取」仍走 SCHEMA 改寫、
  「可解析且含字面 `<reasoning>`」原樣不動、不出現兩個新旗標。
- 開關開啟：推理不進下一次取樣的 messages（含工具呼叫訊息——Q3：Bedrock 不收推理欄位）；
  改寫時照 DSP-022 斷言最後一則 user 訊息。
- 價目：`openai.gpt-oss-120b-1:0` 依 Q6 單價計價。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from services import usage_metering
from services.agent import llm_output as LO
from services.agent.budget import Budget
from services.agent.runtime import (
    LLM_OUTPUT_JSON_EXTRACTED,
    LLM_OUTPUT_REASONING_STRIPPED,
    AgentRuntime,
    rewrite_feedback,
)
from services.agent.tools.registry import ToolResult
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _fake_message,
    _fake_response,
    _identity,
    _tool_call_response,
)

pytestmark = pytest.mark.unit

_NEW_FLAGS = {LLM_OUTPUT_REASONING_STRIPPED, LLM_OUTPUT_JSON_EXTRACTED}
_SCHEMA_FEEDBACK = rewrite_feedback("SCHEMA", "輸出不符 AgentOutput schema。")


def _payload(text: str = "答案內容") -> dict:
    return {
        "kind": "answer",
        "sentences": [{"text": text, "kind": "greeting", "refs": []}],
        "fact_class": "feature",
        "handoff_reason": None,
    }


def _clean_json(text: str = "答案內容") -> str:
    return json.dumps(_payload(text), ensure_ascii=False)


def _content_response(content: str, *, finish_reason=None):
    resp = _fake_response(_fake_message(content=content))
    if finish_reason is not None:
        resp.choices[0].finish_reason = finish_reason
    return resp


def _runtime(provider, *, clean: bool, registry=None, budget=None) -> AgentRuntime:
    return AgentRuntime(
        provider,
        registry or FakeRegistry(),
        FakeVerifier(),
        FakeAssembler(),
        budget or Budget(),
        stage="M1",
        clock=FakeClock(),
        clean_llm_output=clean,
    )


def _last_user(messages: list) -> dict:
    return [m for m in messages if m.get("role") == "user"][-1]


# ---------------------------------------------------------------------------
# 1. 清理器（純函式）
# ---------------------------------------------------------------------------


def test_has_reasoning_detects_either_tag_and_ignores_non_str():
    assert LO.has_reasoning("<reasoning>x</reasoning>{}")
    assert LO.has_reasoning("x</reasoning>{}")          # 開頭標籤被截掉的形狀
    assert LO.has_reasoning("<reasoning>沒收尾")
    assert not LO.has_reasoning(_clean_json())
    assert not LO.has_reasoning(None)
    assert not LO.has_reasoning(["<reasoning>"])


def test_final_segment_shapes():
    body = _clean_json()
    # Q5 主形狀：恰一對標籤、前綴為空
    assert LO.final_segment(f"<reasoning>想一下</reasoning>{body}") == body
    # 多段推理 ⇒ 取最後一個 `</reasoning>` 之後
    assert LO.final_segment(f"<reasoning>a</reasoning>中間<reasoning>b</reasoning>{body}") == body
    # 沒有標籤 ⇒ 原文
    assert LO.final_segment(body) == body
    # 有開頭沒收尾 ⇒ 沒有最終段
    assert LO.final_segment("<reasoning>想到一半被截") is None
    # 去標籤後為空（只有推理、stop）
    assert LO.final_segment("<reasoning>只有推理</reasoning>") == ""
    assert LO.final_segment(None) is None


def test_iter_json_objects_tolerates_prefix_suffix_and_skips_nested():
    body = _clean_json()
    objs = list(LO.iter_json_objects(f"以下{body}\n謝謝"))
    assert objs == [_payload()]                          # 巢狀的 sentences 物件不另算
    two = list(LO.iter_json_objects('{"a": 1} 雜字 {"b": {"c": 2}}'))
    assert two == [{"a": 1}, {"b": {"c": 2}}]
    assert list(LO.iter_json_objects("沒有任何 JSON")) == []


def test_whitespace_flood_yields_nothing():
    # Q5 的 length 那筆：JSON 中段起灌空白至上限 ⇒ 擷取不到（截斷屬第 3 步）
    flood = '{"kind": "answer", "sentences": [' + " " * 5000
    assert list(LO.iter_json_objects(LO.final_segment(f"<reasoning>x</reasoning>{flood}"))) == []


def test_json_like_text_inside_reasoning_is_not_taken():
    decoy = json.dumps(_payload("推理裡的誘餌"), ensure_ascii=False)
    content = f"<reasoning>草稿 {decoy}</reasoning>{_clean_json('真正的答案')}"
    objs = list(LO.iter_json_objects(LO.final_segment(content)))
    assert objs == [_payload("真正的答案")]


# ---------------------------------------------------------------------------
# 2. 開關關閉（正式機現況）：行為與改前相同
# ---------------------------------------------------------------------------


async def test_off_switch_extractable_output_still_takes_schema_rewrite():
    noisy = "以下" + _clean_json("第一次")
    provider = FakeProvider([_content_response(noisy), _content_response(_clean_json("第二次"))])
    runtime = _runtime(provider, clean=False)

    result = await runtime.run_turn(_identity(), "這個系統怎麼用呢", {})

    assert result.answer == "第二次"
    assert result.trace.llm_calls == 2
    second = provider.calls[1]["messages"]
    # 改寫路徑 append 的是原文（含前綴），最後一則 user 是 SCHEMA 回饋（DSP-022）
    assert second[-2] == {"role": "assistant", "content": noisy}
    assert _last_user(second) == {"role": "user", "content": _SCHEMA_FEEDBACK}
    assert not (_NEW_FLAGS & set(result.trace.violations))


async def test_off_switch_reasoning_wrapped_output_is_not_cleaned():
    raw = f"<reasoning>想一下</reasoning>{_clean_json('第一次')}"
    provider = FakeProvider([_content_response(raw), _content_response(_clean_json("第二次"))])
    runtime = _runtime(provider, clean=False)

    result = await runtime.run_turn(_identity(), "這個系統怎麼用呢", {})

    assert result.answer == "第二次"
    assert provider.calls[1]["messages"][-2] == {"role": "assistant", "content": raw}
    assert not (_NEW_FLAGS & set(result.trace.violations))


async def test_off_switch_parseable_output_with_literal_tag_untouched():
    text = "請在欄位填入 <reasoning> 這個字樣"
    provider = FakeProvider([_content_response(_clean_json(text))])
    runtime = _runtime(provider, clean=False)

    result = await runtime.run_turn(_identity(), "這個欄位要填什麼", {})

    assert result.answer == text
    assert result.trace.llm_calls == 1
    assert not (_NEW_FLAGS & set(result.trace.violations))


# ---------------------------------------------------------------------------
# 3. 開關開啟（本機接 Bedrock）
# ---------------------------------------------------------------------------


async def test_on_switch_reasoning_wrapped_final_passes_in_one_call():
    raw = f"<reasoning>想一下 {_clean_json('誘餌')}</reasoning>以下{_clean_json('正確答案')}\n"
    provider = FakeProvider([_content_response(raw)])
    runtime = _runtime(provider, clean=True)

    result = await runtime.run_turn(_identity(), "這個系統怎麼用呢", {})

    assert result.kind == "answer"
    assert result.answer == "正確答案"
    assert result.trace.llm_calls == 1
    assert LLM_OUTPUT_REASONING_STRIPPED in result.trace.violations
    assert LLM_OUTPUT_JSON_EXTRACTED in result.trace.violations


async def test_on_switch_clean_output_records_no_flags():
    provider = FakeProvider([_content_response(_clean_json("乾淨輸出"))])
    runtime = _runtime(provider, clean=True)

    result = await runtime.run_turn(_identity(), "這個系統怎麼用呢", {})

    assert result.answer == "乾淨輸出"
    assert not (_NEW_FLAGS & set(result.trace.violations))


async def test_on_switch_unparseable_rewrite_sends_no_reasoning():
    raw = "<reasoning>這段推理不能回送</reasoning>抱歉沒有 JSON"
    provider = FakeProvider([_content_response(raw), _content_response(_clean_json("改寫後"))])
    runtime = _runtime(provider, clean=True)

    result = await runtime.run_turn(_identity(), "這個系統怎麼用呢", {})

    assert result.answer == "改寫後"
    second = provider.calls[1]["messages"]
    assert second[-2] == {"role": "assistant", "content": "抱歉沒有 JSON"}
    assert _last_user(second) == {"role": "user", "content": _SCHEMA_FEEDBACK}
    assert "<reasoning" not in json.dumps(second, ensure_ascii=False)
    assert LLM_OUTPUT_REASONING_STRIPPED in result.trace.violations
    assert LLM_OUTPUT_JSON_EXTRACTED not in result.trace.violations


async def test_on_switch_unclosed_reasoning_becomes_empty_and_rewrites():
    provider = FakeProvider([
        _content_response("<reasoning>想到一半被截", finish_reason="length"),
        _content_response(_clean_json("改寫後")),
    ])
    runtime = _runtime(provider, clean=True)

    result = await runtime.run_turn(_identity(), "這個系統怎麼用呢", {})

    assert result.answer == "改寫後"
    second = provider.calls[1]["messages"]
    assert second[-2] == {"role": "assistant", "content": ""}
    assert _last_user(second) == {"role": "user", "content": _SCHEMA_FEEDBACK}
    assert "<reasoning" not in json.dumps(second, ensure_ascii=False)


async def test_on_switch_tool_call_message_is_stripped_too():
    tool_resp = _tool_call_response("kb.get", {"kb_id": "3600"})
    tool_resp.choices[0].message.content = "<reasoning>先查知識</reasoning>"
    provider = FakeProvider([tool_resp, _content_response(_clean_json("查完回答"))])
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"id": 3600}, text_for_model="知識原文")]
    )
    runtime = _runtime(provider, clean=True, registry=registry)

    result = await runtime.run_turn(_identity(), "我要找一下帳單", {})

    assert result.answer == "查完回答"
    second = provider.calls[1]["messages"]
    assert second[-1]["role"] == "tool"
    assistant_tool = [m for m in second if m.get("role") == "assistant" and m.get("tool_calls")]
    assert assistant_tool and assistant_tool[-1]["content"] == ""
    assert "<reasoning" not in json.dumps(second, ensure_ascii=False)
    assert "我要找一下帳單" in _last_user(second)["content"]   # DSP-022：最後一則 user 仍是本回合提問


# ---------------------------------------------------------------------------
# 4. 價目（清單 #7）
# ---------------------------------------------------------------------------


def test_gpt_oss_pricing_from_q6(monkeypatch):
    monkeypatch.delenv("LLM_PRICING_PATH", raising=False)
    assert usage_metering.DEFAULT_PRICING["openai.gpt-oss-120b-1:0"] == (0.18, 0.73)
    ctx = usage_metering.UsageContext(request_id="r", ts=datetime.now(timezone.utc))
    ctx.model_breakdown = {"openai.gpt-oss-120b-1:0": {"calls": 1, "pt": 1_000_000, "ct": 1_000_000}}
    usage_metering._compute_cost(ctx)
    assert ctx.est_cost_usd == Decimal("0.910000")
    # 正對照：缺價模型 ⇒ 整筆留空（R2.4，既有行為不變）
    ctx.model_breakdown["unknown-model"] = {"calls": 1, "pt": 1, "ct": 1}
    usage_metering._compute_cost(ctx)
    assert ctx.est_cost_usd is None


# ---------------------------------------------------------------------------
# 5. 對話端點與金鑰（§3.1；§5 F1／F5／F6）
# ---------------------------------------------------------------------------

_BEDROCK = "https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1"
_FAKE_KEY = "fake-key-ABCdef0123456789+/=._~"


def _agent_env(monkeypatch, *, base=None, key_file=None):
    from services import llm_provider as P
    for name in (P.AGENT_LLM_BASE_URL_ENV, P.AGENT_LLM_API_KEY_FILE_ENV, "OPENAI_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    if base is not None:
        monkeypatch.setenv(P.AGENT_LLM_BASE_URL_ENV, base)
    if key_file is not None:
        monkeypatch.setenv(P.AGENT_LLM_API_KEY_FILE_ENV, str(key_file))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-default-should-not-move")
    return P


def test_agent_provider_none_when_both_unset(monkeypatch):
    P = _agent_env(monkeypatch)
    assert P.build_agent_provider_from_env() is None
    assert P.agent_endpoint_configured() is False


@pytest.mark.parametrize("which", ["base_only", "key_only"])
def test_agent_provider_half_config_raises(monkeypatch, tmp_path, which):
    kf = tmp_path / "k"; kf.write_text(_FAKE_KEY + "\n")
    P = _agent_env(monkeypatch, base=_BEDROCK if which == "base_only" else None,
                   key_file=kf if which == "key_only" else None)
    with pytest.raises(P.AgentLLMConfigError) as ei:
        P.build_agent_provider_from_env()
    assert ei.value.code == "agent_llm_config_incomplete"


@pytest.mark.parametrize("content,code", [
    ("", "agent_llm_key_file_empty"),
    ("   \n", "agent_llm_key_file_empty"),
    ("SECRETa\nSECRETb\n", "agent_llm_key_file_multiline"),
    ("SECRETa\rSECRETb", "agent_llm_key_file_multiline"),
    ("SECRET with space", "agent_llm_key_file_invalid_charset"),
    ("SECRET#bad", "agent_llm_key_file_invalid_charset"),
    ("SECRET金鑰", "agent_llm_key_file_invalid_charset"),
])
def test_bad_key_file_raises_without_content(monkeypatch, tmp_path, content, code):
    kf = tmp_path / "k"; kf.write_bytes(content.encode("utf-8"))
    P = _agent_env(monkeypatch, base=_BEDROCK, key_file=kf)
    with pytest.raises(P.AgentLLMConfigError) as ei:
        P.build_agent_provider_from_env()
    assert ei.value.code == code
    assert "SECRET" not in str(ei.value) and ei.value.__context__ is None


def test_missing_key_file_raises(monkeypatch, tmp_path):
    P = _agent_env(monkeypatch, base=_BEDROCK, key_file=tmp_path / "nope")
    with pytest.raises(P.AgentLLMConfigError) as ei:
        P.build_agent_provider_from_env()
    assert ei.value.code == "agent_llm_key_file_missing"


def test_openai_base_url_conflict_raises(monkeypatch, tmp_path):
    kf = tmp_path / "k"; kf.write_text(_FAKE_KEY)
    P = _agent_env(monkeypatch, base=_BEDROCK, key_file=kf)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    with pytest.raises(P.AgentLLMConfigError) as ei:
        P.build_agent_provider_from_env()
    assert ei.value.code == "agent_llm_openai_base_url_conflict"


@pytest.mark.parametrize("key", [None, "", "   "])
def test_provider_with_base_url_requires_explicit_key(monkeypatch, key):
    P = _agent_env(monkeypatch)
    with pytest.raises(ValueError):
        P.OpenAIProvider(api_key=key, base_url=_BEDROCK)


def test_agent_provider_configured_is_separate_from_cache(monkeypatch, tmp_path):
    kf = tmp_path / "k"; kf.write_text(_FAKE_KEY + "\n")
    P = _agent_env(monkeypatch, base=_BEDROCK, key_file=kf)
    default = P.get_llm_provider()
    agent = P.build_agent_provider_from_env()
    assert agent is not None and agent is not default
    assert agent not in P._provider_cache.values()
    assert P.get_llm_provider() is default
    assert agent.async_client.base_url.host == "bedrock-runtime.ap-northeast-1.amazonaws.com"
    assert agent.api_key == _FAKE_KEY
    assert default.async_client.base_url.host == "api.openai.com"


# ---------------------------------------------------------------------------
# 6. 健康檢查（§3.3；§5 F4）
# ---------------------------------------------------------------------------


def _health_service_with_stubbed_checkers():
    from services.pipeline_health_service import PipelineHealthService
    svc = PipelineHealthService()

    def _stub(name, core):
        async def _c():
            return {"name": name, "status": "healthy", "latency_ms": 0.0, "version": None,
                    "error": None, "is_core": core, "degradation_impact": None}
        return _c
    for attr, name, core in (("_check_db", "PostgreSQL", True), ("_check_redis", "Redis", False),
                             ("_check_embedding", "Embedding API", True), ("_check_reranker", "Reranker", False),
                             ("_check_llm", "LLM API", True), ("_check_vector_search", "Vector Search", False),
                             ("_check_keyword_search", "Keyword Search", False), ("_check_agent", "Agent", False)):
        setattr(svc, attr, _stub(name, core))
    return svc


async def test_health_list_unchanged_when_unset(monkeypatch):
    _agent_env(monkeypatch)
    res = await _health_service_with_stubbed_checkers().check_all_components()
    names = [c["name"] for c in res["components"]]
    assert names == ["PostgreSQL", "Redis", "Embedding API", "Reranker", "LLM API",
                     "Vector Search", "Keyword Search", "Agent"]


async def test_health_adds_agent_llm_when_configured(monkeypatch, tmp_path):
    kf = tmp_path / "k"; kf.write_text(_FAKE_KEY)
    _agent_env(monkeypatch, base=_BEDROCK, key_file=kf)
    res = await _health_service_with_stubbed_checkers().check_all_components()
    comp = [c for c in res["components"] if c["name"] == "Agent LLM Endpoint"]
    assert len(comp) == 1 and comp[0]["status"] == "healthy" and comp[0]["is_core"] is True
    assert comp[0]["version"] == "bedrock-runtime.ap-northeast-1.amazonaws.com"
    assert _FAKE_KEY not in json.dumps(res, ensure_ascii=False, default=str)


async def test_health_error_field_never_carries_exception_text(monkeypatch, tmp_path):
    from services import llm_provider as P
    from services.pipeline_health_service import PipelineHealthService
    kf = tmp_path / "k"; kf.write_text("SECRETbad key")
    _agent_env(monkeypatch, base=_BEDROCK, key_file=kf)
    bad = await PipelineHealthService()._check_agent_llm()
    assert bad["status"] == "unhealthy"
    assert bad["error"] == "agent_llm_config_invalid:AgentLLMConfigError:agent_llm_key_file_invalid_charset"

    def _boom():
        raise RuntimeError("Illegal header value b'Bearer SECRETleak'")
    monkeypatch.setattr(P, "build_agent_provider_from_env", _boom)
    res = await PipelineHealthService()._check_agent_llm()
    assert res["error"] == "agent_llm_check_failed:RuntimeError"
    assert "SECRET" not in json.dumps(res)
