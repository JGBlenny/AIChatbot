"""unit：DocuMind 建物謄本解析的呼叫端（站內幫手 S3，計畫 §3h 第 4 點＋安全審查 D1～D10）。

全部離線：HTTP 一律走 `httpx.MockTransport`（⛔ 一次真連線都不發）；回應形狀照
DocuMind 對接規格 2.4.0 實測回應的**形狀**，以**合成值**在本檔重建（⛔ 依賴 repo 外檔）。
每條「擋掉／不填」旁邊都有一個已知必然通過的正對照。
"""
from __future__ import annotations

import copy
import io
import json
import logging

import httpx
import pytest
from PIL import Image

from services import documind_client as dm

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R10")]

# 合成值（虛構；所有權部三項是 must_not_appear 負對照）
OWNER_NAME = "合成甲"
OWNER_ID = "Z199999999"
OWNER_ADDR = "新北市合成區虛構路九段9號9樓"
DOOR = "合成路一段1號5樓"
MUST_NOT_APPEAR = (OWNER_NAME, OWNER_ID, OWNER_ADDR)


def electronic_response(**label_over) -> dict:
    """電子謄本回應（`transcript_records` 恰 1 筆、`標示部` 有值）。"""
    label = {
        "登記日期": "民國100年03月15日", "登記原因": "第一次登記",
        "建物門牌": DOOR, "建物坐落地號": [{"段小段": "合成段一小段", "編號": "0123-0000"}],
        "主要用途": "住家用", "主要建材": "鋼筋混凝土造", "層數": "12層", "總面積": 68.47,
        "層次": [{"層次": "五層", "面積": 60.35}], "附屬建物": [{"用途": "陽台", "面積": 8.12}],
        "建築完成日期": "民國099年12月20日",
        "共有部分": [{"坐落": "合成段一小段", "建號": "01299-000", "面積": 211.8,
                   "權利範圍": "10分之1", "其他登記事項": []}],
        "其他登記事項": [],
    }
    label.update(label_over)
    record = {
        "謄本": {"謄本種類": "建物登記第一類謄本(建號全部)", "類別": "第一類", "申請範圍": "建號全部",
               "行政區": "大安區", "段": "合成段", "小段": "一小段", "編號": "01234-000",
               "編號類型": "建號", "列印時間": "民國115年10月15日10時32分", "頁數": 1,
               "資料管轄機關": "臺北市大安地政事務所", "謄本核發機關": "臺北市大安地政事務所",
               "頁首附註": ["合成測試資料"]},
        "類型": "建物",
        "標示部": label,
        "所有權部": [{"次序": "0001", "所有權人": OWNER_NAME, "統一編號": OWNER_ID,
                  "住址": OWNER_ADDR, "權利範圍": "全部", "管理者": [], "其他登記事項": []}],
        "他項權利部": [],
        "判定": {"他項權利": "未見", "限制登記": "未見", "信託": "未見"},
        "部是否印出": {"標示部": True, "所有權部": True, "他項權利部": True},
        "部附註": {"標示部": [], "所有權部": [], "他項權利部": []},
        "注意事項": [], "其他欄位": [],
    }
    return {
        "file_name": "deed.pdf", "file_url": None, "document_type": "transcript", "total_pages": 1,
        "pages": [{"page_number": 1, "ocr_raw": {"text": f"{OWNER_NAME} {OWNER_ID} {OWNER_ADDR}",
                                                  "confidence": 1.0}}],
        "document_fields": {
            "owner": OWNER_NAME, "building_address": DOOR, "main_usage": "住家用",
            "total_area": "68.47", "floor_level": "五層",
            "field_confidences": {"building_address": 0.9, "main_usage": 0.9,
                                  "total_area": 0.9, "floor_level": 0.9, "owner": 0.9},
            "needs_confirmation": [],
            "owners": [{"part": "building", "transcript_id": "01234-000", "order": "0001",
                        "name": OWNER_NAME, "rights_scope": "全部"}],
            "land_numbers": [{"section": "合成段一小段", "number": "0123-0000"}],
            "floor_area_checks": [{"transcript_id": "01234-000", "sum": "60.35",
                                   "total": "68.47", "matches": False}],
            "shared_parts": [{"transcript_id": "01234-000", "build_number": "01299-000"}],
            "transcripts": [{"sections": [{"部": "建物所有權部", "entries": [
                {"所有權人": {"_值": OWNER_NAME, "統一編號": OWNER_ID, "住址": OWNER_ADDR}}]}]}],
            "transcript_records": [record],
        },
        "needs_review": False,
    }


