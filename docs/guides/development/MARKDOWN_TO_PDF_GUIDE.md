# 📄 Markdown 轉 PDF 指南

## 方法 1：VS Code + Markdown PDF 擴充套件（最推薦）⭐

### 安裝步驟：
1. 開啟 VS Code
2. 安裝擴充套件：
   - 搜尋並安裝 `Markdown PDF` (by yzane)
   - 或搜尋並安裝 `Markdown Preview Enhanced` (by Yiyi Wang)

### 使用 Markdown PDF：
```bash
1. 開啟 COMPLETE_CONVERSATION_ARCHITECTURE.md
2. 按 Cmd+Shift+P (Mac) 或 Ctrl+Shift+P (Windows)
3. 輸入 "Markdown PDF: Export (pdf)"
4. 選擇輸出位置
```

### 使用 Markdown Preview Enhanced：
```bash
1. 開啟 COMPLETE_CONVERSATION_ARCHITECTURE.md
2. 按 Cmd+K V (Mac) 開啟預覽
3. 在預覽視窗右鍵 → "Chrome (Puppeteer) → PDF"
```

---

## 方法 2：使用 Pandoc + mermaid-filter（專業方法）

### 安裝：
```bash
# macOS
brew install pandoc
brew install mactex  # 或 brew install basictex
npm install -g mermaid-filter

# 檢查安裝
pandoc --version
mermaid-filter --version
```

### 轉換命令：
```bash
cd docs/architecture   # 從 repo 根目錄起算

# 基本轉換
pandoc COMPLETE_CONVERSATION_ARCHITECTURE.md \
  -o COMPLETE_CONVERSATION_ARCHITECTURE.pdf \
  --pdf-engine=xelatex \
  -F mermaid-filter

# 美化版本（含中文支援）
pandoc COMPLETE_CONVERSATION_ARCHITECTURE.md \
  -o COMPLETE_CONVERSATION_ARCHITECTURE.pdf \
  --pdf-engine=xelatex \
  -F mermaid-filter \
  -V geometry:margin=1in \
  -V mainfont="PingFang SC" \
  -V monofont="Monaco" \
  --highlight-style=tango
```

---

## 方法 3：使用 mdpdf（簡單命令行）

### 安裝：
```bash
npm install -g mdpdf
```

### 使用：
```bash
cd docs/architecture   # 從 repo 根目錄起算
mdpdf COMPLETE_CONVERSATION_ARCHITECTURE.md
```

---

## 方法 4：使用 Typora（視覺化編輯器）

### 步驟：
1. 下載 Typora：https://typora.io/
2. 開啟 COMPLETE_CONVERSATION_ARCHITECTURE.md
3. 檔案 → 匯出 → PDF

### 優點：
- 即時預覽
- 支援 Mermaid
- 可自訂樣式

---

## 方法 5：線上工具（免安裝）

### 選項 A：HackMD
1. 訪問 https://hackmd.io/
2. 貼上 Markdown 內容
3. 點擊 "..." → "Download" → "PDF"

### 選項 B：Markdown to PDF
1. 訪問 https://md2pdf.netlify.app/
2. 貼上內容
3. 點擊 "Download PDF"

### 選項 C：GitHub/GitLab
1. 將文件推送到 GitHub/GitLab
2. 在瀏覽器中查看渲染後的文件
3. 按 Cmd+P (Mac) 或 Ctrl+P (Windows)
4. 選擇"儲存為 PDF"

---

## 方法 6：使用 Chrome/Edge 瀏覽器打印

### 步驟：
```bash
# 1. 先用 markdown 預覽工具生成 HTML
npm install -g markdown-it-cli
npm install -g @mermaid-js/mermaid-cli

# 2. 轉換為 HTML
markdown-it COMPLETE_CONVERSATION_ARCHITECTURE.md > output.html

# 3. 用瀏覽器開啟 HTML
open output.html  # macOS
start output.html # Windows

# 4. Cmd+P 打印為 PDF
```

