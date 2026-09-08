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
    suggested_emergency: int  # 2=緊急, 1=非緊急（對齊 jgb2 DB 真值）
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
    "suggested_emergency": 1,
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
  "suggested_emergency": 1,
  "secondary_damages": []
}}

suggested_emergency：2=緊急、1=非緊急（對齊 jgb2 DB 真值）。
severity 判斷標準：
- critical：影響安全或生活（如水管爆裂、電線外露、大面積漏水）→ suggested_emergency=2
- high：明顯損壞需要儘快修繕（如設備完全失靈）→ suggested_emergency=1
- medium：一般損壞可安排修繕（如牆面裂痕、小範圍滲水）→ suggested_emergency=1
- low：輕微損壞或磨損（如油漆剝落、小刮痕）→ suggested_emergency=1"""


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


#: gpt-5 系列的參數不相容（S9-16）：`max_tokens` 被拒、`temperature` 只收預設值。
#: ⛔ 不在呼叫點各寫一次 if——分歧一定會發生在只改了其中一處的那天。
_MAX_OUTPUT_TOKENS = 500


def _completion_params(model: str) -> dict:
    """依模型回 `chat.completions.create` 的輸出長度／取樣參數。

    gpt-5 系列 ⇒ `max_completion_tokens`、**不傳 `temperature`**；
    其餘（gpt-4o／4o-mini…）⇒ `max_tokens` ＋ `temperature=0.2`（逐值同舊版）。
    """
    if str(model or "").startswith("gpt-5"):
        return {"max_completion_tokens": _MAX_OUTPUT_TOKENS}
    return {"max_tokens": _MAX_OUTPUT_TOKENS, "temperature": 0.2}


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
        max_retries: Optional[int] = None,
    ):
        self.model = model or os.getenv("IMAGE_RECOGNITION_MODEL", "gpt-4o")
        self.detail = detail or os.getenv("IMAGE_RECOGNITION_DETAIL", "low")
        self.timeout = timeout

        # `max_retries`（Plan W8 (2)／S9-7）：`/mcp` 路徑**顯式傳 1**——帶圖回合
        # 有時間預算（`image_budget`），SDK 預設的重試次數會把預算悄悄吃掉。
        # ⛔ 不改預設值：REST 路徑（`routers/chat.py`）不在本項範圍，
        # 沒傳就維持 SDK 既有行為。
        client_kwargs: dict = {"api_key": os.getenv("OPENAI_API_KEY")}
        if max_retries is not None:
            client_kwargs["max_retries"] = int(max_retries)
        self.client = AsyncOpenAI(**client_kwargs)

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
        *,
        max_images: Optional[int] = 3,
        detail: Optional[str] = None,
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

        # `max_images=None` ⇒ **不截斷**（Plan W8 (2)／S9-6：`/mcp` 路徑一次可到
        # 10 張，由呼叫端每 5 張一批送進來；⛔ 不在這裡再截一次）。
        # 預設 3＝REST 路徑既有行為，⛔ 不變。
        urls = list(image_urls) if max_images is None else list(image_urls[:max_images])
        # `detail` 具名參數優先於建構值（`/mcp` 路徑程式釘 `low`，⛔ 不由 env，S9-8）。
        image_detail = detail or self.detail

        # 組裝 prompt
        prompt_text = build_prompt(category_names, categories_tree)
        if context:
            prompt_text += f"\n\n用戶描述：{context}"

        # 組裝 content 陣列
        content = [{"type": "text", "text": prompt_text}]
        for url in urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": image_detail},
            })

        messages = [{"role": "user", "content": content}]

        # 呼叫 Vision API，設 timeout
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    **_completion_params(self.model),
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Vision API 逾時 ({self.timeout}s)，降級為文字流程")
            raise
        except Exception as e:
            # ⛔⛔ **只記例外類別名**（S9-10／10b）：bytes 模型下 `str(e)` 可能把
            #     整串 base64 data URL（＝照片本身）寫進 log。
            logger.error("Vision API 呼叫失敗: %s", type(e).__name__)
            raise

        # 解析結果
        raw_text = response.choices[0].message.content
        usage = response.usage

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            # ⛔ 不印回傳原文：那是**照片內容衍生的自由文字**（照片裡的字也在內），
            #    S9-10 的同一條紀律。只留長度。
            logger.error("Vision API 回傳非 JSON（長度 %d）", len(raw_text or ""))
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
        cost_usd = self._estimate_cost(
            getattr(usage, "prompt_tokens", 0) if usage else 0,
            getattr(usage, "completion_tokens", 0) if usage else 0,
        )

        # ⛔ 不印 `description`／`suggested_item`／`suggested_reason` 等**自由文字**
        #    （模型從照片讀出來的字會原樣進 log，S9-10 的同一條紀律）；
        #    只留封閉值域欄位與計數。
        logger.info(
            "圖像辨識完成 | damage=%s type=%s conf=%.2f tokens=%d cost=$%.6f",
            recognition["is_damage"], recognition["damage_type"],
            recognition["confidence"], total_tokens, cost_usd,
        )

        # 寫入 DB：openai_cost_tracking + image_uploads
        if db_pool and total_tokens > 0:
            await self._record_cost(
                db_pool, recognition, total_tokens, cost_usd, image_id, usage
            )

        return recognition

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """依**模型價目表**估成本（USD）；表裡沒有這個模型 ⇒ 回退舊的平頭費率。

        S9-9：舊版對每個模型都用 `$5/1M` 的混合費率，換模型（gpt-5-mini 便宜一個
        數量級）後那個數字就只是個好看的假值。價目表的唯一來源是
        `services.usage_metering.DEFAULT_PRICING`（USD／1M tokens，`(prompt, completion)`），
        ⛔ 不在本檔另抄一份費率。
        """
        from services.usage_metering import DEFAULT_PRICING

        price = DEFAULT_PRICING.get(self.model)
        if price is None:
            return ((int(prompt_tokens) + int(completion_tokens)) / 1_000_000) * 5.0
        return (int(prompt_tokens) / 1_000_000) * price[0] + (
            int(completion_tokens) / 1_000_000
        ) * price[1]

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
            logger.error("成本記錄寫入失敗: %s", type(e).__name__)
            # 不阻塞主流程
