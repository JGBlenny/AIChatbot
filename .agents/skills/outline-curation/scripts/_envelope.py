"""StepEnvelope 組裝與最小 schema 校驗（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

⛔ 標準庫 only（不引 jsonschema）。校驗只做 required／type／enum／additionalProperties 四項，
足以擋住本 skill 七步腳本自己產生的輸出——不是通用 JSON Schema 引擎。

也提供狀態檔 helper：讀舊 JSON → 更新指定鍵 → 原子寫回，契約與 1.2 hook 共用
（`.claude/hooks/state/outline-gate/session.json`，鍵：diff_report／evals_ran／
materials_frozen／object_under_test_path／answerability／cost）。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Any


# ---------- repo root ----------

def find_repo_root() -> str:
    """repo 根＝ CLAUDE_PROJECT_DIR 環境變數；缺時從 cwd 往上找含 .claude/settings.json 的目錄。"""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    cur = os.path.abspath(os.getcwd())
    while True:
        if os.path.isfile(os.path.join(cur, ".claude", "settings.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("找不到 repo 根：CLAUDE_PROJECT_DIR 未設，且 cwd 往上無 .claude/settings.json")
        cur = parent


# ---------- sha256 ----------

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: str) -> str:
    """檔案或目錄皆可（9.6 S4：`--canon` 可能指到圖書館正本目錄）。目錄＝遞迴列舉一般檔案，
    對「相對路徑:內容 sha256」清單（依相對路徑排序）整體再算一次 sha256——新增/刪除/改名/內容
    任一變動都會改變值。單檔行為與 `sha256_file` 完全相同（不是它的別名，是同一套邏輯的超集）。"""
    if os.path.isdir(path):
        entries = []
        for root, _dirs, files in os.walk(path):
            for fn in files:
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, path)
                entries.append(f"{rel}:{sha256_file(fp)}")
        return hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()
    return sha256_file(path)


# ---------- StepEnvelope ----------

STEPS = ("page_surface", "feature_surface", "intake", "structure", "phrasing", "answerability", "reweigh", "diff", "import")


def make_envelope(
    *,
    step: str,
    skill_version: str,
    inputs_sha: dict,
    deterministic: bool,
    payload: dict,
    raw_outputs_path: str | None = None,
    cost: dict | None = None,
) -> dict:
    if step not in STEPS:
        raise ValueError(f"未知 step：{step}（須為 {STEPS} 之一）")
    return {
        "step": step,
        "skill_version": skill_version,
        "inputs_sha": inputs_sha,
        "deterministic": deterministic,
        "raw_outputs_path": raw_outputs_path,
        "cost": cost or {"agents": 0, "wall_s": 0.0},
        "payload": payload,
    }


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    _atomic_write(path, text)


def _atomic_write(path: str, text: str) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------- minimal schema validation ----------

class SchemaError(Exception):
    pass


def validate(instance: Any, schema: dict, *, path: str = "$") -> None:
    """最小校驗：type／enum／required／properties／additionalProperties／items。

    不支援的 schema 關鍵字一律忽略（非通用引擎，夠用即可）。
    """
    if "enum" in schema:
        if instance not in schema["enum"]:
            raise SchemaError(f"{path}: 值 {instance!r} 不在 enum {schema['enum']}")

    t = schema.get("type")
    if t is not None:
        _check_type(instance, t, path)

    is_object = isinstance(instance, dict) and (t is None or "object" in (t if isinstance(t, list) else [t]))
    is_array = isinstance(instance, list) and (t is None or "array" in (t if isinstance(t, list) else [t]))

    if is_object:
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in instance:
                raise SchemaError(f"{path}: 缺必要欄位 {req!r}")
        if schema.get("additionalProperties") is False:
            extra = set(instance.keys()) - set(props.keys())
            if extra:
                raise SchemaError(f"{path}: 不允許的額外欄位 {sorted(extra)}")
        for k, v in instance.items():
            if k in props:
                validate(v, props[k], path=f"{path}.{k}")

    if is_array:
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(instance):
                validate(item, item_schema, path=f"{path}[{i}]")


def _check_type(instance: Any, t, path: str) -> None:
    types = t if isinstance(t, list) else [t]
    py_map = {
        "object": dict,
        "array": list,
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": (int, float),
        "null": type(None),
    }
    for one in types:
        py = py_map.get(one)
        if py is None:
            return
        if one in ("integer", "number") and isinstance(instance, bool):
            continue
        if isinstance(instance, py):
            return
    raise SchemaError(f"{path}: 期望 {types}，得到 {type(instance).__name__}")


def load_schema(schema_path: str) -> dict:
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def validate_file(instance_path: str, schema_path: str) -> None:
    with open(instance_path, encoding="utf-8") as f:
        instance = json.load(f)
    validate(instance, load_schema(schema_path))


# ---------- state file helper ----------

STATE_KEYS = (
    "diff_report",
    "evals_ran",
    "materials_frozen",
    "object_under_test_path",
    "answerability",
    "cost",
)


def state_file_path(repo_root: str) -> str:
    return os.path.join(repo_root, ".claude", "hooks", "state", "outline-gate", "session.json")


def update_state(repo_root: str | None, updates: dict, *, path: str | None = None) -> dict:
    """讀舊 JSON → 只更新 updates 內的鍵 → 原子寫回。不存在的鍵不清除。

    `path`（Plan 9.14 S1-4 `--state-file`）：給了就寫這一份、⛔ 不碰預設 session.json；不給＝現行行為。"""
    if path is None:
        path = state_file_path(repo_root)
    state: dict = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}
    for k, v in updates.items():
        state[k] = v
    write_json(path, state)
    return state


def state_relpath(target: str, repo_root: str | None, state_file: str | None) -> str:
    """狀態檔內記的相對路徑：給了 `--state-file` ⇒ 相對該狀態檔所在目錄；否則相對 repo 根（現行）。"""
    base = os.path.dirname(os.path.abspath(state_file)) if state_file else repo_root
    return os.path.relpath(os.path.abspath(target), base)


# ---------- 客戶文字守門（Plan 9.14 S1-3）----------

_HERE = os.path.dirname(os.path.abspath(__file__))
#: 僅供測試：把定位器指向另一個 rag root（該處必須有 `tools/text_containment.py`，否則 raise，⛔ 不退回預設）。
TEXT_CONTAINMENT_RAG_ENV = "OUTLINE_CURATION_TEST_RAG_ROOT"
_TEXT_CONTAINMENT = None


def containment_rag_root() -> str:
    """定位 `rag-orchestrator`：照 `canon_items.py` 以 `__file__` 為基準（主機與 `.agents` 鏡像皆
    `<repo>/rag-orchestrator`），不存在就退 `/app`（容器）。⛔ 不用 `reweigh.py::_rag_root`（依賴 cwd）。"""
    override = os.environ.get(TEXT_CONTAINMENT_RAG_ENV)
    if override:
        root = os.path.abspath(override)
    else:
        root = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
        if not os.path.isdir(root):
            root = "/app"
    if not os.path.isfile(os.path.join(root, "tools", "text_containment.py")):
        raise RuntimeError(f"找不到 {root}/tools/text_containment.py——客戶文字守門缺席，⛔ 不執行（fail-closed）")
    return root


def text_containment():
    """載入唯一實作 `rag-orchestrator/tools/text_containment.py`。七個呼叫點每次執行都呼叫（不論是否觸發）；
    找不到或 import 失敗 ⇒ raise。"""
    global _TEXT_CONTAINMENT
    if _TEXT_CONTAINMENT is None:
        import importlib.util
        path = os.path.join(containment_rag_root(), "tools", "text_containment.py")
        spec = importlib.util.spec_from_file_location("_outline_text_containment", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"無法載入 {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _TEXT_CONTAINMENT = mod
    return _TEXT_CONTAINMENT
