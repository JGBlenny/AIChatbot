"""unit：`tools/canon_fine_size_lint.py`（DSP-059a——K 上界拉高後的細目大小提示）。

⛔ 這支工具是建議清單，不是 gate；本測試只釘「>threshold 的細目被列出、
<=threshold 的不被列出、彙總行會印」，不測 exit code 以外的行為。
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from services.agent.canon.canon_parser import CanonDoc, CoarseItem, FineItem

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:dsp-059a-lint"),
]


def _fine(fid, title, *, units, target_user=("prospect",), business_types=("system_provider",)):
    return FineItem(
        id=fid,
        coarse_id=fid.split("/")[1],
        title=title,
        phrasings=(),
        content_units=tuple(units),
        content_sha256="0" * 64,
        sources=("kb:1",),
        reviewed_by="owner",
        reviewed_at="2026-09-07",
        see_also=(),
        policy="answerable",
        policy_ref=None,
        target_user=tuple(target_user),
        business_types=tuple(business_types),
        categories=(),
        instance_applicability="general",
    )


def _canon(fines):
    return CanonDoc(
        audience="jgb",
        version="2026-09-18.1",
        reviewers=("owner",),
        language="zh-TW",
        budget_tokens=0,
        target_user=(),
        business_types=(),
        coarses=(CoarseItem(id="A", title="粗目 A", fines=tuple(fines)),),
        canon_sha256="a" * 64,
        phrasing_set_sha256="b" * 64,
        name="jgb",
        library=True,
    )


@pytest.fixture()
def lint_module():
    mod = importlib.import_module("canon_fine_size_lint")
    return importlib.reload(mod)


def test_over_threshold_fine_listed_under_threshold_fine_not_listed(lint_module, monkeypatch, capsys):
    # 一條約 1,600 tokens（灌長文字）、一條約 100 tokens 的短細目
    big = _fine("jgb/A/big", "長細目", units=("字" * 6_400,))
    small = _fine("jgb/A/small", "短細目", units=("這是一句短內容。",))
    doc = _canon([big, small])

    monkeypatch.setattr(lint_module, "load_canon_or_die", lambda canon_dir: doc)
    monkeypatch.setattr(sys, "argv", ["canon_fine_size_lint.py"])

    rc = lint_module.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "jgb/A/big" in out
    assert "jgb/A/small" not in out
    # 正對照：彙總行有印（不是「沒印任何東西」的假陰性）
    assert "over 1500 tokens" in out
    assert "top-5 sum (prospect)" in out
    assert "top-5 sum (property_manager)" in out
