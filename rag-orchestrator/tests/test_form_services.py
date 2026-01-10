"""
表單服務測試腳本
用於驗證 FormManager、FormValidator、DigressionDetector 是否正常工作
"""
import asyncio
from form_manager import FormManager, FormState
from form_validator import FormValidator
from digression_detector import DigressionDetector, DigressionType


async def test_form_manager():
    """測試 FormManager"""
    print("\n" + "=" * 60)
    print("測試 FormManager")
    print("=" * 60)

    manager = FormManager()

    # 測試 1: 獲取表單定義
    print("\n📝 測試 1: 獲取表單定義")
    form_schema = await manager.get_form_schema('rental_application')
    if form_schema:
        print(f"   ✅ 表單名稱: {form_schema['form_name']}")
        print(f"   ✅ 欄位數量: {len(form_schema['fields'])}")
    else:
        print("   ❌ 獲取表單定義失敗")

    # 測試 2: 根據意圖查找表單
    print("\n📝 測試 2: 根據意圖查找表單")
    form = await manager.find_form_by_intent('租屋申請', vendor_id=1)
    if form:
        print(f"   ✅ 找到表單: {form['form_name']}")
    else:
        print("   ❌ 未找到匹配的表單")

    # 測試 3: 創建表單會話
    print("\n📝 測試 3: 創建表單會話")
    session_id = "test_session_123"
    session = await manager.create_form_session(
        session_id=session_id,
        user_id="test_user",
        vendor_id=1,
        form_id='rental_application'
    )
    if session:
        print(f"   ✅ 會話創建成功")
        print(f"   ✅ 會話 ID: {session['session_id']}")
        print(f"   ✅ 狀態: {session['state']}")
        print(f"   ✅ 當前欄位索引: {session['current_field_index']}")
    else:
        print("   ❌ 會話創建失敗")

    # 測試 4: 查詢會話狀態
    print("\n📝 測試 4: 查詢會話狀態")
    retrieved_session = await manager.get_session_state(session_id)
    if retrieved_session:
        print(f"   ✅ 會話查詢成功")
        print(f"   ✅ 狀態: {retrieved_session['state']}")
    else:
        print("   ❌ 會話查詢失敗")

    # 測試 5: 更新會話狀態
    print("\n📝 測試 5: 更新會話狀態")
    updated_session = await manager.update_session_state(
        session_id=session_id,
        current_field_index=1
    )
    if updated_session:
        print(f"   ✅ 會話更新成功")
        print(f"   ✅ 新的欄位索引: {updated_session['current_field_index']}")
    else:
        print("   ❌ 會話更新失敗")

    print("\n" + "=" * 60)


def test_form_validator():
    """測試 FormValidator"""
    print("\n" + "=" * 60)
    print("測試 FormValidator")
    print("=" * 60)

    validator = FormValidator()

    # 測試案例
    test_cases = [
        {
            "name": "台灣身分證號碼（有效）",
            "field_config": {
                "field_name": "id_number",
                "field_label": "身分證字號",
                "field_type": "text",
                "validation_type": "taiwan_id",
                "required": True
            },
            "user_input": "A123456789",
            "expected_valid": True
        },
        {
            "name": "台灣身分證號碼（無效）",
            "field_config": {
                "field_name": "id_number",
                "field_label": "身分證字號",
                "field_type": "text",
                "validation_type": "taiwan_id",
                "required": True
            },
            "user_input": "X999999999",
            "expected_valid": False
        },
        {
            "name": "手機號碼（有效）",
            "field_config": {
                "field_name": "phone",
                "field_label": "聯絡電話",
                "field_type": "text",
                "validation_type": "phone",
                "required": True
            },
            "user_input": "0912345678",
            "expected_valid": True
        },
        {
            "name": "手機號碼（無效）",
            "field_config": {
                "field_name": "phone",
                "field_label": "聯絡電話",
                "field_type": "text",
                "validation_type": "phone",
                "required": True
            },
            "user_input": "12345",
            "expected_valid": False
        },
        {
            "name": "台灣姓名（中文）",
            "field_config": {
                "field_name": "full_name",
                "field_label": "全名",
                "field_type": "text",
                "validation_type": "taiwan_name",
                "required": True
            },
            "user_input": "王小明",
            "expected_valid": True
        },
        {
            "name": "地址（有效）",
            "field_config": {
                "field_name": "address",
                "field_label": "通訊地址",
                "field_type": "text",
                "validation_type": "address",
                "required": True,
                "max_length": 200
            },
            "user_input": "台北市信義區信義路五段7號",
            "expected_valid": True
        }
    ]

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 測試案例 {i}: {test_case['name']}")
        is_valid, extracted_value, error_message = validator.validate_field(
            field_config=test_case['field_config'],
            user_input=test_case['user_input']
        )

        if is_valid == test_case['expected_valid']:
            print(f"   ✅ 通過")
            if is_valid:
                print(f"   ✅ 提取值: {extracted_value}")
            else:
                print(f"   ✅ 錯誤訊息: {error_message}")
            passed += 1
        else:
            print(f"   ❌ 失敗")
            print(f"   預期: {'有效' if test_case['expected_valid'] else '無效'}")
            print(f"   實際: {'有效' if is_valid else '無效'}")
            if error_message:
                print(f"   錯誤訊息: {error_message}")
            failed += 1

    print(f"\n✅ 通過: {passed} / {len(test_cases)}")
    print(f"❌ 失敗: {failed} / {len(test_cases)}")
    print("=" * 60)


async def test_digression_detector():
    """測試 DigressionDetector"""
    print("\n" + "=" * 60)
    print("測試 DigressionDetector")
    print("=" * 60)

    detector = DigressionDetector()

    # 模擬欄位配置
    current_field = {
        "field_name": "full_name",
        "field_label": "全名",
        "prompt": "請問您的全名是？"
    }

    # 模擬表單定義
    form_schema = {
        "form_name": "租屋申請表",
        "trigger_intents": ["租屋申請", "我要租房"]
    }

    # 測試案例
    test_cases = [
        {
            "name": "明確退出",
            "user_message": "取消",
            "expected_type": DigressionType.EXPLICIT_EXIT
        },
        {
            "name": "問問題",
            "user_message": "為什麼需要提供全名？",
            "expected_type": DigressionType.QUESTION
        },
        {
            "name": "正常回答",
            "user_message": "王小明",
            "expected_type": None
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 測試案例 {i}: {test_case['name']}")
        is_digression, digression_type, confidence = await detector.detect(
            user_message=test_case['user_message'],
            current_field=current_field,
            form_schema=form_schema,
            intent_result=None
        )

        if is_digression:
            print(f"   🚩 檢測到離題")
            print(f"   ✅ 離題類型: {digression_type}")
            print(f"   ✅ 置信度: {confidence:.2f}")
        else:
            print(f"   ✅ 未檢測到離題")

    print("\n" + "=" * 60)


async def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("表單服務測試套件")
    print("=" * 80)

    # 測試 FormManager
    await test_form_manager()

    # 測試 FormValidator
    test_form_validator()

    # 測試 DigressionDetector
    await test_digression_detector()

    print("\n" + "=" * 80)
    print("所有測試完成！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
