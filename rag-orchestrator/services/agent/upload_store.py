"""瀏覽器直傳附件的記憶體暫存（UD-1，plan-upload-documind-20261028 §4 UD-1／D1〜D3）。

流程（JGB 規格草稿 §2〜§4）：
  ① JGB 代理呼叫 `agent.upload_ticket` ⇒ 本模組 `issue_ticket` 發一張上傳票；
  ② 瀏覽器 `POST /api/v1/agent/uploads`（`routers/agent_uploads.py`）帶票上傳
     ⇒ `verify_ticket` → `add_upload` 存進記憶體，回 `upload_id`；
  ③ `agent.turn` 帶 `upload_ids` ⇒ `check`／`claim` 取出位元組交給既有的
     `prepare_image_turn`／`prepare_document_turn`，回合結束 `end_turn`。

安全性決定（S6／S7／S8；審查時請對這幾條）：
- **票與 `upload_id` 一律「selector.verifier」兩段式**：selector＝64 bit 隨機
  hex，只當查表鍵（非秘密）；verifier＝`secrets.token_urlsafe(32)`（CSPRNG、
  256 bit），伺服端**只存 `sha256(verifier)`**，比對用 `hmac.compare_digest`
  （定時比較）。原字串只在發出的那一刻存在於回應裡，⛔ 不存、⛔ 不進 log。
- **綁定（S6）**：`UploadBinding`＝(api_key_id, vendor_id, user_id, role_id,
  命名空間 session_id, attachment_purpose)。票發出時綁定，上傳繼承票的綁定；
  `agent.turn` 用自己的身分重算綁定，**六欄逐一等值**才放行。
- **缺 `user_id` 一律拒（S7）**：`binding_from_identity` 直接 raise，不論金鑰種類。
- **單次使用**：`claim` 之後狀態離開 `unreferenced`，同一個 `upload_id` 第二次
  引用 ⇒ 判為無效。
- **錯誤不分原因**：不符、用過、過期、不存在一律同一種錯（`UploadRefError`），
  只帶「第幾個」與 selector（非秘密段）——⛔ 不讓呼叫端藉錯誤區分「別人的
  upload_id 存在」。
- **保留時間（D2）**：每筆上傳自上傳起最長 `LIMITS.upload_ttl_s`（30 分鐘），
  不論狀態，到點即刪；文件類在引用回合結束即刪；修繕照片在回合結束轉
  `retained`，等確認卡兌現或作廢時 `release`（UD-3 接線），最遲同樣 30 分鐘。
- **只在記憶體（D3）**：位元組 ⛔ 不落地、⛔ 進 `agent_state`／trace／log；
  `repr` 不含位元組。依賴單一 worker（S12，`upload_endpoint_status`）。

全部操作是同步函式、以 `threading.Lock` 包住——同一事件迴圈內不會在檢查與
寫入之間讓出控制權，張數上限與單次使用因此是原子的。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional
from urllib.parse import urlsplit

from services.agent.limits import LIMITS

# ════════════════════════════════════════════════════════════════════
# 常數與設定
# ════════════════════════════════════════════════════════════════════
#: 上傳端點的後端路徑。`McpServiceGate`、`api_key_guard`、CORS 旁路三處
#: 都以**完全等於**這個字串判斷（S1：⛔ 前綴豁免）。
UPLOAD_PATH = "/api/v1/agent/uploads"
#: 對外（經 nginx `location = /rag-api/v1/agent/uploads`）的路徑。
PUBLIC_UPLOAD_PATH = "/rag-api/v1/agent/uploads"

ATTACHMENT_ENDPOINT_ENV = "AGENT_UPLOAD_ENDPOINT"
ATTACHMENT_INPUT_ENV = "AGENT_ATTACHMENT_INPUT"
UPLOAD_ALLOWED_ORIGINS_ENV = "AGENT_UPLOAD_ALLOWED_ORIGINS"
UPLOAD_PUBLIC_URL_ENV = "AGENT_UPLOAD_PUBLIC_URL"

INPUT_MODE_UPLOAD_IDS = "upload_ids"
INPUT_MODE_URLS = "urls"

TICKET_PREFIX = "upt_"
UPLOAD_ID_PREFIX = "upl_"
_SELECTOR_HEX_LEN = 16          # secrets.token_hex(8) ⇒ 64 bit 查表鍵
_VERIFIER_BYTES = 32            # 256 bit（S8）
_VERIFIER_LEN = 43              # token_urlsafe(32) 的長度（無 padding）
#: 進解析前的長度上限：超過即判無效，⛔ 不對任意長字串跑正規式。
TOKEN_MAX_LEN = 128
_TOKEN_RE = re.compile(
    r"\A(upt_|upl_)([0-9a-f]{%d})\.([A-Za-z0-9_-]{%d})\Z" % (_SELECTOR_HEX_LEN, _VERIFIER_LEN)
)

#: 用途 → 可收的內容型別（JGB 規格 §2）。⛔ 擴充前先改規格。
ACCEPT: dict = {
    "repair": ("image/jpeg", "image/png", "image/webp"),
    "document": ("application/pdf", "image/jpeg", "image/png"),
}
PDF_CONTENT_TYPE = "application/pdf"


def max_files_for(purpose: str) -> int:
    if purpose == "repair":
        return LIMITS.upload_max_files_repair
    if purpose == "document":
        return LIMITS.upload_max_files_document
    raise ValueError("unknown attachment_purpose")


def attachment_input_mode() -> str:
    """`AGENT_ATTACHMENT_INPUT`：`urls` ⇒ 舊網址模式（回滾用）；其餘一律
    `upload_ids`（S13：未設、空值、非法值 ⇒ `upload_ids`，⛔ 抓網址）。"""
    raw = os.getenv(ATTACHMENT_INPUT_ENV, "")
    if raw.strip().lower() == INPUT_MODE_URLS:
        return INPUT_MODE_URLS
    return INPUT_MODE_UPLOAD_IDS


_FALSY = ("0", "false", "no", "off")
_TRUTHY = ("1", "true", "yes", "on")


def configured_uvicorn_workers() -> int:
    """`python app.py` 啟動時實際使用的 worker 數（與 `app.py` `__main__` 同一條規則）。

    `UVICORN_RELOAD=true` ⇒ 1；否則 `UVICORN_WORKERS`（預設 4）。非整數 ⇒ `ValueError`。
    """
    if os.getenv("UVICORN_RELOAD", "false").lower() == "true":
        return 1
    return int(os.getenv("UVICORN_WORKERS", "4"))


def upload_endpoint_status() -> tuple:
    """直傳是否啟用 ⇒ `(enabled: bool, reason: str)`。

    - `AGENT_UPLOAD_ENDPOINT` 未設／真值 ⇒ 想開（S13：預設開）；假值 ⇒ 關；
      其他值 ⇒ 關（fail-closed，並說明原因）。
    - 想開時 worker 數必須為 1（S12）：暫存在行程記憶體，多 worker 下票、上傳、
      `agent.turn` 可能落在不同行程 ⇒ 關閉直傳並印原因。
    - `AGENT_UPLOAD_PUBLIC_URL` 必須是對外的 https 絕對網址（見 `upload_public_url_problem`）；
      未設或不合格 ⇒ 關閉（fail-closed）。⛔ 退回相對路徑：瀏覽器會打到嵌入頁自己的主機，
      設定漏了也看不出來。
    """
    raw = os.getenv(ATTACHMENT_ENDPOINT_ENV)
    if raw is not None and raw.strip() != "":
        value = raw.strip().lower()
        if value in _FALSY:
            return (False, f"{ATTACHMENT_ENDPOINT_ENV}={raw.strip()}：直傳已關閉")
        if value not in _TRUTHY:
            return (False, f"{ATTACHMENT_ENDPOINT_ENV} 值無法辨識：直傳關閉（fail-closed）")
    try:
        workers = configured_uvicorn_workers()
    except ValueError:
        return (False, "UVICORN_WORKERS 不是整數：直傳關閉（暫存只在單一行程記憶體，S12）")
    if workers != 1:
        return (
            False,
            f"UVICORN_WORKERS={workers}≠1：直傳關閉（暫存只在單一行程記憶體，S12；"
            f"要啟用請設 UVICORN_WORKERS=1）",
        )
    problem = upload_public_url_problem(os.getenv(UPLOAD_PUBLIC_URL_ENV))
    if problem is not None:
        return (False, f"{UPLOAD_PUBLIC_URL_ENV} {problem}：直傳關閉（fail-closed）")
    return (True, "")


def upload_public_url_problem(raw: Optional[str]) -> Optional[str]:
    """`AGENT_UPLOAD_PUBLIC_URL` 合格 ⇒ `None`；不合格 ⇒ 原因（⛔ 回顯值本身）。

    合格＝原字（不修剪）以 `https://` 開頭、有主機、以 `PUBLIC_UPLOAD_PATH` 結尾
    （因此也不能帶 query／fragment），且不含空白或控制字元。
    """
    if raw is None or raw == "":
        return "未設"
    if any(ord(c) <= 0x20 or ord(c) == 0x7F for c in raw):
        return "含空白或控制字元"
    if not raw.startswith("https://"):
        return "不是 https:// 開頭的絕對網址"
    try:
        host = urlsplit(raw).hostname
    except ValueError:
        host = None
    if not host:
        return "沒有主機名"
    if not raw.endswith(PUBLIC_UPLOAD_PATH):
        return f"路徑不以 {PUBLIC_UPLOAD_PATH} 結尾"
    return None


def load_upload_allowed_origins() -> frozenset:
    """上傳端點自己的 Origin 白名單（S8）：逗號分隔。回空集合（未設／空／只有 `*`）
    ＝開放模式，路由不檢查 Origin、回 ACAO `*`（業主 2026-10-29 裁示）；非空才照白名單擋。

    ⛔ 不與 `MCP_ALLOWED_ORIGINS` 共用；`*` 一律丟掉，不會成為白名單裡的萬用字。
    """
    raw = os.getenv(UPLOAD_ALLOWED_ORIGINS_ENV, "")
    origins = {o.strip() for o in raw.split(",") if o.strip()}
    origins.discard("*")
    return frozenset(origins)


def public_upload_url() -> str:
    """回給 JGB 的 `upload_url`＝`AGENT_UPLOAD_PUBLIC_URL` 原字。

    不合格 ⇒ `RuntimeError`（fail-closed；正常情況下直傳已在啟動時關閉、上傳票工具
    根本不註冊，走不到這裡）。⛔ 退回相對路徑。
    """
    raw = os.getenv(UPLOAD_PUBLIC_URL_ENV)
    if upload_public_url_problem(raw) is not None:
        raise RuntimeError(f"{UPLOAD_PUBLIC_URL_ENV} 不合格")
    return raw


def sniff_content_type(data: bytes) -> Optional[str]:
    """以檔案內容（magic bytes）判型別；⛔ 看副檔名、⛔ 看瀏覽器送的 Content-Type。

    判準與下游 `S3ImageService.validate_format`（照片）、`image_fetch.validate_pdf_bytes`
    （PDF）相同，交給 `prepare_*_turn` 時兩邊不會判得不一樣。
    """
    if not isinstance(data, (bytes, bytearray)):
        return None
    head = bytes(data[:12])
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return PDF_CONTENT_TYPE
    return None


# ════════════════════════════════════════════════════════════════════
# 綁定與錯誤
# ════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class UploadBinding:
    api_key_id: int
    vendor_id: int
    user_id: str
    role_id: Optional[str]
    session_id: str           # 命名空間鍵 `mcp:{api_key_id}:{vendor_id}:{session_id}`
    purpose: str


class UploadBindingError(ValueError):
    """身分組不出綁定（缺 user_id／api_key_id／vendor_id／session_id，或用途不明）。"""


def binding_from_identity(identity: Any, purpose: str) -> UploadBinding:
    """由**命名空間身分**（`mcp_facade.namespaced_identity` 之後）組綁定。

    S7：缺 `user_id` ⇒ raise，不論金鑰種類。
    """
    user_id = getattr(identity, "user_id", None)
    if user_id is None or str(user_id).strip() == "":
        raise UploadBindingError("user_id required")
    api_key_id = getattr(identity, "api_key_id", None)
    vendor_id = getattr(identity, "vendor_id", None)
    session_id = getattr(identity, "session_id", None)
    if api_key_id is None or vendor_id is None or not isinstance(session_id, str) or not session_id:
        raise UploadBindingError("identity incomplete")
    if purpose not in ACCEPT:
        raise UploadBindingError("unknown purpose")
    role_id = getattr(identity, "role_id", None)
    return UploadBinding(
        api_key_id=int(api_key_id),
        vendor_id=int(vendor_id),
        user_id=str(user_id),
        role_id=None if role_id is None else str(role_id),
        session_id=session_id,
        purpose=purpose,
    )


class UploadTokenInvalid(Exception):
    """票不存在、格式不對、驗證段不符。"""


class UploadTokenExpired(Exception):
    """票驗證段正確但已過期。"""


class UploadLimitReached(Exception):
    """這張票已傳滿 `max_files`。"""


class UploadRefError(Exception):
    """`agent.turn` 的某個 `upload_id` 無效（不符、用過、過期、不存在一律同一種）。

    `index`＝在 `upload_ids` 裡的位置；`selector`＝能解析出時的非秘密段（16 hex），
    否則 `None`。⛔ 不帶驗證段、⛔ 不帶失敗原因。
    """

    def __init__(self, index: int, selector: Optional[str]):
        super().__init__("upload_id invalid")
        self.index = index
        self.selector = selector

    def describe(self) -> str:
        ref = f"（{UPLOAD_ID_PREFIX}{self.selector}…）" if self.selector else ""
        return f"upload_ids[{self.index}]{ref} 無效：不符、已用過或已過期"


def _parse_token(token: Any, prefix: str) -> Optional[tuple]:
    """`(selector, verifier)`；格式不對 ⇒ `None`。"""
    if not isinstance(token, str) or len(token) > TOKEN_MAX_LEN:
        return None
    m = _TOKEN_RE.match(token)
    if m is None or m.group(1) != prefix:
        return None
    return (m.group(2), m.group(3))


def _digest(verifier: str) -> bytes:
    return hashlib.sha256(verifier.encode("ascii")).digest()


# ════════════════════════════════════════════════════════════════════
# 紀錄
# ════════════════════════════════════════════════════════════════════
@dataclass
class _Ticket:
    binding: UploadBinding
    digest: bytes = field(repr=False)
    expires_at: float
    max_files: int
    uploaded: int = 0


STATE_UNREFERENCED = "unreferenced"
STATE_CLAIMED = "claimed"
STATE_RETAINED = "retained"


@dataclass
class _Upload:
    binding: UploadBinding
    digest: bytes = field(repr=False)
    content_type: str
    size: int
    sha256: str
    data: bytes = field(repr=False)
    expires_at: float
    state: str = STATE_UNREFERENCED
    #: UD-3（S11）：修繕照片出卡時重新編碼成 JPEG 後的 sha256；`None`＝還沒編。編過之後
    #: `data`／`size` 換成重新編碼那一份（原檔位元組丟掉），`sha256` 仍是原檔的（對檔用）。
    photo_sha256: Optional[str] = None


@dataclass(frozen=True)
class IssuedTicket:
    upload_token: str = field(repr=False)
    expires_at: int            # epoch 秒（回給 JGB）
    max_files: int
    max_bytes: int
    accept: tuple


@dataclass(frozen=True)
class TicketHandle:
    selector: str
    binding: UploadBinding
    max_files: int


@dataclass(frozen=True)
class UploadReceipt:
    upload_id: str = field(repr=False)
    content_type: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ClaimedUpload:
    """`claim` 交給 `agent.turn` 的一筆：`ref` 是 selector（給 `end_turn`／`retain`／
    `release` 用的內部參照，非秘密）；`data` 不進 `repr`。"""

    ref: str
    content_type: str
    data: bytes = field(repr=False)
    sha256: str


class UploadStore:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 wall: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._wall = wall
        self._lock = threading.Lock()
        self._tickets: dict = {}
        self._uploads: dict = {}

    # ── 測試用 ────────────────────────────────────────────────
    def reset(self) -> None:
        with self._lock:
            self._tickets.clear()
            self._uploads.clear()

    def set_clock(self, clock: Callable[[], float],
                  wall: Optional[Callable[[], float]] = None) -> None:
        self._clock = clock
        if wall is not None:
            self._wall = wall

    def counts(self) -> dict:
        """只有計數（A2「暫存計數」的觀測點）；⛔ 不含任何鍵或位元組。"""
        with self._lock:
            self._sweep_locked(self._clock())
            states = [u.state for u in self._uploads.values()]
            return {
                "tickets": len(self._tickets),
                "uploads": len(self._uploads),
                STATE_UNREFERENCED: states.count(STATE_UNREFERENCED),
                STATE_CLAIMED: states.count(STATE_CLAIMED),
                STATE_RETAINED: states.count(STATE_RETAINED),
                "bytes": sum(u.size for u in self._uploads.values()),
            }

    # ── 回收 ──────────────────────────────────────────────────
    def sweep(self) -> int:
        with self._lock:
            return self._sweep_locked(self._clock())

    def _sweep_locked(self, now: float) -> int:
        removed = 0
        for sel in [s for s, u in self._uploads.items() if now >= u.expires_at]:
            del self._uploads[sel]
            removed += 1
        # 過期的票多留一個票期，才分得出「過期」與「不存在」（兩者都是 401）。
        grace = LIMITS.upload_ticket_ttl_s
        for sel in [s for s, t in self._tickets.items() if now >= t.expires_at + grace]:
            del self._tickets[sel]
        return removed

    # ── ① 發票 ────────────────────────────────────────────────
    def issue_ticket(self, binding: UploadBinding) -> IssuedTicket:
        if binding.purpose not in ACCEPT:
            raise UploadBindingError("unknown purpose")
        ttl = LIMITS.upload_ticket_ttl_s
        max_files = max_files_for(binding.purpose)
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            selector = self._new_selector_locked(self._tickets)
            verifier = secrets.token_urlsafe(_VERIFIER_BYTES)
            self._tickets[selector] = _Ticket(
                binding=binding, digest=_digest(verifier),
                expires_at=now + ttl, max_files=max_files,
            )
            expires_epoch = int(self._wall() + ttl)
        return IssuedTicket(
            upload_token=f"{TICKET_PREFIX}{selector}.{verifier}",
            expires_at=expires_epoch,
            max_files=max_files,
            max_bytes=LIMITS.upload_max_bytes,
            accept=tuple(ACCEPT[binding.purpose]),
        )

    @staticmethod
    def _new_selector_locked(table: dict) -> str:
        while True:
            sel = secrets.token_hex(_SELECTOR_HEX_LEN // 2)
            if sel not in table:
                return sel

    # ── ② 驗票、上傳 ──────────────────────────────────────────
    def verify_ticket(self, token: Any) -> TicketHandle:
        parsed = _parse_token(token, TICKET_PREFIX)
        if parsed is None:
            raise UploadTokenInvalid()
        selector, verifier = parsed
        digest = _digest(verifier)
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            ticket = self._tickets.get(selector)
            if ticket is None or not hmac.compare_digest(ticket.digest, digest):
                raise UploadTokenInvalid()
            if now >= ticket.expires_at:
                raise UploadTokenExpired()
            return TicketHandle(selector=selector, binding=ticket.binding,
                                max_files=ticket.max_files)

    def has_capacity(self, handle: TicketHandle) -> bool:
        with self._lock:
            ticket = self._tickets.get(handle.selector)
            return ticket is not None and ticket.uploaded < ticket.max_files

    def add_upload(self, handle: TicketHandle, *, content_type: str,
                   data: bytes) -> UploadReceipt:
        """存一筆上傳。張數判斷與計數在同一把鎖內（原子）。"""
        if content_type not in ACCEPT.get(handle.binding.purpose, ()):
            raise ValueError("content_type not accepted")
        if len(data) > LIMITS.upload_max_bytes:
            raise ValueError("too large")
        sha = hashlib.sha256(data).hexdigest()
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            ticket = self._tickets.get(handle.selector)
            if ticket is None:
                raise UploadTokenInvalid()
            if now >= ticket.expires_at:
                raise UploadTokenExpired()
            if ticket.uploaded >= ticket.max_files:
                raise UploadLimitReached()
            ticket.uploaded += 1
            selector = self._new_selector_locked(self._uploads)
            verifier = secrets.token_urlsafe(_VERIFIER_BYTES)
            self._uploads[selector] = _Upload(
                binding=ticket.binding, digest=_digest(verifier),
                content_type=content_type, size=len(data), sha256=sha,
                data=bytes(data), expires_at=now + LIMITS.upload_ttl_s,
            )
        return UploadReceipt(
            upload_id=f"{UPLOAD_ID_PREFIX}{selector}.{verifier}",
            content_type=content_type, size=len(data), sha256=sha,
        )

    # ── ③ agent.turn 引用 ─────────────────────────────────────
    def _resolve_locked(self, upload_ids: list, binding: UploadBinding, now: float) -> list:
        seen: set = set()
        out = []
        for i, raw in enumerate(upload_ids):
            parsed = _parse_token(raw, UPLOAD_ID_PREFIX)
            if parsed is None:
                raise UploadRefError(i, None)
            selector, verifier = parsed
            rec = self._uploads.get(selector)
            if (
                rec is None
                or selector in seen
                or not hmac.compare_digest(rec.digest, _digest(verifier))
                or rec.state != STATE_UNREFERENCED
                or now >= rec.expires_at
                or rec.binding != binding
            ):
                raise UploadRefError(i, selector)
            seen.add(selector)
            out.append((selector, rec))
        return out

    def check(self, upload_ids: list, binding: UploadBinding) -> list:
        """只驗不取：全部有效 ⇒ 回每筆的 content_type（順序同輸入）；任一無效 ⇒
        `UploadRefError`（全有或全無）。"""
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            return [rec.content_type for _, rec in self._resolve_locked(upload_ids, binding, now)]

    def claim(self, upload_ids: list, binding: UploadBinding) -> list:
        """驗過即標為已引用（單次使用），回 `ClaimedUpload` 清單（順序同輸入）。"""
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            resolved = self._resolve_locked(upload_ids, binding, now)
            out = []
            for selector, rec in resolved:
                rec.state = STATE_CLAIMED
                out.append(ClaimedUpload(ref=selector, content_type=rec.content_type,
                                         data=rec.data, sha256=rec.sha256))
            return out

    def end_turn(self, refs: Iterable[str]) -> None:
        """引用它的 `agent.turn` 結束（不論成敗）：文件類即刪；修繕照片轉保留，
        等確認卡兌現或作廢時 `release`（UD-3），最遲 30 分鐘。"""
        with self._lock:
            for ref in refs:
                rec = self._uploads.get(ref)
                if rec is None or rec.state != STATE_CLAIMED:
                    continue
                if rec.binding.purpose == "document":
                    del self._uploads[ref]
                else:
                    rec.state = STATE_RETAINED

    def retain(self, refs: Iterable[str]) -> None:
        """把已引用的照片標為保留（UD-3 出卡時呼叫；`end_turn` 對修繕照片已自動做）。
        ⛔ 延長保存期限——到期仍以上傳起 30 分鐘為準。"""
        with self._lock:
            for ref in refs:
                rec = self._uploads.get(ref)
                if rec is not None and rec.state == STATE_CLAIMED:
                    rec.state = STATE_RETAINED

    def release(self, refs: Iterable[str]) -> None:
        """確認卡兌現或作廢 ⇒ 刪除（UD-3 接線）。"""
        with self._lock:
            for ref in refs:
                rec = self._uploads.get(ref)
                if rec is not None and rec.state in (STATE_CLAIMED, STATE_RETAINED):
                    del self._uploads[ref]

    # ── ④ UD-3：確認卡上的照片（重新編碼、兌現取回、釋放） ──────────
    def photo_source(self, original_sha256: str, binding: UploadBinding,
                     exclude_refs: Iterable[str] = ()) -> Optional[tuple]:
        """出卡時找照片建議裡那一張（以**原檔** sha256 對）：綁定六欄逐一等值、用途
        repair、狀態 claimed／retained、未過期 ⇒ `(ref, data, photo_sha256 或 None)`；
        找不到 ⇒ `None`。`exclude_refs`＝同一張卡已對到的 ref（同一張照片傳兩次時
        兩筆各自對一筆）。⛔ 不改任何狀態。"""
        if binding.purpose != "repair" or not isinstance(original_sha256, str):
            return None
        excluded = set(exclude_refs)
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            for ref, rec in self._uploads.items():
                if (
                    ref not in excluded
                    and rec.binding == binding
                    and rec.state in (STATE_CLAIMED, STATE_RETAINED)
                    and hmac.compare_digest(rec.sha256, original_sha256)
                ):
                    return (ref, rec.data, rec.photo_sha256)
            return None

    def set_photo(self, ref: str, binding: UploadBinding, jpeg: bytes) -> Optional[str]:
        """把重新編碼後的 JPEG 存回同一筆（原檔位元組丟掉）⇒ 回它的 sha256。

        已編過 ⇒ ⛔ 再換，回既有的 sha256（同一筆不會有兩份不同的「卡上那一份」）。
        綁定不符、不在 claimed／retained、過期、不是 JPEG、超過上限 ⇒ `None`。"""
        if not isinstance(jpeg, (bytes, bytearray)) or sniff_content_type(jpeg) != "image/jpeg":
            return None
        if len(jpeg) > LIMITS.upload_max_bytes:
            return None
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            rec = self._uploads.get(ref)
            if (rec is None or rec.binding != binding
                    or rec.state not in (STATE_CLAIMED, STATE_RETAINED)):
                return None
            if rec.photo_sha256 is not None:
                return rec.photo_sha256
            rec.data = bytes(jpeg)
            rec.size = len(rec.data)
            rec.content_type = "image/jpeg"
            rec.photo_sha256 = hashlib.sha256(rec.data).hexdigest()
            return rec.photo_sha256

    def photo_bytes(self, photo_sha256: str, binding: UploadBinding,
                    exclude_refs: Iterable[str] = ()) -> Optional[tuple]:
        """兌現時取回卡上那一張（以**重新編碼後**的 sha256 對）⇒ `(ref, data)`；綁定不符、
        未編過、不在 claimed／retained、過期、不存在 ⇒ `None`。呼叫端仍須自己重算
        sha256 比對（S5：⛔ 只信這裡的查表）。"""
        if binding.purpose != "repair" or not isinstance(photo_sha256, str):
            return None
        excluded = set(exclude_refs)
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            for ref, rec in self._uploads.items():
                if (
                    ref not in excluded
                    and rec.binding == binding
                    and rec.state in (STATE_CLAIMED, STATE_RETAINED)
                    and rec.photo_sha256 is not None
                    and hmac.compare_digest(rec.photo_sha256, photo_sha256)
                ):
                    return (ref, rec.data)
            return None

    def release_photos(self, photo_sha256s: Iterable[str], binding: UploadBinding) -> int:
        """確認卡兌現或作廢 ⇒ 刪掉這張卡引用的照片（以重新編碼後的 sha256 對、綁定
        六欄逐一等值）。回刪了幾筆。⛔ 動別人的、⛔ 動文件類。"""
        wanted = [s for s in photo_sha256s if isinstance(s, str)]
        if binding.purpose != "repair" or not wanted:
            return 0
        removed = 0
        with self._lock:
            for sha in wanted:
                for ref, rec in list(self._uploads.items()):
                    if (
                        rec.binding == binding
                        and rec.state in (STATE_CLAIMED, STATE_RETAINED)
                        and rec.photo_sha256 is not None
                        and hmac.compare_digest(rec.photo_sha256, sha)
                    ):
                        del self._uploads[ref]
                        removed += 1
                        break
        return removed

    def retained(self, ref: str, binding: UploadBinding) -> Optional[ClaimedUpload]:
        """UD-3 兌現時取回保留中的照片；綁定不符、不在保留狀態、過期 ⇒ `None`。"""
        with self._lock:
            now = self._clock()
            self._sweep_locked(now)
            rec = self._uploads.get(ref)
            if rec is None or rec.state != STATE_RETAINED or rec.binding != binding:
                return None
            return ClaimedUpload(ref=ref, content_type=rec.content_type,
                                 data=rec.data, sha256=rec.sha256)


#: 行程內單例（S12：直傳只在單一 worker 啟用）。
STORE = UploadStore()

#: 背景回收間隔（秒）。到期判斷本身在每次操作時也會跑一次；這裡只是讓沒人碰的
#: 暫存也準時被刪。
SWEEP_INTERVAL_S = 60.0
