# 微觀引擎兩頁參考報告

[開啟兩頁 PDF](微觀引擎-兩頁參考報告.pdf)

依新版簡報第 9–11 張與評分項目整理，作為閱讀與討論的參考稿。內容包含控溫與溫度定義、控制功、正功證據、三種準靜態變因、兩張線性關係圖與雙週期邊界。本文的數值來自 Langevin 模擬，不是實驗室實測。

## 資料來源

- 正功：`../docs/verification/2026-10-22/chromium-all-evidence.json` 的 positive 證據；N=64、20 次獨立重複，各暖機 2 圈再平均 5 圈。
- 兩張線性圖：`../docs/verification/2026-10-22/formal-temperature.json` 與 `formal-ratio.json`；每點 N=32、20 次獨立重複，各暖機 2 圈再平均 3 圈。這些是已保存的資料，本次未重跑。
- 本次補跑：`quasistatic-data.json`，直接讀取 bd51397 的 `index.html` 中 engine-core 與 engine-jobs。共 26 個掃描點、520 次獨立重複，保留暖機及配對對照共 4,340 圈原始記錄。曲率時間、曲率尺度、搬運各使用 N=32、R=20、K=5；邊界掃描另使用曲率段 100、換浴段 20。
- 所有均值先在同次重複內平均，再計算跨重複的 95% t 信賴區間；PDF 擬合表中的 SE 是 OLS 斜率標準誤。圖為向量圖，可放大閱讀；沒有放大誤差棒或以理論生成資料點。
- 補跑各掃描的完整點集都保留；兩頁表格只摘列端點比較，未刪除不利結果。快速搬運的平均淨功為負。

## 重製

從 repo 根目錄執行：

```sh
node reports/collect.cjs
python3 reports/generate_report.py
```

第一行會重算補跑資料；若只重新排版既有結果，只執行第二行。Python 需要 ReportLab；目前版面使用 macOS 的 STHeiti Light、STHeiti Medium 與 Arial Unicode 字型，PDF 已嵌入所用字型。其他平台重製時需改成可用的中文字型；閱讀 PDF 不需安裝這些依賴。腳本會檢查數值核心 hash 是否與原始資料相同。

`validation.json` 記錄交付 PDF 的頁數、hash 與檢查範圍。新資料的圈平均、跨重複平均、95% CI 與配對差皆另行核對；PDF 兩頁已轉成圖像逐頁檢視，修正缺字後才交付。本次沒有改動網站或重跑既有全套網站測試。
