"""DocuMind 建物謄本解析的呼叫端（站內幫手 S3，計畫 §3h 第 4 點＋DocuMind 安全審查 D1～D10）。

業主 2026-10-15：謄本欄位 ⛔ 由我方模型抽，改送 DocuMind（對接規格 2.4.0，
`POST {base}/analyze`、`document_type=transcript`）。本模組是那一條**對外送檔**路徑的
唯一出口，紀律如下（⛔ 不得為了某一次實測而放寬）：

  ① **設定 fail-closed（D1）**：`DOCUMIND_BASE_URL` 必須 `https`、⛔ userinfo／query／
     fragment，且另需 `DOCUMIND_TOKEN`（以 `Authorization` header 帶）才啟用。明文
     `http` 只准 env `DOCUMIND_INSECURE_TEST_HOST`（`host:port`）指定的那一台測試主機，
     且須另一個顯式開關 `DOCUMIND_ALLOW_INSECURE_TEST_HOST` 逐字為 `1`。其餘任何組合
     一律**視同未設＝功能關閉**。⚠️ 測試主機位址 ⛔ 寫進 repo（repo 公開，該主機明文、
     無認證）——只放部署環境的 env。
  ② **送出最少（D3／D6）**：只送呼叫端交來的那一份位元組（PDF 原檔或已重新編碼、
     去 EXIF 的 JPEG），multipart 檔名由程式產生、副檔名依 magic bytes；
     `enable_llm=false`。
  ③ **讀回最少（D5）**：`follow_redirects=False`、`trust_env=False`；串流讀回應、
     上限 `RESPONSE_MAX_BYTES`；非 JSON／缺鍵／型別不符＝錯誤（⛔ 改走掃描路徑）；
     ⛔ 不對整包回應建模型，只以 `dict.get` 走固定路徑取**有型別值**。
  ④ **其餘一律丟**：所有權部（所有權人、統編、住址）、他項權利、原文 `pages`／
     `transcripts`——本模組 ⛔ 讀那些鍵、⛔ 進回傳值、⛔ 進 log。
  ⑤ **log 只印例外類別名與 HTTP 狀態碼**（⛔ 網址、⛔ 回應內容、⛔ 欄位值）。
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# ① 設定（D1）
# ════════════════════════════════════════════════════════════════════
DOCUMIND_BASE_URL_ENV = "DOCUMIND_BASE_URL"
DOCUMIND_TOKEN_ENV = "DOCUMIND_TOKEN"
#: 明文 http 的**開關**（逐字 `"1"` 才算開；⛔ 收 `true`／`yes`／前後空白）。
DOCUMIND_INSECURE_TEST_HOST_ENV = "DOCUMIND_ALLOW_INSECURE_TEST_HOST"
#: 明文 http 唯一允許的測試主機 `host:port`（業主 2026-10-15：位址移出程式——repo 公開，
#: 該主機明文、無認證，⛔ 寫死在程式或測試裡）。未設／空／格式不合 ⇒ ⛔ 不准 http。
DOCUMIND_INSECURE_HOST_ENV = "DOCUMIND_INSECURE_TEST_HOST"

#: `host:port` 的唯一合法形狀：主機只收小寫英數、`.`、`-`（⛔ scheme、路徑、userinfo、
#: 空白、方括號）；連接埠 1～65535、⛔ 前導零。整串錨定、⛔ 去頭尾空白。
_INSECURE_HOST_RE = re.compile(r"([a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?):([1-9][0-9]{0,4})")


def insecure_test_host() -> Optional[tuple]:
    """`DOCUMIND_INSECURE_TEST_HOST` ⇒ `(host, port)`；未設、空字串、格式不合 ⇒ `None`。"""
    raw = os.getenv(DOCUMIND_INSECURE_HOST_ENV)
    if not raw:
        return None
    m = _INSECURE_HOST_RE.fullmatch(raw)
    if m is None:
        return None
    port = int(m.group(2))
    if port > 65535:
        return None
    return m.group(1), port

#: Token 只收 header 安全的可見 ASCII（⛔ 換行／空白——那會變成 header 注入）。
_TOKEN_RE = re.compile(r"[\x21-\x7e]{1,4096}")


@dataclass(frozen=True)
class DocuMindConfig:
    """已驗過的設定：`analyze_url`＝由解析後的成分**重組**的端點（⛔ 直接用原字串）。"""

    analyze_url: str
    token: Optional[str] = None


def documind_config() -> Optional[DocuMindConfig]:
    """讀 env 組設定；任何一項不合 ⇒ `None`（＝功能關閉，fail-closed）。"""
    raw = (os.getenv(DOCUMIND_BASE_URL_ENV) or "").strip()
    if not raw:
        return None
    if any(ch in raw for ch in ("?", "#", "@", " ", "\t", "\r", "\n")):
        return None
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if parsed.query or parsed.fragment:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    raw_token = (os.getenv(DOCUMIND_TOKEN_ENV) or "").strip()
    token = raw_token if raw_token and _TOKEN_RE.fullmatch(raw_token) else None
    if raw_token and token is None:
        return None                      # 給了一把形狀不對的 token ⇒ 關閉，⛔ 不靜默不帶
    path = parsed.path.rstrip("/")
    netloc = host if port is None else f"{host}:{port}"
    if parsed.scheme == "https":
        if token is None:
            return None
        return DocuMindConfig(analyze_url=f"https://{netloc}{path}/analyze", token=token)
    if parsed.scheme == "http":
        allow = os.getenv(DOCUMIND_INSECURE_TEST_HOST_ENV) == "1"
        allowed_host = insecure_test_host() if allow else None
        if allowed_host is not None and port is not None and (host, port) == allowed_host:
            return DocuMindConfig(analyze_url=f"http://{netloc}{path}/analyze", token=token)
    return None


# ════════════════════════════════════════════════════════════════════
# ② 送出（D3／D5／D6）
# ════════════════════════════════════════════════════════════════════
#: 回應串流讀取上限（D5）。
RESPONSE_MAX_BYTES = 4_000_000

#: 照片送 DocuMind 前重新編碼的長邊上限（OCR 要看得清楚字；仍去 EXIF）。
PHOTO_MAX_PX = 2400

#: 結果狀態的封閉值域。
DEED_STATUSES: frozenset = frozenset(
    {"ok", "not_deed", "multiple", "failed", "timeout", "disabled"}
)


@dataclass(frozen=True)
class DeedResult:
    """謄本解析的**封閉**結果：狀態＋`((estate_create 欄位, 值), …)`。⛔ 沒有任何原文。"""

    status: str
    typed_fields: tuple = ()

    def __post_init__(self) -> None:
        if self.status not in DEED_STATUSES:
            raise ValueError(f"DeedResult.status 只允許 {sorted(DEED_STATUSES)}")


def upload_name(data: bytes) -> Optional[tuple]:
    """依 **magic bytes** 決定 `(multipart 檔名, content-type)`；認不得 ⇒ `None`（⛔ 不送）。"""
    if not isinstance(data, (bytes, bytearray)):
        return None
    head = bytes(data[:8])
    if head.startswith(b"%PDF-"):
        return "deed.pdf", "application/pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "deed.jpg", "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "deed.png", "image/png"
    return None


def reencode_photo_jpeg(data: bytes, *, max_px: int = PHOTO_MAX_PX) -> bytes:
    """照片 ⇒ **重新編碼**的 JPEG（轉正方向、長邊 ≤ `max_px`、⛔ 帶 EXIF）（D3）。

    ⚠️ PIL 的 `Image.MAX_IMAGE_PIXELS` 解壓縮炸彈閘照樣生效（呼叫端接例外即放棄）。
    """
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)      # ⛔ 不傳 exif= ⇒ 輸出沒有 EXIF
    return buf.getvalue()


def _new_client(timeout_s: float) -> httpx.AsyncClient:
    # ⛔ `follow_redirects=False`、`trust_env=False` 都**顯式**（D5）：前者不讓對方把檔
    #    轉送到別處，後者不讓環境的 proxy／netrc 設定參與這一條對外路徑。
    return httpx.AsyncClient(
        follow_redirects=False, trust_env=False, timeout=httpx.Timeout(timeout_s)
    )


async def analyze_deed(
    data: bytes,
    *,
    timeout_s: float,
    pdf_pages: Optional[int] = None,
    config: Optional[DocuMindConfig] = None,
    client_factory: Optional[Callable[[float], httpx.AsyncClient]] = None,
) -> DeedResult:
    """送一份謄本給 DocuMind，回**封閉**結果。任何例外 ⇒ `failed`／`timeout`。

    `config` 缺省 ⇒ 當場讀 env（`documind_config()`）；`None` ⇒ `disabled`、⛔ 不連線。
    `pdf_pages`：送的是 PDF 時它的頁數（掃描路徑多頁不填，D7）；照片傳 `None`。
    """
    cfg = config if config is not None else documind_config()
    if cfg is None:
        return DeedResult("disabled")
    if not isinstance(timeout_s, (int, float)) or timeout_s <= 0:
        return DeedResult("timeout")
    named = upload_name(data)
    if named is None:
        return DeedResult("failed")
    filename, content_type = named
    headers = {"Accept": "application/json"}
    if cfg.token:
        headers["Authorization"] = f"Bearer {cfg.token}"
    factory = client_factory or _new_client

    async def _call() -> Any:
        async with factory(float(timeout_s)) as client:
            async with client.stream(
                "POST",
                cfg.analyze_url,
                headers=headers,
                files={"file": (filename, bytes(data), content_type)},
                data={"document_type": "transcript", "enable_llm": "false"},
            ) as response:
                if response.status_code != 200:
                    logger.warning("DocuMind 回應非 200：%d", int(response.status_code))
                    return None
                total = 0
                chunks: list = []
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > RESPONSE_MAX_BYTES:
                        logger.warning("DocuMind 回應超過上限，放棄")
                        return None
                    chunks.append(chunk)
        try:
            return json.loads(b"".join(chunks))
        except (ValueError, TypeError) as exc:
            logger.warning("DocuMind 回應不是 JSON：%s", type(exc).__name__)
            return None

    try:
        payload = await asyncio.wait_for(_call(), timeout=float(timeout_s))
    except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
        logger.warning("DocuMind 逾時：%s", type(exc).__name__)
        return DeedResult("timeout")
    except Exception as exc:  # noqa: BLE001 — 對外只回封閉狀態（D5）
        logger.warning("DocuMind 呼叫失敗：%s", type(exc).__name__)
        return DeedResult("failed")
    if payload is None:
        return DeedResult("failed")
    try:
        return extract_deed_fields(payload, pdf_pages=pdf_pages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DocuMind 回應取值失敗：%s", type(exc).__name__)
        return DeedResult("failed")


# ════════════════════════════════════════════════════════════════════
# ③ 取值（D4／D7～D10）——只走固定路徑、只取有型別值
# ════════════════════════════════════════════════════════════════════
#: 22 縣市 × 鄉鎮市區的**封閉對照表**（D8；官方寫法，縣市名用「臺」）。
CITY_DISTRICTS: dict = {
    "臺北市": ("中正區", "大同區", "中山區", "松山區", "大安區", "萬華區", "信義區",
             "士林區", "北投區", "內湖區", "南港區", "文山區"),
    "新北市": ("板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", "樹林區",
             "鶯歌區", "三峽區", "淡水區", "汐止區", "瑞芳區", "土城區", "蘆洲區",
             "五股區", "泰山區", "林口區", "深坑區", "石碇區", "坪林區", "三芝區",
             "石門區", "八里區", "平溪區", "雙溪區", "貢寮區", "金山區", "萬里區",
             "烏來區"),
    "桃園市": ("桃園區", "中壢區", "大溪區", "楊梅區", "蘆竹區", "大園區", "龜山區",
             "八德區", "龍潭區", "平鎮區", "新屋區", "觀音區", "復興區"),
    "臺中市": ("中區", "東區", "南區", "西區", "北區", "西屯區", "南屯區", "北屯區",
             "豐原區", "東勢區", "大甲區", "清水區", "沙鹿區", "梧棲區", "后里區",
             "神岡區", "潭子區", "大雅區", "新社區", "石岡區", "外埔區", "大安區",
             "烏日區", "大肚區", "龍井區", "霧峰區", "太平區", "大里區", "和平區"),
    "臺南市": ("新營區", "鹽水區", "白河區", "柳營區", "後壁區", "東山區", "麻豆區",
             "下營區", "六甲區", "官田區", "大內區", "佳里區", "學甲區", "西港區",
             "七股區", "將軍區", "北門區", "新化區", "善化區", "新市區", "安定區",
             "山上區", "玉井區", "楠西區", "南化區", "左鎮區", "仁德區", "歸仁區",
             "關廟區", "龍崎區", "永康區", "東區", "南區", "北區", "安南區", "安平區",
             "中西區"),
    "高雄市": ("新興區", "前金區", "苓雅區", "鹽埕區", "鼓山區", "旗津區", "前鎮區",
             "三民區", "楠梓區", "小港區", "左營區", "仁武區", "大社區", "岡山區",
             "路竹區", "阿蓮區", "田寮區", "燕巢區", "橋頭區", "梓官區", "彌陀區",
             "永安區", "湖內區", "鳳山區", "大寮區", "林園區", "鳥松區", "大樹區",
             "旗山區", "美濃區", "六龜區", "內門區", "杉林區", "甲仙區", "桃源區",
             "那瑪夏區", "茂林區", "茄萣區"),
    "基隆市": ("仁愛區", "信義區", "中正區", "中山區", "安樂區", "暖暖區", "七堵區"),
    "新竹市": ("東區", "北區", "香山區"),
    "嘉義市": ("東區", "西區"),
    "新竹縣": ("竹北市", "竹東鎮", "新埔鎮", "關西鎮", "湖口鄉", "新豐鄉", "芎林鄉",
             "橫山鄉", "北埔鄉", "寶山鄉", "峨眉鄉", "尖石鄉", "五峰鄉"),
    "苗栗縣": ("苗栗市", "頭份市", "苑裡鎮", "通霄鎮", "竹南鎮", "後龍鎮", "卓蘭鎮",
             "大湖鄉", "公館鄉", "銅鑼鄉", "南庄鄉", "頭屋鄉", "三義鄉", "西湖鄉",
             "造橋鄉", "三灣鄉", "獅潭鄉", "泰安鄉"),
    "彰化縣": ("彰化市", "員林市", "鹿港鎮", "和美鎮", "北斗鎮", "溪湖鎮", "田中鎮",
             "二林鎮", "線西鄉", "伸港鄉", "福興鄉", "秀水鄉", "花壇鄉", "芬園鄉",
             "大村鄉", "埔鹽鄉", "埔心鄉", "永靖鄉", "社頭鄉", "二水鄉", "田尾鄉",
             "埤頭鄉", "芳苑鄉", "大城鄉", "竹塘鄉", "溪州鄉"),
    "南投縣": ("南投市", "埔里鎮", "草屯鎮", "竹山鎮", "集集鎮", "名間鄉", "鹿谷鄉",
             "中寮鄉", "魚池鄉", "國姓鄉", "水里鄉", "信義鄉", "仁愛鄉"),
    "雲林縣": ("斗六市", "斗南鎮", "虎尾鎮", "西螺鎮", "土庫鎮", "北港鎮", "古坑鄉",
             "大埤鄉", "莿桐鄉", "林內鄉", "二崙鄉", "崙背鄉", "麥寮鄉", "東勢鄉",
             "褒忠鄉", "臺西鄉", "元長鄉", "四湖鄉", "口湖鄉", "水林鄉"),
    "嘉義縣": ("太保市", "朴子市", "布袋鎮", "大林鎮", "民雄鄉", "溪口鄉", "新港鄉",
             "六腳鄉", "東石鄉", "義竹鄉", "鹿草鄉", "水上鄉", "中埔鄉", "竹崎鄉",
             "梅山鄉", "番路鄉", "大埔鄉", "阿里山鄉"),
    "屏東縣": ("屏東市", "潮州鎮", "東港鎮", "恆春鎮", "萬丹鄉", "長治鄉", "麟洛鄉",
             "九如鄉", "里港鄉", "鹽埔鄉", "高樹鄉", "萬巒鄉", "內埔鄉", "竹田鄉",
             "新埤鄉", "枋寮鄉", "新園鄉", "崁頂鄉", "林邊鄉", "南州鄉", "佳冬鄉",
             "琉球鄉", "車城鄉", "滿州鄉", "枋山鄉", "三地門鄉", "霧臺鄉", "瑪家鄉",
             "泰武鄉", "來義鄉", "春日鄉", "獅子鄉", "牡丹鄉"),
    "宜蘭縣": ("宜蘭市", "頭城鎮", "羅東鎮", "蘇澳鎮", "礁溪鄉", "壯圍鄉", "員山鄉",
             "冬山鄉", "五結鄉", "三星鄉", "大同鄉", "南澳鄉"),
    "花蓮縣": ("花蓮市", "鳳林鎮", "玉里鎮", "新城鄉", "吉安鄉", "壽豐鄉", "光復鄉",
             "豐濱鄉", "瑞穗鄉", "富里鄉", "秀林鄉", "萬榮鄉", "卓溪鄉"),
    "臺東縣": ("臺東市", "成功鎮", "關山鎮", "卑南鄉", "鹿野鄉", "池上鄉", "東河鄉",
             "長濱鄉", "太麻里鄉", "大武鄉", "綠島鄉", "海端鄉", "延平鄉", "金峰鄉",
             "達仁鄉", "蘭嶼鄉"),
    "澎湖縣": ("馬公市", "湖西鄉", "白沙鄉", "西嶼鄉", "望安鄉", "七美鄉"),
    "金門縣": ("金城鎮", "金湖鎮", "金沙鎮", "金寧鄉", "烈嶼鄉", "烏坵鄉"),
    "連江縣": ("南竿鄉", "北竿鄉", "莒光鄉", "東引鄉"),
}
assert len(CITY_DISTRICTS) == 22, "縣市封閉表必須是 22 個"

#: 主要用途 ⇒ `use_for`（D10：**逐字完全相符**才對照；對不到 ⇒ `None`）。
USAGE_TO_USE_FOR: dict = {
    "住家用": "residential",
    "商業用": "business",
    "辦公室": "business",
    "店鋪": "business",
    "停車空間": "parking_space",
}

#: 掃描路徑單值欄位的信心門檻。
SCAN_MIN_CONFIDENCE = 0.85

#: 掃描路徑：這三個清單出現多個不同 `transcript_id` ⇒ 一份裡有多張謄本 ⇒ 不填（D7）。
SCAN_MULTI_TRANSCRIPT_KEYS: tuple = ("floor_area_checks", "shared_parts", "land_numbers")

#: 面積（平方公尺）合理範圍（同 `confirm_card` 的 `size` 欄位）。
_SIZE_LO, _SIZE_HI = 0, 100000

#: 門牌裡 ⛔ 該出現的標籤字樣（出現 ⇒ 多半是讀到別的欄位或夾帶，拒）。
_ADDRESS_LABEL_WORDS: tuple = (
    "所有權", "統一編號", "統編", "住址", "權利範圍", "地號", "建號", "登記",
    "面積", "用途", "門牌", "層次", "管理者", "出生", "謄本",
)

#: 門牌形狀（錨定；D7）：路段巷弄（中文與數字）＋門號「N號」（可帶 -N／之N）
#: ＋選填樓層「N樓」（可帶之N）。⛔ 空白、冒號、英文字母、附加姓名或證號。
_ADDRESS_RE = re.compile(
    r"^[一-鿿0-9]{1,40}?[0-9]+(?:-[0-9]+)?號(?:之[0-9]+)?"
    r"(?:(?:[0-9]+|[一二三四五六七八九十]+)樓(?:之[0-9]+)?)?$"
)

#: 樓層只認 `^[一二三四五六七八九十]+層$`（D10）。
_FLOOR_RE = re.compile(r"^([一二三四五六七八九十]+)層$")
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

_AREA_TEXT_RE = re.compile(r"^[0-9]{1,6}(?:\.[0-9]{1,2})?$")


def _norm_tai(text: str) -> str:
    """「台」視同「臺」（只用於比對縣市名，⛔ 不改寫門牌其他字）。"""
    return text.replace("台", "臺")


def jgb_city_name(city: str) -> str:
    """對照表的官方寫法（「臺」）⇒ **JGB 資料的寫法**（「台」）——只用在**輸出**。

    站內幫手 S3-live 修正 R2（主 session 裁示：寫入端改用 JGB 實際資料寫法）：JGB 錄製
    資料（`services/jgb/fixture_data/assistant_demo_vendor4.json` 的物件列）縣市一律寫
    「台」，送「臺北市」建物件會被以名稱解析的那一端回「無法辨識縣市／行政區」。
    ⚠️ 比對一律仍走 `_norm_tai`（台／臺視同），本函式 ⛔ 用在比對。
    """
    return city.replace("臺", "台")


def _city_prefix(text: str) -> Optional[str]:
    """字串開頭的縣市名（正規化後比對 22 縣市封閉表）；沒有 ⇒ `None`。"""
    norm = _norm_tai(text)
    for city in CITY_DISTRICTS:
        if norm.startswith(city):
            return city
    return None


def _clean_text(value: Any, max_len: int) -> Optional[str]:
    """字串欄位：經 `sanitize_data_piece` 後必須**逐字不變**（會被改動 ⇒ 拒）、限長（D10）。"""
    from services.agent.completed_actions import sanitize_data_piece

    if not isinstance(value, str):
        return None
    if sanitize_data_piece(value) != value:
        return None
    text = value.strip()
    if not text or len(text) > max_len:
        return None
    return text


def clean_address(value: Any, city: Optional[str], district: Optional[str]) -> Optional[str]:
    """建物門牌 ⇒ 去掉縣市／行政區前綴後的門牌；形狀不合 ⇒ `None`（D7）。

    先**驗**、再去前綴：前綴只認本份謄本導出的同一縣市／行政區；去完之後若開頭仍是
    任一縣市名（例如讀到所有權人住址那種別縣市的地址）⇒ 拒。
    """
    text = _clean_text(value, 100)
    if text is None:
        return None
    if any(ch.isspace() for ch in text) or ":" in text or "：" in text:
        return None
    if city is not None:
        city = _norm_tai(city)            # 呼叫端給「台」或「臺」都視同（R2）
    if city is not None and _norm_tai(text).startswith(city):
        text = text[len(city):]
        if district is not None and text.startswith(district):
            text = text[len(district):]
    if _city_prefix(text) is not None:
        return None
    if any(word in text for word in _ADDRESS_LABEL_WORDS):
        return None
    if not _ADDRESS_RE.fullmatch(text):
        return None
    return text


def _cn_number(text: str) -> Optional[int]:
    """「五」「十二」「二十三」⇒ 整數（1～99）；其他寫法 ⇒ `None`。"""
    if "十" not in text:
        return _CN_DIGITS.get(text) if len(text) == 1 else None
    if text.count("十") != 1:
        return None
    left, right = text.split("十")
    if len(left) > 1 or len(right) > 1:
        return None
    tens = 1 if left == "" else _CN_DIGITS.get(left)
    ones = 0 if right == "" else _CN_DIGITS.get(right)
    if tens is None or ones is None:
        return None
    return tens * 10 + ones


def floor_text(level: Any) -> Optional[str]:
    """「五層」⇒「5樓」；不合 `^[一二三四五六七八九十]+層$` ⇒ `None`（D10）。"""
    if not isinstance(level, str):
        return None
    m = _FLOOR_RE.fullmatch(level.strip())
    if m is None:
        return None
    n = _cn_number(m.group(1))
    return f"{n}樓" if n else None


def _area_number(value: Any) -> Optional[float]:
    """電子路徑的總面積（數字）：型別與範圍檢查（D10）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not (_SIZE_LO < value <= _SIZE_HI):
        return None
    return float(value)


