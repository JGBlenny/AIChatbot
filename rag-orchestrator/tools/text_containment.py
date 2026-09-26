"""客戶文字不落 repo 的守門（Plan 9.14 S1-3｜fail-closed｜唯一實作）。

`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.14-real-questions-into-outline-curation-20260925.md` §2 S1-3。

為什麼是「正向圍欄」而不是偵測 `.git`：測試容器沒有掛 `.git`，且 `_envelope.find_repo_root()` 在容器內會停在
`/`（`/.claude/settings.json` 有掛載）——任何「以 git 工作樹判斷」的規則在主機與容器會得出不同結果。
所以改成：外部文字只准寫進**含標記檔 `.text-external` 的目錄（或其子孫）**，找不到圍欄一律拒絕。

- 觸發（`is_external`）：任一輸入檔 `_meta.text_policy == "external"`，或輸入檔 realpath 任一祖先目錄含
  `.text-external`（後者讓 `_meta` 在某環節掉了仍然觸發）。
- 觸發後（`require_contained`）：輸出路徑 realpath 必須有祖先（含自身）含 `.text-external`；而且輸出路徑與圍欄
  都 ⛔ 不得位於本模組定位出的 rag root 底下、⛔ 不得有任何祖先含 `.git`（`assert_outside_repo`）。
- 未觸發（既有流程）⇒ 完全不檢查，行為逐位元不變。
- 標記檔只由 `real_questions_to_cells.py` 經 `create_marker` 建立；建立前走同一個 `assert_outside_repo`。

⛔ 只用標準庫。⛔ 不在他處另寫一份（skill 端 `_envelope.text_containment()` 依 `__file__` 定位後載入本檔；
`tools/gapmap/coverage_map.py` 從同層 `tools/` 直接 import）。
"""
from __future__ import annotations

import json
import os
from typing import Iterable, Optional

MARKER = ".text-external"
TEXT_POLICY_KEY = "text_policy"
EXTERNAL = "external"

#: 本模組定位出的 rag root：主機 `<repo>/rag-orchestrator`、容器 `/app`（`./rag-orchestrator:/app` 可寫、無 `.git`）。
RAG_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class TextContainmentError(RuntimeError):
    """外部文字的輸出不在圍欄內（或圍欄落在 repo 內）——⛔ 不寫檔。"""


def _ancestors(real_path: str):
    """real_path 自身起、逐層往上到根（含根）。"""
    cur = real_path
    while True:
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return
        cur = parent


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def fence_of(path: str) -> Optional[str]:
    """path 的 realpath 自身或任一祖先含標記檔 ⇒ 回該目錄（最近的一個）；否則 None。"""
    for d in _ancestors(os.path.realpath(path)):
        if os.path.isfile(os.path.join(d, MARKER)):
            return d
    return None


def assert_outside_repo(path: str) -> str:
    """path 的 realpath 位於 rag root 下、或任一祖先（含自身）有 `.git`（目錄或檔）⇒ raise。回 realpath。

    轉換器建立標記檔與 `require_contained` 共用這一個函式（Plan 9.14 §9 #3）。"""
    rp = os.path.realpath(path)
    if _is_under(rp, RAG_ROOT):
        raise TextContainmentError(f"外部文字路徑位於 rag root（{RAG_ROOT}）底下：{rp}——⛔ 圍欄不得落在 repo 內")
    for d in _ancestors(rp):
        if os.path.lexists(os.path.join(d, ".git")):
            raise TextContainmentError(f"外部文字路徑的祖先 {d} 含 .git：{rp}——⛔ 圍欄不得落在 git 工作樹內")
    return rp


def _meta_text_policy(path: str) -> Optional[str]:
    """JSON 檔頂層 `_meta.text_policy`；非檔／非 JSON／無此鍵 ⇒ None（圍欄判斷另外照做）。"""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if isinstance(doc, dict) and isinstance(doc.get("_meta"), dict):
        v = doc["_meta"].get(TEXT_POLICY_KEY)
        return v if isinstance(v, str) else None
    return None


def text_policy_of(paths: Iterable[Optional[str]]) -> Optional[str]:
    """第一個帶 `_meta.text_policy` 的輸入檔之值（供往下游原樣傳遞）；皆無 ⇒ None。"""
    for p in paths:
        if p:
            v = _meta_text_policy(p)
            if v is not None:
                return v
    return None


def is_external(input_paths: Iterable[Optional[str]]) -> bool:
    """任一輸入 `_meta.text_policy == "external"`，或其 realpath 任一祖先含 `.text-external` ⇒ True。"""
    for p in input_paths:
        if not p:
            continue
        if _meta_text_policy(p) == EXTERNAL:
            return True
        if fence_of(p) is not None:
            return True
    return False


def require_contained(out_path: str) -> str:
    """輸出路徑（檔或 `--out-dir`）的 realpath 必須有祖先（含自身）含 `.text-external`，且不在 repo 內。回圍欄目錄。"""
    rp = assert_outside_repo(out_path)
    fence = fence_of(rp)
    if fence is None:
        raise TextContainmentError(f"輸入含外部文字，但輸出 {rp} 不在任何含 {MARKER} 的目錄內——⛔ 不寫檔")
    assert_outside_repo(fence)
    return fence


def guard(input_paths: Iterable[Optional[str]], output_paths: Iterable[str]) -> bool:
    """呼叫點共用：未觸發 ⇒ 回 False、完全不檢查；觸發 ⇒ 每個輸出都 `require_contained`（不合即 raise）。"""
    if not is_external(list(input_paths)):
        return False
    for o in output_paths:
        require_contained(o)
    return True


def create_marker(out_dir: str) -> str:
    """轉換器專用：`out_dir` 不在 repo 內 ⇒ 建目錄與空標記檔，回標記檔路徑；否則 raise（⛔ 不建任何東西）。"""
    assert_outside_repo(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    rp = assert_outside_repo(out_dir)  # 建完再以 realpath 核一次（防 makedirs 經 symlink 落進 repo）
    marker = os.path.join(rp, MARKER)
    if not os.path.exists(marker):
        with open(marker, "w", encoding="utf-8"):
            pass
    return marker
