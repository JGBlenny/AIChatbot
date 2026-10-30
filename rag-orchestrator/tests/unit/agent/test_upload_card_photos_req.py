"""unit：UD-3 照片隨卡、暫存回收、S11 重新編碼、S5／A13 兌現比對、multipart 交 jgb2、張數 5→10。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-upload-documind-20261028.md` §4 UD-3、§4.1 S5／S11；
凍結清單同目錄 `acceptance-upload-documind-20261028.md` A5、A8、A13 與「業主核可的縮減」①。
UD-0 改前錯筆卡（`~/jgb-archive/upload-direct-20261028/ud0/convs/` R2-0、R2-5、R5-4）：
  - R2-0：改物件後重出的卡沒有「附照片」、寫入 0 張；
  - R2-5：改物件後分類退回「其他（未指定，歸其他）」、照片也掉；
  - R5-4：改描述後照片掉。

載具：真 `AgentRuntime`＋真 `mcp_facade.build_registry`＋真 `JGBSystemAPI`／`JGBMockTransport`
（`assistant_demo_vendor4.json`）＋有狀態的 token 表替身（`test_step3_write_lifecycle_req._World`）；
照片放進真 `upload_store.STORE`（同 UD-1 的發票→上傳→引用→回合結束流程，綁定＝本回合身分）。
全部離線。每個「擋下／沒送／沒刪」的斷言旁有正對照。
"""
from __future__ import annotations

import hashlib
import io
import json

import pytest
from PIL import Image

from services.agent import mcp_facade as F
from services.agent import upload_store as U
from services.agent.agent_session import PENDING_CONFIRM_KEY
from services.agent.confirm_card import (
    CANCELLED_TEXT,
    CONFIRMATION_REQUIRED_TEXT,
    PHOTO_REUPLOAD_TEXT,
    REPAIR_PHOTOS_MAX,
    ConfirmCardError,
    render,
)
from services.agent.runtime import (
    IMAGE_SUGGESTION_KEY,
    PENDING_PHOTO_SUGGESTION_KEY,
    PENDING_PHOTOS_RELEASED_KEY,
    V_PHOTOS_CARRIED,
    _encode_card_photos,
)
from services.jgb.transport import MOCK_WRITE_LOG_ENV, JGBMockTransport

from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — fixtures
    _env, _fill_data_text_off, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import KEELUNG_ESTATE, STUDENT_ESTATE, _intent

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-upload-documind-20261028-UD-3")]

REPAIR_POST = ("POST", "/api/external/v1/repairs")


@pytest.fixture(autouse=True)
def _clean_store():
    U.STORE.reset()
    yield
    U.STORE.reset()


# ---------------------------------------------------------------------------
# 照片與暫存
# ---------------------------------------------------------------------------
def _jpeg(color=(120, 140, 160), size=(64, 32), *, exif=False, trailer=b"") -> bytes:
    """合成 JPEG；`exif=True` ⇒ 帶相機型號、GPS、方向＝6（需順時針轉 90°）。"""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "SynthCam"
        ex[0x0112] = 6
        gps = ex.get_ifd(0x8825)
        gps[1] = "N"
        gps[2] = (25.0, 2.0, 0.0)
        img.save(buf, format="JPEG", exif=ex.tobytes())
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue() + trailer


