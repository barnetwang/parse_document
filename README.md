# Document Parser for LLM & RAG (文件解析工具)

This Python script is designed to parse `.pdf` and `.docx` documents and split them into structured, chunked Markdown files based on section headings. It is highly optimized for preparing documentation for Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) systems.

本 Python 腳本專為解析 `.pdf` 與 `.docx` 文件所設計，能夠依據章節標題將文件切割並轉換為結構化的 Markdown 檔案。此工具非常適合用於為大型語言模型 (LLM) 以及檢索增強生成 (RAG) 系統準備知識庫文件。

## Features (功能特色)

- **Multi-Format Support (支援多格式)**: Parses both `.pdf` (using `pymupdf4llm`) and `.docx` (using `python-docx`) files.
- **Intelligent Chunking (智慧分塊)**: Automatically identifies document headings (e.g., `1.1 Title`) and splits the content into logical sections.
- **Metadata Extraction (元資料萃取)**: Each chunk includes metadata such as the source file name, section number, and starting page.
- **Noise Filtering (過濾雜訊)**: Automatically ignores common page noise like "Table of Contents", headers/footers, "Page X", or confidential stamps based on predefined regex patterns.
- **Index Generation (生成目錄)**: Automatically creates a `toc.json` and a beautifully structured `index.md` linking to all generated chunks.

## Installation (安裝說明)

1. Clone or download this repository. (下載或複製此專案)
2. Install the required dependencies using `pip`. (使用 `pip` 安裝相依套件):

```bash
pip install -r requirements.txt
```

## Usage (使用方法)

Run the script by passing the target file as an argument.
透過命令列執行腳本，並將目標檔案作為參數傳入。

```bash
python parse_document.py <input_file.pdf_or_docx>
```

**Example (範例)**:
```bash
python parse_document.py sample.pdf
```

## Output Structure (輸出結構)

After processing, an `output` folder will be generated in the same directory:
執行後，會在相同目錄下自動建立 `output` 資料夾：

```text
output/
├── toc.json          # JSON format table of contents (JSON 格式目錄)
├── index.md          # Markdown knowledge base index (Markdown 知識庫入口)
└── chunks/           # Folder containing all parsed markdown sections (存放所有解析出的 Markdown 區塊)
    ├── 1_Introduction.md
    ├── 1.1_Background.md
    └── ...
```

Each generated Markdown chunk looks like this:
每個生成的 Markdown 區塊大致長這樣：

```markdown
# 1.1 Background

metadata:
- source file: sample.pdf
- section number: 1.1
- page start: 3

content:
(Actual content of the section goes here... / 實際章節內容...)
```

## Advanced Configuration (進階設定)

You can customize the parsing logic directly within `parse_document.py`:
您可以在 `parse_document.py` 內直接修改以下參數以符合您的文件：

- `IGNORE_PATTERNS`: Add or remove regular expressions to ignore specific page noise (e.g., footers). (自訂要忽略的字串規則)
- `BAD_KEYWORDS`: Ignore sections containing specific keywords (e.g., "revision history"). (略過包含特定關鍵字的無效章節)
- `HEADING_REGEX`: Modify the regex if your document uses a different heading structure. (若文件標題結構不同，可調整此正規表達式)
