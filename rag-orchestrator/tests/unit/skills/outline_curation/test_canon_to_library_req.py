"""unit：`scripts/canon_to_library.py`（DSP-058／計畫 9.6 S1）。

驗：兩份舊受眾正本 → 一目錄＋九架（H 空架亦產）；檔級預設**落成明列** `target_user`／
`business_types`；id 前綴改 `jgb/` 且 `see_also` 同步 remap；其餘屬性與內容逐字原樣；
決定性（同輸入兩次逐位元相同）；`id_map.json` 是 `remap_ids.py` 吃得下的裸陣列；
停點（同架同 slug 碰撞／version 不一致／scope 缺）各自 exit 2 且**不留半套產出**。

材料一律合成（⛔ 不讀版控正本——那是 S1 驗收 ⑩ 的整合跑，不是 unit 的事）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "canon_to_library.py")
_SCOPES_SRC = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas", "scopes-jgb.json")

_CODES = "ABCDEFGHI"
_TITLES = {
    "A": "帳號與身分", "B": "團隊、人員與大房東", "C": "社區與物件",
    "D": "租約（含委託約子題）", "E": "帳務（含發票、收款金流、抄表）", "F": "修繕",
    "G": "裝置（IoT）", "H": "幫助中心", "I": "方案與導入",
}


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _canon(audience: str, target_user: str, bodies: dict, version: str = "2026-09-15.0") -> str:
    """合成一份舊受眾正本：九個粗目全在，`bodies` 指定哪些粗目底下放細目。"""
    head = (
        "---\n"
        f"audience: {audience}\n"
        f"version: {version}\n"
        "reviewers: [owner]\n"
        "language: zh-TW\n"
        "budget_tokens: 12000\n"
        f"target_user: [{target_user}]\n"
        "business_types: [system_provider]\n"
        "---\n"
    )
    out = [head]
    for code in _CODES:
        out.append(f"## {code} {_TITLES[code]} {{#{code}}}\n")
        out.append(bodies.get(code, ""))
    return "".join(out)


_PROSPECT_A = (
    "### 怎麼註冊帳號 {#prospect/A/account-registration}\n"
    "- phrasings:\n"
    '  - {text: "怎麼註冊帳號", source: "question_summary:3585", status: approved}\n'
    '  - {text: "註冊要多久", source: "koyu:03#12", status: proposed}\n'
    "- sources: [kb:3585]\n"
    "- reviewed: {by: owner, at: 2026-09-15}\n"
    "- see_also: [prospect/C/estate-import]\n"
    "- categories: [帳號]\n"
    "- instance_applicability: general\n"
    "註冊後系統會寄出驗證碼通知。\n"
    "驗證完成才能建立第一個社區。\n"
)
_PROSPECT_C = (
    "### 物件批次匯入 {#prospect/C/estate-import}\n"
    "- policy: deliberate_no\n"
    "- policy_ref: DSP-009\n"
    "- instance_applicability: instance\n"
    "物件可以用試算表批次匯入。\n"
)
_PM_B = (
    "### 怎麼邀請團隊成員 {#property_manager/B/team-invite}\n"
    "- sources: [kb:3600]\n"
    "- instance_applicability: general\n"
    "團隊管理頁可以寄出邀請信。\n"
)


@pytest.fixture
def inputs(tmp_path):
    _skip_if_missing()
    prospect = tmp_path / "prospect.md"
    pm = tmp_path / "property_manager.md"
    prospect.write_text(_canon("prospect", "prospect", {"A": _PROSPECT_A, "C": _PROSPECT_C}), encoding="utf-8")
    pm.write_text(_canon("property_manager", "property_manager", {"B": _PM_B}), encoding="utf-8")
    scopes = tmp_path / "scopes.json"
    scopes.write_text(json.dumps({c: f"{_TITLES[c]} 的歸位判準" for c in _CODES}, ensure_ascii=False), encoding="utf-8")
    return prospect, pm, scopes


def _run(inputs, out, extra=None):
    prospect, pm, scopes = inputs
    cmd = [sys.executable, _SCRIPT, "--prospect", str(prospect), "--pm", str(pm),
           "--scopes", str(scopes), "--out", str(out)] + list(extra or [])
    return subprocess.run(cmd, capture_output=True, text=True)


def test_produces_nine_shelves_plus_derived(inputs, tmp_path):
    out = tmp_path / "lib"
    proc = _run(inputs, out, ["--id-map-out", str(tmp_path / "id_map.json")])
    assert proc.returncode == 0, proc.stderr
    assert sorted(p.name for p in out.iterdir()) == \
        ["A.md", "B.md", "C.md", "CATALOG.md", "D.md", "E.md", "F.md", "G.md", "H.md", "I.md", "jgb.json"]
    # H 是空架：只有 front matter ＋粗目標題，零細目
    assert "###" not in (out / "H.md").read_text(encoding="utf-8")


def test_output_reparses_and_materializes_axes(inputs, tmp_path):
    """檔級預設落成**明列**——圖書館形態沒有檔級預設，隔離只認明列成員（DSP-058）。"""
    out = tmp_path / "lib"
    assert _run(inputs, out).returncode == 0
    sys.path.insert(0, os.path.join(_REPO, "rag-orchestrator"))
    from services.agent.canon.canon_parser import parse_canon_dir  # noqa: E402

    doc = parse_canon_dir(str(out))
    fines = {f.id: f for f in doc.fines()}
    assert sorted(fines) == ["jgb/A/account-registration", "jgb/B/team-invite", "jgb/C/estate-import"]
    assert fines["jgb/A/account-registration"].target_user == ("prospect",)
    assert fines["jgb/B/team-invite"].target_user == ("property_manager",)
    assert all(f.business_types == ("system_provider",) for f in fines.values())
    # 明列而非繼承：架檔裡真的寫了那兩行
    a_text = (out / "A.md").read_text(encoding="utf-8")
    assert "- target_user: [prospect]" in a_text and "- business_types: [system_provider]" in a_text
    # see_also 同步 remap
    assert fines["jgb/A/account-registration"].see_also == ("jgb/C/estate-import",)
    # 其餘屬性逐字原樣
    assert fines["jgb/C/estate-import"].policy == "deliberate_no"
    assert fines["jgb/C/estate-import"].policy_ref == "DSP-009"
    assert fines["jgb/C/estate-import"].instance_applicability == "instance"
    assert fines["jgb/A/account-registration"].categories == ("帳號",)
    assert fines["jgb/A/account-registration"].content_units == (
        "註冊後系統會寄出驗證碼通知。", "驗證完成才能建立第一個社區。")
    assert [(p.text, p.status) for p in fines["jgb/A/account-registration"].phrasings] == [
        ("怎麼註冊帳號", "approved"), ("註冊要多久", "proposed")]
    # front matter 恰六鍵、⛔ 無 budget_tokens
    assert "budget_tokens" not in a_text
    assert doc.budget_tokens == 0


def test_deterministic_two_runs_byte_identical(inputs, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert _run(inputs, a).returncode == 0
    assert _run(inputs, b).returncode == 0
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(p.name for p in b.iterdir())
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
    # 正對照：動一個位元就測得出來（證明上面的相等不是「兩邊都空」）
    assert len((a / "A.md").read_bytes()) > 100
    assert (a / "A.md").read_bytes() != (a / "A.md").read_bytes() + b"x"


def test_id_map_is_bare_array_readable_by_remap_ids(inputs, tmp_path):
    out, id_map = tmp_path / "lib", tmp_path / "id_map.json"
    assert _run(inputs, out, ["--id-map-out", str(id_map)]).returncode == 0
    data = json.loads(id_map.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 3
    assert all(set(e) == {"old", "new", "op"} and e["op"] == "keep" for e in data)
    assert {e["old"]: e["new"] for e in data}["prospect/A/account-registration"] == "jgb/A/account-registration"

    # 真的餵給 remap_ids.py（正對照：它改得動、且報表認得出來）
    remap = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "remap_ids.py")
    material = tmp_path / "material.json"
    material.write_text('{"rows": [{"fine_id": "prospect/A/account-registration"}]}\n', encoding="utf-8")
    proc = subprocess.run([sys.executable, remap, "--id-map", str(id_map), "--files", str(material)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "jgb/A/account-registration" in proc.stdout


def test_same_shelf_same_slug_collision_stops(inputs, tmp_path):
    """停點：同架同 slug 碰撞 ⇒ exit 2 列出，⛔ 不自動改名、⛔ 不留半套產出。"""
    prospect, pm, scopes = inputs
    pm.write_text(_canon("property_manager", "property_manager", {
        "A": _PM_B.replace("property_manager/B/team-invite", "property_manager/A/account-registration"),
    }), encoding="utf-8")
    out = tmp_path / "lib"
    proc = _run((prospect, pm, scopes), out)
    assert proc.returncode == 2
    assert "碰撞" in proc.stderr and "A/account-registration" in proc.stderr
    assert not out.exists(), "停點觸發時 ⛔ 不得留下半套產出"


def test_version_mismatch_stops_unless_given(inputs, tmp_path):
    prospect, pm, scopes = inputs
    pm.write_text(_canon("property_manager", "property_manager", {"B": _PM_B}, version="2026-09-16.0"),
                  encoding="utf-8")
    out = tmp_path / "lib"
    proc = _run((prospect, pm, scopes), out)
    assert proc.returncode == 2 and "version 不一致" in proc.stderr
    # 正對照：明確指定 --version 就放行，且寫進每一架
    ok = _run((prospect, pm, scopes), out, ["--version", "2026-09-17.0"])
    assert ok.returncode == 0, ok.stderr
    assert "version: 2026-09-17.0" in (out / "I.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("mutate, expect", [
    (lambda d: d.pop("H"), "缺架 H"),
    (lambda d: d.update({"E": "   "}), "缺架 E"),
])
def test_scopes_must_cover_nine_shelves(inputs, tmp_path, mutate, expect):
    prospect, pm, scopes = inputs
    data = json.loads(scopes.read_text(encoding="utf-8"))
    mutate(data)
    scopes.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    proc = _run((prospect, pm, scopes), tmp_path / "lib")
    assert proc.returncode == 2 and expect in proc.stderr


def test_coarse_title_mismatch_stops(inputs, tmp_path):
    prospect, pm, scopes = inputs
    pm.write_text(pm.read_text(encoding="utf-8").replace("## B 團隊、人員與大房東 {#B}",
                                                        "## B 團隊管理 {#B}"), encoding="utf-8")
    proc = _run((prospect, pm, scopes), tmp_path / "lib")
    assert proc.returncode == 2 and "標題不一致" in proc.stderr


def test_versioned_scopes_file_covers_nine_shelves():
    """版控的 `schemas/scopes-jgb.json`（計畫附錄 A）九架齊全且各有非空 scope。"""
    _skip_if_missing()
    data = json.loads(open(_SCOPES_SRC, encoding="utf-8").read())
    assert [c for c in _CODES if not str(data.get(c, "")).strip()] == []
    assert sorted(k for k in data if not k.startswith("_")) == list(_CODES)
