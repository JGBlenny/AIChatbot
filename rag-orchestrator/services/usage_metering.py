"""usage-metering 歸集器（spec usage-metering 任務 1.2/1.3）。

以 contextvar 承載「本請求」的計量狀態：middleware 進場 begin、
llm_provider 尾端 add_llm_usage、chat 流程 set_path、出場/串流 finally
finalize（冪等，雙落點只寫一次）→ asyncio.create_task fire-and-forget 寫
usage_events。任何失敗只 log，不得影響回答（R1.3）。

鐵律：不存問題原文與回答全文（R7，只存 message_len）；
USAGE_METERING_ENABLED=false 時全鏈 no-op（R8.2）；
token 只計經 llm_provider 統一出口者（embedding 自建不計）。
"""
import asyncio
import contextvars
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TPE = timezone(timedelta(hours=8))          # Asia/Taipei 日界（research 裁決）
_ctx: contextvars.ContextVar = contextvars.ContextVar("usage_ctx", default=None)

# ── 單價表（USD / 1M tokens，(prompt, completion)）；env LLM_PRICING_PATH 外部 JSON 覆蓋 ──
DEFAULT_PRICING: Dict[str, tuple] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}


def _pricing() -> Dict[str, tuple]:
    path = os.getenv("LLM_PRICING_PATH", "").strip()
    table = dict(DEFAULT_PRICING)
    if path:
        try:
            with open(path, encoding="utf-8") as f:
                ext = json.load(f)
            for m, v in ext.items():
                table[m] = (float(v["prompt"]), float(v["completion"]))
        except Exception as e:  # 設定壞不擋計量，缺價=成本留空
            logger.warning(f"[usage] 單價表載入失敗（沿用內建）：{e}")
    return table


# ── 內部流量判定（R3.2；規則表驅動可增補）──
_SMOKE_PREFIXES = ("smoke_", "verify_", "probe_", "demo_", "fp_", "fp2_",
                   "reg_", "vgap", "bill_diag_e2e", "dev_", "web_meter_", "web_it_",
                   "aggtest_")
INTERNAL_RULES = [
    ("backtest", lambda r: (r.get("session_id") or "").startswith("backtest_")),
    ("backtest", lambda r: bool(r.get("disable_answer_synthesis")) or bool(r.get("skip_sop"))),
    ("loop",     lambda r: (r.get("session_id") or "").startswith(("loop_", "kcl_"))),
    ("smoke",    lambda r: (r.get("session_id") or "").startswith(_SMOKE_PREFIXES)),
]

_KNOWN_USER_TYPES = ("tenant", "landlord", "property_manager", "system_admin", "prospect")


@dataclass
class UsageContext:
    request_id: str
    ts: datetime
    vendor_id: Optional[int] = None
    mode: Optional[str] = None
    target_user: Optional[str] = None
    user_type: str = "unknown"
    role_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    channel: str = "web"
    is_internal: bool = False
    internal_kind: Optional[str] = None
    message_len: int = 0
    processing_path: Optional[str] = None
    answer_source: Optional[str] = None
    status: str = "success"
    http_status: Optional[int] = None
    duration_ms: Optional[int] = None
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    est_cost_usd: Optional[Decimal] = None
    model_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)
    _t0: float = 0.0
    _finalized: bool = False


def is_enabled() -> bool:
    return os.getenv("USAGE_METERING_ENABLED", "true").lower() != "false"


def begin(fields: Dict[str, Any]) -> None:
    """middleware 進場：建 context（含內部流量判定與 user_type 推導）。"""
    if not is_enabled():
        _ctx.set(None)
        return
    is_internal, kind = False, None
    for k, pred in INTERNAL_RULES:
        try:
            if pred(fields):
                is_internal, kind = True, k
                break
        except Exception:
            continue
    tu = fields.get("target_user")
    if tu in _KNOWN_USER_TYPES:
        user_type = tu
    elif fields.get("mode") == "b2b" and not fields.get("role_id") and not is_internal:
        user_type = "prospect"                       # 生產推導慣例：b2b＋無 role_id
    elif is_internal:
        user_type = "internal"                       # 內部且無形狀
    else:
        user_type = "unknown"
    _ctx.set(UsageContext(
        request_id=str(uuid.uuid4()),
        ts=datetime.now(timezone.utc),
        vendor_id=fields.get("vendor_id"),
        mode=fields.get("mode"),
        target_user=tu,
        user_type=user_type,
        role_id=fields.get("role_id"),
        user_id=fields.get("user_id"),
        session_id=fields.get("session_id"),
        channel=fields.get("channel") or "web",
        is_internal=is_internal,
        internal_kind=kind,
        message_len=len(fields.get("message") or ""),
        _t0=time.monotonic(),
    ))


