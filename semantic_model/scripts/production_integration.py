#!/usr/bin/env python3
"""
生產環境整合範例 - 展示如何在實際系統中使用模型管理器
"""

from model_manager import ModelManager, ModelType
from typing import List, Dict, Optional
import json
import logging
from datetime import datetime

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedChatService:
    """
    增強版聊天服務 - 整合多個模型的生產系統
    """

    def __init__(self, config_path: str = "config/models.json"):
        """初始化服務"""
        logger.info("初始化增強版聊天服務...")

        # 載入模型管理器
        self.model_manager = ModelManager(config_path)

        # 載入知識庫
        self.knowledge_base = self.load_knowledge_base()

        # 配置
        self.config = {
            "use_ensemble": False,  # 是否使用多模型集成
            "top_k": 10,            # 返回前K個結果
            "min_score": 0.5,       # 最低分數閾值
            "log_queries": True     # 是否記錄查詢
        }

        logger.info("✅ 服務初始化完成")

    def load_knowledge_base(self) -> List[Dict]:
        """載入知識庫"""
        try:
            with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
                kb = json.load(f)
                logger.info(f"載入 {len(kb)} 個知識點")
                return kb
        except Exception as e:
            logger.error(f"載入知識庫失敗: {e}")
            return []

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        主要搜索方法 - 支援多種策略
        """
        if top_k is None:
            top_k = self.config["top_k"]

        logger.info(f"處理查詢: {query}")

        # 1. 初步篩選（這裡簡化，實際應該用向量檢索）
        candidates = self.knowledge_base[:50]  # 取前50個做示範

        # 2. 使用模型評分
        if self.config["use_ensemble"]:
            # 使用多模型集成
            results = self._search_with_ensemble(query, candidates, top_k)
        else:
            # 使用單一模型
            results = self._search_with_single_model(query, candidates, top_k)

        # 3. 記錄查詢
        if self.config["log_queries"]:
            self._log_query(query, results)

        return results

    def _search_with_single_model(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """使用單一模型搜索"""

        # 準備文檔
        documents = [kb['content'] for kb in candidates]

        # 獲取分數
        active_model = self.model_manager.config["active_models"][0]
        scores = self.model_manager.predict_single(
            active_model, query, documents
        )

        # 組合結果
        results = []
        for i, (kb, score) in enumerate(zip(candidates, scores)):
            if score >= self.config["min_score"]:
                results.append({
                    "knowledge_id": kb['id'],
                    "title": kb['title'],
                    "content": kb['content'][:200] + "...",
                    "score": float(score),
                    "action_type": kb.get('action_type'),
                    "form_id": kb.get('form_id'),
                    "model_used": active_model
                })

        # 排序並返回前K個
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def _search_with_ensemble(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """使用多模型集成搜索"""

        documents = [kb['content'] for kb in candidates]

        # 獲取集成分數
        ensemble_scores = self.model_manager.predict_ensemble(query, documents)

        # 組合結果
        results = []
        for kb, score in zip(candidates, ensemble_scores):
            if score >= self.config["min_score"]:
                results.append({
                    "knowledge_id": kb['id'],
                    "title": kb['title'],
                    "content": kb['content'][:200] + "...",
                    "score": float(score),
                    "action_type": kb.get('action_type'),
                    "form_id": kb.get('form_id'),
                    "model_used": "ensemble"
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def switch_model(self, model_name: str):
        """切換模型"""
        try:
            self.model_manager.switch_model(model_name)
            logger.info(f"✅ 已切換到模型: {model_name}")
            return True
        except Exception as e:
            logger.error(f"切換模型失敗: {e}")
            return False

    def enable_ensemble(self, models: List[str]):
        """啟用多模型集成"""
        self.model_manager.config["active_models"] = models
        self.config["use_ensemble"] = True
        logger.info(f"✅ 啟用集成模式: {models}")

    def disable_ensemble(self):
        """停用多模型集成"""
        self.config["use_ensemble"] = False
        logger.info("已停用集成模式")

    def _log_query(self, query: str, results: List[Dict]):
        """記錄查詢（用於分析和優化）"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "results_count": len(results),
            "top_score": results[0]["score"] if results else 0,
            "model_used": results[0]["model_used"] if results else "none"
        }

        # 實際環境應該寫入資料庫或日誌文件
        logger.debug(f"查詢日誌: {log_entry}")

    def get_status(self) -> Dict:
        """獲取服務狀態"""
        return {
            "service": "running",
            "knowledge_base_size": len(self.knowledge_base),
            "model_status": self.model_manager.get_status(),
            "config": self.config
        }

