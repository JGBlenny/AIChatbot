"""F12「名稱講不準時找得到」：寫入流程的物件／合約名稱查無時的寬鬆比對（前篩＋AI 挑選＋程式補齊）。

分工（DSP-091、DSP-110 甲′ 同型）：AI 只做「理解」——把使用者這句話對到**送出清單內**的編號；
何時呼叫、驗證、補齊、列候選、選定、出卡一律由程式。本模組只產「候選編號」，⛔ 選定、⛔ 出卡。

- `prefilter`：純函式。讀音單位（中文字＝整個無聲調音節，其他字元一字一單位）的最長共同子序列，
  名稱核心＝正名去【…】［…］與括號內文字；分數 ≥2 才入選、取前 `NAME_LENIENT_PRE_K`。
- `ai_pick`：一次模型呼叫。送模型的每列只有 `id`、`title`（`MODEL_ROW_KEYS` 等值斷言），名稱逐列過
  `sanitize_data_piece`、整份清單以 `wrap_tool_data`＋nonce 包住。輸出只經 `llm_output.final_segment`＋
  `iter_json_objects` 解析：恰好一個、只有 `ids` 鍵的物件；每項須為字串且精確等於送出清單內的編號；
  `none` 與編號混用 ⇒ 空；解析失敗、逾時、例外 ⇒ 空（⛔ 重試、⛔ fail-open）。
- `augment`：純函式。AI 所挑＋同名紀錄＋前篩分數不低於 AI 所挑最低分者，去重、上限 `NAME_LENIENT_CAP`；
  AI 回空 ⇒ 空。補齊只在**送模型的那份清單**內（候選 ⊆ 送模型清單）。
- `NameLenientTurn`：每回合一份（runtime 建立）——每回合寬鬆最多 1 次、結果依（動作、欄位、型別、
  名稱指紋）暫存，畫面清單與候選集 `ids` 取自同一份。
- 開關 `AGENT_NAME_LENIENT`（on／off；未設或空字串＝on；其他值 ⇒ `ValueError`）；生效＝開關 on 且
  `write_candidates_effective_from_env()`。
- log／trace 只記型別與筆數（`name_lenient:shown:estate:3`、`name_lenient:none`）；⛔ 記句子、名稱、
  編號或模型原始輸出。
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Final, List, Mapping, Optional, Sequence, Tuple

from pypinyin import lazy_pinyin

from services import usage_metering
from services.agent.completed_actions import sanitize_data_piece
from services.agent.llm_output import final_segment, iter_json_objects
from services.agent.prompt_assembler import new_nonce, wrap_tool_data
from services.agent.write_forms import write_candidates_effective_from_env

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 開關（`AGENT_NAME_LENIENT`）
# ---------------------------------------------------------------------------
NAME_LENIENT_ENV: Final[str] = "AGENT_NAME_LENIENT"


def name_lenient_enabled_from_env(environ: Optional[Mapping[str, str]] = None) -> bool:
    """`on`／`off`；**未設或空字串＝on**。其他非空值（如 `OFF`、`false`、`0`）⇒ `ValueError`
    （啟動失敗並說明原因；同 `write_candidates_enabled_from_env`）。"""
    env = os.environ if environ is None else environ
    raw = env.get(NAME_LENIENT_ENV, "")
    value = (raw or "").strip() or "on"
    if value == "on":
        return True
    if value == "off":
        return False
    raise ValueError(
        f"{NAME_LENIENT_ENV}={raw!r} 不在允許值域（on／off；未設或空字串＝on）"
    )


def name_lenient_effective_from_env(environ: Optional[Mapping[str, str]] = None) -> bool:
    """寬鬆比對生效＝`AGENT_NAME_LENIENT` on **且** A-2a 生效（`write_candidates_effective_from_env`）。
    呼叫當下讀（A-2a 關 ⇒ 不生效，結果只能是候選形狀）。"""
    return name_lenient_enabled_from_env(environ) and write_candidates_effective_from_env(environ)


# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
#: 前篩後送模型的列數上限。
NAME_LENIENT_PRE_K: Final[int] = 50
#: 寬鬆候選上限（AI 所挑＋補齊）。
NAME_LENIENT_CAP: Final[int] = 5
#: 前篩入選的最低分（共同讀音單位數）。
NAME_LENIENT_MIN_SCORE: Final[int] = 2
#: 寬鬆清單只取第一頁的列數上限（＝`get_estate_status` 的 `per_page`、合約端點 `MAX_PER_PAGE`）。
NAME_LENIENT_LIST_MAX: Final[int] = 200
#: 模型呼叫的 `max_completion_tokens`。
NAME_LENIENT_MAX_COMPLETION_TOKENS: Final[int] = 2000
#: 模型呼叫逾時上限（秒）；實際值另受本回合剩餘期限限制（`NameLenientTurn.remaining_s`）。
NAME_LENIENT_TIMEOUT_S: Final[float] = 6.0
#: 本回合剩餘期限扣掉這個餘裕才是可給模型呼叫的時間（≤0 ⇒ 不呼叫、得空）。
NAME_LENIENT_DEADLINE_MARGIN_S: Final[float] = 1.0
#: runtime 對帶寬鬆脈絡的 `confirm.request` 加長的 registry 逾時（秒）：模型呼叫＋一次清單查詢。
NAME_LENIENT_EXTRA_TOOL_TIMEOUT_S: Final[float] = NAME_LENIENT_TIMEOUT_S + 3.0
#: 逾時被取消 ⇒ prompt token 以輸入字元數估算（比照判讀閘 `STATE_CLAIM_CANCEL_CHARS_PER_TOKEN`）。
NAME_LENIENT_CANCEL_CHARS_PER_TOKEN: Final[float] = 1.1
#: 資料段標籤與 JSON schema 名稱。
NAME_LENIENT_DATA_LABEL: Final[str] = "name_lenient_list"
NAME_LENIENT_SCHEMA_NAME: Final[str] = "name_lenient_pick"
#: 送模型每列的鍵（白名單等值斷言；合約列含承租人電話／Email，⛔ 帶出）。
MODEL_ROW_KEYS: Final[Tuple[str, ...]] = ("id", "title")
#: AI 回「沒有對得上」的值。
NONE_ID: Final[str] = "none"
#: 編號形狀（同 `write_candidates.CANDIDATE_ID_RE`）。
_ID_RE: Final = re.compile(r"[A-Za-z0-9_-]{1,32}")

TYPE_ESTATE: Final[str] = "estate"
TYPE_CONTRACT: Final[str] = "contract"
NOUN_OF_TYPE: Final[Mapping[str, str]] = {TYPE_ESTATE: "物件", TYPE_CONTRACT: "合約"}

#: 系統句（清單放 nonce 資料段，不在句中）。
NAME_LENIENT_SYSTEM_PROMPT: Final[str] = (
    "下面是這位使用者在系統裡的{noun}清單（編號｜名稱）。使用者講名稱時可能用簡稱、漏字、錯字或同音字。"
    "判斷使用者這句話指的可能是清單中的哪幾筆{noun}，最可能的排前面，最多 5 筆；"
    "這句話沒有指稱任何{noun}、或清單裡沒有對得上的，回 [\"none\"]。只回 JSON。"
)

# ── 給人看的固定句（⛔ 回顯使用者原話）────────────────────────────────────
#: 有寬鬆候選時的候選前言。
NAME_LENIENT_LEAD_TEXT: Final[str] = "找不到完全相同的名稱，你是不是指下面這幾筆？"
#: 清單可能超過第一頁時接在前言後。
NAME_LENIENT_TRUNCATED_NOTE: Final[str] = "（只比對了前 200 筆）"
#: 寬鬆也落空。
NAME_NOT_FOUND_TEXT: Final[str] = "找不到這個名稱的物件／合約，請再確認名稱，或直接給編號。"

# ── trace 標記（只記型別與筆數）──────────────────────────────────────────────────────
V_NAME_LENIENT_PREFIX: Final[str] = "name_lenient:"
V_NAME_LENIENT_NONE: Final[str] = "name_lenient:none"
V_NAME_LENIENT_MODEL_FAILED: Final[str] = "name_lenient:model_failed"
V_NAME_LENIENT_LIST_FAILED: Final[str] = "name_lenient:list_failed"
V_NAME_LENIENT_NOT_FOUND_EXIT: Final[str] = "name_lenient:not_found_exit"


def shown_mark(cand_type: str, n: int) -> str:
    """`name_lenient:shown:<型別>:<筆數>`（⛔ 編號、⛔ 名稱）。"""
    return f"{V_NAME_LENIENT_PREFIX}shown:{cand_type}:{int(n)}"


# ---------------------------------------------------------------------------
# 前篩（純函式）
# ---------------------------------------------------------------------------
#: 名稱核心去掉的標籤：【…】、[…]／［…］（NFKC 前後皆收）與半形／全形括號內文字。
_TAG_RE: Final = re.compile(r"[【\[［][^】\]］]*[】\]］]|\([^)]*\)|（[^）]*）")


def units(text: Any) -> List[str]:
    """比對單位：NFKC、小寫，去掉標點（P）、空白（Z）、符號（S）、控制字元（C）；中文字（U+4E00～U+9FFF）
    轉成**整個無聲調音節**（`lazy_pinyin`），其他字元一字一單位。"""
    t = unicodedata.normalize("NFKC", text if isinstance(text, str) else "").lower()
    out: List[str] = []
    for ch in t:
        if unicodedata.category(ch)[0] in "PZSC":
            continue
        if "一" <= ch <= "鿿":
            out.append(lazy_pinyin(ch)[0])
        else:
            out.append(ch)
    return out


def lcs(a: Sequence[str], b: Sequence[str]) -> int:
    """最長共同子序列長度（單位數）。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def core_units(title: Any) -> List[str]:
    """名稱核心的比對單位：去【…】［…］與括號內文字；去完是空的 ⇒ 用整個名稱。"""
    raw = title if isinstance(title, str) else ""
    return units(_TAG_RE.sub("", raw)) or units(raw)


