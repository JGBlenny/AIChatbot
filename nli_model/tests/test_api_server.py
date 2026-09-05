"""unit：`nli_model/scripts/api_server.py` 的 handler 與 canary 邏輯（DSP-033）。

⛔ **不載真模型、不觸網**：全部用假 tokenizer／假 model／假 torch 物件。
真模型的自證是**容器啟動時的 canary**（r18 F-6），那是 integration 層的事；
本檔驗的是「canary 這把尺本身會不會咬」與「錯誤回應會不會回吐原文」。

執行（rag-orchestrator 測試容器內；本目錄不在 tests/unit/agent/ 之下，
⛔ 不會被 `run-tests.sh unit tests/unit/agent/` 帶到，要另外指定）：
    docker compose -f docker-compose.dev.yml run --rm \\
      -e PYTHONPATH=/nli_model/scripts rag-orchestrator \\
      python3 -m pytest /nli_model/tests/test_api_server.py -q
"""
import contextlib
import json
import os
import sys
from pathlib import Path

import pytest

_NLI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_NLI_ROOT / "scripts"))

import api_server  # noqa: E402

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- 假物件

class _FakeTokenizer:
    """`num_special_tokens_to_add`／`encode`／`__call__` 三個真 tokenizer 介面。

    切詞規則：一個字元一個 token（中文近似），⛔ 不引 transformers。
    """

    def num_special_tokens_to_add(self, pair=False):
        return 3 if pair else 2

    def encode(self, text, add_special_tokens=True):
        return list(range(len(text) + (2 if add_special_tokens else 0)))

    def __call__(self, premise, hypothesis, **kwargs):
        return {"input_ids": [[0] * (len(premise) + len(hypothesis))]}


class _FakeModel:
    """呼叫即回固定 logits；`config.id2label` 決定 ENTAILMENT 在第幾格。"""

    class _Config:
        id2label = {0: "CONTRADICTION", 1: "NEUTRAL", 2: "ENTAILMENT"}

    def __init__(self, probs):
        self.config = self._Config()
        self._probs = list(probs)

    def __call__(self, **enc):
        return type("R", (), {"logits": _FakeLogits(self._probs)})()


class _FakeLogits:
    def __init__(self, probs):
        self.probs = probs


class _FakeTorch:
    """只實作 `no_grad`／`softmax` 兩個本檔用到的 API。"""

    @staticmethod
    @contextlib.contextmanager
    def no_grad():
        yield

    @staticmethod
    def softmax(logits, dim=-1):
        return [[_FakeScalar(p) for p in logits.probs]]


class _FakeScalar:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


# ---------------------------------------------------------------- entailment_index

def test_entailment_index_reads_id2label():
    assert api_server.entailment_index({0: "CONTRADICTION", 1: "NEUTRAL", 2: "ENTAILMENT"}) == 2
    # 正對照：**順序不同的權重**必須算出不同的索引，⛔ 不得寫死 2
    assert api_server.entailment_index({0: "ENTAILMENT", 1: "NEUTRAL", 2: "CONTRADICTION"}) == 0
    assert api_server.entailment_index({"0": "neutral", "1": "entailment"}) == 1


@pytest.mark.parametrize("bad", [{}, {0: "NEUTRAL"}, None, [], "ENTAILMENT"])
def test_entailment_index_raises_instead_of_defaulting(bad):
    """🔴 找不到 ENTAILMENT ⇒ raise。⛔ 不得預設 2——那會把『矛盾』的機率
    當成『蘊涵』回報，而失敗方向是放行捏造且毫無徵兆。"""
    with pytest.raises(ValueError):
        api_server.entailment_index(bad)


# ---------------------------------------------------------------- hypothesis 長度

def test_hypothesis_too_long_boundary():
    n_special = 3
    limit = api_server.MAX_LENGTH - n_special
    assert api_server.hypothesis_too_long(limit, n_special) is False
    assert api_server.hypothesis_too_long(limit + 1, n_special) is True


