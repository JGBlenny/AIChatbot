"""unit：正本組裝與啟動契約（spec knowledge-outline-and-intent-architecture 任務 3.2）。

Plan `inputs/plan-3.2-canon-assembler-20260907.md` §4.2／§4.3／§4.5／§4.7。

⚠️ **版控正本（`rag-orchestrator/canon/prospect.md`／`.json`）一律唯讀**——所有竄改情境
都先複製到 `tmp_path` 再改，⛔ 不動版控檔（本檔任何一條測試都不寫入 `CANON_DIR`）。
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import pytest

from services.agent.canon.canon_assembler import (
    CANON_DIR_ENV,
    DB_ENV_KEY,
    CanonLoadError,
    canon_registry_shas,
    get_canon,
    load_canon_or_die,
    register_canon,
    reset_canon_registry,
    resolve_canon_dir,
)
from services.agent.canon.canon_parser import export_json, parse_canon
from services.agent.outline import OutlineBudgetExceeded, build_prospect_outline

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.2"),
]

_RAG_ROOT = Path(__file__).resolve().parents[3]
CANON_DIR = _RAG_ROOT / "canon"
PROSPECT_MD = CANON_DIR / "prospect.md"
PROSPECT_JSON = CANON_DIR / "prospect.json"


@pytest.fixture(autouse=True)
def _clean_registry():
    """每條測試前後都清註冊表——⛔ 不讓某條測試的註冊漏給下一條。"""
    reset_canon_registry()
    yield
    reset_canon_registry()


@pytest.fixture
def tmp_canon(tmp_path):
    """版控正本的 tmp 複本（`.md`＋`.json`），可安全竄改。"""
    dst = tmp_path / "canon"
    dst.mkdir()
    shutil.copy2(PROSPECT_MD, dst / "prospect.md")
    shutil.copy2(PROSPECT_JSON, dst / "prospect.json")
    return dst


def _reexport(canon_dir: Path, audience: str = "prospect") -> None:
    """依 `.md` 重新導出 `.json`（改了 `.md` 之後要維持同源時用）。"""
    doc = parse_canon(str(canon_dir / f"{audience}.md"))
    export_json(doc, str(canon_dir / f"{audience}.json"))


# ── §4.2 load_canon_or_die ───────────────────────────────────────────────


def test_load_canon_or_die_accepts_versioned_canon():
    """正對照：版控正本原樣載得起來（⛔ 沒有這條，下面每個 raise 都可能只是量尺壞了）。"""
    doc = load_canon_or_die(CANON_DIR, "prospect")
    assert doc.audience == "prospect"
    assert len(doc.fines()) == 38, [f.id for f in doc.fines()]
    assert all(f.reviewed_by is not None for f in doc.fines())


def test_load_canon_or_die_reads_content_only_from_markdown(tmp_canon):
    """內容只來自 `.md`：`.md` 的內容句在回傳的 `CanonDoc` 裡，且 `.json` 未被解析。"""
    doc = load_canon_or_die(tmp_canon, "prospect")
    md_text = (tmp_canon / "prospect.md").read_text(encoding="utf-8")
    for unit in doc.fines()[0].content_units:
        assert unit in md_text


def test_missing_markdown_raises_with_resolved_path(tmp_canon):
    (tmp_canon / "prospect.md").unlink()
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon, "prospect")
    assert str((tmp_canon / "prospect.md").resolve()) in str(exc.value)


def test_missing_json_raises(tmp_canon):
    (tmp_canon / "prospect.json").unlink()
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon, "prospect")
    assert str((tmp_canon / "prospect.json").resolve()) in str(exc.value)


def test_json_tampered_outside_sha_field_raises(tmp_canon):
    """⚠️ 本檔最關鍵的一條（security-reviewer P1-1）：改的**不是** `canon_sha256` 欄位。

    `canon_sha256` 只涵蓋 `.md` 的位元組 ⇒ 只比對 sha 欄位的實作對這個竄改**看不見**；
    逐位元組比對重導出結果才抓得到。
    """
    json_path = tmp_canon / "prospect.json"
    raw = json_path.read_bytes()
    needle = b'"language": "zh-TW"'
    assert needle in raw, "正對照失敗：找不到要竄改的欄位，這條測試沒有在測東西"
    tampered = raw.replace(needle, b'"language": "zh-TX"', 1)
    assert len(tampered) == len(raw)
    # 竄改點不在 canon_sha256 欄位內（否則這條就退化成「sha 欄被改」的弱版本）
    sha_idx = raw.index(b'"canon_sha256"')
    assert not (sha_idx <= raw.index(needle) <= sha_idx + 100)
    json_path.write_bytes(tampered)
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon, "prospect")
    assert "不同源" in str(exc.value)


def test_markdown_whitespace_change_without_reexport_raises(tmp_canon):
    """`.md` 多一個空白 ⇒ sha 變、`.json` 未重導出 ⇒ 不同源 ⇒ raise。"""
    md = tmp_canon / "prospect.md"
    md.write_text(md.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(CanonLoadError):
        load_canon_or_die(tmp_canon, "prospect")


def test_markdown_change_with_reexport_loads_and_changes_sha(tmp_canon):
    """正對照：同一個改動**有**重導出 `.json` ⇒ 載得起來，且 `canon_sha256` 變了。"""
    before = load_canon_or_die(tmp_canon, "prospect").canon_sha256
    md = tmp_canon / "prospect.md"
    md.write_text(md.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    _reexport(tmp_canon)
    after = load_canon_or_die(tmp_canon, "prospect").canon_sha256
    assert after != before


def test_format_error_raises_canon_load_error(tmp_canon):
    (tmp_canon / "prospect.md").write_text("沒有 front matter 的一行字\n", encoding="utf-8")
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon, "prospect")
    assert "格式錯誤" in str(exc.value)


@pytest.mark.parametrize("audience", ["prospect2", "", "PROSPECT", "../etc/passwd", None])
def test_non_literal_audience_raises(tmp_canon, audience):
    with pytest.raises(CanonLoadError):
        load_canon_or_die(tmp_canon, audience)


def test_front_matter_audience_must_match_filename(tmp_canon):
    """檔名受眾與 front matter 不符 ⇒ raise（⛔ 不讓 tenant 正本被當成 prospect 載入）。"""
    md = tmp_canon / "tenant.md"
    text = (tmp_canon / "prospect.md").read_text(encoding="utf-8")
    md.write_text(text, encoding="utf-8")
    _reexport(tmp_canon, "tenant")
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon, "tenant")
    assert "不符" in str(exc.value)


# ── §4.3 resolve_canon_dir ───────────────────────────────────────────────


def test_resolve_canon_dir_default_is_rag_root_canon(monkeypatch):
    monkeypatch.delenv(CANON_DIR_ENV, raising=False)
    assert resolve_canon_dir() == CANON_DIR.resolve()


def test_env_override_applies_only_under_db_env_test(monkeypatch, tmp_canon):
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon) + "/./")
    assert resolve_canon_dir() == tmp_canon.resolve()


def test_env_override_ignored_without_db_env_test(monkeypatch, tmp_canon, caplog):
    monkeypatch.delenv(DB_ENV_KEY, raising=False)
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    with caplog.at_level("WARNING"):
        resolved = resolve_canon_dir()
    assert resolved == CANON_DIR.resolve()
    assert any(CANON_DIR_ENV in r.getMessage() for r in caplog.records), caplog.text


def test_env_override_ignored_when_db_env_is_production(monkeypatch, tmp_canon):
    monkeypatch.setenv(DB_ENV_KEY, "production")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    assert resolve_canon_dir() == CANON_DIR.resolve()


# ── §4.7 註冊表 ──────────────────────────────────────────────────────────


def test_registry_round_trip_and_reset():
    doc = load_canon_or_die(CANON_DIR, "prospect")
    assert get_canon("prospect") is None
    register_canon("prospect", doc)
    assert get_canon("prospect") is doc
    assert canon_registry_shas() == {"prospect": doc.canon_sha256}
    reset_canon_registry()
    assert get_canon("prospect") is None


def test_register_rejects_non_literal_audience():
    doc = load_canon_or_die(CANON_DIR, "prospect")
    with pytest.raises(CanonLoadError):
        register_canon("prospect2", doc)


async def test_build_prospect_outline_registers_same_doc_and_leaves_sha_unchanged():
    """`build_prospect_outline` 後 `get_canon("prospect")` 是同一份，且 `doc.sha256` 不因註冊而變。"""
    standalone = load_canon_or_die(CANON_DIR, "prospect")
    reset_canon_registry()

    doc = await build_prospect_outline(None)
    registered = get_canon("prospect")
    assert registered is not None
    assert registered.canon_sha256 == standalone.canon_sha256
    # 註冊的就是組裝用的那一份：第一節內容＝第一個細目的內容句
    first_fine = registered.fines()[0]
    first_section = doc.sections[0]
    assert first_section.id == first_fine.id
    assert first_section.text == "\n".join(first_fine.content_units)

    doc_again = await build_prospect_outline(None)
    assert doc_again.sha256 == doc.sha256          # 決定性：同一份正本 ⇒ 同一個 sha
    assert get_canon("prospect") is not None


# ── §4.5 check_budget 用 min(env, doc.budget_tokens) ─────────────────────


def _canon_with_budget(tmp_canon: Path, budget: int) -> Path:
    md = tmp_canon / "prospect.md"
    text = md.read_text(encoding="utf-8")
    assert re.search(r"^budget_tokens: \d+$", text, re.M), "正本 front matter 缺 budget_tokens"
    md.write_text(re.sub(r"^budget_tokens: \d+$", f"budget_tokens: {budget}", text, count=1, flags=re.M), encoding="utf-8")
    _reexport(tmp_canon)
    return tmp_canon


async def test_budget_positive_control_passes(monkeypatch, tmp_canon):
    """正對照：預設上限下組得起來（否則下面的 raise 只是「本來就會炸」）。"""
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    monkeypatch.delenv("AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT", raising=False)
    doc = await build_prospect_outline(None)
    assert doc.token_count > 0


async def test_env_limit_lower_than_actual_raises(monkeypatch, tmp_canon):
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    monkeypatch.setenv("AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT", "100")
    with pytest.raises(OutlineBudgetExceeded):
        await build_prospect_outline(None)


async def test_canon_budget_lower_than_env_raises(monkeypatch, tmp_canon):
    """正本自帶的 `budget_tokens` 較小時由它把關——⛔ env 不得單方面把上限開大。"""
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(_canon_with_budget(tmp_canon, 100)))
    monkeypatch.setenv("AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT", "999999")
    with pytest.raises(OutlineBudgetExceeded):
        await build_prospect_outline(None)


def test_canon_dir_versioned_files_untouched():
    """守門：本檔跑完之後版控正本仍與載入時一致（⛔ 測試不得動正本）。"""
    assert os.path.exists(PROSPECT_MD) and os.path.exists(PROSPECT_JSON)
    load_canon_or_die(CANON_DIR, "prospect")   # 仍然同源