def row_id(row: Any) -> Optional[str]:
    """列上的編號 → 字串；形狀不合（含 bool、None）⇒ `None`。"""
    if not isinstance(row, Mapping):
        return None
    value = row.get("id")
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text if _ID_RE.fullmatch(text) else None


def row_title(row: Any) -> Optional[str]:
    if not isinstance(row, Mapping):
        return None
    title = row.get("title")
    return title if isinstance(title, str) and title.strip() else None


def prefilter(sentence: Any, rows: Sequence[Mapping[str, Any]],
              k: int = NAME_LENIENT_PRE_K) -> Tuple[List[str], Dict[str, int]]:
    """`(依分數排序的入選編號（≤k）, 入選編號 ⇒ 分數)`。

    分數＝名稱核心與整句的最長共同子序列（單位數）；≥`NAME_LENIENT_MIN_SCORE` 才入選；排序鍵＝
    （分數高、覆蓋率高、編號）。編號或名稱形狀不合的列、重複編號一律略過。"""
    s = units(sentence)
    scored: list = []
    seen: set = set()
    for row in rows:
        rid, title = row_id(row), row_title(row)
        if rid is None or title is None or rid in seen:
            continue
        seen.add(rid)
        core = core_units(title)
        m = lcs(core, s)
        if m >= NAME_LENIENT_MIN_SCORE:
            scored.append((-m, -(m / len(core)), rid))
    scored.sort()
    kept = scored[:max(0, int(k))]
    return [rid for _m, _c, rid in kept], {rid: -m for m, _c, rid in kept}


