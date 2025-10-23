"""
統一去重配置模組
Unified Deduplication Configuration Module

提供系統所有去重相關的閾值配置，確保配置的一致性和可維護性。
所有閾值從環境變數讀取，並提供預設值。

使用範例：
    from config.deduplication_config import DedupConfig

    config = DedupConfig()
    threshold = config.intent_suggestion_similarity
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class DedupConfig:
    """
    統一去重配置類別

    所有閾值配置的單一來源，從環境變數載入並提供預設值。
    """

    # ==================== 意圖建議去重 ====================
    # Intent Suggestion Deduplication
    intent_suggestion_similarity: float = 0.80
    """
    意圖建議語義相似度閾值
    - 用途: 判斷新建議是否與現有建議語義重複
    - 預設: 0.80
    - 推薦範圍: 0.75 - 0.85
    - 環境變數: INTENT_SUGGESTION_SIMILARITY_THRESHOLD
    """

    # ==================== 未釐清問題去重 ====================
    # Unclear Question Deduplication
    unclear_semantic_similarity: float = 0.80
    """
    未釐清問題語義相似度閾值
    - 用途: 判斷新問題是否與現有問題語義相似
    - 預設: 0.80
    - 推薦範圍: 0.75 - 0.85
    - 環境變數: UNCLEAR_SEMANTIC_THRESHOLD
    """

    unclear_pinyin_similarity: float = 0.80
    """
    未釐清問題拼音相似度閾值
    - 用途: 檢測同音錯誤（配合語義相似度 0.60-0.80）
    - 預設: 0.80
    - 推薦範圍: 0.75 - 0.90
    - 環境變數: UNCLEAR_PINYIN_THRESHOLD
    """

    unclear_semantic_pinyin_lower: float = 0.60
    """
    拼音檢測的語義相似度下限
    - 用途: 當語義 0.60-0.80 且拼音 ≥ 0.80 時判定為同音錯誤
    - 預設: 0.60
    - 固定值（不從環境變數讀取）
    """

    # ==================== RAG 檢索閾值 ====================
    # RAG Retrieval Thresholds
    rag_similarity_threshold: float = 0.6
    """
    RAG 檢索最低相似度要求
    - 用途: 向量檢索時的最低相似度門檻
    - 預設: 0.6
    - 推薦範圍: 0.5 - 0.7
    - 環境變數: RAG_SIMILARITY_THRESHOLD
    """

    # ==================== 答案合成閾值 ====================
    # Answer Synthesis Threshold
    synthesis_threshold: float = 0.80
    """
    答案合成觸發閾值
    - 用途: 當多個 SOP 項目相似度 ≥ 此值時觸發合成
    - 預設: 0.80
    - 推薦範圍: 0.75 - 0.85
    - 環境變數: SYNTHESIS_THRESHOLD
    """

    # ==================== 信心度評估閾值 ====================
    # Confidence Evaluation Thresholds
    confidence_high_threshold: float = 0.85
    """
    高信心度閾值
    - 用途: 相似度 ≥ 此值判定為高信心度
    - 預設: 0.85
    - 環境變數: CONFIDENCE_HIGH_THRESHOLD
    """

    confidence_medium_threshold: float = 0.70
    """
    中等信心度閾值
    - 用途: 相似度 ≥ 此值判定為中等信心度
    - 預設: 0.70
    - 環境變數: CONFIDENCE_MEDIUM_THRESHOLD
    """

    # ==================== 條件式優化閾值 ====================
    # Conditional Optimization Thresholds
    fast_path_threshold: float = 0.75
    """
    快速路徑閾值
    - 用途: 相似度 ≥ 此值跳過 LLM 處理（直接返回）
    - 預設: 0.75
    - 推薦範圍: 0.70 - 0.80
    - 環境變數: FAST_PATH_THRESHOLD
    """

    template_min_score: float = 0.55
    """
    模板格式化最低分數
    - 用途: 相似度 ≥ 此值使用模板格式化
    - 預設: 0.55
    - 環境變數: TEMPLATE_MIN_SCORE
    """

    template_max_score: float = 0.75
    """
    模板格式化最高分數
    - 用途: 相似度 < 此值使用模板，≥ 此值進入快速路徑
    - 預設: 0.75
    - 環境變數: TEMPLATE_MAX_SCORE
    """

    def __init__(self):
        """
        從環境變數初始化配置
        如果環境變數不存在，使用類別定義的預設值
        """
        # 意圖建議去重
        self.intent_suggestion_similarity = float(
            os.getenv("INTENT_SUGGESTION_SIMILARITY_THRESHOLD", self.intent_suggestion_similarity)
        )

        # 未釐清問題去重
        self.unclear_semantic_similarity = float(
            os.getenv("UNCLEAR_SEMANTIC_THRESHOLD", self.unclear_semantic_similarity)
        )
        self.unclear_pinyin_similarity = float(
            os.getenv("UNCLEAR_PINYIN_THRESHOLD", self.unclear_pinyin_similarity)
        )

        # RAG 檢索
        self.rag_similarity_threshold = float(
            os.getenv("RAG_SIMILARITY_THRESHOLD", self.rag_similarity_threshold)
        )

        # 答案合成
        self.synthesis_threshold = float(
            os.getenv("SYNTHESIS_THRESHOLD", self.synthesis_threshold)
        )

        # 信心度評估
        self.confidence_high_threshold = float(
            os.getenv("CONFIDENCE_HIGH_THRESHOLD", self.confidence_high_threshold)
        )
        self.confidence_medium_threshold = float(
            os.getenv("CONFIDENCE_MEDIUM_THRESHOLD", self.confidence_medium_threshold)
        )

        # 條件式優化
        self.fast_path_threshold = float(
            os.getenv("FAST_PATH_THRESHOLD", self.fast_path_threshold)
        )
        self.template_min_score = float(
            os.getenv("TEMPLATE_MIN_SCORE", self.template_min_score)
        )
        self.template_max_score = float(
            os.getenv("TEMPLATE_MAX_SCORE", self.template_max_score)
        )

    def to_dict(self) -> Dict[str, float]:
        """
        將配置轉換為字典格式

        Returns:
            包含所有閾值配置的字典
        """
        return {
            # 意圖建議去重
            "intent_suggestion_similarity": self.intent_suggestion_similarity,

            # 未釐清問題去重
            "unclear_semantic_similarity": self.unclear_semantic_similarity,
            "unclear_pinyin_similarity": self.unclear_pinyin_similarity,
            "unclear_semantic_pinyin_lower": self.unclear_semantic_pinyin_lower,

            # RAG 檢索
            "rag_similarity_threshold": self.rag_similarity_threshold,

            # 答案合成
            "synthesis_threshold": self.synthesis_threshold,

            # 信心度評估
            "confidence_high_threshold": self.confidence_high_threshold,
            "confidence_medium_threshold": self.confidence_medium_threshold,

            # 條件式優化
            "fast_path_threshold": self.fast_path_threshold,
            "template_min_score": self.template_min_score,
            "template_max_score": self.template_max_score,
        }

    def get_dedup_thresholds(self) -> Dict[str, float]:
        """
        取得所有去重相關閾值

        Returns:
            僅包含去重相關閾值的字典
        """
        return {
            "intent_suggestion": self.intent_suggestion_similarity,
            "unclear_semantic": self.unclear_semantic_similarity,
            "unclear_pinyin": self.unclear_pinyin_similarity,
        }

    def get_rag_thresholds(self) -> Dict[str, float]:
        """
        取得所有 RAG 相關閾值

        Returns:
            包含 RAG 檢索、信心度、優化相關閾值的字典
        """
        return {
            "retrieval": self.rag_similarity_threshold,
            "synthesis": self.synthesis_threshold,
            "confidence_high": self.confidence_high_threshold,
            "confidence_medium": self.confidence_medium_threshold,
            "fast_path": self.fast_path_threshold,
            "template_min": self.template_min_score,
            "template_max": self.template_max_score,
        }

    def validate(self) -> Dict[str, Any]:
        """
        驗證配置的合理性

        Returns:
            驗證結果字典，包含是否通過和警告訊息
        """
        warnings = []
        errors = []

        # 1. 檢查閾值範圍
        if not (0.0 <= self.intent_suggestion_similarity <= 1.0):
            errors.append(f"intent_suggestion_similarity 超出範圍 [0, 1]: {self.intent_suggestion_similarity}")

        if not (0.0 <= self.unclear_semantic_similarity <= 1.0):
            errors.append(f"unclear_semantic_similarity 超出範圍 [0, 1]: {self.unclear_semantic_similarity}")

        if not (0.0 <= self.unclear_pinyin_similarity <= 1.0):
            errors.append(f"unclear_pinyin_similarity 超出範圍 [0, 1]: {self.unclear_pinyin_similarity}")

        if not (0.0 <= self.rag_similarity_threshold <= 1.0):
            errors.append(f"rag_similarity_threshold 超出範圍 [0, 1]: {self.rag_similarity_threshold}")

        # 2. 檢查邏輯一致性
        if self.confidence_medium_threshold >= self.confidence_high_threshold:
            errors.append(
                f"confidence_medium_threshold ({self.confidence_medium_threshold}) "
                f"必須小於 confidence_high_threshold ({self.confidence_high_threshold})"
            )

        if self.template_min_score >= self.template_max_score:
            errors.append(
                f"template_min_score ({self.template_min_score}) "
                f"必須小於 template_max_score ({self.template_max_score})"
            )

        if self.template_max_score > self.fast_path_threshold:
            warnings.append(
                f"template_max_score ({self.template_max_score}) 大於 "
                f"fast_path_threshold ({self.fast_path_threshold})，可能導致模板路徑與快速路徑重疊"
            )

        # 3. 檢查推薦範圍
        if not (0.75 <= self.intent_suggestion_similarity <= 0.85):
            warnings.append(
                f"intent_suggestion_similarity ({self.intent_suggestion_similarity}) "
                f"超出推薦範圍 [0.75, 0.85]"
            )

        if not (0.75 <= self.unclear_semantic_similarity <= 0.85):
            warnings.append(
                f"unclear_semantic_similarity ({self.unclear_semantic_similarity}) "
                f"超出推薦範圍 [0.75, 0.85]"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def __repr__(self) -> str:
        """字串表示"""
        return (
            f"DedupConfig(\n"
            f"  意圖建議: {self.intent_suggestion_similarity},\n"
            f"  未釐清語義: {self.unclear_semantic_similarity},\n"
            f"  未釐清拼音: {self.unclear_pinyin_similarity},\n"
            f"  RAG 檢索: {self.rag_similarity_threshold},\n"
            f"  答案合成: {self.synthesis_threshold},\n"
            f"  信心度(高/中): {self.confidence_high_threshold}/{self.confidence_medium_threshold},\n"
            f"  快速路徑: {self.fast_path_threshold}\n"
            f")"
        )


# ============================================================
# 單例模式（全域共用實例）
# ============================================================

_dedup_config_instance: DedupConfig = None


def get_dedup_config(reload: bool = False) -> DedupConfig:
    """
    取得去重配置的單例實例

    Args:
        reload: 是否重新載入配置（預設 False）

    Returns:
        DedupConfig 實例
    """
    global _dedup_config_instance

    if _dedup_config_instance is None or reload:
        _dedup_config_instance = DedupConfig()
        print("✅ 去重配置已載入:")
        print(f"   - 意圖建議閾值: {_dedup_config_instance.intent_suggestion_similarity}")
        print(f"   - 未釐清語義閾值: {_dedup_config_instance.unclear_semantic_similarity}")
        print(f"   - 未釐清拼音閾值: {_dedup_config_instance.unclear_pinyin_similarity}")

    return _dedup_config_instance


# ============================================================
# 測試與範例
# ============================================================

if __name__ == "__main__":
    """測試去重配置模組"""

    print("=" * 60)
    print("測試去重配置模組")
    print("=" * 60)

    # 1. 載入配置
    config = get_dedup_config()
    print("\n📋 當前配置:")
    print(config)

    # 2. 驗證配置
    print("\n🔍 驗證配置:")
    validation = config.validate()

    if validation['valid']:
        print("✅ 配置驗證通過")
    else:
        print("❌ 配置驗證失敗")
        for error in validation['errors']:
            print(f"   - 錯誤: {error}")

    if validation['warnings']:
        print("⚠️  警告:")
        for warning in validation['warnings']:
            print(f"   - {warning}")

    # 3. 取得去重閾值
    print("\n🎯 去重閾值:")
    dedup_thresholds = config.get_dedup_thresholds()
    for key, value in dedup_thresholds.items():
        print(f"   - {key}: {value}")

    # 4. 取得 RAG 閾值
    print("\n🤖 RAG 閾值:")
    rag_thresholds = config.get_rag_thresholds()
    for key, value in rag_thresholds.items():
        print(f"   - {key}: {value}")

    # 5. 轉換為字典
    print("\n📊 完整配置字典:")
    config_dict = config.to_dict()
    for key, value in config_dict.items():
        print(f"   - {key}: {value}")

    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)
