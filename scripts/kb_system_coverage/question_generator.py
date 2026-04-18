#!/usr/bin/env python3
"""
QuestionGenerator — 各角色操作問題清單生成

讀取 jgb_module_inventory.json，依模組×角色組合呼叫 LLM（gpt-4o-mini）
生成操作問題清單，涵蓋三類問題：基本操作、常見疑問、異常處理。

每個問題標註 topic_id、角色、入口、優先級、query_type（static/dynamic）。

Usage:
    python3 scripts/kb_system_coverage/question_generator.py
    python3 scripts/kb_system_coverage/question_generator.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # AIChatbot/
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import Module, Feature, SystemQuestion

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
INVENTORY_PATH = _SCRIPT_DIR / "jgb_module_inventory.json"
OUTPUT_PATH = _SCRIPT_DIR / "system_questions_checklist.json"

# 模組中文縮寫對照表（用於 topic_id 前綴）
MODULE_ABBR: Dict[str, str] = {
    "estate": "物件",
    "contract": "合約",
    "billing": "帳務",
    "repair": "修繕",
    "payment": "支付",
    "iot": "設備",
    "community": "社區",
    "big_landlord": "大房東",
    "entrusted_contract": "委託",
    "balance_invoice": "差額發票",
    "esign": "簽章",
    "user_account": "帳號",
    "notification": "通知",
    "subscription": "訂閱",
    "lessee": "租客",
    "invoice": "發票",
    "recharge_account": "虛帳",
    "listing": "刊登",
    "approval": "簽核",
    "nthurc": "住都",
    "deposit_interest": "押息",
    "admin_tools": "後台",
    "line_integration": "LINE",
    "external_api": "API",
}

# 角色中文顯示名稱
ROLE_DISPLAY: Dict[str, str] = {
    "tenant": "租客",
    "landlord": "房東",
    "property_manager": "物業經理",
    "major_landlord": "大房東",
    "agent": "經紀人",
}

# 入口中文顯示
ENTRY_DISPLAY: Dict[str, str] = {
    "app": "APP / 管理後台",
    "admin": "後台管理系統",
    "both": "APP 與管理後台",
}

# OpenAI 設定
MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒
BATCH_SIZE = 3   # 並行處理的模組×角色組合數量
BATCH_DELAY = 1  # 批次間延遲（秒）


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------
QUESTION_GENERATION_PROMPT = """你是 JGB 好租寶租屋管理平台的產品專家。

我需要你為以下模組的特定角色，生成使用者可能會問 AI 客服的操作問題清單。

## 模組資訊
- 模組名稱：{module_name}
- 模組說明：{module_description}
- 角色：{role_display}（{role_id}）
- 操作入口：{entry_display}

## 該角色在此模組中可使用的功能
{features_list}

## 生成要求

請生成操作問題，分為三類：
1. **basic_operation**（基本操作）：如何使用該功能的步驟型問題，例如「怎麼在 APP 查看帳單」
2. **common_question**（常見疑問）：操作過程中常遇到的疑問，例如「帳單什麼時候會自動產生」
3. **error_handling**（異常處理）：操作失敗或出錯時的問題，例如「繳費失敗怎麼辦」

每個問題請標註：
- **priority**：
  - p0 = 高頻必答（每天都有人問的核心操作）
  - p1 = 常見（經常被問到）
  - p2 = 偶爾（特殊情境才會碰到）
- **query_type**：
  - static = 用固定說明即可回答（如「怎麼繳費」「怎麼報修」）
  - dynamic = 需要查詢使用者在系統中的實際資料才能回答（如「我的帳單為什麼沒發票」「合約為什麼不能點交」）
- **keywords**：2-5 個搜尋關鍵字（繁體中文）

## 數量要求
- 根據功能數量合理生成，每個功能至少 1-2 題
- 三類問題都必須有涵蓋
- basic_operation 至少 {min_basic} 題
- common_question 至少 {min_common} 題
- error_handling 至少 {min_error} 題

## 輸出格式

請以 JSON 陣列格式回應，每個元素包含：
```json
{{
  "question": "問題文字（繁體中文，以「怎麼」「如何」「在哪裡」「為什麼」等問句開頭）",
  "question_category": "basic_operation | common_question | error_handling",
  "priority": "p0 | p1 | p2",
  "query_type": "static | dynamic",
  "keywords": ["關鍵字1", "關鍵字2"],
  "related_features": ["feature_id_1"]
}}
```

只輸出 JSON 陣列，不要有其他文字。"""


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------

def load_inventory(path: Path) -> List[Module]:
    """載入 jgb_module_inventory.json"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    modules: List[Module] = []
    for m in raw:
        features = [
            Feature(
                feature_id=feat["feature_id"],
                feature_name=feat["feature_name"],
                roles=feat["roles"],
                entry_point=feat["entry_point"],
            )
            for feat in m.get("features", [])
        ]
        modules.append(
            Module(
                module_id=m["module_id"],
                module_name=m["module_name"],
                description=m["description"],
                features=features,
            )
        )
    return modules