def model_rows(rows: Sequence[Mapping[str, Any]], ids: Sequence[str]) -> List[dict]:
    """送模型的列：只留 `ids` 內的列、依原清單順序、每列只有 `MODEL_ROW_KEYS`（`id` 為字串）。"""
    wanted = set(ids)
    out: List[dict] = []
    seen: set = set()
    for row in rows:
        rid, title = row_id(row), row_title(row)
        if rid is None or title is None or rid not in wanted or rid in seen:
            continue
        seen.add(rid)
        out.append({"id": rid, "title": title})
    return out


# ---------------------------------------------------------------------------
# AI 挑選
# ---------------------------------------------------------------------------
def pick_messages(sentence: Any, sent: Sequence[Mapping[str, Any]], cand_type: str,
                  nonce: str) -> list:
    """系統句（名詞依型別）＋nonce 資料段（每列 `編號｜名稱`，名稱過 `sanitize_data_piece`）＋使用者這句。"""
    for r in sent:
        if tuple(r.keys()) != MODEL_ROW_KEYS:      # 白名單等值斷言
            raise ValueError("送模型的列只能有 id、title 兩鍵")
    noun = NOUN_OF_TYPE[cand_type]
    listing = "\n".join(f"{r['id']}｜{sanitize_data_piece(r['title'])}" for r in sent)
    return [
        {"role": "system", "content": NAME_LENIENT_SYSTEM_PROMPT.format(noun=noun)},
        {"role": "user", "content": wrap_tool_data(NAME_LENIENT_DATA_LABEL, listing, nonce)},
        {"role": "user", "content": sentence if isinstance(sentence, str) else ""},
    ]


