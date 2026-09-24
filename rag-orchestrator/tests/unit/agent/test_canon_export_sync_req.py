"""unit：正本同源硬把關（spec knowledge-outline-and-intent-architecture 任務 2.5；需求 2.9）。

`rag-orchestrator/canon/jgb/[A-I].md` 是唯一正本（DSP-058／9.6 S3）；兩個衍生物必須逐位元等於重導出：
`canon/jgb.json` ＝ `export_json(parse_canon_dir(canon/jgb))`、
`canon/jgb/CATALOG.md` ＝ `export_catalog(...)`——⛔ 手改衍生物或忘了重導出都紅。
正對照：把導出的位元組竄改一位元 ⇒ 必紅（守門真的在看位元組，不是看檔案存在）。

⚠️ ⛔ **不再以 `glob("canon/*.md")` 決定要驗什麼**：舊兩份受眾正本封存後那個 glob 會變成空清單，
整條把關靜默 skip 成綠（2026-09-15 實際踩到）。改成**寫死目錄路徑**，缺檔即紅。
"""
from __future__ import annotations

import os
from dataclasses import replace

import pytest

from services.agent.canon.canon_parser import (
    CANON_NAME, CanonDoc, CanonFormatError, CoarseItem, FineItem, Phrasing,
    export_catalog, export_json, parse_canon, parse_canon_dir,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.5")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # rag-orchestrator/
CANON_DIR = os.path.join(_RAG, "canon")
SHELF_DIR = os.path.join(CANON_DIR, CANON_NAME)
CANON_JSON = os.path.join(CANON_DIR, f"{CANON_NAME}.json")
CATALOG_MD = os.path.join(SHELF_DIR, "CATALOG.md")

SAMPLE = """---
audience: prospect
version: 2026-09-06.1
reviewers: [owner]
language: zh-TW
budget_tokens: 10000
target_user: [prospect]
business_types: [system_provider]
---
## A 產品基本盤 {#A}
### 系統定位 {#prospect/A/positioning}
- sources: [kb:3585]
- instance_applicability: general
金箍棒把物件、合約、收租集中管理。
"""


def _exported_bytes(md_path: str, tmp_dir: str) -> bytes:
    doc = parse_canon(md_path)
    out = os.path.join(tmp_dir, os.path.basename(md_path)[:-3] + ".json")
    export_json(doc, out)
    with open(out, "rb") as fh:
        return fh.read()


def test_canon_dir_exists():
    """正對照的正對照：⛔ 目錄／衍生物不在就是紅，不是 skip（那會讓下面兩條靜默變綠）。"""
    assert os.path.isdir(SHELF_DIR), f"缺正本目錄 {SHELF_DIR}"
    assert os.path.isfile(CANON_JSON), f"缺版控導出檔 {CANON_JSON}：請跑 export_json 並一起提交"
    assert os.path.isfile(CATALOG_MD), f"缺版控衍生目錄 {CATALOG_MD}：請跑 export_catalog 並一起提交"


def test_versioned_json_is_byte_identical_to_export(tmp_path):
    """版控 `jgb.json` ＝ 重新導出的 JSON（逐位元）。"""
    doc = parse_canon_dir(SHELF_DIR)
    out = str(tmp_path / "jgb.json")
    export_json(doc, out)
    with open(CANON_JSON, "rb") as fh:
        versioned = fh.read()
    with open(out, "rb") as fh:
        exported = fh.read()
    assert versioned == exported, f"{CANON_JSON} 與九架導出不一致：JSON 是衍生物，請重導出"


def test_versioned_catalog_is_byte_identical_to_export(tmp_path):
    """版控 `CATALOG.md` ＝ 重新導出的目錄（逐位元）。"""
    doc = parse_canon_dir(SHELF_DIR)
    out = str(tmp_path / "CATALOG.md")
    export_catalog(doc, out)
    with open(CATALOG_MD, "rb") as fh:
        versioned = fh.read()
    with open(out, "rb") as fh:
        exported = fh.read()
    assert versioned == exported, f"{CATALOG_MD} 與九架導出不一致：目錄是衍生物，請重導出"


def test_tampering_one_byte_is_detected(tmp_path):
    """正對照：同一份正本，導出兩次逐位元相同；把其中一份改一位元 ⇒ 比對必紅。"""
    md = tmp_path / "prospect.md"
    md.write_text(SAMPLE, encoding="utf-8")
    a = _exported_bytes(str(md), str(tmp_path / "a")) if (tmp_path / "a").mkdir() is None else b""
    b = _exported_bytes(str(md), str(tmp_path / "b")) if (tmp_path / "b").mkdir() is None else b""
    assert a == b and len(a) > 100
    tampered = bytearray(a)
    idx = a.index(b'"version"') + len(b'"version": "') + 1
    tampered[idx] = ord("9") if tampered[idx] != ord("9") else ord("8")
    assert bytes(tampered) != a
    # 竄改 Markdown 一個字 ⇒ 導出也變（canon_sha256 隨位元組走）
    md2 = tmp_path / "prospect2.md"
    md2.write_text(SAMPLE.replace("集中管理。", "集中管理！"), encoding="utf-8")
    (tmp_path / "c").mkdir()
    assert _exported_bytes(str(md2), str(tmp_path / "c")) != a


# ---------------------------------------------------------------------------
# 計畫 9.10 S2：CATALOG 新形態（架內多粗目）逐行字面 ── §3 S2 驗收
# ---------------------------------------------------------------------------


def _nav_fine(fid, *, title, phrasing_text, target_user=("property_manager", "prospect")):
    return FineItem(
        id=fid, coarse_id=fid.split("/")[1], title=title,
        phrasings=(Phrasing(text=phrasing_text, source="test:1", status="approved"),),
        content_units=(f"{title}的內容。",), content_sha256="0" * 64, sources=("kb:1",),
        reviewed_by="owner", reviewed_at="2026-09-21",
        see_also=(), policy="answerable", policy_ref=None,
        target_user=tuple(target_user), business_types=("system_provider",),
        categories=(), instance_applicability="general",
    )


def _single_slug_doc(*, coarse_id="A-account-registration", coarse_title="註冊帳號"):
    """計畫 §3 S2 逐字字面樣本：一架、一個帶 slug 粗目。"""
    coarse = CoarseItem(id=coarse_id, title=coarse_title, fines=(
        _nav_fine("jgb/A/email-register", title="怎麼用 Email 註冊", phrasing_text="怎麼開帳號"),
    ))
    return CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse,),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        scopes=(("A", "註冊、登入、找回帳號"),), shelf_titles=(("A", "帳號與身分"),),
    )


