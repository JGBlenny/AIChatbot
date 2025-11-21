# B2B 外部 API 整合框架設計

## 1. 架構概覽

### 1.1 核心組件

```
┌─────────────────────────────────────────────────────────┐
│              B2B Chat API Endpoint                        │
│         POST /api/v1/b2b/chat                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│         Conversation Session Manager                      │
│   功能：                                                   │
│   - session_id 追蹤                                       │
│   - 會話狀態儲存（Redis 或 DB）                            │
│   - 上下文管理（context 歷史）                             │
│   - 超時自動清理                                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Flow Orchestrator                            │
│   功能：                                                   │
│   - 意圖識別（透過現有 IntentClassifier）                  │
│   - 流程路由（根據 intent + state）                        │
│   - 狀態機控制（FSM - Finite State Machine）               │
│   - 條件判斷與流程控制                                      │
└─────────────────────────────────────────────────────────┘
              │                       │
              ▼                       ▼
┌──────────────────────┐  ┌────────────────────────────┐
│  External API Client │  │   RAG Knowledge Base       │
│  功能：               │  │   功能：                    │
│  - 合約查詢          │  │   - 通用知識問答            │
│  - 點退狀態檢查      │  │   - Fallback 回答           │
│  - 補件驗證          │  │                            │
│  - 錯誤處理與重試    │  │                            │
└──────────────────────┘  └────────────────────────────┘
```

---

## 2. 資料模型

### 2.1 會話狀態（Session State）

```python
class SessionState:
    """會話狀態資料結構"""
    session_id: str             # 唯一會話 ID
    vendor_id: int              # 業者 ID
    user_id: str                # 業者使用者 ID
    current_flow: str           # 當前流程名稱（如 "contract_cancel"）
    current_state: str          # 當前狀態（如 "checking_contract"）
    context: Dict               # 流程上下文（保存 API 返回的資料）
    history: List[Dict]         # 對話歷史
    created_at: datetime
    updated_at: datetime
    expires_at: datetime        # 會話過期時間（預設 30 分鐘）
```

**資料庫表結構（PostgreSQL）**：

```sql
CREATE TABLE b2b_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    current_flow VARCHAR(100),
    current_state VARCHAR(100),
    context JSONB DEFAULT '{}',
    history JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_b2b_sessions_vendor_user ON b2b_sessions(vendor_id, user_id);
CREATE INDEX idx_b2b_sessions_expires ON b2b_sessions(expires_at);
```

**或使用 Redis（更高效）**：

```
Key: session:{session_id}
Value: JSON 格式的 SessionState
TTL: 30 分鐘
```

---

### 2.2 流程定義（Flow Definition）

```python
class FlowDefinition:
    """流程定義（可儲存在資料庫或 YAML 配置）"""
    flow_id: str                # 流程 ID（如 "contract_cancel_check"）
    name: str                   # 流程名稱
    description: str            # 流程描述
    trigger_intents: List[str]  # 觸發意圖列表
    states: Dict[str, State]    # 狀態定義
    transitions: List[Transition]  # 狀態轉換規則
    api_endpoints: Dict         # 使用的外部 API 端點配置
```

**範例 YAML 配置**：

