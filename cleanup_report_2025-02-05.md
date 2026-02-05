# 專案清理報告 - 2025-02-05

## 🗑️ 建議刪除的檔案清單

### 1. 臨時和備份檔案
```bash
# 備份檔案
rm /Users/lenny/jgb/AIChatbot/database/init/12-create-ai-knowledge-system.sql.backup
rm /Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/api_endpoints.py.bak
rm -rf /Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/.backup
rm /Users/lenny/jgb/AIChatbot/rag-orchestrator/services/business_scope_utils.py.backup
rm -rf /Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/.backup

# Mac 系統檔案
rm /Users/lenny/jgb/AIChatbot/docs/architecture/.DS_Store
```

### 2. 舊測試檔案（scripts/testing/archive/2026-01-26）
這個資料夾包含 17 個舊測試檔案，建議整個刪除：
```bash
rm -rf /Users/lenny/jgb/AIChatbot/scripts/testing/archive/2026-01-26
```

包含的檔案：
- test_specific_question.py
- test_threshold_evaluation.py
- test_sop_coverage.py
- test_fix_verification.py
- test_sop_retrieval.py
- create_test_sop_scenarios.py
- test_single_question.py
- cleanup_test_forms.py
- create_real_scenario_test.py
- test_new_sop_embedding.py
- create_test_forms.py
- cleanup_test_sop.py
- test_false_positive.py

### 3. docs/archive 中的過時文件（選擇性）
以下是 2025-10 月的舊文件，如果不再需要可以刪除：
```bash
# 2025年10月的清理報告（已過時）
rm /Users/lenny/jgb/AIChatbot/docs/archive/CLEANUP_EXECUTION_REPORT_2025-10-28.md
rm /Users/lenny/jgb/AIChatbot/docs/archive/CLEANUP_SUMMARY_2025-10-28.md
rm /Users/lenny/jgb/AIChatbot/docs/archive/COMPLETE_CLEANUP_PLAN.md
rm /Users/lenny/jgb/AIChatbot/docs/archive/LEGACY_FILES_CLEANUP_2025-10-28.md
```

### 4. 重複或冗餘的文件
```bash
# 檢查是否有重複的 form_retry 文件
ls /Users/lenny/jgb/AIChatbot/docs/fixes/form-retry-limit/
# 可能有些檔案內容重複，需要手動檢查
```

## 📁 建議保留但整理的檔案

### docs 資料夾結構優化建議
```
docs/
├── fixes/           # 問題修復（保留）
├── features/        # 新功能（保留）
├── implementation/  # 實作細節（保留）
├── guides/          # 使用指南（保留）
├── testing/         # 測試相關（保留）
├── architecture/    # 架構設計（保留）
└── archive/         # 歸檔
    └── 2025/        # 按年份整理
        └── 10/      # 按月份整理
```

## 🧹 清理指令（一鍵執行）

### 安全清理（只刪除明確的垃圾檔案）
```bash
#!/bin/bash
# 儲存為 cleanup.sh

echo "開始清理專案..."

# 1. 刪除備份檔案
find . -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*.swp" | xargs rm -f

# 2. 刪除 Mac 系統檔案
find . -name ".DS_Store" | xargs rm -f

# 3. 刪除舊測試檔案
rm -rf scripts/testing/archive/2026-01-26

echo "清理完成！"
```

## 📊 清理統計

- **備份檔案**: 5 個
- **測試檔案**: 17 個
- **系統檔案**: 1 個
- **預計釋放空間**: 約 2-3 MB

## ⚠️ 注意事項

1. **執行前請確認**: 確保沒有正在進行的開發工作需要這些檔案
2. **建議備份**: 如果不確定，可以先移到 `/tmp` 而不是直接刪除
3. **Git 狀態**: 確認 git 狀態是否乾淨，避免誤刪未提交的更改

## 🔄 建議的清理流程

1. **先備份重要檔案**
   ```bash
   tar -czf backup_$(date +%Y%m%d).tar.gz docs/archive scripts/testing/archive
   ```

2. **執行清理**
   ```bash
   # 刪除備份和臨時檔案
   find . -name "*.bak" -o -name "*.backup" -o -name ".DS_Store" | xargs rm -f

   # 刪除舊測試
   rm -rf scripts/testing/archive/2026-01-26
   ```

3. **確認 Git 狀態**
   ```bash
   git status
   git add -A
   git commit -m "chore: 清理專案中的臨時檔案和舊測試"
   ```

## 📝 後續建議

1. 建立 `.gitignore` 規則防止這些檔案再次進入版控
2. 定期（每月）執行清理
3. 建立文件歸檔政策（超過 3 個月的文件自動歸檔）