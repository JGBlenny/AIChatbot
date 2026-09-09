"""照片抓檔的硬邊界（Plan W8 (2)／security-reviewer S9-1～S9-5、S9-21、S9-23）。

line-bot 把使用者傳的照片落在 relay 上、給一個 HMAC 簽章網址，**chatai 自己下載**。
這是一條「服務端拿著呼叫端給的網址去連線」的路徑 ⇒ 預設就是 SSRF。本模組是那條
路徑上唯一的閘門，`/mcp` 的照片進場（`mcp_facade._agent_turn`）只能經這裡抓檔。

**六道閘（順序固定，⛔ 不得調換、⛔ 不得為了讓某個 demo 過而放寬）**：
  ① `urlparse` 後 scheme 必為 `https`（⛔ http、⛔ 其他 scheme）；
  ② host 與白名單**等值**（`IMAGE_URL_ALLOWLIST`，預設 `relay.jgbsmart.com`；
     ⛔ 後綴／子字串比對——`relay.jgbsmart.com.evil.tld` 正是那樣被放進來的）；
  ③ ⛔ userinfo（`https://relay.jgbsmart.com@evil.tld/` 的 host 其實是 evil.tld，
     只有把 userinfo 一律拒掉才不必跟解析器的邊角案例賭）、⛔ IP literal、
     port ∈ {443, 空}；
  ④ 簽章網址的 `exp` 查詢參數**先於抓檔**預檢（過期 ⇒ 丟棄）。
     ⚠️ 這是**時戳預檢、不是驗簽**：HMAC 金鑰未交付給 chatai，`sig` 由 relay 自驗
     （明寫的依賴，S9-4）；⛔ 不要因為這裡有一段 `exp` 就以為網址被驗過了。
  ⑤ 解析後的 IP 落私網／loopback／link-local／保留段即拒。
     ⚠️ **殘窗（明寫取捨）**：這裡查的 IP 與 httpx 之後真正連線用的 IP 是兩次解析，
     中間可被 DNS rebinding 換掉。要關掉這個殘窗得自己接 socket／pin IP，
     那是另一條路徑的工程；在「白名單只有一台 relay」的前提下接受。
  ⑥ **bytes 硬閘**：串流邊讀邊累計，超過 `IMAGE_MAX_BYTES` 立刻中止連線
     （`Content-Length` 是對方說的，⛔ 不可信）。

**bytes 生命週期**：本模組只回傳 bytes 給呼叫端，⛔ 不落地、⛔ 不寫任何紀錄；
所有例外訊息只帶**內部錯誤碼**，⛔ 不帶網址、不帶內容、不帶對方的例外訊息。
"""
from __future__ import annotations

import ipaddress
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

import httpx

# ════════════════════════════════════════════════════════════════════
# 常數與旋鈕
# ════════════════════════════════════════════════════════════════════
#: 允許抓檔的主機（**等值**比對）。unit 釘住這個預設值——放寬白名單是
#: 「停下交裁」的事（Plan §6 W8 (2) 停止條件），⛔ 不由改碼的人自己決定。
DEFAULT_IMAGE_URL_ALLOWLIST: tuple = ("relay.jgbsmart.com",)

_IMAGE_URL_ALLOWLIST_ENV = "IMAGE_URL_ALLOWLIST"

#: 單張照片的 bytes 硬上限（5,000,000）。⚠️ 不是 5 MiB——契約寫的是十進位。
IMAGE_MAX_BYTES = 5_000_000

#: 一回合最多幾張（第 11 張起整回合 `INVALID_INPUT`，業主 2026-09-08 裁）。
IMAGE_MAX_COUNT = 10

# ── W9 U1：文件線（`file_urls`）的量級常數 ──────────────────────────
# ⚠️ **同一條抓檔路徑、不同的量級旋鈕**：文件走的是 `fetch_image(max_bytes=…)`
#    這一支（W9-5：⛔ 不得新增第二支抓檔函式——第二支就是第二套閘門，而第二套
#    永遠會少一道）。下面四個常數是「文件比照片多出來的那幾個上限」。
#: 單份 PDF 的 bytes 硬上限（與照片同值 5,000,000，W9-7）。
FILE_MAX_BYTES = 5_000_000

#: 一回合最多幾份檔（demo ≤1；第 2 份起整回合 `INVALID_INPUT`）。
#: ⛔ 不寫進 `AGENT_TURN_SPEC` 的 `maxItems`——`registry._validate_value` 不認它
#:    （S9-5／W9-18：寫了等於掛一張看起來有守、實際靜默無效的牌）。
FILE_MAX_COUNT = 1

