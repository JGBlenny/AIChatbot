"""unit：Plan 9.26——頁面入口檔閉包 `page_import_closure.py`（import 鏈＋子路由，只收 `src/pages/`）。
Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.26-page-metric-closure-20261004.md` §1。
以 tmp 目錄合成一份最小 jgb2 匯出（`src/pages`、`src/components`、`src/routes`）。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))
_REPO = os.path.dirname(_RAG)
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")

if not os.path.isdir(_SCRIPTS):  # pragma: no cover
    pytest.skip(f"[env] 找不到 {_SCRIPTS}——容器需掛 repo 根 .claude/", allow_module_level=True)
sys.path.insert(0, _SCRIPTS)
import page_import_closure as pic  # noqa: E402

_FILES = {
    # 忘記密碼頁：畫面由子路由渲染（router-view），子路由陣列以 ...forgetChildren 展開
    "src/pages/users/auth/Forget.vue": "import Layout from '@src/pages/users/auth/Layout.vue'\n<router-view />",
    "src/pages/users/auth/Layout.vue": "<div/>",
    "src/pages/users/auth/parts/forget/Password.vue": "import Panel from '../VerifyPanel.vue'",
    "src/pages/users/auth/parts/VerifyPanel.vue": "import Btn from '@src/components/BottomNav.vue'",
    # 同目錄兄弟頁：⛔ 被忘記密碼頁的閉包吸進來
    "src/pages/users/auth/Login.vue": "import Form from './parts/LoginForm'",
    "src/pages/users/auth/parts/LoginForm.vue": "<form/>",
    "src/components/BottomNav.vue": "<nav/>",
    "src/routes/users.js": (
        "/* 註解裡的 children: [ 不算 */\n"
        "const forgetChildren = [\n"
        "    { name: 'users.forget.password', path: 'password',"
        " component: ()=>import('@src/pages/users/auth/parts/forget/Password.vue') },\n"
        "]\n"
        "export default [\n"
        "    { name: 'users.login', path: '/login', component: ()=>import('@src/pages/users/auth/Login.vue') },\n"
        "    { name: 'users.forget', path: '/forget', component: ()=>import('@src/pages/users/auth/Forget.vue'),\n"
        "      children: [\n"
        "        ...forgetChildren,\n"
        "      ] },\n"
        "]\n"
    ),
}


def _export(tmp_path):
    root = tmp_path / "export"
    for rel, body in _FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return str(root)


def _units(*comps):
    return [{"kind": "spa", "component": c, "in_baseline": True} for c in comps]


def test_children_spread_and_imports_are_followed(tmp_path):
    out = pic.build(_export(tmp_path), _units("users/auth/Forget.vue", "users/auth/Login.vue"))
    assert out["users/auth/Forget.vue"] == [
        "users/auth/Forget.vue", "users/auth/Layout.vue",
        "users/auth/parts/VerifyPanel.vue", "users/auth/parts/forget/Password.vue",
    ]
    # 相對路徑＋省略副檔名
    assert out["users/auth/Login.vue"] == ["users/auth/Login.vue", "users/auth/parts/LoginForm.vue"]


def test_siblings_and_shared_components_are_excluded(tmp_path):
    out = pic.build(_export(tmp_path), _units("users/auth/Forget.vue", "users/auth/Login.vue"))
    assert "users/auth/Login.vue" not in out["users/auth/Forget.vue"]  # 同目錄兄弟頁不互入
    assert "users/auth/Forget.vue" not in out["users/auth/Login.vue"]
    assert not any("components" in f or f.startswith("..") for v in out.values() for f in v)  # 共用元件不收


def test_route_children_resolves_spread(tmp_path):
    kids = pic.route_children(_export(tmp_path))
    assert kids == {"users/auth/Forget.vue": ["users/auth/parts/forget/Password.vue"]}


def test_missing_entry_or_export_fails_loudly(tmp_path):
    root = _export(tmp_path)
    assert pic.build(root, _units("users/auth/Login.vue"))  # 正對照
    with pytest.raises(SystemExit):
        pic.build(root, _units("users/auth/Nope.vue"))
    surface = tmp_path / "s.json"
    surface.write_text(json.dumps({"payload": {"units": _units("users/auth/Login.vue")}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        pic.main(["--export", str(tmp_path / "nope"), "--surface", str(surface), "--sha", "x",
                  "--out", str(tmp_path / "o.json")])