def _area_text(value: Any) -> Optional[float]:
    """掃描路徑的總面積（字串）⇒ 數字；形狀不合 ⇒ `None`。"""
    if not isinstance(value, str) or not _AREA_TEXT_RE.fullmatch(value.strip()):
        return None
    number = float(value.strip())
    return number if _SIZE_LO < number <= _SIZE_HI else None


def _use_for(value: Any) -> Optional[str]:
    return USAGE_TO_USE_FOR.get(value) if isinstance(value, str) else None


def _pairs(**values: Any) -> tuple:
    """依固定順序回 `((欄位, 值), …)`，只留有值的欄位。"""
    order = ("city", "district", "address", "use_for", "size", "floor")
    return tuple((k, values[k]) for k in order if values.get(k) is not None)


class _ShapeError(Exception):
    """回應缺鍵／型別不符（D5：＝錯誤，⛔ 改走掃描路徑）。"""


def _require(obj: Any, key: str, kind: type) -> Any:
    if not isinstance(obj, dict):
        raise _ShapeError()
    value = obj.get(key)
    if not isinstance(value, kind):
        raise _ShapeError()
    return value


def extract_deed_fields(payload: Any, *, pdf_pages: Optional[int] = None) -> DeedResult:
    """DocuMind 回應 ⇒ 封閉結果。**純函式**（⛔ I/O、⛔ log 欄位值）。

    電子謄本（`transcript_records` 恰 1 筆且 `標示部` 非 null）：`類型` 必須是「建物」
    （D8／D9），取 `city`（資料管轄機關開頭的縣市）、`district`（謄本.行政區；與縣市
    一起對封閉表，對不上兩者皆不填）、`address`、`use_for`、`size`、`floor`。
    掃描／拍照（空殼或 `標示部` 為 null）：`building_address` 有值才算謄本（D9）；
    只取不在 `needs_confirmation` 且信心 ≥ 0.85 的 `building_address`／`main_usage`／
    `total_area`，⛔ 不取 `floor`、`city`、`district`；多張謄本或 PDF 超過 1 頁 ⇒ 不填（D7）。
    """
    try:
        fields = _require(payload, "document_fields", dict)
        records = _require(fields, "transcript_records", list)
    except _ShapeError:
        return DeedResult("failed")
    if len(records) > 1:
        return DeedResult("multiple")
    record = records[0] if records else None
    if record is not None and not isinstance(record, dict):
        return DeedResult("failed")
    label = record.get("標示部") if record is not None else None
    if label is not None and not isinstance(label, dict):
        return DeedResult("failed")
    try:
        if isinstance(label, dict):
            return _electronic(record, label)
        return _scanned(fields, pdf_pages)
    except _ShapeError:
        return DeedResult("failed")