```yaml
flow_id: contract_cancel_check
name: 合約點退檢查流程
description: 檢查業者合約是否可以點退，並引導補件
trigger_intents:
  - contract_cancel
  - contract_issue
states:
  initial:
    type: entry
    actions:
      - call_api:
          endpoint: check_contract_status
          params:
            contract_id: "${context.contract_id}"
      - set_state: checking_contract

  checking_contract:
    type: decision
    condition: "${api_response.status}"
    branches:
      normal:
        message: "您的合約狀態正常，請嘗試重新整理後再試。"
        actions:
          - set_state: resolved
      incomplete:
        message: "您的合約資料不完整，需補上以下資訊：${api_response.missing_fields}"
        actions:
          - set_state: waiting_for_documents
      error:
        message: "查詢合約時發生錯誤，請稍後再試或聯繫技術支援。"
        actions:
          - set_state: error

  waiting_for_documents:
    type: waiting
    expected_input: user_confirmation
    timeout: 1800  # 30 分鐘
    on_input:
      - call_api:
          endpoint: verify_contract_documents
          params:
            contract_id: "${context.contract_id}"
      - set_state: verifying_documents

  verifying_documents:
    type: decision
    condition: "${api_response.verified}"
    branches:
      verified:
        message: "資料已確認完整，現在您可以執行點退流程了。"
        actions:
          - set_state: resolved
      still_incomplete:
        message: "資料仍不完整，請確認：${api_response.issues}"
        actions:
          - set_state: waiting_for_documents

  resolved:
    type: final
    message: "流程已完成"

  error:
    type: final
    message: "流程發生錯誤"
```

---

## 3. 核心服務實作

### 3.1 SessionManager（會話管理器）

**檔案位置**：`rag-orchestrator/services/b2b_session_manager.py`

```python
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncpg


class SessionManager:
    """B2B 會話管理器"""

    def __init__(self, db_pool: asyncpg.Pool, session_timeout: int = 1800):
        """
        初始化會話管理器

        Args:
            db_pool: 資料庫連接池
            session_timeout: 會話超時時間（秒，預設 30 分鐘）
        """
        self.db_pool = db_pool
        self.session_timeout = session_timeout

    async def create_session(
        self,
        vendor_id: int,
        user_id: str,
        initial_flow: Optional[str] = None
    ) -> str:
        """建立新會話"""
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO b2b_sessions (
                    session_id, vendor_id, user_id, current_flow,
                    current_state, context, history, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, session_id, vendor_id, user_id, initial_flow,
                 "initial", json.dumps({}), json.dumps([]), expires_at)

        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """取得會話資料"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM b2b_sessions
                WHERE session_id = $1 AND expires_at > NOW()
            """, session_id)

            if not row:
                return None

            return {
                "session_id": row["session_id"],
                "vendor_id": row["vendor_id"],
                "user_id": row["user_id"],
                "current_flow": row["current_flow"],
                "current_state": row["current_state"],
                "context": json.loads(row["context"]) if row["context"] else {},
                "history": json.loads(row["history"]) if row["history"] else [],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"]
            }

    async def update_session(
        self,
        session_id: str,
        current_flow: Optional[str] = None,
        current_state: Optional[str] = None,
        context_update: Optional[Dict] = None,
        add_to_history: Optional[Dict] = None
    ) -> bool:
        """更新會話資料"""
        session = await self.get_session(session_id)
        if not session:
            return False

        # 更新欄位
        updates = []
        params = []
        param_idx = 1

        if current_flow is not None:
            updates.append(f"current_flow = ${param_idx}")
            params.append(current_flow)
            param_idx += 1

        if current_state is not None:
            updates.append(f"current_state = ${param_idx}")
            params.append(current_state)
            param_idx += 1

        if context_update:
            new_context = {**session["context"], **context_update}
            updates.append(f"context = ${param_idx}")
            params.append(json.dumps(new_context))
            param_idx += 1

        if add_to_history:
            new_history = session["history"] + [add_to_history]
            updates.append(f"history = ${param_idx}")
            params.append(json.dumps(new_history))
            param_idx += 1

        # 更新時間戳與過期時間
        updates.append(f"updated_at = NOW()")
        expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
        updates.append(f"expires_at = ${param_idx}")
        params.append(expires_at)
        param_idx += 1

        params.append(session_id)

        async with self.db_pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE b2b_sessions
                SET {', '.join(updates)}
                WHERE session_id = ${param_idx}
            """, *params)

        return True

    async def delete_session(self, session_id: str) -> bool:
        """刪除會話"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM b2b_sessions WHERE session_id = $1
            """, session_id)
            return result != "DELETE 0"

    async def cleanup_expired_sessions(self) -> int:
        """清理過期會話（定期任務）"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM b2b_sessions WHERE expires_at < NOW()
            """)
            # 從 "DELETE 5" 提取數字
            count = int(result.split()[1]) if result.startswith("DELETE") else 0
            return count
```