def get_roles_for_module(module: Module) -> Dict[str, List[Feature]]:
    """取得模組中每個角色對應的功能列表"""
    role_features: Dict[str, List[Feature]] = {}
    for feat in module.features:
        for role in feat.roles:
            if role not in role_features:
                role_features[role] = []
            role_features[role].append(feat)
    return role_features


def determine_entry_point(features: List[Feature]) -> str:
    """從功能列表推斷該角色的主要操作入口"""
    entries = set(f.entry_point for f in features)
    if entries == {"app"}:
        return "app"
    if entries == {"admin"}:
        return "admin"
    return "both"


def build_features_list(features: List[Feature]) -> str:
    """格式化功能列表為文字"""
    lines = []
    for f in features:
        entry = ENTRY_DISPLAY.get(f.entry_point, f.entry_point)
        lines.append(f"- {f.feature_name}（{f.feature_id}，入口：{entry}）")
    return "\n".join(lines)


def calculate_min_questions(feature_count: int) -> tuple[int, int, int]:
    """根據功能數量計算各類最低問題數"""
    if feature_count <= 3:
        return (2, 1, 1)
    elif feature_count <= 8:
        return (3, 2, 2)
    else:
        return (5, 3, 3)


# ---------------------------------------------------------------------------
# LLM 呼叫
# ---------------------------------------------------------------------------

