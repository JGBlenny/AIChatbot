"""integration：`OutlineAssembler`（spec knowledge-outline-and-intent-architecture 3.2）。

真測試庫。灌三列（形狀沿用 3.1）：
- 已審列（`outline_approved_by='reviewed:test'`）——⚠️ **3.2 起它不該再出現在售前大綱裡**：
  大綱來源改成 git 正本，DB 售前池是正本的衍生物。
- 未標記一般列——同上，形狀對照組。
- `系統脈絡` 列（`vendor_ids=[OWN_VENDOR_ID]`）——只給 `build_toc`（pm／tenant 現役）用；
  vendor 相符時應出現，vendor 不符時不應出現（**這道 vendor 過濾 ⛔ 不得拿掉**）。

## 突變控制（Plan §4.8）
`test_prospect_outline_is_assembled_from_canon` 走**版控正本目錄**（不設 `AGENT_CANON_DIR`）：
`rag-orchestrator/canon/prospect.md` 改一位元而未重導出 `.json` ⇒ `load_canon_or_die` raise
⇒ 這條測試變紅。⛔ 這不是「測試很脆弱」，這正是啟動契約要的：正本被動過就不准起來。

⚠️ 竄改情境一律用 `tmp_path` 複本＋`AGENT_CANON_DIR`（只在 `DB_ENV=test` 生效），
⛔ 本檔不寫入 `rag-orchestrator/canon/`。

無法連 DB → skip（非 fail）；連到非測試庫 → 大聲失敗（⛔ 不得寫入非測試資料）。
用完在 finally 依 id 區間刪除，且開跑前先驗該區間為空（⛔ 不覆蓋既有資料）。
"""
import os
import re
import shutil
from pathlib import Path

import psycopg2
import pytest

from services.agent.canon.canon_assembler import (
    CANON_DIR_ENV, DB_ENV_KEY, TOC_SECTION_ID, CanonLoadError, load_canon_or_die,
    reset_canon_registry, resolve_canon_dir,
)
from services.agent.canon.canon_parser import export_json, parse_canon
from services.agent.outline import build_prospect_outline, build_toc

pytestmark = pytest.mark.integration

_SPEC = "knowledge-outline-and-intent-architecture:3.2"

CANON_DIR = Path(__file__).resolve().parents[3] / "canon"
#: 版控正本現況細目數（Plan §4.8 釘死；正本增刪細目時**要一起改這個數字**，
#: ⛔ 不改成 `len(fines)` 自證——那會讓「正本被砍到只剩 1 個細目」也綠。
CANON_FINE_COUNT = 38

#: 明示 id 起點，⛔ 不靠 serial 預設值（與 test_kb_tools_req.py／
#: test_outline_approval_columns_req.py 同理由）。
BASE_ID = 9_300_000
APPROVED_ID = BASE_ID + 1
UNAPPROVED_ID = BASE_ID + 2
SYSTEM_CONTEXT_ID = BASE_ID + 3
_ALL_IDS = [APPROVED_ID, UNAPPROVED_ID, SYSTEM_CONTEXT_ID]

OWN_VENDOR_ID = 4242
OTHER_VENDOR_ID = 4243


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _connect():
    """連測試庫；不可達 ⇒ skip（⛔ 不是 fail），連到非測試庫 ⇒ 大聲失敗。"""
    db = _conn_kwargs()["database"]
    if db not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(f"[env] 解析到的資料庫 {db!r} 不是測試庫——本測試會寫入列，⛔ 拒絕執行")
    try:
        return psycopg2.connect(**_conn_kwargs())
    except psycopg2.Error as e:
        pytest.skip(f"測試 DB 不可達（{e.__class__.__name__}）→ OutlineAssembler 整合測試未驗")


class _SingleConnPool:
    """psycopg2 pool 介面的最小替身，包一條真連線給 `outline.py` 的取列函式用。"""

    def __init__(self, conn):
        self._conn = conn

    def getconn(self):
        return self._conn

    def putconn(self, conn):
        assert conn is self._conn