def scanned_response(**field_over) -> dict:
    """掃描／拍照回應：`transcript_records` 是 1 筆空殼（`標示部` null）。"""
    resp = electronic_response()
    shell = {k: None for k in ("類型", "標示部")}
    shell.update({"謄本": {k: None for k in resp["document_fields"]["transcript_records"][0]["謄本"]},
                  "所有權部": [], "他項權利部": []})
    resp["document_fields"]["transcript_records"] = [shell]
    resp["document_fields"]["section"] = "测試段"          # OCR 錯字（⛔ 取 city／district）
    resp["document_fields"].update(field_over)
    return resp


EXPECTED_ELECTRONIC = (
    ("city", "台北市"), ("district", "大安區"), ("address", DOOR),      # R2：輸出用 JGB 寫法
    ("use_for", "residential"), ("size", 68.47), ("floor", "5樓"),
)


def _blob(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str) + repr(obj)


# ════════════════════════════════════════════════════════════════════
# D1：設定 fail-closed
# ════════════════════════════════════════════════════════════════════
#: 文件保留位址（RFC 5737 TEST-NET-1）。⚠️ 真的測試主機位址 ⛔ 寫進 repo（repo 公開；
#: 業主 2026-10-15），程式改由 env `DOCUMIND_INSECURE_TEST_HOST` 指定。
TEST_HOST = "192.0.2.10:8085"


@pytest.fixture()
def clean_env(monkeypatch):
    for k in (dm.DOCUMIND_BASE_URL_ENV, dm.DOCUMIND_TOKEN_ENV, dm.DOCUMIND_INSECURE_TEST_HOST_ENV,
              dm.DOCUMIND_INSECURE_HOST_ENV):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def _cfg(env, base=None, token=None, insecure=None, host=TEST_HOST):
    for key, value in ((dm.DOCUMIND_BASE_URL_ENV, base), (dm.DOCUMIND_TOKEN_ENV, token),
                       (dm.DOCUMIND_INSECURE_TEST_HOST_ENV, insecure),
                       (dm.DOCUMIND_INSECURE_HOST_ENV, host)):
        if value is None:
            env.delenv(key, raising=False)
        else:
            env.setenv(key, value)
    return dm.documind_config()


def test_config_https_with_token_is_the_only_normal_way(clean_env):
    cfg = _cfg(clean_env, "https://documind.example.test/api/v1/", "tok_abc-123")
    assert cfg == dm.DocuMindConfig("https://documind.example.test/api/v1/analyze", "tok_abc-123")


@pytest.mark.parametrize("base,token,insecure", [
    (None, None, None),                                             # 未設
    ("", "tok", None),                                              # 空字串
    ("https://documind.example.test/api/v1", None, None),          # https 缺 token
    ("https://u:p@documind.example.test/api/v1", "tok", None),     # userinfo
    ("https://documind.example.test/api/v1?x=1", "tok", None),     # query
    ("https://documind.example.test/api/v1#f", "tok", None),       # fragment
    ("https://documind.example.test/api/v1", "tok en", None),      # token 含空白
    ("https://documind.example.test/api/v1", "tok\nX-Evil: 1", None),  # header 注入
    ("http://documind.example.test/api/v1", "tok", "1"),           # 明文 http 但不是測試主機
    ("http://192.0.2.10:8085/api/v1", None, None),                 # 測試主機缺開關
    ("http://192.0.2.10:8085/api/v1", None, "true"),               # 開關值不是逐字 "1"
    ("http://192.0.2.10:8085/api/v1", None, " 1"),                 # 開關帶空白也不算
    ("http://192.0.2.10:8086/api/v1", None, "1"),                  # 連接埠不同
    ("http://192.0.2.10/api/v1", None, "1"),                       # 缺連接埠
    ("http://192.0.2.11:8085/api/v1", None, "1"),                  # 主機不同
    ("ftp://documind.example.test/api/v1", "tok", "1"),            # 其他 scheme
])
def test_config_everything_else_is_disabled(clean_env, base, token, insecure):
    assert _cfg(clean_env, base, token, insecure) is None


def test_config_insecure_test_host_needs_the_explicit_switch(clean_env):
    cfg = _cfg(clean_env, "http://192.0.2.10:8085/api/v1", None, "1")
    assert cfg == dm.DocuMindConfig("http://192.0.2.10:8085/api/v1/analyze", None)