def pick_response_format(ids: Sequence[str]) -> dict:
    """`{"ids": [...]}`，enum＝送出清單內編號＋`none`（只當提示；程式自己驗）。"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": NAME_LENIENT_SCHEMA_NAME,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "ids": {"type": "array",
                            "items": {"type": "string", "enum": list(ids) + [NONE_ID]}},
                },
                "required": ["ids"],
                "additionalProperties": False,
            },
        },
    }


def parse_pick_content(content: Any, allowed_ids: Sequence[str]) -> List[str]:
    """模型輸出 → 清單內編號（保序、去重）；任何不合 ⇒ `[]`。

    - 只看最後一個 `</reasoning>` 之後（`final_segment`）；推理段未收尾 ⇒ `[]`；
    - 逐 `{` 解出的頂層值去重後須**恰好一個**、是 dict、鍵集合恰為 `{"ids"}`、`ids` 是 list；
    - 含 `none` ⇒ `[]`（`none` 單獨或與編號混用皆是）；
    - 每項須為字串且精確等於 `allowed_ids` 其中之一；清單外、型別不對、重複者丟棄。"""
    tail = final_segment(content)
    if tail is None:
        return []
    found: list = []
    for obj in iter_json_objects(tail):
        if obj not in found:
            found.append(obj)
    if len(found) != 1:
        return []
    obj = found[0]
    if not isinstance(obj, dict) or set(obj.keys()) != {"ids"}:
        return []
    ids = obj["ids"]
    if not isinstance(ids, list):
        return []
    if any(isinstance(i, str) and i == NONE_ID for i in ids):
        return []
    allowed = set(allowed_ids)
    out: List[str] = []
    for i in ids:
        if isinstance(i, str) and i in allowed and i not in out:
            out.append(i)
    return out


@dataclass(frozen=True)
class AiPick:
    """一次 AI 挑選的結果：`ids`（已驗證）、`failed`（例外／逾時／未呼叫）與 token。"""

    ids: Tuple[str, ...]
    failed: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0


async def ai_pick(create: Callable[..., Awaitable[Any]], *, model: str,
                  reasoning_effort: Optional[str], sentence: Any,
                  sent: Sequence[Mapping[str, Any]], cand_type: str, timeout_s: float) -> AiPick:
    """一次模型呼叫（⛔ 重試）。`sent`＝`model_rows` 的產出。`timeout_s ≤ 0` ⇒ 不呼叫、`failed`。
    token 經 `usage_metering.add_llm_usage` 計量並回傳；⛔ 記錄任何輸入或輸出原文。"""
    ids = [r["id"] for r in sent]
    if not ids or timeout_s <= 0:
        return AiPick((), True)
    messages = pick_messages(sentence, sent, cand_type, new_nonce())
    kwargs: dict = dict(
        model=model,
        messages=messages,
        response_format=pick_response_format(ids),
        max_completion_tokens=NAME_LENIENT_MAX_COMPLETION_TOKENS,
    )
    if reasoning_effort is not None:
        kwargs["extra_body"] = {"reasoning_effort": reasoning_effort}
    try:
        response = await asyncio.wait_for(create(**kwargs), timeout=timeout_s)
    except asyncio.TimeoutError:
        pt = int(sum(len(m["content"]) for m in messages) / NAME_LENIENT_CANCEL_CHARS_PER_TOKEN)
        usage_metering.add_llm_usage(model, {"prompt_tokens": pt, "completion_tokens": 0})
        return AiPick((), True, pt, 0)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — 任何例外 ⇒ 空（⛔ 記原文，只記類別名）
        logger.warning("name_lenient_model_failed exc=%s", type(exc).__name__)
        return AiPick((), True)
    usage = getattr(response, "usage", None)
    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    usage_metering.add_llm_usage(model, {"prompt_tokens": pt, "completion_tokens": ct})
    try:
        content = response.choices[0].message.content
    except Exception:  # noqa: BLE001 — 回應形狀不對 ⇒ 空
        content = None
    return AiPick(tuple(parse_pick_content(content, ids)), False, pt, ct)


# ---------------------------------------------------------------------------
# 補齊（純函式）
# ---------------------------------------------------------------------------
def augment(picks: Sequence[str], sent: Sequence[Mapping[str, Any]],
            scores: Mapping[str, int], cap: int = NAME_LENIENT_CAP) -> List[str]:
    """AI 所挑（保序）＋同名紀錄（送出清單順序）＋前篩分數不低於 AI 所挑最低分者（分數高者先），
    去重、上限 `cap`；AI 回空 ⇒ `[]`。一律只在 `sent`（送模型的清單）內補（候選 ⊆ 送模型清單）。"""
    sent_ids = [r["id"] for r in sent]
    in_sent = set(sent_ids)
    picks = [p for p in dict.fromkeys(picks) if p in in_sent and p in scores]
    if not picks:
        return []
    title = {r["id"]: r["title"] for r in sent}
    floor = min(scores[i] for i in picks)
    names = {title[i] for i in picks}
    same = [rid for rid in sent_ids if title[rid] in names and rid not in picks]
    extra = sorted((rid for rid in sent_ids if scores.get(rid, -1) >= floor and rid not in picks),
                   key=lambda rid: -scores[rid])
    return list(dict.fromkeys(picks + same + extra))[:max(0, int(cap))]


# ---------------------------------------------------------------------------
# 每回合脈絡
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LenientOutcome:
    """一次寬鬆比對的結果。`status`：`ok`（`ids` 可能為空＝找不到）／`error`（清單沒查成 ⇒ 呼叫端
    維持現行出口）。`rows_by_id`＝清單上的原始列（呼叫端再經 `minimize_row` 白名單）。"""

    status: str
    ids: Tuple[str, ...] = ()
    rows_by_id: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    truncated: bool = False
    sent_ids: Tuple[str, ...] = ()

    @classmethod
    def error(cls) -> "LenientOutcome":
        return cls("error")


@dataclass
class NameLenientTurn:
    """本回合的寬鬆比對脈絡（runtime 每回合建一份；⛔ 落地）。

    - `create_factory()`＝服務既有 provider 的 `chat.completions.create`（同 DSP-110 意圖呼叫、判讀閘；
      本模組 ⛔ 自讀金鑰）；在真的要呼叫時才取（取不到 ⇒ 當模型失敗、得空）；
    - `user_message`、`touched`：整句來源——名稱欄位本回合由使用者句子寫進（`touched` 含該欄位鍵）
      ⇒ 本句；否則用草稿裡既有的名稱欄值（⛔ 為此新存原句）；
    - `marks`：trace 標記寫到這份 list（runtime 傳本回合 violations）；
    - `on_usage(pt, ct)`：token 計入本回合；
    - 每回合寬鬆最多 1 次（`calls`）；同一鍵重問回同一份結果（畫面清單與候選集同源）。"""

    create_factory: Callable[[], Callable[..., Awaitable[Any]]]
    model: str
    reasoning_effort: Optional[str]
    user_message: str
    touched: Any
    remaining_s: Callable[[], float]
    marks: list
    on_usage: Optional[Callable[[int, int], None]] = None
    #: 每真的發出一次模型呼叫就叫一次（runtime 計入本回合 `llm_calls`）。
    on_model_call: Optional[Callable[[], None]] = None
    calls: int = 0
    model_calls: int = 0
    _cache: dict = field(default_factory=dict)
    _lock: Optional[asyncio.Lock] = None

    def sentence_for(self, field_key: str, name_value: Any) -> str:
        touched = self.touched if self.touched is not None else ()
        if field_key in touched and isinstance(self.user_message, str) and self.user_message.strip():
            return self.user_message
        return name_value if isinstance(name_value, str) else ""

    def _mark(self, mark: str) -> None:
        self.marks.append(mark)
        logger.info("[agent] %s", mark)

    async def run_once(self, key: Tuple[Any, ...],
                       compute: Callable[[], Awaitable[LenientOutcome]]) -> Optional[LenientOutcome]:
        """同一鍵 ⇒ 回暫存結果；本回合已跑過別的鍵 ⇒ `None`（呼叫端維持現行出口）；否則跑一次並暫存。"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if key in self._cache:
                return self._cache[key]
            if self.calls >= 1:
                return None
            self.calls += 1
            outcome = await compute()
            self._cache[key] = outcome
            return outcome

    async def pick(self, *, sentence: Any, rows: Sequence[Mapping[str, Any]], cand_type: str,
                   truncated: bool) -> LenientOutcome:
        """前篩 → AI 挑選（前篩為空 ⇒ ⛔ 呼叫模型）→ 補齊。標記只記型別與筆數。"""
        rows_by_id: Dict[str, Mapping[str, Any]] = {}
        for row in rows:
            rid = row_id(row)
            if rid is not None and row_title(row) is not None and rid not in rows_by_id:
                rows_by_id[rid] = row
        ranked, scores = prefilter(sentence, list(rows_by_id.values()))
        sent = model_rows(list(rows_by_id.values()), ranked)
        ids: List[str] = []
        if sent:
            try:
                create = self.create_factory()
            except Exception as exc:  # noqa: BLE001 — 取不到 client ⇒ 當模型失敗（⛔ fail-open）
                logger.warning("name_lenient_client_unavailable exc=%s", type(exc).__name__)
                create = None
            timeout = min(NAME_LENIENT_TIMEOUT_S, self.remaining_s() - NAME_LENIENT_DEADLINE_MARGIN_S)
            if create is None:
                picked = AiPick((), True)
            else:
                self.model_calls += 1
                if self.on_model_call is not None:
                    self.on_model_call()
                picked = await ai_pick(create, model=self.model, reasoning_effort=self.reasoning_effort,
                                       sentence=sentence, sent=sent, cand_type=cand_type,
                                       timeout_s=timeout)
            if self.on_usage is not None and (picked.prompt_tokens or picked.completion_tokens):
                self.on_usage(picked.prompt_tokens, picked.completion_tokens)
            if picked.failed:
                self._mark(V_NAME_LENIENT_MODEL_FAILED)
            ids = augment(picked.ids, sent, scores)
        self._mark(shown_mark(cand_type, len(ids)) if ids else V_NAME_LENIENT_NONE)
        return LenientOutcome("ok", tuple(ids), rows_by_id, bool(truncated),
                              tuple(r["id"] for r in sent))

    def list_failed(self) -> LenientOutcome:
        self._mark(V_NAME_LENIENT_LIST_FAILED)
        return LenientOutcome.error()