def _electronic(record: dict, label: dict) -> DeedResult:
    if record.get("類型") != "建物":
        return DeedResult("not_deed")
    header = _require(record, "謄本", dict)
    office = header.get("資料管轄機關")
    city = _city_prefix(office) if isinstance(office, str) else None
    district_raw = _clean_text(header.get("行政區"), 20)
    district = None
    if city is not None and district_raw is not None and district_raw in CITY_DISTRICTS[city]:
        district = district_raw
    else:
        city = None                       # D8：對不上封閉表 ⇒ 兩者皆不填、追問
    floor = None
    levels = label.get("層次")
    if isinstance(levels, list) and len(levels) == 1 and isinstance(levels[0], dict):
        floor = floor_text(levels[0].get("層次"))
    return DeedResult("ok", _pairs(
        city=jgb_city_name(city) if city is not None else None,     # 輸出用 JGB 寫法（R2）
        district=district,
        address=clean_address(label.get("建物門牌"), city, district),
        use_for=_use_for(label.get("主要用途")),
        size=_area_number(label.get("總面積")),
        floor=floor,
    ))


def _scanned(fields: dict, pdf_pages: Optional[int]) -> DeedResult:
    raw_address = fields.get("building_address")
    if not isinstance(raw_address, str) or not raw_address.strip():
        return DeedResult("not_deed")     # D9：掃描件連門牌都沒有 ⇒ 不當謄本
    confidences = _require(fields, "field_confidences", dict)
    needs = _require(fields, "needs_confirmation", list)
    ids: set = set()
    for key in SCAN_MULTI_TRANSCRIPT_KEYS:
        for item in _require(fields, key, list):
            if isinstance(item, dict) and isinstance(item.get("transcript_id"), str):
                ids.add(item["transcript_id"])
    if len(ids) > 1 or (isinstance(pdf_pages, int) and pdf_pages > 1):
        return DeedResult("ok")           # 是謄本，但可能多張／多頁 ⇒ 一欄都不填（D7）

    def _confident(key: str) -> bool:
        conf = confidences.get(key)
        return (
            key not in needs
            and isinstance(conf, (int, float)) and not isinstance(conf, bool)
            and conf >= SCAN_MIN_CONFIDENCE
        )

    return DeedResult("ok", _pairs(
        address=clean_address(raw_address, None, None) if _confident("building_address") else None,
        use_for=_use_for(fields.get("main_usage")) if _confident("main_usage") else None,
        size=_area_text(fields.get("total_area")) if _confident("total_area") else None,
    ))


__all__ = [
    "CITY_DISTRICTS",
    "DEED_STATUSES",
    "DOCUMIND_BASE_URL_ENV",
    "DOCUMIND_INSECURE_TEST_HOST_ENV",
    "DOCUMIND_TOKEN_ENV",
    "DeedResult",
    "DocuMindConfig",
    "DOCUMIND_INSECURE_HOST_ENV",
    "insecure_test_host",
    "PHOTO_MAX_PX",
    "RESPONSE_MAX_BYTES",
    "USAGE_TO_USE_FOR",
    "analyze_deed",
    "clean_address",
    "documind_config",
    "extract_deed_fields",
    "floor_text",
    "jgb_city_name",
    "reencode_photo_jpeg",
    "upload_name",
]