#: 每小時每 `(api_key_id, vendor_id)` 的份數上限。
FILE_COUNT_CAP_PER_HOUR = 20

#: 單份 PDF 最多看前幾頁（超過只看前 N 頁**並明講**，⛔ 不靜默截斷）。
DOC_MAX_PAGES = 5

#: 照片頁＋PDF 頁的**合計**上限；超過 ⇒ 整回合 `INVALID_INPUT`（W9-15，
#: 沿用「超過即拒、⛔ 不截斷後照跑」的紀律）。
DOC_TOTAL_PAGES_MAX = 10

_FILE_MAX_BYTES_ENV = "FILE_MAX_BYTES"
_FILE_COUNT_CAP_ENV = "FILE_COUNT_CAP_PER_HOUR"
_DOC_MAX_PAGES_ENV = "DOC_MAX_PAGES"
_DOC_TOTAL_PAGES_MAX_ENV = "DOC_TOTAL_PAGES_MAX"

#: PDF 的宣告 MIME（**逐字等值**，⛔ 不前綴比對）與 magic bytes。
#: ⚠️ magic 只**防誤派**（W9-14）：它證明「這不是被叫成 PDF 的別種東西」，
#:    ⛔ 不是解析面的緩解——解析面的防線在 `document_extract.rasterize_pdf`。
PDF_CONTENT_TYPE = "application/pdf"
PDF_MAGIC = b"%PDF-"

#: 每批送辨識的張數（>5 張時 chatai **內部**分批，⛔ 不讓 line-bot 拆回合）。
IMAGE_BATCH_SIZE = 5

#: 每小時每 `(api_key_id, vendor_id)` 的張數上限。
_DEFAULT_IMAGE_COUNT_CAP_PER_HOUR = 200
_IMAGE_COUNT_CAP_ENV = "IMAGE_COUNT_CAP_PER_HOUR"
_IMAGE_COUNT_WINDOW_S = 3600.0

#: 內部錯誤碼（**只進 trace 的 violation 與健檢**，⛔ 不外送給呼叫端——
#: `/mcp` 的錯誤值域是封閉五值，見 S9-22 (a)）。
IMAGE_URL_NOT_ALLOWED = "IMAGE_URL_NOT_ALLOWED"
IMAGE_URL_EXPIRED = "IMAGE_URL_EXPIRED"
IMAGE_FETCH_FAILED = "IMAGE_FETCH_FAILED"
IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
IMAGE_FORMAT_INVALID = "IMAGE_FORMAT_INVALID"
#: W9 U1：宣告 MIME 或 magic 不是 PDF（⇒ 該檔丟棄）。
FILE_FORMAT_INVALID = "FILE_FORMAT_INVALID"


