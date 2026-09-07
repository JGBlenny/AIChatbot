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
  `confirmation_token`（這一層**只查存在**、⛔ 不碰 DB）⇒ `CONFIRMATION_REQUIRED`。
  ⚠️ 真正的確認閘門在 `register()` 強制包上去的**共用 wrapper**
  （`_wrap_write_tool`：`assert_redeemed(token, session_id)` ＋ pm 雙證，
  DSP-038／S-8／S-9）——⛔ 別把「守門②過了」讀成「這張 token 是真的」。
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

from services.agent.identity import (
    DEFAULT_ENTRY_CHANNEL,
    STAGE_ORDER,
    Audience,
    Identity,
    Stage,
)

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

#: 寫入型工具的總開關（DSP-038-1／R4.4）。**預設 false**——旗標沒開，
#: `mcp_only=True` 的工具在任何入口、任何 stage 都不可見、也呼叫不到。
#: 解析方式與 `services/presales_gate.extractive_enabled()` 同款（`{1,true,on,yes}`
#: 不分大小寫），⛔ 不另立第三種真值語法。
#: ⚠️ **定義放在 registry 而不是 `bootstrap.py`**：閘門在這一層執行，而
#: `bootstrap` 反過來 import 本模組——把讀值點放進 bootstrap 會造成環狀 import。
#: `bootstrap.write_tools_enabled` 是本函式的**別名**（同一個物件），
#: 「bootstrap 讀旗標」因此仍然成立，⛔ 不是兩份實作。
AGENT_WRITE_TOOLS_ENV: str = "AGENT_WRITE_TOOLS_ENABLED"
_TRUTHY: frozenset = frozenset({"1", "true", "on", "yes"})


def write_tools_enabled() -> bool:
    """`AGENT_WRITE_TOOLS_ENABLED` ∈ {1,true,on,yes}（不分大小寫）⇒ True；
    未設或其他值 ⇒ **False**（fail-closed）。本旗標的唯一讀值點。"""
    return (os.environ.get(AGENT_WRITE_TOOLS_ENV) or "").strip().lower() in _TRUTHY


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
    mcp_only: bool  # 預設 False；DSP-038-1：True ⇒ 只有 `identity.entry=="mcp"` 看得到，且另需 AGENT_WRITE_TOOLS_ENABLED
    # ⚠️ `scope=="write"` **必須**同時是 `mcp_only=True`（`register()` 期 raise），
    #    且寫入面一律被共用 wrapper 包住（`_wrap_write_tool`）。


ToolFn = Callable[[Identity, dict], Awaitable[ToolResult]]

#: 寫入型工具共用 wrapper 的兌現查核（DSP-038／S-9）：`(token, session_id) -> bool`。
#: 實作是 `services.agent.tools.confirm.assert_redeemed` 的薄綁定（帶著 db pool），
#: 由 `mcp_facade.build_registry` 以 `bind_redeem_checker()` 綁一次。
#: ⚠️ **沒綁 ⇒ 任何 write 工具一律 `CONFIRMATION_REQUIRED`**（fail-closed）——
#: ⛔ 不得改成「沒綁就放行」，那會讓「忘了接線」等於「確認閘門不存在」。
RedeemChecker = Callable[[str, str], Awaitable[bool]]


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


def _make_nullable(subschema: dict) -> dict:
    """把一個「選填鍵」的子 schema 改成「可為 null」，保持 strict 合法。

    ⛔ 不是把鍵變非必填——strict function calling 沒有非必填這回事，
    選填語義只能靠「型別多收一個 null」表達（呼叫端仍可傳 `None` 代表
    「不填」，`call()` 端的 `_validate_against_schema` 用的是另一份原始
    schema，選填鍵真正可以整個省略，見 `to_openai_tools` 呼叫處註解）。
    """
    sub = dict(subschema)
    sub.pop("default", None)
    if "enum" in sub:
        if None in sub["enum"]:
            return sub
        return {"anyOf": [sub, {"type": "null"}]}
    for union_key in ("anyOf", "oneOf", "allOf"):
        if union_key in sub:
            branches = sub[union_key]
            if not any(
                isinstance(b, dict) and b.get("type") == "null" for b in branches
            ):
                sub[union_key] = list(branches) + [{"type": "null"}]
            return sub
    expected_type = sub.get("type")
    if expected_type is None:
        return {"anyOf": [sub, {"type": "null"}]}
    if isinstance(expected_type, list):
        if "null" not in expected_type:
            sub["type"] = list(expected_type) + ["null"]
    else:
        sub["type"] = [expected_type, "null"]
    return sub


