"""integration：正本啟動契約（spec knowledge-outline-and-intent-architecture 3.2｜Plan §4.6）。

走**真的那條啟動路徑** `app.py::_init_agent_runtime`（⛔ 不另寫一份組裝流程來測）：
`_agent_configured()` 為真時，缺架／`.json`／`CATALOG.md` 被竄改 ⇒ **啟動紅**（raise）；未竄改 ⇒ 綠，
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
    CANON_DIR_ENV, DB_ENV_KEY, TOC_SECTION_ID, build_canon_toc, build_outline, get_canon,
    reset_canon_registry,
)
from services.agent.canon.canon_parser import (
    CANON_NAME, export_catalog, export_json, parse_canon_dir,
)
from services.agent.health import compute_agent_health
from services.agent.identity import Identity

pytestmark = [
    pytest.mark.integration,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.2"),
]

CANON_DIR = Path(__file__).resolve().parents[3] / "canon"
#: 拿來當「未審細目」的那一筆（把它的 `- reviewed:` 行拿掉）——⚠️ 必須是**現在就**已審
#: 且 **prospect 視圖內**的細目（drop 之後才會真的從「已審」變成「未審」，量得到東西）；
#: 否則它根本不在 prospect 視圖（`build_outline(canon, "prospect", …)`）裡。
#: 2026-09-16 9.7 七架連跑後改用腳本對 210 條正本逐條篩出（見完成報告）：C 架同時有
#: 多筆已審＋prospect 可見的細目，取其中兩筆分別當 UNREVIEWED／REVIEWED 來源。
UNREVIEWED_FINE_ID = "jgb/C/community-batch-create"
REVIEWED_FINE_ID = "jgb/C/property-management-overview"
#: 只在 pm 視圖的細目（⛔ 不得出現在 prospect 視圖的任何欄位）——`target_user` 只有
#: `property_manager`、不含 `prospect`。
PM_ONLY_FINE_ID = "jgb/A/email-case-sensitivity"
#: `UNREVIEWED_FINE_ID` 所在的架（`_drop_reviewed_line` 只改這一檔）。
_SHELF_OF_UNREVIEWED = "C.md"


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
    shutil.copytree(CANON_DIR / CANON_NAME, dst / CANON_NAME)   # 九架＋CATALOG.md
    shutil.copy2(CANON_DIR / f"{CANON_NAME}.json", dst / f"{CANON_NAME}.json")
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
    doc = parse_canon_dir(str(canon_dir / CANON_NAME))
    export_json(doc, str(canon_dir / f"{CANON_NAME}.json"))
    export_catalog(doc, str(canon_dir / CANON_NAME / "CATALOG.md"))


def _drop_reviewed_line(canon_dir: Path, fine_id: str) -> None:
    """把某細目的 `- reviewed: {...}` 屬性行拿掉 ⇒ 該細目變成未審（其餘不動）。"""
    md = canon_dir / CANON_NAME / _SHELF_OF_UNREVIEWED
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
    (tmp_canon / CANON_NAME / "A.md").unlink()
    with pytest.raises(RuntimeError) as exc:
        await _init(_fake_app())
    assert "啟動紅" in str(exc.value)


async def test_startup_red_when_catalog_tampered(tmp_canon):
    """衍生目錄手改 ⇒ 啟動紅（9.6 S3 新增的第三道同源比對）。"""
    catalog = tmp_canon / CANON_NAME / "CATALOG.md"
    catalog.write_text(catalog.read_text(encoding="utf-8") + "手改一行\n", encoding="utf-8")
    with pytest.raises(RuntimeError) as exc:
        await _init(_fake_app())
    assert "啟動紅" in str(exc.value)


async def test_startup_red_when_json_byte_flipped_outside_sha_field(tmp_canon):
    """⚠️ 改的**不是** `canon_sha256` 欄位——只比 sha 欄的實作對這個竄改是瞎的。"""
    json_path = tmp_canon / f"{CANON_NAME}.json"
    raw = json_path.read_bytes()
    needle = b'"language": "zh-TW"'
    assert needle in raw, "正對照失敗：找不到要竄改的位元組"
    json_path.write_bytes(raw.replace(needle, b'"language": "zh-TX"', 1))
    with pytest.raises(RuntimeError) as exc:
        await _init(_fake_app())
    assert "啟動紅" in str(exc.value)


async def test_startup_green_positive_control(tmp_canon):
    """正對照：未竄改的同一份 tmp 複本起得來——否則上面幾條紅可能只是環境壞了。

    另釘 DSP-058 的啟動形狀：兩受眾都通過啟動預算、**共用同一個 `FineIndex`**。
    9.8 DSP-059 D′ S2：權威旗標是 `agent_audiences`（frozenset），⛔ 不再有
    預組的 `agent_outline`／`agent_outlines`——受眾視圖改用 `build_outline`
    現組來驗證兩份視圖確實不同（sha 不同、節數 > 1）。
    """
    app = await _init(_fake_app())
    assert app.state.agent_runtime is not None
    assert app.state.outline_resolver is not None
    assert app.state.agent_audiences == frozenset({"prospect", "property_manager"})
    assert (app.state.agent_indexes["prospect"]
            is app.state.agent_indexes["property_manager"])
    canon = get_canon()
    pros_identity = Identity(vendor_id=0, target_user="prospect", mode="b2b")
    pm_identity = Identity(vendor_id=0, target_user="property_manager", mode="b2b")
    pros = build_outline(canon, "prospect", pros_identity, vendor_business_types=frozenset())
    pm = build_outline(canon, "property_manager", pm_identity, vendor_business_types=frozenset())
    assert pros.sha256 != pm.sha256
    assert len(pros.sections) > 1 and len(pm.sections) > 1


# ── 綠：resolver 與 health 的行為 ─────────────────────────────────────────


async def test_resolver_applies_visibility_and_toc_is_not_citable(tmp_canon):
    _drop_reviewed_line(tmp_canon, UNREVIEWED_FINE_ID)
    app = await _init(_fake_app())

    # 9.8 DSP-059 D′ S2：沒有預組的 `app.state.agent_outline` 可讀——用
    # `build_outline`＋`build_canon_toc` 現組 prospect 視圖（與
    # `build_audience_outline` 同一式：受眾細目節 ＋ toc 節）來驗可見性規則。
    identity = Identity(vendor_id=0, target_user="prospect", mode="b2b")
    canon = get_canon()
    doc = build_outline(canon, "prospect", identity, vendor_business_types=frozenset())
    toc = build_canon_toc(canon, identity, vendor_business_types=frozenset())
    by_id = {s.id: s for s in list(doc.sections) + [toc]}
    assert TOC_SECTION_ID in by_id
    assert by_id[TOC_SECTION_ID].citable is False
    # 未審細目：仍出現在大綱（只有標題）、但 citable=False 且無內容
    assert by_id[UNREVIEWED_FINE_ID].citable is False
    assert by_id[UNREVIEWED_FINE_ID].text == ""
    # 計畫 9.10 S2：目錄改列粗目——目錄不列任何細目 id（負對照，未審或已審皆然）
    assert UNREVIEWED_FINE_ID not in by_id[TOC_SECTION_ID].text
    assert REVIEWED_FINE_ID not in by_id[TOC_SECTION_ID].text
    # 正對照：REVIEWED_FINE_ID 所屬的粗目那一行出現在目錄裡（目錄改列粗目後，
    # 可引用內容仍透過「粗目行 → 粗目導航 → 細目」兩跳到得了，這裡先釘第一跳）
    reviewed_coarse = next(c for c in canon.coarses if any(f.id == REVIEWED_FINE_ID for f in c.fines))
    assert f"{reviewed_coarse.id}｜{reviewed_coarse.title}｜" in by_id[TOC_SECTION_ID].text
    # DSP-058：另一受眾（pm）的細目**連標題都不在** prospect 視圖裡
    assert PM_ONLY_FINE_ID not in by_id
    assert PM_ONLY_FINE_ID not in doc.text

    resolver = app.state.outline_resolver

    ok = resolver(identity, f"outline:{REVIEWED_FINE_ID}")
    assert ok.ok is True and ok.provenance[0].citable is True

    for miss_id in (
        f"outline:{UNREVIEWED_FINE_ID}",
        f"outline:{PM_ONLY_FINE_ID}",          # 另一受眾的細目：同一個 NO_MATCH（⛔ 不分不可見與不存在）
        "outline:jgb/A/does-not-exist",
    ):
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
    assert canon["sha256"] == {CANON_NAME: get_canon().canon_sha256}
    # 9.8 DSP-059 D′ S2：`outline_version` 改讀 `canon_state["sha256"]["jgb"]`
    # （⛔ 不再有預組 `agent_outline.sha256` 可比）。
    assert health["checks"]["outline_version"] == get_canon().canon_sha256
