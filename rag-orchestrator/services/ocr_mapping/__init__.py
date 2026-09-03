"""documind-ocr-mapping —— DocuMind OCR 回應 → JGB 欄位草稿的映射管線。

分工（業主 2026-09-03 拍板 B）：DocuMind 負責 OCR＋抽欄位、line-bot 負責檔案與呼叫 DocuMind，
本套件只做映射與規則校驗。⛔ 不碰檔案、⛔ 不呼叫 DocuMind、⛔ 不寫 JGB。
規格：.kiro/specs/documind-ocr-mapping/（requirements v2、design 9 元件）。
"""