def test_catalog_single_slug_coarse_shelf_matches_literal_sample_and_mutation_reddens(tmp_path):
    """①單一帶 slug 粗目的架 fixture：逐行等於計畫 §3 S2 寫死的字面（架層兩行＋一行 `###`），不拋例外。

    ⚠️ mutation 檢查：`### ` 行任一欄位（粗目 id／標題）改動即紅——證明比對真的在看欄位，
    不是碰巧字串相符。
    """
    doc = _single_slug_doc()
    out = str(tmp_path / "CATALOG.md")
    payload = export_catalog(doc, out)
    expected = (
        "## A 帳號與身分 {#A}\n"
        "scope: 註冊、登入、找回帳號\n"
        "### A-account-registration 註冊帳號 {#A-account-registration}\n"
        "jgb/A/email-register｜怎麼用 Email 註冊｜target_user=property_manager,prospect｜怎麼開帳號\n"
    )
    assert payload == expected
    with open(out, "rb") as fh:
        assert fh.read().decode("utf-8") == expected

    # mutation：粗目 id 改了 ⇒ `### ` 那一行（含錨點）必須跟著變，輸出不再等於原字面
    mutated_id = export_catalog(
        _single_slug_doc(coarse_id="A-account-registration-x"), str(tmp_path / "m_id.md")
    )
    assert mutated_id != expected
    # mutation：粗目標題改了 ⇒ 同一行的標題欄位必須跟著變
    mutated_title = export_catalog(
        _single_slug_doc(coarse_title="改過的標題"), str(tmp_path / "m_title.md")
    )
    assert mutated_title != expected