---

## 方法 7：使用 Docker（環境獨立）

### 使用 pandoc docker：
```bash
docker run --rm \
  -v $(pwd):/data \
  pandoc/latex:latest \
  COMPLETE_CONVERSATION_ARCHITECTURE.md \
  -o COMPLETE_CONVERSATION_ARCHITECTURE.pdf \
  --pdf-engine=xelatex
```

---

## 🎨 樣式優化建議

如果要讓 PDF 更美觀，可以創建自訂 CSS：

### custom.css
```css
body {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei";
  line-height: 1.6;
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  color: #2c3e50;
  border-bottom: 3px solid #3498db;
  padding-bottom: 10px;
}

h2 {
  color: #34495e;
  margin-top: 30px;
}

code {
  background: #f4f4f4;
  padding: 2px 5px;
  border-radius: 3px;
}

pre {
  background: #282c34;
  color: #abb2bf;
  padding: 15px;
  border-radius: 5px;
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  width: 100%;
  margin: 20px 0;
}

table th {
  background: #3498db;
  color: white;
  padding: 10px;
  text-align: left;
}

table td {
  border: 1px solid #ddd;
  padding: 10px;
}

.mermaid {
  text-align: center;
  margin: 20px 0;
}

/* 頁面設定 */
@page {
  size: A4;
  margin: 2cm;
}

/* 分頁控制 */
h1 { page-break-before: always; }
h2 { page-break-after: avoid; }
```

### 使用自訂樣式：
```bash
# VS Code Markdown PDF 設定
"markdown-pdf.styles": [
  "./custom.css"
]

# Pandoc 使用
pandoc COMPLETE_CONVERSATION_ARCHITECTURE.md \
  -o output.pdf \
  --css=custom.css \
  --self-contained
```

---

## 🚀 快速開始（推薦）

### 最簡單的方法（3 分鐘）：
```bash
# 1. 安裝 VS Code 擴充套件
code --install-extension yzane.markdown-pdf

# 2. 開啟檔案
code docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md

# 3. 按 Cmd+Shift+P → 輸入 "export pdf" → Enter
```

### 最專業的方法（10 分鐘）：
```bash
# 1. 安裝工具
brew install pandoc
brew install mactex
npm install -g mermaid-filter

# 2. 轉換
cd docs/architecture   # 從 repo 根目錄起算
pandoc COMPLETE_CONVERSATION_ARCHITECTURE.md \
  -o COMPLETE_CONVERSATION_ARCHITECTURE.pdf \
  --pdf-engine=xelatex \
  -F mermaid-filter \
  -V mainfont="PingFang SC"
```

---

## ⚠️ 常見問題

### Q1: Mermaid 圖表沒有顯示
**解決**：確保安裝了 mermaid-filter 或使用支援 Mermaid 的工具

### Q2: 中文亂碼
**解決**：
- Pandoc：使用 `--pdf-engine=xelatex` 和 `-V mainfont="PingFang SC"`
- VS Code：在設定中指定字體

### Q3: 圖表太大被截斷
**解決**：
- 調整頁面大小：`-V geometry:papersize=a3paper`
- 或橫向打印：`-V geometry:landscape`

### Q4: 樣式不美觀
**解決**：使用自訂 CSS 或選擇有主題的工具（如 Typora）

---

## 📊 各方法比較

| 方法 | 難度 | 速度 | 效果 | 支援 Mermaid | 適合場景 |
|------|------|------|------|-------------|----------|
| VS Code 擴充 | ⭐ | 快 | 好 | ✅ | 日常使用 |
| Pandoc | ⭐⭐⭐ | 中 | 極佳 | ✅ | 專業文檔 |
| Typora | ⭐ | 快 | 好 | ✅ | 視覺編輯 |
| 線上工具 | ⭐ | 快 | 中 | 部分 | 臨時使用 |
| Chrome 打印 | ⭐ | 快 | 中 | ✅ | 快速輸出 |

選擇最適合您的方法即可！