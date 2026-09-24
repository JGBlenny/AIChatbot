"""unit：知識匯入的 `target_user` 值域閘門（DSP-061／security review F5）。

`target_user_config` 是**資料面**設定表，可以放任何 `user_value`；
`KNOWN_TARGET_USERS` 是**程式面**值域，同時也是 `kb.search` SQL 謂詞的值域。
兩者不一致時，匯入必須當場大聲失敗——把值域外的字串寫進
`knowledge_base.target_user` 的失敗形狀是**靜默**：該列對所有身分永遠不可見、
檢索端無 log，只會被當成「知識庫沒這題」。

⚠️ 每條斷言都配正對照組：只驗「會 raise」而沒有「該過的會過」，
閘門寫成「一律 raise」時也會全綠。
"""
import time

import pytest

from services.knowledge_import_service import KnowledgeImportService
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:DSP-061")]


def _service(mapping):
    """不建 DB 連線的匯入服務：直接餵 `_load_target_user_config` 的快取。"""
    svc = KnowledgeImportService.__new__(KnowledgeImportService)
    svc._target_user_config_cache = mapping
    svc._target_user_cache_time = time.time()
    return svc


#: 設定表現況的替身：`landlord` 這類設定列仍可能存在（停用與否由業主的 DML 決定）。
_MAPPING = {
    "tenant": "tenant",
    "租客": "tenant",
    "landlord": "landlord",
    "property_manager": "property_manager",
    "房東": "property_manager",
    "prospect": "prospect",
}


async def test_landlord_row_raises_instead_of_silently_importing():
    svc = _service(_MAPPING)
    with pytest.raises(ValueError) as ei:
        await svc._normalize_target_user("landlord", row_ref="第 7 列")
    msg = str(ei.value)
    assert "'landlord'" in msg, msg          # 訊息點名值
    assert "第 7 列" in msg, msg              # 訊息點名來源列


async def test_known_values_pass_through():
    """正對照：值域內的值照樣匯入得了（中文顯示名稱也要通）。"""
    svc = _service(_MAPPING)
    assert await svc._normalize_target_user("property_manager", row_ref="第 1 列") == "property_manager"
    assert await svc._normalize_target_user("房東", row_ref="第 2 列") == "property_manager"
    assert await svc._normalize_target_user("租客", row_ref="第 3 列") == "tenant"


async def test_unmapped_audience_falls_back_to_tenant():
    """對象欄是自由文字：對不到設定表 ⇒ 落 tenant（既有行為，⛔ 不因閘門改成 raise）。"""
    svc = _service(_MAPPING)
    assert await svc._normalize_target_user("某種沒見過的對象", row_ref="第 4 列") == "tenant"
    assert await svc._normalize_target_user("") == "tenant"


def test_gate_reads_the_single_source_of_truth():
    """閘門的值域＝檢索器那一份（⛔ 不是匯入端自己抄的第二份）。"""
    known = VendorKnowledgeRetrieverV2.KNOWN_TARGET_USERS
    assert "landlord" not in known
    assert {"tenant", "property_manager", "system_admin", "prospect"} == set(known)
    for value in sorted(known):
        assert KnowledgeImportService._require_known_target_user(value, value, None) == value