def test_config_insecure_host_env_unset_or_empty_rejects_even_with_the_switch(clean_env):
    base = "http://192.0.2.10:8085/api/v1"
    assert _cfg(clean_env, base, None, "1", host=None) is None        # 未設
    assert _cfg(clean_env, base, None, "1", host="") is None          # 空字串
    assert _cfg(clean_env, base, None, "1") is not None               # 正對照：同一組設好 env 才准


@pytest.mark.parametrize("host_env", [
    "192.0.2.10",                    # 缺 port
    "192.0.2.10:",                   # port 空
    "192.0.2.10:80a5",               # port 非數字
    "192.0.2.10:08085",              # 前導零
    "192.0.2.10:99999",              # 超出範圍
    "http://192.0.2.10:8085",        # 含 scheme
    "192.0.2.10:8085/api/v1",        # 含路徑
    " 192.0.2.10:8085",              # 前後空白
    "user@192.0.2.10:8085",          # userinfo
    "192.0.2.10:8085,192.0.2.11:8085",  # 多台
])
def test_config_insecure_host_env_bad_shape_rejects(clean_env, host_env):
    assert _cfg(clean_env, "http://192.0.2.10:8085/api/v1", None, "1", host=host_env) is None
    assert dm.insecure_test_host() is None


def test_config_insecure_host_env_same_host_other_port_rejects(clean_env):
    assert _cfg(clean_env, "http://192.0.2.10:8085/api/v1", None, "1", host="192.0.2.10:9000") is None
    assert dm.insecure_test_host() == ("192.0.2.10", 9000)              # env 本身形狀合法（正對照）


def test_config_https_ignores_the_insecure_host_env(clean_env):
    """https 規則不變：與明文測試主機的設定無關。"""
    cfg = _cfg(clean_env, "https://documind.example.test/api/v1", "tok", None, host=None)
    assert cfg == dm.DocuMindConfig("https://documind.example.test/api/v1/analyze", "tok")
    assert _cfg(clean_env, "https://192.0.2.10:8085/api/v1", None, "1") is None   # https 缺 token 仍關


async def test_disabled_config_never_opens_a_connection(clean_env):
    opened: list = []

    def factory(timeout_s):
        opened.append(timeout_s)
        raise AssertionError("不該建連線")

    res = await dm.analyze_deed(b"%PDF-1.4 x", timeout_s=5, client_factory=factory)
    assert res.status == "disabled" and opened == []


# ════════════════════════════════════════════════════════════════════
# D3／D5／D6：送出與讀回
# ════════════════════════════════════════════════════════════════════
_CFG = dm.DocuMindConfig("https://documind.example.test/api/v1/analyze", "tok123")


def _factory(handler, seen=None):
    def factory(timeout_s):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler),
                                   follow_redirects=False, trust_env=False,
                                   timeout=httpx.Timeout(timeout_s))
        if seen is not None:
            seen.append(client)
        return client
    return factory


async def test_request_shape_minimal_and_headers():
    seen_req: list = []

    def handler(request: httpx.Request):
        seen_req.append(request)
        return httpx.Response(200, json=electronic_response())

    res = await dm.analyze_deed(b"%PDF-1.4 body", timeout_s=5, config=_CFG,
                                client_factory=_factory(handler))
    assert res.status == "ok" and res.typed_fields == EXPECTED_ELECTRONIC
    req = seen_req[0]
    assert req.method == "POST" and str(req.url) == _CFG.analyze_url
    assert req.headers["authorization"] == "Bearer tok123"
    body = req.read().decode("latin-1")
    assert 'name="document_type"' in body and "transcript" in body
    assert 'name="enable_llm"' in body and "false" in body                  # D6
    assert 'filename="deed.pdf"' in body                                     # 程式產生
    assert "question" not in body


def test_upload_name_follows_magic_bytes():
    assert dm.upload_name(b"%PDF-1.7") == ("deed.pdf", "application/pdf")
    assert dm.upload_name(b"\xff\xd8\xff\xe0xx") == ("deed.jpg", "image/jpeg")
    assert dm.upload_name(b"\x89PNG\r\n\x1a\nxx") == ("deed.png", "image/png")
    assert dm.upload_name(b"GIF89a") is None


async def test_real_client_is_built_without_redirects_or_env():
    client = dm._new_client(3.0)
    try:
        assert client.follow_redirects is False
        assert client.trust_env is False
    finally:
        await client.aclose()