async def call_openai(
    client: Any,
    module: Module,
    role: str,
    features: List[Feature],
) -> List[dict]:
    """呼叫 OpenAI 生成問題清單"""
    entry_point = determine_entry_point(features)
    features_text = build_features_list(features)
    min_basic, min_common, min_error = calculate_min_questions(len(features))

    prompt = QUESTION_GENERATION_PROMPT.format(
        module_name=module.module_name,
        module_description=module.description,
        role_display=ROLE_DISPLAY.get(role, role),
        role_id=role,
        entry_display=ENTRY_DISPLAY.get(entry_point, entry_point),
        features_list=features_text,
        min_basic=min_basic,
        min_common=min_common,
        min_error=min_error,
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是 JGB 好租寶的產品專家，負責產出系統操作問題清單。只輸出合法 JSON 陣列。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()
            parsed = json.loads(content)

            # 處理不同格式的回應（可能是 {"questions": [...]} 或直接是 [...]）
            if isinstance(parsed, dict):
                # 取第一個 list 型別的值
                for v in parsed.values():
                    if isinstance(v, list):
                        return v
                return []
            elif isinstance(parsed, list):
                return parsed
            else:
                print(f"  [WARN] Unexpected response format for {module.module_id}×{role}")
                return []

        except json.JSONDecodeError as e:
            print(f"  [WARN] JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"  [WARN] OpenAI API error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    print(f"  [ERROR] Failed after {MAX_RETRIES} attempts for {module.module_id}×{role}")
    return []


def build_system_questions(
    raw_questions: List[dict],
    module: Module,
    role: str,
    features: List[Feature],
    counter: Dict[str, int],
) -> List[SystemQuestion]:
    """將 LLM 回傳的原始問題轉為 SystemQuestion 物件"""
    entry_point = determine_entry_point(features)
    abbr = MODULE_ABBR.get(module.module_id, module.module_name)
    questions: List[SystemQuestion] = []

    for raw in raw_questions:
        question_text = raw.get("question", "").strip()
        if not question_text:
            continue

        # 遞增計數器
        if module.module_id not in counter:
            counter[module.module_id] = 0
        counter[module.module_id] += 1
        seq = counter[module.module_id]
        topic_id = f"{abbr}_{seq:03d}"

        # 驗證與正規化欄位
        category = raw.get("question_category", "basic_operation")
        if category not in ("basic_operation", "common_question", "error_handling"):
            category = "basic_operation"

        priority = raw.get("priority", "p1")
        if priority not in ("p0", "p1", "p2"):
            priority = "p1"

        query_type = raw.get("query_type", "static")
        if query_type not in ("static", "dynamic"):
            query_type = "static"

        keywords = raw.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        # 確保 keywords 都是字串
        keywords = [str(k) for k in keywords if k]

        questions.append(
            SystemQuestion(
                topic_id=topic_id,
                module_id=module.module_id,
                question=question_text,
                roles=[role],
                entry_point=entry_point,
                priority=priority,
                query_type=query_type,
                question_category=category,
                keywords=keywords,
            )
        )

    return questions


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

async def generate_questions(
    modules: List[Module],
    dry_run: bool = False,
) -> List[SystemQuestion]:
    """主流程：為所有模組×角色組合生成問題"""
    from openai import AsyncOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY 環境變數未設定")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key)

    # 建立所有 模組×角色 任務
    tasks: List[tuple[Module, str, List[Feature]]] = []
    for module in modules:
        role_features = get_roles_for_module(module)
        for role, features in role_features.items():
            tasks.append((module, role, features))

    if dry_run:
        # Dry-run 模式：只取前 3 組
        tasks = tasks[:3]
        print(f"[DRY-RUN] 只處理前 {len(tasks)} 個模組×角色組合\n")

    print(f"共 {len(tasks)} 個模組×角色組合需要處理\n")

    all_questions: List[SystemQuestion] = []
    counter: Dict[str, int] = {}  # 模組級流水號計數器
    total_tasks = len(tasks)

    # 分批處理
    for batch_start in range(0, total_tasks, BATCH_SIZE):
        batch = tasks[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total_tasks + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"--- Batch {batch_num}/{total_batches} ---")

        # 並行呼叫 LLM
        coroutines = []
        for module, role, features in batch:
            print(f"  生成: {module.module_name} × {ROLE_DISPLAY.get(role, role)} ({len(features)} 功能)")
            coroutines.append(call_openai(client, module, role, features))

        results = await asyncio.gather(*coroutines)

        # 處理結果
        for (module, role, features), raw_questions in zip(batch, results):
            questions = build_system_questions(
                raw_questions, module, role, features, counter
            )
            all_questions.extend(questions)
            print(f"  -> {module.module_name} × {ROLE_DISPLAY.get(role, role)}: {len(questions)} 題")

        # 批次間延遲
        if batch_start + BATCH_SIZE < total_tasks:
            await asyncio.sleep(BATCH_DELAY)

    return all_questions


def save_output(questions: List[SystemQuestion], path: Path) -> None:
    """儲存問題清單為 JSON"""
    data = [asdict(q) for q in questions]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n已儲存 {len(data)} 個問題到 {path}")


def print_summary(questions: List[SystemQuestion]) -> None:
    """印出摘要統計"""
    print("\n" + "=" * 60)
    print("摘要統計")
    print("=" * 60)

    print(f"\n總問題數：{len(questions)}")

    # 按優先級
    priorities = {}
    for q in questions:
        priorities[q.priority] = priorities.get(q.priority, 0) + 1
    print(f"\n按優先級：")
    for p in ("p0", "p1", "p2"):
        print(f"  {p}: {priorities.get(p, 0)}")

    # 按 query_type
    query_types = {}
    for q in questions:
        query_types[q.query_type] = query_types.get(q.query_type, 0) + 1
    print(f"\n按查詢類型：")
    for qt in ("static", "dynamic"):
        print(f"  {qt}: {query_types.get(qt, 0)}")

    # 按類別
    categories = {}
    for q in questions:
        categories[q.question_category] = categories.get(q.question_category, 0) + 1
    print(f"\n按問題類別：")
    for cat in ("basic_operation", "common_question", "error_handling"):
        print(f"  {cat}: {categories.get(cat, 0)}")

    # 按模組
    modules = {}
    for q in questions:
        modules[q.module_id] = modules.get(q.module_id, 0) + 1
    print(f"\n按模組：")
    for mid, cnt in sorted(modules.items(), key=lambda x: -x[1]):
        abbr = MODULE_ABBR.get(mid, mid)
        print(f"  {abbr}（{mid}）: {cnt}")

    # 按角色
    roles = {}
    for q in questions:
        for r in q.roles:
            roles[r] = roles.get(r, 0) + 1
    print(f"\n按角色：")
    for r, cnt in sorted(roles.items(), key=lambda x: -x[1]):
        display = ROLE_DISPLAY.get(r, r)
        print(f"  {display}（{r}）: {cnt}")


def main():
    parser = argparse.ArgumentParser(
        description="QuestionGenerator — 各角色操作問題清單生成"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只處理前 2-3 個模組×角色組合（測試用）",
    )
    parser.add_argument(
        "--inventory",
        type=str,
        default=str(INVENTORY_PATH),
        help="模組清單路徑（預設：jgb_module_inventory.json）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_PATH),
        help="輸出路徑（預設：system_questions_checklist.json）",
    )
    args = parser.parse_args()

    inventory_path = Path(args.inventory)
    output_path = Path(args.output)

    if not inventory_path.exists():
        print(f"[ERROR] 找不到模組清單：{inventory_path}")
        sys.exit(1)

    print("=" * 60)
    print("QuestionGenerator — 各角色操作問題清單生成")
    print("=" * 60)
    print(f"模組清單：{inventory_path}")
    print(f"輸出路徑：{output_path}")
    print(f"Dry-run：{'是' if args.dry_run else '否'}")
    print()

    # 載入模組清單
    modules = load_inventory(inventory_path)
    print(f"載入 {len(modules)} 個模組\n")

    # 生成問題
    start_time = time.time()
    questions = asyncio.run(generate_questions(modules, dry_run=args.dry_run))
    elapsed = time.time() - start_time

    # 儲存
    save_output(questions, output_path)

    # 印出摘要
    print_summary(questions)
    print(f"\n耗時：{elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