---

### 3.2 FlowOrchestrator（流程編排器）

**檔案位置**：`rag-orchestrator/services/b2b_flow_orchestrator.py`

```python
from typing import Dict, Any, Optional, List
import re
import yaml
from pathlib import Path


class FlowOrchestrator:
    """B2B 流程編排器"""

    def __init__(self, flow_config_dir: str = "./flows"):
        """
        初始化流程編排器

        Args:
            flow_config_dir: 流程配置檔案目錄
        """
        self.flows: Dict[str, Dict] = {}
        self.load_flows(flow_config_dir)

    def load_flows(self, config_dir: str):
        """載入流程定義（從 YAML 檔案）"""
        config_path = Path(config_dir)
        if not config_path.exists():
            print(f"⚠️  流程配置目錄不存在: {config_dir}")
            return

        for yaml_file in config_path.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    flow_def = yaml.safe_load(f)
                    flow_id = flow_def.get('flow_id')
                    if flow_id:
                        self.flows[flow_id] = flow_def
                        print(f"✅ 載入流程: {flow_id} ({flow_def.get('name')})")
            except Exception as e:
                print(f"❌ 載入流程失敗 {yaml_file}: {e}")

    def match_flow(self, intent_name: str) -> Optional[str]:
        """
        根據意圖匹配流程

        Args:
            intent_name: 意圖名稱

        Returns:
            流程 ID（如果匹配）
        """
        for flow_id, flow_def in self.flows.items():
            trigger_intents = flow_def.get('trigger_intents', [])
            if intent_name in trigger_intents:
                return flow_id
        return None

    def execute_state(
        self,
        flow_id: str,
        state_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行狀態邏輯

        Args:
            flow_id: 流程 ID
            state_name: 狀態名稱
            context: 執行上下文

        Returns:
            執行結果（包含 message, next_state, actions）
        """
        flow_def = self.flows.get(flow_id)
        if not flow_def:
            return {"error": f"流程不存在: {flow_id}"}

        state_def = flow_def.get('states', {}).get(state_name)
        if not state_def:
            return {"error": f"狀態不存在: {state_name}"}

        state_type = state_def.get('type')

        # Entry state: 執行初始化動作
        if state_type == 'entry':
            actions = state_def.get('actions', [])
            return {
                "state_type": "entry",
                "actions": actions,
                "next_state": None  # 由 actions 決定
            }

        # Decision state: 根據條件判斷分支
        elif state_type == 'decision':
            condition_expr = state_def.get('condition', '')
            condition_value = self._evaluate_condition(condition_expr, context)

            branches = state_def.get('branches', {})
            branch = branches.get(str(condition_value).lower())

            if not branch:
                return {"error": f"未定義的分支: {condition_value}"}

            return {
                "state_type": "decision",
                "message": self._interpolate(branch.get('message', ''), context),
                "actions": branch.get('actions', []),
                "next_state": None  # 由 actions 決定
            }

        # Waiting state: 等待使用者輸入
        elif state_type == 'waiting':
            return {
                "state_type": "waiting",
                "expected_input": state_def.get('expected_input'),
                "timeout": state_def.get('timeout', 1800),
                "on_input": state_def.get('on_input', [])
            }

        # Final state: 結束流程
        elif state_type == 'final':
            return {
                "state_type": "final",
                "message": self._interpolate(state_def.get('message', ''), context)
            }

        return {"error": f"未知的狀態類型: {state_type}"}

    def _evaluate_condition(self, condition: str, context: Dict) -> Any:
        """
        評估條件表達式（簡化版，支援 ${context.field}）

        範例: "${api_response.status}" -> 從 context['api_response']['status'] 取值
        """
        pattern = r'\$\{([^}]+)\}'
        match = re.search(pattern, condition)
        if match:
            path = match.group(1).split('.')
            value = context
            for key in path:
                value = value.get(key, None)
                if value is None:
                    return None
            return value
        return condition

    def _interpolate(self, template: str, context: Dict) -> str:
        """
        替換模板變數（如 ${context.field}）
        """
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            path = match.group(1).split('.')
            value = context
            for key in path:
                value = value.get(key, '')
                if not value:
                    break
            return str(value)

        return re.sub(pattern, replacer, template)
```

