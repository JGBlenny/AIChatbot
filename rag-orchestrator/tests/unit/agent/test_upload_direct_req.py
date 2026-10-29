"""unit：瀏覽器直傳附件（UD-1，plan-upload-documind-20261028 §4 UD-1、§4.1「測試環境前」）。

全部離線：上傳端點走 ASGI transport（⛔ 真連線），辨識與擷取一律假的。真 `/mcp`
client 那一輪在 `tests/integration/agent/test_upload_direct_req.py`（A2）。

對照（每條「擋掉了」旁邊都放一個已知必過的正對照）：
  S1  服務層閘只對「路徑完全等於 `/api/v1/agent/uploads`、POST／OPTIONS」豁免；
      `GATED_PREFIXES` 不變；`/api/v1/agent/trace` 無金鑰仍 401（A1(b) 正對照）。
  S6  `upload_id` 綁 (api_key_id, vendor_id, user_id, role_id, session_id, purpose)。
  S7  缺 `user_id` 發票被拒。
  S8  票與 upload_id：CSPRNG 256 bit、只存雜湊、定時比較、⛔ 放網址；
      上傳路徑脫離全域 CORS（⛔ credentials）。Origin 兩種模式：
      ・開放模式（`AGENT_UPLOAD_ALLOWED_ORIGINS` 未設／空／只有 `*`，預設）——依業主
        2026-10-29 裁示「不需要擋」：不檢查 Origin，ACAO 一律 `*`，閘門只剩上傳票；
      ・白名單模式（有設）——沒帶 Origin 拒、預檢只回白名單 Origin（原 S8 行為，逐位元不變）。
      本檔 fixture 預設設白名單（www＋staging），原有 Origin 測試都是白名單模式。
  S11 丟棄瀏覽器檔名（回應與暫存都沒有檔名）。
  S12 workers≠1 ⇒ 直傳關閉（A1(g)）。
  S13 `AGENT_UPLOAD_ENDPOINT` 預設開；`AGENT_ATTACHMENT_INPUT` 非法值 ⇒ `upload_ids`（A3）。
  A1(a) jpg／png／webp／pdf 201；無票／過期 401、Origin 403、超大 413、型別 415、超量 429。
  A1(e) 白名單模式：`https://evil.example` 預檢無 ACAO；沒帶 Origin 被拒。
        （預設的開放模式不適用 A1(e)，業主 2026-10-29 裁示取消。）
  A3  預設模式 `image_urls`／`file_urls` ⇒ `INVALID_INPUT`；切 `urls` 恢復舊行為。
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import os
import re
from io import BytesIO

import httpx
import pytest
from PIL import Image

from routers import agent as agent_router
from routers import agent_uploads
from services.agent import image_fetch
from services.agent import mcp_facade as F
from services.agent import upload_store as US
from services.agent.identity import Identity
from services.agent.tools.registry import ToolRegistry, ToolResult

from tests.unit.agent.test_document_turn_req import (
    FakeExtractor,
    _bill_result,
    _synth_pdf,
    _turn_deps,
)
from tests.unit.agent.test_image_entry_req import FakeFetcher, FakeRecognizer, _recognition

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:UD-1"

ALLOWED = "https://www.jgbsmart.com"
ALLOWED_STAGING = "https://staging.jgbsmart.com"
EVIL = "https://evil.example"
PUBLIC_URL = "https://chatai.jgbsmart.com/rag-api/v1/agent/uploads"

API_KEY_ID = 7
VENDOR = 1
SESSION = "backtest_upload_ud1"


# ═══════════════════════════════════════════════════════════════════
# 素材
# ═══════════════════════════════════════════════════════════════════
def _img(fmt: str, size=(64, 48)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (120, 140, 160)).save(buf, format=fmt)
    return buf.getvalue()


def _webp() -> bytes:
    try:
        return _img("WEBP")
    except Exception:  # noqa: BLE001 — PIL 未編進 webp 時退回最小 RIFF 容器
        return b"RIFF" + (20).to_bytes(4, "little") + b"WEBPVP8 " + b"\x00" * 12


def _identity(**over) -> Identity:
    base = dict(vendor_id=VENDOR, target_user="prospect", mode="b2c",
                api_key_id=API_KEY_ID, session_id=SESSION, role_id="20151",
                user_id="88", entry="mcp")
    base.update(over)
    return Identity(**base)


def _binding(purpose="repair", **over) -> US.UploadBinding:
    return US.binding_from_identity(F.namespaced_identity(_identity(**over)), purpose)


def _ticket(purpose="repair", **over) -> str:
    return US.STORE.issue_ticket(_binding(purpose, **over)).upload_token


class Clock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, dt):
        self.now += dt


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    US.STORE.reset()
    clock = Clock()
    US.STORE.set_clock(clock, wall=lambda: 1_793_184_400.0 + clock.now)
    image_fetch.reset_image_count_cap()
    image_fetch.reset_file_count_cap()
    image_fetch.reset_image_failures()
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", F.EMPTY_ORIGIN_SET)
    monkeypatch.setenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, f"{ALLOWED},{ALLOWED_STAGING}")
    monkeypatch.setenv(US.UPLOAD_PUBLIC_URL_ENV, PUBLIC_URL)
    monkeypatch.delenv(US.ATTACHMENT_INPUT_ENV, raising=False)
    monkeypatch.delenv(US.ATTACHMENT_ENDPOINT_ENV, raising=False)
    yield clock
    US.STORE.reset()
    US.STORE.set_clock(__import__("time").monotonic, wall=__import__("time").time)
    image_fetch.reset_image_count_cap()
    image_fetch.reset_file_count_cap()
    image_fetch.reset_image_failures()


# ═══════════════════════════════════════════════════════════════════
# 受測 HTTP app：app.py 的真 CORS 子類＋真服務層閘＋真上傳路由＋真 agent 路由
# ═══════════════════════════════════════════════════════════════════
def _import_app(monkeypatch):
    """匯入真 `app.py`。⚠️ 匯入時 `routers.document_converter` 會建 OpenAI provider，
    缺 `OPENAI_API_KEY` 就 raise——給一個**假字串**（不是憑證，離線不會被拿去連線）。"""
    if not os.getenv("OPENAI_API_KEY"):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test-placeholder-not-a-key")
    import app as app_mod

    return app_mod


def _http_app(monkeypatch, *, exempt=True):
    app_mod = _import_app(monkeypatch)   # 真 `_CorsExceptUpload`（⛔ 在測試裡另寫一份）
    from fastapi import FastAPI

    monkeypatch.setattr(app_mod, "_UPLOAD_ENABLED", exempt)
    a = FastAPI()
    a.add_middleware(app_mod._CorsExceptUpload, allow_origins=["*"], allow_credentials=True,
                     allow_methods=["*"], allow_headers=["*"])
    a.add_middleware(F.McpServiceGate, get_pool=lambda: None, exempt_upload=exempt)
    if exempt:
        a.include_router(agent_uploads.router)
    a.include_router(agent_router.router)
    return a


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _post(client, token, data, *, filename="photo.jpg", ctype="image/jpeg",
                origin=ALLOWED, extra_headers=None):
    headers = {}
    if origin is not None:
        headers["Origin"] = origin
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(extra_headers or {})
    return await client.post(US.UPLOAD_PATH, headers=headers,
                             files={"file": (filename, data, ctype)})


# ═══════════════════════════════════════════════════════════════════
# S8：票與 upload_id 的形狀、熵、只存雜湊、定時比較、⛔ 放網址
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_tokens_are_256_bit_csprng_and_only_hashes_are_stored():
    issued = US.STORE.issue_ticket(_binding())
    tok = issued.upload_token
    m = re.fullmatch(r"upt_([0-9a-f]{16})\.([A-Za-z0-9_-]{43})", tok)
    assert m, "票的形狀不是 upt_<16 hex>.<43 字 base64url>"
    selector, verifier = m.groups()
    # 43 字 base64url（無 padding）＝ 32 bytes ＝ 256 bit
    import base64
    assert len(base64.urlsafe_b64decode(verifier + "=")) == 32
    rec = US.STORE._tickets[selector]
    assert rec.digest == hashlib.sha256(verifier.encode()).digest()
    # 伺服端紀錄裡找不到驗證段原字串（只存雜湊）
    assert verifier not in repr(US.STORE._tickets)
    assert verifier.encode() not in repr(vars(rec)).encode()
    # 兩次發票不同（正對照：同一綁定）
    assert US.STORE.issue_ticket(_binding()).upload_token != tok

    up = US.STORE.add_upload(US.STORE.verify_ticket(tok), content_type="image/jpeg",
                             data=_img("JPEG"))
    m2 = re.fullmatch(r"upl_([0-9a-f]{16})\.([A-Za-z0-9_-]{43})", up.upload_id)
    assert m2
    urec = US.STORE._uploads[m2.group(1)]
    assert urec.digest == hashlib.sha256(m2.group(2).encode()).digest()
    assert m2.group(2) not in repr(US.STORE._uploads)
    assert "data=" not in repr(urec), "位元組不得出現在 repr（log／trace 的出口）"


@pytest.mark.req(_REQ)
def test_compare_is_constant_time_and_rng_is_secrets():
    """原始碼層：比對一律 `hmac.compare_digest`，亂數一律 `secrets`；⛔ `random`、⛔ `==` 比 digest。"""
    src = inspect.getsource(US)
    tree = ast.parse(src)
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert "secrets" in imported and "hmac" in imported
    assert "random" not in imported
    assert src.count("hmac.compare_digest(") >= 2      # 票、upload_id 各一處
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and any(isinstance(o, (ast.Eq, ast.NotEq)) for o in node.ops):
            text = ast.get_source_segment(src, node) or ""
            assert "digest" not in text, f"digest 以 == 比較：{text}"


@pytest.mark.req(_REQ)
async def test_token_is_only_read_from_authorization_header(monkeypatch):
    """S8 ⛔ 放網址：票放在 query string ⇒ 401；`upload_url` 不含票。正對照：標頭帶 ⇒ 201。"""
    issued = US.STORE.issue_ticket(_binding())
    assert issued.upload_token not in US.public_upload_url()
    async with _client(_http_app(monkeypatch)) as c:
        r = await c.post(f"{US.UPLOAD_PATH}?upload_token={issued.upload_token}",
                         headers={"Origin": ALLOWED},
                         files={"file": ("a.jpg", _img("JPEG"), "image/jpeg")})
        assert r.status_code == 401 and r.json()["error_code"] == "UPLOAD_TOKEN_INVALID"
        ok = await _post(c, issued.upload_token, _img("JPEG"))
        assert ok.status_code == 201


# ═══════════════════════════════════════════════════════════════════
# A1(a)：四種型別成功；回應形狀；S11 丟棄檔名
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
@pytest.mark.parametrize("purpose,data,expected", [
    ("repair", "jpeg", "image/jpeg"),
    ("repair", "png", "image/png"),
    ("repair", "webp", "image/webp"),
    ("document", "pdf", "application/pdf"),
    ("document", "jpeg", "image/jpeg"),
    ("document", "png", "image/png"),
])
async def test_accepted_types_return_201_with_upload_id(purpose, data, expected, monkeypatch):
    raw = {"jpeg": lambda: _img("JPEG"), "png": lambda: _img("PNG"),
           "webp": _webp, "pdf": lambda: _synth_pdf(pages=1)}[data]()
    async with _client(_http_app(monkeypatch)) as c:
        r = await _post(c, _ticket(purpose), raw, filename="秘密檔名-身分證.bin",
                        ctype="application/octet-stream")
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"upload_id", "content_type", "size", "sha256"}
    assert body["upload_id"].startswith("upl_")
    assert body["content_type"] == expected
    assert body["size"] == len(raw)
    assert body["sha256"] == hashlib.sha256(raw).hexdigest()
    assert r.headers["access-control-allow-origin"] == ALLOWED
    # S11：瀏覽器檔名丟棄——回應、暫存紀錄都沒有
    assert "秘密檔名" not in r.text
    assert "秘密檔名" not in repr(US.STORE._uploads)


# ═══════════════════════════════════════════════════════════════════
# A1(a)：錯誤碼
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_missing_or_bad_ticket_is_401_invalid(monkeypatch):
    async with _client(_http_app(monkeypatch)) as c:
        for token in (None, "", "garbage", "upt_" + "0" * 16 + "." + "A" * 43,
                      "upl_" + "0" * 16 + "." + "A" * 43, "x" * 500):
            r = await _post(c, token, _img("JPEG"))
            assert r.status_code == 401, token
            assert r.json() == {"error_code": "UPLOAD_TOKEN_INVALID",
                                "message": agent_uploads._MESSAGES["UPLOAD_TOKEN_INVALID"]}
        # 驗證段被改一個字 ⇒ 仍是 INVALID
        good = _ticket()
        tampered = good[:-1] + ("A" if good[-1] != "A" else "B")
        r = await _post(c, tampered, _img("JPEG"))
        assert r.status_code == 401 and r.json()["error_code"] == "UPLOAD_TOKEN_INVALID"
        # 正對照：原票 201
        assert (await _post(c, good, _img("JPEG"))).status_code == 201


@pytest.mark.req(_REQ)
async def test_expired_ticket_is_401_expired(monkeypatch, _clean):
    clock = _clean
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        clock.advance(599)
        assert (await _post(c, tok, _img("JPEG"))).status_code == 201   # 正對照：10 分鐘內
        clock.advance(2)
        r = await _post(c, tok, _img("JPEG"))
        assert r.status_code == 401 and r.json()["error_code"] == "UPLOAD_TOKEN_EXPIRED"


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("origin", [
    EVIL, "https://jgbsmart.com", "http://www.jgbsmart.com", "https://www.jgbsmart.com.evil.example",
    "null", "*", None,
])
async def test_origin_not_in_list_or_missing_is_403_without_acao(origin, monkeypatch):
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        r = await _post(c, tok, _img("JPEG"), origin=origin)
        assert r.status_code == 403
        assert r.json()["error_code"] == "ORIGIN_NOT_ALLOWED"
        assert "access-control-allow-origin" not in r.headers
        # 正對照：兩個白名單 Origin 都放行
        assert (await _post(c, tok, _img("JPEG"), origin=ALLOWED)).status_code == 201
        assert (await _post(c, tok, _img("JPEG"), origin=ALLOWED_STAGING)).status_code == 201


# ── 開放模式（預設）：依業主 2026-10-29 裁示「不需要擋」，取消 S8 的 Origin 白名單與 A1(e) 預設 ──
def _set_open_mode(monkeypatch, raw):
    if raw is None:
        monkeypatch.delenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, raising=False)
    else:
        monkeypatch.setenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, raw)
    assert US.load_upload_allowed_origins() == frozenset()


_OPEN_MODE_ENVS = [None, "", "*", " * , ,"]   # 未設、空值、只有 `*`（去掉 `*` 後空集合）


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("raw", _OPEN_MODE_ENVS)
async def test_owner_ruling_20261029_unset_allowlist_is_open_mode_not_reject_all(raw, monkeypatch):
    """原「預設空就全拒」改為開放模式（業主 2026-10-29 裁示）：任何 Origin、沒帶 Origin，
    只要上傳票有效就 201，ACAO `*`、⛔ credentials。正對照：無效票仍 401（閘門只剩票）。"""
    _set_open_mode(monkeypatch, raw)
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        for origin in (EVIL, ALLOWED, "null", None):
            r = await _post(c, tok, _img("JPEG"), origin=origin)
            assert r.status_code == 201, (origin, r.text)
            assert r.headers["access-control-allow-origin"] == "*"
            assert "access-control-allow-credentials" not in r.headers
        # 無效票：401，錯誤回應同樣帶 ACAO `*`
        for origin in (EVIL, None):
            bad = await _post(c, "garbage", _img("JPEG"), origin=origin)
            assert bad.status_code == 401 and bad.json()["error_code"] == "UPLOAD_TOKEN_INVALID"
            assert bad.headers["access-control-allow-origin"] == "*"
            assert "access-control-allow-credentials" not in bad.headers
            none = await _post(c, None, _img("JPEG"), origin=origin)
            assert none.status_code == 401 and none.json()["error_code"] == "UPLOAD_TOKEN_INVALID"
            assert none.headers["access-control-allow-origin"] == "*"
    assert US.STORE.counts()["uploads"] == 4, "只有四張有效票的上傳進暫存"


@pytest.mark.req(_REQ)
async def test_owner_ruling_20261029_open_mode_preflight_from_evil_gets_star(monkeypatch):
    """開放模式預檢：`https://evil.example`（與沒帶 Origin）回 204＋ACAO `*`；
    Allow-Methods／Allow-Headers／Max-Age 照現行；⛔ credentials。"""
    _set_open_mode(monkeypatch, None)
    async with _client(_http_app(monkeypatch)) as c:
        for headers in ({"Origin": EVIL, "Access-Control-Request-Method": "POST",
                         "Access-Control-Request-Headers": "authorization"},
                        {"Access-Control-Request-Method": "POST"}):
            r = await c.options(US.UPLOAD_PATH, headers=headers)
            assert r.status_code == 204, headers
            assert r.headers["access-control-allow-origin"] == "*"
            assert r.headers["access-control-allow-methods"] == "POST"
            assert r.headers["access-control-allow-headers"] == "Authorization, Content-Type"
            assert r.headers["access-control-max-age"] == agent_uploads._PREFLIGHT_MAX_AGE_S
            assert "access-control-allow-credentials" not in r.headers


@pytest.mark.req(_REQ)
async def test_owner_ruling_20261029_open_mode_other_checks_unchanged_and_errors_carry_star(
        monkeypatch):
    """開放模式只拿掉 Origin 檢查：413／415／400／429 照舊，錯誤回應都帶 ACAO `*`、⛔ credentials。"""
    _set_open_mode(monkeypatch, None)
    big = b"\xff\xd8\xff" + b"\x00" * (5_000_000 - 3 + 1)
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        cases = [
            (await _post(c, tok, big, origin=EVIL), 413, "FILE_TOO_LARGE"),
            (await _post(c, tok, b"hello, not an image", origin=EVIL), 415, "UNSUPPORTED_FILE_TYPE"),
            (await c.post(US.UPLOAD_PATH, headers={"Authorization": f"Bearer {tok}",
                                                   "Content-Type": "image/jpeg"},
                          content=_img("JPEG")), 400, "UPLOAD_MALFORMED"),
        ]
        doc = _ticket("document")
        assert (await _post(c, doc, _synth_pdf(pages=1), origin=None)).status_code == 201
        cases.append((await _post(c, doc, _synth_pdf(pages=1), origin=None), 429,
                      "UPLOAD_LIMIT_REACHED"))
        for r, status, code in cases:
            assert r.status_code == status and r.json()["error_code"] == code, (status, r.text)
            assert r.headers["access-control-allow-origin"] == "*"
            assert "access-control-allow-credentials" not in r.headers
    assert US.STORE.counts()["uploads"] == 1


@pytest.mark.req(_REQ)
async def test_staging_only_allowlist_keeps_whitelist_mode(monkeypatch):
    """白名單模式（env 只設 staging）：A1(e) 照舊——evil 與沒帶 Origin 都 403 且無 ACAO，
    預檢 evil 403；正對照：staging 201、預檢回 staging＋`Vary: Origin`。"""
    monkeypatch.setenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, ALLOWED_STAGING)
    assert US.load_upload_allowed_origins() == frozenset({ALLOWED_STAGING})
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        for origin in (EVIL, ALLOWED, None):
            r = await _post(c, tok, _img("JPEG"), origin=origin)
            assert r.status_code == 403 and r.json()["error_code"] == "ORIGIN_NOT_ALLOWED", origin
            assert "access-control-allow-origin" not in r.headers
        pre = await c.options(US.UPLOAD_PATH, headers={"Origin": EVIL,
                                                       "Access-Control-Request-Method": "POST"})
        assert pre.status_code == 403 and "access-control-allow-origin" not in pre.headers
        ok = await _post(c, tok, _img("JPEG"), origin=ALLOWED_STAGING)
        assert ok.status_code == 201
        assert ok.headers["access-control-allow-origin"] == ALLOWED_STAGING
        assert ok.headers["vary"] == "Origin"
        pre_ok = await c.options(US.UPLOAD_PATH, headers={
            "Origin": ALLOWED_STAGING, "Access-Control-Request-Method": "POST"})
        assert pre_ok.status_code == 204
        assert pre_ok.headers["access-control-allow-origin"] == ALLOWED_STAGING
        assert "access-control-allow-credentials" not in pre_ok.headers


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("raw,expected", [
    (None, "Origin 不檢查（開放"), ("", "Origin 不檢查（開放"), ("*", "Origin 不檢查（開放"),
    (ALLOWED_STAGING, "Origin 白名單 1 個"), (f"{ALLOWED},{ALLOWED_STAGING},*", "Origin 白名單 2 個"),
])
def test_startup_label_distinguishes_open_and_whitelist_mode(raw, expected, monkeypatch):
    if raw is None:
        monkeypatch.delenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, raising=False)
    else:
        monkeypatch.setenv(US.UPLOAD_ALLOWED_ORIGINS_ENV, raw)
    label = agent_uploads.origin_policy_label()
    assert label.startswith(expected), label
    assert ALLOWED not in label and ALLOWED_STAGING not in label, "⛔ 印名單內容"
    src = open(_import_app(monkeypatch).__file__, encoding="utf-8").read()
    assert "agent_uploads_router.origin_policy_label()" in src


@pytest.mark.req(_REQ)
async def test_too_large_is_413(monkeypatch):
    big = b"\xff\xd8\xff" + b"\x00" * (5_000_000 - 3 + 1)      # 5,000,001 bytes
    edge = b"\xff\xd8\xff" + b"\x00" * (5_000_000 - 3)          # 恰 5,000,000 bytes
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        r = await _post(c, tok, big)
        assert r.status_code == 413 and r.json()["error_code"] == "FILE_TOO_LARGE"
        # 宣告長度過大 ⇒ 不讀 body 直接 413
        r2 = await c.post(US.UPLOAD_PATH, headers={
            "Origin": ALLOWED, "Authorization": f"Bearer {tok}",
            "Content-Type": "multipart/form-data; boundary=x",
            "Content-Length": "99999999"}, content=b"")
        assert r2.status_code == 413 and r2.json()["error_code"] == "FILE_TOO_LARGE"
        # 正對照：恰好上限 ⇒ 201
        ok = await _post(c, tok, edge)
        assert ok.status_code == 201 and ok.json()["size"] == 5_000_000


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("purpose,payload,filename,ctype", [
    ("repair", b"hello, not an image", "photo.jpg", "image/jpeg"),     # 副檔名＋Content-Type 都說 jpg
    ("repair", b"GIF89a....", "photo.png", "image/png"),               # GIF 不在 accept
    ("repair", None, "photo.jpg", "image/jpeg"),                       # PDF 冒充照片（修繕不收 PDF）
    ("document", b"<html>pdf</html>", "doc.pdf", "application/pdf"),   # 冒充 PDF
    ("document", None, "doc.webp", "image/webp"),                      # webp 不在 document 的 accept
])
async def test_content_type_is_sniffed_and_extension_cannot_fool_it(
        purpose, payload, filename, ctype, monkeypatch):
    if payload is None:
        payload = _synth_pdf(pages=1) if purpose == "repair" else _webp()
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket(purpose)
        r = await _post(c, tok, payload, filename=filename, ctype=ctype)
        assert r.status_code == 415 and r.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"
        # 正對照：同一張票送真檔 ⇒ 201
        real = _img("JPEG")
        assert (await _post(c, tok, real)).status_code == 201
    assert US.STORE.counts()["uploads"] == 1, "被 415 的檔不得進暫存"


@pytest.mark.req(_REQ)
async def test_over_max_files_is_429(monkeypatch):
    async with _client(_http_app(monkeypatch)) as c:
        doc = _ticket("document")
        assert (await _post(c, doc, _synth_pdf(pages=1))).status_code == 201
        r = await _post(c, doc, _synth_pdf(pages=1))
        assert r.status_code == 429 and r.json()["error_code"] == "UPLOAD_LIMIT_REACHED"

        rep = _ticket("repair")
        for i in range(10):
            assert (await _post(c, rep, _img("JPEG"))).status_code == 201, i
        r = await _post(c, rep, _img("JPEG"))
        assert r.status_code == 429 and r.json()["error_code"] == "UPLOAD_LIMIT_REACHED"
    assert US.STORE.counts()["uploads"] == 11


@pytest.mark.req(_REQ)
async def test_malformed_multipart_is_rejected_and_not_stored(monkeypatch):
    async with _client(_http_app(monkeypatch)) as c:
        tok = _ticket()
        hdr = {"Origin": ALLOWED, "Authorization": f"Bearer {tok}"}
        # 不是 multipart
        r = await c.post(US.UPLOAD_PATH, headers={**hdr, "Content-Type": "image/jpeg"},
                         content=_img("JPEG"))
        assert r.status_code == 400 and r.json()["error_code"] == "UPLOAD_MALFORMED"
        # 欄位名不是 file
        r = await c.post(US.UPLOAD_PATH, headers=hdr,
                         files={"photo": ("a.jpg", _img("JPEG"), "image/jpeg")})
        assert r.status_code == 400
        # 兩個檔
        r = await c.post(US.UPLOAD_PATH, headers=hdr, files=[
            ("file", ("a.jpg", _img("JPEG"), "image/jpeg")),
            ("file", ("b.jpg", _img("JPEG"), "image/jpeg"))])
        assert r.status_code == 400
    assert US.STORE.counts()["uploads"] == 0


# ═══════════════════════════════════════════════════════════════════
# A1(e)／S8：預檢與 CORS
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_preflight_from_allowed_origin_echoes_it_without_credentials(monkeypatch):
    async with _client(_http_app(monkeypatch)) as c:
        r = await c.options(US.UPLOAD_PATH, headers={
            "Origin": ALLOWED, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization"})
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == ALLOWED
    assert "POST" in r.headers["access-control-allow-methods"]
    assert "authorization" in r.headers["access-control-allow-headers"].lower()
    assert r.headers["vary"] == "Origin"
    assert "access-control-allow-credentials" not in r.headers


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("origin", [EVIL, "https://jgbsmart.com", None])
async def test_preflight_from_other_origin_has_no_acao(origin, monkeypatch):
    headers = {"Access-Control-Request-Method": "POST"}
    if origin:
        headers["Origin"] = origin
    async with _client(_http_app(monkeypatch)) as c:
        r = await c.options(US.UPLOAD_PATH, headers=headers)
        assert "access-control-allow-origin" not in r.headers
        assert "access-control-allow-credentials" not in r.headers
        assert r.status_code == 403 and r.json()["error_code"] == "ORIGIN_NOT_ALLOWED"
        # 對照：全域 CORS 對其他路徑仍照舊（證明旁路只有上傳路徑）
        r2 = await c.options("/somewhere-else", headers={
            "Origin": EVIL, "Access-Control-Request-Method": "GET"})
        assert r2.headers.get("access-control-allow-origin") == EVIL


# ═══════════════════════════════════════════════════════════════════
# S1：服務層閘只對「完全等於、POST／OPTIONS」豁免；A1(b) 正對照
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_gated_prefixes_unchanged_and_predicate_is_exact():
    assert F.GATED_PREFIXES == ("/mcp", "/api/v1/agent")
    ok = {"type": "http", "path": "/api/v1/agent/uploads", "method": "POST"}
    assert F.is_upload_request(ok)
    assert F.is_upload_request(dict(ok, method="OPTIONS"))
    for bad in (
        dict(ok, method="GET"), dict(ok, method="PUT"), dict(ok, method="DELETE"),
        dict(ok, path="/api/v1/agent/uploads/"), dict(ok, path="/api/v1/agent/uploads/x"),
        dict(ok, path="/api/v1/agent/uploadsx"), dict(ok, path="/api/v1/agent/trace"),
        dict(ok, path="/api/v1/agent/"), dict(ok, path="/mcp"),
        dict(ok, type="websocket"),
    ):
        assert not F.is_upload_request(bad), bad


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/v1/agent/trace"),             # A1(b) 正對照：同前綴的 trace 仍 401
    ("GET", "/api/v1/agent/trace/abc"),
    ("GET", "/api/v1/agent/health"),
    ("GET", "/api/v1/agent/uploads"),
    ("PUT", "/api/v1/agent/uploads"),
    ("POST", "/api/v1/agent/uploads/"),
    ("POST", "/api/v1/agent/uploads/x"),
    ("POST", "/api/v1/agent/uploadsx"),
    ("OPTIONS", "/api/v1/agent/trace"),
    ("POST", "/mcp"),
])
async def test_everything_else_under_the_prefix_is_still_gated(method, path, monkeypatch):
    async with _client(_http_app(monkeypatch)) as c:
        r = await c.request(method, path)
        assert r.status_code == 401, (method, path, r.status_code)
        assert r.json()["code"] == "API_KEY_REQUIRED"
        # 正對照：豁免路徑本身不回 API_KEY_REQUIRED（走上傳路由自己的檢查）
        r2 = await _post(c, None, _img("JPEG"))
        assert r2.status_code == 401 and r2.json()["error_code"] == "UPLOAD_TOKEN_INVALID"


@pytest.mark.req(_REQ)
async def test_without_exempt_flag_the_upload_path_is_gated(monkeypatch):
    async with _client(_http_app(monkeypatch, exempt=False)) as c:
        r = await _post(c, _ticket(), _img("JPEG"))
    assert r.status_code == 401 and r.json()["code"] == "API_KEY_REQUIRED"


@pytest.mark.req(_REQ)
def test_api_key_guard_and_cors_use_the_same_exact_predicate():
    """app.py 原始碼層：api_key_guard 與 CORS 旁路都呼叫 `is_upload_request`，
    `api_key_auth._EXEMPT_PREFIX`／`_EXEMPT_EXACT` 未加上傳路徑（⛔ 前綴豁免）。"""
    from services import api_key_auth

    src = open(os.path.join(os.path.dirname(F.__file__), "..", "..", "app.py"),
               encoding="utf-8").read()
    guard = src[src.index("async def api_key_guard"):]
    guard = guard[:guard.index("return await call_next(request)\n\n")]
    assert "is_upload_request(request.scope)" in guard
    assert "is_upload_request(scope)" in src[src.index("class _CorsExceptUpload"):]
    assert "exempt_upload=_UPLOAD_ENABLED" in src
    assert not any("upload" in p for p in api_key_auth._EXEMPT_PREFIX)
    assert not any("upload" in p for p in api_key_auth._EXEMPT_EXACT)


@pytest.mark.req(_REQ)
def test_invariant_28_still_green():
    """A1(b)：不變量 28 AST 檢查（`_EXEMPT_PREFIX` 不含 /mcp；facade 不讀 enforce 旗）。"""
    import importlib.util
    import sys

    path = os.path.join(os.path.dirname(F.__file__), "..", "..", "..",
                        "scripts", "audit", "checks", "agent_boundary.py")
    if not os.path.exists(path):
        path = "/scripts/audit/checks/agent_boundary.py"
    spec = importlib.util.spec_from_file_location("_agent_boundary_ud1", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_agent_boundary_ud1"] = mod
    spec.loader.exec_module(mod)
    result = mod.check_28_mcp_auth_unconditional()
    ok, msg = result                      # 檢查函式回 `(bool, 說明)`
    assert ok is True, f"不變量 28 轉紅：{msg}"
    # 新檔也不得出現 enforce 旗（上傳路由不依賴 RAG_API_AUTH_ENFORCE）
    for f in (agent_uploads.__file__, US.__file__):
        assert "auth_enforced" not in open(f, encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════════════
# S6／S7：綁定、缺 user_id、單次使用、30 分鐘
# ═══════════════════════════════════════════════════════════════════
def _upload(purpose="repair", data=None, **over) -> str:
    tok = _ticket(purpose, **over)
    if data is None:
        data = _synth_pdf(pages=1) if purpose == "document" else _img("JPEG")
    ct = US.sniff_content_type(data)
    return US.STORE.add_upload(US.STORE.verify_ticket(tok), content_type=ct, data=data).upload_id


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("field,value", [
    ("api_key_id", 8), ("vendor_id", 2), ("user_id", "89"), ("role_id", "20152"),
    ("session_id", SESSION + "x"),
])
def test_upload_id_is_bound_to_every_identity_field(field, value):
    uid = _upload()
    with pytest.raises(US.UploadRefError) as exc:
        US.STORE.check([uid], _binding(**{field: value}))
    assert exc.value.index == 0
    # 正對照：同一身分過得去（且 check 不消耗）
    assert US.STORE.check([uid], _binding()) == ["image/jpeg"]


@pytest.mark.req(_REQ)
def test_upload_id_is_bound_to_purpose_single_use_and_30_minutes(_clean):
    clock = _clean
    uid = _upload("repair")
    with pytest.raises(US.UploadRefError):
        US.STORE.check([uid], _binding("document"))
    assert len(US.STORE.claim([uid], _binding())) == 1
    with pytest.raises(US.UploadRefError):
        US.STORE.claim([uid], _binding())          # 第二次 ⇒ 無效
    late = _upload("repair")
    clock.advance(1799)
    US.STORE.check([late], _binding())             # 正對照：30 分鐘內
    clock.advance(2)
    with pytest.raises(US.UploadRefError):
        US.STORE.check([late], _binding())
    assert US.STORE.counts()[US.STATE_UNREFERENCED] == 0, "過期的未引用上傳應已刪除"


@pytest.mark.req(_REQ)
def test_missing_user_id_cannot_get_a_binding():
    for uid in (None, "", "   "):
        with pytest.raises(US.UploadBindingError):
            US.binding_from_identity(F.namespaced_identity(_identity(user_id=uid)), "repair")
    assert US.binding_from_identity(F.namespaced_identity(_identity()), "repair").user_id == "88"


def _ticket_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(F.UPLOAD_TICKET_SPEC, F._make_upload_ticket())
    return reg


@pytest.mark.req(_REQ)
async def test_upload_ticket_tool_shape_and_s7():
    reg = _ticket_registry()
    ident = F.namespaced_identity(_identity())
    r = await reg.call(ident, F.UPLOAD_TICKET_NAME, {"attachment_purpose": "repair"}, 5.0,
                       stage="M1")
    assert r.ok, r
    assert set(r.data) == {"upload_url", "upload_token", "expires_at", "max_files",
                           "max_bytes", "accept"}
    assert r.data["max_files"] == 10 and r.data["max_bytes"] == 5_000_000
    assert r.data["accept"] == ["image/jpeg", "image/png", "image/webp"]
    assert r.data["upload_url"] == PUBLIC_URL      # env 原字
    assert r.data["upload_token"] not in r.data["upload_url"]
    assert r.data["expires_at"] == int(1_793_184_400.0 + 1000.0 + 600)
    d = await reg.call(ident, F.UPLOAD_TICKET_NAME, {"attachment_purpose": "document"}, 5.0,
                       stage="M1")
    assert d.data["max_files"] == 1
    assert d.data["accept"] == ["application/pdf", "image/jpeg", "image/png"]
    # S7：缺 user_id ⇒ INVALID_INPUT（附固定說明）
    no_user = F.namespaced_identity(_identity(user_id=None))
    bad = await reg.call(no_user, F.UPLOAD_TICKET_NAME, {"attachment_purpose": "repair"}, 5.0,
                         stage="M1")
    assert bad.ok is False and bad.error == "INVALID_INPUT"
    assert F._input_detail(bad) == F.USER_ID_REQUIRED_DETAIL
    # enum 擋非法用途；tenant 看不到這支工具
    assert (await reg.call(ident, F.UPLOAD_TICKET_NAME, {"attachment_purpose": "x"}, 5.0,
                           stage="M1")).error == "INVALID_INPUT"
    tenant = F.namespaced_identity(_identity(target_user="tenant"))
    assert (await reg.call(tenant, F.UPLOAD_TICKET_NAME, {"attachment_purpose": "repair"},
                           5.0, stage="M1")).error == "NO_MATCH"
    # 模型看不到（facade_only）
    assert F.UPLOAD_TICKET_NAME not in {
        s["name"] for s in reg.specs_for(ident, "M1", for_model=True)}


_BAD_PUBLIC_URLS = [
    (None, "未設"),
    ("", "未設"),
    ("http://chatai.jgbsmart.com/rag-api/v1/agent/uploads", "不是 https://"),
    ("/rag-api/v1/agent/uploads", "不是 https://"),                       # 舊預設：相對路徑
    ("HTTPS://chatai.jgbsmart.com/rag-api/v1/agent/uploads", "不是 https://"),
    ("https://chatai.jgbsmart.com/rag-api/v1/agent/upload", "路徑不以"),
    ("https://chatai.jgbsmart.com/api/v1/agent/uploads", "路徑不以"),        # 後端路徑、少 /rag-api
    ("https://chatai.jgbsmart.com/rag-api/v1/agent/uploads/", "路徑不以"),
    ("https://chatai.jgbsmart.com/rag-api/v1/agent/uploads?x=1", "路徑不以"),
    ("https:///rag-api/v1/agent/uploads", "沒有主機名"),
    (" https://chatai.jgbsmart.com/rag-api/v1/agent/uploads", "含空白"),
    ("https://chatai.jgbsmart.com/rag-api/v1/agent/uploads\n", "含空白"),
]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("raw,why", _BAD_PUBLIC_URLS)
def test_bad_public_upload_url_disables_direct_upload(raw, why, monkeypatch):
    """偏離 4 處置：`AGENT_UPLOAD_PUBLIC_URL` 未設／非 https 絕對網址／路徑不對 ⇒
    直傳關閉（同一個 `upload_endpoint_status`），⛔ 退回相對路徑。正對照：workers=1。"""
    monkeypatch.setenv("UVICORN_WORKERS", "1")
    monkeypatch.delenv("UVICORN_RELOAD", raising=False)
    monkeypatch.delenv(US.ATTACHMENT_ENDPOINT_ENV, raising=False)
    if raw is None:
        monkeypatch.delenv(US.UPLOAD_PUBLIC_URL_ENV, raising=False)
    else:
        monkeypatch.setenv(US.UPLOAD_PUBLIC_URL_ENV, raw)
    enabled, reason = US.upload_endpoint_status()
    assert enabled is False
    assert US.UPLOAD_PUBLIC_URL_ENV in reason and why in reason, reason
    if raw:
        assert raw.strip() not in reason, "⛔ 在啟動輸出回顯設定值"
    with pytest.raises(RuntimeError):
        US.public_upload_url()
    # 路由同一個判斷：上傳票工具不註冊
    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None))
    assert F.UPLOAD_TICKET_NAME not in reg._specs
    assert F.AGENT_TURN_NAME in reg._specs              # 正對照：同一個 registry 有 agent.turn


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("raw", [
    PUBLIC_URL,
    "https://chatai.jgbsmart.com:8443/rag-api/v1/agent/uploads",
    "https://example.test/prefix/rag-api/v1/agent/uploads",
])
def test_good_public_upload_url_enables_and_is_returned_verbatim(raw, monkeypatch):
    monkeypatch.setenv("UVICORN_WORKERS", "1")
    monkeypatch.delenv("UVICORN_RELOAD", raising=False)
    monkeypatch.setenv(US.UPLOAD_PUBLIC_URL_ENV, raw)
    assert US.upload_endpoint_status() == (True, "")
    assert US.public_upload_url() == raw
    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None))
    assert F.UPLOAD_TICKET_NAME in reg._specs


@pytest.mark.req(_REQ)
def test_input_detail_only_passes_program_built_shapes():
    good = ToolResult(ok=False, error="INVALID_INPUT",
                      data={F.INPUT_DETAIL_KEY: US.UploadRefError(3, "0123456789abcdef").describe()})
    assert F._input_detail(good) == "upload_ids[3]（upl_0123456789abcdef…） 無效：不符、已用過或已過期"
    for evil in ("<script>", "upload_ids[0] 無效：不符、已用過或已過期 + extra",
                 "upload_ids[0]（upl_" + "A" * 43 + "…）無效：不符、已用過或已過期"):
        assert F._input_detail(ToolResult(ok=False, error="INVALID_INPUT",
                                          data={F.INPUT_DETAIL_KEY: evil})) is None
    assert F._input_detail(ToolResult(ok=False, error="NO_MATCH",
                                      data={F.INPUT_DETAIL_KEY: F.URL_INPUT_DISABLED_DETAIL})) is None


# ═══════════════════════════════════════════════════════════════════
# S12／S13：啟動檢查與開關（A1(g)、A3）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
@pytest.mark.parametrize("env,expected", [
    ({}, False),                                                 # UVICORN_WORKERS 預設 4
    ({"UVICORN_WORKERS": "1"}, True),
    ({"UVICORN_WORKERS": "2"}, False),
    ({"UVICORN_WORKERS": "abc"}, False),
    ({"UVICORN_WORKERS": "4", "UVICORN_RELOAD": "true"}, True),  # reload ⇒ app.py 用 1
    ({"UVICORN_WORKERS": "1", "AGENT_UPLOAD_ENDPOINT": "false"}, False),
    ({"UVICORN_WORKERS": "1", "AGENT_UPLOAD_ENDPOINT": "off"}, False),
    ({"UVICORN_WORKERS": "1", "AGENT_UPLOAD_ENDPOINT": "maybe"}, False),
    ({"UVICORN_WORKERS": "1", "AGENT_UPLOAD_ENDPOINT": "true"}, True),
    ({"UVICORN_WORKERS": "1", "AGENT_UPLOAD_ENDPOINT": ""}, True),  # 空＝未設＝預設開
])
def test_upload_endpoint_status(env, expected, monkeypatch):
    for k in ("UVICORN_WORKERS", "UVICORN_RELOAD", "AGENT_UPLOAD_ENDPOINT"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    enabled, reason = US.upload_endpoint_status()
    assert enabled is expected
    assert (reason == "") is expected, "關閉時一定要有原因、開啟時不得有"
    if env.get("UVICORN_WORKERS") in ("2",) or env == {}:
        assert "UVICORN_WORKERS" in reason and "≠1" in reason


@pytest.mark.req(_REQ)
def test_workers_not_one_means_no_route_and_no_ticket_tool(monkeypatch, capsys):
    """A1(g)：以 workers≠1（unit 環境預設 4）匯入真 `app.py` ⇒ 直傳關閉、路由不在、
    上傳票工具未註冊。正對照：同一函式在 workers=1 ⇒ 註冊。"""
    monkeypatch.delenv("UVICORN_WORKERS", raising=False)
    monkeypatch.delenv("UVICORN_RELOAD", raising=False)
    app_mod = _import_app(monkeypatch)

    if app_mod._UPLOAD_ENABLED:
        pytest.fail("[env] 本行程匯入 app.py 時 workers=1——這條測不到 workers≠1")
    assert "UVICORN_WORKERS" in app_mod._UPLOAD_DISABLED_REASON
    paths = {getattr(r, "path", None) for r in app_mod.app.router.routes}
    assert US.UPLOAD_PATH not in paths
    assert "/api/v1/agent/trace" in paths                    # 正對照：同前綴路由在
    assert F.UPLOAD_TICKET_NAME not in app_mod._mcp_registry._specs
    # app.py 的 __main__ 與檢查用同一條 worker 規則
    src = open(app_mod.__file__, encoding="utf-8").read()
    assert "workers = _upload_store.configured_uvicorn_workers()" in src

    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    monkeypatch.setenv("UVICORN_WORKERS", "1")
    reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None))
    assert F.UPLOAD_TICKET_NAME in reg._specs
    monkeypatch.setenv("UVICORN_WORKERS", "3")
    reg2 = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None))
    assert F.UPLOAD_TICKET_NAME not in reg2._specs


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("raw,mode", [
    (None, "upload_ids"), ("", "upload_ids"), ("upload_ids", "upload_ids"),
    ("urls", "urls"), (" URLS ", "urls"), ("url", "upload_ids"), ("both", "upload_ids"),
    ("1", "upload_ids"),
])
def test_attachment_input_mode(raw, mode, monkeypatch):
    if raw is None:
        monkeypatch.delenv(US.ATTACHMENT_INPUT_ENV, raising=False)
    else:
        monkeypatch.setenv(US.ATTACHMENT_INPUT_ENV, raw)
    assert US.attachment_input_mode() == mode


# ═══════════════════════════════════════════════════════════════════
# A3＋位元組接線：agent.turn 經 registry.call（門面走的同一條）
# ═══════════════════════════════════════════════════════════════════
def _turn_registry(deps) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    return reg


async def _turn(reg, args, identity=None):
    return await reg.call(identity or _identity(), F.AGENT_TURN_NAME, args, 30.0, stage="M1")


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("mode", [None, "garbage"])
async def test_default_or_invalid_mode_rejects_urls_without_fetching(mode, monkeypatch):
    if mode is not None:
        monkeypatch.setenv(US.ATTACHMENT_INPUT_ENV, mode)
    fetcher = FakeFetcher()
    monkeypatch.setattr(F, "_image_fetch_one", fetcher)
    monkeypatch.setattr(F, "_document_fetch_one", fetcher)
    reg = _turn_registry(_turn_deps())
    r = await _turn(reg, {"message": "看照片", "image_urls": ["https://relay.jgbsmart.com/a.jpg"]})
    assert r.ok is False and r.error == "INVALID_INPUT"
    assert F._input_detail(r) == F.URL_INPUT_DISABLED_DETAIL
    r2 = await _turn(reg, {"message": "看文件", "attachment_purpose": "document",
                           "file_urls": ["https://relay.jgbsmart.com/a.pdf"]})
    assert r2.ok is False and r2.error == "INVALID_INPUT"
    assert fetcher.urls == [], "預設模式 ⛔ 抓任何網址"
    # 正對照：純文字回合照常
    assert (await _turn(reg, {"message": "你好"})).ok is True


@pytest.mark.req(_REQ)
async def test_urls_mode_restores_old_behavior_and_rejects_upload_ids(monkeypatch):
    monkeypatch.setenv(US.ATTACHMENT_INPUT_ENV, "urls")
    monkeypatch.setattr(image_fetch, "resolve_host", lambda h: ["93.184.216.34"])
    fetcher = FakeFetcher()
    monkeypatch.setattr(F, "_image_fetch_one", fetcher)
    monkeypatch.setattr(F, "_image_recognize_batch", FakeRecognizer([_recognition()]))
    reg = _turn_registry(_turn_deps())
    url = "https://relay.jgbsmart.com/a.jpg"
    r = await _turn(reg, {"message": "看照片", "image_urls": [url]})
    assert r.ok is True and fetcher.urls == [url]
    uid = _upload()
    r2 = await _turn(reg, {"message": "看照片", "upload_ids": [uid]})
    assert r2.ok is False and r2.error == "INVALID_INPUT"
    assert F._input_detail(r2) == F.UPLOAD_INPUT_DISABLED_DETAIL
    assert US.STORE.counts()[US.STATE_UNREFERENCED] == 1, "被拒的回合 ⛔ 消耗 upload_id"


@pytest.mark.req(_REQ)
async def test_repair_upload_bytes_reach_recognition_and_are_retained_then_released(monkeypatch):
    fetcher = FakeFetcher()
    monkeypatch.setattr(F, "_image_fetch_one", fetcher)
    recognizer = FakeRecognizer([_recognition()])
    monkeypatch.setattr(F, "_image_recognize_batch", recognizer)
    reg = _turn_registry(_turn_deps())
    ids = [_upload(), _upload(data=_img("PNG"))]
    r = await _turn(reg, {"message": "漏水", "upload_ids": ids})
    assert r.ok is True, r
    assert fetcher.urls == [], "直傳 ⛔ 連網抓檔"
    assert len(recognizer.batches) == 1 and len(recognizer.batches[0]) == 2
    assert recognizer.batches[0][1].startswith("data:image/png;base64,")
    counts = US.STORE.counts()
    assert counts[US.STATE_RETAINED] == 2 and counts["uploads"] == 2
    # 再用一次 ⇒ INVALID_INPUT（單次）
    again = await _turn(reg, {"message": "漏水", "upload_ids": ids[:1]})
    assert again.ok is False and again.error == "INVALID_INPUT"
    assert F._input_detail(again).startswith("upload_ids[0]（upl_")
    # 卡兌現／作廢 ⇒ release ⇒ 刪除
    US.STORE.release([i.split(".")[0][len("upl_"):] for i in ids])
    assert US.STORE.counts()["uploads"] == 0


@pytest.mark.req(_REQ)
async def test_document_upload_flows_to_extraction_and_is_deleted_at_turn_end(monkeypatch):
    extractor = FakeExtractor(_bill_result())
    monkeypatch.setattr(F, "_document_extract_pages", extractor)
    doc_fetcher = FakeFetcher()
    monkeypatch.setattr(F, "_document_fetch_one", doc_fetcher)
    reg = _turn_registry(_turn_deps())
    uid = _upload("document")
    assert US.STORE.counts()["uploads"] == 1
    r = await _turn(reg, {"message": "幫我看", "attachment_purpose": "document",
                          "upload_ids": [uid]})
    assert r.ok is True, r
    assert doc_fetcher.urls == []
    assert len(extractor.batches) == 1 and extractor.batches[0], "PDF 頁圖沒送到擷取"
    assert US.STORE.counts()["uploads"] == 0, "文件類在引用回合結束即刪"


@pytest.mark.req(_REQ)
async def test_document_turn_is_cleaned_up_even_when_the_turn_fails(monkeypatch):
    """回合失敗（擷取例外）也照樣刪：收尾在 try/finally。"""
    monkeypatch.setattr(F, "_document_extract_pages", FakeExtractor(raises=RuntimeError("x")))
    reg = _turn_registry(_turn_deps())
    uid = _upload("document")
    await _turn(reg, {"message": "幫我看", "attachment_purpose": "document", "upload_ids": [uid]})
    assert US.STORE.counts()["uploads"] == 0


@pytest.mark.req(_REQ)
async def test_any_bad_upload_id_rejects_the_whole_turn_without_partial_processing(monkeypatch):
    recognizer = FakeRecognizer([_recognition()])
    monkeypatch.setattr(F, "_image_recognize_batch", recognizer)
    reg = _turn_registry(_turn_deps())
    good = _upload()
    other = _upload(user_id="99")                   # 別人的
    r = await _turn(reg, {"message": "漏水", "upload_ids": [good, other]})
    assert r.ok is False and r.error == "INVALID_INPUT"
    assert F._input_detail(r).startswith("upload_ids[1]")
    assert recognizer.batches == [], "⛔ 部分處理"
    assert US.STORE.counts()[US.STATE_UNREFERENCED] == 2, "被拒的回合 ⛔ 消耗任何 upload_id"
    # 用途不符
    r2 = await _turn(reg, {"message": "x", "attachment_purpose": "document", "upload_ids": [good]})
    assert r2.ok is False and r2.error == "INVALID_INPUT"
    # 超量：repair 11、document 2
    r3 = await _turn(reg, {"message": "x", "upload_ids": [good] * 11})
    assert r3.ok is False and r3.error == "INVALID_INPUT"
    d1, d2 = _upload("document"), _upload("document")
    r4 = await _turn(reg, {"message": "x", "attachment_purpose": "document", "upload_ids": [d1, d2]})
    assert r4.ok is False and r4.error == "INVALID_INPUT"
    # 重複同一個
    dup = _upload()
    r5 = await _turn(reg, {"message": "x", "upload_ids": [dup, dup]})
    assert r5.ok is False and r5.error == "INVALID_INPUT"
    # 缺 user_id 的身分 ⇒ INVALID_INPUT
    r6 = await _turn(reg, {"message": "x", "upload_ids": [good]}, _identity(user_id=None))
    assert r6.ok is False and r6.error == "INVALID_INPUT"
    assert F._input_detail(r6) == F.USER_ID_REQUIRED_DETAIL
    # 正對照：只帶好的那一個 ⇒ 成功
    assert (await _turn(reg, {"message": "漏水", "upload_ids": [good]})).ok is True


@pytest.mark.req(_REQ)
async def test_upload_only_turn_is_allowed_and_empty_is_not(monkeypatch):
    monkeypatch.setattr(F, "_image_recognize_batch", FakeRecognizer([_recognition()]))
    reg = _turn_registry(_turn_deps())
    assert (await _turn(reg, {"message": "", "upload_ids": [_upload()]})).ok is True
    empty = await _turn(reg, {"message": "  ", "upload_ids": []})
    assert empty.ok is False and empty.error == "INVALID_INPUT"


@pytest.mark.req(_REQ)
def test_upload_bytes_never_enter_agent_state_or_logs_by_construction():
    """暫存模組與路由不呼叫 logger 記錄任何票、檔名、內容（只有錯誤碼）。"""
    for mod in (US, agent_uploads):
        src = inspect.getsource(mod)
        for call in re.findall(r"logger\.\w+\(([^)]*)\)", src):
            assert not re.search(r"token|upload_id|data|filename|verifier", call), call