@pytest.mark.parametrize("response", [
    httpx.Response(500, json={"detail": "x"}),
    httpx.Response(302, headers={"location": "https://evil.test/"}),
    httpx.Response(200, content=b"not json"),
    # 超過上限：**合法**的謄本回應＋墊料（拿掉上限時它會被當成成功——證明擋它的是上限）
    httpx.Response(200, json={**electronic_response(), "pad": "x" * (dm.RESPONSE_MAX_BYTES + 10)}),
])
async def test_non_200_redirect_non_json_and_oversize_are_failed(response):
    res = await dm.analyze_deed(b"%PDF-1.4", timeout_s=5, config=_CFG,
                                client_factory=_factory(lambda r: response))
    assert res.status == "failed" and res.typed_fields == ()


async def test_timeout_is_timeout():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    res = await dm.analyze_deed(b"%PDF-1.4", timeout_s=5, config=_CFG,
                                client_factory=_factory(handler))
    assert res.status == "timeout"
    assert (await dm.analyze_deed(b"%PDF-1.4", timeout_s=0, config=_CFG)).status == "timeout"


async def test_log_only_has_class_names_and_status(caplog):
    def handler(request):
        raise httpx.ConnectError(f"{OWNER_NAME} {_CFG.analyze_url}", request=request)

    with caplog.at_level(logging.DEBUG):
        res = await dm.analyze_deed(b"%PDF-1.4", timeout_s=5, config=_CFG,
                                    client_factory=_factory(handler))
        await dm.analyze_deed(b"%PDF-1.4", timeout_s=5, config=_CFG,
                              client_factory=_factory(lambda r: httpx.Response(503)))
    assert res.status == "failed"
    # 只看本模組的 logger（httpx 自己的 INFO 請求行是函式庫全域行為，另列回報）。
    blob = "\n".join(r.getMessage() for r in caplog.records if r.name == dm.__name__)
    assert "ConnectError" in blob and "503" in blob                     # 正對照：真的有記
    for secret in (OWNER_NAME, "documind.example.test", "tok123"):
        assert secret not in blob


def test_reencode_drops_exif_and_original_bytes():
    img = Image.new("RGB", (64, 48), (10, 20, 30))
    exif = Image.Exif()
    exif[0x010F] = "合成相機"                 # Make
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    original = buf.getvalue()
    assert b"Exif" in original                                          # 正對照：原檔真的有 EXIF
    out = dm.reencode_photo_jpeg(original)
    assert out != original and out.startswith(b"\xff\xd8\xff")
    assert b"Exif" not in out


# ════════════════════════════════════════════════════════════════════
# 取值：電子路徑、掃描路徑、多筆、不是謄本、形狀錯
# ════════════════════════════════════════════════════════════════════
def test_electronic_path_takes_the_six_fields_and_nothing_else():
    res = dm.extract_deed_fields(electronic_response())
    assert res.status == "ok" and res.typed_fields == EXPECTED_ELECTRONIC
    for secret in MUST_NOT_APPEAR:
        assert secret not in _blob(res)


def test_scanned_path_takes_only_confident_single_values():
    res = dm.extract_deed_fields(scanned_response())
    assert res.status == "ok"
    assert res.typed_fields == (("address", DOOR), ("use_for", "residential"), ("size", 68.47))
    keys = {k for k, _ in res.typed_fields}
    assert not keys & {"city", "district", "floor"}                     # D7：⛔ 取這三欄


def test_scanned_low_confidence_or_flagged_fields_are_dropped():
    low = scanned_response(field_confidences={"building_address": 0.84, "main_usage": 0.9,
                                              "total_area": 0.9})
    assert dict(dm.extract_deed_fields(low).typed_fields) == {"use_for": "residential", "size": 68.47}
    flagged = scanned_response(needs_confirmation=["total_area"])
    assert "size" not in dict(dm.extract_deed_fields(flagged).typed_fields)


def test_scanned_multi_transcript_or_multi_page_pdf_fills_nothing():
    multi = scanned_response(shared_parts=[{"transcript_id": "01234-000"},
                                           {"transcript_id": "05555-000"}])
    assert dm.extract_deed_fields(multi) == dm.DeedResult("ok", ())
    assert dm.extract_deed_fields(scanned_response(), pdf_pages=2) == dm.DeedResult("ok", ())
    assert dm.extract_deed_fields(scanned_response(), pdf_pages=1).typed_fields   # 正對照


def test_multiple_records_and_non_building_and_no_address():
    two = electronic_response()
    recs = two["document_fields"]["transcript_records"]
    recs.append(copy.deepcopy(recs[0]))
    assert dm.extract_deed_fields(two).status == "multiple"
    land = electronic_response()
    land["document_fields"]["transcript_records"][0]["類型"] = "土地"
    assert dm.extract_deed_fields(land).status == "not_deed"               # D9
    no_addr = scanned_response(building_address=None)
    assert dm.extract_deed_fields(no_addr).status == "not_deed"


