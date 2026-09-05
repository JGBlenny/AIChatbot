"""unit：agent 路徑退休符號稽核（spec agentic-mcp-orchestration 任務 5.2｜退休標記與相容文件）。

`services/agent/**/*.py` ⛔ 不得 import／from-import／屬性存取以下舊鏈符號：

- `_top1_relevance_gate` —— 舊鏈 top-1 相關性把關，定義於 `routers/chat.py`
  （見 `async def _top1_relevance_gate`）；agent 路徑不做知識列表相關性重判，
  由 agent Runtime／MCP facade 另行決定證據取用。
- `decide_arbitration` —— 舊鏈六 case 答題仲裁，定義於 `services/decision_layer.py`
  （見 `def decide_arbitration`）；agent 路徑不跑舊鏈仲裁決策樹。
- `select_nominated` —— 舊鏈 categories 面向提名（collapse → admissibility → top-N），
  定義於 `services/responsibility_collapse.py`（見 `def select_nominated`）；
  agent 路徑的面向/工具選擇走 `services/agent/mcp_facade.py`、`services/agent/agent_rules.py`，
  不共用舊鏈提名管線。

用 `ast` 掃描每個檔案的 import 陳述與屬性存取（`ast.Attribute`），比對名稱是否為上述
退休符號之一。掃描函式獨立於測試斷言之外，因此可以直接餵假原始碼做「正對照」——
證明掃描器本身抓得到已知會中的樣本，而不是形同虛設（見 `TestScannerSanityPositiveControl`）。
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# 退休符號清單：來源見本檔 docstring；每個符號僅認定於 services/（agent 目錄以外）
# 或 routers/ 已實際存在的定義，查無來源者不得列入。
RETIRED_SYMBOLS = {
    "_top1_relevance_gate",  # routers/chat.py: async def _top1_relevance_gate
    "decide_arbitration",     # services/decision_layer.py: def decide_arbitration
    "select_nominated",       # services/responsibility_collapse.py: def select_nominated
}

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_SERVICES_DIR = REPO_ROOT / "services" / "agent"


def find_retired_symbol_usages(source: str, retired_symbols: set) -> "list[str]":
    """掃描一段原始碼的 import／from-import／屬性存取，回傳中招的符號名清單（可重複）。

    掃描範圍：
    - `import x` / `import x as y` —— 檢查 `x`（含點號路徑的最後一段與整段）
    - `from x import y` / `from x import y as z` —— 檢查 `y`
    - `obj.attr` 屬性存取 —— 檢查 `attr`
    """
    hits = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return hits

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                parts = name.split(".")
                if name in retired_symbols or parts[-1] in retired_symbols:
                    hits.append(parts[-1] if parts[-1] in retired_symbols else name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in retired_symbols:
                    hits.append(alias.name)
        elif isinstance(node, ast.Attribute):
            if node.attr in retired_symbols:
                hits.append(node.attr)
        elif isinstance(node, ast.Name):
            # 涵蓋 `from x import *` 後直接裸名使用、或動態別名賦值後的直接引用
            if node.id in retired_symbols:
                hits.append(node.id)

    return hits


def _iter_agent_service_files():
    assert AGENT_SERVICES_DIR.is_dir(), (
        f"正對照失敗：{AGENT_SERVICES_DIR} 不存在——查核目錄本身有問題，"
        "不是「查無退休符號」"
    )
    return sorted(AGENT_SERVICES_DIR.rglob("*.py"))


class TestNoRetiredSymbolsInAgentPath:
    """agent 路徑（services/agent/**）不得出現舊鏈退休符號。"""

    def test_agent_services_dir_has_python_files(self):
        """正對照組：確認掃描目標本身非空，避免『查無』只是掃到空目錄。"""
        files = _iter_agent_service_files()
        assert len(files) > 0, "services/agent/ 下找不到任何 .py 檔——掃描條件本身壞了"

    @pytest.mark.parametrize("py_file", _iter_agent_service_files() or [None])
    def test_no_retired_symbol_usage(self, py_file):
        if py_file is None:
            pytest.fail("services/agent/ 下找不到任何 .py 檔可供逐檔比對")
        source = py_file.read_text(encoding="utf-8")
        hits = find_retired_symbol_usages(source, RETIRED_SYMBOLS)
        assert hits == [], (
            f"{py_file.relative_to(REPO_ROOT)} 引用了退休符號 {hits}——"
            f"agent 路徑不應依賴舊鏈 {', '.join(sorted(set(hits)))}"
        )


class TestScannerSanityPositiveControl:
    """正對照：掃描器必須抓得到已知會中的假樣本，否則測試形同虛設。"""

    def test_scanner_catches_from_import_of_decide_arbitration(self):
        fake_source = (
            "from services.decision_layer import decide_arbitration\n"
            "\n"
            "def run():\n"
            "    return decide_arbitration(sop_score=0.1, knowledge_score=0.2)\n"
        )
        hits = find_retired_symbol_usages(fake_source, RETIRED_SYMBOLS)
        assert "decide_arbitration" in hits, (
            "掃描器沒抓到假原始碼裡的 decide_arbitration import——掃描器本身失效"
        )

    def test_scanner_catches_attribute_access_of_top1_relevance_gate(self):
        fake_source = (
            "import routers.chat as chat_mod\n"
            "\n"
            "def run():\n"
            "    return chat_mod._top1_relevance_gate\n"
        )
        hits = find_retired_symbol_usages(fake_source, RETIRED_SYMBOLS)
        assert "_top1_relevance_gate" in hits

    def test_scanner_catches_select_nominated_import(self):
        fake_source = (
            "from services.responsibility_collapse import select_nominated\n"
        )
        hits = find_retired_symbol_usages(fake_source, RETIRED_SYMBOLS)
        assert "select_nominated" in hits

    def test_scanner_is_silent_on_unrelated_code(self):
        clean_source = (
            "from services.agent.identity import Identity, audience_of\n"
            "\n"
            "def run():\n"
            "    return audience_of(mode='b2c', target_user='tenant', role_id=None)\n"
        )
        hits = find_retired_symbol_usages(clean_source, RETIRED_SYMBOLS)
        assert hits == []
