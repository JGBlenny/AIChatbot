#!/usr/bin/env python3
"""
ModuleMapper — 從 JGB 程式碼爬梳模組清單

掃描 JGB Laravel 專案 (routes, controllers, views, Vue pages)，
識別並整理功能模組，產出 jgb_module_inventory.json。

Usage:
    python3 scripts/kb_system_coverage/module_mapper.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # AIChatbot/
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import Feature, Module

# ---------------------------------------------------------------------------
# JGB 專案路徑
# ---------------------------------------------------------------------------
JGB_ROOT = Path("/Users/lenny/jgb/project/jgb/jgb2")
ROUTES_DIR = JGB_ROOT / "routes"
CONTROLLERS_DIR = JGB_ROOT / "app" / "Http" / "Controllers"
VUE_PAGES_DIR = JGB_ROOT / "src" / "pages"
VIEWS_DIR = JGB_ROOT / "resources" / "views"

OUTPUT_PATH = _SCRIPT_DIR / "jgb_module_inventory.json"


# ---------------------------------------------------------------------------
# Scanner helpers
# ---------------------------------------------------------------------------

def read_file_safe(path: Path) -> str:
    """Read file, return empty string on failure."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def scan_route_prefixes(route_file: Path) -> List[Tuple[str, str]]:
    """Extract route prefix groups and their comments from a Laravel route file.

    Returns list of (prefix, comment) tuples.
    """
    content = read_file_safe(route_file)
    results: List[Tuple[str, str]] = []

    # Match patterns like: Route::prefix('xxx') with optional preceding comment
    lines = content.split("\n")
    for i, line in enumerate(lines):
        m = re.search(r"Route::prefix\(['\"]([^'\"]+)['\"]\)", line)
        if m:
            prefix = m.group(1)
            # Look for comment in preceding lines
            comment = ""
            for j in range(max(0, i - 3), i):
                cm = re.search(r"//\s*(.+)", lines[j])
                if cm:
                    comment = cm.group(1).strip()
            results.append((prefix, comment))

    return results


def scan_controllers(base_dir: Path, subdir: str = "") -> List[str]:
    """List controller filenames (without .php) in a directory."""
    target = base_dir / subdir if subdir else base_dir
    if not target.is_dir():
        return []
    return [
        f.stem
        for f in target.iterdir()
        if f.is_file() and f.suffix == ".php" and f.stem != "Controller"
    ]


def scan_vue_pages(pages_dir: Path) -> List[str]:
    """List top-level Vue page directories."""
    if not pages_dir.is_dir():
        return []
    return [
        d.name
        for d in sorted(pages_dir.iterdir())
        if d.is_dir() and not d.name.startswith("_")
    ]


def scan_vue_subdirs(pages_dir: Path, page_name: str) -> List[str]:
    """List subdirectories inside a Vue page directory."""
    target = pages_dir / page_name
    if not target.is_dir():
        return []
    return [
        d.name
        for d in sorted(target.iterdir())
        if d.is_dir() and not d.name.startswith("_")
    ]


# ---------------------------------------------------------------------------
# Module definitions — based on actual JGB codebase analysis
# ---------------------------------------------------------------------------
# Each module is defined with knowledge from scanning the actual codebase:
# - routes/web.php, routes/api.php
# - app/Http/Controllers/ (root, Admin/, Vendors/, External/)
# - src/pages/ (Vue frontend)
# - resources/views/

