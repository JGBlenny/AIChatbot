#!/usr/bin/env python3
"""
測試不同錯誤嚴重程度的相似度
"""
import asyncio
import httpx
import numpy as np

async def get_embedding(text: str) -> list:
    """獲取文本的 embedding"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5001/api/v1/embeddings",
            json={"text": text}
        )
        if response.status_code != 200:
            raise Exception(f"Embedding API error: {response.status_code}")
        data = response.json()
        return data['embedding']

def cosine_similarity(vec1: list, vec2: list) -> float:
    """計算餘弦相似度"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)

def levenshtein_distance(s1: str, s2: str) -> int:
    """計算編輯距離（Levenshtein Distance）"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

async def test_questions(original: str, variations: list):
    """測試原始問題和變體的相似度"""
    print(f"\n原始問題: {original}")
    print("=" * 80)

    # 獲取原始問題的 embedding
    original_emb = await get_embedding(original)

    for idx, variant in enumerate(variations, 1):
        variant_emb = await get_embedding(variant)

        sem_sim = cosine_similarity(original_emb, variant_emb)
        edit_dist = levenshtein_distance(original, variant)

        # 判斷各種策略是否能捕捉
        strategy_results = {
            "語義 0.85": "✅" if sem_sim >= 0.85 else "❌",
            "語義 0.80": "✅" if sem_sim >= 0.80 else "❌",
            "編輯≤2": "✅" if edit_dist <= 2 else "❌",
            "組合(0.80或編輯≤2)": "✅" if (sem_sim >= 0.80 or edit_dist <= 2) else "❌"
        }

        print(f"\n變體 {idx}: {variant}")
        print(f"  語義相似度: {sem_sim:.4f}")
        print(f"  編輯距離: {edit_dist}")
        print(f"  策略判斷: ", end="")
        for strategy, result in strategy_results.items():
            print(f"{strategy}={result}  ", end="")
        print()

async def main():
    print("=" * 80)
    print("測試不同錯誤嚴重程度的檢測效果")
    print("=" * 80)

    # 測試集 1: 輕微打字錯誤（相鄰鍵位誤觸）
    await test_questions(
        "每月租金幾號要繳",
        [
            "每月租金幾號要繳",  # 完全相同
            "每月租金幾號較腳",  # 同音錯誤（"要繳" → "較腳"）
            "美越租金幾號較腳",  # 同音錯誤（"每月" → "美越" + "要繳" → "較腳"）
            "每月住金幾號要繳",  # 同音近似（"租" → "住"）
            "每月租金幾好要繳",  # 相鄰鍵位（"號" → "好"）
        ]
    )

    # 測試集 2: 語義保留但用詞不同
    await test_questions(
        "每月租金幾號要繳",
        [
            "租金每個月幾號繳納",  # 換句話說
            "什麼時候要繳租金",      # 完全不同表達
            "房租繳費日期是幾號",    # 同義詞替換
        ]
    )

    print("\n" + "=" * 80)
    print("結論分析")
    print("=" * 80)
    print("""
1. 輕微打字錯誤（1-2字符）:
   - 語義相似度通常在 0.80-0.90 之間
   - 編輯距離 ≤ 2
   - 組合策略可以捕捉 ✅

2. 嚴重同音錯誤（3+字符）:
   - 語義相似度可能 < 0.80
   - 編輯距離 > 2
   - 組合策略無法捕捉 ❌
   - 需要額外的同音檢測機制

3. 語義保留的改寫:
   - 編輯距離很大
   - 但語義相似度高（> 0.85）
   - 純語義策略可以捕捉 ✅

建議方案：
- 階段 1: 實施組合策略（語義 0.80 OR 編輯距離 ≤ 2）
          → 可解決大部分輕微錯誤

- 階段 2: 增加拼音/音似檢測（如果需要）
          → 解決嚴重同音錯誤
          → 但實施成本高、可能誤判

- 階段 3: 考慮預處理拼字修正
          → 在記錄前先修正明顯錯誤
    """)

if __name__ == "__main__":
    asyncio.run(main())
