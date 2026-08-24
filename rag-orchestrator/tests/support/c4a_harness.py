"""C4a 執行觀測 primitive（任務 5.3／5.4 共用）。

⚠️ **兩種事件必須分開觀測**（5.4 最容易假紅之處）：

```text
transport endpoint call     adapter 為取得 bill facts 自行呼叫 detail 也算在內
Face secondary_call dispatch  面向設定的 `secondary_call` 真的被派發
```

5.3 實測：一次收斂中 detail 端點被呼叫**兩次**（adapter 數字分支一次、面向 secondary_call 一次）。
故**不得**以「`bill_detail` 有沒有被呼叫」代表 secondary call 是否發生——
`billing_anomaly`（`secondary_call_required=false`）仍會因 adapter 數字分支打一次 detail。
"""

DETAIL_TMPL = "/api/external/v1/bills/{bill_id}"


class RecordingTransport:
    """記錄每一次 transport 請求，再委派給真 mock transport（OB-3 的落點）。"""

    def __init__(self, inner):
        self.inner = inner
        self.calls = []          # [(method, path, params)]

    async def send(self, method, path, *, params=None, data=None):
        self.calls.append((method, path, dict(params or {})))
        return await self.inner.send(method, path, params=params, data=data)

    def endpoint_keys(self):
        from services.jgb.transport import resolve_endpoint
        return [resolve_endpoint(m, p) for m, p, _ in self.calls]

    def detail_bill_ids(self):
        from services.jgb.transport import match_template
        out = []
        for _, path, _ in self.calls:
            hit = match_template(DETAIL_TMPL, path)
            if hit:
                out.append(int(hit["bill_id"]))
        return out


class RecordingHandler:
    """包住真 `APICallHandler`，記錄每一次 `execute_api_call` 的 endpoint。

    ⚠️ **Face secondary_call 的可觀測事件**：`_ground_by_api` 先派發主查詢，
    其後於同一次收斂內對 `secondary_call` 再派發一次 `execute_api_call`
    （services/conversational_engine.py:985-987）。
    故 **第一次以後的派發即為 secondary dispatch**——這與 transport 層的 detail 呼叫是兩回事。
    """

    def __init__(self, inner):
        self._inner = inner
        self.dispatched = []     # [endpoint]

    async def execute_api_call(self, api_config, session_data, form_data, **kwargs):
        self.dispatched.append((api_config or {}).get("endpoint"))
        return await self._inner.execute_api_call(api_config, session_data, form_data, **kwargs)

    def secondary_dispatch_count(self) -> int:
        return max(0, len(self.dispatched) - 1)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def install_recorders(handler):
    """在真 handler 上裝配兩層記錄器，回傳 `(handler_proxy, transport_recorder)`。"""
    inner_transport = handler.jgb_api._mock_transport
    assert inner_transport is not None, "mock transport 未裝配（4.6 應已裝配 fixture 表）"
    rec = RecordingTransport(inner_transport)
    handler.jgb_api._mock_transport = rec
    return RecordingHandler(handler), rec
