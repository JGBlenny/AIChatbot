"""unit：測試容器與 production 的 routing 行為參數必須同源（任務 3.1｜R9.4）。

**為什麼需要這條**：R9.4 要求離線驗證「完整複刻該版本 production 實際啟用的候選變換」——
其中包含**參數值**。任務 3.1 實跑逼出的事故：測試容器原本完全不帶 `.env`，
`KB_SIMILARITY_THRESHOLD` 未設 → `DecisionConfig` 落回程式預設 **0.55**，
而 production 容器實際跑 **0.65**。同一組測試在兩個門檻下候選集不同、紅的題目也不同，
用錯門檻做的對照會得出完全相反的結論（本專案已三次因 runner 保真度不足而結論作廢）。

本檔比對兩份 compose 對 routing 行為參數的宣告是否逐字一致。
⚠️ 只比**宣告**，不比執行期實際值——後者取決於宿主 env，非本檔可及。
"""
import os
import re

import pytest

pytestmark = pytest.mark.unit

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_PROD = os.path.join(_REPO, "docker-compose.prod.yml")
_DEV = os.path.join(_REPO, "docker-compose.dev.yml")

#: routing 決策會讀到的參數——任一邊漏宣告即可能靜默分歧
ROUTING_PARAMS = (
    "KB_SIMILARITY_THRESHOLD",
    "FORM_TRIGGER_THRESHOLD",
    "ENABLE_QUERY_REWRITE_B2B",
    "PREENTRY_ROUTABILITY_GATE",
)


def _declared(path: str, key: str) -> "str | None":
    """取 compose 檔中該鍵的宣告字串（去註解與前後空白）；未宣告回 None。"""
    for line in open(path, encoding="utf-8").read().splitlines():
        m = re.match(rf"\s*{re.escape(key)}:\s*(.+?)\s*(?:#.*)?$", line)
        if m:
            return m.group(1).strip()
    return None


@pytest.mark.req("conversational-routing-execution:9.4")
@pytest.mark.parametrize("key", ROUTING_PARAMS)
def test_dev_compose_mirrors_prod_declaration(key):
    prod = _declared(_PROD, key)
    dev = _declared(_DEV, key)
    assert prod is not None, f"{key} 未在 docker-compose.prod.yml 宣告——請同步更新本清單"
    assert dev is not None, (
        f"docker-compose.dev.yml 未宣告 {key}——測試容器會落回程式預設，"
        f"而 production 宣告為 {prod!r}。兩者若碰巧同值，任一邊改動即靜默分歧。")
    assert dev == prod, (
        f"{key} 宣告分歧：prod={prod!r} vs dev={dev!r}。"
        f"測試會在與 production 不同的組態下跑，其對照結論不可用（R9.4）。")


@pytest.mark.req("conversational-routing-execution:9.4")
def test_service_locations_are_container_view_not_host_view():
    """prod 宣告的服務位置，dev 必須逐字鏡射——不得讓 .env 的宿主視角值生效。

    `.env` 是宿主視角（`EMBEDDING_API_URL=http://localhost:5001/...`），
    容器內 `localhost` 指向容器自己。實測後果：向量檢索整組失效 → 檢索回空 →
    「應進對話」的案例全數變單發（59 筆）。與 DB_HOST 同一類 bug，只是換了服務。
    """
    import yaml
    prod_env = (yaml.safe_load(open(_PROD, encoding="utf-8").read())
                ["services"]["rag-orchestrator"].get("environment") or {})
    # 只管指向本堆疊內部服務者；外部端點（JGB、SMTP）不在此限
    internal = {k: str(v) for k, v in prod_env.items()
                if k.endswith("_URL") and "://" in str(v)
                and "localhost" not in str(v) and "${" not in str(v)}
    assert internal, "prod compose 找不到內部服務 URL 宣告——本測試的前提已變"
    for key, prod_val in sorted(internal.items()):
        dev_val = _declared(_DEV, key)
        assert dev_val == prod_val, (
            f"{key} 未鏡射 production：prod={prod_val!r} vs dev={dev_val!r}。"
            f"未覆蓋則 .env 的宿主視角值生效，容器內連不到該服務。")


@pytest.mark.req("conversational-routing-execution:9.4")
def test_dev_compose_overrides_connection_vars_with_test_namespace():
    """連線類變數必須用 TEST_* 覆蓋鍵——不得沿用裸名（會被宿主 .env 蓋成 production）。"""
    src = open(_DEV, encoding="utf-8").read()
    for key in ("DB_HOST", "DB_NAME", "DB_ENV", "DB_USER", "DB_PASSWORD", "REDIS_HOST"):
        decl = _declared(_DEV, key)
        assert decl and decl.startswith("${TEST_"), (
            f"{key} 的預設來源不是 TEST_* 命名空間（實際 {decl!r}）——"
            f"docker compose 會自動載入專案根目錄的 .env（宿主視角：localhost／aichatbot_admin），"
            f"用裸名會被直接蓋掉，測試將指向 production。")
