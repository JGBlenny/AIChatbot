#!/usr/bin/env python3
"""
SystemKBGenerator — 靜態系統操作 KB 批量生成

讀取覆蓋缺口報告中 recommendation=add_kb 且 query_type=static 的缺口，
使用 gpt-4o-mini 搭配 JGB 模組清單上下文批量生成 KB 內容，
經品質驗證後輸出為 ai_generated_knowledge_candidates（pending_review）。

Usage:
    python3 scripts/kb_system_coverage/system_kb_generator.py
    python3 scripts/kb_system_coverage/system_kb_generator.py --dry-run
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # AIChatbot/
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import Feature, GapItem, Module

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------

# 模組中文縮寫 → module_id 對照（反向查表）
MODULE_ABBR_TO_ID: Dict[str, str] = {
    "物件": "estate",
    "合約": "contract",
    "帳務": "billing",
    "修繕": "repair",
    "支付": "payment",
    "設備": "iot",
    "社區": "community",
    "大房東": "big_landlord",
    "委託": "entrusted_contract",
    "差額發票": "balance_invoice",
    "簽章": "esign",
    "帳號": "user_account",
    "通知": "notification",
    "訂閱": "subscription",
    "租客": "lessee",
    "發票": "invoice",
    "虛帳": "recharge_account",
    "刊登": "listing",
    "簽核": "approval",
    "住都": "nthurc",
    "押息": "deposit_interest",
    "後台": "admin_tools",
    "LINE": "line_integration",
    "API": "external_api",
}

# 工程術語正則
_ENGINEERING_PATTERNS: List[re.Pattern] = [
    re.compile(r'/api/[a-z]'),                  # API 路徑
    re.compile(r'[a-z]+_[a-z]+', re.IGNORECASE),  # snake_case 變數名
    re.compile(r'[a-z]+[A-Z][a-z]+\('),         # camelCase 函式呼叫
    re.compile(r'\bJSON\b'),                      # JSON
    re.compile(r'\bendpoint\b', re.IGNORECASE),   # endpoint
    re.compile(r'\bresponse\b', re.IGNORECASE),   # response
    re.compile(r'\bfunction\b', re.IGNORECASE),   # function
    re.compile(r'\bGET\b|\bPOST\b|\bPUT\b|\bDELETE\b|\bPATCH\b'),  # HTTP methods
    re.compile(r'\bquery\b', re.IGNORECASE),      # query
    re.compile(r'\bschema\b', re.IGNORECASE),     # schema
    re.compile(r'\btoken\b', re.IGNORECASE),      # token
    re.compile(r'\bpayload\b', re.IGNORECASE),    # payload
]

# 入口路徑指示詞
_ENTRY_PATH_INDICATORS: List[str] = [
    "APP 首頁",
    "管理後台",
    "首頁 >",
    "首頁>",
    ">",
    "點選",
    "進入",
    "開啟",
    "點擊",
    "選擇「",
]

# OpenAI 設定
MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY = 2
SIMILARITY_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

KB_GENERATION_PROMPT = """你是 JGB 好租寶租屋管理平台的資深客服人員。

請根據以下模組與問題資訊，生成一則知識庫回答。

## 模組資訊
- 模組名稱：{module_name}
- 模組說明：{module_description}

## 可用功能
{features_list}

## 使用者問題
{question}

## 生成要求

請生成以下格式的知識庫內容：

1. **question_summary**（問題摘要）：提取問題核心主題，不超過 20 個字
2. **answer**（回答內容）：
   - 字數：100-500 字
   - 必須包含明確的操作入口路徑（如「在 APP 首頁 > 繳費 > 帳單明細」或「在管理後台 > 帳務管理 > 帳單列表」）
   - 使用淺顯易懂的語言，像在跟使用者面對面說明
   - 描述具體操作步驟
   - 如果功能可能因業者設定不同而有差異，請說明「視業者設定而定」
3. **keywords**（搜尋關鍵字）：3-6 個繁體中文搜尋關鍵字
4. **category**（所屬模組）：{module_name}
5. **target_user**（適用角色）：依問題內容判斷適用的角色，可選值：tenant, landlord, property_manager, major_landlord, agent
6. **business_types**（適用業態）：依問題內容判斷，可選值：rental, management, social_housing

## 絕對禁止
- ❌ 使用 API 端點路徑（如 /api/v1/bills）
- ❌ 使用程式碼變數名（如 bill_status, getBillList）
- ❌ 使用 JSON、endpoint、response、function、query、schema、token、payload 等工程術語
- ❌ 使用 GET、POST、PUT、DELETE 等 HTTP 方法名稱
- ❌ 只說「請洽管理師」而不提供具體操作說明
- ❌ 編造電話號碼、Email、網址

