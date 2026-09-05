"""`ToolRegistry`（spec agentic-mcp-orchestration・任務 1.3）。

守門在 `ToolRegistry.call()` 這一層，MCP 門面（任務 1.7）只是薄包裝。
見 `.kiro/specs/agentic-mcp-orchestration/design.md` 元件 2、附錄 B 不變量 18。

**速率限制 key（⛔ 不用呼叫方字串／session_id）**：`(identity.api_key_id,
identity.vendor_id)`。換 `session_id` 不重置計數——同一把 API key 對同一
業者的呼叫共用一個桶，這是刻意設計（防止用換 session 繞過額度）。

**`call()` 守門四步骨架**（design 元件 2；本檔逐步照做）：
⓪身分鍵剝除（1.10 P2，⛔ 勿刪）：不變量 18／27 只在 `register()` 擋**spec 側**，
  擋不到**呼叫端**夾帶。`call()` 一律把 `_IDENTITY_KEYS` 從 `args` 剝掉並記
  `IDENTITY_KEY:<鍵>` 到 `last_violations()`。⛔ 不回 `INVALID_INPUT`——那等於
  告訴模型「你剛才踩到我們在擋的東西」，把守門規則洩出去。
①可見性（`specs_for` 名單，不含 ⇒ `NO_MATCH` 並在 trace 記 `FORBIDDEN`）
②`scope=="write"`：`readonly_view=True` 時一律 `NO_MATCH`；否則 args 缺
  `confirmation_token`（token 驗證本身是任務 2.4 的事，這裡只查存在）⇒
  `CONFIRMATION_REQUIRED`
③速率：每分鐘 ≤ `RATE_PER_MIN`（env，預設 60）；`kb.get` 另外每小時
  ≤ `KB_GET_CAP`（env，預設 300）⇒ `RATE_LIMITED`
④`input_schema` 驗證失敗 ⇒ `INVALID_INPUT`
再 `asyncio.wait_for(fn(identity, args), timeout_s)`：逾時 ⇒ `TOOL_TIMEOUT`。

**fn 拋例外的決定（⛔ 不是 TOOL_TIMEOUT、⛔ 不是 INVALID_INPUT）**：
一律 `ok=False, error="NO_MATCH"`，並在 trace 記 `"EXC:<例外類名>"`。
理由：對模型的錯誤語彙只有 design 列的五個 `ToolResult.error` 值，多一個
「工具內部炸了」的第六個值等於把實作細節（會不會有 traceback、是哪個
例外）洩給模型；`NO_MATCH` 對模型是「這條路走不通」，語意上最接近、
且不會誘使模型去猜測後端狀態。真正的除錯落在 trace 的 `EXC:` 前綴，
不落在對模型可見的 `error` 值域。

**違規／例外記錄（二選一：這裡選 `last_violations()`，⛔ 不額外加
`trace_note` 欄位到 `ToolResult`）**：`ToolResult` 是 design 定義的封閉
schema，不節外生枝加欄位；違規改記在 registry 內部的 `_violations` 清單，
供呼叫端（未來 `AgentRuntime`／測試）事後查閱。
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import (
    Any,
    Awaitable,
    Callable,
    Literal,
    Optional,
    TypedDict,
)

from pydantic import BaseModel

from services.agent.identity import STAGE_ORDER, Audience, Identity, Stage

ToolError = Literal[
    "NO_MATCH",
    "TOOL_TIMEOUT",
    "CONFIRMATION_REQUIRED",
    "INVALID_INPUT",
    "RATE_LIMITED",
]

# 不變量 18／audit 27：ToolSpec.input_schema 不得含這六個身分鍵（register() 內擋），
# 且 `call()` 一律從 args 剝掉同一組鍵（1.10 P2）——同一個常數，⛔ 不得各有一份。
_IDENTITY_KEYS = frozenset(
    {"vendor_id", "role_id", "user_id", "target_user", "mode", "viewer_user_id"}
)

_DEFAULT_RATE_PER_MIN = 60
_DEFAULT_KB_GET_CAP = 300
_MINUTE_S = 60.0
_HOUR_S = 3600.0


class Provenance(BaseModel):
    source: str
    text: str
    citable: bool = True


class ToolResult(BaseModel):
    ok: bool
    data: Optional[dict] = None
    error: Optional[ToolError] = None
    provenance: list[Provenance] = []
    text_for_model: str = ""


class ToolSpec(TypedDict, total=False):
    name: str
    description: str
    input_schema: dict
    output_model: type[BaseModel]
    scope: Literal["read", "write"]
    stage: dict[Audience, Stage]
    facade_only: bool  # 預設 False；1.4.1：True ⇒ 只由 MCP 門面呼叫
    mutates_session: bool  # 預設 False；DSP-016：True ⇒ 會寫 session 狀態（slots／token 表），影子 readonly_view 不可見


ToolFn = Callable[[Identity, dict], Awaitable[ToolResult]]


def _stage_le(a: Stage, b: Stage) -> bool:
    """`a <= b`（Stage 全序，見 identity.STAGE_ORDER）。"""
    return STAGE_ORDER.index(a) <= STAGE_ORDER.index(b)


def _validate_against_schema(schema: dict, args: Any) -> Optional[str]:
    """JSON-Schema 子集驗證（⛔ 專案未安裝 `jsonschema` 套件，見任務回報）。

    只支援本 spec 工具實際會用到的形狀：`type`（object/string/integer/
    number/boolean/array）、`properties`、`required`、`enum`、
    `maximum`／`minimum`、`additionalProperties`（bool）、`items`（array 的
    元素 schema，遞迴）。回傳 `None` 表示通過，否則回傳失敗原因字串。
    """
    return _validate_value(schema, args, path="$")


_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
}


def _validate_value(schema: dict, value: Any, *, path: str) -> Optional[str]:
    expected_type = schema.get("type")
    if expected_type is not None:
        py_types = _TYPE_MAP.get(expected_type)
        if py_types is None:
            return f"{path}: unsupported schema type {expected_type!r}"
        # bool 是 int 的子類別；「integer」/「number」不得誤收 bool。
        if expected_type in ("integer", "number") and isinstance(value, bool):
            return f"{path}: expected {expected_type}, got bool"
        if not isinstance(value, py_types):
            return f"{path}: expected {expected_type}, got {type(value).__name__}"

    if "enum" in schema and value not in schema["enum"]:
        return f"{path}: {value!r} not in enum {schema['enum']!r}"

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "maximum" in schema and value > schema["maximum"]:
            return f"{path}: {value} > maximum {schema['maximum']}"
        if "minimum" in schema and value < schema["minimum"]:
            return f"{path}: {value} < minimum {schema['minimum']}"

    if isinstance(value, str):
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            return f"{path}: length {len(value)} > maxLength {schema['maxLength']}"
        if "minLength" in schema and len(value) < schema["minLength"]:
            return f"{path}: length {len(value)} < minLength {schema['minLength']}"

    if expected_type == "object" or (expected_type is None and isinstance(value, dict)):
        if not isinstance(value, dict):
            return None  # type 已在上面擋過非 object 的情況
        properties = schema.get("properties", {})
        for required_key in schema.get("required", []):
            if required_key not in value:
                return f"{path}: missing required key {required_key!r}"
        if schema.get("additionalProperties") is False:
            extra = set(value.keys()) - set(properties.keys())
            if extra:
                return f"{path}: additional properties not allowed: {sorted(extra)}"
        for key, sub_value in value.items():
            sub_schema = properties.get(key)
            if sub_schema is None:
                continue
            err = _validate_value(sub_schema, sub_value, path=f"{path}.{key}")
            if err is not None:
                return err

    if expected_type == "array" and isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema is not None:
            for i, item in enumerate(value):
                err = _validate_value(items_schema, item, path=f"{path}[{i}]")
                if err is not None:
                    return err

    return None


_OPENAI_NAME_SEP = "__"   # OpenAI function name 只准 ^[a-zA-Z0-9_-]+$（真線路 2026-09-05 400 抓到）；MCP 工具名有 "."


def openai_tool_name(name: str) -> str:
    """`kb.get` → `kb__get`：給 Chat Completions 的 function name。⛔ 工具名不得含 `__`（register 擋），保證可逆。"""
    return name.replace(".", _OPENAI_NAME_SEP)


def tool_name_from_openai(name: str) -> str:
    """`kb__get` → `kb.get`；沒有 `__` 的名字原樣回（相容假 provider 直接用點名）。"""
    return name.replace(_OPENAI_NAME_SEP, ".")


class ToolRegistry:
    """工具白名單＋守門四步＋兩種面（`openapi`／`to_openai_tools`）。"""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._fns: dict[str, ToolFn] = {}
        self._clock = clock
        # 速率視窗：key -> 呼叫時間戳清單（滑動視窗，呼叫時清掉過期項）。
        self._rate_calls: dict[tuple[Any, Any], list[float]] = {}
        self._kb_get_calls: dict[tuple[Any, Any], list[float]] = {}
        # 違規／例外紀錄，供 trace／測試查閱（design：FORBIDDEN 只進 trace）。
        self._violations: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 註冊
    # ------------------------------------------------------------------
    def register(self, spec: ToolSpec, fn: ToolFn) -> None:
        name = spec["name"]
        if name in self._specs:
            raise ValueError(f"tool {name!r} already registered")
        input_schema = spec.get("input_schema", {})
        properties = input_schema.get("properties", {})
        bad_keys = _IDENTITY_KEYS & set(properties.keys())
        if bad_keys:
            raise ValueError(
                f"ToolSpec {name!r}.input_schema 含身分鍵（不變量 18）："
                f"{sorted(bad_keys)}"
            )
        spec = dict(spec)  # 淺拷貝，避免呼叫端事後改動影響已註冊 spec
        # 封閉 schema（1.10 P2）：未宣告的鍵一律不收。⛔ 對 `input_schema` 另做一份
        # 拷貝再 setdefault——直接改原字典會回頭汙染呼叫端的模組級常數
        # （`KB_GET_SPEC` 之類）。
        # ⚠️ 連帶約束：`scope="write"` 的 spec **必須**把 `confirmation_token` 寫進
        #    `properties`，否則守門②放行後會在④被這條 additionalProperties 擋成
        #    `INVALID_INPUT`（任務 2.4 落 write 工具時注意）。
        if _OPENAI_NAME_SEP in name:
            raise ValueError(f"工具名 {name!r} 不得含 {_OPENAI_NAME_SEP!r}（OpenAI 名稱編碼保留字，見 openai_tool_name）")
        input_schema = dict(input_schema)
        input_schema.setdefault("additionalProperties", False)
        spec["input_schema"] = input_schema
        spec.setdefault("facade_only", False)
        spec.setdefault("mutates_session", False)
        self._specs[name] = spec  # type: ignore[assignment]
        self._fns[name] = fn

    # ------------------------------------------------------------------
    # 可見性
    # ------------------------------------------------------------------
    def specs_for(
        self,
        identity: Identity,
        stage: Stage,
        *,
        readonly_view: bool = False,
        for_model: bool = True,
    ) -> list[ToolSpec]:
        """唯一可見性規則（design 元件 2）：

        `name` 可見 ⇔ `audience ∈ spec.stage
            and spec.stage[audience] <= stage
            and (not readonly_view or (scope == "read" and not mutates_session))
            and not (facade_only and (for_model or readonly_view))`

        DSP-016（2026-09-05）：`session.slots.set`／`confirm.request` 是 scope=read 但會寫
        `form_sessions`／token 表；影子回合與正式回合共用 session_id，只看 scope 會讓影子
        污染正式狀態 ⇒ `mutates_session=True` 的工具在 `readonly_view` 一律不可見。
        """
        audience = identity.resolved_audience()
        visible: list[ToolSpec] = []
        for spec in self._specs.values():
            spec_stage = spec.get("stage", {})
            if audience not in spec_stage:
                continue
            if not _stage_le(spec_stage[audience], stage):
                continue
            if readonly_view and (spec.get("scope") == "write" or spec.get("mutates_session")):
                continue
            if spec.get("facade_only") and (for_model or readonly_view):
                continue
            visible.append(spec)
        return visible

    def _is_visible(
        self,
        identity: Identity,
        name: str,
        stage: Stage,
        *,
        readonly_view: bool,
        for_model: bool,
    ) -> bool:
        return any(
            s["name"] == name
            for s in self.specs_for(
                identity, stage, readonly_view=readonly_view, for_model=for_model
            )
        )

    # ------------------------------------------------------------------
    # 速率限制
    # ------------------------------------------------------------------
    def _prune(self, calls: list[float], now: float, window_s: float) -> None:
        cutoff = now - window_s
        while calls and calls[0] <= cutoff:
            calls.pop(0)

    def _check_and_record_rate(
        self, key: tuple[Any, Any], now: float
    ) -> bool:
        limit = int(os.environ.get("RATE_PER_MIN", _DEFAULT_RATE_PER_MIN))
        calls = self._rate_calls.setdefault(key, [])
        self._prune(calls, now, _MINUTE_S)
        if len(calls) >= limit:
            return False
        calls.append(now)
        return True

    def _check_and_record_kb_get_cap(
        self, key: tuple[Any, Any], now: float
    ) -> bool:
        cap = int(os.environ.get("KB_GET_CAP", _DEFAULT_KB_GET_CAP))
        calls = self._kb_get_calls.setdefault(key, [])
        self._prune(calls, now, _HOUR_S)
        if len(calls) >= cap:
            return False
        calls.append(now)
        return True

    # ------------------------------------------------------------------
    # 違規紀錄
    # ------------------------------------------------------------------
    def _record_violation(self, identity: Identity, name: str, note: str) -> None:
        self._violations.append(
            {
                "name": name,
                "note": note,
                "api_key_id": identity.api_key_id,
                "vendor_id": identity.vendor_id,
            }
        )

    def last_violations(self) -> list[dict[str, Any]]:
        """回傳目前累積的違規／例外紀錄
        （`FORBIDDEN`／`EXC:<類名>`／`IDENTITY_KEY:<鍵>`）。

        ⛔ 不對外洩到 `ToolResult`——這是 registry 內部 trace，供
        `AgentRuntime`／測試查閱，不進模型可見的回應。
        """
        return list(self._violations)

    # ------------------------------------------------------------------
    # 呼叫（守門四步）
    # ------------------------------------------------------------------
    async def call(
        self,
        identity: Identity,
        name: str,
        args: dict,
        timeout_s: float,
        *,
        stage: Stage,
        readonly_view: bool = False,
        for_model: bool = False,
    ) -> ToolResult:
        # ⓪ 身分鍵剝除（1.10 P2）：呼叫端（模型／MCP client）夾帶的 vendor_id 之類
        #    一律丟掉，⛔ 不讓它有機會覆寫 `identity`。靜默剝除＋記 trace，
        #    ⛔ 不回錯誤碼（見模組 docstring）。
        if isinstance(args, dict):
            stripped = sorted(_IDENTITY_KEYS & set(args.keys()))
            args = {k: v for k, v in args.items() if k not in _IDENTITY_KEYS}
            for key in stripped:
                self._record_violation(identity, name, f"IDENTITY_KEY:{key}")

        # ① 可見性
        if name not in self._specs or not self._is_visible(
            identity, name, stage, readonly_view=readonly_view, for_model=for_model
        ):
            self._record_violation(identity, name, "FORBIDDEN")
            return ToolResult(ok=False, error="NO_MATCH")

        spec = self._specs[name]

        # ② scope=="write"：readonly_view 一律擋；否則查 confirmation_token 存在
        if spec.get("scope") == "write":
            if readonly_view:
                return ToolResult(ok=False, error="NO_MATCH")
            if not args.get("confirmation_token"):
                return ToolResult(ok=False, error="CONFIRMATION_REQUIRED")

        # ③ 速率限制：key = (api_key_id, vendor_id)，⛔ 不含 session_id
        rate_key = (identity.api_key_id, identity.vendor_id)
        now = self._clock()
        if not self._check_and_record_rate(rate_key, now):
            return ToolResult(ok=False, error="RATE_LIMITED")
        if name == "kb.get" and not self._check_and_record_kb_get_cap(rate_key, now):
            return ToolResult(ok=False, error="RATE_LIMITED")

        # ④ input_schema 驗證
        schema_error = _validate_against_schema(spec.get("input_schema", {}), args)
        if schema_error is not None:
            return ToolResult(ok=False, error="INVALID_INPUT")

        fn = self._fns[name]
        try:
            return await asyncio.wait_for(fn(identity, args), timeout=timeout_s)
        except asyncio.TimeoutError:
            return ToolResult(ok=False, error="TOOL_TIMEOUT")
        except Exception as exc:  # noqa: BLE001 — 刻意吞：見模組 docstring 的決定
            self._record_violation(identity, name, f"EXC:{type(exc).__name__}")
            return ToolResult(ok=False, error="NO_MATCH")

    # ------------------------------------------------------------------
    # 兩種面：OpenAPI（門面）／OpenAI Chat Completions tools[]（模型）
    # ------------------------------------------------------------------
    def openapi(self, identity: Identity, stage: Stage) -> dict:
        """只列該身分可見工具（`for_model=False`，門面視角）。"""
        paths: dict[str, Any] = {}
        for spec in self.specs_for(identity, stage, for_model=False):
            name = spec["name"]
            output_model = spec.get("output_model")
            response_schema = (
                output_model.model_json_schema() if output_model is not None else {}
            )
            paths[f"/tools/{name}"] = {
                "post": {
                    "summary": spec.get("description", ""),
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": spec.get("input_schema", {})}
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": response_schema}
                            },
                        }
                    },
                }
            }
        return {"openapi": "3.0.0", "paths": paths}

    def to_openai_tools(
        self, identity: Identity, stage: Stage, *, readonly_view: bool = False
    ) -> list[dict]:
        """Chat Completions `tools[]`（`for_model=True`，模型視角）。

        每筆 `strict: true`，`parameters` 即 `input_schema` 且強制
        `additionalProperties: false`（若原 schema 未設，這裡補上——
        strict function calling 的硬性要求，不影響 `call()` 端另跑一次
        `_validate_against_schema` 的驗證邏輯）。
        """
        tools: list[dict] = []
        for spec in self.specs_for(
            identity, stage, readonly_view=readonly_view, for_model=True
        ):
            parameters = dict(spec.get("input_schema", {}))
            parameters.setdefault("additionalProperties", False)
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": openai_tool_name(spec["name"]),   # 點 → __（OpenAI 名稱規則）
                        "description": spec.get("description", ""),
                        "strict": True,
                        "parameters": parameters,
                    },
                }
            )
        return tools