def _multi_shelf_multi_coarse_doc():
    """兩架：架 A 兩個粗目（同架不插空行）、架 B 一個粗目；架與架之間一個空行。"""
    coarse_a1 = CoarseItem(id="A-account-registration", title="註冊帳號", fines=(
        _nav_fine("jgb/A/email-register", title="怎麼用 Email 註冊", phrasing_text="怎麼開帳號"),
    ))
    coarse_a2 = CoarseItem(id="A-login", title="登入", fines=(
        _nav_fine("jgb/A/password-reset", title="忘記密碼", phrasing_text="忘記密碼"),
    ))
    coarse_b1 = CoarseItem(id="B-team-invite", title="邀請團隊", fines=(
        _nav_fine("jgb/B/team-invite", title="怎麼邀請成員", phrasing_text="邀請同事"),
    ))
    return CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse_a1, coarse_a2, coarse_b1),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        scopes=(("A", "註冊、登入、找回帳號"), ("B", "團隊與成員")),
        shelf_titles=(("A", "帳號與身分"), ("B", "團隊、人員與大房東")),
    )


def test_catalog_multi_shelf_multi_coarse_blank_lines_match_byte_for_byte_and_mutation_reddens(tmp_path):
    """②多架多粗目 fixture：跨架空行逐位元符合（同架粗目間不插空行、架與架之間一個空行）。

    ⚠️ mutation 檢查：改動任一 `### ` 行的粗目 id 或標題即紅。
    """
    doc = _multi_shelf_multi_coarse_doc()
    payload = export_catalog(doc, str(tmp_path / "CATALOG.md"))
    expected = (
        "## A 帳號與身分 {#A}\n"
        "scope: 註冊、登入、找回帳號\n"
        "### A-account-registration 註冊帳號 {#A-account-registration}\n"
        "jgb/A/email-register｜怎麼用 Email 註冊｜target_user=property_manager,prospect｜怎麼開帳號\n"
        "### A-login 登入 {#A-login}\n"
        "jgb/A/password-reset｜忘記密碼｜target_user=property_manager,prospect｜忘記密碼\n"
        "\n"
        "## B 團隊、人員與大房東 {#B}\n"
        "scope: 團隊與成員\n"
        "### B-team-invite 邀請團隊 {#B-team-invite}\n"
        "jgb/B/team-invite｜怎麼邀請成員｜target_user=property_manager,prospect｜邀請同事\n"
    )
    assert payload == expected

    mutated = replace(doc, coarses=(
        CoarseItem(id="A-account-registration", title="改過的標題", fines=doc.coarses[0].fines),
        doc.coarses[1], doc.coarses[2],
    ))
    assert export_catalog(mutated, str(tmp_path / "m.md")) != expected


def test_catalog_export_raises_when_shelf_titles_missing_key(tmp_path):
    """`shelf_titles` 缺該架 ⇒ `export_catalog` 丟出點名架字母與粗目 id 的例外（負對照）。"""
    coarse = CoarseItem(id="C-missing", title="缺架標題的粗目", fines=(
        _nav_fine("jgb/C/x", title="X", phrasing_text="x"),
    ))
    doc = CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse,),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        scopes=(("C", "範圍"),), shelf_titles=(),  # ⚠️ 刻意缺 C
    )
    with pytest.raises(CanonFormatError, match="C.*shelf_titles|shelf_titles.*C"):
        export_catalog(doc, str(tmp_path / "CATALOG.md"))

    # 正對照：補上 shelf_titles 後不再 raise
    ok_doc = CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse,),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        scopes=(("C", "範圍"),), shelf_titles=(("C", "標題"),),
    )
    export_catalog(ok_doc, str(tmp_path / "ok.md"))


