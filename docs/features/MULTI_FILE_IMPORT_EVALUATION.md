# 📊 多筆匯入功能評估報告

**日期**: 2025-11-18
**需求**: http://localhost:8087/knowledge-import 支援多檔案上傳

---

## 🔍 現況分析

### 當前實現

**前端** (`KnowledgeImportView.vue`, 873 行):
```vue
<input
  type="file"
  accept=".txt,.xlsx,.xls,.csv,.json"
  @change="handleFileSelect"
/>
```
- ❌ 無 `multiple` 屬性，僅支援單檔案
- ✅ 4 步驟流程：上傳 → 預覽 → 處理 → 完成
- ✅ 進度追蹤（處理訊息數、embedding 生成數）
- ✅ 即時狀態更新（polling job status）

**後端** (`knowledge_import.py`):
```python
async def upload_knowledge_file(
    file: UploadFile = File(...),  # 單一檔案
    background_tasks: BackgroundTasks,
    ...
):
```
- ✅ 單檔案處理架構
- ✅ 背景任務處理（不阻塞 API）
- ✅ Job ID 追蹤系統
- ✅ 檔案大小限制：50MB
- ✅ 支援格式：Excel, CSV, TXT, JSON

---

## 💡 三種設計方案

### 方案 1: 多檔案並行處理 ⚡

**描述**: 一次上傳多個檔案，同時處理

**前端設計**:
```vue
<input type="file" multiple accept=".txt,.xlsx,.xls,.csv,.json" />
```

**UI 流程**:
```
上傳多檔案 → 批次預覽（檔案列表） → 確認匯入 → 並行處理（多進度條） → 完成總覽
```

**後端設計**:
```python
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks,
    ...
):
    job_ids = []
    for file in files:
        job_id = str(uuid.uuid4())
        background_tasks.add_task(process_file, file, job_id)
        job_ids.append(job_id)
    return {"job_ids": job_ids}
```

**優點**:
- ✅ 用戶體驗最佳：一次性操作
- ✅ 總時間最短（並行處理）
- ✅ 適合大量檔案（如 10+ 個）

**缺點**:
- ❌ UI 複雜度高（需要多進度條）
- ❌ 資源消耗大（同時多個 OpenAI API 請求）
- ❌ 錯誤處理複雜（部分成功、部分失敗）
- ❌ 前端代碼量增加 ~300-400 行

**實現工時**: 8-12 小時

---

### 方案 2: 批次佇列處理 🔄

**描述**: 一次上傳多個檔案，依序處理

**前端設計**:
```vue
<input type="file" multiple accept=".txt,.xlsx,.xls,.csv,.json" />
```

**UI 流程**:
```
上傳多檔案 → 檔案佇列（列表顯示） → 依序處理（單一進度條，顯示當前檔案） → 完成總覽
```

**後端設計**:
```python
# 方式 A: 單一 job，序列處理
async def process_batch(files: List[UploadFile], batch_id: str):
    for i, file in enumerate(files):
        print(f"處理檔案 {i+1}/{len(files)}")
        await process_single_file(file)

# 方式 B: Redis 任務佇列
# 使用 Celery 或 RQ 管理佇列
```

**優點**:
- ✅ 資源控制好（一次一個 OpenAI 請求）
- ✅ 進度清晰（當前處理第幾個）
- ✅ 錯誤處理簡單（逐個處理，逐個報錯）
- ✅ 可暫停/取消

**缺點**:
- ❌ 總時間較長（序列處理）
- ❌ 仍需改動前端 UI（佇列管理）
- ❌ 後端需要佇列機制（如果用 Redis）

**實現工時**: 10-16 小時

---

### 方案 3: 簡化版 - 檔案管理器 📋

**描述**: 允許添加多個檔案到列表，但保持單檔案處理流程

**前端設計**:
```vue
<!-- 檔案列表 -->
<div class="file-manager">
  <div v-for="file in uploadedFiles" class="file-item">
    <span>{{ file.name }}</span>
    <button @click="processFile(file)">處理</button>
    <span class="status">{{ file.status }}</span>
  </div>
  <button @click="selectFiles">+ 添加檔案</button>
</div>
```

**UI 流程**:
```
添加多個檔案到列表 → 點擊單個「處理」→ 單檔案流程（不變） → 返回列表 → 繼續處理下一個
```

**後端設計**:
- ❌ 不需要修改（保持單檔案 API）

**優點**:
- ✅ 實現最簡單（前端 ~150 行）
- ✅ 後端完全不變
- ✅ UI 清晰直觀
- ✅ 錯誤處理簡單

**缺點**:
- ❌ 仍需逐個點擊「處理」（半自動）
- ❌ 總時間最長（手動操作）
- ❌ 適合少量檔案（3-5 個）

**實現工時**: 3-5 小時

---

## 📊 方案比較表

| 特性 | 方案 1: 並行處理 | 方案 2: 佇列處理 | 方案 3: 檔案管理器 |
|------|-----------------|-----------------|-------------------|
| **實現複雜度** | ⭐⭐⭐⭐⭐ 高 | ⭐⭐⭐⭐ 中高 | ⭐⭐ 低 |
| **開發工時** | 8-12 小時 | 10-16 小時 | 3-5 小時 |
| **用戶體驗** | ⭐⭐⭐⭐⭐ 最佳 | ⭐⭐⭐⭐ 良好 | ⭐⭐⭐ 一般 |
| **總處理時間** | ⭐⭐⭐⭐⭐ 最快 | ⭐⭐⭐ 中等 | ⭐⭐ 較慢 |
| **資源消耗** | ⭐⭐ 高 | ⭐⭐⭐⭐ 低 | ⭐⭐⭐⭐⭐ 最低 |
| **錯誤處理** | ⭐⭐ 複雜 | ⭐⭐⭐⭐ 簡單 | ⭐⭐⭐⭐⭐ 最簡單 |
| **適合檔案數** | 10+ | 5-20 | 2-5 |
| **後端改動** | 新增 API | 新增 API + 佇列 | 無需改動 ✅ |
| **前端改動** | ~400 行 | ~350 行 | ~150 行 |

