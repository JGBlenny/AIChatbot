"""unit：SEC-01 衍生守則——**測試輸出／失敗訊息不得含憑證值**（2026-08-30）。

```text
test logs ／ failure output MUST NOT contain credential/token values
```
⚠️ 起因：本線已發生一次 key exposure（`env | grep -i openai`）。新的紀律要防的是
**第二次不是 env，而是 exception／debug log 又把 secret 帶進 transcript**。
"""
import os
import re

import pytest

pytestmark = pytest.mark.unit

#: ⚠️ 只列**變數名**，⛔ 不列值
SECRET_ENV_KEYS = ("JGB_API_KEY", "OPENAI_API_KEY", "DB_PASSWORD", "ANTHROPIC_API_KEY")


def _present_secrets():
    return {k: v for k in SECRET_ENV_KEYS if (v := os.getenv(k)) and len(v) >= 8}


@pytest.mark.req("SEC01_G1:1")
def test_real_transport_repr_does_not_leak_api_key():
    """RealHttpTransport 的 repr／str ⛔ 不得吐出 api_key。"""
    from services.jgb_system_api import RealHttpTransport
    t = RealHttpTransport("https://example.invalid", "SUPER-SECRET-TOKEN-123456", 1.0)
    blob = f"{t!r} {t}"
    assert "SUPER-SECRET-TOKEN-123456" not in blob, "transport repr 洩漏 api_key"


@pytest.mark.req("SEC01_G1:2")
def test_jgb_api_init_log_does_not_include_key(capsys, monkeypatch):
    """初始化 log 只印 base_url 與 use_mock——⛔ 不得含 key。"""
    monkeypatch.setenv("JGB_API_KEY", "SUPER-SECRET-TOKEN-123456")
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    import importlib

    import services.jgb_system_api as m
    importlib.reload(m)
    m.JGBSystemAPI()
    out = capsys.readouterr()
    assert "SUPER-SECRET-TOKEN-123456" not in (out.out + out.err)


@pytest.mark.req("SEC01_G1:3")
def test_environment_secrets_are_not_echoed_by_helpers():
    """⚠️ 正對照：先確認**確實有**秘密可洩，否則本檢查恆真＝假綠。"""
    present = _present_secrets()
    if not present:
        pytest.skip("env_skipped: 本環境未設任何受測秘密 ⇒ 這條檢查無鑑別力")
    from services import responsibility_bill_resolution as rbr
    from services import responsibility_completion as rc
    from services import fulfillment_registry as fr
    blob = " ".join(str(getattr(mod, "__doc__", "") or "") for mod in (rbr, rc, fr))
    for name, value in present.items():
        assert value not in blob, f"{name} 的值出現在模組文件字串中"


@pytest.mark.req("SEC01_G1:4")
def test_no_hardcoded_key_shape_in_responsibility_modules():
    """responsibility 線的模組 ⛔ 不得硬編任何看起來像金鑰的字串。"""
    import pathlib
    base = pathlib.Path(__file__).resolve().parents[3] / "services"
    pat = re.compile(r"(sk-[A-Za-z0-9_\-]{16,}|AKIA[0-9A-Z]{16})")
    for f in ("responsibility_session.py", "responsibility_entity_resolution.py",
              "responsibility_bill_resolution.py", "responsibility_completion.py",
              "fulfillment_registry.py"):
        text = (base / f).read_text(encoding="utf-8")
        assert not pat.search(text), f"{f} 含疑似硬編金鑰"