def lead_text(truncated: bool) -> str:
    """寬鬆候選前言（固定句；清單可能超過第一頁 ⇒ 接「只比對了前 200 筆」）。"""
    return NAME_LENIENT_LEAD_TEXT + (NAME_LENIENT_TRUNCATED_NOTE if truncated else "")


__all__ = [
    "NAME_LENIENT_ENV", "name_lenient_enabled_from_env", "name_lenient_effective_from_env",
    "NAME_LENIENT_PRE_K", "NAME_LENIENT_CAP", "NAME_LENIENT_MIN_SCORE", "NAME_LENIENT_LIST_MAX",
    "NAME_LENIENT_MAX_COMPLETION_TOKENS", "NAME_LENIENT_TIMEOUT_S", "NAME_LENIENT_DEADLINE_MARGIN_S",
    "NAME_LENIENT_EXTRA_TOOL_TIMEOUT_S", "NAME_LENIENT_CANCEL_CHARS_PER_TOKEN",
    "NAME_LENIENT_DATA_LABEL", "NAME_LENIENT_SCHEMA_NAME", "MODEL_ROW_KEYS", "NONE_ID",
    "TYPE_ESTATE", "TYPE_CONTRACT", "NOUN_OF_TYPE", "NAME_LENIENT_SYSTEM_PROMPT",
    "NAME_LENIENT_LEAD_TEXT", "NAME_LENIENT_TRUNCATED_NOTE", "NAME_NOT_FOUND_TEXT",
    "V_NAME_LENIENT_PREFIX", "V_NAME_LENIENT_NONE", "V_NAME_LENIENT_MODEL_FAILED",
    "V_NAME_LENIENT_LIST_FAILED", "V_NAME_LENIENT_NOT_FOUND_EXIT", "shown_mark",
    "units", "lcs", "core_units", "row_id", "row_title", "prefilter", "model_rows",
    "pick_messages", "pick_response_format", "parse_pick_content", "AiPick", "ai_pick",
    "augment", "LenientOutcome", "NameLenientTurn", "lead_text",
]