def test_catalog_export_raises_when_scopes_missing_key(tmp_path):
    """`scopes` 缺該架 ⇒ 同上，例外點名架字母與粗目 id（負對照）。"""
    coarse = CoarseItem(id="C-missing", title="缺 scope 的粗目", fines=(
        _nav_fine("jgb/C/x", title="X", phrasing_text="x"),
    ))
    doc = CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse,),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        scopes=(), shelf_titles=(("C", "標題"),),  # ⚠️ 刻意缺 C
    )
    with pytest.raises(CanonFormatError, match="C.*scopes|scopes.*C"):
        export_catalog(doc, str(tmp_path / "CATALOG.md"))


def test_export_catalog_rejects_bare_letter_coarse_id_regardless_of_scopes(tmp_path):
    """計畫 9.10 S5／DSP-070 item 3／7c：裸字母粗目（is_bare 分支已整條移除）在**目錄路徑**
    （`library=True`）一律 raise 並點名該粗目 id——⛔ 不因補齊 `scopes`／`shelf_titles` 就放行，
    也⛔ 不得靜默落進新形態分支（新形態分支會拿 `coarse.id[0]` 當架字母，裸字母恰好也能取到
    首字元，若不先擋會「看似正常」地輸出，掩蓋這其實是已停用的形態）。

    正對照：同一份 doc 只把粗目 id 換成合法的 `<架字母>-<slug>` 形態即可成功導出。
    mutation：拿掉 `_reject_bare_coarse_ids` 的呼叫，本測試前半段（`pytest.raises`）即紅。
    """
    coarse = CoarseItem(id="C", title="社區與物件", fines=(
        _nav_fine("jgb/C/x", title="X", phrasing_text="x"),
    ))
    kwargs = dict(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse,),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        shelf_titles=(("C", "社區與物件"),), scopes=(("C", "社區範圍"),),
    )
    with pytest.raises(CanonFormatError, match="裸字母"):
        export_catalog(CanonDoc(**kwargs), str(tmp_path / "CATALOG.md"))

    ok_coarse = CoarseItem(id="C-estate", title="社區與物件", fines=coarse.fines)
    ok_doc = replace(CanonDoc(**kwargs), coarses=(ok_coarse,))
    payload = export_catalog(ok_doc, str(tmp_path / "ok.md"))
    assert "### C-estate 社區與物件 {#C-estate}" in payload
    assert "scope: 社區範圍" in payload


def test_export_json_rejects_bare_letter_coarse_id_in_library_doc(tmp_path):
    """同上，`export_json` 這一側的防線（計畫 9.10 S5／DSP-070 item 7c）。

    ⚠️ ⛔ 只查目錄路徑（`library=True`）——單檔路徑的裸字母粗目是既有、未變的合法形態
    （見 `test_canon_parser_req.py` 的 SAMPLE），本檢查不得誤傷它，正對照見下一條測試。
    """
    coarse = CoarseItem(id="C", title="社區與物件", fines=(
        _nav_fine("jgb/C/x", title="X", phrasing_text="x"),
    ))
    doc = CanonDoc(
        audience="jgb", version="v1", reviewers=("owner",), language="zh-TW", budget_tokens=0,
        target_user=(), business_types=(), coarses=(coarse,),
        canon_sha256="a" * 64, phrasing_set_sha256="b" * 64, name="jgb", library=True,
        shelf_titles=(("C", "社區與物件"),), scopes=(("C", "社區範圍"),),
    )
    with pytest.raises(CanonFormatError, match="裸字母"):
        export_json(doc, str(tmp_path / "jgb.json"))


def test_export_json_does_not_reject_bare_letter_coarse_id_for_single_file_doc(tmp_path):
    """正對照：單檔路徑（`library=False`）的裸字母粗目 ⛔ 不受本片新檢查影響——
    `export_json` 對 SAMPLE（`## A 產品基本盤 {#A}`）仍成功，逐位元與既有行為相同。
    """
    doc = parse_canon(_write_sample(tmp_path))
    out = str(tmp_path / "out.json")
    assert export_json(doc, out) == doc.canon_sha256


def _write_sample(tmp_path) -> str:
    p = tmp_path / "single_file_sample.md"
    p.write_text(SAMPLE, encoding="utf-8")
    return str(p)
