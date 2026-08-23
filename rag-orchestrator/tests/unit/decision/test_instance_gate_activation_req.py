"""unit：**啟用狀態**的兩層契約（任務 4.1｜R7.1, R3.5）。

```text
requested  = 旗標被打開（運維意圖）
authorized = 規則集已通過 matching holdout（證據授權）
active     = requested AND authorized
```

⚠️ **不得摺疊成 `flag=true → gate active`**：
Task 6 的 unseen holdout 裁決前，**即使有人把 env 設成 true，也不得真正放行**。
"""
import pytest

pytestmark = pytest.mark.unit

ACTIVE_PROTOCOL_DIGEST = "4690a258f502d98d"


def _m():
    from services import instance_reference_gate as m
    return m


def _authorized_manifest(m):
    """synthetic：三重 digest 相符的已授權 manifest（**僅供測邏輯**）。

    ⚠️ 必須在 monkeypatch **之前**取 base——patch 後再呼叫 `current_manifest()`
    會遞迴進 patch 本身（實測 RecursionError）。
    """
    base = m.current_manifest()
    return m.RulesetManifest(
        version=base.version, positive_patterns=dict(base.positive_patterns),
        counter_patterns=dict(base.counter_patterns), digest=base.digest,
        holdout=m.HoldoutRecord(status="passed", ruleset_digest=base.digest,
                                protocol_digest=ACTIVE_PROTOCOL_DIGEST,
                                dataset_id="synthetic", dataset_digest="ds-synthetic"))


@pytest.mark.req("routing-disambiguation:7.1")
def test_flag_defaults_to_off(monkeypatch):
    monkeypatch.delenv("INSTANCE_REFERENCE_GATE", raising=False)
    assert _m().gate_requested() is False


@pytest.mark.req("routing-disambiguation:7.1")
@pytest.mark.parametrize("value,expected", [("true", True), ("TRUE", True), ("false", False),
                                            ("1", False), ("yes", False), ("", False)])
def test_flag_parsing_is_strict(monkeypatch, value, expected):
    """只有字面 true（不分大小寫）算開——`1`／`yes` 不算，避免各處各自解讀。"""
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", value)
    assert _m().gate_requested() is expected


@pytest.mark.req("routing-disambiguation:3.5")
def test_today_the_gate_is_not_authorized():
    """⚠️ 現階段 production manifest 為 `not_run` → **未授權**。"""
    assert _m().gate_authorized() is False


@pytest.mark.req("routing-disambiguation:3.5")
def test_requesting_without_authorization_does_not_activate(monkeypatch):
    """⚠️ 本檔最重要的一條：**把 env 設成 true 也不會真的生效**。"""
    m = _m()
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    assert m.gate_requested() is True
    assert m.gate_authorized() is False
    assert m.gate_active() is False, "旗標打開就生效——requested 與 authorized 被摺疊了"


@pytest.mark.req("routing-disambiguation:7.1")
def test_authorized_without_request_does_not_activate(monkeypatch):
    """反向：通過 holdout 也不代表自動上線——上線仍是運維決定。"""
    m = _m()
    authorized = _authorized_manifest(m)                  # ⚠️ 先建好再 patch
    monkeypatch.setattr(m, "current_manifest", lambda: authorized)
    monkeypatch.delenv("INSTANCE_REFERENCE_GATE", raising=False)
    assert m.gate_authorized() is True and m.gate_active() is False


@pytest.mark.req("routing-disambiguation:7.1")
def test_active_requires_both(monkeypatch):
    m = _m()
    authorized = _authorized_manifest(m)                  # ⚠️ 先建好再 patch
    monkeypatch.setattr(m, "current_manifest", lambda: authorized)
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    assert m.gate_active() is True


@pytest.mark.req("routing-disambiguation:3.5")
def test_authorization_only_swallows_gate_not_enablable(monkeypatch):
    """⚠️ 授權判定**不得**吞掉任意例外——否則「守門壞掉」會偽裝成「尚未通過」。"""
    m = _m()

    def _boom():
        raise RuntimeError("manifest 讀取炸了")

    monkeypatch.setattr(m, "current_manifest", _boom)
    with pytest.raises(RuntimeError):
        m.gate_authorized()