class ImageFetchError(Exception):
    """抓檔被閘門擋下／失敗。

    ⛔ **訊息只有內部錯誤碼**：網址、回應內容、對方的例外訊息一律不進來——
    這個例外會被記進 log／violation，帶原文等於把照片與簽章網址寫進紀錄。
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def image_url_allowlist() -> tuple:
    """`IMAGE_URL_ALLOWLIST`（逗號分隔）；未設 ⇒ `DEFAULT_IMAGE_URL_ALLOWLIST`。

    設成空字串 ⇒ **空白名單**＝任何網址都抓不到（fail-closed），
    ⛔ 不回退成預設值——「我要關掉照片進場」必須關得掉。
    """
    raw = os.getenv(_IMAGE_URL_ALLOWLIST_ENV)
    if raw is None:
        return DEFAULT_IMAGE_URL_ALLOWLIST
    hosts = tuple(h.strip().lower() for h in raw.split(",") if h.strip())
    return hosts


def image_entry_enabled() -> bool:
    """`/mcp` 照片進場這一刻是否真的抓得到檔＝**白名單非空**。

    ⚠️ 這**不是** REST 路徑的 `ENABLE_IMAGE_RECOGNITION`（那條是另一條信任模型，
    S9-17）。健檢印的 `image_recognition.enabled` 取本函式——印一個對本路徑
    沒有作用的旗標，比不印還糟。
    """
    return bool(image_url_allowlist())


def image_count_cap_per_hour() -> int:
    """`IMAGE_COUNT_CAP_PER_HOUR`（預設 200）；非法值回預設。"""
    raw = (os.getenv(_IMAGE_COUNT_CAP_ENV) or "").strip()
    if not raw:
        return _DEFAULT_IMAGE_COUNT_CAP_PER_HOUR
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_IMAGE_COUNT_CAP_PER_HOUR
    return value if value >= 0 else _DEFAULT_IMAGE_COUNT_CAP_PER_HOUR


#: `(api_key_id, vendor_id) -> [(時戳, 張數)]`。⚠️ **行程內記憶體**——多 worker
#: 部署時每個 worker 各有一份（與 `mcp_facade._agent_turn_calls` 同一個已知限制，
#: ⛔ 不在本切片另建共享計數器）。
_image_counts: dict = {}


def check_and_record_image_count(key: tuple, count: int, now: Optional[float] = None) -> bool:
    """滑動窗記 `count` 張；**這一回合會超過上限 ⇒ `False` 且⛔ 不記**（全有全無）。"""
    now = time.monotonic() if now is None else now
    cap = image_count_cap_per_hour()
    entries = _image_counts.setdefault(key, [])
    cutoff = now - _IMAGE_COUNT_WINDOW_S
    while entries and entries[0][0] <= cutoff:
        entries.pop(0)
    used = sum(n for _, n in entries)
    if used + count > cap:
        return False
    entries.append((now, count))
    return True


def reset_image_count_cap() -> None:
    """測試用：清掉行程內的滑動窗（⛔ 產品路徑不呼叫）。"""
    _image_counts.clear()


# ════════════════════════════════════════════════════════════════════
# W9 U1：文件線的旋鈕、配額與 PDF 形狀檢查
# ════════════════════════════════════════════════════════════════════
def _int_env(name: str, default: int, *, minimum: int = 0) -> int:
    """`name` 的整數 env；未設／非整數／小於 `minimum` ⇒ **回預設**（⛔ 不炸）。

    ⚠️ 壞值退預設而不是退 0：把「打錯字」變成「這條路整個關掉」是靜默的行為
    改變，而部署者只會看到功能突然不見、看不到原因。
    """
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def file_max_bytes() -> int:
    """`FILE_MAX_BYTES`（預設 5,000,000）；非法值回預設。"""
    return _int_env(_FILE_MAX_BYTES_ENV, FILE_MAX_BYTES, minimum=1)


def file_count_cap_per_hour() -> int:
    """`FILE_COUNT_CAP_PER_HOUR`（預設 20）；非法值回預設。"""
    return _int_env(_FILE_COUNT_CAP_ENV, FILE_COUNT_CAP_PER_HOUR)


def doc_max_pages() -> int:
    """`DOC_MAX_PAGES`（預設 5）；非法值回預設。"""
    return _int_env(_DOC_MAX_PAGES_ENV, DOC_MAX_PAGES, minimum=1)


def doc_total_pages_max() -> int:
    """`DOC_TOTAL_PAGES_MAX`（預設 10）；非法值回預設。"""
    return _int_env(_DOC_TOTAL_PAGES_MAX_ENV, DOC_TOTAL_PAGES_MAX, minimum=1)


#: `(api_key_id, vendor_id) -> [(時戳, 份數)]`。⚠️ **行程內記憶體**，多 worker
#: 各一份——與 `_image_counts` 同一個已知限制（契約照實寫，見 U5 契約表）。
_file_counts: dict = {}


def check_and_record_file_count(key: tuple, count: int, now: Optional[float] = None) -> bool:
    """滑動窗記 `count` 份；**這一回合會超過上限 ⇒ `False` 且⛔ 不記**（全有全無）。

    形狀逐位比照 `check_and_record_image_count`——⛔ 不另立第二套語義：兩個配額
    在 `_agent_turn` 是**並列**檢查的，語義一旦分歧，「用罄」在兩條線上會是兩件
    不同的事。
    """
    now = time.monotonic() if now is None else now
    cap = file_count_cap_per_hour()
    entries = _file_counts.setdefault(key, [])
    cutoff = now - _IMAGE_COUNT_WINDOW_S
    while entries and entries[0][0] <= cutoff:
        entries.pop(0)
    used = sum(n for _, n in entries)
    if used + count > cap:
        return False
    entries.append((now, count))
    return True


def reset_file_count_cap() -> None:
    """測試用：清掉行程內的檔案滑動窗（⛔ 產品路徑不呼叫）。"""
    _file_counts.clear()


def validate_pdf_bytes(data: bytes, content_type: str) -> None:
    """PDF 的**雙檢**：宣告 MIME 逐字等值 ＋ magic `%PDF-`；不符 ⇒ `ImageFetchError`。

    ⚠️ **逐字等值、⛔ 不前綴比對、⛔ 不接受 `octet-stream`**：relay 對 PDF
    必須回 `Content-Type: application/pdf`（U5 契約要求，W9-14）。回別的值時整
    條線 fail-closed——這是刻意的：「猜它大概是 PDF」等於讓宣告型別失去意義。
    ⚠️ magic 只防誤派，⛔ 不是解析面的緩解（解析面在 `rasterize_pdf`）。
    """
    declared = str(content_type or "").split(";")[0].strip().lower()
    if declared != PDF_CONTENT_TYPE:
        raise ImageFetchError(FILE_FORMAT_INVALID)
    if not isinstance(data, (bytes, bytearray)) or not bytes(data).startswith(PDF_MAGIC):
        raise ImageFetchError(FILE_FORMAT_INVALID)


# ════════════════════════════════════════════════════════════════════
# 健檢計數（`services/agent/health.py` 的 `image_recognition` 鍵）
# ════════════════════════════════════════════════════════════════════
#: 近一小時的辨識失敗時戳（wall clock；`last_failure_at` 要印得出 ISO 時間）。
_image_failures: list = []


def record_image_failure(now: Optional[float] = None) -> None:
    """記一次 vision 失敗——**失敗必須看得見**（⛔ 不沿用 REST 的靜默降級）。"""
    now = time.time() if now is None else now
    _image_failures.append(now)
    cutoff = now - _IMAGE_COUNT_WINDOW_S
    while _image_failures and _image_failures[0] <= cutoff:
        _image_failures.pop(0)


def image_failure_stats(now: Optional[float] = None) -> dict:
    """`{failures_1h, last_failure_at}`；沒有失敗 ⇒ `{0, None}`。"""
    now = time.time() if now is None else now
    cutoff = now - _IMAGE_COUNT_WINDOW_S
    recent = [t for t in _image_failures if t > cutoff]
    last = max(_image_failures) if _image_failures else None
    return {
        "failures_1h": len(recent),
        "last_failure_at": (
            datetime.fromtimestamp(last, tz=timezone.utc).isoformat() if last else None
        ),
    }


def reset_image_failures() -> None:
    """測試用：清掉行程內的失敗計數（⛔ 產品路徑不呼叫）。"""
    _image_failures.clear()


# ════════════════════════════════════════════════════════════════════
# 網址閘門
# ════════════════════════════════════════════════════════════════════
def _host_is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _ip_is_forbidden(ip: str) -> bool:
    """私網／loopback／link-local／保留／multicast／未指定 ⇒ 拒。"""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _exp_is_expired(query: str, now: float) -> bool:
    """簽章網址的 `exp` 時戳預檢——**只判時戳，⛔ 不是驗簽**（S9-4）。

    沒有 `exp` ⇒ 不擋（relay 端仍會驗 `sig`）；`exp` 不是整數 ⇒ 當**過期**處理
    （形狀不對的簽章網址不該被抓，fail-closed）。
    """
    values = parse_qs(query or "").get("exp")
    if not values:
        return False
    try:
        exp = int(str(values[0]).strip())
    except (TypeError, ValueError):
        return True
    return exp <= now


def validate_image_url(url: str, *, now: Optional[float] = None) -> str:
    """跑完①～⑤道閘；通過 ⇒ 回**主機名**，否則 `ImageFetchError`。

    ⛔ 不回傳「清洗後的網址」——重寫網址等於再開一條「我以為我改對了」的路，
    呼叫端一律用**原字串**去連線，閘門只負責判它能不能連。
    """
    now = time.time() if now is None else now
    if not isinstance(url, str) or not url.strip():
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    host = (parsed.hostname or "").lower()
    if not host or _host_is_ip_literal(host):
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    if host not in image_url_allowlist():
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    try:
        port = parsed.port
    except ValueError:                       # port 不是數字 ⇒ 形狀就不對
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    if port not in (None, 443):
        raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    if _exp_is_expired(parsed.query, now):
        raise ImageFetchError(IMAGE_URL_EXPIRED)
    for ip in resolve_host(host):
        if _ip_is_forbidden(ip):
            raise ImageFetchError(IMAGE_URL_NOT_ALLOWED)
    return host


def resolve_host(host: str) -> list:
    """`host` 的所有 IP（解析失敗 ⇒ `ImageFetchError`）。

    ⚠️ 抽成模組級具名函式**就是為了讓測試 monkeypatch 得到它**——離線測試不得
    真的發 DNS 查詢，而「私網 IP 即拒」那條又非測不可。
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise ImageFetchError(IMAGE_FETCH_FAILED)
    return [info[4][0] for info in infos]


