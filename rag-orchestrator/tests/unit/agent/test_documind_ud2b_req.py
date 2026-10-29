"""unit：UD-2b——收據與修繕照片的辨識接到 DocuMind（設了 DocuMind 才走；沒設 ⇒ 現行路徑）。

依據：`plan-upload-documind-20261028.md` §4 UD-2、S4、S10；UD-2b 執行合約「要做的事」1～6。

全部離線：抓檔、我方擷取、DocuMind 一律替身——DocuMind 的結果用
`fixtures/documind_probe/` 的 5 份實測回應經 UD-2a 的 `parse_*_response` 解出（⛔ 手寫結果）；
走真 client 的幾條用 `httpx.MockTransport`（⛔ 一次真連線都不發）。每條「不填／不送」旁邊
都有一個已知必然通過的正對照。
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from services import documind_client as dm
from services.agent import document_extract as dx
from services.agent import image_fetch
from services.agent import mcp_facade as F
from services.agent.runtime import IMAGE_CANDIDATE_MAX

from tests.unit.agent.test_documind_client_req import DOOR, electronic_response

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R10")]

_PROBE_DIR = Path(__file__).parent / "fixtures" / "documind_probe"
_PDF_URL = "https://relay.jgbsmart.com/d.pdf"
_IMG_URL = "https://relay.jgbsmart.com/a.jpg"
FREE_ISSUER = "合成五金行"
FREE_ITEM = "合成燈泡"

#: 測試用分類樹：「天花板」是唯一葉；「牆壁」不在樹上；「門窗類」是大類名（不是葉）。
TREE = [
    {"id": 1, "name": "土木類", "items": [{"id": 11, "name": "天花板"}, {"id": 12, "name": "地板"}]},
    {"id": 2, "name": "門窗類", "items": [{"id": 21, "name": "門鎖"}]},
]


def probe(name: str) -> dict:
    return json.loads((_PROBE_DIR / f"probe-{name}.json").read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jpeg(color=(120, 140, 160), *, exif=False) -> bytes:
    img = Image.new("RGB", (64, 48), color)
    buf = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "合成相機"
        img.save(buf, format="JPEG", exif=ex.tobytes())
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def _webp(color=(30, 90, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), color).save(buf, format="WEBP")
    return buf.getvalue()


def _synth_pdf(pages: int = 1) -> bytes:
    from tests.unit.agent.test_document_turn_req import _synth_pdf as make
    return make(pages=pages)


@pytest.fixture(autouse=True)
def _clean_counts():
    image_fetch.reset_image_count_cap()
    image_fetch.reset_file_count_cap()
    image_fetch.reset_image_failures()
    yield


@pytest.fixture()
def no_documind(monkeypatch):
    for k in (dm.DOCUMIND_BASE_URL_ENV, dm.DOCUMIND_TOKEN_ENV, dm.DOCUMIND_INSECURE_TEST_HOST_ENV,
              dm.DOCUMIND_INSECURE_HOST_ENV):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


@pytest.fixture()
def documind_on(no_documind):
    no_documind.setenv(dm.DOCUMIND_BASE_URL_ENV, "https://documind.example.test/api/v1")
    no_documind.setenv(dm.DOCUMIND_TOKEN_ENV, "tok123")
    no_documind.delenv(dm.DOCUMIND_SYNTHETIC_GUARD_ENV, raising=False)     # 防護開著
    return no_documind


def _allow(monkeypatch, *datas: bytes) -> None:
    allowed = frozenset(_sha(d) for d in datas)
    monkeypatch.setattr(dm, "synthetic_sha256_allowlist", lambda: allowed)


class _FileFetcher:
    def __init__(self, data, content_type="application/pdf"):
        self.data = data
        self.content_type = content_type

    async def __call__(self, url, *, timeout_s):
        return image_fetch.FetchedImage(data=self.data, content_type=self.content_type)


class _PhotoFetcher:
    def __init__(self, blobs, content_type="image/jpeg"):
        self.blobs = list(blobs)
        self.content_type = content_type

    async def __call__(self, url, *, timeout_s):
        return image_fetch.FetchedImage(data=self.blobs.pop(0), content_type=self.content_type)


class _Extractor:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def __call__(self, data_urls, **kw):
        self.calls += 1
        return self.result, {"prompt_tokens": 1, "completion_tokens": 1}, "gpt-6-luna"


def _receipt_result(**fields_over) -> dict:
    """我方模型的收據擷取（分類用；DocuMind 路徑 ⛔ 取它的欄位值）。金額刻意與 probe 不同。"""
    fields = {"issuer": FREE_ISSUER, "payer": "合成乙", "amount": 111, "currency": "TWD",
              "date": "2026-01-01", "items": [{"name": FREE_ITEM, "amount": 111}],
              "payment_method": "現金", "reference_no": "ZZ-00000001"}
    fields.update(fields_over)
    return {"kind": "bill_receipt", "page_count": 1, "unreadable": False, "uncertain": [],
            "fields": fields, "evidence": None}


def _deed_result() -> dict:
    return {"kind": "building_deed", "page_count": 1, "unreadable": False, "uncertain": [],
            "fields": {}, "evidence": None}


class _AnalyzeSpy:
    """`F._documind_analyze_file` 的替身：依序回 `results`（不足 ⇒ 重複最後一個）。"""

    def __init__(self, *results):
        self.results = list(results)
        self.calls: list = []

    async def __call__(self, data, *, document_type, timeout_s, config):
        self.calls.append({"data": data, "document_type": document_type,
                           "timeout_s": timeout_s, "config": config})
        if len(self.results) > 1:
            out = self.results.pop(0)
        else:
            out = self.results[0]
        if isinstance(out, Exception):
            raise out
        return out


class _DeedSpy:
    def __init__(self, result):
        self.result = result
        self.calls: list = []

    async def __call__(self, data, *, timeout_s, pdf_pages, config):
        self.calls.append({"data": data, "pdf_pages": pdf_pages})
        return self.result


def _receipt_of(name: str) -> dm.ReceiptResult:
    return dm.parse_receipt_response(probe(name))


def _photo_of(name: str) -> dm.RepairPhotoResult:
    return dm.parse_repair_photo_response(probe(name))


def _fact_lines(facts: str) -> list:
    head, _, body = facts.partition("\n")
    assert head == dx.DOCUMENT_CONTENT_PREFIX
    return body.split("\n")


# ════════════════════════════════════════════════════════════════════
# 要做的事 2：收據
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("name,amount,day", [
    ("receipt-receipt-1", 588, "2026-10-12"),
    ("receipt-receipt-2", 2350, "2026-10-08"),
    ("receipt-receipt-inject", 860, "2026-10-13"),
])
async def test_receipt_probe_amount_goes_on_card_and_facts_are_closed_sentences(
        monkeypatch, documind_on, name, amount, day):
    original = _jpeg(exif=True)
    spy = _AnalyzeSpy(_receipt_of(name))
    monkeypatch.setattr(F, "_documind_analyze_file", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    # 送的是上傳原檔、類型 receipt
    assert len(spy.calls) == 1 and spy.calls[0]["document_type"] == "receipt"
    assert spy.calls[0]["data"] == original and b"Exif" in spy.calls[0]["data"]
    # 卡：金額取 DocuMind，日期當卡外提示
    assert turn.typed_fields == (("total", amount),) and turn.receipt_date == day
    assert dx.document_writable_action(turn) == "manual_bill_create"
    # 資料段：只有程式組的封閉句（⛔ 我方模型的開立單位、品名、金額 111）
    assert _fact_lines(turn.facts) == [
        "文件種類：收據。", f"金額：{amount} 元。", f"收據日期：{day}。",
    ]
    assert FREE_ISSUER not in turn.facts and FREE_ITEM not in turn.facts and "111" not in turn.facts
    # 縱深比對用的自由文字照舊來自本回合擷取（只活在記憶體）
    assert FREE_ISSUER in turn.free_text


@pytest.mark.parametrize("result", [
    dm.ReceiptResult("ok", None, "2026-10-12"),
    dm.ReceiptResult("ok"),
    dm.ReceiptResult("failed"), dm.ReceiptResult("timeout"),
    dm.ReceiptResult("blocked"), dm.ReceiptResult("disabled"),
])
async def test_receipt_without_amount_or_not_ok_falls_to_missing_field_ask(
        monkeypatch, documind_on, result):
    monkeypatch.setattr(F, "_documind_analyze_file", _AnalyzeSpy(result))
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert turn.typed_fields == () and turn.notice is None
    assert dx.RECEIPT_NO_AMOUNT_SENTENCE in turn.facts and "111" not in turn.facts
    assert dx.document_writable_action(turn) == "manual_bill_create"     # 仍可出卡 ⇒ 缺欄追問
    assert turn.receipt_date == result.date


async def test_receipt_documind_exception_is_treated_as_no_amount(monkeypatch, documind_on):
    monkeypatch.setattr(F, "_documind_analyze_file", _AnalyzeSpy(RuntimeError("boom")))
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert turn.typed_fields == () and dx.RECEIPT_NO_AMOUNT_SENTENCE in turn.facts


async def test_receipt_without_documind_uses_current_path_unchanged(monkeypatch, no_documind):
    """正對照：沒設 DocuMind ⇒ 我方模型路徑（金額 111、資料段＝`build_document_facts`）、0 次送出。"""
    spy = _AnalyzeSpy(_receipt_of("receipt-receipt-1"))
    monkeypatch.setattr(F, "_documind_analyze_file", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert spy.calls == []
    assert turn.typed_fields == (("total", 111),) and turn.receipt_date == "2026-01-01"
    assert turn.facts == dx.build_document_facts(_receipt_result())
    assert FREE_ISSUER in turn.facts


async def test_receipt_pdf_is_not_accepted_by_client_so_it_is_not_sent(monkeypatch, documind_on):
    spy = _AnalyzeSpy(_receipt_of("receipt-receipt-1"))
    monkeypatch.setattr(F, "_documind_analyze_file", spy)
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([], [_PDF_URL])
    assert spy.calls == [] and turn.typed_fields == ()
    assert dx.RECEIPT_NO_AMOUNT_SENTENCE in turn.facts
    assert "pdf" not in dm._ALLOWED_KINDS["receipt"] and "pdf" in dm._ALLOWED_KINDS["transcript"]


async def test_receipt_with_two_attachments_is_not_sent(monkeypatch, documind_on):
    spy = _AnalyzeSpy(_receipt_of("receipt-receipt-1"))
    monkeypatch.setattr(F, "_documind_analyze_file", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg(), _jpeg((1, 2, 3))]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL, _IMG_URL], [])
    assert spy.calls == [] and turn.typed_fields == ()
    # 正對照：一張 ⇒ 送出、有金額
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    turn2, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert len(spy.calls) == 1 and turn2.typed_fields == (("total", 588),)


async def test_receipt_through_real_client_guard_compares_original_and_sends_reencoded(
        monkeypatch, documind_on):
    """真 client：原檔在合成清單 ⇒ 過防護；送出的是去 EXIF 的重新編碼 JPEG；回 probe ⇒ 588 上卡。"""
    original = _jpeg(exif=True)
    _allow(monkeypatch, original)
    seen: list = []

    def handler(request: httpx.Request):
        request.read()
        seen.append(request)
        return httpx.Response(200, json=probe("receipt-receipt-1"))

    monkeypatch.setattr(dm, "_new_client", lambda t: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False))
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert turn.typed_fields == (("total", 588),)
    body = seen[0].content
    assert b'name="document_type"' in body and b"receipt" in body
    assert original not in body and b"Exif" not in body and b"\xff\xd8\xff" in body
    # 反向：原檔不在清單 ⇒ blocked ⇒ 不送、缺欄追問
    seen.clear()
    _allow(monkeypatch, b"something-else")
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original]))
    turn2, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert seen == [] and turn2.typed_fields == ()


def test_build_receipt_facts_is_closed_and_never_empty():
    assert _fact_lines(dx.build_receipt_facts((), None)) == [
        dx.RECEIPT_KIND_SENTENCE, dx.RECEIPT_NO_AMOUNT_SENTENCE]
    # 型別不對、未知鍵、壞日期一律不進
    facts = dx.build_receipt_facts((("total", "588"), ("issuer", "x")), "2026-02-30")
    assert _fact_lines(facts) == [dx.RECEIPT_KIND_SENTENCE, dx.RECEIPT_NO_AMOUNT_SENTENCE]
    assert _fact_lines(dx.build_receipt_facts((("total", 588),), "2026-10-12")) == [
        "文件種類：收據。", "金額：588 元。", "收據日期：2026-10-12。"]


# ════════════════════════════════════════════════════════════════════
# 要做的事 3：修繕照片
# ════════════════════════════════════════════════════════════════════
class _Recognizer:
    def __init__(self):
        self.batches: list = []

    async def __call__(self, data_urls, **kw):
        self.batches.append(list(data_urls))
        return {"is_damage": True, "confidence": 0.9, "suggested_category": "土木類",
                "suggested_item": "天花板", "description": "我方模型描述"}


async def _photo_turn(monkeypatch, results, blobs=None, tree=TREE, **kw):
    blobs = blobs if blobs is not None else [_jpeg((i * 30 % 255, 10, 10)) for i in range(len(results))]
    spy = _AnalyzeSpy(*results)
    rec = _Recognizer()
    monkeypatch.setattr(F, "_documind_analyze_file", spy)
    monkeypatch.setattr(F, "_image_recognize_batch", rec)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher(blobs))
    turn, elapsed = await F.prepare_image_turn([_IMG_URL] * len(blobs), category_tree=tree, **kw)
    return turn, spy, rec, blobs


async def test_two_damages_ceiling_hits_leaf_and_wall_not_in_tree_is_skipped(monkeypatch, documind_on):
    res = _photo_of("repair_photo-two_damages")
    assert res.damaged_items == ("天花板", "牆壁")                       # 夾具前提
    turn, spy, rec, blobs = await _photo_turn(monkeypatch, [res])
    assert rec.batches == []                                            # 我方模型 0 次
    assert spy.calls[0]["document_type"] == "repair_photo" and spy.calls[0]["data"] == blobs[0]
    assert turn.status == "ok" and turn.suggested_category == "天花板"
    assert turn.suggested_parent_category == "土木類" and turn.candidates == ()
    assert "照片辨識到的修繕分類是「天花板」。" in turn.facts
    # 描述：DocuMind 的 description 只進 suggested_description，⛔ 進資料段
    assert turn.suggested_description == res.description and res.description not in turn.facts
    assert "龜裂" not in turn.facts and "壁癌" not in turn.facts
    assert turn.suggested_item == "天花板" and turn.suggested_reason == "壁癌"
    assert turn.suggested_emergency is None
    assert [p["sha256"] for p in turn.photos] == [_sha(blobs[0])]


async def test_wall_alone_is_not_filled_and_category_name_is_not_a_leaf(monkeypatch, documind_on):
    wall = dm.RepairPhotoResult("damaged", damaged_items=("牆壁",), defect_labels=("霉菌",))
    turn, *_ = await _photo_turn(monkeypatch, [wall])
    assert turn.suggested_category is None and turn.candidates == ()
    assert "照片辨識不出對應的修繕分類。" in turn.facts
    # 大類名稱不算：「門窗類」是大類
    big = dm.RepairPhotoResult("damaged", damaged_items=("門窗類",))
    turn2, *_ = await _photo_turn(monkeypatch, [big])
    assert turn2.suggested_category is None and turn2.candidates == ()
    # 正對照：同一棵樹的葉「門鎖」⇒ 填，大類名記在 parent
    leaf = dm.RepairPhotoResult("damaged", damaged_items=("門鎖",))
    turn3, *_ = await _photo_turn(monkeypatch, [leaf])
    assert turn3.suggested_category == "門鎖" and turn3.suggested_parent_category == "門窗類"


async def test_duplicate_leaf_name_in_tree_is_not_filled(monkeypatch, documind_on):
    dup_tree = TREE + [{"id": 3, "name": "水電類", "items": [{"id": 31, "name": "天花板"}]}]
    res = _photo_of("repair_photo-two_damages")
    turn, *_ = await _photo_turn(monkeypatch, [res], tree=dup_tree)
    assert turn.suggested_category is None and turn.candidates == ()
    # 葉名與某大類同名也算重名
    clash_tree = TREE + [{"id": 4, "name": "天花板", "items": []}]
    turn2, *_ = await _photo_turn(monkeypatch, [res], tree=clash_tree)
    assert turn2.suggested_category is None and turn2.candidates == ()
    # 正對照：原樹 ⇒ 填
    turn3, *_ = await _photo_turn(monkeypatch, [res])
    assert turn3.suggested_category == "天花板"


async def test_multiple_hits_become_candidates(monkeypatch, documind_on):
    one = dm.RepairPhotoResult("damaged", damaged_items=("天花板", "地板"))
    turn, *_ = await _photo_turn(monkeypatch, [one])
    assert turn.candidates == ("天花板", "地板") and turn.suggested_category is None
    # 跨照片合併、去重、上限 IMAGE_CANDIDATE_MAX
    a = dm.RepairPhotoResult("damaged", damaged_items=("天花板", "門鎖"))
    b = dm.RepairPhotoResult("damaged", damaged_items=("天花板", "地板", "牆壁"))
    c = dm.RepairPhotoResult("damaged", damaged_items=("門鎖",))
    turn2, *_ = await _photo_turn(monkeypatch, [a, b, c])
    assert turn2.candidates == ("天花板", "門鎖", "地板")[:IMAGE_CANDIDATE_MAX]
    assert turn2.status == "ok" and turn2.processed == 3 and len(turn2.photos) == 3


async def test_plain_photo_is_no_damage_path(monkeypatch, documind_on):
    res = _photo_of("repair_photo-plain")
    assert res.status == "no_damage"                                    # 夾具前提
    turn, *_ = await _photo_turn(monkeypatch, [res])
    assert turn.status == "ok" and "照片看不出損壞。" in turn.facts
    assert turn.suggested_category is None and turn.candidates == ()
    assert turn.suggested_description is None and len(turn.photos) == 1   # 照片照附（⛔ 擋報修）


@pytest.mark.parametrize("status", ["failed", "timeout", "disabled", "blocked"])
async def test_failed_statuses_are_recognition_failure_and_photos_are_kept(
        monkeypatch, documind_on, status):
    assert image_fetch.image_failure_stats()["failures_1h"] == 0
    turn, spy, rec, blobs = await _photo_turn(monkeypatch, [dm.RepairPhotoResult(status)])
    assert turn.status == "failed" and turn.facts == ""                 # ⛔ 當成看不出損壞
    assert "照片看不出損壞" not in turn.facts
    assert [p["sha256"] for p in turn.photos] == [_sha(blobs[0])]
    assert rec.batches == [] and len(spy.calls) == 1
    assert image_fetch.image_failure_stats()["failures_1h"] == 1        # 失敗看得見（健檢）


async def test_documind_exception_is_recognition_failure(monkeypatch, documind_on):
    turn, *_ = await _photo_turn(monkeypatch, [RuntimeError("boom")])
    assert turn.status == "failed" and len(turn.photos) == 1


async def test_any_damaged_photo_wins_and_failed_photo_is_still_attached(monkeypatch, documind_on):
    results = [dm.RepairPhotoResult("failed"), _photo_of("repair_photo-two_damages"),
               _photo_of("repair_photo-plain")]
    turn, spy, rec, blobs = await _photo_turn(monkeypatch, results)
    assert turn.status == "partial" and turn.processed == 2 and turn.total == 3
    assert turn.suggested_category == "天花板"
    assert "照片辨識到的修繕分類是「天花板」。" in turn.facts
    assert [p["sha256"] for p in turn.photos] == [_sha(b) for b in blobs]
    assert [p["filename"] for p in turn.photos] == ["photo-1.jpg", "photo-2.jpg", "photo-3.jpg"]


async def test_photos_without_documind_use_current_recognizer(monkeypatch, no_documind):
    """正對照：沒設 DocuMind ⇒ 我方模型辨識 1 批、DocuMind 0 次。"""
    turn, spy, rec, _ = await _photo_turn(monkeypatch, [_photo_of("repair_photo-two_damages")])
    assert spy.calls == [] and len(rec.batches) == 1
    assert turn.suggested_category == "天花板" and turn.suggested_description == "我方模型描述"


async def test_photo_budget_exhausted_before_any_call_is_timeout(monkeypatch, documind_on):
    from tests.unit.agent.test_runtime_req import FakeClock
    clock = FakeClock()

    class _SlowFetcher(_PhotoFetcher):
        async def __call__(self, url, *, timeout_s):
            clock.advance(10.0)
            return await super().__call__(url, timeout_s=timeout_s)

    spy = _AnalyzeSpy(_photo_of("repair_photo-two_damages"))
    monkeypatch.setattr(F, "_documind_analyze_file", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _SlowFetcher([_jpeg()]))
    turn, _ = await F.prepare_image_turn([_IMG_URL], category_tree=TREE, budget_s=5.0, clock=clock)
    assert spy.calls == [] and turn.status == "timeout"
    # 正對照：預算夠 ⇒ 送出
    clock2 = FakeClock()
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    turn2, _ = await F.prepare_image_turn([_IMG_URL], category_tree=TREE, budget_s=5.0, clock=clock2)
    assert len(spy.calls) == 1 and turn2.status == "ok"


async def test_photo_through_real_client_and_webp_is_reencoded(monkeypatch, documind_on):
    """真 client：webp 原檔過防護比對後重新編碼成 JPEG 送出；回 two_damages ⇒ 天花板。"""
    original = _webp()
    assert dm._magic_kind(original) == "webp"
    _allow(monkeypatch, original)
    seen: list = []

    def handler(request: httpx.Request):
        request.read()
        seen.append(request)
        return httpx.Response(200, json=probe("repair_photo-two_damages"))

    monkeypatch.setattr(dm, "_new_client", lambda t: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False))
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original], content_type="image/webp"))
    turn, _ = await F.prepare_image_turn([_IMG_URL], category_tree=TREE)
    assert turn.suggested_category == "天花板"
    assert turn.photos[0]["content_type"] == "image/webp" and turn.photos[0]["sha256"] == _sha(original)
    body = seen[0].content
    assert b"repair_photo" in body and b'filename="photo.jpg"' in body
    assert original not in body and b"RIFF" not in body and b"\xff\xd8\xff" in body


async def test_webp_magic_bytes_accepted_only_for_photo_types():
    original = _webp()
    assert "webp" in dm._ALLOWED_KINDS["repair_photo"] and "webp" in dm._ALLOWED_KINDS["receipt"]
    assert "webp" not in dm._ALLOWED_KINDS["transcript"]
    assert dm._magic_kind(b"RIFF\x00\x00\x00\x00WAVE") is None                # 非 WEBP 的 RIFF
    assert dm.upload_name(original) is None                                    # 謄本相容入口不變
    status, _ = await dm._post(original, document_type="transcript", timeout_s=5,
                               config=dm.DocuMindConfig("https://x.test/analyze", "t"),
                               client_factory=None)
    assert status == "failed"


# ════════════════════════════════════════════════════════════════════
# 要做的事 1：謄本——傳原檔、blocked 固定句
# ════════════════════════════════════════════════════════════════════
async def test_deed_photo_passes_original_bytes_to_client(monkeypatch, documind_on):
    original = _jpeg(exif=True)
    spy = _DeedSpy(dm.DeedResult("ok", (("address", DOOR),)))
    monkeypatch.setattr(F, "_documind_analyze", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert spy.calls[0]["data"] == original and b"Exif" in spy.calls[0]["data"]
    assert spy.calls[0]["pdf_pages"] is None
    assert turn.notice is None and turn.typed_fields == (("address", DOOR),)


async def test_deed_photo_through_real_client_passes_guard_and_is_reencoded(monkeypatch, documind_on):
    """修正前呼叫端先重新編碼 ⇒ 送進 client 的 sha 不在清單 ⇒ 必然 blocked；現在原檔過防護。"""
    original = _jpeg(exif=True)
    _allow(monkeypatch, original)
    seen: list = []

    def handler(request: httpx.Request):
        request.read()
        seen.append(request)
        return httpx.Response(200, json=electronic_response())

    monkeypatch.setattr(dm, "_new_client", lambda t: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False))
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([_IMG_URL], [])
    assert turn.notice is None and ("address", DOOR) in turn.typed_fields
    body = seen[0].content
    assert original not in body and b"Exif" not in body and b'filename="deed.jpg"' in body


async def test_deed_blocked_returns_fixed_sentence(monkeypatch, documind_on):
    monkeypatch.setattr(F, "_documind_analyze", _DeedSpy(dm.DeedResult("blocked")))
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([], [_PDF_URL])
    assert turn.notice == "deed_blocked" and turn.facts == "" and turn.typed_fields == ()
    assert dx.DOCUMENT_NOTICE_TEXTS["deed_blocked"] == (
        "這份文件目前無法辨識（測試期間只接受指定的樣本檔），請改用手動輸入。")
    assert dx.document_writable_action(turn) is None
    # 正對照：failed 仍是「沒讀成功」那一句
    monkeypatch.setattr(F, "_documind_analyze", _DeedSpy(dm.DeedResult("failed")))
    turn2, _ = await F.prepare_document_turn([], [_PDF_URL])
    assert turn2.notice == "deed_failed"


async def test_deed_blocked_through_real_client_when_original_not_in_list(monkeypatch, documind_on):
    _allow(monkeypatch, b"other")
    seen: list = []
    monkeypatch.setattr(dm, "_new_client", lambda t: httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: seen.append(r) or httpx.Response(500)),
        follow_redirects=False, trust_env=False))
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([], [_PDF_URL])
    assert seen == [] and turn.notice == "deed_blocked"