# ========== API 整合範例 ==========

class ChatAPI:
    """
    API 層 - 展示如何整合到 FastAPI 或 Flask
    """

    def __init__(self):
        self.service = EnhancedChatService()

    def handle_query(self, request: Dict) -> Dict:
        """
        處理查詢請求

        請求格式:
        {
            "query": "我要報修",
            "vendor_id": 1,
            "top_k": 5,
            "use_ensemble": false
        }
        """
        query = request.get("query", "")
        top_k = request.get("top_k", 5)
        use_ensemble = request.get("use_ensemble", False)

        # 根據請求調整設定
        if use_ensemble:
            self.service.enable_ensemble(["bge_reranker", "m3e_base"])
        else:
            self.service.disable_ensemble()

        # 執行搜索
        results = self.service.search(query, top_k)

        # 返回結果
        return {
            "status": "success",
            "query": query,
            "results": results,
            "model_info": self.service.model_manager.get_status()
        }

    def switch_model(self, request: Dict) -> Dict:
        """切換模型"""
        model_name = request.get("model", "bge_reranker")
        success = self.service.switch_model(model_name)

        return {
            "status": "success" if success else "error",
            "current_model": self.service.model_manager.config["active_models"]
        }

    def get_status(self) -> Dict:
        """獲取系統狀態"""
        return self.service.get_status()

# ========== 使用範例 ==========

def demo():
    """展示生產環境整合"""

    print("="*60)
    print("生產環境整合範例")
    print("="*60)

    # 初始化 API
    api = ChatAPI()

    # 測試查詢
    test_queries = [
        {
            "query": "我要報修",
            "top_k": 3,
            "use_ensemble": False
        },
        {
            "query": "電費怎麼算",
            "top_k": 3,
            "use_ensemble": False
        }
    ]

    for test in test_queries:
        print(f"\n查詢: {test['query']}")
        print("-" * 40)

        response = api.handle_query(test)

        print(f"找到 {len(response['results'])} 個結果:")
        for i, result in enumerate(response['results'], 1):
            print(f"  {i}. {result['title']}")
            print(f"     分數: {result['score']:.3f}")
            print(f"     類型: {result['action_type']}")
            if result.get('form_id'):
                print(f"     表單: {result['form_id']}")

    # 切換模型測試
    print("\n" + "="*60)
    print("模型切換測試")
    print("="*60)

    # 切換到大型模型
    print("\n切換到大型模型:")
    switch_response = api.switch_model({"model": "bge_reranker"})
    print(f"狀態: {switch_response['status']}")
    print(f"當前模型: {switch_response['current_model']}")

    # 查看系統狀態
    print("\n" + "="*60)
    print("系統狀態")
    print("="*60)

    status = api.get_status()
    print(f"服務狀態: {status['service']}")
    print(f"知識庫大小: {status['knowledge_base_size']}")
    print(f"啟用的模型: {status['model_status']['active_models']}")
    print(f"可用的模型: {status['model_status']['available_models']}")

def integration_guide():
    """整合指南"""

    print("\n" + "="*60)
    print("整合到您的系統")
    print("="*60)

    print("""
### FastAPI 整合範例:

```python
from fastapi import FastAPI
from production_integration import ChatAPI

app = FastAPI()
chat_api = ChatAPI()

@app.post("/api/search")
async def search(request: dict):
    return chat_api.handle_query(request)

@app.post("/api/switch-model")
async def switch_model(request: dict):
    return chat_api.switch_model(request)

@app.get("/api/status")
async def status():
    return chat_api.get_status()
```

### 環境變數配置:

```bash
export MODEL_CONFIG_PATH="config/models.json"
export KNOWLEDGE_BASE_PATH="data/knowledge_base.json"
export LOG_LEVEL="INFO"
```

### Docker 部署:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY semantic_model/ ./semantic_model/
COPY data/ ./data/
COPY config/ ./config/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
    """)

if __name__ == "__main__":
    # 執行示範
    demo()

    # 顯示整合指南
    integration_guide()

    print("\n✅ 完成！您的系統現在支援多模型管理")