# ════════════════════════════════════════════════════════════════════
# 抓檔
# ════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class FetchedImage:
    """抓回來的一張照片：**只有 bytes 與 content-type**，⛔ 不帶網址。"""

    data: bytes
    content_type: str


def _new_client(timeout_s: float) -> httpx.AsyncClient:
    # ⛔ `follow_redirects=False` **顯式**：httpx 的預設值變過，靠預設等於把
    #    「不跟轉址」這條閘門交給函式庫版本決定。3xx ⇒ 當抓檔失敗丟棄。
    return httpx.AsyncClient(follow_redirects=False, timeout=timeout_s)


async def fetch_image(
    url: str,
    *,
    timeout_s: float = 10.0,
    now: Optional[float] = None,
    client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    max_bytes: int = IMAGE_MAX_BYTES,
) -> FetchedImage:
    """跑完六道閘抓一個檔；任一關失敗 ⇒ `ImageFetchError`（帶內部碼）。

    `max_bytes`（W9 U1／W9-5）：第⑥道 bytes 硬閘的量級。⛔⛔ **文件線就是走這
    一支、只換這一個參數**——⛔ 不得為 PDF 新增第二支抓檔函式：第二支就是第二
    套閘門，而第二套永遠會漏掉其中一道（白名單／https／userinfo／IP／`exp`／
    轉址／串流上限，這六道少任何一道都是一個獨立的 SSRF 或 DoS）。
    ⚠️ 函式名維持 `fetch_image` 也是刻意的：改名會讓「這條路只有一個抓檔閘」
       這件事在 grep 上斷掉。
    """
    validate_image_url(url, now=now)
    factory = client_factory or (lambda: _new_client(timeout_s))
    total = 0
    chunks: list = []
    try:
        async with factory() as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    # 3xx 也走這裡：⛔ 不跟轉址（S9-2），轉址就是丟棄。
                    raise ImageFetchError(IMAGE_FETCH_FAILED)
                content_type = str(response.headers.get("content-type") or "").split(";")[0].strip()
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        # ⚠️ 邊讀邊判、當場中止連線——`Content-Length` 不可信
                        #    （對方大可少報，S9-21）。
                        raise ImageFetchError(IMAGE_TOO_LARGE)
                    chunks.append(chunk)
    except ImageFetchError:
        raise
    except Exception:                        # 連線／TLS／逾時
        # ⛔ `from None`：對方可控的例外訊息不得掛在 `__cause__` 上被 log 印出去。
        raise ImageFetchError(IMAGE_FETCH_FAILED) from None
    return FetchedImage(data=b"".join(chunks), content_type=content_type)