---

## 🎯 建議與決策

### 使用場景分析

**如果您的場景是**:
- 📁 **偶爾需要匯入 2-5 個檔案** → **推薦方案 3**（快速實現，夠用）
- 📁 **經常需要匯入 5-10 個檔案** → **推薦方案 2**（平衡性能和體驗）
- 📁 **大批量匯入 10+ 個檔案** → **推薦方案 1**（體驗最佳）

### 我的推薦：方案 3（檔案管理器）

**理由**:
1. ✅ **快速上線**：3-5 小時即可完成
2. ✅ **後端零改動**：不影響現有穩定架構
3. ✅ **風險低**：改動小，測試簡單
4. ✅ **可擴展**：未來可升級為方案 2 或方案 1
5. ✅ **符合實際需求**：大多數情況下不會一次上傳 10+ 個檔案

### 如果選擇方案 3，實現細節

**前端改動**:
```vue
<template>
  <div class="file-queue">
    <!-- 檔案列表 -->
    <div class="queue-header">
      <h3>📋 檔案佇列 ({{ files.length }})</h3>
      <button @click="addFiles">+ 添加檔案</button>
    </div>

    <div v-for="(file, index) in files" :key="index" class="file-row">
      <span class="file-name">{{ file.name }}</span>
      <span class="file-size">{{ formatSize(file.size) }}</span>

      <!-- 狀態 -->
      <span v-if="file.status === 'pending'" class="badge badge-gray">待處理</span>
      <span v-if="file.status === 'processing'" class="badge badge-blue">處理中...</span>
      <span v-if="file.status === 'completed'" class="badge badge-green">✅ 完成</span>
      <span v-if="file.status === 'error'" class="badge badge-red">❌ 失敗</span>

      <!-- 操作按鈕 -->
      <button
        v-if="file.status === 'pending'"
        @click="processFile(file)"
        class="btn-small btn-primary"
      >
        處理
      </button>

      <button @click="removeFile(index)" class="btn-small btn-remove">移除</button>
    </div>

    <!-- 批次操作 -->
    <div class="queue-actions">
      <button @click="processAll" :disabled="processing">處理全部</button>
      <button @click="clearCompleted">清除已完成</button>
    </div>
  </div>
</template>

<script>
data() {
  return {
    files: [],  // 檔案佇列
    processing: false,
  }
},
methods: {
  addFiles() {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.accept = '.txt,.xlsx,.xls,.csv,.json'
    input.onchange = (e) => {
      const newFiles = Array.from(e.target.files).map(f => ({
        file: f,
        name: f.name,
        size: f.size,
        status: 'pending',
        jobId: null,
      }))
      this.files.push(...newFiles)
    }
    input.click()
  },

  async processFile(fileItem) {
    fileItem.status = 'processing'

    // 使用現有的單檔案處理 API
    const formData = new FormData()
    formData.append('file', fileItem.file)
    formData.append('skip_review', this.skipReview)
    formData.append('default_priority', this.enablePriority ? 1 : 0)

    try {
      const res = await axios.post('/api/v1/knowledge-import/upload', formData)
      fileItem.jobId = res.data.job_id

      // 輪詢狀態
      await this.pollJobStatus(fileItem)

      fileItem.status = 'completed'
    } catch (error) {
      fileItem.status = 'error'
      fileItem.error = error.message
    }
  },

  async processAll() {
    this.processing = true
    for (const file of this.files.filter(f => f.status === 'pending')) {
      await this.processFile(file)
    }
    this.processing = false
  },
}
</script>
```

**CSS 估計**:
~50 行（badge 樣式、檔案列表排版）

---

## 🚀 下一步行動

### 如果您決定實現，請回答以下問題：

1. **您通常一次需要匯入幾個檔案？**
   - [ ] 2-3 個（推薦方案 3）
   - [ ] 5-10 個（推薦方案 2）
   - [ ] 10+ 個（推薦方案 1）

2. **是否可以接受逐個點擊「處理」？**
   - [ ] 可以（方案 3 即可）
   - [ ] 不行，需要全自動（方案 1 或 2）

3. **預期的上線時間？**
   - [ ] 3-5 小時內（僅方案 3 可行）
   - [ ] 1-2 天（方案 2 可行）
   - [ ] 3-5 天（方案 1 可行）

4. **是否願意改動後端？**
   - [ ] 否，僅改前端（僅方案 3）
   - [ ] 可以（方案 1, 2, 3 都可）

5. **是否需要進階功能？**
   - [ ] 檔案優先順序調整
   - [ ] 暫停/繼續處理
   - [ ] 處理歷史記錄
   - [ ] 失敗重試機制

---

## 📝 總結

| 方案 | 適合場景 | 開發時間 | 推薦度 |
|------|---------|---------|--------|
| **方案 1: 並行處理** | 大批量、高頻使用 | 8-12h | ⭐⭐⭐ |
| **方案 2: 佇列處理** | 中批量、資源受限 | 10-16h | ⭐⭐⭐⭐ |
| **方案 3: 檔案管理器** | 小批量、偶爾使用 | 3-5h | ⭐⭐⭐⭐⭐ |

**個人推薦**: 先實現**方案 3**，快速滿足需求，未來視使用情況再升級為方案 2。

---

**評估人員**: Claude Code
**評估日期**: 2025-11-18
**文檔版本**: v1.0
