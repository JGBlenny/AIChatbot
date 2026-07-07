# 📁 根目錄清理計劃

**現狀**：根目錄有 19 個文件，過於混亂
**目標**：保持根目錄簡潔，只保留核心配置文件

---

## 📊 現有文件分類

### ✅ 保留在根目錄（7個）

**原因**：核心配置文件，慣例放在根目錄

```
.env                      # 環境變數（敏感）
.env.example              # 環境變數範例
.gitignore                # Git 忽略規則
docker-compose.yml        # Docker 配置（主要）
docker-compose.prod.yml   # Docker 配置（生產）
README.md                 # 項目說明
CHANGELOG.md              # 變更日誌
```

---

### 📚 移至 docs/（9個）

**原因**：技術文檔，應集中管理

```
當前位置 → 新位置

DOCUMENTATION_INDEX.md              → docs/README.md ⭐
FINAL_IMPLEMENTATION_2026-01-13.md  → docs/implementation/FINAL_2026-01-13.md
IMPLEMENTATION_SUMMARY.md           → docs/implementation/SUMMARY.md
RETRIEVAL_LOGIC_COMPLETE_ANALYSIS.md → docs/analysis/retrieval_logic_complete.md
RETRIEVAL_PHILOSOPHY_ANALYSIS.md    → docs/analysis/retrieval_philosophy.md
VERIFICATION_REPORT_2026-01-13.md   → docs/verification/report_2026-01-13.md
CLEANUP_REPORT_2026-01-13.md        → docs/maintenance/cleanup_2026-01-13.md
DEPLOY_STEPS_2026-01-13.md          → docs/deployment/steps_2026-01-13.md
HOTFIX_STEPS_2026-01-13.md          → docs/deployment/hotfix_2026-01-13.md
```

---

### 🔧 移至 scripts/（2個）

**原因**：實用腳本，應集中管理

```
當前位置 → 新位置

test_retrieval_logic_validation.sh  → scripts/test_retrieval_validation.sh
cleanup_outdated_docs.sh            → scripts/cleanup_docs.sh
```

---

### 💾 移至 sql/hotfixes/（1個）

**原因**：SQL 熱修復腳本，應單獨管理

```
當前位置 → 新位置

HOTFIX_knowledge_1262_classification.sql → sql/hotfixes/2026-01-13_knowledge_1262.sql
```

---

## 📁 整理後的目錄結構

```
AIChatbot/
├─ 📄 配置文件（7個）
│  ├─ .env
│  ├─ .env.example
│  ├─ .gitignore
│  ├─ docker-compose.yml
│  ├─ docker-compose.prod.yml
│  ├─ README.md
│  └─ CHANGELOG.md
│
├─ 📚 docs/
│  ├─ README.md ⭐ (原 DOCUMENTATION_INDEX.md)
│  │
│  ├─ implementation/
│  │  ├─ FINAL_2026-01-13.md
│  │  └─ SUMMARY.md
│  │
│  ├─ analysis/
│  │  ├─ retrieval_logic_complete.md
│  │  └─ retrieval_philosophy.md
│  │
│  ├─ verification/
│  │  └─ report_2026-01-13.md
│  │
│  ├─ deployment/
│  │  ├─ steps_2026-01-13.md
│  │  └─ hotfix_2026-01-13.md
│  │
│  ├─ maintenance/
│  │  └─ cleanup_2026-01-13.md
│  │
│  └─ archive/
│     └─ 2026-01-13/
│
├─ 🔧 scripts/
│  ├─ test_retrieval_validation.sh
│  └─ cleanup_docs.sh
│
└─ 💾 sql/
   └─ hotfixes/
      └─ 2026-01-13_knowledge_1262.sql
```

---

## 📊 清理效果

| 指標 | 清理前 | 清理後 | 改善 |
|------|--------|--------|------|
| **根目錄文件數** | 19 個 | 7 個 | -63% |
| **技術文檔** | 混雜 | 集中在 docs/ | ✅ |
| **腳本文件** | 混雜 | 集中在 scripts/ | ✅ |
| **可維護性** | 低 | 高 | ⬆️ |
| **查找文件** | 困難 | 簡單 | ✅ |

---

## 🎯 整理優勢

### 1. 根目錄簡潔

