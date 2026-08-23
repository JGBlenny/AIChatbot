"""unit：測試資料庫安全邊界（spec conversational-routing-execution 任務 2.1｜R1.2）。

守的是一句話：**解析出的 DB target 若不能證明是 test DB，就拒絕連線。**

背景：任務 1.2 把測試容器接上 `aichatbot_default` 網路後，它看得見 production DB。
`session_id` 前綴隔離與 `finally` 清理是清理機制、不是隔離機制——
它們假設測試已經連到正確的庫；連錯庫時，它們清的就是 production 的資料。

⚠️ 特別注意 `DB_NAME` **未設**的情形：產線碼預設 `aichatbot_admin`，
故「未設」不是「未知」，而是「已經指向 production」——必須拒絕。
"""
import pytest

from tests.conftest import (
    ALLOWED_TEST_DATABASES,
    ProductionDatabaseRefused,
    assert_non_production_db,
    resolve_db_target,
)

pytestmark = pytest.mark.unit


# ── 必須拒絕（fail closed）──
@pytest.mark.req("conversational-routing-execution:1.2")
@pytest.mark.parametrize("db_name,db_env,why", [
    ("aichatbot_test",  None,          "DB_ENV 缺值＝未證明"),
    ("aichatbot_test",  "",            "DB_ENV 空字串＝未證明"),
    ("aichatbot_test",  "   ",         "DB_ENV 純空白＝未證明"),
    ("aichatbot_test",  "production",  "明確宣告 production"),
    ("aichatbot_test",  "PRODUCTION",  "大小寫不得繞過"),
    ("aichatbot_admin", "test",        "production 庫名不在白名單"),
    ("random_db",       "test",        "任意庫名不在白名單"),
    ("aichatbot_admin", None,          "兩道皆不過"),
])
def test_refuses_unless_proven_test_db(db_name, db_env, why):
    with pytest.raises(ProductionDatabaseRefused):
        assert_non_production_db(db_name=db_name, db_env=db_env)


# ── 必須放行 ──
@pytest.mark.req("conversational-routing-execution:1.2")
@pytest.mark.parametrize("db_name", sorted(ALLOWED_TEST_DATABASES))
def test_allows_whitelisted_test_db(db_name):
    assert_non_production_db(db_name=db_name, db_env="test")


@pytest.mark.req("conversational-routing-execution:1.2")
def test_whitelist_is_not_a_blacklist():
    """白名單語義：不在清單內一律拒絕，不是「只擋已知的 production 名稱」。"""
    assert "aichatbot_admin" not in ALLOWED_TEST_DATABASES
    with pytest.raises(ProductionDatabaseRefused):
        assert_non_production_db(db_name="some_new_db_nobody_listed", db_env="test")


# ── 解析：未設 DB_NAME 等同指向 production ──
@pytest.mark.req("conversational-routing-execution:1.2")
def test_unset_db_name_resolves_to_production_and_is_refused(monkeypatch):
    """`DB_NAME` 未設 → 產線碼預設 aichatbot_admin → 必須被攔下。

    這是最容易漏的一條：守門若只驗「有沒有設」而不驗「解析結果」，
    未設的情形會直接連上 production。
    """
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.setenv("DB_ENV", "test")
    name, env = resolve_db_target()
    assert name == "aichatbot_admin", "產線預設值已變動，本測試與守門需同步更新"
    with pytest.raises(ProductionDatabaseRefused):
        assert_non_production_db(db_name=name, db_env=env)


@pytest.mark.req("conversational-routing-execution:1.2")
def test_resolve_reads_actual_env(monkeypatch):
    monkeypatch.setenv("DB_NAME", "aichatbot_test")
    monkeypatch.setenv("DB_ENV", "test")
    assert resolve_db_target() == ("aichatbot_test", "test")
