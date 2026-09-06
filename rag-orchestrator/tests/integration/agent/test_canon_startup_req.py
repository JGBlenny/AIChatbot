"""integration：正本啟動契約（spec knowledge-outline-and-intent-architecture 3.2｜Plan §4.6）。

走**真的那條啟動路徑** `app.py::_init_agent_runtime`（⛔ 不另寫一份組裝流程來測）：
`_agent_configured()` 為真時，正本缺檔／`.json` 被竄改 ⇒ **啟動紅**（raise）；未竄改 ⇒ 綠，
且 `app.state.outline_resolver` 對未審／不存在的 `outline:*` 回 `NO_MATCH`、對已審回
`citable=True`、`outline:toc` 在 `sections` 內且 `citable=False`，`health` 印得出正本
resolved path 與 `canon_sha256`。

⚠️ 一律用 `tmp_path` 複本＋`AGENT_CANON_DIR`（只在 `DB_ENV=test` 生效），
⛔ 本檔不寫入 `rag-orchestrator/canon/`。
⚠️ 本檔不連 DB：3.2 之後大綱組裝完全不讀 DB，`_init_agent_runtime` 只需要 registry 與
LLM provider（兩者都在 import app 時就備妥）。
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.agent import mcp_facade
from services.agent.canon.canon_assembler import (
    CANON_DIR_ENV, DB_ENV_KEY, TOC_SECTION_ID, get_canon, reset_canon_registry,
)
from services.agent.canon.canon_parser import export_json, parse_canon
from services.agent.health import compute_agent_health
from services.agent.identity import Identity

pytestmark = [
    pytest.mark.integration,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.2"),
]

CANON_DIR = Path(__file__).resolve().parents[3] / "canon"
#: 拿來當「未審細目」的那一筆（把它的 `- reviewed:` 行拿掉）。
UNREVIEWED_FINE_ID = "prospect/A/pain-points"
REVIEWED_FINE_ID = "prospect/A/product-overview"


@pytest.fixture(autouse=True)
def _agent_switch_on(monkeypatch):
    """`_agent_configured()` 為真 ⇒ 組裝失敗必須升成啟動紅（⛔ 不是 fail-soft 警告）。"""
    monkeypatch.setenv("AGENT_TURN_ENABLED", "1")
    reset_canon_registry()
    yield
    reset_canon_registry()


@pytest.fixture
def tmp_canon(tmp_path, monkeypatch):
    assert os.environ.get(DB_ENV_KEY, "").strip() == "test", (
        "AGENT_CANON_DIR 覆寫只在 DB_ENV=test 生效——沒設就會靜默打到版控正本"
    )
    dst = tmp_path / "canon"
    dst.mkdir()
    shutil.copy2(CANON_DIR / "prospect.md", dst / "prospect.md")
    shutil.copy2(CANON_DIR / "prospect.json", dst / "prospect.json")
    monkeypatch.setenv(CANON_DIR_ENV, str(dst))
    return dst


def _fake_app():
    """`_init_agent_runtime` 只碰 `app.state` 與模組層的 registry／kb pool。"""
    return SimpleNamespace(state=SimpleNamespace(db_pool=None))


async def _init(app):
    import app as app_module
    assert app_module._agent_configured() is True, "前置條件沒達成：agent 開關沒開 ⇒ 失敗會被吞成警告"
    await app_module._init_agent_runtime(app)
    return app


def _reexport(canon_dir: Path) -> None:
    export_json(parse_canon(str(canon_dir / "prospect.md")), str(canon_dir / "prospect.json"))


def _drop_reviewed_line(canon_dir: Path, fine_id: str) -> None:
    """把某細目的 `- reviewed: {...}` 屬性行拿掉 ⇒ 該細目變成未審（其餘不動）。"""
    md = canon_dir / "prospect.md"
    lines = md.read_text(encoding="utf-8").split("\n")
    out, inside, dropped = [], False, False
    for line in lines:
        if line.startswith("### "):
            inside = f"{{#{fine_id}}}" in line
        if inside and line.startswith("- reviewed:"):
            dropped = True
            continue
        out.append(line)
    assert dropped, f"正對照失敗：{fine_id} 找不到 reviewed 屬性行，這條測試沒有造出未審細目"
    md.write_text("\n".join(out), encoding="utf-8")
    _reexport(canon_dir)


# ── 紅：正本缺檔／`.json` 被竄改 ──────────────────────────────────────────


async def test_startup_red_when_canon_markdown_missing(tmp_canon):
    (tmp_canon / "prospect.md").unlink()
    with pytest.raises(RuntimeError) as exc:
        await _init(_fake_app())
    assert "啟動紅" in str(exc.value)


async def test_startup_red_when_json_byte_flipped_outside_sha_field(tmp_canon):
    """⚠️ 改的**不是** `canon_sha256` 欄位——只比 sha 欄的實作對這個竄改是瞎的。"""
    json_path = tmp_canon / "prospect.json"
    raw = json_path.read_bytes()
    needle = b'"language": "zh-TW"'
    assert needle in raw, "正對照失敗：找不到要竄改的位元組"
    json_path.write_bytes(raw.replace(needle, b'"language": "zh-TX"', 1))
    with pytest.raises(RuntimeError) as exc:
        await _init(_fake_app())
    assert "啟動紅" in str(exc.value)


async def test_startup_green_positive_control(tmp_canon):
    """正對照：未竄改的同一份 tmp 複本起得來——否則上面兩條紅可能只是環境壞了。"""
    app = await _init(_fake_app())
    assert app.state.agent_runtime is not None
    assert app.state.agent_outline is not None
    assert app.state.outline_resolver is not None


# ── 綠：resolver 與 health 的行為 ─────────────────────────────────────────


async def test_resolver_applies_visibility_and_toc_is_not_citable(tmp_canon):
    _drop_reviewed_line(tmp_canon, UNREVIEWED_FINE_ID)
    app = await _init(_fake_app())

    doc = app.state.agent_outline
    by_id = {s.id: s for s in doc.sections}
    assert TOC_SECTION_ID in by_id
    assert by_id[TOC_SECTION_ID].citable is False
    # 未審細目：仍出現在大綱（只有標題）、但 citable=False 且無內容
    assert by_id[UNREVIEWED_FINE_ID].citable is False
    assert by_id[UNREVIEWED_FINE_ID].text == ""
    # 目錄不列未審細目
    assert UNREVIEWED_FINE_ID not in by_id[TOC_SECTION_ID].text
    assert REVIEWED_FINE_ID in by_id[TOC_SECTION_ID].text

    resolver = app.state.outline_resolver
    identity = Identity(vendor_id=0, target_user="prospect", mode="b2b")

    ok = resolver(identity, f"outline:{REVIEWED_FINE_ID}")
    assert ok.ok is True and ok.provenance[0].citable is True

    for miss_id in (f"outline:{UNREVIEWED_FINE_ID}", "outline:prospect/A/does-not-exist"):
        miss = resolver(identity, miss_id)
        assert miss.ok is False and miss.error == "NO_MATCH", miss_id

    toc = resolver(identity, TOC_SECTION_ID)
    assert toc.ok is True and toc.provenance[0].citable is False


async def test_health_reports_resolved_canon_dir_and_sha(tmp_canon):
    app = await _init(_fake_app())
    health = await compute_agent_health(
        registry=__import__("app")._mcp_registry,
        get_kb_pool=None,
        stage=mcp_facade.current_stage(),
        get_runtime=lambda: app.state.agent_runtime,
    )
    canon = health["checks"]["canon"]
    assert canon["dir"] == str(tmp_canon.resolve())
    assert canon["sha256"]["prospect"] == get_canon("prospect").canon_sha256
    assert health["checks"]["outline_version"] == app.state.agent_outline.sha256
