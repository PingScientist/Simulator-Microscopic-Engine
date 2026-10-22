# 字體調整驗證 · 2026-10-22

本目錄保存字體調整後的實際檢查紀錄與截圖，不是預填進網站的數據。

- HTML SHA-256：`2a1347b770330f60498832f54fdde4e5bc025a6abad7ec56f70bacf37dcbd3c1`，145,142 bytes。
- `chromium-browser.json`、`webkit-browser.json`：直接執行現有 `tests/browser.cjs`，各 22 組通過。
- `chromium-typography.json`、`webkit-typography.json`：各 30 個版面條件；五分頁 × 320／375／768／1024／1440px，以及 768px 下把根字級放大為 200%。沒有整頁水平溢出，預設字級下沒有小於 14px 的可見文字（數學上下標除外）。放大檢查是文字縮放，不等同所有瀏覽器的完整頁面縮放。
- 字級檢查讀取可見 DOM 的 computed style；Canvas 字體使用同一 CSS 字級，另以實際圖表與 PNG 截圖檢視。
- 使用已保存的 `../2026-10-22/chromium-all-evidence.json` 載入完整證據，以檢查長文字、數字、圖例與匯出排版。本輪沒有重算正式線性掃描；回歸仍有實際循環與 Worker 掃描。
- Chromium 151.0.7922.34／Playwright 1.62.1：新 context、file://、offline=true，另攔截 HTTP(S)。WebKit 26.4／Playwright 1.59.1：新 context、file://、攔截 HTTP(S)。兩者皆零外部請求、零未捕捉錯誤。
- `engine-core` 與 `engine-jobs` 相較 `1bdf8c9` 逐字相同；本輪未重跑數值核心全套測試。
- 本目錄是保留的驗證產物；本輪生成它們的暫存資料與資料夾在交付前清除。