def _png(color=(10, 200, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buf, format="PNG")
    return buf.getvalue()


def _upload(ident, blobs) -> list:
    """照 UD-1 流程把照片放進暫存（發票→上傳→`claim`→`end_turn` ⇒ retained），回原檔中繼資料
    （＝`mcp_facade._photo_meta`，照片建議裡的那一份）。"""
    binding = U.binding_from_identity(ident, "repair")
    handle = U.STORE.verify_ticket(U.STORE.issue_ticket(binding).upload_token)
    ids, metas = [], []
    for i, blob in enumerate(blobs, start=1):
        ctype = U.sniff_content_type(blob)
        ids.append(U.STORE.add_upload(handle, content_type=ctype, data=blob).upload_id)
        metas.append(F._photo_meta(blob, ctype.split("/")[1], i))
    taken = U.STORE.claim(ids, binding)
    U.STORE.end_turn([c.ref for c in taken])
    return metas


def _seed_photos(w, blobs, *, category="水龍頭", parent="水路衛浴") -> list:
    metas = _upload(w.ident, blobs)
    w.state.setdefault("agent", {})[IMAGE_SUGGESTION_KEY] = {
        "category_name": category, "parent_category_name": parent, "item": None, "reason": None,
        "description": None, "photos": metas}
    return metas


def _card_photos(w, pid) -> list:
    return w.pending()[pid]["payload"].get("broken_photos") or []


def _repair_posts(api) -> list:
    rec = api._mock_transport
    return [i for i, c in enumerate(rec.calls) if c[:2] == REPAIR_POST]


def _retained() -> int:
    return U.STORE.counts()[U.STATE_RETAINED]


# ════════════════════════════════════════════════════════════════════
# 1. 照片隨卡（R2-0／R2-5／R5-4）
# ════════════════════════════════════════════════════════════════════
async def test_estate_change_keeps_two_photos_with_the_same_sha(api):
    """R2-0：改物件後重出的卡仍「附照片：2 張」、sha256 與舊卡逐張相同；送出後 jgb2 收到 2 個檔。"""
    w = _World()
    originals = _seed_photos(w, [_jpeg((200, 0, 0)), _png()])
    r1, pid1 = await w.repair_card()
    assert "・附照片：2 張" in r1.answer
    old = _card_photos(w, pid1)
    # S11：卡上綁的是**重新編碼後**的 JPEG（⛔ 原檔 sha）
    assert [p["content_type"] for p in old] == ["image/jpeg", "image/jpeg"]
    assert [p["filename"] for p in old] == ["photo-1.jpg", "photo-2.jpg"]
    assert {p["sha256"] for p in old}.isdisjoint({p["sha256"] for p in originals})

    r2 = await w.turn(f"物件改成{KEELUNG_ESTATE}",
                      intents=[_intent("repair_create", estate_name=KEELUNG_ESTATE)])
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    pid2 = r2.trace.pending_id
    assert pid2 != pid1 and f"・物件：{KEELUNG_ESTATE}" in r2.answer
    assert "・附照片：2 張" in r2.answer
    assert _card_photos(w, pid2) == old                      # 同一份中繼資料、同 sha
    assert V_PHOTOS_CARRIED in r2.trace.violations
    # 正對照：carry 的來源確實是舊卡（已被 A2 燒掉作廢）
    assert w.pending()[pid1].get("invalidated") is True

    done = await w.turn(f"confirm_submit:{pid2}")
    assert done.outcome["state"] == "confirmed", done.answer
    i = _repair_posts(api)[-1]
    files = api._mock_transport.files[i]
    assert [f[0] for f in files] == ["broken_photos[]"] * 2
    assert [hashlib.sha256(f[3]).hexdigest() for f in files] == [p["sha256"] for p in old]


async def test_description_change_keeps_photos(api):
    """R5-4：改描述後照片仍在（同 sha），卡上描述換成新的。"""
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid1 = await w.repair_card()
    old = _card_photos(w, pid1)
    assert len(old) == 1
    r2 = await w.turn("描述不對，是熱水器壞了", intents=[_intent("repair_create", description="熱水器壞了")])
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    pid2 = r2.trace.pending_id
    assert "・問題描述：熱水器壞了" in r2.answer and "・附照片：1 張" in r2.answer
    assert _card_photos(w, pid2) == old


async def test_r2_5_category_from_photo_survives_estate_change(api):
    """R2-5：照片判出的分類（水龍頭）在改物件後 ⛔ 退回「其他（未指定，歸其他）」。"""
    w = _World()
    _seed_photos(w, [_jpeg(), _jpeg((0, 0, 255))])
    r1, pid1 = await w.repair_card()
    assert "・修繕分類：水龍頭" in r1.answer
    assert w.pending()[pid1][PENDING_PHOTO_SUGGESTION_KEY]["category_name"] == "水龍頭"
    assert "photos" not in w.pending()[pid1][PENDING_PHOTO_SUGGESTION_KEY]   # ⛔ 中繼資料第二份
    r2 = await w.turn(f"物件改成{KEELUNG_ESTATE}",
                      intents=[_intent("repair_create", estate_name=KEELUNG_ESTATE)])
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    assert "・修繕分類：水龍頭" in r2.answer and "其他" not in r2.answer
    assert "・附照片：2 張" in r2.answer


async def test_customer_explicit_category_change_wins(api):
    """客人明講換分類 ⇒ 以客人的話為準（照片仍附）；連「父分類」也 ⛔ 被換回照片的葉節點。"""
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, _pid1 = await w.repair_card()
    r2 = await w.turn("分類改成馬桶", intents=[_intent("repair_create", category_name="馬桶")])
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    assert "・修繕分類：馬桶" in r2.answer and "水龍頭" not in r2.answer
    assert "・附照片：1 張" in r2.answer
    # 客人講的是照片葉節點的父分類 ⇒ 仍以客人為準（新照片回合才會換葉節點，卡後更正 ⛔）
    r3 = await w.turn("分類改成水路衛浴", intents=[_intent("repair_create", category_name="水路衛浴")])
    assert r3.outcome["state"] == "confirm_pending", r3.answer
    assert "・修繕分類：水路衛浴" in r3.answer


async def test_new_draft_never_inherits_photos_of_an_earlier_card(api):
    """⛔ 照片補到無關的單：舊卡已送出（草稿清掉）⇒ 下一張新修繕卡沒有照片、也沒有照片分類。"""
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid1 = await w.repair_card()
    assert (await w.turn(f"confirm_submit:{pid1}")).outcome["state"] == "confirmed"
    r2, _pid2 = await w.repair_card(f"{STUDENT_ESTATE} 燈不亮", description="燈不亮")
    assert "附照片" not in r2.answer and "水龍頭" not in r2.answer
    assert V_PHOTOS_CARRIED not in r2.trace.violations


async def test_model_photo_keys_are_still_dropped_on_a_carried_card(api):
    """照片中繼資料只由程式寫：carry 路徑的程式呼叫照樣無條件刪模型照片鍵（新卡＝舊卡那一份）。"""
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid1 = await w.repair_card()
    old = _card_photos(w, pid1)
    r2 = await w.turn("描述改成門鎖壞了", intents=[_intent("repair_create", description="門鎖壞了")])
    pid2 = r2.trace.pending_id
    payload = w.pending()[pid2]["payload"]
    assert payload["broken_photos"] == old
    assert not [k for k in payload if ("photo" in k.lower() or "image" in k.lower())
                and k != "broken_photos"]


# ════════════════════════════════════════════════════════════════════
# 2. 暫存回收（縮減 ①）
# ════════════════════════════════════════════════════════════════════
async def test_redeem_success_releases_photos(api):
    w = _World()
    _seed_photos(w, [_jpeg(), _jpeg((1, 2, 3))])
    _r1, pid = await w.repair_card()
    assert _retained() == 2                                   # 正對照：出卡後照片還在
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.outcome["state"] == "confirmed", res.answer
    assert U.STORE.counts()["uploads"] == 0
    assert w.pending()[pid][PENDING_PHOTOS_RELEASED_KEY] is True


async def test_redeem_write_failure_also_releases_photos(api, monkeypatch):
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid = await w.repair_card()
    assert _retained() == 1
    monkeypatch.setenv("MOCK_FAIL_NEXT_WRITE", "1")
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.outcome["state"] == "failed", res.answer
    assert U.STORE.counts()["uploads"] == 0


async def test_cancel_releases_photos(api):
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid = await w.repair_card()
    assert _retained() == 1
    res = await w.turn(f"confirm_cancel:{pid}")
    assert res.answer == CANCELLED_TEXT
    assert U.STORE.counts()["uploads"] == 0


async def test_select_void_releases_photos(api):
    """清單點選另一筆 ⇒ 待確認卡作廢 ⇒ 照片釋放。"""
    from services.agent.budget import Budget
    from services.agent.runtime import AgentRuntime
    from tests.unit.agent.test_runtime_req import FakeAssembler, FakeClock, VerifierVerdict
    from tests.unit.agent.test_step3_write_lifecycle_req import _RouteVerifier
    from tests.unit.agent.test_write_draft_flow_req import _Provider

    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid = await w.repair_card()
    assert _retained() == 1
    rt = AgentRuntime(_Provider([], None), w.reg, _RouteVerifier([VerifierVerdict(ok=True)] * 6),
                      FakeAssembler(), Budget(), stage="M1", clock=FakeClock(), db_pool=w.db)
    await rt.run_turn(w.ident, "select:bill:709744", w.state)
    assert w.pending()[pid].get("invalidated") is True
    assert U.STORE.counts()["uploads"] == 0


async def test_superseded_card_is_not_released(api):
    """被更正取代的舊卡 ⛔ 釋放（照片移給新卡）；按舊卡 ⇒ 失效句、照片仍在；新卡送出才釋放。"""
    w = _World()
    _seed_photos(w, [_jpeg(), _png()])
    _r1, pid1 = await w.repair_card()
    r2 = await w.turn("描述改成熱水器壞了", intents=[_intent("repair_create", description="熱水器壞了")])
    pid2 = r2.trace.pending_id
    assert _retained() == 2
    assert PENDING_PHOTOS_RELEASED_KEY not in w.pending()[pid1]
    stale = await w.turn(f"confirm_submit:{pid1}")
    assert stale.answer == CONFIRMATION_REQUIRED_TEXT
    cancel_old = await w.turn(f"confirm_cancel:{pid1}")
    assert cancel_old.answer == CONFIRMATION_REQUIRED_TEXT
    assert _retained() == 2                                   # 仍被活卡 pid2 引用 ⇒ 不刪
    done = await w.turn(f"confirm_submit:{pid2}")
    assert done.outcome["state"] == "confirmed", done.answer
    assert U.STORE.counts()["uploads"] == 0


# ════════════════════════════════════════════════════════════════════
# 3／4. S11 重新編碼、S5／A13 兌現比對
# ════════════════════════════════════════════════════════════════════
async def test_restart_store_empty_redeem_does_not_write_and_asks_reupload(api):
    """服務重啟（暫存清空）⇒ 兌現 ⛔ 寫入、回固定句；重按回同一句；⛔ 改成不附照片照送。"""
    w = _World()
    _seed_photos(w, [_jpeg(), _jpeg((9, 9, 9))])
    _r1, pid = await w.repair_card()
    U.STORE.reset()                                           # 模擬重啟
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.answer == PHOTO_REUPLOAD_TEXT and res.outcome["state"] == "failed"
    assert "photos_unavailable_at_redeem" in res.trace.violations
    assert _repair_posts(api) == []                           # jgb2 一次都沒被呼叫
    again = await w.turn(f"confirm_submit:{pid}")
    assert again.answer == PHOTO_REUPLOAD_TEXT and _repair_posts(api) == []
    # 正對照：同一套裝置、暫存還在 ⇒ 寫得進去且帶 2 個檔
    w2 = _World()
    w2.ident = w.ident
    _seed_photos(w2, [_jpeg(), _jpeg((9, 9, 9))])
    _r, pid_ok = await w2.repair_card()
    assert (await w2.turn(f"confirm_submit:{pid_ok}")).outcome["state"] == "confirmed"
    assert len(api._mock_transport.files[_repair_posts(api)[-1]]) == 2


async def test_swapped_bytes_do_not_write(api):
    """暫存裡的位元組被換掉（sha256 對不上卡）⇒ ⛔ 寫入、回固定句。"""
    w = _World()
    _seed_photos(w, [_jpeg()])
    _r1, pid = await w.repair_card()
    card_sha = _card_photos(w, pid)[0]["sha256"]
    rec = next(r for r in U.STORE._uploads.values() if r.photo_sha256 == card_sha)
    rec.data = _jpeg((0, 255, 0))                             # 查表仍命中、內容已不同
    res = await w.turn(f"confirm_submit:{pid}")
    assert res.answer == PHOTO_REUPLOAD_TEXT
    assert _repair_posts(api) == []


async def test_sent_file_is_reencoded_jpeg_without_exif_gps_or_trailer(api):
    """S11：送出的是 Pillow 重新編碼的 JPEG：轉正方向、⛔ EXIF／GPS、⛔ 檔尾夾帶；PNG 也轉成 JPEG。"""
    w = _World()
    tainted = _jpeg(exif=True, trailer=b"HIDDEN-TRAILER-PAYLOAD")
    assert b"Exif" in tainted and b"HIDDEN-TRAILER-PAYLOAD" in tainted     # 正對照：原檔真的有
    assert Image.open(io.BytesIO(tainted)).getexif().get(0x0112) == 6
    _seed_photos(w, [tainted, _png()])
    _r1, pid = await w.repair_card()
    assert (await w.turn(f"confirm_submit:{pid}")).outcome["state"] == "confirmed"
    files = api._mock_transport.files[_repair_posts(api)[-1]]
    assert [(f[1], f[2]) for f in files] == [("photo-1.jpg", "image/jpeg"), ("photo-2.jpg", "image/jpeg")]
    for _field, _name, _ctype, content in files:
        assert content.startswith(b"\xff\xd8\xff")
        assert b"Exif" not in content and b"HIDDEN-TRAILER-PAYLOAD" not in content
        img = Image.open(io.BytesIO(content))
        assert img.format == "JPEG" and len(img.getexif()) == 0
    assert Image.open(io.BytesIO(files[0][3])).size == (32, 64)            # 方向 6 已轉正


async def test_card_sha_is_bound_at_issuance_and_matches_the_sent_bytes(api):
    """卡上 sha256＝出卡時重新編碼那一份；暫存裡同一筆只編一次（再出卡沿用）。"""
    w = _World()
    metas = _upload(w.ident, [_jpeg()])
    first = await _encode_card_photos(w.ident, metas)
    second = await _encode_card_photos(w.ident, metas)
    assert first == second and first[0]["sha256"] != metas[0]["sha256"]
    binding = U.binding_from_identity(w.ident, "repair")
    ref, data = U.STORE.photo_bytes(first[0]["sha256"], binding)
    assert hashlib.sha256(data).hexdigest() == first[0]["sha256"] and len(data) == first[0]["size"]
    # 暫存裡沒有的照片（重啟、到期、URL 回退模式）⇒ 保留原中繼資料（兌現時 fail-closed）
    U.STORE.reset()
    assert await _encode_card_photos(w.ident, metas) == metas


# ════════════════════════════════════════════════════════════════════
# 5. multipart 交 jgb2（mock）
# ════════════════════════════════════════════════════════════════════
async def test_multipart_fields_and_broken_photos_files(api, tmp_path, monkeypatch):
    """有照片 ⇒ multipart：文字欄位同名表單欄位（字串）、每張一個 `broken_photos[]`、冪等鍵照舊；
    mock 紀錄 `row.broken_photos`＝每張 sha256／大小，⛔ 位元組。沒照片 ⇒ 現行 JSON（正對照）。"""
    log = tmp_path / "writes.jsonl"
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(log))
    w = _World()
    _seed_photos(w, [_jpeg(), _jpeg((5, 6, 7))])
    _r1, pid = await w.repair_card()
    card = _card_photos(w, pid)
    assert (await w.turn(f"confirm_submit:{pid}")).outcome["state"] == "confirmed"
    i = _repair_posts(api)[-1]
    form = api._mock_transport.bodies[i]
    files = api._mock_transport.files[i]
    assert all(isinstance(v, str) for v in form.values())
    assert {"role_id", "viewer_user_id", "estate_id", "category_id", "broken_reason", "emergency_status",
            "idempotency_key"} <= set(form) and "user_id" not in form
    assert form["estate_id"] == "67338" and "broken_photos" not in form
    assert [f[0] for f in files] == ["broken_photos[]", "broken_photos[]"]
    line = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert line["multipart"] is True and line["status"] == 200
    assert line["body"]["idempotency_key"] == "<redacted>"
    assert line["row"]["broken_photos"] == card == line["body"]["broken_photos"]
    raw = log.read_text(encoding="utf-8")
    for f in files:
        assert f[3][200:240].hex() not in raw and "\\xff\\xd8" not in raw
    assert len(raw) < 20_000                                 # 只有中繼資料

    # 正對照：沒照片的修繕卡 ⇒ JSON body（無檔、整數型別不變）
    w2 = _World()
    w2.ident = w.ident
    _r, pid2 = await w2.repair_card(f"{STUDENT_ESTATE} 燈不亮", description="燈不亮")
    assert (await w2.turn(f"confirm_submit:{pid2}")).outcome["state"] == "confirmed"
    j = _repair_posts(api)[-1]
    assert api._mock_transport.files[j] is None
    assert api._mock_transport.bodies[j]["estate_id"] == 67338
    assert "multipart" not in json.loads(log.read_text(encoding="utf-8").splitlines()[-1])