def test_score_pair_rejects_over_long_hypothesis_instead_of_truncating(monkeypatch):
    """r18 F-8：hypothesis 超長 ⇒ 回錯誤碼，⛔ 不截斷後硬算一個分數出來。"""
    monkeypatch.setitem(api_server.STATE, "tokenizer", _FakeTokenizer())
    monkeypatch.setitem(api_server.STATE, "model", _FakeModel([0.1, 0.2, 0.7]))
    monkeypatch.setitem(api_server.STATE, "torch", _FakeTorch())
    monkeypatch.setitem(api_server.STATE, "entail_idx", 2)

    long_hyp = "字" * (api_server.MAX_LENGTH + 10)
    score, err = api_server._score_pair_sync("前提。", long_hyp)
    assert score is None
    assert err == api_server.ERR_HYPOTHESIS_TOO_LONG

    # 正對照：同一組假物件下，正常長度的句對算得出分數——否則上面那條
    # 什麼都沒證明（可能只是整條路徑都壞了）。
    ok_score, ok_err = api_server._score_pair_sync("前提。", "假設。")
    assert ok_err is None and isinstance(ok_score, float)


def test_score_is_rounded_to_four_decimals(monkeypatch):
    """P2-5 決定性：四捨五入到 4 位**之後**才與 τ 比較。"""
    monkeypatch.setitem(api_server.STATE, "tokenizer", _FakeTokenizer())
    monkeypatch.setitem(api_server.STATE, "model", _FakeModel([0.1, 0.2, 0.401239999]))
    monkeypatch.setitem(api_server.STATE, "torch", _FakeTorch())
    monkeypatch.setitem(api_server.STATE, "entail_idx", 2)

    score, err = api_server._score_pair_sync("前提。", "假設。")
    assert err is None
    assert score == 0.4012


def test_entail_index_selects_which_logit_is_reported(monkeypatch):
    """正對照：換一格 `entail_idx` 就回另一個機率——證明它真的被用上，
    ⛔ 不是一路寫死第 2 格。"""
    monkeypatch.setitem(api_server.STATE, "tokenizer", _FakeTokenizer())
    monkeypatch.setitem(api_server.STATE, "model", _FakeModel([0.11, 0.22, 0.67]))
    monkeypatch.setitem(api_server.STATE, "torch", _FakeTorch())
    monkeypatch.setitem(api_server.STATE, "entail_idx", 2)
    assert api_server._score_pair_sync("p", "h")[0] == 0.67
    monkeypatch.setitem(api_server.STATE, "entail_idx", 0)
    assert api_server._score_pair_sync("p", "h")[0] == 0.11


# ---------------------------------------------------------------- canary

def _shipped_canary() -> dict:
    return json.loads((_NLI_ROOT / "canary.json").read_text(encoding="utf-8"))


def test_shipped_canary_has_three_fabrications_and_two_grounded():
    """正對照：出貨的 canary 真的是 DSP-033 說的那五句，⛔ 不是空表。
    空表在 `evaluate_canary` 下會「通過」（0==0），那是最糟的假綠。"""
    canary = _shipped_canary()
    assert len(canary["fabrications"]) == 3
    assert len(canary["grounded"]) == 2
    assert canary["tau"] == 0.4
    assert canary["expect"]["fabrications_below_tau"] == 1     # F-1 裁定 (a)：1/3
    assert canary["expect"]["grounded_below_tau"] == 0


def test_canary_pairs_order_is_fabrications_then_grounded():
    canary = _shipped_canary()
    pairs = api_server.canary_pairs(canary)
    assert len(pairs) == 5
    assert pairs[0][1] == canary["fabrications"][0]["hypothesis"]
    assert pairs[3][1] == canary["grounded"][0]["hypothesis"]


def test_evaluate_canary_matches_dsp033_observed_scores():
    """DSP-033 F-1 實測：三捏造句 p_ent 0.92／0.44／0.36，τ=0.40 ⇒ 恰 1/3 低於 τ。"""
    ok, detail = api_server.evaluate_canary(
        _shipped_canary(), [0.92, 0.44, 0.36, 0.98, 0.95])
    assert ok is True, detail


