"""不變量 33／34 的 unit 收編（spec knowledge-outline-and-intent-architecture・任務 3.5）。

`scripts/audit/checks/canon_visibility_reconcile.py`／`canon_phrasing_frozen_disjoint.py`
本身各有 `--self-test`（CLI 層的正/反對照）；本檔補的是 pytest 收編，讓 `make test`／CI
也跑得到這兩條 checker，不必額外記得跑 `make audit`。⛔ 不重寫 checker 邏輯，只呼叫它。

⚠️ 33 的 DB／容器子檢查（`docker exec`）：測試容器內沒有 docker，故本檔對 33 一律走
`--self-test`（本身已全程注入假依賴、⛔ 不連 docker／DB，見該檔模組 docstring）；
34 不需要 docker，`check_canon_phrasing_frozen_disjoint()` 直接對現樹跑（真跑一次
額外覆蓋「現樹真的講法／凍結題不相交」這個事實斷言）。
"""
import importlib.util
import os

import pytest

pytestmark = pytest.mark.unit

_SPEC = "knowledge-outline-and-intent-architecture:3.5"

_RAG_ROOT = os.path.dirname(  # rag-orchestrator/
    os.path.dirname(  # tests/
        os.path.dirname(  # tests/unit/
            os.path.dirname(os.path.abspath(__file__))  # tests/unit/audit/
        )
    )
)
_REPO_ROOT = os.path.dirname(_RAG_ROOT)
_V33_PY = os.path.join(_REPO_ROOT, "scripts", "audit", "checks", "canon_visibility_reconcile.py")
_V34_PY = os.path.join(_REPO_ROOT, "scripts", "audit", "checks", "canon_phrasing_frozen_disjoint.py")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def v33():
    assert os.path.exists(_V33_PY), f"{_V33_PY} 不存在——checker 檔案位置變了"
    return _load(_V33_PY, "canon_visibility_reconcile_checker")


@pytest.fixture(scope="module")
def v34():
    assert os.path.exists(_V34_PY), f"{_V34_PY} 不存在——checker 檔案位置變了"
    return _load(_V34_PY, "canon_phrasing_frozen_disjoint_checker")


# ── 33：正本可見性與 kb 衍生列三軸對帳 ──────────────────────────────────

@pytest.mark.req(_SPEC)
def test_33_self_test_passes(v33):
    """⛔ 這條紅了不代表現況違規，代表 checker 本身壞了——其餘 33 斷言不可信。"""
    assert v33.self_test() == 0


@pytest.mark.req(_SPEC)
def test_33_zero_derived_rows_is_skip_not_fail(v33):
    ok, detail = v33.check_canon_visibility_reconcile(query=lambda: "")
    assert ok is None
    assert "pending-D1" in detail


@pytest.mark.req(_SPEC)
def test_33_query_exception_is_fail_not_skip(v33):
    """CLAUDE.md 否定結論鐵則：查詢失敗 ⛔ 不得偽裝成「沒有列」的 SKIP。"""
    def _raise():
        raise RuntimeError("Cannot connect to the Docker daemon（測試模擬）")
    ok, _detail = v33.check_canon_visibility_reconcile(query=_raise)
    assert ok is False


@pytest.mark.req(_SPEC)
def test_33_required_group_zero_hits_is_fail(v33):
    """空跑不得綠：必查組命中 0 列必須紅，即使另一必查組命中正常。"""
    fine_map = {
        "A": {"business_types": ["system_provider"], "target_user": []},
        "C": {"business_types": ["system_provider"], "target_user": ["prospect"]},
    }
    mem_fn = v33._fake_mem_visible_fn(fine_map)
    pred_fn = v33._fake_predicate_fn(
        mem_fn, override={("property_manager", "b2b"): frozenset()}
    )
    raw = "103~|~C~|~{system_provider}~|~{prospect}\n"
    ok, detail = v33.check_canon_visibility_reconcile(
        query=lambda: raw,
        predicate_visible_fn=pred_fn,
        mem_visible_fn=mem_fn,
        canon_fine_map_fn=lambda: fine_map,
        vendor_business_types_fn=lambda _vid: [],
    )
    assert ok is False
    assert "b2b pm" in detail


