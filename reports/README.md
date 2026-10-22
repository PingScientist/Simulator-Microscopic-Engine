# 微觀引擎兩頁參考報告

[開啟兩頁 PDF](微觀引擎-兩頁參考報告.pdf)

依新版簡報第 9–11 張與評分項目整理，作為閱讀與討論的參考稿。內容包含控溫與溫度定義、控制功、正功證據、三種準靜態變因、兩張線性關係圖與雙週期邊界。本文的數值來自 Langevin 模擬，不是實驗室實測。公式、內文符號、表格數學與圖表座標均由 LaTeX 排版；`latex/main.tex` 為可編輯原稿，兩張圖由 PGFPlots 繪製。現行版式採中文學術報告：置中標題與摘要、雙欄正文、連續編號公式、中文圖表說明及參考文獻；黑白圖表以點形與線型區分資料與理論，沒有彩色色塊或裝飾頁首。

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

第一行會重算補跑資料；若只重新排版既有結果，只執行第二行。本次學術版式修訂沒有重跑或修改模擬資料。

產生器需要 Python 3、`pypdf` 與 Tectonic。它會優先使用 PATH 中的 Tectonic，或此 macOS 上 ChatGPT 應用程式隨附的編譯器；也可用 `--tectonic /path/to/tectonic` 指定。原稿使用 `fontspec`、`xeCJK`、`amsmath` 與 `pgfplots`，中文字型為 Songti TC（宋體），西文字型為 Times New Roman。其他平台需在原稿中改成可用的字型；Tectonic 初次編譯可能下載 TeX 套件。閱讀交付 PDF 不需安裝這些依賴。

腳本先核對數值核心 hash，再從原始 JSON 產生 `latex/data/` 的數據巨集和 CSV；圖表保留原始精度，表格才做顯示用四捨五入。`--prepare-only` 可只更新這些資料。`latex/` 也可直接在 LaTeX 編輯器開啟，以 XeLaTeX 或 Tectonic 編譯 `main.tex`。隨附的產生器會在暫存資料夾編譯，確認為兩頁 A4 且沒有缺字或超出版面的警告後，才更新上層 PDF；暫存檔及其資料夾會自動移除。

此環境的 Codex 內建預覽目前無法讀取系統字型；本報告已由 Tectonic 命令列成功編譯，交付 PDF 的閱讀不受影響。

`validation.json` 記錄交付 PDF 的頁數、hash 與檢查範圍。模擬資料的圈平均、跨重複平均、95% CI 與配對差已於資料產生時另行核對。本次針對 LaTeX 編譯、字型嵌入、頁數與兩頁實際渲染進行檢查；沒有改動網站，也沒有重跑既有網站或數值測試。