@pytest.fixture
def db_pool():
    conn = _connect()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT count(*) FROM knowledge_base WHERE id BETWEEN %s AND %s",
            (BASE_ID, BASE_ID + 100),
        )
        stale = cur.fetchone()[0]
        assert stale == 0, (
            f"id 區間 {BASE_ID}–{BASE_ID + 100} 已有 {stale} 列非本測試的資料——"
            "⛔ 拒絕覆蓋，請先確認來源"
        )

        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, categories, vendor_ids, business_types,
                 target_user, is_active, category, outline_approved_by, outline_approved_at)
            VALUES (%s, %s, %s, %s::text[], NULL, ARRAY['system_provider']::text[], NULL, TRUE, NULL, %s, now())  -- 售前池是 b2b 池（business_types && ['system_provider']）
            """,
            (
                APPROVED_ID, "修繕系統 線上報修", "可線上報修並追蹤進度。",
                # ⚠️ 2026-09-07 起「已審」＝ `reviewed:<who>`（值域見
                # services/agent/canon/review_state.py）；⛔ 不能再用
                # `owner-20260905`——那是值域外的舊標記，新謂詞視為未審。
                ["售前模組"], "reviewed:test",
            ),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, categories, vendor_ids, business_types,
                 target_user, is_active, category, outline_approved_by, outline_approved_at)
            VALUES (%s, %s, %s, %s::text[], NULL, ARRAY['system_provider']::text[], NULL, TRUE, NULL, NULL, NULL)
            """,
            (
                UNAPPROVED_ID, "未審核的售前知識", "這句不該進大綱。",
                ["售前模組"],
            ),
        )
        cur.execute(
            """
            INSERT INTO knowledge_base
                (id, question_summary, answer, vendor_ids, business_types, target_user,
                 is_active, category)
            VALUES (%s, %s, %s, %s::int[], NULL, NULL, TRUE, %s)
            """,
            (
                SYSTEM_CONTEXT_ID, "系統整體介紹（測試用）", "這是系統脈絡測試內容。",
                [OWN_VENDOR_ID], "系統脈絡",
            ),
        )
        cur.close()
        yield _SingleConnPool(conn)
    finally:
        cleanup_cur = conn.cursor()
        cleanup_cur.execute(
            "DELETE FROM knowledge_base WHERE id BETWEEN %s AND %s",
            (BASE_ID, BASE_ID + 100),
        )
        cleanup_cur.close()
        conn.close()


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_canon_registry()
    yield
    reset_canon_registry()


@pytest.fixture
def tmp_canon(tmp_path, monkeypatch):
    """版控正本的 tmp 複本，並把 `AGENT_CANON_DIR` 指過去（⛔ 不動版控檔）。"""
    assert os.environ.get(DB_ENV_KEY, "").strip() == "test", (
        "AGENT_CANON_DIR 覆寫只在 DB_ENV=test 生效——測試容器沒設 DB_ENV=test，"
        "這條測試會靜默量到版控正本"
    )
    dst = tmp_path / "canon"
    dst.mkdir()
    shutil.copy2(CANON_DIR / "prospect.md", dst / "prospect.md")
    shutil.copy2(CANON_DIR / "prospect.json", dst / "prospect.json")
    monkeypatch.setenv(CANON_DIR_ENV, str(dst))
    assert resolve_canon_dir() == dst.resolve(), "覆寫沒生效——下面的竄改會打到版控正本"
    return dst


def _reexport(canon_dir: Path) -> None:
    export_json(parse_canon(str(canon_dir / "prospect.md")), str(canon_dir / "prospect.json"))


@pytest.mark.req(_SPEC)
async def test_prospect_outline_is_assembled_from_canon(db_pool):
    """大綱＝正本逐細目＋`outline:toc`，**與 DB 售前池列無關**。

    ⚠️ 本條走版控正本目錄（不設 `AGENT_CANON_DIR`）——正本 `.md` 改一位元而未
    重導出 `.json` 時它會紅（Plan §4.8 突變控制）。
    """
    canon = load_canon_or_die(CANON_DIR, "prospect")          # 正對照：正本本身載得起來
    assert len(canon.fines()) == CANON_FINE_COUNT, [f.id for f in canon.fines()]

    doc = await build_prospect_outline(db_pool)
    assert len(doc.sections) == CANON_FINE_COUNT + 1, [s.id for s in doc.sections]

    by_id = {s.id: s for s in doc.sections}
    assert TOC_SECTION_ID in by_id
    assert by_id[TOC_SECTION_ID].citable is False
    fine_ids = [f.id for f in canon.fines()]
    assert [s.id for s in doc.sections[:-1]] == fine_ids
    assert all(s.citable for s in doc.sections[:-1]), "版控正本 38 細目全已審 ⇒ 全可引用"

    # DB 列（不論審核與否）⛔ 不得進大綱：source_ids 全空、內容不含 DB 列的答案
    assert all(not s.source_ids for s in doc.sections)
    assert "可線上報修並追蹤進度" not in doc.text
    assert "這句不該進大綱" not in doc.text


