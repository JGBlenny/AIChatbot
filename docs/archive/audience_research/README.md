# Audience 系統研究資料 (已廢棄)

> ⚠️ **此目錄包含已廢棄的 Audience 系統相關文檔**

**廢棄日期**: 2025-10-28
**取代系統**: Target User Config
**原因**: Audience 系統混合了業務範圍 (B2B/B2C) 和用戶角色的概念，已被更清晰的 Target User Config 取代

## 📁 檔案清單

### 分析文檔 (從根目錄移入)

1. **audience_summary.md** (4.6 KB, 2025-10-27)
   - Audience 系統摘要說明
   - 包含系統設計概念

2. **audience_evaluation.md** (11 KB, 2025-10-27)
   - Audience 評估報告
   - 功能評估和問題分析

3. **audience_field_analysis.md** (8.1 KB, 2025-10-27)
   - Audience 欄位分析
   - 資料結構說明

## 🔄 遷移說明

### 舊系統 (Audience)
```
audience 欄位混合概念：
- B2C: 租客、房東 (external scope)
- B2B: 管理師、系統管理員 (internal scope)
- 混合: 租客|管理師 (跨場景)

問題：
- 概念不清晰
- 難以擴展
- 前後端邏輯複雜
```

### 新系統 (Target User Config)
```
分離為兩個獨立概念：

1. business_scope (由 user_role 決定)
   - external: user_role = 'customer'
   - internal: user_role = 'staff'

2. target_user (PostgreSQL ARRAY)
   - ['tenant'] - 租客
   - ['landlord'] - 房東
   - ['property_manager'] - 物業管理師
   - ['tenant', 'property_manager'] - 多選

優勢：
- 關注點分離
- 語意清晰
- 易於擴展
- 支援多選
```

## 📚 參考新文檔

- [Target User Config 實作報告](../completion_reports/TARGET_USER_CONFIG_IMPLEMENTATION.md)
- [配置管理更新摘要](../completion_reports/CONFIG_MANAGEMENT_UPDATE_SUMMARY.md)
- [完整清理方案](../COMPLETE_CLEANUP_PLAN.md)
- [舊文件清理報告](../LEGACY_FILES_CLEANUP_2025-10-28.md)

## 🗄️ 其他歸檔位置

### 前端文件
```
knowledge-admin/frontend/src/views/.backup/AudienceConfigView.vue
```

### 後端文件
```
rag-orchestrator/routers/.backup/audience_config.py.backup
```

### 資料庫 Migration
保留在原位置（作為資料庫演進歷史）：
```
database/migrations/40-create-audience-config.sql
database/migrations/36-remove-audience.sql
database/migrations/36-remove-audience-fixed.sql
```

## ⚠️ 注意事項

1. **不要恢復這些文件到主程式碼**
   - 這些文件僅供歷史參考
   - 系統已完全遷移到 Target User Config

2. **保留期限**
   - 建議保留 3-6 個月
   - 如確認無需參考，可於 2025-04-28 後刪除

3. **參考用途**
   - 了解舊系統設計思路
   - 遷移過程參考
   - 問題排查（如有遺留問題）

---

**歸檔日期**: 2025-10-28
**執行者**: Claude Code
**狀態**: ✅ 已完成