def build_module_inventory() -> List[Module]:
    """Build the complete JGB module inventory from codebase analysis."""

    modules: List[Module] = []

    # -----------------------------------------------------------------------
    # 1. 物件管理 (Estate Management)
    # Evidence: EstateController, Admin\EstateController,
    #   src/pages/estates/, routes: /estates/*, /api2/estate/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="estate",
        module_name="物件管理",
        description="房源物件的建立、編輯、刊登、管理。包含一般物件與社會住宅物件的批次新增、iStaging 3D 看屋、物件地圖等功能。",
        features=[
            Feature("estate_001", "新增物件", ["landlord", "property_manager"], "both"),
            Feature("estate_002", "編輯物件資料", ["landlord", "property_manager"], "both"),
            Feature("estate_003", "刊登/取消刊登物件", ["landlord", "property_manager"], "both"),
            Feature("estate_004", "刪除物件", ["landlord", "property_manager"], "both"),
            Feature("estate_005", "複製物件", ["landlord", "property_manager"], "both"),
            Feature("estate_006", "物件列表與搜尋", ["landlord", "property_manager", "major_landlord"], "both"),
            Feature("estate_007", "物件地圖檢視", ["landlord", "property_manager"], "both"),
            Feature("estate_008", "物件儀表板", ["landlord", "property_manager"], "both"),
            Feature("estate_009", "一般物件批次新增", ["landlord", "property_manager"], "app"),
            Feature("estate_010", "社會住宅物件批次新增", ["property_manager"], "app"),
            Feature("estate_011", "iStaging 3D 看屋設定", ["landlord", "property_manager"], "app"),
            Feature("estate_012", "自訂費用項目", ["landlord", "property_manager"], "app"),
            Feature("estate_013", "物件月結報表", ["landlord", "property_manager"], "app"),
            Feature("estate_014", "物件 metadata 更新", ["landlord", "property_manager"], "app"),
            Feature("estate_015", "物件收藏管理", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 2. 合約管理 (Contract Management)
    # Evidence: ContractController, Admin\ContractController,
    #   src/pages/contracts/, routes: /contracts/*, /api2/contract/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="contract",
        module_name="合約管理",
        description="出租合約的完整生命週期管理：新建、編輯、簽署邀請、點交入住、點退退租、續約、提前解約等。含 PDF 預覽與電子簽章整合。",
        features=[
            Feature("contract_001", "新建合約", ["landlord", "property_manager"], "both"),
            Feature("contract_002", "編輯合約", ["landlord", "property_manager"], "both"),
            Feature("contract_003", "合約列表與搜尋", ["landlord", "property_manager", "tenant"], "both"),
            Feature("contract_004", "查看合約詳情", ["landlord", "property_manager", "tenant"], "both"),
            Feature("contract_005", "發送簽約邀請", ["landlord", "property_manager"], "both"),
            Feature("contract_006", "合約簽署確認", ["landlord", "property_manager", "tenant"], "both"),
            Feature("contract_007", "合約點交（入住）", ["landlord", "property_manager"], "both"),
            Feature("contract_008", "合約點退（退租）", ["landlord", "property_manager"], "both"),
            Feature("contract_009", "合約續約", ["landlord", "property_manager"], "both"),
            Feature("contract_010", "提前解約", ["landlord", "property_manager", "tenant"], "both"),
            Feature("contract_011", "合約 PDF 檢視/下載", ["landlord", "property_manager", "tenant"], "both"),
            Feature("contract_012", "合約摘要 PDF", ["landlord", "property_manager"], "both"),
            Feature("contract_013", "點交/點退 PDF", ["landlord", "property_manager"], "both"),
            Feature("contract_014", "合約物件封存資料查看", ["landlord", "property_manager"], "app"),
            Feature("contract_015", "合約批次刪除", ["landlord", "property_manager"], "app"),
            Feature("contract_016", "取消入住/退租", ["landlord", "property_manager"], "app"),
            Feature("contract_017", "合約 metadata 更新", ["landlord", "property_manager"], "app"),
            Feature("contract_018", "合約儲值金歷程查詢", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 3. 帳務管理 (Billing Management)
    # Evidence: BillController, Admin\BillController,
    #   src/pages/bills/, routes: /bills/*, /api2/bill/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="billing",
        module_name="帳務管理",
        description="租金帳單的建立、編輯、收款確認、催繳，以及帳務統計報表。包含週期帳單自動產生、社宅清冊、帳單批次匯入匯出等。",
        features=[
            Feature("billing_001", "帳單列表與搜尋", ["landlord", "property_manager", "tenant"], "both"),
            Feature("billing_002", "編輯帳單", ["landlord", "property_manager"], "both"),
            Feature("billing_003", "帳單收據 PDF", ["landlord", "property_manager", "tenant"], "both"),
            Feature("billing_004", "帳務統計報表", ["landlord", "property_manager"], "app"),
            Feature("billing_005", "帳務表單匯出", ["landlord", "property_manager"], "app"),
            Feature("billing_006", "帳單品項管理", ["landlord", "property_manager"], "app"),
            Feature("billing_007", "週期帳單自動產生", ["landlord", "property_manager"], "app"),
            Feature("billing_008", "帳單批次匯入匯出", ["landlord", "property_manager"], "app"),
            Feature("billing_009", "社宅清冊產生", ["property_manager"], "app"),
            Feature("billing_010", "帳單付款連結", ["tenant"], "app"),
            Feature("billing_011", "查看帳單明細", ["tenant"], "app"),
            Feature("billing_012", "費用項目群組設定", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 4. 修繕系統 (Repair System)
    # Evidence: RepairController, src/pages/repair/,
    #   routes: /repair/*, /api2/repairItem/*, /api2/repair/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="repair",
        module_name="修繕系統",
        description="報修提交、修繕項目管理、進度追蹤。租客可提交報修並追蹤進度，房東/管理公司可管理與處理修繕案件。",
        features=[
            Feature("repair_001", "修繕列表（依狀態/角色篩選）", ["landlord", "property_manager", "tenant"], "app"),
            Feature("repair_002", "提交報修申請", ["tenant"], "app"),
            Feature("repair_003", "查看修繕詳情", ["landlord", "property_manager", "tenant"], "app"),
            Feature("repair_004", "更新修繕進度", ["landlord", "property_manager"], "app"),
            Feature("repair_005", "選擇報修合約/物件", ["tenant"], "app"),
            Feature("repair_006", "修繕項目類別選擇", ["tenant"], "app"),
            Feature("repair_007", "修繕分享連結", ["landlord", "property_manager", "tenant"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 5. 支付金流 (Payment & Financial Flow)
    # Evidence: PaymentController, Admin\PaymentController,
    #   Admin\PaymentGatewayController, Vendors\ICashPayController,
    #   routes: /payments/*, admin/payments/*, admin/payment_gateway/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="payment",
        module_name="支付金流",
        description="線上繳費、金流對帳、退款處理。支援永豐金流、國泰 ATM、中信轉帳Pay、愛金卡（iCashPay）、信用卡自動扣款等多種金流管道。",
        features=[
            Feature("payment_001", "線上繳費（多金流管道）", ["tenant"], "app"),
            Feature("payment_002", "信用卡自動扣款授權", ["tenant"], "app"),
            Feature("payment_003", "付款紀錄查詢", ["landlord", "property_manager", "tenant"], "both"),
            Feature("payment_004", "收款設置（現金/線上）", ["landlord", "property_manager"], "app"),
            Feature("payment_005", "開通金流商（智付通/中信）", ["landlord", "property_manager"], "app"),
            Feature("payment_006", "訂閱方案付款", ["landlord", "property_manager"], "both"),
            Feature("payment_007", "永豐金流管理", ["landlord", "property_manager"], "admin"),
            Feature("payment_008", "國泰 ATM 即時入金", ["landlord", "property_manager"], "admin"),
            Feature("payment_009", "愛金卡（iCashPay）會員綁定與付款", ["tenant"], "app"),
            Feature("payment_010", "虛擬帳號繳費", ["tenant"], "app"),
            Feature("payment_011", "金流異常資料檢查", ["property_manager"], "admin"),
            Feature("payment_012", "帳單金流管理", ["property_manager"], "admin"),
            Feature("payment_013", "未對到帳紀錄查詢", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 6. IoT 設備管理 (IoT Device Management)
    # Evidence: IotController, Admin\IotManagementController,
    #   src/pages/iots/, routes: /iots/*, api3/iots/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="iot",
        module_name="IoT 設備管理",
        description="智慧門鎖、電表、攝影機等 IoT 設備的綁定、管理與操作。包含門鎖開關、電表讀數/儲值、設備密碼管理、QR Code 開鎖等功能。",
        features=[
            Feature("iot_001", "門鎖設備列表", ["landlord", "property_manager"], "app"),
            Feature("iot_002", "遠端開關門鎖", ["landlord", "property_manager", "tenant"], "app"),
            Feature("iot_003", "門鎖密碼管理", ["landlord", "property_manager"], "app"),
            Feature("iot_004", "分享門鎖密碼", ["landlord", "property_manager"], "app"),
            Feature("iot_005", "門鎖開門記錄", ["landlord", "property_manager"], "app"),
            Feature("iot_006", "QR Code 開鎖", ["landlord", "property_manager", "tenant"], "app"),
            Feature("iot_007", "電表設備管理", ["landlord", "property_manager"], "app"),
            Feature("iot_008", "電表讀數與統計圖表", ["landlord", "property_manager"], "app"),
            Feature("iot_009", "電表儲值操作", ["landlord", "property_manager"], "app"),
            Feature("iot_010", "電表斷電/恢復供電", ["landlord", "property_manager"], "app"),
            Feature("iot_011", "電表用量查詢", ["landlord", "property_manager"], "app"),
            Feature("iot_012", "電表費率變更記錄", ["landlord", "property_manager"], "app"),
            Feature("iot_013", "攝影機設備管理", ["landlord", "property_manager"], "app"),
            Feature("iot_014", "IoT 廠商帳號管理", ["landlord", "property_manager"], "app"),
            Feature("iot_015", "IoT 設備診斷工具", ["property_manager"], "admin"),
            Feature("iot_016", "手動電表儲值（客服）", ["property_manager"], "admin"),
            Feature("iot_017", "建立 Miezo 電表（客服）", ["property_manager"], "admin"),
            Feature("iot_018", "儲值電表查詢（客服）", ["property_manager"], "admin"),
            Feature("iot_019", "低電度警報查詢（客服）", ["property_manager"], "admin"),
            Feature("iot_020", "iStaging 設備查詢（客服）", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 7. 社區管理 (Community Management)
    # Evidence: CommunityController, src/pages/communities/,
    #   routes: /communities/*, /api2/estate/community
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="community",
        module_name="社區管理",
        description="社區/大樓的建立、編輯、物件綁定管理。包含社區總表、社區物件列表、社區廣告頁、強制綁定流程等。",
        features=[
            Feature("community_001", "社區列表總表", ["landlord", "property_manager"], "app"),
            Feature("community_002", "新增/編輯社區資料", ["landlord", "property_manager"], "app"),
            Feature("community_003", "社區物件列表管理", ["landlord", "property_manager"], "app"),
            Feature("community_004", "社區強制綁定流程", ["property_manager"], "app"),
            Feature("community_005", "社區廣告頁（對外展示）", ["landlord", "property_manager"], "app"),
            Feature("community_006", "社區挑選（關聯物件）", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 8. 大房東管理 (Major Landlord Management)
    # Evidence: BiglandlordController, Admin\BiglandlordController,
    #   src/pages/bigLandlords/, routes: /bigLandlord/*, /bigLandlords/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="big_landlord",
        module_name="大房東管理",
        description="大房東（屋主）的資料管理、物件權限設定、聯絡簿管理、報表排程發送。包含大房東清冊匯出、報表上傳等功能。",
        features=[
            Feature("big_landlord_001", "大房東列表與資料管理", ["property_manager"], "app"),
            Feature("big_landlord_002", "大房東物件權限設定", ["property_manager"], "app"),
            Feature("big_landlord_003", "大房東聯絡簿（匯入/匯出 Excel）", ["property_manager"], "app"),
            Feature("big_landlord_004", "大房東報表排程發送", ["property_manager"], "app"),
            Feature("big_landlord_005", "大房東報表上傳", ["property_manager"], "app"),
            Feature("big_landlord_006", "邀請未註冊大房東", ["property_manager"], "app"),
            Feature("big_landlord_007", "大房東清冊匯出（含綁定物件）", ["property_manager"], "admin"),
            Feature("big_landlord_008", "大房東月報表檢視", ["major_landlord"], "app"),
            Feature("big_landlord_009", "大房東物件總覽", ["major_landlord"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 9. 委託合約 (Entrusted Contract)
    # Evidence: EntrustedContractController, src/pages/entrustedContracts/,
    #   routes: /entrustedContracts/*, /api/entrustedContract/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="entrusted_contract",
        module_name="委託合約",
        description="房東與管理公司間的委託書管理。包含委託合約新建、編輯、簽署、確認、PDF 生成、提前解約等完整流程。",
        features=[
            Feature("entrusted_contract_001", "委託合約列表", ["landlord", "property_manager"], "app"),
            Feature("entrusted_contract_002", "新建委託合約", ["property_manager"], "app"),
            Feature("entrusted_contract_003", "編輯委託合約", ["property_manager"], "app"),
            Feature("entrusted_contract_004", "委託合約簽署邀請", ["property_manager"], "app"),
            Feature("entrusted_contract_005", "委託合約簽署確認", ["landlord", "property_manager"], "app"),
            Feature("entrusted_contract_006", "查看委託合約詳情", ["landlord", "property_manager"], "app"),
            Feature("entrusted_contract_007", "委託合約 PDF 檢視", ["landlord", "property_manager"], "app"),
            Feature("entrusted_contract_008", "委託合約取消", ["property_manager"], "app"),
            Feature("entrusted_contract_009", "委託合約提前解約", ["landlord", "property_manager"], "app"),
            Feature("entrusted_contract_010", "委託合約物件關聯查詢", ["landlord", "property_manager"], "app"),
            Feature("entrusted_contract_011", "雲想電子簽章確認", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 10. 差額發票 (Balance Invoice)
    # Evidence: BalanceInvoiceController, Admin\CustomerServiceController (balance_invoice_inquiry),
    #   src/pages/balanceInvoices/, routes: /api/balanceInvoices/*, /balanceinvoices/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="balance_invoice",
        module_name="差額發票",
        description="差額發票群組的建立、管理、開立與查詢。包含群組物件管理、發票開立/歸檔、報表下載、資料匯出等。",
        features=[
            Feature("balance_invoice_001", "差額發票群組列表", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_002", "新增差額發票群組", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_003", "編輯差額發票群組", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_004", "差額發票群組物件管理", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_005", "差額發票開立", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_006", "差額發票歸檔", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_007", "差額發票報表下載", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_008", "差額發票資料匯出", ["landlord", "property_manager"], "app"),
            Feature("balance_invoice_009", "差額發票盤查（客服）", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 11. 電子簽章 (E-Signature / ThinkCloud)
    # Evidence: ContractController@thinkcloud, EntrustedContractController@thinkcloudCheck,
    #   ExternalController@thinkcloud, Admin\ReportController@esignReport
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="esign",
        module_name="電子簽章",
        description="合約線上簽署（整合雲想 ThinkCloud 電子簽章服務）。支援出租合約與委託合約的電子簽署、簽署狀態追蹤等。",
        features=[
            Feature("esign_001", "合約電子簽署", ["landlord", "property_manager", "tenant"], "app"),
            Feature("esign_002", "簽署狀態追蹤", ["landlord", "property_manager", "tenant"], "app"),
            Feature("esign_003", "委託合約電子簽署", ["landlord", "property_manager"], "app"),
            Feature("esign_004", "電子簽章報表", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 12. 使用者帳號 (User Account)
    # Evidence: UserController, AuthController, Admin\UserController,
    #   src/pages/users/, routes: /users/*, /api2/authEmail/*,
    #   /api2/authPhone/*, /api2/login/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="user_account",
        module_name="使用者帳號",
        description="帳號註冊、登入、密碼管理、角色管理、團隊成員管理、會員中心。包含 Email/手機/SSO 登入、身份切換、帳號資訊管理等。",
        features=[
            Feature("user_account_001", "Email 註冊/登入", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_002", "手機號碼驗證登入", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_003", "SSO 單一登入", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_004", "忘記密碼", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_005", "帳號資訊管理", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_006", "團隊資訊管理", ["landlord", "property_manager"], "app"),
            Feature("user_account_007", "團隊成員管理", ["landlord", "property_manager"], "app"),
            Feature("user_account_008", "身份/角色切換", ["tenant", "landlord", "property_manager", "major_landlord"], "app"),
            Feature("user_account_009", "安全設定", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_010", "進階設定", ["landlord", "property_manager"], "app"),
            Feature("user_account_011", "簽約身份管理（租客）", ["tenant"], "app"),
            Feature("user_account_012", "租客簽約資訊", ["tenant"], "app"),
            Feature("user_account_013", "Dashboard 總覽", ["landlord", "property_manager", "tenant"], "app"),
            Feature("user_account_014", "登出", ["tenant", "landlord", "property_manager", "major_landlord"], "app"),
            Feature("user_account_015", "Email 變更驗證", ["tenant", "landlord", "property_manager"], "app"),
            Feature("user_account_016", "自訂標籤管理", ["landlord", "property_manager"], "app"),
            Feature("user_account_017", "團隊公司管理（新增/刪除）", ["landlord", "property_manager"], "app"),
            Feature("user_account_018", "團隊幣別設定", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 13. 通知系統 (Notification System)
    # Evidence: NotificationController, LineController, MessageController,
    #   src/pages/users/notification/, routes: /notifications/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="notification",
        module_name="通知系統",
        description="通知中心、推播設定、Email/簡訊/LINE 通知、訊息中心。包含 Navbar 通知、通知偏好設定、大聲公群發訊息等。",
        features=[
            Feature("notification_001", "通知中心列表", ["tenant", "landlord", "property_manager"], "app"),
            Feature("notification_002", "通知偏好設定", ["tenant", "landlord", "property_manager"], "app"),
            Feature("notification_003", "Navbar 未讀通知", ["tenant", "landlord", "property_manager"], "app"),
            Feature("notification_004", "LINE 推播通知", ["tenant", "landlord", "property_manager"], "app"),
            Feature("notification_005", "大聲公群發訊息", ["landlord", "property_manager"], "app"),
            Feature("notification_006", "Email 通知", ["tenant", "landlord", "property_manager"], "app"),
            Feature("notification_007", "租客邀請訂閱通知", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 14. 訂閱方案 (Subscription)
    # Evidence: UserController@subscription, UserController@subscriptionChose,
    #   UserController@unsubscribe, Admin\PaymentController@subscriptions,
    #   src/pages/users/subscription/, Admin\ToolController@transferSubscription
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="subscription",
        module_name="訂閱方案",
        description="JGB 平台訂閱方案選擇、付款、退訂、方案變更。包含方案比較、優惠碼使用、訂閱紀錄管理等。",
        features=[
            Feature("subscription_001", "訂閱方案選擇", ["landlord", "property_manager"], "app"),
            Feature("subscription_002", "訂閱方案付款", ["landlord", "property_manager"], "app"),
            Feature("subscription_003", "退訂方案", ["landlord", "property_manager"], "app"),
            Feature("subscription_004", "查看目前方案", ["landlord", "property_manager"], "app"),
            Feature("subscription_005", "優惠碼使用", ["landlord", "property_manager"], "app"),
            Feature("subscription_006", "訂閱紀錄管理", ["property_manager"], "admin"),
            Feature("subscription_007", "方案移轉（客服工具）", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 15. 租客管理 (Lessee / Tenant Management)
    # Evidence: LesseeController, routes: /api/lessee/*, /api/lessees/*,
    #   src/pages/users/lesseeList/
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="lessee",
        module_name="租客管理",
        description="租客資料的新增、編輯、封存、匯入。包含租客列表、租客搜尋、租客合約/帳單/修繕關聯查詢、批次匯入等。",
        features=[
            Feature("lessee_001", "租客列表", ["landlord", "property_manager"], "app"),
            Feature("lessee_002", "新增租客", ["landlord", "property_manager"], "app"),
            Feature("lessee_003", "編輯租客資料", ["landlord", "property_manager"], "app"),
            Feature("lessee_004", "封存租客", ["landlord", "property_manager"], "app"),
            Feature("lessee_005", "租客狀態檢查", ["landlord", "property_manager"], "app"),
            Feature("lessee_006", "租客合約列表查詢", ["landlord", "property_manager"], "app"),
            Feature("lessee_007", "租客帳單列表查詢", ["landlord", "property_manager"], "app"),
            Feature("lessee_008", "租客修繕列表查詢", ["landlord", "property_manager"], "app"),
            Feature("lessee_009", "租客批次匯入", ["landlord", "property_manager"], "app"),
            Feature("lessee_010", "租客搜尋", ["landlord", "property_manager"], "app"),
            Feature("lessee_011", "邀請租客訂閱通知", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 16. 發票管理 (Invoice Management)
    # Evidence: InvoiceController, Admin\InvoiceFailureController,
    #   Admin\InvoiceSupplementController, Admin\RoleInvoiceController,
    #   routes: /api/invoice/callback, admin/invoice-failures/*, admin/customer_service/invoice_supplement/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="invoice",
        module_name="發票管理",
        description="電子發票開立、發票異常處理、發票補開、團隊發票設置。包含發票回調處理、發票異常盤查/通知、帳單發票補開等。",
        features=[
            Feature("invoice_001", "帳單發票自動開立", ["landlord", "property_manager"], "app"),
            Feature("invoice_002", "發票異常盤查", ["property_manager"], "admin"),
            Feature("invoice_003", "發票異常通知", ["property_manager"], "admin"),
            Feature("invoice_004", "帳單發票補開/重開", ["property_manager"], "admin"),
            Feature("invoice_005", "團隊發票設置管理", ["property_manager"], "admin"),
            Feature("invoice_006", "帳單手動開立發票", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 17. 固定虛擬帳號管理 (Recharge Account Management)
    # Evidence: RechargeAccountListController, External\RechargeAccountApiController,
    #   src/pages/users/rechargeAccountList/, routes: /api/recharge-accounts/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="recharge_account",
        module_name="固定虛擬帳號管理",
        description="固定虛擬帳號的建立、管理、匯出。包含帳號綁定物件/合約、帳號歷程查詢、外部匯入等功能。",
        features=[
            Feature("recharge_account_001", "虛擬帳號列表", ["landlord", "property_manager"], "app"),
            Feature("recharge_account_002", "新增虛擬帳號", ["landlord", "property_manager"], "app"),
            Feature("recharge_account_003", "編輯虛擬帳號", ["landlord", "property_manager"], "app"),
            Feature("recharge_account_004", "刪除虛擬帳號", ["landlord", "property_manager"], "app"),
            Feature("recharge_account_005", "虛擬帳號歷程查詢", ["landlord", "property_manager"], "app"),
            Feature("recharge_account_006", "虛擬帳號資料匯出", ["landlord", "property_manager"], "app"),
            Feature("recharge_account_007", "虛擬帳號查詢（客服）", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 18. 物件刊登與搜尋 (Listing & Search)
    # Evidence: ListingController, SearchController,
    #   src/pages/listings/, routes: /api2/getListingsData/*, /api2/listings/search
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="listing",
        module_name="物件刊登與搜尋",
        description="對外的物件刊登頁面、搜尋功能、地圖搜尋。租屋搜尋者可瀏覽已刊登物件、地圖模式搜尋、查看物件詳情等。",
        features=[
            Feature("listing_001", "物件搜尋列表", ["tenant"], "app"),
            Feature("listing_002", "地圖模式搜尋物件", ["tenant"], "app"),
            Feature("listing_003", "物件詳情頁面", ["tenant"], "app"),
            Feature("listing_004", "房東招租店鋪頁面", ["tenant"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 19. 簽核管理 (Approval)
    # Evidence: ApprovalController, src/pages/users/approval/,
    #   routes: api3/users/approval/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="approval",
        module_name="簽核管理",
        description="團隊內部簽核流程管理。包含簽核專案建立、簽核流程處理、簽核狀態查詢等。",
        features=[
            Feature("approval_001", "簽核專案列表", ["landlord", "property_manager"], "app"),
            Feature("approval_002", "簽核流程處理", ["landlord", "property_manager"], "app"),
            Feature("approval_003", "簽核狀態查詢", ["landlord", "property_manager"], "app"),
            Feature("approval_004", "新增簽核", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 20. 住都中心（NTHURC）專案管理
    # Evidence: NthurcController, NthurcParkingController,
    #   src/pages/nthurc/, src/pages/nthurc-parking/,
    #   routes: api3/nthurc/*, api3/nthurc-parking/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="nthurc",
        module_name="住都中心專案管理",
        description="新北住都中心社會住宅專用功能。包含活動列表管理、租客清單、車位活動管理、稅別調整等。",
        features=[
            Feature("nthurc_001", "住都活動列表管理", ["property_manager"], "app"),
            Feature("nthurc_002", "住都租客清單管理", ["property_manager"], "app"),
            Feature("nthurc_003", "車位活動列表管理", ["property_manager"], "app"),
            Feature("nthurc_004", "車位租客清單管理", ["property_manager"], "app"),
            Feature("nthurc_005", "住都合約稅別調整（客服）", ["property_manager"], "admin"),
            Feature("nthurc_006", "取消合約延長（住都）", ["property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 21. 押金設算息 (Deposit Interest)
    # Evidence: DepositInterestController,
    #   Admin\FeatureConfigController@depositInterestSettings,
    #   routes: api3/depositInterest/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="deposit_interest",
        module_name="押金設算息",
        description="押金利息計算功能。依合約押金金額與期間自動計算應退利息，支援批次查詢與計算。",
        features=[
            Feature("deposit_interest_001", "押金設算息計算", ["landlord", "property_manager"], "app"),
            Feature("deposit_interest_002", "押金設算息查詢", ["landlord", "property_manager"], "app"),
            Feature("deposit_interest_003", "押金設算息設定（後台）", ["property_manager"], "admin"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 22. 後台管理工具 (Admin Tools & Customer Service)
    # Evidence: Admin\CustomerServiceController, Admin\ToolController,
    #   Admin\PermissionController, Admin\LogController,
    #   routes: admin/customer_service/*, admin/tools/*, admin/permissions/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="admin_tools",
        module_name="後台管理工具",
        description="JGB 後台管理專用工具：權限管理、客服專區、紀錄管理、系統工具。僅限 JGB 內部管理人員使用。",
        features=[
            Feature("admin_tools_001", "權限群組管理", ["property_manager"], "admin"),
            Feature("admin_tools_002", "管理者帳號管理", ["property_manager"], "admin"),
            Feature("admin_tools_003", "會員資料管理", ["property_manager"], "admin"),
            Feature("admin_tools_004", "客戶使用資料查詢", ["property_manager"], "admin"),
            Feature("admin_tools_005", "功能配置管理", ["property_manager"], "admin"),
            Feature("admin_tools_006", "點退合約管理（客服）", ["property_manager"], "admin"),
            Feature("admin_tools_007", "永豐金流解密查詢（客服）", ["property_manager"], "admin"),
            Feature("admin_tools_008", "用戶資訊修改（客服）", ["property_manager"], "admin"),
            Feature("admin_tools_009", "修改合約狀態（客服）", ["property_manager"], "admin"),
            Feature("admin_tools_010", "住都租客新增（客服）", ["property_manager"], "admin"),
            Feature("admin_tools_011", "Email/簡訊記錄查詢", ["property_manager"], "admin"),
            Feature("admin_tools_012", "管理者異動記錄", ["property_manager"], "admin"),
            Feature("admin_tools_013", "排程執行紀錄/報表", ["property_manager"], "admin"),
            Feature("admin_tools_014", "全站異動紀錄", ["property_manager"], "admin"),
            Feature("admin_tools_015", "系統寄信工具", ["property_manager"], "admin"),
            Feature("admin_tools_016", "排程管理", ["property_manager"], "admin"),
            Feature("admin_tools_017", "統計報表", ["property_manager"], "admin"),
            Feature("admin_tools_018", "Botbonnie 設定管理（客服）", ["property_manager"], "admin"),
            Feature("admin_tools_019", "合約租金修改（客戶）", ["property_manager"], "admin"),
            Feature("admin_tools_020", "代管帳號管理", ["landlord", "property_manager"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 23. LINE 整合 (LINE Integration)
    # Evidence: LineController, BotbonnieSettingController,
    #   BotbonnieWebhookController, routes: /lines/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="line_integration",
        module_name="LINE 整合",
        description="LINE 官方帳號整合功能。包含 LINE Bot Webhook、LINE LIFF 介面、LINE 通知推播、Botbonnie 聊天機器人整合等。",
        features=[
            Feature("line_integration_001", "LINE 帳號綁定", ["tenant", "landlord", "property_manager"], "app"),
            Feature("line_integration_002", "LINE Bot 通知接收", ["tenant", "landlord", "property_manager"], "app"),
            Feature("line_integration_003", "LINE LIFF 介面操作", ["tenant", "landlord", "property_manager"], "app"),
            Feature("line_integration_004", "Botbonnie 聊天機器人", ["tenant"], "app"),
        ],
    ))

    # -----------------------------------------------------------------------
    # 24. 外部 API (External API)
    # Evidence: External\EstateApiController, External\RechargeAccountApiController,
    #   ExternalController, routes: api/external/v1/*
    # -----------------------------------------------------------------------
    modules.append(Module(
        module_id="external_api",
        module_name="外部 API 整合",
        description="對外系統 API 接口。包含物件資料 API、虛擬帳號匯入 API、住都財會串接、雲想圖章外部呼叫等。",
        features=[
            Feature("external_api_001", "物件資料 API（對外）", ["agent"], "app"),
            Feature("external_api_002", "虛擬帳號匯入 API", ["agent"], "app"),
            Feature("external_api_003", "住都財會串接 API", ["property_manager"], "app"),
        ],
    ))

    return modules


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def verify_against_codebase(modules: List[Module]) -> Dict[str, any]:
    """Run basic verification that modules map to actual codebase artifacts."""
    stats = {
        "total_modules": len(modules),
        "total_features": sum(len(m.features) for m in modules),
        "modules_with_controller": 0,
        "modules_with_vue_page": 0,
        "roles_found": set(),
        "entry_points": {"app": 0, "admin": 0, "both": 0},
    }

    # Controller mapping check
    root_controllers = set(scan_controllers(CONTROLLERS_DIR))
    admin_controllers = set(scan_controllers(CONTROLLERS_DIR, "Admin"))
    vue_pages = set(scan_vue_pages(VUE_PAGES_DIR))

    controller_map = {
        "estate": "EstateController",
        "contract": "ContractController",
        "billing": "BillController",
        "repair": "RepairController",
        "payment": "PaymentController",
        "iot": "IotController",
        "community": "CommunityController",
        "big_landlord": "BiglandlordController",
        "entrusted_contract": "EntrustedContractController",
        "balance_invoice": "BalanceInvoiceController",
        "user_account": "UserController",
        "notification": "NotificationController",
        "lessee": "LesseeController",
        "invoice": "InvoiceController",
        "recharge_account": "RechargeAccountListController",
        "listing": "ListingController",
        "approval": "ApprovalController",
        "nthurc": "NthurcController",
        "deposit_interest": "DepositInterestController",
        "line_integration": "LineController",
    }

    vue_map = {
        "estate": "estates",
        "contract": "contracts",
        "billing": "bills",
        "repair": "repair",
        "iot": "iots",
        "community": "communities",
        "big_landlord": "bigLandlords",
        "entrusted_contract": "entrustedContracts",
        "balance_invoice": "balanceInvoices",
        "user_account": "users",
        "listing": "listings",
        "nthurc": "nthurc",
    }

    for m in modules:
        # Check controller
        ctrl_name = controller_map.get(m.module_id)
        if ctrl_name and ctrl_name in root_controllers | admin_controllers:
            stats["modules_with_controller"] += 1

        # Check Vue page
        vue_name = vue_map.get(m.module_id)
        if vue_name and vue_name in vue_pages:
            stats["modules_with_vue_page"] += 1

        for f in m.features:
            for role in f.roles:
                stats["roles_found"].add(role)
            stats["entry_points"][f.entry_point] += 1

    stats["roles_found"] = sorted(stats["roles_found"])
    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("ModuleMapper — JGB 系統功能模組爬梳")
    print("=" * 60)

    # Verify JGB codebase exists
    if not JGB_ROOT.is_dir():
        print(f"ERROR: JGB codebase not found at {JGB_ROOT}")
        sys.exit(1)

    print(f"\nJGB 專案路徑: {JGB_ROOT}")
    print(f"輸出路徑: {OUTPUT_PATH}")

    # Build inventory
    print("\n--- 開始爬梳模組 ---")
    modules = build_module_inventory()

    # Verify
    print("\n--- 驗證結果 ---")
    stats = verify_against_codebase(modules)
    print(f"  模組總數: {stats['total_modules']}")
    print(f"  功能項目總數: {stats['total_features']}")
    print(f"  有對應 Controller 的模組: {stats['modules_with_controller']}")
    print(f"  有對應 Vue Page 的模組: {stats['modules_with_vue_page']}")
    print(f"  涵蓋角色: {', '.join(stats['roles_found'])}")
    print(f"  入口分佈: app={stats['entry_points']['app']}, "
          f"admin={stats['entry_points']['admin']}, "
          f"both={stats['entry_points']['both']}")

    # Serialize to JSON
    output_data = [asdict(m) for m in modules]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 已產出 {OUTPUT_PATH}")
    print(f"  共 {len(modules)} 個模組、{sum(len(m.features) for m in modules)} 個功能項目")

    # Print module summary
    print("\n--- 模組摘要 ---")
    for m in modules:
        roles_in_module: Set[str] = set()
        entries_in_module: Set[str] = set()
        for f in m.features:
            roles_in_module.update(f.roles)
            entries_in_module.add(f.entry_point)
        print(f"  [{m.module_id}] {m.module_name} "
              f"({len(m.features)} features, "
              f"roles={','.join(sorted(roles_in_module))}, "
              f"entry={','.join(sorted(entries_in_module))})")


if __name__ == "__main__":
    main()
