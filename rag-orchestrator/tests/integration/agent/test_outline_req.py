"""integration：`OutlineAssembler`（spec knowledge-outline-and-intent-architecture 3.2）。

真測試庫。灌三列（形狀沿用 3.1）：
- 已審列（`outline_approved_by='reviewed:test'`）——⚠️ **3.2 起它不該再出現在售前大綱裡**：
  大綱來源改成 git 正本，DB 售前池是正本的衍生物。
- 未標記一般列——同上，形狀對照組。
- `系統脈絡` 列（`vendor_ids=[OWN_VENDOR_ID]`）——只給 `build_toc`（pm／tenant 現役）用；
  vendor 相符時應出現，vendor 不符時不應出現（**這道 vendor 過濾 ⛔ 不得拿掉**）。

## 突變控制（Plan §4.8）
`test_prospect_outline_is_assembled_from_canon` 走**版控正本目錄**（不設 `AGENT_CANON_DIR`）：
`rag-orchestrator/canon/jgb/` 任一架改一位元而未重導出 `jgb.json`／`CATALOG.md`
⇒ `load_canon_or_die` raise ⇒ 這條測試變紅。⛔ 這不是「測試很脆弱」，這正是啟動契約要的：
正本被動過就不准起來。

## DSP-058／9.6 S3
正本只有一份（`canon/jgb/`），`build_prospect_outline` 回的是 **prospect 視圖**
（38 細目＋toc，⛔ 不是整份 53 條正本）；未審細目只出標題（`text=""`、`citable=False`）。

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
from services.agent.canon.canon_parser import (
    CANON_NAME, export_catalog, export_json, parse_canon_dir,
)
from services.agent.outline import build_prospect_outline, build_toc

pytestmark = pytest.mark.integration

_SPEC = "knowledge-outline-and-intent-architecture:3.2"

CANON_DIR = Path(__file__).resolve().parents[3] / "canon"
#: 版控正本現況細目數（Plan §4.8 釘死；正本增刪細目時**要一起改這個數字**，
#: ⛔ 不改成 `len(fines)` 自證——那會讓「正本被砍到只剩 1 個細目」也綠。
#: 2026-09-16 9.7 七架連跑後：210（程式 `canon.fines()` 計數與逐架 `.md` `### ` 節標題
#: 總數交叉核一致，見 plan-9.8-turn-budget-dprime S1 完成報告）。
CANON_FINE_COUNT = 210
#: 其中屬於 **prospect 視圖**的（DSP-058：受眾＝視圖，⛔ 不是整份正本）。
#: 交叉核：程式 `build_outline` 節數與 `CATALOG.md` `target_user=` 含 `prospect` 列數一致＝59。
PROSPECT_VIEW_FINE_COUNT = 59
#: prospect 視圖裡**未審**的條數（只出標題、⛔ 不可引用；canon/README R2.9）——交叉核一致＝46。
PROSPECT_VIEW_UNREVIEWED = 46

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
    shutil.copytree(CANON_DIR / CANON_NAME, dst / CANON_NAME)   # 九架＋CATALOG.md
    shutil.copy2(CANON_DIR / f"{CANON_NAME}.json", dst / f"{CANON_NAME}.json")
    monkeypatch.setenv(CANON_DIR_ENV, str(dst))
    assert resolve_canon_dir() == dst.resolve(), "覆寫沒生效——下面的竄改會打到版控正本"
    return dst


def _reexport(canon_dir: Path) -> None:
    doc = parse_canon_dir(str(canon_dir / CANON_NAME))
    export_json(doc, str(canon_dir / f"{CANON_NAME}.json"))
    export_catalog(doc, str(canon_dir / CANON_NAME / "CATALOG.md"))


def _append_to_fine_content(shelf_md: Path, fine_id: str, extra_line: str) -> None:
    """在**這個細目自己的內容區塊**尾端插一行（下一個 `### ` 節標題或檔尾之前）。

    ⚠️ 9.7 七架連跑後，任何架的**檔案最後一個細目**都不保證是「已審且 prospect 可見」
    （逐架連跑順序與內容審核狀態無關）——舊寫法「直接 append 到檔尾」隱含假設
    「目標細目剛好是檔案最後一筆」，這個假設在 210 條正本下不再成立。改成明確定位
    該細目的標題行，插在**它自己**的內容區塊結尾，⛔ 不管它在檔案裡是不是最後一筆。
    """
    lines = shelf_md.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if f"{{#{fine_id}}}" in line)
    end = len(lines)   # 預設：沒有下一個節標題 ⇒ 插在檔尾
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("### ") or lines[i].startswith("## "):
            end = i
            break
    lines[end:end] = [extra_line]
    shelf_md.write_text("\n".join(lines), encoding="utf-8")


@pytest.mark.req(_SPEC)
async def test_prospect_outline_is_assembled_from_canon(db_pool):
    """大綱＝正本逐細目＋`outline:toc`，**與 DB 售前池列無關**。

    ⚠️ 本條走版控正本目錄（不設 `AGENT_CANON_DIR`）——正本 `.md` 改一位元而未
    重導出 `.json` 時它會紅（Plan §4.8 突變控制）。
    """
    canon = load_canon_or_die(CANON_DIR)                      # 正對照：正本本身載得起來
    assert len(canon.fines()) == CANON_FINE_COUNT, [f.id for f in canon.fines()]

    doc = await build_prospect_outline(db_pool)
    assert len(doc.sections) == PROSPECT_VIEW_FINE_COUNT + 1, [s.id for s in doc.sections]

    by_id = {s.id: s for s in doc.sections}
    assert TOC_SECTION_ID in by_id
    assert by_id[TOC_SECTION_ID].citable is False
    # 視圖＝正本序中 `target_user` 含 prospect 的那些（⛔ 不是整份正本）
    view_fines = [f for f in canon.fines() if "prospect" in f.target_user]
    assert [s.id for s in doc.sections[:-1]] == [f.id for f in view_fines]
    assert len(view_fines) == PROSPECT_VIEW_FINE_COUNT
    # 另一受眾的細目連標題都不在（DSP-058 的受眾隔離）
    pm_only = [f.id for f in canon.fines() if "prospect" not in f.target_user]
    assert pm_only and not ({f for f in pm_only} & set(by_id))
    assert all(fid not in doc.text for fid in pm_only)
    # 未審細目：只出標題、⛔ 不可引用（正對照：已審的有內容且可引用）
    unreviewed = [f for f in view_fines if f.reviewed_by is None]
    assert len(unreviewed) == PROSPECT_VIEW_UNREVIEWED, [f.id for f in unreviewed]
    for fine in unreviewed:
        assert by_id[fine.id].citable is False and by_id[fine.id].text == ""
    reviewed = [f for f in view_fines if f.reviewed_by is not None]
    assert reviewed and all(by_id[f.id].citable and by_id[f.id].text for f in reviewed)

    # DB 列（不論審核與否）⛔ 不得進大綱：source_ids 全空、內容不含 DB 列的答案
    assert all(not s.source_ids for s in doc.sections)
    assert "可線上報修並追蹤進度" not in doc.text
    assert "這句不該進大綱" not in doc.text


@pytest.mark.req(_SPEC)
async def test_prospect_outline_sha_follows_canon_bytes_not_db_rows(db_pool, tmp_canon):
    """sha 隨正本 `.md` 位元組變、**不隨 DB 列變**（快取失效判準搬家了）。

    ⚠️ DSP-058：正本**每個行程只載入一次**（`get_canon()` 有值就沿用，第二個受眾不重讀檔）
    ⇒ 本測試每次要重新讀檔前都得先 `reset_canon_registry()`，否則量到的是上一次註冊的那份、
    對檔案的竄改會「看起來沒發生」。
    """
    before = await build_prospect_outline(db_pool)
    before_canon_sha = load_canon_or_die(resolve_canon_dir()).canon_sha256   # ③ 的對照基準

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

    reset_canon_registry()
    after_db = await build_prospect_outline(db_pool)
    assert after_db.sha256 == before.sha256, "大綱 sha 竟隨 DB 列改變——它應該只看正本"

    # ② 正本 `.md` 改一位元（`scope:` 尾碼）、**沒有**重導出 `.json` ⇒ 不同源 ⇒ 啟動紅
    md = tmp_canon / CANON_NAME / "A.md"
    raw = md.read_bytes()
    # ⛔ 不動 `version:`——DSP-058 起九架的 `version`／`reviewers`／`language` 必須一致，
    # 只改一架的 version 會先被 parser 的跨架一致性擋下（那是另一條規則，不是同源比對）。
    # 改 `scope:`（逐架獨立）的最後一個字元，等長 ⇒ 只動一位元。
    m = re.search(rb"^scope: [^\n]+$", raw, re.M)
    assert m, "正對照失敗：架 front matter 沒有 scope 行"
    needle = m.group(0)
    mutated = needle[:-1] + (b"0" if needle[-1:] != b"0" else b"1")
    assert needle in raw and mutated != needle, "正對照失敗：找不到要改的位元組"
    md.write_bytes(raw.replace(needle, mutated, 1))
    assert len(md.read_bytes()) == len(raw), "這不是一位元改動"
    reset_canon_registry()
    with pytest.raises(CanonLoadError):
        await build_prospect_outline(db_pool)

    # ③ 同一個改動**有**重導出 ⇒ 載得起來、節數不變；`canon_sha256` 變、大綱 sha **不變**
    #    （`scope` 只進 `canon_sha256`／`CATALOG.md`，⛔ 不進大綱文字——④ 是它的正對照：
    #     改內容句大綱 sha 就會變）
    _reexport(tmp_canon)
    reset_canon_registry()
    after_md = await build_prospect_outline(db_pool)
    assert len(after_md.sections) == len(before.sections)
    assert after_md.sha256 == before.sha256
    assert load_canon_or_die(resolve_canon_dir()).canon_sha256 != before_canon_sha

    # ④ 內容句改動同樣進 sha（sha 涵蓋 version＋text，⛔ 不是只看 version）
    #    ⚠️ 要挑**已審且在 prospect 視圖內**的細目：未審細目在視圖裡只出標題（`text=""`），
    #    往它後面加內容句大綱文字不會變，那樣這一條會量不到東西。
    #    ⚠️ 9.7 七架連跑後不能再假設「某架檔案裡最後一個細目」剛好是已審的
    #    prospect 細目（逐架連跑順序與審核狀態無關）——改為明確指名一個現在真的
    #    符合條件的細目 id（2026-09-16 用腳本對 210 條正本逐條篩出，見完成報告：
    #    `jgb/B/team-management-overview` 是 B 架**唯一**已審且 prospect 可見的細目），
    #    用 `_append_to_fine_content` 精準插進它自己的內容區塊，⛔ 不管它在檔案裡的
    #    實際位置。
    content_fine_id = "jgb/B/team-management-overview"
    content_shelf = tmp_canon / CANON_NAME / "B.md"
    content_fine = next(
        f for f in load_canon_or_die(resolve_canon_dir()).fines() if f.id == content_fine_id
    )
    assert content_fine.reviewed_by is not None and "prospect" in content_fine.target_user, (
        f"正對照失敗：{content_fine_id} 不是已審的 prospect 細目 ⇒ 這一條量不到內容句改動"
    )
    _append_to_fine_content(content_shelf, content_fine_id, "這是一句只在測試複本裡的內容。")
    _reexport(tmp_canon)
    reset_canon_registry()
    after_content = await build_prospect_outline(db_pool)
    assert after_content.version == after_md.version
    assert after_content.sha256 != after_md.sha256
    assert len(after_content.sections) == len(before.sections)


@pytest.mark.req(_SPEC)
async def test_prospect_outline_dies_when_canon_markdown_missing(db_pool, tmp_canon):
    """缺架 ⇒ raise（`app.py` 在 agent 開關為真時把它升成啟動紅）。"""
    reset_canon_registry()
    (tmp_canon / CANON_NAME / "A.md").unlink()
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
