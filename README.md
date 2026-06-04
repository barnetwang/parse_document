# Document Structuring Tool (文件結構化與管理工具)

這是一個用來解析 PDF 與 Word (.docx) 文件並進行結構化分塊的工具。它能自動識別章節標題將長文件切碎為 Markdown 區塊，並提供了一個網頁介面（WebUI），讓你可以方便地透過瀏覽器上傳文件、瀏覽目錄結構、進行全域內文搜尋以及下載/複製切片內容。

所有的解析結果除了會產出實體 Markdown 檔案外，也會自動同步存入本機的 SQLite 資料庫，方便日後整理與快速查詢。

---

## 功能特色

* **雙格式支援**：支援 `.pdf` (基於 `pymupdf4llm`) 與 `.docx` (基於 `python-docx`) 文件解析。
* **智慧標題分塊**：
  * 自動辨識各級標題（例如 `#`, `##` 或 Word 中的 `Heading 1-9`、`Title` 樣式）進行切割。
  * 自動產生偽章節編號（如遇到無編號標題會依層級產生 `1.1`, `1.2` 等序號），並在遇到顯式編號時自動同步計數器。
* **雜訊過濾**：自動過濾頁首、頁尾、頁碼、機密標記及目錄（Table of Contents）等無效雜訊。
* **網頁化管理介面 (WebUI)**：
  * **拖曳上傳**：直覺的文件上傳與即時解析進度條。
  * **章節目錄樹**：以樹狀目錄直觀展示文件結構。
  * **閱讀器**：直接在網頁上以排版美觀的 HTML 格式閱讀 Markdown 內容，支援一鍵複製與下載實體 `.md` 檔案。
  * **全域搜尋**：支援跨文件或針對單一文件的內文關鍵字快速檢索。
* **SQLite 本機資料庫**：所有解析出的段落、標題、頁碼、檔案路徑都會寫入 `documents.db`，查詢快速且不佔用外部資料庫伺服器。

---

## 安裝步驟

安裝所需的 Python 套件：

```bash
pip install -r requirements.txt
```

---

## 使用說明

### 1. 啟動網頁介面 (推薦)

執行後端伺服器：

```bash
python app.py
```

啟動後，使用瀏覽器開啟以下網址即可使用完整的上傳與管理功能：
`http://localhost:5000`

### 2. 使用命令列單獨解析

如果您只想透過指令快速解析單一文件：

```bash
python parse_document.py <文件路徑.pdf_或_docx>
```

解析完成後，會直接在 `output/` 目錄下生成結構化的 markdown 檔案與 `index.md` 索引。

---

## 專案結構

```text
├── app.py              # Web 伺服器 (Flask) 的進入點
├── database.py         # 資料庫存取模組 (SQLite 建立、儲存、查詢、刪除)
├── parse_document.py   # 文件解析與標題切割核心邏輯
├── test_parser.py      # 解析器單元測試
├── requirements.txt    # 專案套件相依清單
├── documents.db        # SQLite 資料庫檔案 (執行後自動生成)
├── templates/          # WebUI HTML 模板
├── static/             # CSS 樣式與前端 JS 腳本
├── uploads/            # 上傳時的暫存資料夾
└── output/             # 實體 Markdown 切片輸出目錄 (依 document ID 分門別類)
    └── <document_id>/
        ├── index.md    # 該文件的 Markdown 索引檔
        ├── toc.json    # 該文件的目錄結構資料
        └── chunks/     # 存放該文件所有的段落 Markdown 檔案
```

---

## 執行測試

本專案附帶單元測試，用以驗證標題識別、編號同步、雜訊過濾等核心邏輯：

```bash
python test_parser.py
```

---

# Document Structuring Tool (English Version)

This tool parses PDF and Word (.docx) documents and splits them into structured Markdown chunks. It automatically detects section headings to slice long documents into readable Markdown files and provides a Web UI for you to upload documents, browse table of contents (TOC) trees, perform global text searches, and copy or download the generated markdown chunks.

In addition to writing the physical Markdown files, all parsing results are synchronized into a local SQLite database for easy organization and fast lookups.

---

## Features

* **Multi-Format Support**: Parse both `.pdf` (powered by `pymupdf4llm`) and `.docx` (powered by `python-docx`) files.
* **Intelligent Heading Chunking**:
  * Automatically identifies heading levels (e.g., `#`, `##` in Markdown, or `Heading 1-9`, `Title` styles in Word) for clean slicing.
  * Generates pseudo-section numbers dynamically for unnumbered headings (e.g., `1.1`, `1.2`), and synchronizes the counters when explicit ones are encountered.
* **Noise Filtering**: Automatically filters out footers, headers, page numbers, confidential stamps, and Tables of Contents.
* **Web UI Management Dashboard**:
  * **Drag & Drop Upload**: Upload files easily with an interactive progress indicator.
  * **Interactive TOC Tree**: Explore document hierarchy with collapsible section nodes.
  * **Reader Panel**: Read chunks as formatted HTML with instant "Copy Markdown" and "Download File" buttons.
  * **Global Search**: Search terms across all files or target the active document only.
* **Local SQLite Database**: Stores all parsed text, titles, pages, and file paths in `documents.db` for zero-setup, fast queries.

---

## Installation

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage Guide

### 1. Launch the Web UI (Recommended)

Run the backend web server:

```bash
python app.py
```

Once started, open your browser and navigate to:
`http://localhost:5000`

### 2. Slicing via CLI

If you prefer to run parsing workflows directly from the terminal:

```bash
python parse_document.py <path_to_file.pdf_or_docx>
```

The output will be created inside the `output/` directory, including structured markdown files and an `index.md` catalog.

---

## Project Structure

```text
├── app.py              # Flask Web Server entry point
├── database.py         # SQLite database connector (saves, searches, and deletes docs)
├── parse_document.py   # Document parsing and slicing core logic
├── test_parser.py      # Parser logic unit tests
├── requirements.txt    # Python dependencies list
├── documents.db        # SQLite database file (auto-generated)
├── templates/          # HTML templates for the Web UI
├── static/             # CSS styling and frontend JavaScript application
├── uploads/            # Temporary upload workspace folder
└── output/             # Sliced Markdown output directory (organized by document ID)
    └── <document_id>/
        ├── index.md    # Markdown table of contents index
        ├── toc.json    # TOC json index file
        └── chunks/     # Markdown slices folder
```

---

## Running Tests

To execute the suite of unit tests verifying heading detection, counter syncing, and measurement noise filters:

```bash
python test_parser.py
```