__all__ = [
    "DEFAULT_IMAGE_URL_ALLOWLIST",
    "DOC_MAX_PAGES",
    "DOC_TOTAL_PAGES_MAX",
    "FILE_COUNT_CAP_PER_HOUR",
    "FILE_FORMAT_INVALID",
    "FILE_MAX_BYTES",
    "FILE_MAX_COUNT",
    "PDF_CONTENT_TYPE",
    "PDF_MAGIC",
    "FetchedImage",
    "IMAGE_BATCH_SIZE",
    "IMAGE_FETCH_FAILED",
    "IMAGE_FORMAT_INVALID",
    "IMAGE_MAX_BYTES",
    "IMAGE_MAX_COUNT",
    "IMAGE_TOO_LARGE",
    "IMAGE_URL_EXPIRED",
    "IMAGE_URL_NOT_ALLOWED",
    "ImageFetchError",
    "check_and_record_file_count",
    "check_and_record_image_count",
    "doc_max_pages",
    "doc_total_pages_max",
    "fetch_image",
    "file_count_cap_per_hour",
    "file_max_bytes",
    "image_count_cap_per_hour",
    "image_entry_enabled",
    "image_failure_stats",
    "image_url_allowlist",
    "record_image_failure",
    "reset_file_count_cap",
    "reset_image_count_cap",
    "reset_image_failures",
    "resolve_host",
    "validate_image_url",
    "validate_pdf_bytes",
]