@pytest.mark.req(_SPEC)
def test_33_business_types_null_vs_canon_empty_mismatch_is_fail(v33):
    """owner 對帳（2026-09-07）：business_types NULL ⇔ 正本該欄空清單，破例必紅。"""
    fine_map = {"A": {"business_types": [], "target_user": []}}
    # 正本該欄空清單，但衍生列卻有值（模擬被預設成 system_provider）——不對帳。
    raw = "101~|~A~|~{system_provider}~|~<NULL>\n"
    ok, detail = v33.check_canon_visibility_reconcile(
        query=lambda: raw,
        canon_fine_map_fn=lambda: fine_map,
    )
    assert ok is False
    assert "對不上" in detail


@pytest.mark.req(_SPEC)
def test_33_empty_array_literal_is_always_fail(v33):
    """owner 對帳：business_types 出現字面 '{}'（空陣列非 NULL）一律紅。"""
    fine_map = {"A": {"business_types": ["system_provider"], "target_user": []}}
    raw = "101~|~A~|~{}~|~<NULL>\n"
    ok, detail = v33.check_canon_visibility_reconcile(
        query=lambda: raw,
        canon_fine_map_fn=lambda: fine_map,
    )
    assert ok is False
    assert "'{}'" in detail


# ── 34：凍結題不入講法 ───────────────────────────────────────────────────

@pytest.mark.req(_SPEC)
def test_34_self_test_passes(v34):
    assert v34.self_test() == 0


@pytest.mark.req(_SPEC)
def test_34_nfkc_normalization_catches_fullwidth_variant(v34, tmp_path):
    """正對照：全形／半形視為同一句（NFKC）——塞一句必紅。"""
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    v34._write_canon(str(canon_dir), ["ＡＢＣ全形測試"])
    manifest_dir = tmp_path / "manifest"
    manifest_dir.mkdir()
    v34._write_manifest(str(manifest_dir), ["ABC全形測試"])
    ok, _detail = v34.check_canon_phrasing_frozen_disjoint(
        canon_glob_abs=str(canon_dir / "*.json"),
        manifest_abs=str(manifest_dir / "samples-manifest.json"),
    )
    assert ok is False


@pytest.mark.req(_SPEC)
def test_34_missing_manifest_set_file_is_fail_not_empty(v34, tmp_path):
    """跨 spec 依賴（E8）：凍結樣本檔缺讀 ⇒ 大聲失敗，⛔ 不當成 0 句。"""
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    v34._write_canon(str(canon_dir), ["測試講法"])
    manifest_dir = tmp_path / "manifest"
    manifest_dir.mkdir()
    manifest_path = v34._write_manifest(str(manifest_dir), ["測試題句"])
    os.remove(os.path.join(str(manifest_dir), "sensitive-v1.json"))
    ok, detail = v34.check_canon_phrasing_frozen_disjoint(
        canon_glob_abs=str(canon_dir / "*.json"), manifest_abs=manifest_path)
    assert ok is False
    assert "讀不到" in detail or "凍結題句收集失敗" in detail


@pytest.mark.req(_SPEC)
def test_34_real_repo_canon_and_manifest_are_scanned_not_empty(v34):
    """正對照（CLAUDE.md 否定結論鐵則）：現樹真的掃到講法與凍結題，⛔ 不是空跑。"""
    phrasings, canon_files = v34.collect_canon_phrasings(v34._resolve_canon_glob())
    assert len(phrasings) > 0
    assert len(canon_files) > 0
    frozen, counts, sample_files = v34.collect_frozen_questions(v34._resolve_manifest_path())
    assert len(frozen) > 0
    assert len(sample_files) >= 1
    assert counts  # 至少一個 set 被讀到