@pytest.mark.req(_SPEC)
async def test_prospect_outline_sha_follows_canon_bytes_not_db_rows(db_pool, tmp_canon):
    """sha 隨正本 `.md` 位元組變、**不隨 DB 列變**（快取失效判準搬家了）。"""
    before = await build_prospect_outline(db_pool)

    # ① UPDATE 售前池列 ⇒ sha 不變（正對照：確認 UPDATE 真的改到 1 列）
    conn = db_pool.getconn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE knowledge_base SET answer = %s, updated_at = now() WHERE id = %s",
        ("可線上報修並追蹤進度（已更新）。", APPROVED_ID),
    )
    assert cur.rowcount == 1, "前置條件沒達成：UPDATE 沒改到那一列，下面的「sha 不變」不可信"
    cur.close()
    db_pool.putconn(conn)

    after_db = await build_prospect_outline(db_pool)
    assert after_db.sha256 == before.sha256, "大綱 sha 竟隨 DB 列改變——它應該只看正本"

    # ② 正本 `.md` 改一位元（version 尾碼）、**沒有**重導出 `.json` ⇒ 不同源 ⇒ 啟動紅
    md = tmp_canon / "prospect.md"
    raw = md.read_bytes()
    # ⛔ 不寫死版本字串——正本每改一版就誤紅；從檔案抓 `version:` 行，把最後一個字元換掉（等長）
    m = re.search(rb"^version: [^\n]+$", raw, re.M)
    assert m, "正對照失敗：正本 front matter 沒有 version 行"
    needle = m.group(0)
    mutated = needle[:-1] + (b"0" if needle[-1:] != b"0" else b"1")
    assert needle in raw and mutated != needle, "正對照失敗：找不到要改的位元組"
    md.write_bytes(raw.replace(needle, mutated, 1))
    assert len(md.read_bytes()) == len(raw), "這不是一位元改動"
    with pytest.raises(CanonLoadError):
        await build_prospect_outline(db_pool)

    # ③ 同一個改動**有**重導出 ⇒ 載得起來、sha 變、節數不變
    _reexport(tmp_canon)
    after_md = await build_prospect_outline(db_pool)
    assert after_md.sha256 != before.sha256
    assert len(after_md.sections) == len(before.sections)

    # ④ 內容句改動同樣進 sha（sha 涵蓋 version＋text，⛔ 不是只看 version）
    md.write_text(md.read_text(encoding="utf-8") + "這是一句只在測試複本裡的內容。\n",
                  encoding="utf-8")
    _reexport(tmp_canon)
    after_content = await build_prospect_outline(db_pool)
    assert after_content.version == after_md.version
    assert after_content.sha256 != after_md.sha256
    assert len(after_content.sections) == len(before.sections)


@pytest.mark.req(_SPEC)
async def test_prospect_outline_dies_when_canon_markdown_missing(db_pool, tmp_canon):
    """正本缺檔 ⇒ raise（`app.py` 在 agent 開關為真時把它升成啟動紅）。"""
    (tmp_canon / "prospect.md").unlink()
    with pytest.raises(CanonLoadError):
        await build_prospect_outline(db_pool)


@pytest.mark.req(_SPEC)
async def test_toc_includes_system_context_row_for_matching_vendor(db_pool):
    doc = await build_toc(db_pool, "property_manager", vendor_id=OWN_VENDOR_ID)
    ids = {sid for section in doc.sections for sid in section.source_ids}
    assert SYSTEM_CONTEXT_ID in ids
    matched = next(s for s in doc.sections if SYSTEM_CONTEXT_ID in s.source_ids)
    assert matched.citable is False


@pytest.mark.req(_SPEC)
async def test_toc_excludes_system_context_row_for_other_vendor(db_pool):
    doc = await build_toc(db_pool, "property_manager", vendor_id=OTHER_VENDOR_ID)
    ids = {sid for section in doc.sections for sid in section.source_ids}
    assert SYSTEM_CONTEXT_ID not in ids, (
        "vendor_ids=[OWN_VENDOR_ID] 的系統脈絡列被非該業者的 vendor_id 看到——"
        "build_toc 的 vendor 過濾沒生效"
    )
