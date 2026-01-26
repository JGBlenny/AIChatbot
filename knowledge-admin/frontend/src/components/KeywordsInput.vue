<template>
  <div class="keywords-input">
    <div class="keywords-container">
      <span
        v-for="(keyword, index) in modelValue"
        :key="index"
        class="keyword-tag"
      >
        {{ keyword }}
        <button
          type="button"
          @click="removeKeyword(index)"
          class="remove-btn"
          :aria-label="`移除關鍵詞: ${keyword}`"
        >
          ✕
        </button>
      </span>

      <input
        ref="keywordInput"
        v-model="newKeyword"
        @keydown.enter.prevent="addKeyword"
        @keydown.comma.prevent="addKeyword"
        @paste="handlePaste"
        :placeholder="placeholder"
        class="keyword-input"
        type="text"
      />
    </div>

    <p v-if="hint" class="keyword-hint">{{ hint }}</p>
  </div>
</template>

<script>
export default {
  name: 'KeywordsInput',

  props: {
    modelValue: {
      type: Array,
      default: () => []
    },
    placeholder: {
      type: String,
      default: '輸入關鍵詞後按 Enter 或逗號'
    },
    hint: {
      type: String,
      default: ''
    },
    maxKeywords: {
      type: Number,
      default: 20
    },
    allowDuplicates: {
      type: Boolean,
      default: false
    }
  },

  emits: ['update:modelValue'],

  data() {
    return {
      newKeyword: ''
    };
  },

  methods: {
    addKeyword() {
      const keyword = this.newKeyword.trim();

      if (!keyword) {
        return;
      }

      // 檢查是否超過最大數量
      if (this.modelValue.length >= this.maxKeywords) {
        alert(`最多只能新增 ${this.maxKeywords} 個關鍵詞`);
        return;
      }

      // 檢查是否重複（如果不允許重複）
      if (!this.allowDuplicates && this.modelValue.includes(keyword)) {
        alert('此關鍵詞已存在');
        this.newKeyword = '';
        return;
      }

      // 新增關鍵詞
      const updatedKeywords = [...this.modelValue, keyword];
      this.$emit('update:modelValue', updatedKeywords);
      this.newKeyword = '';

      // 保持 input 焦點
      this.$nextTick(() => {
        this.$refs.keywordInput?.focus();
      });
    },

    removeKeyword(index) {
      const updatedKeywords = [...this.modelValue];
      updatedKeywords.splice(index, 1);
      this.$emit('update:modelValue', updatedKeywords);
    },

    handlePaste(event) {
      // 處理貼上多個關鍵詞（以逗號、分號、換行分隔）
      event.preventDefault();
      const pastedText = event.clipboardData.getData('text');

      if (!pastedText) {
        return;
      }

      // 分割文字（支援逗號、分號、換行）
      const keywords = pastedText
        .split(/[,;\n]+/)
        .map(k => k.trim())
        .filter(k => k.length > 0);

      if (keywords.length === 0) {
        return;
      }

      // 檢查是否超過最大數量
      const remainingSlots = this.maxKeywords - this.modelValue.length;
      if (keywords.length > remainingSlots) {
        alert(`最多只能新增 ${remainingSlots} 個關鍵詞（目前已有 ${this.modelValue.length} 個）`);
        return;
      }

      // 過濾重複項（如果不允許重複）
      let validKeywords = keywords;
      if (!this.allowDuplicates) {
        validKeywords = keywords.filter(k => !this.modelValue.includes(k));
        const duplicateCount = keywords.length - validKeywords.length;
        if (duplicateCount > 0) {
          alert(`已過濾 ${duplicateCount} 個重複的關鍵詞`);
        }
      }

      if (validKeywords.length > 0) {
        const updatedKeywords = [...this.modelValue, ...validKeywords];
        this.$emit('update:modelValue', updatedKeywords);
      }
    }
  }
};
</script>

<style scoped>
.keywords-input {
  width: 100%;
}

.keywords-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background-color: #fff;
  min-height: 42px;
  cursor: text;
}

.keywords-container:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.keyword-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background-color: #3b82f6;
  color: white;
  border-radius: 16px;
  font-size: 0.875rem;
  line-height: 1.25rem;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.keyword-tag:hover {
  background-color: #2563eb;
}

.remove-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.remove-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.keyword-input {
  flex: 1;
  min-width: 120px;
  border: none;
  outline: none;
  padding: 4px;
  font-size: 0.875rem;
  background: transparent;
}

.keyword-input::placeholder {
  color: #9ca3af;
}

.keyword-hint {
  margin-top: 6px;
  margin-bottom: 0;
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.4;
}
</style>