def add_llm_usage(model: str, usage: Optional[Dict[str, Any]]) -> None:
    """llm_provider 統一出口尾端呼叫；無 context（非計量路徑）靜默略過。"""
    ctx = _ctx.get()
    if ctx is None or ctx._finalized:
        return
    pt = int((usage or {}).get("prompt_tokens") or 0)
    ct = int((usage or {}).get("completion_tokens") or 0)
    ctx.llm_calls += 1
    ctx.prompt_tokens += pt
    ctx.completion_tokens += ct
    mb = ctx.model_breakdown.setdefault(model, {"calls": 0, "pt": 0, "ct": 0})
    mb["calls"] += 1
    mb["pt"] += pt
    mb["ct"] += ct


def set_path(processing_path: Optional[str] = None, answer_source: Optional[str] = None) -> None:
    ctx = _ctx.get()
    if ctx is None:
        return
    if processing_path:
        ctx.processing_path = processing_path[:60]
    if answer_source:
        ctx.answer_source = answer_source[:40]


def _compute_cost(ctx: UsageContext) -> None:
    """按 model_breakdown 逐模型計價；任一模型缺價 → 整筆成本留空不臆造（R2.4）。"""
    if not ctx.model_breakdown:
        ctx.est_cost_usd = None
        return
    table = _pricing()
    total = Decimal("0")
    for model, mb in ctx.model_breakdown.items():
        price = table.get(model)
        if price is None:
            ctx.est_cost_usd = None
            return
        total += (Decimal(mb["pt"]) * Decimal(str(price[0]))
                  + Decimal(mb["ct"]) * Decimal(str(price[1]))) / Decimal(1_000_000)
    ctx.est_cost_usd = total.quantize(Decimal("0.000001"))


def _to_row(ctx: UsageContext) -> Dict[str, Any]:
    """事件列（不含原文——message_len 為唯一內容痕跡，R7.1）。"""
    return {
        "request_id": ctx.request_id,
        "ts": ctx.ts,
        "date_tpe": ctx.ts.astimezone(_TPE).date(),
        "vendor_id": ctx.vendor_id,
        "mode": ctx.mode,
        "target_user": ctx.target_user,
        "user_type": ctx.user_type,
        "role_id": ctx.role_id,
        "user_id": ctx.user_id,
        "session_id": ctx.session_id,
        "channel": ctx.channel,
        "is_internal": ctx.is_internal,
        "internal_kind": ctx.internal_kind,
        "message_len": ctx.message_len,
        "processing_path": ctx.processing_path,
        "answer_source": ctx.answer_source,
        "status": ctx.status,
        "http_status": ctx.http_status,
        "duration_ms": ctx.duration_ms,
        "llm_calls": ctx.llm_calls,
        "prompt_tokens": ctx.prompt_tokens,
        "completion_tokens": ctx.completion_tokens,
        "est_cost_usd": ctx.est_cost_usd,
        "model_breakdown": json.dumps(ctx.model_breakdown, ensure_ascii=False),
    }


async def _write_event(db_pool, row: Dict[str, Any]) -> None:
    cols = list(row.keys())
    sql = (f"INSERT INTO usage_events ({', '.join(cols)}) "
           f"VALUES ({', '.join(f'${i+1}' for i in range(len(cols)))}) "
           f"ON CONFLICT (request_id) DO NOTHING")
    async with db_pool.acquire() as conn:
        await conn.execute(sql, *row.values())


async def _safe_write(db_pool, row: Dict[str, Any]) -> None:
    try:
        await _write_event(db_pool, row)
    except Exception as e:                            # 寧漏勿堵（R1.3）
        logger.warning(f"[usage] 事件寫入失敗（丟棄）：{e}")


def finalize(status: str = "success", http_status: int = 200, db_pool=None) -> None:
    """冪等收尾：算成本、發 fire-and-forget 寫入。雙落點（middleware/串流 finally）安全。"""
    ctx = _ctx.get()
    if ctx is None or ctx._finalized:
        return
    ctx._finalized = True
    ctx.status = status
    ctx.http_status = http_status
    if ctx._t0:
        ctx.duration_ms = int((time.monotonic() - ctx._t0) * 1000)
    _compute_cost(ctx)
    if db_pool is None:
        logger.warning("[usage] finalize 無 db_pool，事件丟棄")
        return
    try:
        row = _to_row(ctx)

        async def _task():
            await _safe_write(db_pool, row)

        asyncio.create_task(_task())
    except Exception as e:                            # event loop 邊界等，皆不外拋
        logger.warning(f"[usage] finalize 失敗（丟棄）：{e}")