**清理前**：19 個文件，難以找到核心配置
```bash
$ ls -1
.env
.env.example
.gitignore
CHANGELOG.md
CLEANUP_REPORT_2026-01-13.md  # ❌ 混亂
DEPLOY_STEPS_2026-01-13.md     # ❌ 混亂
...（太多）
```

**清理後**：7 個文件，一目了然
```bash
$ ls -1
.env
.env.example
.gitignore
CHANGELOG.md
README.md
docker-compose.yml
docker-compose.prod.yml
```

### 2. 文檔分類清晰

**docs/** 目錄結構：
- `implementation/` - 實施文檔
- `analysis/` - 分析文檔
- `verification/` - 驗證文檔
- `deployment/` - 部署文檔
- `maintenance/` - 維護文檔
- `archive/` - 歸檔文檔

### 3. 符合最佳實踐

**行業慣例**：
- ✅ 根目錄只放核心配置
- ✅ 文檔集中在 docs/
- ✅ 腳本集中在 scripts/
- ✅ SQL 集中在 sql/

**參考項目**：
- Rails: 根目錄只有 Gemfile, README 等
- Django: 根目錄只有 manage.py, requirements.txt 等
- React: 根目錄只有 package.json, README 等

---

## 🔄 執行步驟

### 選項 A：自動執行（推薦）

```bash
# 執行自動整理腳本
bash scripts/organize_root_directory.sh
```

### 選項 B：手動執行

```bash
# 1. 創建目錄結構
mkdir -p docs/{implementation,analysis,verification,deployment,maintenance}
mkdir -p scripts
mkdir -p sql/hotfixes

# 2. 移動文檔
mv DOCUMENTATION_INDEX.md docs/README.md
mv FINAL_IMPLEMENTATION_2026-01-13.md docs/implementation/FINAL_2026-01-13.md
mv IMPLEMENTATION_SUMMARY.md docs/implementation/SUMMARY.md
mv RETRIEVAL_LOGIC_COMPLETE_ANALYSIS.md docs/analysis/retrieval_logic_complete.md
mv RETRIEVAL_PHILOSOPHY_ANALYSIS.md docs/analysis/retrieval_philosophy.md
mv VERIFICATION_REPORT_2026-01-13.md docs/verification/report_2026-01-13.md
mv CLEANUP_REPORT_2026-01-13.md docs/maintenance/cleanup_2026-01-13.md
mv DEPLOY_STEPS_2026-01-13.md docs/deployment/steps_2026-01-13.md
mv HOTFIX_STEPS_2026-01-13.md docs/deployment/hotfix_2026-01-13.md

# 3. 移動腳本
mv test_retrieval_logic_validation.sh scripts/test_retrieval_validation.sh
mv cleanup_outdated_docs.sh scripts/cleanup_docs.sh

# 4. 移動 SQL
mv HOTFIX_knowledge_1262_classification.sql sql/hotfixes/2026-01-13_knowledge_1262.sql

# 5. 更新權限
chmod +x scripts/*.sh

# 6. Git 提交
git add -A
git commit -m "refactor: 整理根目錄，建立清晰的項目結構"
```

---

## 📝 注意事項

### 需要更新的引用

整理後需要更新以下文件中的路徑引用：

1. **README.md**
   - 更新文檔鏈接指向 docs/

2. **docs/README.md**（原 DOCUMENTATION_INDEX.md）
   - 更新所有文檔路徑

3. **其他文檔內的相對鏈接**
   - 更新 markdown 文件間的鏈接

4. **CI/CD 配置**（如果有）
   - 更新腳本路徑

---

## ✅ 驗證清單

整理完成後檢查：

- [ ] 根目錄只有 7 個文件
- [ ] docs/ 目錄結構正確
- [ ] scripts/ 腳本可執行
- [ ] sql/ 文件存在
- [ ] 所有文檔鏈接正常
- [ ] Git 提交成功
- [ ] 測試腳本可運行

---

## 🚀 執行建議

**現在執行？**
- ✅ 推薦：代碼已穩定，文檔已完善
- ✅ 好處：立即改善項目結構
- ⚠️ 注意：需要更新文檔內的路徑引用

**稍後執行？**
- 可以，但會持續混亂
- 建議在下次重大更新前執行

---

**準備好執行整理了嗎？**
