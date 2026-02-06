#!/usr/bin/env python3
"""
模型管理器 - 支援多模型切換的可擴展架構
"""

from abc import ABC, abstractmethod
from sentence_transformers import CrossEncoder
import json
from typing import Dict, List, Any
from enum import Enum

class ModelType(Enum):
    """支援的模型類型"""
    SEMANTIC = "semantic"      # 語義理解
    RERANKER = "reranker"      # 重排序
    VECTOR = "vector"          # 向量檢索
    CUSTOM = "custom"          # 自定義

class BaseModel(ABC):
    """模型基礎類別 - 所有模型都要實作這個介面"""

    @abstractmethod
    def predict(self, query: str, documents: List[str]) -> List[float]:
        """預測查詢與文檔的相關性分數"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict:
        """獲取模型資訊"""
        pass

class BGERerankerModel(BaseModel):
    """BGE Reranker 模型實作"""

    def __init__(self, model_path: str = "BAAI/bge-reranker-base"):
        self.model = CrossEncoder(model_path, max_length=512)
        self.model_path = model_path

    def predict(self, query: str, documents: List[str]) -> List[float]:
        """計算相關性分數"""
        pairs = [[query, doc] for doc in documents]
        scores = self.model.predict(pairs)
        return scores.tolist()

    def get_model_info(self) -> Dict:
        return {
            "name": "BGE Reranker",
            "type": ModelType.RERANKER.value,
            "path": self.model_path,
            "version": "1.0"
        }

class M3EModel(BaseModel):
    """M3E 向量模型實作（示例）"""

    def __init__(self, model_path: str = "moka-ai/m3e-base"):
        # 這裡示範另一種模型的整合
        self.model_path = model_path

    def predict(self, query: str, documents: List[str]) -> List[float]:
        """向量相似度計算"""
        # 實際實作會使用真實的向量計算
        # 這裡只是示範
        import random
        return [random.random() for _ in documents]

    def get_model_info(self) -> Dict:
        return {
            "name": "M3E Vector",
            "type": ModelType.VECTOR.value,
            "path": self.model_path,
            "version": "1.0"
        }

class CustomModel(BaseModel):
    """自定義模型 - 您未來的模型"""

    def __init__(self, config: Dict):
        self.config = config
        # 載入您的自定義模型

    def predict(self, query: str, documents: List[str]) -> List[float]:
        """自定義預測邏輯"""
        # 實作您的預測邏輯
        pass

    def get_model_info(self) -> Dict:
        return {
            "name": "Custom Model",
            "type": ModelType.CUSTOM.value,
            "config": self.config,
            "version": "custom"
        }

class ModelManager:
    """
    模型管理器 - 統一管理所有模型
    支援動態載入、切換、組合多個模型
    """

    def __init__(self, config_file: str = "config/models.json"):
        self.models = {}
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """從配置文件載入模型設定"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            # 預設配置
            self.config = {
                "active_models": ["bge_reranker"],
                "models": {
                    "bge_reranker": {
                        "type": "reranker",
                        "class": "BGERerankerModel",
                        "path": "BAAI/bge-reranker-base",
                        "weight": 0.5
                    },
                    "m3e_vector": {
                        "type": "vector",
                        "class": "M3EModel",
                        "path": "moka-ai/m3e-base",
                        "weight": 0.3
                    }
                },
                "ensemble_strategy": "weighted_average"
            }

    def register_model(self, name: str, model: BaseModel):
        """註冊新模型"""
        self.models[name] = model
        print(f"✅ 註冊模型: {name}")

    def load_model(self, name: str) -> BaseModel:
        """載入指定模型"""
        if name in self.models:
            return self.models[name]

        # 從配置載入
        if name in self.config["models"]:
            model_config = self.config["models"][name]
            model_class = model_config["class"]

            if model_class == "BGERerankerModel":
                model = BGERerankerModel(model_config["path"])
            elif model_class == "M3EModel":
                model = M3EModel(model_config["path"])
            else:
                raise ValueError(f"未知的模型類別: {model_class}")

            self.register_model(name, model)
            return model

        raise ValueError(f"找不到模型: {name}")

    def predict_single(self, model_name: str, query: str, documents: List[str]) -> List[float]:
        """使用單一模型預測"""
        model = self.load_model(model_name)
        return model.predict(query, documents)

    def predict_ensemble(self, query: str, documents: List[str]) -> List[float]:
        """使用多個模型集成預測"""
        all_scores = []
        weights = []

        for model_name in self.config["active_models"]:
            model = self.load_model(model_name)
            scores = model.predict(query, documents)
            all_scores.append(scores)

            # 獲取權重
            weight = self.config["models"][model_name].get("weight", 1.0)
            weights.append(weight)

        # 加權平均
        ensemble_scores = []
        for i in range(len(documents)):
            weighted_sum = sum(
                scores[i] * weight
                for scores, weight in zip(all_scores, weights)
            )
            total_weight = sum(weights)
            ensemble_scores.append(weighted_sum / total_weight)

        return ensemble_scores

    def switch_model(self, model_name: str):
        """切換到指定模型"""
        if model_name not in self.config["models"]:
            raise ValueError(f"模型不存在: {model_name}")

        self.config["active_models"] = [model_name]
        print(f"✅ 已切換到模型: {model_name}")

    def add_model_config(self, name: str, model_config: Dict):
        """新增模型配置"""
        self.config["models"][name] = model_config
        self.save_config()
        print(f"✅ 已新增模型配置: {name}")

    def save_config(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_status(self) -> Dict:
        """獲取管理器狀態"""
        return {
            "loaded_models": list(self.models.keys()),
            "active_models": self.config["active_models"],
            "available_models": list(self.config["models"].keys()),
            "ensemble_strategy": self.config["ensemble_strategy"]
        }

# ========== 使用範例 ==========

def example_usage():
    """展示如何使用模型管理器"""

    print("="*60)
    print("模型管理器使用範例")
    print("="*60)

    # 初始化管理器
    manager = ModelManager()

    # 測試數據
    query = "我要報修"
    documents = [
        "如何報修：請填寫報修單",
        "租金繳納方式說明",
        "退租流程與注意事項"
    ]

    # 1. 使用單一模型
    print("\n1. 使用單一模型:")
    scores = manager.predict_single("bge_reranker", query, documents)
    for i, (doc, score) in enumerate(zip(documents, scores)):
        print(f"   {i+1}. {doc[:20]}... 分數: {score:.3f}")

    # 2. 使用多模型集成
    print("\n2. 使用多模型集成:")
    ensemble_scores = manager.predict_ensemble(query, documents)
    for i, (doc, score) in enumerate(zip(documents, ensemble_scores)):
        print(f"   {i+1}. {doc[:20]}... 分數: {score:.3f}")

    # 3. 新增自定義模型
    print("\n3. 新增新模型配置:")
    manager.add_model_config("my_custom_model", {
        "type": "custom",
        "class": "CustomModel",
        "config": {"key": "value"},
        "weight": 0.2
    })

    # 4. 查看狀態
    print("\n4. 管理器狀態:")
    status = manager.get_status()
    print(f"   已載入: {status['loaded_models']}")
    print(f"   啟用中: {status['active_models']}")
    print(f"   可用: {status['available_models']}")

if __name__ == "__main__":
    example_usage()