async def test_mock_multipart_validation(api):
    """mock 收 multipart：型別（magic bytes）、張數、欄位名都驗；⛔ 別的端點收 multipart。"""
    base = {"role_id": "20151", "viewer_user_id": "12291", "estate_id": "67338", "category_id": "1",
            "item_id": "1", "broken_reason": "斷裂", "broken_note": "", "emergency_status": "1"}
    jpg = _jpeg()

    def files(n, *, field="broken_photos[]", ctype="image/jpeg", content=jpg):
        return [(field, (f"photo-{k}.jpg", content, ctype)) for k in range(1, n + 1)]

    async def send(fs, form=base, path="/api/external/v1/repairs"):
        return await api._send("POST", path, data=dict(form), files=fs)

    ok = await send(files(10))                                # 10 張可收
    assert ok["success"] is True and len(ok["data"]["broken_photos"]) == 10
    assert ok["data"]["broken_photos"][0] == {"filename": "photo-1.jpg", "content_type": "image/jpeg",
                                              "size": len(jpg),
                                              "sha256": hashlib.sha256(jpg).hexdigest()}
    for bad in (files(11), files(1, field="photos[]"), files(1, ctype="image/png"),
                files(1, content=b"GIF89a" + b"0" * 20), []):
        r = await send(bad)
        assert r["success"] is False and r["error"]["code"] == 422, bad
    r = await send(files(1), form={**base, "estate_id": "abc"})
    assert r["error"]["code"] == 422
    r = await send(files(1), path="/agent/v1/bills/manual")
    assert r["error"]["code"] == 415


