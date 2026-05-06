"""
圖像辨識服務

使用 GPT-4o Vision API 分析損壞現場照片，產出結構化辨識結果
支援動態 prompt（注入實際修繕分類名稱）、逾時控制、成本追蹤
"""
import os
import json
import asyncio
import logging
from typing import Optional, List, TypedDict

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


# ============================================================
# 資料模型
# ============================================================

class RecognitionResult(TypedDict, total=False):
    is_damage: bool
    damage_type: str        # water_leak/equipment_failure/wall_damage/electrical/plumbing/door_window/floor/other/none
    severity: str           # low/medium/high/critical
    description: str        # 繁體中文損壞描述
    confidence: float       # 0.0 - 1.0
    suggested_category: str # 建議的修繕分類名稱
    suggested_item: str     # 建議的損壞項目（如「天花板」「馬桶」）
    suggested_reason: str   # 建議的損壞原因（如「漏水」「堵塞」）
    suggested_emergency: int  # 1=緊急, 2=非緊急
    secondary_damages: List[str]


# 非損壞的預設回傳
_NOT_DAMAGE_RESULT: RecognitionResult = {
    "is_damage": False,
    "damage_type": "none",
    "severity": "low",
    "description": "",
    "confidence": 0.0,
    "suggested_category": "",
    "suggested_item": "",
    "suggested_reason": "",
    "suggested_emergency": 2,
    "secondary_damages": [],
}

# 功能開關
def is_image_recognition_enabled() -> bool:
    return os.getenv("ENABLE_IMAGE_RECOGNITION", "false").lower() == "true"


# ============================================================
# Prompt 建構
# ============================================================

_BASE_PROMPT = """你是一個租屋損壞辨識專家。請分析以下圖片，判斷是否為房屋損壞情境。

支援辨識的損壞類型：
- water_leak：漏水（天花板滲水、牆面水漬、管線漏水）
- equipment_failure：設備故障（冷氣不運作、熱水器異常、馬桶堵塞）
- wall_damage：牆面損壞（裂痕、剝落、發霉）
- electrical：電力問題（插座燒焦、開關損壞、線路外露）
- door_window：門窗損壞（門鎖故障、玻璃破裂、鉸鏈損壞）
- floor：地板損壞（磁磚破裂、木地板翹起）
- plumbing：水管問題
- other：其他損壞

{category_instruction}

請以 JSON 格式回傳（不要包含 markdown 標記）：

若為損壞情境：
{{
  "is_damage": true,
  "damage_type": "損壞類型代碼",
  "severity": "low|medium|high|critical",
  "description": "繁體中文描述，50-100字，描述損壞狀況與可能原因",
  "confidence": 0.0到1.0之間的數字,
  "suggested_category": "建議的修繕分類名稱",
  "suggested_item": "建議的損壞項目（必須屬於 suggested_category 底下的項目，如天花板、馬桶、冷氣等）",
  "suggested_reason": "建議的損壞原因（必須屬於 suggested_item 底下的原因，如漏水、堵塞、剝落等）",
  "suggested_emergency": 1或2,
  "secondary_damages": ["其他可能的損壞類型代碼"]
}}

若非損壞情境：
{{
  "is_damage": false,
  "damage_type": "none",
  "severity": "low",
  "description": "",
  "confidence": 0.0,
  "suggested_category": "",
  "suggested_item": "",
  "suggested_reason": "",
  "suggested_emergency": 2,
  "secondary_damages": []
}}

severity 判斷標準：
- critical：影響安全或生活（如水管爆裂、電線外露、大面積漏水）→ suggested_emergency=1
- high：明顯損壞需要儘快修繕（如設備完全失靈）→ suggested_emergency=2
- medium：一般損壞可安排修繕（如牆面裂痕、小範圍滲水）→ suggested_emergency=2
- low：輕微損壞或磨損（如油漆剝落、小刮痕）→ suggested_emergency=2"""


def build_prompt(category_names: Optional[List[str]] = None, categories_tree: Optional[list] = None) -> str:
    """
    建構 Vision API prompt，支援注入實際修繕分類名稱及樹狀結構。

    Args:
        category_names: JGB 修繕分類名稱列表（如 ["水電類", "土木類", "設備類"]）
        categories_tree: 完整分類樹（含 items 和 broken_reasons），用於精準匹配 item 和 reason
    """
    if category_names:
        names_str = "、".join(category_names)
        instruction = f"可選的修繕分類名稱（suggested_category 必須從以下選項中選擇）：{names_str}"
    else:
        instruction = "suggested_category 請填入你判斷最合適的修繕分類名稱（如「水電類」「設備類」「土木類」等）"

    # 注入完整分類樹以幫助 Vision 精準選擇 item 和 reason
    if categories_tree:
        tree_lines = []
        for cat in categories_tree:
            cat_name = cat.get("name", "")
            items_info = []
            for item in cat.get("items", []):
                reasons = item.get("broken_reasons", [])
                reasons_str = "、".join(reasons) if reasons else ""
                item_line = f"    - {item.get('name', '')}"
                if reasons_str:
                    item_line += f"（原因：{reasons_str}）"
                items_info.append(item_line)
            tree_lines.append(f"  - {cat_name}:\n" + "\n".join(items_info))
        instruction += "\n\n分類樹狀結構（suggested_item 必須從對應 category 的 items 中選擇，suggested_reason 必須從對應 item 的 broken_reasons 中選擇）：\n" + "\n".join(tree_lines)

    return _BASE_PROMPT.format(category_instruction=instruction)


# ============================================================
# 辨識服務
# ============================================================