@pytest.mark.parametrize(
    "scores,why",
    [
        ([0.92, 0.44, 0.90, 0.98, 0.95], "三句都沒抓到（換了把更鬆的尺）"),
        ([0.92, 0.10, 0.36, 0.98, 0.95], "抓到 2/3（換了把更嚴的尺）"),
        ([0.92, 0.44, 0.36, 0.30, 0.95], "有據句被判無據（誤殺）"),
        ([0.92, 0.44, 0.36, 0.98], "分數數量不符"),
        ([0.92, 0.44, None, 0.98, 0.95], "有一對算不出來"),
    ],
)
def test_evaluate_canary_rejects_a_different_ruler(scores, why):
    """尺自證要會咬：分數分佈只要偏離凍結的觀測結果就不通過。
    ⛔ 期望值不得為了讓新權重過關而被調整——那是宣稱換了尺卻說沒換。"""
    ok, _ = api_server.evaluate_canary(_shipped_canary(), scores)
    assert ok is False, why


def test_evaluate_canary_does_not_treat_missing_score_as_pass():
    """『這一對沒算到』⛔ 不得與『這一對符合期望』同一個結論。"""
    ok, detail = api_server.evaluate_canary(
        _shipped_canary(), [None, None, None, None, None])
    assert ok is False
    assert detail == "score_missing"


# ---------------------------------------------------------------- ready / handlers

@pytest.mark.parametrize(
    "canary_ok,sha_ok,expected",
    [(True, True, True), (True, False, False), (False, True, False), (False, False, False)],
)
def test_ready_requires_both_canary_and_fingerprint(monkeypatch, canary_ok, sha_ok, expected):
    """`nli_ready = canary_ok and sha_ok`——指紋沒過但 canary 過，仍然不 ready。"""
    monkeypatch.setitem(api_server.STATE, "canary_ok", canary_ok)
    monkeypatch.setitem(api_server.STATE, "sha_ok", sha_ok)
    assert api_server._ready() is expected


def _client():
    from fastapi.testclient import TestClient

    # ⚠️ 不觸發 startup（那會載真模型）：TestClient 的 context manager 才跑
    # lifespan，這裡刻意直接建構。
    return TestClient(api_server.app)


def test_health_returns_exactly_three_fields(monkeypatch):
    monkeypatch.setitem(api_server.STATE, "canary_ok", True)
    monkeypatch.setitem(api_server.STATE, "sha_ok", True)
    monkeypatch.setitem(api_server.STATE, "model_sha", "a" * 64)
    body = _client().get("/health").json()
    assert set(body) == {"nli_ready", "model_sha", "canary_ok"}
    assert body == {"nli_ready": True, "model_sha": "a" * 64, "canary_ok": True}


def test_nli_returns_503_when_not_ready(monkeypatch):
    """⛔ 未就緒不得算出分數——orchestrator 端要的是明確的降級訊號。"""
    monkeypatch.setitem(api_server.STATE, "canary_ok", False)
    monkeypatch.setitem(api_server.STATE, "sha_ok", True)
    resp = _client().post("/nli", json={"pairs": [{"premise": "a", "hypothesis": "b"}]})
    assert resp.status_code == 503
    assert resp.json() == {"error": "not_ready"}


def test_validation_error_body_does_not_echo_input(monkeypatch):
    """r18 F-12：422 只回代碼。pydantic 預設 body 會把送進來的欄位值原樣回吐，
    而送進來的正是使用者問句與知識庫原文。"""
    monkeypatch.setitem(api_server.STATE, "canary_ok", True)
    monkeypatch.setitem(api_server.STATE, "sha_ok", True)
    secret = "租客的身分證字號是 A123456789"
    resp = _client().post("/nli", json={"pairs": [{"premise": secret}]})
    assert resp.status_code == 422
    assert resp.json() == {"error": "invalid_request"}
    assert secret not in resp.text