# ════════════════════════════════════════════════════════════════════
# 6. 張數上限 5→10
# ════════════════════════════════════════════════════════════════════
async def test_six_to_ten_photos_attach_and_eleven_are_blocked(api):
    assert REPAIR_PHOTOS_MAX == 10
    w = _World()
    _seed_photos(w, [_jpeg((k * 20, 0, 0)) for k in range(10)])
    r1, pid = await w.repair_card()
    assert "・附照片：10 張" in r1.answer
    assert (await w.turn(f"confirm_submit:{pid}")).outcome["state"] == "confirmed"
    assert len(api._mock_transport.files[_repair_posts(api)[-1]]) == 10
    # 6 張也照附
    w6 = _World()
    w6.ident = w.ident
    _seed_photos(w6, [_jpeg((0, k * 20, 0)) for k in range(6)])
    r6, _ = await w6.repair_card()
    assert "・附照片：6 張" in r6.answer
    # 11 張 ⇒ 卡上「未附」、⛔ 送（render 也擋 11 張的中繼資料）
    meta = {"filename": "photo-1.jpg", "content_type": "image/jpeg", "size": 10, "sha256": "a" * 64}
    with pytest.raises(ConfirmCardError):
        render("repair_create", {"action": "repair_create", "estate_name": "x", "description": "y",
                                 "broken_photos": [meta] * 11})
    w11 = _World()
    w11.ident = w.ident
    w11.state = {"agent": {IMAGE_SUGGESTION_KEY: {"category_name": "水龍頭",
                                                  "photos": [dict(meta, filename=f"photo-{k}.jpg")
                                                             for k in range(1, 12)]}}}
    r11, pid11 = await w11.repair_card()
    assert "・附照片：未附（本次 11 張，超過 10 張上限）" in r11.answer
    assert "broken_photos" not in w11.pending()[pid11]["payload"]