def _walk_strict(node: Any) -> Any:
    """遞迴把 JSON Schema 轉成 OpenAI strict function-calling 合法形：
    每一層 object（`type=="object"` 或帶 `properties`）都補
    `additionalProperties: False` 且 `required` ＝該層 properties 全部鍵；
    原本不在 `required` 的鍵型別改為可為 null（`_make_nullable`）；移除
    strict 不接受的 `default`。`items`／`anyOf`／`oneOf`／`allOf` 遞迴處理。
    """
    if not isinstance(node, dict):
        return node
    node.pop("default", None)
    if node.get("type") == "object" or "properties" in node:
        properties = node.get("properties") or {}
        required_orig = set(node.get("required") or [])
        new_properties: dict[str, Any] = {}
        for key, sub_schema in properties.items():
            walked = _walk_strict(sub_schema)
            if key not in required_orig:
                walked = _make_nullable(walked)
            new_properties[key] = walked
        node["properties"] = new_properties
        node["additionalProperties"] = False
        node["required"] = list(new_properties.keys())
    if "items" in node:
        node["items"] = _walk_strict(node["items"])
    for union_key in ("anyOf", "oneOf", "allOf"):
        if isinstance(node.get(union_key), list):
            node[union_key] = [_walk_strict(v) for v in node[union_key]]
    return node


def _openai_strict_parameters(input_schema: dict) -> dict:
    """`ToolSpec.input_schema` → OpenAI strict function-calling 合法的
    `parameters`（純函式，回新 dict，⛔ 不改入參）。

    每一層 object 都 `additionalProperties: False` 且 `required` ＝該層
    properties 全部鍵；原本選填的鍵型別改為可為 null，保留「可不填」的
    語義給模型（strict 沒有非必填，只能靠 nullable 表達）。⚠️ 這份
    `required` 只給模型看的 `parameters` 用——`call()` 端的
    `_validate_against_schema` 走的是 spec 原始 `input_schema`（原始
    `required`），選填鍵在真正呼叫時仍可整個省略，語義不變。
    """
    import copy

    return _walk_strict(copy.deepcopy(input_schema))

def _drop_null_optionals(schema: dict, args: Any) -> Any:
    """`_openai_strict_parameters` 的逆向：OpenAI strict function calling 強制模型送出
    properties 的**每一個**鍵，選填鍵「沒填」只能以 `null` 表示；而 `call()` 驗的是
    spec 原始 `input_schema`（選填鍵不接受 null）⇒ 先把「非 required 的 null」還原成
    「省略」再驗，工具函式看到的參數形狀與 strict 之前一致。required 鍵的 null 原樣
    保留（仍 INVALID_INPUT）；**未宣告鍵**的 null 也原樣保留（交 `additionalProperties:false`
    擋，⛔ 不得成為繞過口）。每層 object、陣列元素、union 分支同樣處理（與 `_walk_strict`
    對稱）；回新物件、不改入參。
    真線路 2026-09-08 pm 煙霧抓到：模型送 `{"face": …, "ref": "900001", "keyword": null}`
    ⇒ INVALID_INPUT ×4 ⇒ 工具預算耗盡 ⇒ `budget_exhausted` 轉人（demo 帳本 D-BLOCK-2）。
    """
    if not isinstance(schema, dict):
        return args
    if isinstance(args, list):
        # 陣列：逐元素套 items（與 `_walk_strict` 的 items 走訪對稱）
        items = schema.get("items")
        return [_drop_null_optionals(items, v) for v in args] if isinstance(items, dict) else args
    if not isinstance(args, dict):
        return args
    if "properties" not in schema:
        # union 分支（anyOf／oneOf／allOf）：套第一個 object 形狀的分支；都不是就原樣
        for key in ("anyOf", "oneOf", "allOf"):
            for branch in schema.get(key) or []:
                if isinstance(branch, dict) and "properties" in branch:
                    return _drop_null_optionals(branch, args)
        return args
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    out: dict = {}
    for key, value in args.items():
        sub = props.get(key)
        # ⛔ 只還原「宣告過的選填鍵」：未宣告鍵的 null 原樣留給 additionalProperties:false 去擋
        if value is None and sub is not None and key not in required:
            continue
        if isinstance(sub, dict) and isinstance(value, (dict, list)):
            value = _drop_null_optionals(sub, value)
        out[key] = value
    return out



_OPENAI_NAME_SEP = "__"   # OpenAI function name 只准 ^[a-zA-Z0-9_-]+$（真線路 2026-09-05 400 抓到）；MCP 工具名有 "."


def openai_tool_name(name: str) -> str:
    """`kb.get` → `kb__get`：給 Chat Completions 的 function name。⛔ 工具名不得含 `__`（register 擋），保證可逆。"""
    return name.replace(".", _OPENAI_NAME_SEP)


