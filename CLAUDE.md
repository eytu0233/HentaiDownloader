# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-site manga/comic downloader application with a PySide2 (Qt) GUI. It supports downloading from multiple sources: NHentai, WNACG, EHentai, 18Comic, AHentai, and ImHentai. The application monitors the clipboard for supported URLs and automatically initiates downloads.

## Running the Application

```bash
# Run the GUI application
python main.py

# Or use the batch file
downloader.bat

# Organize downloads by author
python organize_by_author.py [download_path] [--dry-run]
# Or use the batch file
organize.bat
```

## Core Architecture

### Plugin-Based Downloader Pattern

The application uses a plugin-style architecture where each supported site implements two classes:

1. **Parser (extends `Downloader.Parser`)**:
   - Checks if a URL matches the site's pattern via `check()` method
   - Extracts metadata (title, page count, media IDs, etc.) from the site
   - Emits a Downloader instance when parsing is complete via `signal.parsed`
   - Runs as a QRunnable in a dedicated thread pool

2. **Downloader (extends `Downloader.Downloader`)**:
   - Handles the actual download process
   - Updates progress via `signal.progress` (percentage)
   - Updates status via `signal.status` (STATUS_PENDING, STATUS_DOWNLOADING, STATUS_DOWNLOADED, STATUS_FAIL)
   - Runs in a site-specific thread pool to manage concurrent downloads

### Thread Pool Management

Each site has its own QThreadPool (defined in `main.py:MainWindow.__init__`):
- `ehentaiThreadPool`
- `nhentaiThreadPool` (max 1 thread)
- `wnacgThreadPool` (max 1 thread)
- `eighteenComicThreadPool`
- `ahentaiThreadPool`
- `imhentaiThreadPool`

Additionally:
- `parserThreadPool`: Handles all parsing operations
- `checkerThreadPool`: Monitors clipboard (max 1 thread)

### URL Processing Flow

1. URL detected via clipboard monitor or manual entry
2. `MainWindow.start_parser()` creates instances of all Parser classes
3. Each Parser's `check()` method determines if it can handle the URL
4. First matching Parser is added to `parserList` and started
5. Parser extracts metadata and emits a Downloader instance
6. `MainWindow.add_download_item()` receives Downloader, adds to UI table
7. Downloader starts and updates progress/status via signals

## Adding a New Site

To add support for a new download source:

1. Create `NewSiteDownloader.py` with:
   - `NewSiteParser(Parser)` class with `check()` and `run()` methods
   - `NewSiteDownloader(Downloader)` class with `run()` method

2. Import in `main.py`:
   ```python
   from NewSiteDownloader import NewSiteParser
   ```

3. Add thread pool in `MainWindow.__init__`:
   ```python
   self.newsiteThreadPool = QThreadPool()
   ```

4. Add to parser list in `MainWindow.start_parser()`:
   ```python
   parsers = [
       # ... existing parsers ...
       NewSiteParser(url, path, self.newsiteThreadPool)
   ]
   ```

## Special Features

### Chrome Cookie Access
Several downloaders use `browser_cookie3` to access Chrome cookies for authenticated requests. Chrome version is detected via Windows registry (`winreg`) to set proper User-Agent headers.

### WNACG Auto-Unzip
`WNACGDownloader` automatically extracts downloaded ZIP files using `zipfile2` (supports deflate64 compression). After download:
1. File is downloaded as `.zip`
2. Status changes to `STATUS_UNZIPING`
3. ZIP is extracted to folder (using `extract_deflate64_zip`)
4. Temporary ZIP file is removed
5. Status changes to `STATUS_UNZIP`

### Image Scramble Fix
`ImageReviser.py` contains logic to unscramble images that some sites serve in scrambled format. Images are split into `IMAGE_PART_NUM` parts and rearranged. This is accessed via context menu "圖片修正" (Image Revision) in the UI.

### Clipboard Monitoring
The application continuously monitors the system clipboard. When a URL is copied, it automatically triggers the parsing flow without manual paste/click.

### Author Organization Script
`organize_by_author.py` reorganizes downloaded content by author:
- Extracts author names from directory names in `[作者名]作品名` format
- Creates author directories `[作者名]/`
- Moves all works by the same author into their directory
- Deletes duplicate directories if found
- Supports dry-run mode (`--dry-run` or `-n`) to preview changes without modifying files
- Can be run via `organize.bat` for interactive menu
- Supports merge mode (`--merge`) to combine author directories from two separate locations
- Automatically exports logs to `logs/organize_YYYYMMDD_HHMM.log` with timestamp

## File Structure

- `main.py` - Application entry point, MainWindow class, UI event handling
- `ui.py` - Auto-generated PySide2 UI code (DO NOT EDIT - regenerate from `.ui` file)
- `Downloader.py` - Base classes: `Parser` and `Downloader`
- `*Downloader.py` - Site-specific implementations (NHentai, WNACG, EHentai, etc.)
- `ImageReviser.py` - Utility to fix scrambled images
- `organize_by_author.py` - Script to organize downloads by author name into subdirectories
- `logo.ico` - Application icon
- `downloader.bat` - Batch file to launch the application
- `organize.bat` - Batch file to run the organization script
- `downloader.exe` - Compiled executable (likely PyInstaller output)

## Platform-Specific Notes

This application is **Windows-only** due to:
- Use of `winreg` module to detect Chrome version from Windows Registry
- Windows-specific path handling (backslashes)
- Browser cookie extraction assumes Windows Chrome installation

## Dependencies

Based on imports, the application requires:
- PySide2 (Qt for Python)
- BeautifulSoup4 (HTML parsing)
- requests (HTTP requests)
- browser_cookie3 (Chrome cookie extraction)
- zipfile2 (deflate64 ZIP support)
- rookiepy (alternative cookie extraction)
- pycryptodomex (AES encryption for cookies)
- Pillow (image processing)

## Status Constants

Defined in `Downloader.py`:
- `STATUS_PENDING` = '列隊中' (Queued)
- `STATUS_DOWNLOADING` = '下載中' (Downloading)
- `STATUS_DOWNLOADED` = '下載完成' (Download Complete)
- `STATUS_UNZIPING` = '解壓縮中' (Unzipping)
- `STATUS_UNZIP` = '解壓縮完成' (Unzip Complete)
- `STATUS_UNZIP_FAIL` = '解壓縮失敗' (Unzip Failed)
- `STATUS_FAIL` = '下載失敗' (Download Failed)

## Logging

Logging is configured in `main.py` at DEBUG level. External library logs (requests, chardet, urllib3) are set to WARNING to reduce noise.