---

### 3.3 ExternalAPIClient（外部 API 客戶端）

**檔案位置**：`rag-orchestrator/services/b2b_api_client.py`

```python
import aiohttp
from typing import Dict, Any, Optional
import asyncio


class ExternalAPIClient:
    """外部 API 客戶端"""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        初始化 API 客戶端

        Args:
            base_url: API 基礎 URL
            api_key: API 金鑰（如果需要）
            timeout: 請求超時時間（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def call(
        self,
        endpoint: str,
        method: str = "POST",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        呼叫外部 API

        Args:
            endpoint: API 端點（相對路徑）
            method: HTTP 方法
            params: URL 參數
            data: 請求 body（JSON）
            headers: 自訂 headers

        Returns:
            API 回應（JSON）
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # 準備 headers
        req_headers = {"Content-Type": "application/json"}
        if self.api_key:
            req_headers["Authorization"] = f"Bearer {self.api_key}"
        if headers:
            req_headers.update(headers)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=req_headers
                ) as response:
                    response.raise_for_status()
                    return await response.json()

        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": f"API 請求失敗: {str(e)}"
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "API 請求超時"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"未知錯誤: {str(e)}"
            }

    async def check_contract_status(self, contract_id: str, vendor_id: int) -> Dict[str, Any]:
        """
        檢查合約狀態（範例 API）

        Args:
            contract_id: 合約 ID
            vendor_id: 業者 ID

        Returns:
            合約狀態資訊
        """
        return await self.call(
            endpoint="/contracts/check",
            method="POST",
            data={
                "contract_id": contract_id,
                "vendor_id": vendor_id
            }
        )

    async def verify_contract_documents(self, contract_id: str) -> Dict[str, Any]:
        """
        驗證合約文件完整性（範例 API）

        Args:
            contract_id: 合約 ID

        Returns:
            驗證結果
        """
        return await self.call(
            endpoint="/contracts/verify_documents",
            method="POST",
            data={"contract_id": contract_id}
        )
```

---

## 4. API 端點實作

### 4.1 B2B Chat API

**檔案位置**：`rag-orchestrator/routers/b2b_chat.py`

