"""
獨立測試執行腳本 - ScenarioSelector

直接執行測試而不經過 __init__.py，避免循環導入問題。
"""

import sys
import os

# 確保可以導入 scenario_selector
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 直接導入並執行測試
import subprocess

# 使用 pytest 的直接 API
import pytest

if __name__ == "__main__":
    # 使用 --import-mode=importlib 避免循環導入
    exit_code = pytest.main([
        "test_scenario_selector.py",
        "-v",
        "--tb=short",
        "-p", "no:cacheprovider",
        "--import-mode=importlib"
    ])

    sys.exit(exit_code)
