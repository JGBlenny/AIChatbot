"""unit：Plan 9.15 S1——終點指標 `endpoint_progress.py`（M1 已審細目數、M2 頁面覆蓋）。
Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.15-reviewed-canon-progress-20260926.md` §1、§2 S1。
正本用既有合成 fixture `tests/fixtures/canon_jgb/shelves`（6 條細目、3 條已審）；page-surface 為合成單位。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import types

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))  # host: <repo>/rag-orchestrator；容器：/app
_REPO = os.path.dirname(_RAG)
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")
_SHELVES = os.path.join(_RAG, "tests", "fixtures", "canon_jgb", "shelves")

if not os.path.isdir(_SCRIPTS):  # pragma: no cover
    pytest.skip(f"[env] 找不到 {_SCRIPTS}——容器需掛 repo 根 .claude/", allow_module_level=True)
sys.path.insert(0, _SCRIPTS)
import endpoint_progress as ep  # noqa: E402

#: 合成頁面樹：兩頁會被已審細目命中（SPA＋blade）、一頁只被未審細目命中、一頁不在基準
_UNITS = [
    {"kind": "spa", "component": "users/register/Index.vue", "in_baseline": True},
    {"kind": "blade", "component": "ListingController@index", "in_baseline": True},
    {"kind": "spa", "component": "users/forget/Index.vue", "in_baseline": True},
    {"kind": "spa", "component": "users/register/Index.vue", "in_baseline": False},
]


def _canon(tmp_path):
    dst = tmp_path / "shelves"
    shutil.copytree(_SHELVES, dst)
    a = dst / "A.md"
    text = a.read_text(encoding="utf-8")
    old_reviewed, old_unreviewed = "- sources: [kb:3585]", "- sources: [kb:3586]"
    assert old_reviewed in text and old_unreviewed in text, "fixture 已變"
    text = text.replace(old_reviewed, "- sources: [kb:3585, code:src/pages/users/register/Index.vue, "
                                      "code:app/Http/Controllers/Front/ListingController.php]", 1)
    text = text.replace(old_unreviewed, "- sources: [kb:3586, code:src/pages/users/forget/Index.vue]", 1)
    a.write_text(text, encoding="utf-8")
    return str(dst)


def _surface(tmp_path):
    p = tmp_path / "surface.json"
    p.write_text(json.dumps({"step": "page_surface", "payload": {"units": _UNITS}}), encoding="utf-8")
    return str(p)


def test_m1_counts_reviewed_per_identity(tmp_path):
    m = ep.measure(_canon(tmp_path), _surface(tmp_path))
    assert m["fines"] == 6 and m["pages"] == 3
    assert m["by_identity"]["property_manager"] == {"reviewed": 2, "total": 4, "pages": 2}
    assert m["by_identity"]["prospect"]["reviewed"] == 2 and m["by_identity"]["prospect"]["total"] == 3
    assert m["by_shelf"]["A"]["property_manager"] == [1, 2]
    assert ep.headline(m).startswith("已審細目 pm 2／4、prospect 2／3；頁面 pm 2／3")


def test_m2_counts_spa_and_blade_but_not_unreviewed_hits(tmp_path):
    m = ep.measure(_canon(tmp_path), _surface(tmp_path))
    # 已審的 account-registration 命中 SPA＋blade 各一頁 ⇒ 2；未審的 password-reset 命中的第三頁不計
    assert m["by_identity"]["property_manager"]["pages"] == 2
    assert m["by_identity"]["prospect"]["pages"] == 2


def test_ignore_review_is_the_positive_control(tmp_path):
    m = ep.measure(_canon(tmp_path), _surface(tmp_path), ignore_review=True)
    assert m["pages_any_identity_ignore_review"] == 3  # 未審命中的頁也算進來 ⇒ 比對器確實會命中
    assert m["by_identity"]["property_manager"]["reviewed"] == 2  # M1 不受旗標影響


def test_missing_inputs_fail_loudly(tmp_path):
    canon = _canon(tmp_path)
    assert ep.measure(canon, _surface(tmp_path))["fines"] == 6  # 正對照：同一份輸入在齊全時可量
    with pytest.raises(SystemExit):
        ep.measure(str(tmp_path / "nope"), _surface(tmp_path))
    with pytest.raises(SystemExit):
        ep.measure(canon, str(tmp_path / "nope.json"))
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"payload": {"units": [dict(_UNITS[3])]}}), encoding="utf-8")
    with pytest.raises(SystemExit):  # in_baseline 0 頁
        ep.measure(canon, str(empty))


def test_blank_reviewed_by_counts_as_unreviewed():
    assert ep.is_reviewed(types.SimpleNamespace(reviewed_by="owner"))
    assert not ep.is_reviewed(types.SimpleNamespace(reviewed_by=""))
    assert not ep.is_reviewed(types.SimpleNamespace(reviewed_by="  "))
    assert not ep.is_reviewed(types.SimpleNamespace(reviewed_by=None))


# ---------- Plan 9.26：閉包量尺與 `#方法` 去除 ----------
#: 合成閉包：入口檔 users/register/Index.vue 的畫面另由子元件 parts/Form.vue 渲染
_CLOSURE = {"users/register/Index.vue": ["users/register/Index.vue", "users/register/parts/Form.vue"],
            "users/forget/Index.vue": ["users/forget/Index.vue"]}


def _canon_citing(tmp_path, reviewed_src: str):
    """複本：已審細目只引用 `reviewed_src`（不引用入口檔）。"""
    dst = tmp_path / "shelves"
    shutil.copytree(_SHELVES, dst)
    a = dst / "A.md"
    text = a.read_text(encoding="utf-8")
    assert "- sources: [kb:3585]" in text, "fixture 已變"
    a.write_text(text.replace("- sources: [kb:3585]", f"- sources: [kb:3585, {reviewed_src}]", 1), encoding="utf-8")
    return str(dst)


def test_closure_counts_subcomponent_citation(tmp_path):
    canon = _canon_citing(tmp_path, "code:src/pages/users/register/parts/Form.vue")
    surface = _surface(tmp_path)
    # 正對照：給閉包 ⇒ 引用子元件的已審細目點亮該頁
    assert ep.measure(canon, surface, closure=_CLOSURE)["by_identity"]["property_manager"]["pages"] == 1
    # 舊量尺（不給閉包）只比入口檔 ⇒ 同一份輸入不命中
    assert ep.measure(canon, surface)["by_identity"]["property_manager"]["pages"] == 0


def test_closure_missing_page_fails_loudly(tmp_path):
    canon = _canon_citing(tmp_path, "code:src/pages/users/register/parts/Form.vue")
    partial = {"users/register/Index.vue": _CLOSURE["users/register/Index.vue"]}  # 缺 users/forget/Index.vue
    with pytest.raises(SystemExit):
        ep.measure(canon, _surface(tmp_path), closure=partial)


def test_blade_hit_strips_method_suffix():
    unit = {"kind": "blade", "component": "NotificationController@index"}
    fine = types.SimpleNamespace(sources=["code:app/Http/Controllers/NotificationController.php#index"])
    assert ep.page_hit(unit, ep.code_paths(fine))
    # 負對照：別的 controller 不命中
    other = types.SimpleNamespace(sources=["code:app/Http/Controllers/UserController.php#index"])
    assert not ep.page_hit(unit, ep.code_paths(other))


def test_load_closure_fails_loudly(tmp_path):
    good = tmp_path / "c.json"
    good.write_text(json.dumps({"sha": "x", "pages": _CLOSURE}), encoding="utf-8")
    assert ep.load_closure(str(good)) == _CLOSURE  # 正對照
    assert ep.load_closure(None) is None
    with pytest.raises(SystemExit):
        ep.load_closure(str(tmp_path / "nope.json"))
    empty = tmp_path / "e.json"
    empty.write_text(json.dumps({"sha": "x", "pages": {}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        ep.load_closure(str(empty))