```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

router = APIRouter()


class B2BChatRequest(BaseModel):
    """B2B 聊天請求"""
    message: str = Field(..., description="使用者訊息", min_length=1)
    vendor_id: int = Field(..., description="業者 ID", ge=1)
    user_id: str = Field(..., description="業者使用者 ID")
    session_id: Optional[str] = Field(None, description="會話 ID（續接對話時提供）")
    context: Optional[Dict] = Field(None, description="額外上下文（如 contract_id）")


class B2BChatResponse(BaseModel):
    """B2B 聊天回應"""
    session_id: str
    message: str
    current_flow: Optional[str] = None
    current_state: Optional[str] = None
    requires_action: bool = False
    timestamp: str


@router.post("/b2b/chat", response_model=B2BChatResponse)
async def b2b_chat(request: B2BChatRequest, req: Request):
    """
    B2B 聊天端點（支援多輪對話與外部 API 整合）

    流程：
    1. 檢查是否有既有 session（多輪對話）
    2. 如果無 session，透過意圖分類決定流程
    3. 執行流程狀態機
    4. 根據狀態呼叫外部 API
    5. 更新 session 並返回回應
    """
    try:
        # 取得服務
        session_manager = req.app.state.session_manager
        flow_orchestrator = req.app.state.flow_orchestrator
        intent_classifier = req.app.state.intent_classifier
        api_client = req.app.state.api_client

        # Step 1: 取得或建立 session
        session = None
        if request.session_id:
            session = await session_manager.get_session(request.session_id)

        if not session:
            # 新會話：進行意圖分類
            intent_result = intent_classifier.classify(request.message)
            flow_id = flow_orchestrator.match_flow(intent_result['intent_name'])

            if not flow_id:
                # 無匹配流程，使用 RAG fallback
                raise HTTPException(
                    status_code=400,
                    detail=f"無法處理意圖: {intent_result['intent_name']}"
                )

            # 建立新 session
            session_id = await session_manager.create_session(
                vendor_id=request.vendor_id,
                user_id=request.user_id,
                initial_flow=flow_id
            )

            session = await session_manager.get_session(session_id)

            # 初始化 context
            if request.context:
                await session_manager.update_session(
                    session_id=session_id,
                    context_update=request.context
                )
                session = await session_manager.get_session(session_id)

        # Step 2: 執行當前狀態
        flow_id = session['current_flow']
        current_state = session['current_state']
        context = session['context']

        state_result = flow_orchestrator.execute_state(
            flow_id=flow_id,
            state_name=current_state,
            context=context
        )

        if "error" in state_result:
            raise HTTPException(status_code=500, detail=state_result["error"])

        # Step 3: 處理狀態結果
        message = ""
        next_state = current_state

        # Entry state: 執行 API 呼叫
        if state_result['state_type'] == 'entry':
            actions = state_result.get('actions', [])
            for action in actions:
                if 'call_api' in action:
                    api_config = action['call_api']
                    endpoint_name = api_config['endpoint']
                    api_params = {
                        k: flow_orchestrator._interpolate(v, context)
                        for k, v in api_config.get('params', {}).items()
                    }

                    # 呼叫 API（根據端點名稱路由）
                    if endpoint_name == 'check_contract_status':
                        api_response = await api_client.check_contract_status(
                            contract_id=api_params.get('contract_id'),
                            vendor_id=request.vendor_id
                        )
                    else:
                        api_response = {"error": f"未知的 API 端點: {endpoint_name}"}

                    # 儲存 API 回應到 context
                    context['api_response'] = api_response

                if 'set_state' in action:
                    next_state = action['set_state']

            # 重新執行新狀態（decision state）
            await session_manager.update_session(
                session_id=session['session_id'],
                current_state=next_state,
                context_update=context
            )
            session = await session_manager.get_session(session['session_id'])

            state_result = flow_orchestrator.execute_state(
                flow_id=flow_id,
                state_name=next_state,
                context=session['context']
            )

        # Decision state: 取得訊息並決定下一步
        if state_result['state_type'] == 'decision':
            message = state_result['message']
            actions = state_result.get('actions', [])
            for action in actions:
                if 'set_state' in action:
                    next_state = action['set_state']

        # Waiting state: 等待使用者輸入
        elif state_result['state_type'] == 'waiting':
            # 使用者輸入了訊息，執行 on_input 動作
            on_input_actions = state_result.get('on_input', [])
            for action in on_input_actions:
                if 'call_api' in action:
                    api_config = action['call_api']
                    endpoint_name = api_config['endpoint']
                    api_params = {
                        k: flow_orchestrator._interpolate(v, context)
                        for k, v in api_config.get('params', {}).items()
                    }

                    # 呼叫 API
                    if endpoint_name == 'verify_contract_documents':
                        api_response = await api_client.verify_contract_documents(
                            contract_id=api_params.get('contract_id')
                        )
                    else:
                        api_response = {"error": f"未知的 API 端點: {endpoint_name}"}

                    context['api_response'] = api_response

                if 'set_state' in action:
                    next_state = action['set_state']

            # 重新執行新狀態
            await session_manager.update_session(
                session_id=session['session_id'],
                current_state=next_state,
                context_update=context
            )
            session = await session_manager.get_session(session['session_id'])

            state_result = flow_orchestrator.execute_state(
                flow_id=flow_id,
                state_name=next_state,
                context=session['context']
            )

            if state_result['state_type'] == 'decision':
                message = state_result['message']
                actions = state_result.get('actions', [])
                for action in actions:
                    if 'set_state' in action:
                        next_state = action['set_state']

        # Final state: 結束流程
        elif state_result['state_type'] == 'final':
            message = state_result['message']
            # 刪除 session
            await session_manager.delete_session(session['session_id'])

        # Step 4: 更新 session
        await session_manager.update_session(
            session_id=session['session_id'],
            current_state=next_state,
            add_to_history={
                "role": "user",
                "message": request.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        await session_manager.update_session(
            session_id=session['session_id'],
            add_to_history={
                "role": "assistant",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Step 5: 返回回應
        return B2BChatResponse(
            session_id=session['session_id'],
            message=message,
            current_flow=flow_id,
            current_state=next_state,
            requires_action=(state_result['state_type'] == 'waiting'),
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"處理 B2B 聊天請求失敗: {str(e)}")
```

