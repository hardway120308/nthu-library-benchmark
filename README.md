# NTHU Library Benchmark

使用 Playwright 自動搜尋清華大學圖書館 Primo，測量搜尋結果首次可用的 DOM 時間。

## 安裝

需求：Python 3.14+ 與 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run playwright install chromium
```

## 使用

執行預設的 1000 個跨主題書籍關鍵字：

```bash
uv run main
```

程式會逐一填入關鍵字、送出搜尋，並在 DOM 首筆結果可見時記錄
`dom_elapsed`。按 `Ctrl+C` 可安全停止並輸出統計。

### 自訂關鍵字

預設從根目錄的 [keywords.txt](/home/hardway/projects/nthu-library-benchmark/keywords.txt)
載入，一行一個關鍵字；空白行與 `#` 開頭的行會被忽略。

```bash
uv run main --keywords-file my-keywords.txt
```

也可以直接指定關鍵字：

```bash
uv run main --keywords artificial intelligence database library
```

### 常用選項

```text
--headless                 使用無頭模式
--output PATH              記錄檔路徑前綴
--stats-output PATH        保存統計報告
--url URL                  指定 Primo 起始網址
```

例如：

```bash
uv run main --headless --stats-output storage/statistics.txt
```

## 輸出

- 事件記錄：`storage/records_YYYYMMDD_HHMMSS.txt`
- 統計報告：使用 `--stats-output` 指定，包含平均數、樣本標準差、四分位數與 ASCII histogram。

## 開發檢查

```bash
uv run python -m compileall src
uv run main --help
```
