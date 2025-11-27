/**
 * 集中管理所有頁面的說明文字
 *
 * 優點：
 * 1. 統一更新：只需修改這個文件，所有頁面自動同步
 * 2. 易於維護：說明文字集中管理，Git 可追蹤變更歷史
 * 3. 版本追蹤：每個說明可標記 lastUpdated 日期
 *
 * 最後更新：2025-10-28
 */

export default {
  /**
   * 意圖管理
   */
  intents: {
    title: "💡 什麼是意圖？意圖系統的作用說明",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "🎯",
        title: "核心功能",
        content: "<strong>意圖（Intent）</strong> 是用戶問題的語義分類，系統會自動識別用戶問題屬於哪個意圖，並據此優化答案。",
        items: [
          "<strong>自動分類</strong>：使用 LLM 或關鍵字匹配識別用戶意圖",
          "<strong>知識關聯</strong>：每筆知識可關聯多個意圖（primary/secondary）",
          "<strong>SOP 關聯</strong>：SOP 項目可指定相關意圖"
        ]
      },
      {
        icon: "🚀",
        title: "檢索增強（Intent Boost）",
        important: true,
        content: "最重要的功能！提升相關知識的排序優先級：",
        items: [
          '<strong>主要意圖</strong>：<span class="badge boost-primary">1.5x</span> 相似度加成',
          '<strong>次要意圖</strong>：<span class="badge boost-secondary">1.2x</span> 相似度加成',
          '<strong>其他意圖</strong>：<span class="badge boost-normal">1.0x</span> 無加成'
        ],
        example: `<strong>範例：</strong>問題「租金怎麼繳？」
<br>→ 系統識別為「帳務查詢」意圖
<br>→ 帶有「帳務查詢」標籤的知識會優先顯示
<br>→ 原始相似度 0.7 × 1.5 = <strong>1.05</strong> （加成後）`
      },
      {
        icon: "📋",
        title: "Type 欄位的作用",
        content: "用於調整 LLM 答案生成的風格和提示詞：",
        table: {
          rows: [
            [
              { badge: true, text: "knowledge", badgeClass: "type-knowledge" },
              "<strong>知識查詢</strong>",
              "提供完整說明、步驟和注意事項<br><small>例如：「退租流程」「合約規定」</small>"
            ],
            [
              { badge: true, text: "data_query", badgeClass: "type-data_query" },
              "<strong>資料查詢</strong>",
              "說明如何查詢具體資料，通常需要 API<br><small>例如：「租約查詢」「帳務查詢」</small>"
            ],
            [
              { badge: true, text: "action", badgeClass: "type-action" },
              "<strong>操作執行</strong>",
              "提供具體、可執行的操作步驟<br><small>例如：「設備報修」「申請退租」</small>"
            ],
            [
              { badge: true, text: "hybrid", badgeClass: "type-hybrid" },
              "<strong>混合型</strong>",
              "結合多種類型的問題<br><small>例如：「怎麼查租金並繳費」</small>"
            ]
          ]
        },
        note: "<strong>💡 注意：</strong>type 主要影響 LLM 提示詞和答案模板，不影響檢索邏輯。<br>檢索增強只看 intent_id，不看 type。"
      },
      {
        icon: "⚙️",
        title: "其他重要欄位",
        items: [
          "<strong>關鍵字（keywords）</strong>：用於關鍵字匹配分類，輔助 LLM 判斷",
          "<strong>信心度閾值（confidence_threshold）</strong>：低於此值視為不確定",
          "<strong>優先級（priority）</strong>：多個意圖匹配時的優先順序",
          "<strong>API 設定（api_required）</strong>：是否需要調用外部 API",
          "<strong>使用次數（usage_count）</strong>：統計此意圖被觸發的次數"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>新增意圖時</strong>，選擇最貼切的 type，幫助 LLM 生成更合適的答案",
        "✅ <strong>設定關鍵字</strong>，提高自動分類的準確度",
        "✅ <strong>關聯知識</strong>，在「知識管理」頁面為知識添加意圖標籤",
        "⚠️ <strong>不要過度細分</strong>，過多意圖會降低匹配準確度",
        "⚠️ <strong>定期檢視使用次數</strong>，刪除不常用的意圖"
      ]
    }
  },

  /**
   * 知識庫管理
   */
  knowledge: {
    title: "💡 什麼是知識庫？知識管理系統說明",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "📚",
        title: "核心功能",
        content: "<strong>知識庫（Knowledge Base）</strong> 是 AI 回答的資料來源，包含問題、答案、意圖標籤等資訊。",
        items: [
          "<strong>問題答案配對</strong>：每筆知識包含問題摘要和標準答案",
          "<strong>向量檢索</strong>：使用 Embedding 進行語義相似度搜尋",
          "<strong>意圖關聯</strong>：可為知識添加主要/次要意圖標籤，提升檢索準確度",
          "<strong>業態過濾</strong>：可指定知識適用的業態類型（如：包租、代管等）",
          "<strong>目標用戶</strong>：可指定知識的目標受眾（租客、房東、物業等）"
        ]
      },
      {
        icon: "🎯",
        title: "作用域（Scope）",
        important: true,
        content: "知識庫支援三種作用域，決定知識的可見範圍：",
        table: {
          rows: [
            ["<strong>global</strong>", "全域知識", "所有業者共用，統一標準答案"],
            ["<strong>vendor</strong>", "業者專屬", "特定業者的獨有知識"],
            ["<strong>customized</strong>", "客製化知識", "針對特定業者的個別調整"]
          ]
        },
        note: "<strong>🔍 檢索優先級：</strong>customized (1000) > vendor (500) > global (100)<br>系統會優先返回客製化知識，其次是業者專屬，最後才是全域知識。"
      },
      {
        icon: "🔧",
        title: "模板變數功能",
        content: "支援動態模板，根據業者參數自動替換內容：",
        example: `<strong>模板範例：</strong><br>
原始答案：「租金繳費日為每月 <strong>{{payment_day}}</strong> 號」<br>
→ 業者 A 配置 payment_day=5<br>
→ 實際輸出：「租金繳費日為每月 <strong>5</strong> 號」`
      },
      {
        icon: "🎬",
        title: "影片支援",
        content: "知識可以附帶教學影片，提升使用者體驗：",
        items: [
          "支援上傳至 AWS S3 雲端儲存",
          "自動記錄影片時長、檔案大小、格式",
          "前端支援線上播放"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>新增知識時</strong>，務必關聯相關意圖，提升檢索準確度",
        "✅ <strong>使用模板功能</strong>，減少重複維護相似內容",
        "✅ <strong>設定業態類型</strong>，確保知識只顯示給適合的用戶",
        "✅ <strong>定期審查</strong>，更新過時的知識內容",
        "⚠️ <strong>避免過度客製化</strong>，優先使用全域知識 + 模板變數"
      ]
    }
  },

  /**
   * 目標用戶配置
   */
  targetUsers: {
    title: "💡 什麼是目標用戶配置？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "👥",
        title: "核心功能",
        content: "<strong>目標用戶（Target User）</strong> 用於區分不同角色的用戶，確保他們只看到相關的知識。",
        items: [
          "<strong>角色分類</strong>：租客、房東、物業管理師、系統管理員等",
          "<strong>知識過濾</strong>：根據用戶角色自動過濾知識內容",
          "<strong>個性化體驗</strong>：不同角色看到不同的答案風格"
        ]
      },
      {
        icon: "🎯",
        title: "常見角色",
        table: {
          headers: ["角色代碼", "中文名稱", "說明"],
          rows: [
            ["tenant", "租客", "B2C 終端用戶，租屋的承租人"],
            ["landlord", "房東", "B2C 終端用戶，房屋的出租人"],
            ["property_manager", "物業管理師", "B2B 用戶，管理物業的專業人員"],
            ["system_admin", "系統管理員", "B2B 用戶，系統後台管理者"],
            ["staff", "業者員工", "B2B 用戶，包租代管公司員工"]
          ]
        }
      },
      {
        icon: "🔍",
        title: "運作機制",
        content: "當用戶提問時，系統會：",
        items: [
          "1️⃣ 識別用戶角色（從 user_role 參數）",
          "2️⃣ 過濾知識庫，只顯示標記為該角色的知識",
          "3️⃣ 如果知識未標記目標用戶（NULL），則所有角色都可見"
        ],
        note: "<strong>💡 提示：</strong>通用知識不需要設定目標用戶，保持 NULL 即可讓所有角色共用。"
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>新增角色時</strong>，使用英文小寫加底線命名（如：property_manager）",
        "✅ <strong>標記知識時</strong>，思考該知識是否只適用特定角色",
        "✅ <strong>保持彈性</strong>，大部分知識應該是通用的（不設定目標用戶）",
        "⚠️ <strong>避免過度細分</strong>，角色太多會增加維護複雜度"
      ]
    }
  },

  /**
   * 業態類型配置
   */
  businessTypes: {
    title: "💡 什麼是業態類型配置？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "🏢",
        title: "核心功能",
        content: "<strong>業態類型（Business Type）</strong> 用於區分不同經營模式的業者，確保知識內容符合業務特性。",
        items: [
          "<strong>業務分類</strong>：包租、代管、系統商等不同經營模式",
          "<strong>知識過濾</strong>：根據業者的業態類型自動過濾知識",
          "<strong>多業態支援</strong>：單一業者可同時具有多種業態"
        ]
      },
      {
        icon: "📋",
        title: "常見業態類型",
        table: {
          headers: ["代碼", "名稱", "說明"],
          rows: [
            ["sublease", "包租業", "向房東承租後，再轉租給租客"],
            ["property_management", "代管業", "受房東委託管理房屋"],
            ["system_provider", "系統商", "提供系統服務的 B2B 業者"],
            ["hybrid", "混合型", "同時經營多種業態"]
          ]
        }
      },
      {
        icon: "🎯",
        title: "運作機制",
        important: true,
        content: "當業者的用戶提問時，系統會：",
        items: [
          "1️⃣ 查詢業者的業態類型（可能有多個）",
          "2️⃣ 過濾知識庫，只顯示符合業態的知識",
          "3️⃣ 如果知識未標記業態（NULL），則視為通用知識"
        ],
        note: "<strong>⚠️ 特殊規則：</strong><br>• <strong>B2C 模式</strong>（customer）：允許 NULL（通用知識）<br>• <strong>B2B 模式</strong>（staff）：只允許 system_provider，不允許 NULL"
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>新增業態時</strong>，使用英文小寫加底線命名",
        "✅ <strong>標記知識時</strong>，思考該知識是否只適用特定業態",
        "✅ <strong>通用知識</strong>保持業態為 NULL，讓所有業者共用",
        "⚠️ <strong>B2B 系統商知識</strong>必須明確標記為 system_provider"
      ]
    }
  },

  /**
   * 分類配置
   */
  categories: {
    title: "💡 什麼是分類配置？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "📂",
        title: "核心功能",
        content: "<strong>分類（Category）</strong> 用於組織和管理知識庫，方便後台人員檢視和維護。",
        items: [
          "<strong>知識組織</strong>：將知識按主題分類（如：租金、合約、設備等）",
          "<strong>快速篩選</strong>：在知識管理頁面可按分類篩選",
          "<strong>統計分析</strong>：了解各分類的知識數量和使用頻率"
        ]
      },
      {
        icon: "🔍",
        title: "與意圖的差異",
        table: {
          headers: ["項目", "分類（Category）", "意圖（Intent）"],
          rows: [
            ["用途", "後台管理和組織", "AI 檢索和增強"],
            ["影響範圍", "不影響檢索邏輯", "影響檢索加成（1.5x/1.2x）"],
            ["使用者", "後台管理員", "AI 系統自動使用"],
            ["數量", "建議 10-20 個", "建議 15-30 個"]
          ]
        },
        note: "<strong>💡 建議：</strong>分類用於人工管理，意圖用於 AI 檢索。兩者可以並存，互不影響。"
      },
      {
        icon: "📊",
        title: "建議分類",
        items: [
          "💰 <strong>租金與費用</strong>：租金繳納、水電費、管理費",
          "📄 <strong>合約與流程</strong>：簽約、續約、退租",
          "🔧 <strong>設備與維修</strong>：設備報修、IOT 使用",
          "🏠 <strong>房屋管理</strong>：鑰匙、清潔、檢查",
          "📞 <strong>客服與聯絡</strong>：聯絡方式、服務時間"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>避免過度細分</strong>，保持 10-20 個分類即可",
        "✅ <strong>使用清晰命名</strong>，讓團隊成員一看就懂",
        "✅ <strong>定期整理</strong>，合併使用率低的分類",
        "⚠️ <strong>不要與意圖混淆</strong>，分類是給人看的，意圖是給 AI 用的"
      ]
    }
  },

  /**
   * 業者管理
   */
  vendors: {
    title: "💡 什麼是業者管理？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "🏢",
        title: "核心功能",
        content: "<strong>業者（Vendor）</strong> 是使用本系統的包租代管公司或系統商。",
        items: [
          "<strong>多租戶架構</strong>：每個業者擁有獨立的配置和數據",
          "<strong>參數配置</strong>：可為每個業者設定專屬參數（如繳費日、聯絡方式）",
          "<strong>業態標記</strong>：標記業者的經營模式（包租/代管/系統商）",
          "<strong>知識隔離</strong>：業者之間的客製化知識互不干擾"
        ]
      },
      {
        icon: "⚙️",
        title: "業者參數",
        content: "支援為每個業者設定專屬參數，用於模板變數替換：",
        example: `<strong>範例：</strong><br>
• payment_day: 5（租金繳費日）<br>
• contact_phone: 02-1234-5678<br>
• service_hours: 週一至週五 9:00-18:00<br>
<br>這些參數會自動替換到模板知識中，實現個性化回答。`
      },
      {
        icon: "🎯",
        title: "作用域優先級",
        important: true,
        content: "當業者用戶提問時，知識檢索的優先順序為：",
        items: [
          "1️⃣ <strong>Customized</strong>（客製化）：該業者的個別調整知識",
          "2️⃣ <strong>Vendor</strong>（業者專屬）：該業者的獨有知識",
          "3️⃣ <strong>Global</strong>（全域）：所有業者共用的標準知識"
        ],
        note: "<strong>💡 建議：</strong>優先使用全域知識 + 模板變數，只在必要時才建立業者專屬知識。"
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>新增業者時</strong>，務必設定業態類型",
        "✅ <strong>設定參數</strong>，充分利用模板變數功能",
        "✅ <strong>定期檢視</strong>，刪除不再使用的業者",
        "⚠️ <strong>避免過度客製化</strong>，維護成本會很高"
      ]
    }
  },

  /**
   * 平台 SOP
   */
  platformSOP: {
    title: "💡 什麼是平台 SOP？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "📋",
        title: "核心功能",
        content: "<strong>平台 SOP（Standard Operating Procedure）</strong> 是結構化的標準作業流程，用於處理複雜的多步驟問題。",
        items: [
          "<strong>結構化流程</strong>：將複雜問題拆解為多個步驟",
          "<strong>條件分支</strong>：根據不同情況提供不同處理方式",
          "<strong>意圖關聯</strong>：可關聯到特定意圖，優先返回 SOP",
          "<strong>混合檢索</strong>：SOP 與一般知識可混合檢索"
        ]
      },
      {
        icon: "🎯",
        title: "SOP vs 一般知識",
        table: {
          headers: ["項目", "SOP", "一般知識"],
          rows: [
            ["結構", "多步驟結構化", "單一問答對"],
            ["適用場景", "複雜流程（如退租、報修）", "簡單問答（如聯絡方式）"],
            ["維護複雜度", "較高", "較低"],
            ["用戶體驗", "清晰的步驟指引", "直接的答案"]
          ]
        },
        note: "<strong>💡 建議：</strong>只有需要多步驟指引的場景才使用 SOP，簡單問題用一般知識即可。"
      },
      {
        icon: "🔧",
        title: "SOP 結構",
        content: "每個 SOP 包含以下部分：",
        items: [
          "<strong>標題與描述</strong>：清楚說明 SOP 的用途",
          "<strong>步驟列表</strong>：有序的操作步驟",
          "<strong>注意事項</strong>：重要提醒和警告",
          "<strong>相關意圖</strong>：關聯到相關意圖，提升檢索準確度"
        ]
      },
      {
        icon: "🚀",
        title: "混合檢索模式",
        important: true,
        content: "系統會同時檢索 SOP 和一般知識，根據相似度排序：",
        example: `<strong>範例：</strong>問題「我要退租」<br>
→ 系統同時檢索 SOP 和知識庫<br>
→ 如果「退租 SOP」相似度最高，優先返回<br>
→ 否則返回一般知識的答案`
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>複雜流程用 SOP</strong>：退租、報修、合約續簽等",
        "✅ <strong>簡單問題用知識</strong>：聯絡方式、營業時間等",
        "✅ <strong>關聯意圖</strong>：確保 SOP 能被正確檢索到",
        "✅ <strong>定期更新</strong>：流程變更時及時更新 SOP",
        "⚠️ <strong>避免 SOP 過多</strong>，維護成本會很高"
      ]
    }
  },

  /**
   * 審核中心
   */
  reviewCenter: {
    title: "💡 什麼是審核中心？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "✅",
        title: "核心功能",
        content: "<strong>審核中心（Review Center）</strong> 用於審查和管理待審核的知識或對話記錄。",
        items: [
          "<strong>品質把關</strong>：確保知識內容的準確性和完整性",
          "<strong>批量審核</strong>：支援一次審核多筆資料",
          "<strong>審核歷史</strong>：記錄審核人員和審核時間",
          "<strong>統計分析</strong>：了解審核通過率和常見問題"
        ]
      },
      {
        icon: "🔍",
        title: "審核流程",
        items: [
          "1️⃣ <strong>待審核</strong>：新建或修改的知識進入待審核狀態",
          "2️⃣ <strong>人工審核</strong>：審核人員檢視內容，決定通過或拒絕",
          "3️⃣ <strong>通過</strong>：知識正式上線，可被 AI 檢索",
          "4️⃣ <strong>拒絕</strong>：知識返回修改，或直接刪除"
        ]
      },
      {
        icon: "📊",
        title: "審核重點",
        content: "審核知識時，請注意以下重點：",
        items: [
          "✅ <strong>答案準確性</strong>：確保答案內容正確無誤",
          "✅ <strong>語氣適當</strong>：語氣友善、專業",
          "✅ <strong>意圖標籤</strong>：確認意圖標籤正確",
          "✅ <strong>業態過濾</strong>：確認業態和目標用戶設定正確",
          "⚠️ <strong>避免重複</strong>：檢查是否有類似的知識存在"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>定期審核</strong>：避免待審核清單累積過多",
        "✅ <strong>提供反饋</strong>：拒絕時說明原因，幫助改進",
        "✅ <strong>批量處理</strong>：使用批量審核功能提升效率",
        "⚠️ <strong>謹慎審核</strong>：通過的知識會直接影響 AI 回答品質"
      ]
    }
  },

  /**
   * 知識重新分類
   */
  knowledgeReclassify: {
    title: "💡 什麼是知識重新分類？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "🔄",
        title: "核心功能",
        content: "<strong>知識重新分類（Knowledge Reclassify）</strong> 用於批量更新知識的意圖標籤。",
        items: [
          "<strong>批量更新</strong>：一次性重新分類多筆知識",
          "<strong>AI 自動分類</strong>：使用 LLM 自動識別最適合的意圖",
          "<strong>信心度過濾</strong>：可只重新分類低信心度的知識",
          "<strong>預覽模式</strong>：支援 Dry Run，不實際修改數據"
        ]
      },
      {
        icon: "🎯",
        title: "使用場景",
        items: [
          "<strong>新增意圖</strong>：新增意圖後，重新分類相關知識",
          "<strong>修改意圖</strong>：修改意圖描述或關鍵字後，重新分類",
          "<strong>信心度低</strong>：重新分類信心度 < 0.7 的知識",
          "<strong>定期優化</strong>：定期重新分類，保持意圖標籤準確"
        ]
      },
      {
        icon: "⚙️",
        title: "重新分類模式",
        important: true,
        table: {
          headers: ["模式", "說明", "適用場景"],
          rows: [
            ["none", "不重新分類", "只是更新意圖配置"],
            ["low_confidence", "只重新分類低信心度 (<0.7)", "優化不確定的知識"],
            ["all", "重新分類所有知識", "意圖大幅修改後"]
          ]
        },
        note: "<strong>⚠️ 注意：</strong>「全部」模式會消耗較多 OpenAI API 額度，請謹慎使用。"
      },
      {
        icon: "🔍",
        title: "操作流程",
        items: [
          "1️⃣ <strong>選擇範圍</strong>：選擇要重新分類的知識範圍",
          "2️⃣ <strong>預覽結果</strong>：使用 Dry Run 預覽分類結果",
          "3️⃣ <strong>確認執行</strong>：確認無誤後執行批量更新",
          "4️⃣ <strong>檢視報告</strong>：查看重新分類的統計報告"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>先預覽再執行</strong>：使用 Dry Run 確認結果",
        "✅ <strong>分批處理</strong>：避免一次處理過多知識",
        "✅ <strong>定期執行</strong>：每月執行一次，保持意圖準確",
        "⚠️ <strong>注意 API 額度</strong>：重新分類會消耗 OpenAI API",
        "⚠️ <strong>備份數據</strong>：執行前建議先備份數據"
      ]
    }
  },

  /**
   * 知識匯出
   */
  knowledgeExport: {
    title: "💡 什麼是知識匯出？",
    lastUpdated: "2025-11-22",
    sections: [
      {
        icon: "📤",
        title: "核心功能",
        content: "<strong>知識匯出（Knowledge Export）</strong> 用於將知識庫資料匯出為 Excel 格式，方便備份或人工審閱。",
        items: [
          "<strong>Excel 匯出</strong>：生成格式化的 Excel 文件",
          "<strong>三種模式</strong>：基本、格式化、優化模式",
          "<strong>篩選匯出</strong>：可按業者、業態、狀態篩選",
          "<strong>包含元數據</strong>：可選擇是否包含 ID、時間戳等資訊",
          "<strong>背景處理</strong>：大量資料在背景處理，完成後下載"
        ]
      },
      {
        icon: "📋",
        title: "匯出格式",
        important: true,
        content: "<strong>標準匯出格式</strong> - 與匯入功能完全兼容",
        items: [
          "使用與匯入相同的欄位結構",
          "匯出的 Excel 可直接用於匯入功能",
          "包含所有必要欄位：問題、答案、作用域、業態、目標用戶、意圖、關鍵字等",
          "確保資料完整性與一致性"
        ]
      },
      {
        icon: "📁",
        title: "匯出內容",
        content: "匯出的 Excel 文件包含以下欄位：",
        items: [
          "<strong>問題摘要</strong>：知識的問題描述",
          "<strong>標準答案</strong>：知識的答案內容",
          "<strong>意圖標籤</strong>：關聯的意圖（主要/次要）",
          "<strong>業態類型</strong>：適用的業態",
          "<strong>目標用戶</strong>：適用的用戶角色",
          "<strong>分類</strong>：知識所屬分類",
          "<strong>作用域</strong>：global/vendor/customized",
          "<strong>優先級</strong>：知識的優先級",
          "<strong>啟用狀態</strong>：是否已啟用",
          "<strong>元數據</strong>（可選）：ID、建立時間、更新時間等"
        ]
      },
      {
        icon: "⚙️",
        title: "匯出流程",
        items: [
          "1️⃣ <strong>選擇供應商</strong>：選擇要匯出的業者",
          "2️⃣ <strong>開始匯出</strong>：點擊「開始匯出」按鈕",
          "3️⃣ <strong>背景處理</strong>：系統在背景處理匯出任務",
          "4️⃣ <strong>查看進度</strong>：在匯出歷史中監控進度",
          "5️⃣ <strong>下載檔案</strong>：處理完成後點擊下載按鈕"
        ]
      },
      {
        icon: "📊",
        title: "匯出歷史",
        content: "系統會保留所有匯出記錄，包含：",
        items: [
          "<strong>任務狀態</strong>：等待中、處理中、已完成、失敗",
          "<strong>處理進度</strong>：實時顯示處理百分比",
          "<strong>匯出數量</strong>：成功匯出的知識筆數",
          "<strong>建立時間</strong>：任務建立的時間",
          "<strong>下載功能</strong>：隨時重新下載已完成的檔案"
        ]
      },
      {
        icon: "⚠️",
        title: "注意事項",
        type: "warning",
        items: [
          "⚠️ <strong>大量資料</strong>：匯出大量資料需要較長時間，請耐心等待",
          "⚠️ <strong>檔案保留</strong>：匯出檔案會保留 7 天，請及時下載",
          "⚠️ <strong>資料安全</strong>：匯出檔案包含完整知識內容，請妥善保管",
          "⚠️ <strong>格式相容</strong>：建議使用 Excel 2016 或更新版本開啟"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>定期備份</strong>：建議每週或每月匯出一次作為備份",
        "✅ <strong>匯出後可匯入</strong>：匯出的檔案可直接用於匯入功能",
        "✅ <strong>分業者匯出</strong>：分別匯出不同業者的知識，便於管理",
        "✅ <strong>資料遷移</strong>：可用於跨環境的資料遷移",
        "⚠️ <strong>檢查完整性</strong>：匯出後檢查筆數是否正確"
      ]
    }
  },

  /**
   * 知識匯入
   */
  knowledgeImport: {
    title: "💡 什麼是知識匯入？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "📥",
        title: "核心功能",
        content: "<strong>知識匯入（Knowledge Import）</strong> 用於批量匯入知識庫資料，支援多種格式。",
        items: [
          "<strong>多格式支援</strong>：Excel (.xlsx, .xls)、純文字 (.txt)、JSON (.json)",
          "<strong>自動向量化</strong>：匯入時自動生成 Embedding 向量",
          "<strong>智能去重</strong>：自動檢測並跳過重複知識",
          "<strong>意圖自動分類</strong>：可選擇性自動分配意圖標籤",
          "<strong>審核機制</strong>：所有匯入的知識先進入審核佇列"
        ]
      },
      {
        icon: "📄",
        title: "支援的文件格式",
        important: true,
        table: {
          headers: ["格式", "適用場景", "說明"],
          rows: [
            ["Excel (.xlsx, .xls)", "結構化數據批量匯入", "適合有完整欄位的知識庫"],
            ["純文字 (.txt)", "LINE 聊天記錄匯入", "自動提取對話中的問答對"],
            ["JSON (.json)", "API 或程式化匯入", "結構化 JSON 格式數據"]
          ]
        }
      },
      {
        icon: "📋",
        title: "Excel 格式要求",
        content: "匯入的 Excel 文件需包含以下欄位：",
        table: {
          headers: ["欄位名稱", "必填", "說明"],
          rows: [
            ["question_summary", "✅", "問題摘要"],
            ["answer", "✅", "標準答案"],
            ["scope", "✅", "作用域（global/vendor/customized）"],
            ["vendor_id", "❌", "業者 ID（vendor/customized 必填）"],
            ["business_types", "❌", "業態類型（逗號分隔）"],
            ["target_user", "❌", "目標用戶（逗號分隔）"],
            ["category", "❌", "分類"],
            ["intent_names", "❌", "意圖名稱（逗號分隔）"],
            ["is_template", "❌", "是否為模板（true/false）"],
            ["priority", "❌", "優先級（數字）"]
          ]
        }
      },
      {
        icon: "📝",
        title: "TXT 格式說明（LINE 聊天記錄）",
        content: "適用於從 LINE 匯出的聊天記錄文件：",
        items: [
          "<strong>格式</strong>：LINE 標準匯出格式（含時間、發送者、訊息）",
          "<strong>處理方式</strong>：AI 自動識別對話中的問答對",
          "<strong>去重機制</strong>：自動跳過已存在的知識",
          "<strong>審核流程</strong>：提取的問答對會先進入審核佇列"
        ]
      },
      {
        icon: "⚙️",
        title: "匯入流程",
        items: [
          "1️⃣ <strong>準備文件</strong>：按照對應格式要求準備數據",
          "2️⃣ <strong>上傳文件</strong>：選擇文件並上傳（支援拖曳）",
          "3️⃣ <strong>預覽確認</strong>：查看文件基本資訊和前 20 行",
          "4️⃣ <strong>系統處理</strong>：自動提取、向量化、分類意圖",
          "5️⃣ <strong>檢視結果</strong>：查看匯入成功和失敗的統計"
        ]
      },
      {
        icon: "⚠️",
        title: "注意事項",
        type: "warning",
        items: [
          "⚠️ <strong>檔案大小</strong>：單一文件限制 50MB",
          "⚠️ <strong>數據驗證</strong>：匯入前請確保數據格式正確",
          "⚠️ <strong>智能去重</strong>：系統會自動跳過重複知識",
          "⚠️ <strong>審核機制</strong>：所有匯入知識需人工審核後才會生效",
          "⚠️ <strong>API 額度</strong>：向量化和意圖分類會消耗 OpenAI API 額度"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>選擇合適格式</strong>：Excel 適合結構化數據，TXT 適合聊天記錄",
        "✅ <strong>使用預覽功能</strong>：上傳後先預覽，確認格式無誤",
        "✅ <strong>分批匯入</strong>：大量數據分批匯入，避免超時",
        "✅ <strong>定期審核</strong>：及時審核匯入的知識，保持知識庫更新",
        "⚠️ <strong>檢查結果</strong>：匯入完成後檢查統計報告"
      ]
    }
  },

  /**
   * 測試場景
   */
  testScenarios: {
    title: "💡 什麼是測試場景？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "🧪",
        title: "核心功能",
        content: "<strong>測試場景（Test Scenarios）</strong> 用於管理和執行 AI 對話測試案例。",
        items: [
          "<strong>測試案例管理</strong>：建立、編輯、刪除測試案例",
          "<strong>批量測試</strong>：一次執行多個測試案例",
          "<strong>預期答案比對</strong>：比對實際答案與預期答案",
          "<strong>測試報告</strong>：生成詳細的測試結果報告"
        ]
      },
      {
        icon: "📋",
        title: "測試案例結構",
        content: "每個測試案例包含：",
        items: [
          "<strong>問題</strong>：測試用的使用者問題",
          "<strong>預期答案</strong>：期望 AI 回答的內容（可選）",
          "<strong>預期意圖</strong>：期望識別的意圖",
          "<strong>業態標籤</strong>：測試特定業態的回答",
          "<strong>用戶角色</strong>：測試特定角色的回答"
        ]
      },
      {
        icon: "🎯",
        title: "使用場景",
        important: true,
        items: [
          "<strong>迴歸測試</strong>：修改知識庫後，確保現有功能正常",
          "<strong>意圖驗證</strong>：驗證意圖分類是否準確",
          "<strong>業態測試</strong>：測試不同業態的回答差異",
          "<strong>上線前測試</strong>：新功能上線前的品質把關"
        ]
      },
      {
        icon: "📊",
        title: "測試報告",
        content: "測試完成後，系統會生成報告包含：",
        items: [
          "✅ <strong>通過率</strong>：測試通過的比例",
          "📝 <strong>意圖準確度</strong>：意圖分類的準確率",
          "⏱️ <strong>回應時間</strong>：平均回應時間",
          "❌ <strong>失敗案例</strong>：列出所有失敗的測試案例"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>建立核心場景</strong>：涵蓋最常見的問題類型",
        "✅ <strong>定期執行</strong>：每次修改知識庫後都執行測試",
        "✅ <strong>更新測試案例</strong>：隨著系統演進更新測試案例",
        "✅ <strong>分類管理</strong>：按業態、意圖分類測試案例",
        "⚠️ <strong>不要過度測試</strong>：專注核心場景即可"
      ]
    }
  },

  /**
   * 回測系統
   */
  backtest: {
    title: "💡 什麼是回測系統？",
    lastUpdated: "2025-10-28",
    sections: [
      {
        icon: "📊",
        title: "核心功能",
        content: "<strong>回測系統（Backtest）</strong> 用於批量測試 AI 系統的效能和準確度。",
        items: [
          "<strong>批量測試</strong>：一次測試數百個問題",
          "<strong>效能評估</strong>：評估意圖分類和答案品質",
          "<strong>趨勢分析</strong>：追蹤系統效能的變化趨勢",
          "<strong>A/B 比較</strong>：比較不同配置的效能差異"
        ]
      },
      {
        icon: "🎯",
        title: "評估指標",
        important: true,
        table: {
          headers: ["指標", "說明", "目標值"],
          rows: [
            ["意圖準確率", "正確識別意圖的比例", "> 85%"],
            ["答案相關度", "答案與問題的相關程度", "> 0.8"],
            ["回應時間", "從問題到答案的平均時間", "< 3 秒"],
            ["Intent Boost 效果", "主要意圖是否排在前 3 名", "> 90%"]
          ]
        }
      },
      {
        icon: "📋",
        title: "測試流程",
        items: [
          "1️⃣ <strong>準備測試數據</strong>：從測試場景或歷史對話匯入",
          "2️⃣ <strong>配置參數</strong>：選擇業態、用戶角色等過濾條件",
          "3️⃣ <strong>執行測試</strong>：批量執行所有測試案例",
          "4️⃣ <strong>分析結果</strong>：檢視報告，找出需要優化的地方"
        ]
      },
      {
        icon: "🔧",
        title: "優化建議",
        content: "根據回測結果進行優化：",
        items: [
          "<strong>意圖準確率低</strong> → 調整意圖關鍵字、重新分類知識",
          "<strong>答案相關度低</strong> → 優化知識內容、增加意圖標籤",
          "<strong>回應時間慢</strong> → 優化檢索參數、減少 top_k",
          "<strong>Intent Boost 無效</strong> → 檢查知識的意圖標籤是否正確"
        ]
      }
    ],
    tips: {
      title: "使用建議",
      items: [
        "✅ <strong>定期回測</strong>：每週或每月執行一次",
        "✅ <strong>記錄趨勢</strong>：追蹤指標的變化趨勢",
        "✅ <strong>分業態測試</strong>：不同業態分別測試",
        "✅ <strong>比較配置</strong>：測試不同參數的效果",
        "⚠️ <strong>測試數據品質</strong>：確保測試數據具代表性"
      ]
    }
  }
};
