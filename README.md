# NewWNACGDownloader

多站點漫畫下載器，支援 NHentai、WNACG、EHentai、18Comic、AHentai、ImHentai，具備 PySide2 GUI 介面，並自動監聽剪貼簿 URL。

## 支援網站

| 網站 | 說明 |
|------|------|
| WNACG | 自動下載並解壓縮 ZIP |
| NHentai | |
| EHentai / ExHentai | 需要登入 Cookie |
| 18Comic | |
| AHentai | |
| ImHentai | |

## 環境需求

- Windows 10/11
- Python 3.7–3.10（PySide2 限制）
- Google Chrome（用於讀取登入 Cookie）
- [uv](https://github.com/astral-sh/uv)

## 安裝

### 使用 uv（建議）

```bash
# 安裝 uv（若尚未安裝）
pip install uv

# 建立虛擬環境並安裝所有依賴
uv venv --python 3.7
uv sync
```

### 啟動應用程式

```bash
# 啟動 GUI
uv run python main.py

# 或使用批次檔
downloader.bat
```

## 功能說明

### 剪貼簿自動偵測

複製支援網站的 URL 後，應用程式會自動偵測並開始解析，無需手動貼上。

### WNACG 自動解壓縮

下載完成後會自動解壓縮 ZIP 檔案（支援 deflate64 格式），解壓縮完成後刪除原始 ZIP。

### 圖片修正

對於部分網站提供的亂序圖片，可在 UI 右鍵選單選擇「圖片修正」進行還原。

### 依作者整理下載

```bash
# 預覽整理結果（不實際移動檔案）
python organize_by_author.py [下載路徑] --dry-run

# 實際整理
python organize_by_author.py [下載路徑]

# 或使用批次檔（互動選單）
organize.bat
```

整理腳本會依照目錄名稱中 `[作者名]作品名` 的格式，將作品移入對應的 `[作者名]/` 資料夾。

## 專案結構

```
NewWNACGDownloader/
├── main.py                  # 應用程式入口、MainWindow
├── ui.py                    # PySide2 自動生成 UI（勿手動編輯）
├── Downloader.py            # 基底類別 Parser / Downloader
├── WNACGDownloader.py
├── NHentaiDownloader.py
├── EHentaiDownloader.py
├── EighteenComicDownloader.py
├── AHentaiDownloader.py
├── ImHentaiDownloader.py
├── ImageReviser.py          # 亂序圖片修正工具
├── organize_by_author.py    # 依作者整理腳本
├── pyproject.toml           # uv / Python 套件設定
├── downloader.bat           # 啟動批次檔
└── organize.bat             # 整理批次檔
```

## 下載狀態

| 狀態碼 | 說明 |
|--------|------|
| 列隊中 | 等待下載 |
| 下載中 | 下載進行中 |
| 下載完成 | 下載成功 |
| 解壓縮中 | ZIP 解壓縮進行中（WNACG） |
| 解壓縮完成 | 解壓縮成功 |
| 解壓縮失敗 | 解壓縮失敗 |
| 下載失敗 | 下載失敗 |

## 注意事項

- 本工具僅支援 **Windows** 平台（依賴 `winreg` 及 Windows Chrome Cookie 路徑）
- 部分網站需要登入後 Chrome Cookie 才能正常下載
- 請遵守各網站使用條款
