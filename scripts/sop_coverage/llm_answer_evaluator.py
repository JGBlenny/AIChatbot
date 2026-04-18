"""
聚焦 LLM 答案品質判定
判斷「這個回答是否從租客角度回答了租客的問題」
"""
import asyncio
import json
import os
from typing import List, Dict, Literal, TypedDict

import openai


class LLMJudgment(TypedDict):
    verdict: str  # "yes" | "partial" | "no"
    reason: str   # 50 字以內


EVALUATION_PROMPT = """你是包租代管業的客服品質審核員。

請判斷以下 AI 客服的回答是否從租客角度回答了租客的問題。

## 判定標準
- **yes**：回答直接且具體地回應了租客的問題，租客看完知道該怎麼做
- **partial**：回答有觸及相關主題，但遺漏了問題的核心、偏離重點、或過於模糊
- **no**：回答完全沒有回應租客的問題，答非所問

## 租客問題
{question}

## AI 客服回答
{answer}

## 請回答
用以下 JSON 格式回答（不要加其他文字）：
{{"verdict": "yes/partial/no", "reason": "一句話說明理由（50字以內）"}}"""


async def evaluate_answer_quality(
    question: str,
    answer: str,
    model: str = "gpt-4o-mini",
) -> LLMJudgment:
    """
    單筆答案判定

    Args:
        question: 租客問題
        answer: AI 客服回答
        model: OpenAI 模型

    Returns:
        LLMJudgment: {"verdict": "yes/partial/no", "reason": "..."}
    """
    if not question or not answer:
        return {"verdict": "no", "reason": "問題或答案為空"}

    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": EVALUATION_PROMPT.format(
                        question=question,
                        answer=answer,
                    ),
                }
            ],
            temperature=0.0,
            max_tokens=150,
        )

        content = response.choices[0].message.content.strip()
        # 解析 JSON
        result = json.loads(content)

        verdict = result.get("verdict", "partial")
        if verdict not in ("yes", "partial", "no"):
            verdict = "partial"

        reason = result.get("reason", "")[:50]

        return {"verdict": verdict, "reason": reason}

    except (json.JSONDecodeError, KeyError, IndexError):
        return {"verdict": "partial", "reason": "LLM 回傳格式異常，無法解析"}
    except Exception as e:
        return {"verdict": "partial", "reason": f"判定失敗: {str(e)[:30]}"}


async def evaluate_batch(
    results: List[Dict],
    concurrency: int = 5,
    model: str = "gpt-4o-mini",
) -> List[Dict]:
    """
    批量判定回測結果

    Args:
        results: 回測結果列表，每筆需包含 test_question 和 system_answer
        concurrency: 最大並發數
        model: OpenAI 模型

    Returns:
        每筆結果新增 llm_judgment 欄位
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def eval_one(result: Dict) -> Dict:
        async with semaphore:
            question = result.get("test_question", "")
            answer = result.get("system_answer", "")

            judgment = await evaluate_answer_quality(question, answer, model)
            result["llm_judgment"] = judgment

            # 當 LLM 判定為 no 時，final_passed 改為 fail
            if judgment["verdict"] == "no":
                result["final_passed"] = False
            else:
                result["final_passed"] = result.get("passed", False)

            return result

    tasks = [eval_one(r) for r in results]
    evaluated = await asyncio.gather(*tasks)

    # 統計
    stats = {"yes": 0, "partial": 0, "no": 0}
    for r in evaluated:
        v = r.get("llm_judgment", {}).get("verdict", "partial")
        stats[v] = stats.get(v, 0) + 1

    total = len(evaluated)
    print(f"[LLM 判定] 共 {total} 筆")
    print(f"  yes: {stats['yes']} ({stats['yes']/max(total,1)*100:.1f}%)")
    print(f"  partial: {stats['partial']} ({stats['partial']/max(total,1)*100:.1f}%)")
    print(f"  no: {stats['no']} ({stats['no']/max(total,1)*100:.1f}%)")

    return evaluated