## 輸出格式

請以 JSON 格式回應：
```json
{{
  "question_summary": "摘要（≤20字）",
  "answer": "回答內容",
  "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"],
  "category": "{module_name}",
  "target_user": ["tenant"],
  "business_types": ["rental", "management"]
}}
```

只輸出 JSON，不要有其他文字。"""


# ---------------------------------------------------------------------------
# SystemKBGenerator
# ---------------------------------------------------------------------------

class SystemKBGenerator:
    """批量生成靜態系統操作 KB"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        batch_size: int = 5,
    ):
        from openai import AsyncOpenAI

        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = MODEL
        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_batch(
        self,
        gaps: List[GapItem],
        module_inventory: List[Module],
        existing_kb: Optional[List[dict]] = None,
        existing_candidates: Optional[List[dict]] = None,
    ) -> List[dict]:
        """批量生成 KB 候選項。

        Parameters
        ----------
        gaps : 所有缺口（會自動過濾 add_kb + static）
        module_inventory : 模組清單（用於 prompt 上下文）
        existing_kb : 既有 KB 條目（用於語義去重）
        existing_candidates : 已生成的候選項（用於 topic_id 去重）

        Returns
        -------
        通過品質驗證的 KB 候選項列表
        """
        # 1. 過濾缺口
        filtered = self._filter_static_kb_gaps(gaps)
        if not filtered:
            return []

        # 2. topic_id 冪等去重
        if existing_candidates:
            existing_topic_ids = {c["topic_id"] for c in existing_candidates}
            filtered = [g for g in filtered if g.topic_id not in existing_topic_ids]

        if not filtered:
            return []

        # 3. 批量生成
        candidates: List[dict] = []

        for batch_start in range(0, len(filtered), self.batch_size):
            batch = filtered[batch_start : batch_start + self.batch_size]
            tasks = []
            for gap in batch:
                module = self._find_module_for_gap(gap, module_inventory)
                tasks.append(self._generate_single(gap, module, existing_kb))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    print(f"  [WARN] 生成失敗：{result}")
                    continue
                if result is not None:
                    candidates.append(result)

        return candidates

    def export_candidates(self, candidates: List[dict], output_path: Path) -> None:
        """將候選項匯出為 JSON 檔案。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(candidates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Gap Filtering
    # ------------------------------------------------------------------

    def _filter_static_kb_gaps(self, gaps: List[GapItem]) -> List[GapItem]:
        """過濾缺口：只保留 recommendation=add_kb 且 query_type=static"""
        return [
            g for g in gaps
            if g.recommendation == "add_kb" and g.query_type == "static"
        ]

    # ------------------------------------------------------------------
    # Module Lookup
    # ------------------------------------------------------------------

    def _find_module_for_gap(
        self, gap: GapItem, modules: List[Module]
    ) -> Optional[Module]:
        """根據 gap.topic_id 前綴找到對應模組。

        topic_id 格式為 "{模組縮寫}_{序號}"，如 "帳務_001"。
        """
        prefix = gap.topic_id.rsplit("_", 1)[0] if "_" in gap.topic_id else gap.topic_id
        module_id = MODULE_ABBR_TO_ID.get(prefix)
        if module_id is None:
            return None
        for m in modules:
            if m.module_id == module_id:
                return m
        return None

    # ------------------------------------------------------------------
    # Prompt Building
    # ------------------------------------------------------------------

    def _build_prompt(self, gap: GapItem, module: Optional[Module]) -> str:
        """為單個缺口建構 LLM prompt。"""
        if module is None:
            module_name = "未知模組"
            module_description = ""
            features_list = "（無功能資訊）"
        else:
            module_name = module.module_name
            module_description = module.description
            lines = []
            for f in module.features:
                entry_display = {
                    "app": "APP",
                    "admin": "管理後台",
                    "both": "APP 與管理後台",
                }.get(f.entry_point, f.entry_point)
                roles = ", ".join(f.roles)
                lines.append(f"- {f.feature_name}（入口：{entry_display}，角色：{roles}）")
            features_list = "\n".join(lines) if lines else "（無功能資訊）"

        return KB_GENERATION_PROMPT.format(
            module_name=module_name,
            module_description=module_description,
            features_list=features_list,
            question=gap.question,
        )

    # ------------------------------------------------------------------
    # Single Generation
    # ------------------------------------------------------------------

    async def _generate_single(
        self,
        gap: GapItem,
        module: Optional[Module],
        existing_kb: Optional[List[dict]],
    ) -> Optional[dict]:
        """生成單個 KB 候選項，含品質驗證與語義去重。"""
        prompt = self._build_prompt(gap, module)

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是 JGB 好租寶的產品客服專家，負責撰寫系統操作知識庫內容。"
                                "只輸出合法 JSON。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=1024,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content.strip()
                parsed = json.loads(content)
                break

            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON parse error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    return None
            except Exception as e:
                print(f"  [WARN] OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    return None

        # 品質驗證
        is_valid, issues = self._validate_quality(parsed)
        if not is_valid:
            print(f"  [SKIP] 品質不合格 ({gap.topic_id}): {'; '.join(issues)}")
            return None

        # 語義去重
        is_dup = await self._check_semantic_dedup(parsed, existing_kb)
        if is_dup:
            print(f"  [SKIP] 語義重複 ({gap.topic_id})")
            return None

        # 組裝候選項
        return {
            "topic_id": gap.topic_id,
            "question_summary": parsed.get("question_summary", ""),
            "answer": parsed.get("answer", ""),
            "keywords": parsed.get("keywords", []),
            "category": parsed.get("category", module.module_name if module else ""),
            "scope": "global",
            "target_user": parsed.get("target_user", []),
            "business_types": parsed.get("business_types", []),
            "status": "pending_review",
            "source_gap": {
                "topic_id": gap.topic_id,
                "question": gap.question,
                "gap_type": gap.gap_type,
                "priority": gap.priority,
            },
        }

    # ------------------------------------------------------------------
    # Quality Validation
    # ------------------------------------------------------------------

    def _validate_quality(self, kb_item: dict) -> Tuple[bool, List[str]]:
        """驗證 KB 品質。回傳 (通過, 問題列表)。"""
        issues: List[str] = []
        answer = kb_item.get("answer", "")
        summary = kb_item.get("question_summary", "")

        # 1. question_summary 不為空
        if not summary or not summary.strip():
            issues.append("question_summary 為空")

        # 2. question_summary <= 20 字
        if summary and len(summary.strip()) > 20:
            issues.append(f"question_summary 超過 20 字（{len(summary.strip())} 字）")

        # 3. answer 長度 >= 50 字
        if len(answer) < 50:
            issues.append(f"answer 長度不足 50 字（{len(answer)} 字）")

        # 4. 不得僅「請洽管理師」
        stripped = re.sub(
            r'(請|可以|建議|隨時).*?(聯繫|聯絡|詢問|洽詢|洽).*?管理師.*',
            '', answer,
        )
        stripped = re.sub(r'(如果|若).*?(問題|疑問|需要).*', '', stripped)
        # 去掉標點
        meaningful = re.sub(r'[。，、！？；：\s]', '', stripped)
        if len(meaningful) < 20:
            issues.append("answer 實質內容不足，僅「請洽管理師」類回覆")

        # 5. 不含工程術語
        if self._check_engineering_terms(answer):
            issues.append("answer 包含工程術語")

        # 6. 含入口路徑
        if not self._check_has_entry_path(answer):
            issues.append("answer 缺少操作入口路徑描述")

        return (len(issues) == 0, issues)

    def _check_engineering_terms(self, text: str) -> bool:
        """檢查文字是否包含工程術語。回傳 True 表示發現術語。"""
        for pattern in _ENGINEERING_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _check_has_entry_path(self, text: str) -> bool:
        """檢查文字是否包含入口路徑描述。"""
        return any(indicator in text for indicator in _ENTRY_PATH_INDICATORS)

    # ------------------------------------------------------------------
    # Semantic Deduplication
    # ------------------------------------------------------------------

    async def _check_semantic_dedup(
        self,
        kb_item: dict,
        existing_kb: Optional[List[dict]],
    ) -> bool:
        """檢查是否與既有 KB 語義重複（similarity >= 0.85）。

        回傳 True 表示重複，應跳過。
        """
        if not existing_kb:
            return False

        question = kb_item.get("question_summary", "")
        for existing in existing_kb:
            sim = self._compute_similarity(
                question,
                existing.get("question_summary", ""),
            )
            if sim >= SIMILARITY_THRESHOLD:
                return True

        return False

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """計算兩段文字的相似度。

        預設使用簡單的字元重疊比率。
        實際生產環境應替換為 embedding cosine similarity。
        """
        if not text1 or not text2:
            return 0.0
        set1 = set(text1)
        set2 = set(text2)
        intersection = set1 & set2
        union = set1 | set2
        if not union:
            return 0.0
        return len(intersection) / len(union)
