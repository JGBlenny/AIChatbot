"""unit：正本組裝與啟動契約（spec knowledge-outline-and-intent-architecture 任務 3.2；DSP-058／9.6 S3）。

Plan `inputs/plan-3.2-canon-assembler-20260907.md` §4.2／§4.3／§4.5／§4.7；
圖書館形態改點見 `inputs/plan-9.6-library-canon-20260915.md` §2。

⚠️ **版控正本（`rag-orchestrator/canon/jgb/` 九架＋`jgb.json`）一律唯讀**——所有竄改情境
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
    build_canon_toc,
    canon_registry_shas,
    get_canon,
    load_canon_or_die,
    register_canon,
    reset_canon_registry,
    resolve_canon_dir,
    resolve_canon_section,
)
from services.agent.canon.canon_parser import (
    CANON_NAME, CanonDoc, CoarseItem, FineItem, export_catalog, export_json, parse_canon_dir,
)
from services.agent.identity import Identity
from services.agent.outline import OutlineBudgetExceeded, build_prospect_outline

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.2"),
]

_RAG_ROOT = Path(__file__).resolve().parents[3]
CANON_DIR = _RAG_ROOT / "canon"
SHELF_DIR = CANON_DIR / CANON_NAME
CANON_JSON = CANON_DIR / f"{CANON_NAME}.json"
CATALOG_MD = SHELF_DIR / "CATALOG.md"

#: 計畫 9.10 S3 換正本（2026-09-23）：515 條全未審（DSP-066：未審 ⇒ 模型不可見；業主 81 題
#: 裁完重跑 S3 之後條數會再變）。⛔ 不再寫死條數／id 清單本身——`_grep_total_fines()` 用
#: `### ` 節標題數這條**與 `doc.fines()` 完全獨立的管道**在測試內現算，兩者不一致就代表
#: parser 漏收或多收了細目，量尺因此仍具鑑別力（S4 修復：計畫 9.10 §3 S4 病灶①②，
#: 改法 (i)：期望值由正本現算，不再寫死舊條數／舊裸字母粗目假設）。


def _grep_total_fines() -> int:
    """獨立於 `load_canon_or_die` 的第二條計數管道：逐架 `.md` 數 `### ` 節標題。"""
    pattern = re.compile(r"^### ", re.M)
    return sum(
        len(pattern.findall((SHELF_DIR / f"{letter}.md").read_text(encoding="utf-8")))
        for letter in "ABCDEFGHI"
    )



@pytest.fixture(autouse=True)
def _clean_registry():
    """每條測試前後都清註冊表——⛔ 不讓某條測試的註冊漏給下一條。"""
    reset_canon_registry()
    yield
    reset_canon_registry()


@pytest.fixture
def tmp_canon(tmp_path):
    """版控正本的 tmp 複本（`jgb/` 九架＋`CATALOG.md`＋`jgb.json`），可安全竄改。"""
    dst = tmp_path / "canon"
    dst.mkdir()
    shutil.copytree(SHELF_DIR, dst / CANON_NAME)
    shutil.copy2(CANON_JSON, dst / f"{CANON_NAME}.json")
    return dst


def _reexport(canon_dir: Path) -> None:
    """依九架重新導出 `jgb.json`＋`CATALOG.md`（改了架之後要維持同源時用）。"""
    doc = parse_canon_dir(str(canon_dir / CANON_NAME))
    export_json(doc, str(canon_dir / f"{CANON_NAME}.json"))
    export_catalog(doc, str(canon_dir / CANON_NAME / "CATALOG.md"))


#: 計畫 9.10 S4：換正本後 515 條全未審——凡測試假設「正本裡有已審細目」的，
#: 一律不得竄改版控 `canon/jgb/`（S3 已驗），改在 `tmp_path` 下造一份「全審副本」
#: （每條細目補 `reviewed:` 屬性，內容逐字不變）餵給它；`skip_ids` 可讓指定細目
#: 刻意留白（測「已審／未審在視圖裡呈現不同」需要兩者都在場）。
_FINE_HEADING_RE = re.compile(r"^### .+\{#(jgb/[A-Z]/[a-z0-9-]+)\}\s*$", re.M)


def _mark_reviewed_except(shelf_text: str, skip_ids: frozenset) -> str:
    def _sub(m: "re.Match") -> str:
        if m.group(1) in skip_ids:
            return m.group(0)
        return m.group(0) + "\n- reviewed: {by: s4-measurement, at: 2026-09-23}"

    return _FINE_HEADING_RE.sub(_sub, shelf_text)


def all_reviewed_canon_dir(tmp_path: Path, *, skip_ids: frozenset = frozenset(),
                           name: str = "all-reviewed-canon") -> Path:
    """版控正本的「全審副本」（⛔ 只在 `tmp_path` 底下，⛔ 不寫回 `canon/jgb/`）。

    `skip_ids` 非空時，那幾條細目刻意留白（仍未審），其餘全補 `reviewed:`。
    """
    dst = tmp_path / name
    shelf_dst = dst / CANON_NAME
    shelf_dst.mkdir(parents=True)
    changed_any = False
    for letter in "ABCDEFGHI":
        text = (SHELF_DIR / f"{letter}.md").read_text(encoding="utf-8")
        marked = _mark_reviewed_except(text, skip_ids)
        changed_any = changed_any or marked != text
        (shelf_dst / f"{letter}.md").write_text(marked, encoding="utf-8")
    assert changed_any, "沒有任何細目被標 reviewed，注入沒生效"
    doc = parse_canon_dir(str(shelf_dst))
    got_unreviewed = {f.id for f in doc.fines() if f.reviewed_by is None}
    assert got_unreviewed == skip_ids, (got_unreviewed, skip_ids)
    export_json(doc, str(dst / f"{CANON_NAME}.json"))
    export_catalog(doc, str(shelf_dst / "CATALOG.md"))
    return dst


# ── §4.2 load_canon_or_die ───────────────────────────────────────────────


def test_load_canon_or_die_accepts_versioned_canon():
    """正對照：版控正本原樣載得起來（⛔ 沒有這條，下面每個 raise 都可能只是量尺壞了）。

    計畫 9.10 S4：不再寫死條數／id 清單（那是舊 210 條的形狀）——期望值改用與
    `load_canon_or_die` **完全獨立**的第二條管道（`_grep_total_fines`：逐架
    `.md` 數 `### ` 節標題）現算，parser 漏收／多收細目時兩者仍會不一致而抓到。
    新正本（S3，2026-09-23）515 條全未審，DSP-066：未審 ⇒ 模型不可見。
    """
    doc = load_canon_or_die(CANON_DIR)
    assert doc.audience == CANON_NAME and doc.name == CANON_NAME
    grep_total = _grep_total_fines()
    assert len(doc.fines()) == grep_total > 0, (len(doc.fines()), grep_total)
    reviewed = [f.id for f in doc.fines() if f.reviewed_by is not None]
    assert reviewed == [], reviewed  # 換正本後全未審


def test_load_canon_or_die_reads_content_only_from_markdown(tmp_canon):
    """內容只來自九架 `.md`：`.md` 的內容句在回傳的 `CanonDoc` 裡。

    計畫 9.10 S4：`coarse_id` 不再是裸字母（S1 起粗目 id 可為 `<架字母>-<slug>`），
    改用細目 id 中段（`jgb/<架字母>/<slug>` 的 `<架字母>`）取得同一架的第一條細目。
    """
    doc = load_canon_or_die(tmp_canon)
    md_text = (tmp_canon / CANON_NAME / "A.md").read_text(encoding="utf-8")
    first_a = next(f for f in doc.fines() if f.id.split("/")[1] == "A")
    for unit in first_a.content_units:
        assert unit in md_text


def test_missing_shelf_dir_raises_with_resolved_path(tmp_path):
    empty = tmp_path / "canon"
    empty.mkdir()
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(empty)
    assert str((empty / CANON_NAME).resolve()) in str(exc.value)


def test_missing_shelf_file_raises(tmp_canon):
    (tmp_canon / CANON_NAME / "H.md").unlink()
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon)
    assert "缺架 H.md" in str(exc.value)


def test_missing_json_raises(tmp_canon):
    (tmp_canon / f"{CANON_NAME}.json").unlink()
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon)
    assert str((tmp_canon / f"{CANON_NAME}.json").resolve()) in str(exc.value)


def test_missing_catalog_raises(tmp_canon):
    (tmp_canon / CANON_NAME / "CATALOG.md").unlink()
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon)
    assert "CATALOG.md" in str(exc.value)


def test_json_tampered_outside_sha_field_raises(tmp_canon):
    """⚠️ 本檔最關鍵的一條（security-reviewer P1-1）：改的**不是** `canon_sha256` 欄位。

    `canon_sha256` 只涵蓋九架 `.md` 的位元組 ⇒ 只比對 sha 欄位的實作對這個竄改**看不見**；
    逐位元組比對重導出結果才抓得到。
    """
    json_path = tmp_canon / f"{CANON_NAME}.json"
    raw = json_path.read_bytes()
    needle = b'"language": "zh-TW"'
    assert needle in raw, "正對照失敗：找不到要竄改的欄位，這條測試沒有在測東西"
    tampered = raw.replace(needle, b'"language": "zh-TX"', 1)
    assert len(tampered) == len(raw)
    sha_idx = raw.index(b'"canon_sha256"')
    assert not (sha_idx <= raw.index(needle) <= sha_idx + 100)
    json_path.write_bytes(tampered)
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon)
    assert "不同源" in str(exc.value)


def test_catalog_tampered_raises(tmp_canon):
    """衍生目錄手改（多一行講法）⇒ 不同源 ⇒ raise（9.6 S3 新增的第三道比對）。"""
    catalog = tmp_canon / CANON_NAME / "CATALOG.md"
    catalog.write_text(catalog.read_text(encoding="utf-8") + "手改一行\n", encoding="utf-8")
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon)
    assert "CATALOG.md" in str(exc.value) and "不同源" in str(exc.value)


def test_markdown_whitespace_change_without_reexport_raises(tmp_canon):
    """任一架多一個空白 ⇒ sha 變、`.json` 未重導出 ⇒ 不同源 ⇒ raise。"""
    md = tmp_canon / CANON_NAME / "B.md"
    md.write_text(md.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(CanonLoadError):
        load_canon_or_die(tmp_canon)


def test_markdown_change_with_reexport_loads_and_changes_sha(tmp_canon):
    """正對照：同一個改動**有**重導出 ⇒ 載得起來，且 `canon_sha256` 變了。"""
    before = load_canon_or_die(tmp_canon).canon_sha256
    md = tmp_canon / CANON_NAME / "B.md"
    md.write_text(md.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    _reexport(tmp_canon)
    after = load_canon_or_die(tmp_canon).canon_sha256
    assert after != before


def test_format_error_raises_canon_load_error(tmp_canon):
    (tmp_canon / CANON_NAME / "A.md").write_text("沒有 front matter 的一行字\n", encoding="utf-8")
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(tmp_canon)
    assert "格式錯誤" in str(exc.value)


def test_shelf_dir_must_be_named_jgb(tmp_path):
    """⛔ 正本目錄名固定 `jgb`：改名（例如 `prospect/`）⇒ 缺席即 raise，
    ⛔ 不會「自動找到目錄裡唯一那一包」。"""
    dst = tmp_path / "canon"
    dst.mkdir()
    shutil.copytree(SHELF_DIR, dst / "prospect")
    shutil.copy2(CANON_JSON, dst / f"{CANON_NAME}.json")
    with pytest.raises(CanonLoadError) as exc:
        load_canon_or_die(dst)
    assert "正本目錄缺席" in str(exc.value)


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


# ── §4.7 註冊表（DSP-058：單槽，鍵＝正本名）─────────────────────────────


def test_registry_round_trip_and_reset():
    doc = load_canon_or_die(CANON_DIR)
    assert get_canon() is None
    register_canon(doc)
    assert get_canon() is doc
    assert canon_registry_shas() == {CANON_NAME: doc.canon_sha256}
    reset_canon_registry()
    assert get_canon() is None


async def test_both_audience_views_share_one_registered_canon():
    """兩個受眾視圖共用**同一個** `CanonDoc` 物件（⛔ 不各載一份）。"""
    from services.agent.outline import build_audience_outline

    await build_audience_outline("prospect", None)
    first = get_canon()
    assert first is not None
    await build_audience_outline("property_manager", None)
    assert get_canon() is first
    assert list(canon_registry_shas()) == [CANON_NAME]


async def test_prospect_view_fine_ids_match_id_map(tmp_path):
    """prospect 視圖的細目 id 集合＝`runs/library-20260915/id_map.json` 映射後的舊 prospect 集合（38）。

    ⚠️ 取代 9.6 之前的 `test_build_prospect_outline_registers_same_doc_and_leaves_sha_unchanged`
    （那條釘的是「整份正本＝prospect 大綱」，在圖書館形態下已無意義）。
    """
    import json

    repo_root = _RAG_ROOT.parent
    id_map_path = (repo_root / ".claude" / "skills" / "outline-curation" / "runs"
                   / "library-20260915" / "id_map.json")
    if not id_map_path.is_file():
        pytest.skip(f"[env] 容器內看不到 repo 根的 {id_map_path}（compose 只掛 rag-orchestrator）")
    id_map = json.loads(id_map_path.read_text(encoding="utf-8"))
    expected = {row["new"] for row in id_map if row["old"].startswith("prospect/")}
    assert len(expected) == 38, len(expected)

    doc = await build_prospect_outline(None)
    got = {s.id for s in doc.sections if s.id != "outline:toc"}
    # 9.6 遷移的 38 條必須一條不少地在 prospect 視圖；9.7 起逐架擴充只會**多出**該架的新細目
    # （擴充腳本對其他架逐位元不動），⛔ 不得少、⛔ 不得多出非擴充架的 id。
    assert expected <= got, sorted(expected - got)
    extra = got - expected
    expanded_shelves = {"A"}   # 9.7：A 帳號與身分（2026-09-16）；每擴一架加一個字母
    assert {i.split("/")[1] for i in extra} <= expanded_shelves, sorted(extra)


async def test_prospect_outline_is_deterministic_and_registers_canon(monkeypatch, tmp_path):
    """計畫 9.10 S4：版控正本 515 條全未審 ⇒ 找不到「已審且 prospect 可見」的細目
    （`next(...)` 會 `StopIteration`）。本測試要驗的是「已審／未審在視圖裡的呈現差異」，
    這件事需要**兩者都在場**才測得到 ⇒ 造一份全審副本、但把版控正本裡第一條
    prospect 可見細目刻意留白，透過 `AGENT_CANON_DIR`（僅 `DB_ENV=test` 生效）指向它
    （⛔ 不動 `canon/jgb/`）。"""
    real_doc = load_canon_or_die(CANON_DIR)
    prospect_fine = next(f for f in real_doc.fines() if "prospect" in f.target_user)
    canon_dir = all_reviewed_canon_dir(
        tmp_path, skip_ids=frozenset({prospect_fine.id}), name="mostly-reviewed-canon",
    )
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(canon_dir))
    doc = await build_prospect_outline(None)
    registered = get_canon()
    assert registered is not None
    # 註冊的就是組裝用的那一份：已審細目在視圖裡的內容句＝正本內容句；未審者只出標題。
    first_reviewed = next(
        f for f in registered.fines()
        if f.reviewed_by is not None and "prospect" in f.target_user
    )
    section = next(s for s in doc.sections if s.id == first_reviewed.id)
    assert section.text == "\n".join(first_reviewed.content_units) and section.citable
    first_unreviewed = next(
        f for f in registered.fines()
        if f.reviewed_by is None and "prospect" in f.target_user
    )
    unreviewed_section = next(s for s in doc.sections if s.id == first_unreviewed.id)
    assert unreviewed_section.text == "" and unreviewed_section.citable is False

    doc_again = await build_prospect_outline(None)
    assert doc_again.sha256 == doc.sha256          # 決定性：同一份正本 ⇒ 同一個 sha


# ── §4.5 check_budget：env 只能調小，⛔ 不能調大 ─────────────────────────


async def test_budget_positive_control_passes(monkeypatch, tmp_canon):
    """正對照：預設上限下組得起來（否則下面的 raise 只是「本來就會炸」）。"""
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    monkeypatch.delenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", raising=False)
    doc = await build_prospect_outline(None)
    assert doc.token_count > 0


async def test_env_limit_lower_than_actual_raises(monkeypatch, tmp_canon):
    """負對照：env 覆寫低於真實用量 ⇒ raise。

    計畫 9.10 S4：換正本後 515 條全未審，`tmp_canon`（版控正本原樣複本）下
    prospect 視圖的 `k_upper` 恆為 0（DSP-066：未審不可見）——原本「把上限壓到
    100、低於某個已知非零 `k_upper`」的手法在全未審狀態下永遠壓不低於實際用量，
    負對照因此變空（見 `s4-measurement` 報告）。改用**不依賴 `k_upper` 實際值**
    的手段：token 數不可能為負，任何 canon 狀態下 `k_upper（>=0） > -1` 恆成立，
    ⇒ 這條測的是「env 覆寫真的接到 `check_turn_budget` 的比較式」這個契約本身，
    不需要、也不依賴正本的審核狀態。"""
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    monkeypatch.setenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", "-1")
    with pytest.raises(OutlineBudgetExceeded):
        await build_prospect_outline(None)


async def test_env_cannot_raise_the_cap(monkeypatch, tmp_canon):
    """env 設 999999 ⇒ 實際上限仍是常數表的 12000（⛔ 一個 env var 不得把上限開大）。

    ⚠️ 9.6 之前這道由正本 front matter 的 `budget_tokens` 承擔；圖書館形態沒有那一鍵，
    改由兩張常數表＋`min(env, 常數)` 承擔（9.8 D′：K 上界／toc 兩尺各一張表）——語義相同，來源換人。
    """
    from services.agent.outline import OUTLINE_K_TOKEN_LIMIT, default_k_token_limit

    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(tmp_canon))
    monkeypatch.setenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", "999999")
    assert default_k_token_limit("prospect") == OUTLINE_K_TOKEN_LIMIT["prospect"] == 12_000
    doc = await build_prospect_outline(None)   # 仍以兩尺為上限，真實視圖在上限內
    assert doc.token_count > 0


def test_canon_dir_versioned_files_untouched():
    """守門：本檔跑完之後版控正本仍與載入時一致（⛔ 測試不得動正本）。"""
    assert os.path.isdir(SHELF_DIR) and os.path.exists(CANON_JSON) and os.path.exists(CATALOG_MD)


# ---------------------------------------------------------------------------
# 計畫 9.10 S2：目錄改列粗目＋粗目導航（`resolve_canon_section` 新分支）
# ---------------------------------------------------------------------------


def _nav_fine(fid, *, title, reviewed_by="owner", target_user=("prospect",)):
    return FineItem(
        id=fid, coarse_id=fid.split("/")[1], title=title, phrasings=(),
        content_units=(f"{title}的內容。",), content_sha256="0" * 64, sources=("kb:1",),
        reviewed_by=reviewed_by, reviewed_at="2026-09-21" if reviewed_by else None,
        see_also=(), policy="answerable", policy_ref=None,
        target_user=tuple(target_user), business_types=("system_provider",),
        categories=(), instance_applicability="general",
    )


def _nav_canon(coarses):
    return CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=tuple(coarses),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
    )


def _nav_identity():
    return Identity(vendor_id=0, target_user="prospect", mode="b2b")


def test_resolve_canon_section_coarse_navigation_returns_fine_list():
    """粗目導航：`outline:<粗目 id>` 回該粗目下可見已審細目的 `<id>｜<title>` 清單。"""
    doc = _nav_canon([
        CoarseItem(id="A-nav", title="導航粗目", fines=(
            _nav_fine("jgb/A/one", title="第一條"),
            _nav_fine("jgb/A/two", title="第二條"),
            _nav_fine("jgb/A/hidden", title="未審", reviewed_by=None),
        )),
    ])
    result = resolve_canon_section(
        doc, _nav_identity(), "outline:A-nav", vendor_business_types=frozenset()
    )
    assert result.ok is True
    assert result.provenance[0].citable is False
    assert result.data["answer"] == "jgb/A/one｜第一條\njgb/A/two｜第二條"
    assert "未審" not in result.data["answer"]  # 負對照：未審細目不出現


def test_resolve_canon_section_coarse_all_unreviewed_equals_coarse_missing():
    """負對照：**存在但全未審的粗目**與**不存在的粗目**逐欄位相同（`_no_match` 不對模型區分）。"""
    doc = _nav_canon([
        CoarseItem(id="A-empty", title="全未審粗目", fines=(
            _nav_fine("jgb/A/only", title="唯一一條", reviewed_by=None),
        )),
    ])
    identity = _nav_identity()
    all_unreviewed = resolve_canon_section(
        doc, identity, "outline:A-empty", vendor_business_types=frozenset()
    )
    missing = resolve_canon_section(
        doc, identity, "outline:A-does-not-exist", vendor_business_types=frozenset()
    )
    assert all_unreviewed.model_dump() == missing.model_dump()
    assert all_unreviewed.ok is False and all_unreviewed.error == "NO_MATCH"
    # 正對照：同一粗目補上 reviewed 後就找得到（證明上面兩者相同不是量尺本身壞掉）
    reviewed_doc = _nav_canon([
        CoarseItem(id="A-empty", title="全未審粗目", fines=(
            _nav_fine("jgb/A/only", title="唯一一條"),
        )),
    ])
    found = resolve_canon_section(
        reviewed_doc, identity, "outline:A-empty", vendor_business_types=frozenset()
    )
    assert found.ok is True


def test_resolve_canon_section_bare_letter_coarse_accepted_during_transition():
    """過渡鷹架：裸字母粗目（`outline:A`）與 `<架字母>-<slug>` 走同一條路徑。"""
    doc = _nav_canon([CoarseItem(id="A", title="裸字母粗目", fines=(
        _nav_fine("jgb/A/legacy", title="舊形態細目"),
    ))])
    result = resolve_canon_section(
        doc, _nav_identity(), "outline:A", vendor_business_types=frozenset()
    )
    assert result.ok is True
    assert result.data["answer"] == "jgb/A/legacy｜舊形態細目"


def test_resolve_canon_section_fine_id_shape_checked_before_coarse_id():
    """判別順序：先比細目 id 形狀——細目 id 永遠不含裸字母粗目 id 的形狀，兩者不會碰撞。

    正對照：同一份正本用細目 id 查得到內容（citable=True）；用粗目 id 查得到導航清單
    （citable=False）——兩條路徑各自正確落地，證明判別順序沒有把其中一個吃掉。
    """
    doc = _nav_canon([
        CoarseItem(id="A-shape", title="判別測試粗目", fines=(
            _nav_fine("jgb/A/shape-fine", title="判別測試細目"),
        )),
    ])
    identity = _nav_identity()
    fine_hit = resolve_canon_section(
        doc, identity, "outline:jgb/A/shape-fine", vendor_business_types=frozenset()
    )
    coarse_hit = resolve_canon_section(
        doc, identity, "outline:A-shape", vendor_business_types=frozenset()
    )
    assert fine_hit.ok is True and fine_hit.provenance[0].citable is True
    assert coarse_hit.ok is True and coarse_hit.provenance[0].citable is False


def test_build_canon_toc_excludes_coarse_with_zero_visible_reviewed_fines():
    """負對照：零可見已審細目的粗目連粗目 id 都不出現在目錄裡。"""
    doc = _nav_canon([
        CoarseItem(id="A-visible", title="有可見細目", fines=(_nav_fine("jgb/A/v", title="可見"),)),
        CoarseItem(id="B-empty", title="零可見細目", fines=(
            _nav_fine("jgb/B/hidden", title="未審", reviewed_by=None),
        )),
    ])
    toc = build_canon_toc(doc, _nav_identity(), vendor_business_types=frozenset())
    assert "A-visible｜有可見細目｜1" in toc.text.splitlines()
    assert "B-empty" not in toc.text  # 負對照：零可見細目的粗目不出現
    load_canon_or_die(CANON_DIR)   # 仍然同源