---

## 5. 流程配置範例

**檔案位置**：`rag-orchestrator/flows/contract_cancel_check.yaml`

```yaml
flow_id: contract_cancel_check
name: 合約點退檢查流程
description: 檢查業者合約是否可以點退，並引導補件
trigger_intents:
  - contract_cancel
  - contract_issue

states:
  initial:
    type: entry
    actions:
      - call_api:
          endpoint: check_contract_status
          params:
            contract_id: "${context.contract_id}"
      - set_state: checking_contract

  checking_contract:
    type: decision
    condition: "${api_response.status}"
    branches:
      normal:
        message: "您的合約狀態正常，請嘗試重新整理後再試。如果問題持續，請聯繫技術支援。"
        actions:
          - set_state: resolved
      incomplete:
        message: "您的合約資料不完整，需補上以下資訊：\n${api_response.missing_fields}\n\n請您補充完成後，回覆「已補好」或「補好了」。"
        actions:
          - set_state: waiting_for_documents
      error:
        message: "查詢合約時發生錯誤：${api_response.error}\n請稍後再試或聯繫技術支援。"
        actions:
          - set_state: error

  waiting_for_documents:
    type: waiting
    expected_input: user_confirmation
    timeout: 1800  # 30 分鐘
    on_input:
      - call_api:
          endpoint: verify_contract_documents
          params:
            contract_id: "${context.contract_id}"
      - set_state: verifying_documents

  verifying_documents:
    type: decision
    condition: "${api_response.verified}"
    branches:
      true:
        message: "資料已確認完整！✅\n\n現在您可以執行點退流程了。請到合約管理頁面進行操作。"
        actions:
          - set_state: resolved
      false:
        message: "抱歉，資料仍不完整。請確認以下項目：\n${api_response.issues}\n\n補充完成後，請再次回覆「已補好」。"
        actions:
          - set_state: waiting_for_documents

  resolved:
    type: final
    message: "流程已完成，感謝您的配合。"

  error:
    type: final
    message: "流程發生錯誤，請聯繫技術支援。"

api_endpoints:
  check_contract_status:
    url: "/api/contracts/check"
    method: POST
    description: "檢查合約狀態"
  verify_contract_documents:
    url: "/api/contracts/verify_documents"
    method: POST
    description: "驗證合約文件完整性"
```

---

## 6. 整合到主應用

**修改檔案**：`rag-orchestrator/app.py`