class ImageRecognitionService:
    """GPT-4o Vision 圖像辨識服務"""

    def __init__(
        self,
        model: Optional[str] = None,
        detail: Optional[str] = None,
        timeout: int = 15,
    ):
        self.model = model or os.getenv("IMAGE_RECOGNITION_MODEL", "gpt-4o")
        self.detail = detail or os.getenv("IMAGE_RECOGNITION_DETAIL", "low")
        self.timeout = timeout

        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def analyze_image(
        self,
        image_url: str,
        context: Optional[str] = None,
        category_names: Optional[List[str]] = None,
        categories_tree: Optional[list] = None,
        db_pool=None,
        image_id: Optional[int] = None,
    ) -> RecognitionResult:
        """
        分析單張圖片。

        Args:
            image_url: 圖片 S3 URL
            context: 用戶文字描述（輔助判斷）
            category_names: 可選的修繕分類名稱列表
            categories_tree: 完整分類樹（含 items 和 broken_reasons）
            db_pool: asyncpg 連接池（用於成本記錄）
            image_id: image_uploads 表 ID（用於回寫辨識結果）

        Returns:
            RecognitionResult 結構化辨識結果

        Raises:
            asyncio.TimeoutError: 逾時 15 秒
        """
        return await self.analyze_images(
            [image_url], context, category_names, categories_tree, db_pool, image_id
        )

    async def analyze_images(
        self,
        image_urls: List[str],
        context: Optional[str] = None,
        category_names: Optional[List[str]] = None,
        categories_tree: Optional[list] = None,
        db_pool=None,
        image_id: Optional[int] = None,
    ) -> RecognitionResult:
        """
        分析多張圖片（同一損壞情境），最多 3 張。

        Args:
            image_urls: 圖片 URL 列表
            context: 用戶文字描述
            category_names: 修繕分類名稱列表
            categories_tree: 完整分類樹（含 items 和 broken_reasons）
            db_pool: asyncpg 連接池（用於成本記錄）
            image_id: image_uploads 表 ID（用於回寫辨識結果）

        Returns:
            RecognitionResult
        """
        if not image_urls:
            return dict(_NOT_DAMAGE_RESULT)

        urls = image_urls[:3]

        # 組裝 prompt
        prompt_text = build_prompt(category_names, categories_tree)
        if context:
            prompt_text += f"\n\n用戶描述：{context}"

        # 組裝 content 陣列
        content = [{"type": "text", "text": prompt_text}]
        for url in urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": self.detail},
            })

        messages = [{"role": "user", "content": content}]

        # 呼叫 Vision API，設 timeout
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=500,
                    temperature=0.2,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Vision API 逾時 ({self.timeout}s)，降級為文字流程")
            raise
        except Exception as e:
            logger.error(f"Vision API 呼叫失敗: {e}")
            raise

        # 解析結果
        raw_text = response.choices[0].message.content
        usage = response.usage

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error(f"Vision API 回傳非 JSON: {raw_text[:200]}")
            return dict(_NOT_DAMAGE_RESULT)

        # 正規化欄位
        recognition: RecognitionResult = {
            "is_damage": bool(result.get("is_damage", False)),
            "damage_type": str(result.get("damage_type", "none")),
            "severity": str(result.get("severity", "low")),
            "description": str(result.get("description", "")),
            "confidence": float(result.get("confidence", 0.0)),
            "suggested_category": str(result.get("suggested_category", "")),
            "suggested_item": str(result.get("suggested_item", "")),
            "suggested_reason": str(result.get("suggested_reason", "")),
            "suggested_emergency": int(result.get("suggested_emergency", 2)),
            "secondary_damages": list(result.get("secondary_damages", [])),
        }

        # 成本追蹤
        total_tokens = usage.total_tokens if usage else 0
        cost_usd = self._estimate_cost(total_tokens)

        logger.info(
            f"圖像辨識完成 | damage={recognition['is_damage']} "
            f"type={recognition['damage_type']} conf={recognition['confidence']:.2f} "
            f"item={recognition['suggested_item']} reason={recognition['suggested_reason']} "
            f"tokens={total_tokens} cost=${cost_usd:.6f}"
        )

        # 寫入 DB：openai_cost_tracking + image_uploads
        if db_pool and total_tokens > 0:
            await self._record_cost(
                db_pool, recognition, total_tokens, cost_usd, image_id, usage
            )

        return recognition

    def _estimate_cost(self, total_tokens: int) -> float:
        """根據 token 數估算成本（USD）"""
        # GPT-4o vision pricing: $2.50/1M prompt + $10/1M completion
        # 簡化為混合費率（大部分是 prompt tokens）
        return (total_tokens / 1_000_000) * 5.0  # 平均 $5/1M tokens

    async def _record_cost(
        self, db_pool, recognition, total_tokens, cost_usd, image_id, usage
    ):
        """記錄辨識成本至資料庫"""
        try:
            async with db_pool.acquire() as conn:
                # 1) 寫入 openai_cost_tracking
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0

                await conn.execute(
                    """
                    INSERT INTO openai_cost_tracking
                        (operation, model, prompt_tokens, completion_tokens, cost_usd)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    "image_recognition", self.model,
                    prompt_tokens, completion_tokens, cost_usd,
                )

                # 2) 回寫 image_uploads（辨識結果 + token + 成本）
                if image_id:
                    await conn.execute(
                        """
                        UPDATE image_uploads
                        SET recognition_result = $1,
                            recognition_model = $2,
                            recognition_tokens = $3,
                            recognition_cost_usd = $4
                        WHERE id = $5
                        """,
                        json.dumps(recognition, ensure_ascii=False),
                        self.model, total_tokens, cost_usd, image_id,
                    )
        except Exception as e:
            logger.error(f"成本記錄寫入失敗: {e}")
            # 不阻塞主流程