def tool_name_from_openai(name: str) -> str:
    """`kb__get` → `kb.get`；沒有 `__` 的名字原樣回（相容假 provider 直接用點名）。"""
    return name.replace(_OPENAI_NAME_SEP, ".")


class ToolRegistry:
    """工具白名單＋守門四步＋兩種面（`openapi`／`to_openai_tools`）。"""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        write_tools_enabled: Optional[bool] = None,
        redeem_checker: Optional[RedeemChecker] = None,
    ) -> None:
        """`write_tools_enabled`（DSP-038-1）：

        - `None`（預設）⇒ **每次判可見性時現讀 env**（`write_tools_enabled()`），
          與 `RATE_PER_MIN` 同慣例：旗標翻面不必重建 registry。
        - 明給 `True`／`False` ⇒ 釘住，⛔ 不再看 env（測試與明示接線用）。

        ⚠️ 兩種情況都 fail-closed：env 未設 ⇒ False。

        `redeem_checker`（DSP-038／S-9）：寫入型工具共用 wrapper 用的兌現查核。
        `None`（預設）⇒ **任何 write 工具一律 `CONFIRMATION_REQUIRED`**——
        ⛔ 不是「沒綁就跳過檢查」。可事後以 `bind_redeem_checker()` 綁一次
        （set-once，⛔ 不得換掉已綁的那一個）。
        """
        self._specs: dict[str, ToolSpec] = {}
        self._fns: dict[str, ToolFn] = {}
        self._clock = clock
        self._write_tools_enabled = write_tools_enabled
        self._redeem_checker: Optional[RedeemChecker] = redeem_checker
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
        spec.setdefault("mcp_only", False)

        # ── DSP-038-1／W1b F2：`scope=="write"` 的兩條**註冊期**硬性要求 ──────
        # ① `mcp_only=True` 是強制的（⛔ 不是慣例）。舊碼把旗標閘只綁在
        #    `mcp_only` 上，於是一支忘了寫 `mcp_only` 的 write 工具會同時逃過
        #    入口閘與旗標閘 ⇒ REST 入口在旗標關著時也看得見、呼叫得到。
        #    這裡改成**註冊當下大聲失敗**：漏寫的形狀根本註冊不進來。
        #    （`specs_for` 的旗標閘同時也綁 `scope=="write"`，兩道互為備援。）
        if spec.get("scope") == "write":
            if not spec.get("mcp_only"):
                raise ValueError(
                    f"ToolSpec {name!r} 是 scope=\"write\" 但沒有 mcp_only=True"
                    "（DSP-038-1：寫入型工具只准從 /mcp 入口可見）"
                )
            # ② 共用 wrapper 強制包（S-9）：確認兌現查核＋pm 雙證，
            #    ⛔ 不由各工具自己記得寫——「忘了寫」的失效形狀是無聲放行。
            fn = self._wrap_write_tool(name, fn)

        self._specs[name] = spec  # type: ignore[assignment]
        self._fns[name] = fn

    def bind_redeem_checker(self, checker: RedeemChecker) -> None:
        """綁定寫入 wrapper 的兌現查核（**set-once**）。

        ⛔ 不得換掉已綁的那一個：一個可以在執行期被替換的安全控制，等於沒有控制。
        接線點是 `mcp_facade.build_registry`（那裡才拿得到 db pool 的 getter）。
        """
        if self._redeem_checker is not None and self._redeem_checker is not checker:
            raise ValueError("redeem_checker 已綁定，⛔ 不得替換")
        self._redeem_checker = checker

    def _wrap_write_tool(self, name: str, fn: ToolFn) -> ToolFn:
        """`scope=="write"` 的**共用 wrapper**（S-8／S-9，`register()` 強制包）。

        兩道閘，兩道都在進 handler **之前**：
          ① **確認兌現**——`assert_redeemed(token, session_id)` 為真才放行。
             `call()` 的守門②只查 `confirmation_token` **有沒有帶**（那一層不碰 DB），
             ⛔ 它不是確認閘門；真正的閘門是這一道。沒綁 checker、token 不是字串、
             或查核為假 ⇒ `CONFIRMATION_REQUIRED`（四種原因共用同一個碼，
             ⛔ 不細分——細分會把 token 表變成可探測的預言機，同
             `confirm.RedeemResult` 的紀律）。
          ② **pm 寫入要雙證**（S-8）——`property_manager` 的**讀**是刻意的單證路徑
             （見 `tools/jgb2.py:_identity_gate_ok`），但**寫**不是：單證等於「持有
             role_id 就能改整個 role 名下的資料」。缺 `user_id` ⇒ `NO_MATCH`。

        ⚠️ 資源層級的範圍檢查（這張帳單是不是這個 role 的、這個物件名字查不查得到）
        ⛔ 不在這裡——那是**每支工具自己**的事（只有它知道自己要動什麼資源），
        見 `services/agent/tools/action.py`。
        """

        async def _guarded(identity: Identity, args: dict) -> ToolResult:
            token = args.get("confirmation_token") if isinstance(args, dict) else None
            session_id = getattr(identity, "session_id", None)
            checker = self._redeem_checker
            if (
                checker is None
                or not isinstance(token, str)
                or not token
                or not isinstance(session_id, str)
                or not session_id
            ):
                self._record_violation(identity, name, "WRITE_NOT_REDEEMED")
                return ToolResult(ok=False, error="CONFIRMATION_REQUIRED")
            if not await checker(token, session_id):
                self._record_violation(identity, name, "WRITE_NOT_REDEEMED")
                return ToolResult(ok=False, error="CONFIRMATION_REQUIRED")
            if identity.resolved_audience() == "property_manager" and not getattr(
                identity, "user_id", None
            ):
                self._record_violation(identity, name, "WRITE_PM_SINGLE_PROOF")
                return ToolResult(ok=False, error="NO_MATCH")
            return await fn(identity, args)

        return _guarded

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
            and not (facade_only and (for_model or readonly_view))
            and (not (mcp_only or scope == "write")
                 or (identity.entry == "mcp" and 旗標開))`

        DSP-016（2026-09-05）：`session.slots.set`／`confirm.request` 是 scope=read 但會寫
        `form_sessions`／token 表；影子回合與正式回合共用 session_id，只看 scope 會讓影子
        污染正式狀態 ⇒ `mutates_session=True` 的工具在 `readonly_view` 一律不可見。

        DSP-038-1（2026-09-08）：**寫入面**（`mcp_only=True` **或** `scope=="write"`）
        另外要過**兩道**閘，兩道都與 `for_model`／`readonly_view` 正交：
          ① **入口**——`identity.entry != "mcp"` ⇒ 不可見。REST 入口的身分一律
             落預設 `"rest"`（`identity.DEFAULT_ENTRY_CHANNEL`），因此看不到、
             也呼叫不到（`call()` 走同一個 `_is_visible` ⇒ `NO_MATCH`）。
          ② **旗標**——`AGENT_WRITE_TOOLS_ENABLED` 未開 ⇒ 不可見（R4.4）。

        ⚠️ **W1b F2（2026-09-08）：閘綁在「`mcp_only` 或 `scope=="write"`」兩者的
        聯集，⛔ 不再只綁 `mcp_only`。** 舊寫法只看 `mcp_only`，於是一支忘了寫
        `mcp_only=True` 的 write 工具會同時逃過入口閘與旗標閘。現在有兩道互為
        備援的防線：`register()` 對 `scope=="write"` 缺 `mcp_only` **直接 raise**
        （那種 spec 註冊不進來），而這裡的聯集判斷保證**即使繞過 `register()`
        把 spec 塞進 `_specs`**，寫入面仍然關著。⛔ 兩道都不得單獨拿掉。
        """
        audience = identity.resolved_audience()
        entry = getattr(identity, "entry", DEFAULT_ENTRY_CHANNEL)
        write_ok = self.write_tools_enabled()
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
            if (spec.get("mcp_only") or spec.get("scope") == "write") and (
                entry != "mcp" or not write_ok
            ):
                continue
            visible.append(spec)
        return visible

    def write_tools_enabled(self) -> bool:
        """本 registry 這一刻認定的旗標值（建構時釘住的值，或現讀 env）。

        公開是刻意的：健檢／門面要印「這台機器現在放不放寫入工具」時，
        讀的必須是**這個 registry 實際在用的那個值**，⛔ 不是各自再讀一次 env。
        """
        if self._write_tools_enabled is not None:
            return self._write_tools_enabled
        return write_tools_enabled()

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

        # ④ input_schema 驗證（先把 strict 模型送來的「選填 null」還原成省略——見 _drop_null_optionals）
        args = _drop_null_optionals(spec.get("input_schema", {}), args)
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

        每筆 `strict: true`，`parameters` 由 `_openai_strict_parameters` 從
        `input_schema` 轉出：每一層 object 都 `additionalProperties: false`
        且 `required` 涵蓋該層 properties 全部鍵（OpenAI strict function
        calling 的硬性要求——`required` 缺一個 properties 的鍵就 400），
        選填鍵改為可為 null 以保留「可不填」語義。⛔ 不影響 `call()` 端
        另跑一次 `_validate_against_schema`——那邊用的是 spec 原始
        `input_schema`（原始 `required`），選填鍵在真正呼叫時仍可省略。
        """
        tools: list[dict] = []
        for spec in self.specs_for(
            identity, stage, readonly_view=readonly_view, for_model=True
        ):
            parameters = _openai_strict_parameters(spec.get("input_schema", {}))
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
