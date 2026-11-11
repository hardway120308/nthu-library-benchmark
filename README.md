# NTHU Library Benchmark

以 Playwright 開啟清華大學圖書館 Primo 搜尋頁面，記錄使用者首次能看到搜尋記錄的時間。

## 需求

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Playwright Chromium

## 安裝

```bash
uv sync
uv run playwright install chromium
```

## 使用方式

在專案根目錄執行：

```bash
uv run main
```

程式會開啟 Chromium，自動將固定關鍵字逐一填入搜尋欄並按下搜尋按鈕。每個關鍵字完成 DOM ready 後才會進入下一筆；按 `Ctrl+C` 發出停止請求。程式會先自然結束輪詢、關閉瀏覽器，再輸出統計，不會以例外中斷 Playwright 等待。

也可以使用模組入口：

```bash
uv run python -m nthu_library_benchmark
```

### 命令列選項

```text
--url URL       指定啟動頁面
--output PATH   指定記錄檔名稱前綴
--headless      使用無頭模式執行
--stats-output PATH  Ctrl+C 後將統計報告與 ASCII 圖表儲存至指定路徑
--keywords KEYWORD  直接指定要執行的關鍵字列表
--keywords-file PATH  從檔案載入關鍵字（預設：keywords.txt）
```

例如：

```bash
uv run main --headless --output /tmp/nthu-records.txt
```

預設會從根目錄的 [keywords.txt](./keywords.txt) 載入 1000 個跨主題的書籍搜尋詞，
檔案格式是一行一個關鍵字，也支援空白行與 `#` 開頭的註解。

指定自訂關鍵字檔案：

```bash
uv run main --headless --keywords-file my-keywords.txt
```

也可以直接指定少量關鍵字（會覆蓋關鍵字檔案）：

```bash
uv run main --headless --keywords artificial intelligence database library
```

程式會先完成初始頁面載入，之後才開始執行與統計關鍵字列表，因此初始載入不會混入統計結果。

## 判定方式

每次主頁面 URL 變更時才會開始新的計時。當
`prm-brief-result-container` 的第一筆元素同時符合以下條件，就視為搜尋記錄首次可用：

1. 元素可見。
2. 元素包含非空文字。

程式不會等待圖片、追蹤請求或其他無關資源完成，因此 `dom_elapsed` 代表 DOM 結果首次可供使用的大致時間。

## 輸出

記錄會寫入 `storage/records_YYYYMMDD_HHMMSS.txt`。目前只會持久化事件記錄，例如：

```text
URLCHANGE               delta=0.012s
READY_FOR_INTERACTIVE   delta=0.351s    dom_elapsed=0.351s
```

- `delta`：距離上一個記錄事件的秒數。
- `dom_elapsed`：從該 URL 變更到首筆搜尋記錄可見的秒數。

按下 `Ctrl+C` 後，程式會針對本次執行成功完成的 `dom_elapsed` 輸出：

- 樣本數、平均數、樣本標準差、最小值與最大值。
- 第一四分位數（Q1）、中位數與第三四分位數（Q3）。
- 以 ASCII histogram 顯示各時間區間的樣本數。

若要同時保存統計報告：

```bash
uv run main --stats-output storage/statistics.txt
```

## 開發檢查

```bash
uv run python -m compileall src
uv run main --help
```