# ════════════════════════════════════════════════════════════
# quota-management（spec quota-management 任務 1）：團隊月額度檢查
# 沿本模組哲學：fail-open、內部流量豁免、Asia/Taipei 月界（滾動窗口免排程）。
# ════════════════════════════════════════════════════════════

_QUOTA_TTL_SEC = 60
_quota_cache: Dict[int, tuple] = {}      # vendor_id -> (QuotaState, row, fetched_monotonic)


@dataclass
class QuotaState:
    state: str            # 'none'|'ok'|'warn'|'blocked'
    used: int = 0
    quota: int = 0
    pct: int = 0


def _month_start_tpe():
    today = datetime.now(_TPE).date()
    return today.replace(day=1)


def _quota_state_from(row, used: int) -> "QuotaState":
    quota = int(row["monthly_message_quota"])
    pct = int(used * 100 / quota) if quota else 0
    if used >= quota:
        # 寬限模式（block_on_exceed=false）達限仍只警示（R4.4）
        state = "blocked" if row["block_on_exceed"] else "warn"
    elif pct >= int(row["warn_threshold_pct"]):
        state = "warn"
    else:
        state = "ok"
    return QuotaState(state, used, quota, min(pct, 999))


async def _quota_fetch(db_pool, vendor_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT monthly_message_quota, warn_threshold_pct, block_on_exceed, is_active "
            "FROM vendor_quotas WHERE vendor_id = $1", vendor_id)
        if not row or not row["is_active"]:
            return None, 0
        used = await conn.fetchval(
            "SELECT count(*) FROM usage_events "
            "WHERE vendor_id = $1 AND date_tpe >= $2 "
            "  AND is_internal = FALSE AND status <> 'blocked'",   # 攔截事件不計入額度（R4.6）
            vendor_id, _month_start_tpe())
        return row, int(used or 0)


async def quota_check(db_pool, vendor_id: Optional[int], is_internal: bool) -> "QuotaState":
    """額度狀態判定。內部流量/無 vendor/計量關閉 → 'none'（不計不攔，R2.2/R2.5）；
    任何例外 fail-open 回 'none'（R5.2）。60s 快取；**blocked 狀態不走快取**
    （直查——加值後第一句即恢復，R4.5）。"""
    if is_internal or not vendor_id or not is_enabled() or db_pool is None:
        return QuotaState("none")
    try:
        now = time.monotonic()
        cached = _quota_cache.get(vendor_id)
        if cached and (now - cached[2]) < _QUOTA_TTL_SEC and cached[0].state != "blocked":
            return cached[0]
        row, used = await _quota_fetch(db_pool, vendor_id)
        if row is None:
            qs = QuotaState("none")
        else:
            qs = _quota_state_from(row, used)
        _quota_cache[vendor_id] = (qs, row, now)
        return qs
    except Exception as e:
        logger.warning(f"[quota] 檢查失敗 fail-open：{e}")
        return QuotaState("none")


def quota_blocked_body(user_type: str, qs: "QuotaState", fields: Dict[str, Any]) -> Dict[str, Any]:
    """攔截回應（jgb2 前台只讀 answer——形狀對齊 VendorChatResponse 必填欄）。
    受眾分流（R4.2/R4.3）：pm 加值引導含數字；其餘中性文案零商業字眼。"""
    if user_type == "property_manager":
        answer = (f"本月 AI 客服對話額度已達上限（{qs.quota:,} 則）。\n"
                  f"如需繼續使用智慧客服，請聯繫金箍棒客服加值或調整方案，"
                  f"加值後服務將立即恢復。")
    else:
        answer = ("智慧客服暫停服務中，請聯繫您的管理公司，"
                  "或撥打客服專線由專人為您服務。")
    return {
        "answer": answer,
        "mode": fields.get("mode") or "b2c",
        "session_id": fields.get("session_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_count": 0,
        "action_type": "quota_blocked",
        "intent_name": None,
        "sources": [],
    }


def append_quota_hint(body_bytes: bytes, user_type: str, qs: "QuotaState") -> Optional[bytes]:
    """警示提示 append（R3.1–3.3）：僅 pm；answer 尾端附一行，其他欄位不動。
    非 JSON/無 answer/任何失敗 → None（呼叫端沿用原回應，警示丟失優於回應損毀）。"""
    if user_type != "property_manager":
        return None
    try:
        d = json.loads(body_bytes)
        if not isinstance(d, dict) or not d.get("answer"):
            return None
        d["answer"] += (f"\n\n──\n📊 本月 AI 客服額度已使用 {qs.pct}%"
                        f"（{qs.used:,}/{qs.quota:,}）")
        return json.dumps(d, ensure_ascii=False).encode()
    except Exception:
        return None