# ════════════════════════════════════════════════════════════════════
# 暫存：綁定
# ════════════════════════════════════════════════════════════════════
def test_photo_lookups_and_release_require_the_same_binding():
    from services.agent.identity import Identity
    me = F.namespaced_identity(Identity(vendor_id=4, target_user="property_manager", mode="b2b",
                                        role_id="20151", user_id="12291", session_id="w1",
                                        api_key_id=1, entry="mcp"))
    other = F.namespaced_identity(Identity(vendor_id=4, target_user="property_manager", mode="b2b",
                                           role_id="20151", user_id="12291", session_id="w2",
                                           api_key_id=1, entry="mcp"))
    mine, theirs = U.binding_from_identity(me, "repair"), U.binding_from_identity(other, "repair")
    metas = _upload(me, [_jpeg()])
    assert U.STORE.photo_source(metas[0]["sha256"], theirs) is None
    ref, data, done = U.STORE.photo_source(metas[0]["sha256"], mine)
    assert done is None
    from services.documind_client import reencode_photo_jpeg
    sha = U.STORE.set_photo(ref, mine, reencode_photo_jpeg(data))
    assert U.STORE.set_photo(ref, theirs, reencode_photo_jpeg(data)) is None
    assert U.STORE.photo_bytes(sha, theirs) is None and U.STORE.photo_bytes(sha, mine) is not None
    assert U.STORE.release_photos([sha], theirs) == 0 and U.STORE.counts()["uploads"] == 1
    assert U.STORE.release_photos([sha], mine) == 1 and U.STORE.counts()["uploads"] == 0
    assert isinstance(JGBMockTransport.REPAIR_PHOTO_MAX_COUNT, int)