在 `lifespan` 函數中初始化新服務：

```python
# 新增導入
from services.b2b_session_manager import SessionManager
from services.b2b_flow_orchestrator import FlowOrchestrator
from services.b2b_api_client import ExternalAPIClient
from routers import b2b_chat

# 在 lifespan 中初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 現有初始化 ...

    # B2B 服務初始化
    session_manager = SessionManager(db_pool)
    print("✅ B2B 會話管理器已初始化")

    flow_orchestrator = FlowOrchestrator(flow_config_dir="./flows")
    print("✅ B2B 流程編排器已初始化")

    api_client = ExternalAPIClient(
        base_url=os.getenv("EXTERNAL_API_BASE_URL", "http://external-api:8080"),
        api_key=os.getenv("EXTERNAL_API_KEY")
    )
    print("✅ B2B 外部 API 客戶端已初始化")

    # 注入到 app.state
    app.state.session_manager = session_manager
    app.state.flow_orchestrator = flow_orchestrator
    app.state.api_client = api_client

    yield

    # 關閉時清理
    # ...

# 註冊路由
app.include_router(b2b_chat.router, prefix="/api/v1", tags=["b2b_chat"])
```

---

## 7. 使用範例

### 7.1 第一輪對話（無 session_id）

**請求**：

```json
POST /api/v1/b2b/chat

{
  "message": "我的合約為什麼不能點退？",
  "vendor_id": 1,
  "user_id": "vendor_user_123",
  "context": {
    "contract_id": "CONTRACT_456"
  }
}
```

**回應**：

```json
{
  "session_id": "abc123...",
  "message": "您的合約資料不完整，需補上以下資訊：\n- 簽約日期\n- 保證金收據\n\n請您補充完成後，回覆「已補好」或「補好了」。",
  "current_flow": "contract_cancel_check",
  "current_state": "waiting_for_documents",
  "requires_action": true,
  "timestamp": "2024-10-16T10:30:00Z"
}
```

---

### 7.2 第二輪對話（有 session_id）

**請求**：

```json
POST /api/v1/b2b/chat

{
  "message": "我已經補好了",
  "vendor_id": 1,
  "user_id": "vendor_user_123",
  "session_id": "abc123..."
}
```

**回應**：

```json
{
  "session_id": "abc123...",
  "message": "資料已確認完整！✅\n\n現在您可以執行點退流程了。請到合約管理頁面進行操作。",
  "current_flow": "contract_cancel_check",
  "current_state": "resolved",
  "requires_action": false,
  "timestamp": "2024-10-16T10:35:00Z"
}
```

---

## 8. 擴展方向

### 8.1 支援更多流程類型

可以輕鬆新增其他 B2B 流程：
- 繳費問題處理
- 帳單查詢
- 服務申請
- 故障報修

只需新增對應的 YAML 配置檔案即可。

### 8.2 整合更多外部 API

在 `ExternalAPIClient` 中新增方法：
- 查詢租客資訊
- 更新合約狀態
- 發送通知
- 觸發工單

### 8.3 狀態持久化優化

- 使用 Redis 提升性能
- 支援分散式鎖（避免並發問題）
- 實作狀態快照與回滾

### 8.4 流程可視化

- 提供管理介面編輯流程
- 流程執行追蹤與監控
- 流程執行日誌分析

---

## 9. 總結

此架構設計提供：

✅ **模組化**：SessionManager、FlowOrchestrator、APIClient 各司其職
✅ **可配置**：流程定義使用 YAML，無需改代碼
✅ **多輪對話**：session_id 追蹤會話狀態
✅ **外部 API 整合**：統一的 API 客戶端管理
✅ **狀態機控制**：清晰的流程狀態轉換
✅ **易擴展**：新增流程只需新增 YAML 配置

這個框架可以支援你的 B2B 場景需求，並且可以輕鬆擴展到更多業務流程。
