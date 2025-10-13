#!/usr/bin/env python3
"""
測試打字錯誤問題的相似度
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
            print(f"Error: {response.status_code} - {response.text}")
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
            # 插入、刪除、替換的成本
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def character_overlap_similarity(s1: str, s2: str) -> float:
    """計算字符重疊相似度（Jaccard）"""
    set1 = set(s1)
    set2 = set(s2)

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0

async def main():
    question1 = "每月租金幾號要繳"
    question2 = "每月租金幾號較腳"

    print("=" * 60)
    print("測試打字錯誤問題的相似度")
    print("=" * 60)
    print(f"問題 1: {question1}")
    print(f"問題 2: {question2}")
    print("=" * 60)

    # 1. Embedding 相似度
    print("\n📊 1. Embedding 語義相似度")
    print("   正在獲取 embeddings...")
    emb1 = await get_embedding(question1)
    emb2 = await get_embedding(question2)

    semantic_sim = cosine_similarity(emb1, emb2)
    print(f"   餘弦相似度: {semantic_sim:.4f}")
    print(f"   {'✅ 高於 0.85 閾值' if semantic_sim >= 0.85 else '❌ 低於 0.85 閾值'}")
    print(f"   {'✅ 高於 0.80 閾值' if semantic_sim >= 0.80 else '❌ 低於 0.80 閾值'}")

    # 2. 編輯距離
    print("\n📝 2. 編輯距離（Levenshtein Distance）")
    edit_dist = levenshtein_distance(question1, question2)
    print(f"   編輯距離: {edit_dist}")
    print(f"   差異字符數: {edit_dist}")
    print(f"   {'✅ 編輯距離 < 3' if edit_dist < 3 else '❌ 編輯距離 >= 3'}")

    # 3. 字符重疊相似度
    print("\n🔤 3. 字符重疊相似度（Jaccard）")
    char_sim = character_overlap_similarity(question1, question2)
    print(f"   Jaccard 相似度: {char_sim:.4f}")
    print(f"   共同字符: {set(question1) & set(question2)}")
    print(f"   差異字符: {set(question1) ^ set(question2)}")

    # 4. 綜合判斷
    print("\n🎯 4. 綜合判斷")
    print("   目前系統：")
    print(f"      - 只使用語義相似度（閾值 0.85）: {'✅ 會合併' if semantic_sim >= 0.85 else '❌ 不會合併'}")

    print("\n   建議改進方案：")
    should_merge_improved = (semantic_sim >= 0.80) or (edit_dist <= 2)
    print(f"      - 語義相似度 >= 0.80 OR 編輯距離 <= 2: {'✅ 會合併' if should_merge_improved else '❌ 不會合併'}")

    # 5. 顯示差異
    print("\n🔍 5. 字符差異分析")
    print(f"   問題 1: {question1}")
    print(f"   問題 2: {question2}")
    print(f"   差異點: ", end="")
    for i, (c1, c2) in enumerate(zip(question1, question2)):
        if c1 != c2:
            print(f"位置 {i}: '{c1}' → '{c2}'", end="; ")
    print()

    print("\n" + "=" * 60)
    print("結論:")
    if semantic_sim >= 0.85:
        print("✅ 目前系統可正確識別為重複問題")
    else:
        print("❌ 目前系統無法識別為重複問題")
        print("💡 建議實施改進方案（降低閾值或增加編輯距離檢測）")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