@pytest.mark.parametrize("mutate", [
    lambda r: r.pop("document_fields"),
    lambda r: r["document_fields"].pop("transcript_records"),
    lambda r: r["document_fields"].__setitem__("transcript_records", "x"),
    lambda r: r["document_fields"]["transcript_records"].__setitem__(0, "x"),
    lambda r: r["document_fields"]["transcript_records"][0].__setitem__("標示部", "x"),
    lambda r: r["document_fields"]["transcript_records"][0].pop("謄本"),
])
def test_missing_keys_or_wrong_types_are_errors_not_scan_path(mutate):
    resp = electronic_response()
    mutate(resp)
    assert dm.extract_deed_fields(resp).status == "failed"
    assert dm.extract_deed_fields("not a dict").status == "failed"


def test_scanned_path_missing_list_key_is_an_error():
    resp = scanned_response()
    resp["document_fields"].pop("land_numbers")
    assert dm.extract_deed_fields(resp).status == "failed"


def test_city_district_must_match_the_closed_table():
    resp = electronic_response()
    resp["document_fields"]["transcript_records"][0]["謄本"]["行政區"] = "信義區"
    resp["document_fields"]["transcript_records"][0]["謄本"]["資料管轄機關"] = "新竹縣竹北地政事務所"
    d = dict(dm.extract_deed_fields(resp).typed_fields)
    assert "city" not in d and "district" not in d                     # 竹北 ∌ 信義區 ⇒ 兩者皆不填
    assert d["address"] == DOOR                                          # 其餘照常
    taipei = electronic_response()
    taipei["document_fields"]["transcript_records"][0]["謄本"]["資料管轄機關"] = "台北市大安地政事務所"
    assert dict(dm.extract_deed_fields(taipei).typed_fields)["city"] == "台北市"   # 台／臺同名
    assert len(dm.CITY_DISTRICTS) == 22
    assert sum(len(v) for v in dm.CITY_DISTRICTS.values()) == 368


# ════════════════════════════════════════════════════════════════════
# D7／D10：門牌形狀、去前綴、樓層、用途
# ════════════════════════════════════════════════════════════════════
def test_address_prefix_is_stripped_after_validation():
    assert dm.clean_address("臺北市大安區" + DOOR, "臺北市", "大安區") == DOOR
    assert dm.clean_address("台北市大安區" + DOOR, "臺北市", "大安區") == DOOR
    assert dm.clean_address(DOOR, "臺北市", "大安區") == DOOR             # 正對照


@pytest.mark.parametrize("bad", [
    DOOR + OWNER_NAME,                       # 附加姓名
    DOOR + OWNER_ID,                         # 附加證號
    DOOR + " " + OWNER_NAME,                 # 空白
    "建物門牌:" + DOOR,                       # 冒號＋標籤
    "合成路一段1號5樓  所有權人",               # 連續空白＋標籤
    OWNER_ADDR,                              # 別縣市地址（所有權人住址負對照）
    "合成路一段五樓",                          # 沒有門號
    "合成路一段1號\n5樓",                     # 換行（sanitize 會改動 ⇒ 拒）
])
def test_address_shape_rejects_appended_or_foreign_text(bad):
    assert dm.clean_address(bad, "臺北市", "大安區") is None


def test_floor_and_usage_are_exact():
    assert dm.floor_text("五層") == "5樓" and dm.floor_text("十二層") == "12樓"
    assert dm.floor_text("二十三層") == "23樓"
    for bad in ("5層", "五樓", "地下一層", "五層x", "騎樓", "十十層", None):
        assert dm.floor_text(bad) is None
    multi = electronic_response(層次=[{"層次": "一層", "面積": 1.0}, {"層次": "二層", "面積": 1.0}])
    assert "floor" not in dict(dm.extract_deed_fields(multi).typed_fields)
    near = electronic_response(主要用途="住家用 ")
    assert "use_for" not in dict(dm.extract_deed_fields(near).typed_fields)
    for usage, code in (("商業用", "business"), ("停車空間", "parking_space"), ("辦公室", "business")):
        assert dict(dm.extract_deed_fields(electronic_response(主要用途=usage)).typed_fields)["use_for"] == code


@pytest.mark.parametrize("area", [True, "68.47", 0, -1, 100001, None])
def test_size_type_and_range(area):
    assert "size" not in dict(dm.extract_deed_fields(electronic_response(總面積=area)).typed_fields)