def test_nli_scores_are_per_pair_and_carry_model_sha(monkeypatch):
    """逐對推論（P2-5）＋回應帶 `model_sha`（可稽核：verdict 要能重算）。"""
    monkeypatch.setitem(api_server.STATE, "canary_ok", True)
    monkeypatch.setitem(api_server.STATE, "sha_ok", True)
    monkeypatch.setitem(api_server.STATE, "model_sha", "b" * 64)
    monkeypatch.setitem(api_server.STATE, "tau", 0.4)
    calls = []

    def _fake_score_all(pairs):
        calls.append(list(pairs))
        return [0.9, {"error": api_server.ERR_HYPOTHESIS_TOO_LONG}]

    monkeypatch.setattr(api_server, "_score_all_sync", _fake_score_all)
    resp = _client().post("/nli", json={"pairs": [
        {"premise": "p1", "hypothesis": "h1"},
        {"premise": "p2", "hypothesis": "h2"},
    ]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scores"] == [0.9, {"error": "hypothesis_too_long"}]
    assert body["model_sha"] == "b" * 64
    assert body["tau_hint"] == 0.4
    assert calls == [[("p1", "h1"), ("p2", "h2")]]


def test_fingerprint_unset_expectation_is_not_ready(monkeypatch, tmp_path):
    """P2-10：期望指紋沒烤進映像 ⇒ `sha_ok=False`。
    ⛔ 不得視為「沒設定所以跳過」——忘記傳 build-arg 的映像正是要擋的那一種。"""
    from model_fingerprint import INCLUDED_FILES

    for name in INCLUDED_FILES:
        (tmp_path / name).write_bytes(b"x")
    monkeypatch.setattr(api_server, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(api_server, "EXPECTED_MODEL_SHA", "")
    monkeypatch.setitem(api_server.STATE, "sha_ok", True)   # 先設成 True 才驗得出被改掉
    api_server._verify_fingerprint()
    assert api_server.STATE["sha_ok"] is False
    assert len(api_server.STATE["model_sha"]) == 64

    # 正對照：把實得值當期望值傳回去就會過——證明上面不是「永遠 False」。
    monkeypatch.setattr(api_server, "EXPECTED_MODEL_SHA", api_server.STATE["model_sha"])
    api_server._verify_fingerprint()
    assert api_server.STATE["sha_ok"] is True


def test_directory_fingerprint_raises_on_missing_file(tmp_path):
    """🔴 少一個檔 ⛔ 不得算出「看起來正常」的指紋。"""
    from model_fingerprint import INCLUDED_FILES, directory_fingerprint

    for name in INCLUDED_FILES[:-1]:
        (tmp_path / name).write_bytes(b"x")
    with pytest.raises(FileNotFoundError):
        directory_fingerprint(str(tmp_path))
    # 正對照：補齊就算得出來
    (tmp_path / INCLUDED_FILES[-1]).write_bytes(b"x")
    assert len(directory_fingerprint(str(tmp_path))) == 64


def test_directory_fingerprint_changes_when_config_changes(tmp_path):
    """F-7：指紋要涵蓋 `config.json`／`vocab.txt`——只釘權重等於門框可以換。"""
    from model_fingerprint import INCLUDED_FILES, directory_fingerprint

    for name in INCLUDED_FILES:
        (tmp_path / name).write_bytes(b"x")
    before = directory_fingerprint(str(tmp_path))
    (tmp_path / "config.json").write_bytes(b"y")
    assert directory_fingerprint(str(tmp_path)) != before


def test_download_model_rejects_branch_names_as_revision(monkeypatch):
    """revision ⛔ 不接受分支或 tag（兩者都會移動）。"""
    import download_model

    monkeypatch.setenv("NLI_MODEL_REVISION", "main")
    assert download_model.main() == 1
    assert len(download_model.DEFAULT_REVISION) == 40


def test_api_server_does_not_import_torch_at_module_level():
    """`api_server` 在模組層 import torch 的話，這整份測試就只能在 nli-model
    映像裡跑——也就等於不會被跑。用 AST 直接驗，⛔ 不靠 `sys.modules` 猜
    （別的測試可能已經把 torch 載進來了）。"""
    import ast

    src = (_NLI_ROOT / "scripts" / "api_server.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    top_level_imports = set()
    for node in tree.body:                      # ⚠️ 只看**頂層**，函式內 import 是刻意的
        if isinstance(node, ast.Import):
            top_level_imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.add(node.module.split(".")[0])
    assert "torch" not in top_level_imports
    assert "transformers" not in top_level_imports
    # 正對照：頂層確實有 import 東西（否則上面兩條在空集合上也會過）
    assert "fastapi" in top_level_imports
