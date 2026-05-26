# Document Parser for LLM & RAG (文件解析工具)

This Python script is designed to parse `.pdf` and `.docx` documents and split them into structured, chunked Markdown files based on section headings. It is highly optimized for preparing documentation for Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) systems.

本 Python 腳本專為解析 `.pdf` 與 `.docx` 文件所設計，能夠依據章節標題將文件切割並轉換為結構化的 Markdown 檔案。此工具非常適合用於為大型語言模型 (LLM) 以及檢索增強生成 (RAG) 系統準備知識庫文件。

---

## Features (功能特色)

- **Multi-Format Support (支援多格式)**: Parses both `.pdf` (using `pymupdf4llm`) and `.docx` (using `python-docx`) files.
- **Intelligent Chunking (智慧分塊)**: Automatically identifies headings and splits content into logical sections. Seamlessly supports **numbered, unnumbered, and hybrid** documents by dynamically generating pseudo-section numbers (e.g., `1.1`, `1.2`) based on heading depth while synchronizing with explicit ones.
  - **支援無編號與混合型文件**：會依標題層級（如 `#` 的數量）自動生成偽章節編號，並在遇到原有編號時自動同步計數器。
- **Word Formatting Support (Word 結構辨識)**: Automatically converts Word Heading styles (`Heading 1-9`, `Title`, `Subtitle`) into standard Markdown headers. Includes a bold-paragraph fallback to capture unstyled bold headers as document sections.
  - **自動轉換 Word 標題樣式**：能自動將 Word 的標題樣式或短粗體段落轉化為 Markdown 標題以進行切割。
- **Metadata Extraction (元資料萃取)**: Each chunk includes metadata such as the source file name, section number, and starting page.
- **Noise Filtering (過濾雜訊)**: Automatically ignores common page noise like "Table of Contents", headers/footers, "Page X", or confidential stamps. Optimized specifically for BIOS specs (e.g., ignoring timing/voltage measurements like `3.3 V`, `500 ns`).
- **Index Generation (生成目錄)**: Automatically creates a `toc.json` and a beautifully structured `index.md` linking to all generated chunks.

---

## Installation (安裝說明)

1. Clone or download this repository. (下載或複製此專案)
2. Install the required dependencies using `pip`. (使用 `pip` 安裝相依套件):

```bash
pip install -r requirements.txt
```

---

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

---

## Running Tests (執行單元測試)

A comprehensive unit test suite has been added to ensure robust parsing logic across numbered, unnumbered, and hybrid documents, as well as timing/voltage measurement exclusions.
專案內含完整的單元測試，可用於驗證編號、無編號、混合文件以及硬體參數過濾的解析邏輯。

```bash
python test_parser.py
```

---

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

---

## Advanced Configuration (進階設定)

You can customize the parsing logic directly within `parse_document.py`:
您可以在 `parse_document.py` 內直接修改以下參數以符合您的文件：

- `IGNORE_PATTERNS`: Add or remove regular expressions to ignore specific page noise (e.g., footers). (自訂要忽略的字串規則)
- `BAD_KEYWORDS`: Ignore sections containing specific keywords (e.g., "revision history"). (略過包含特定關鍵字的無效章節)
- `MD_HEADING_REGEX`: Matches markdown headings and extracts level and text. (用於識別 Markdown 標題與層級的正規表達式)
- `EXPLICIT_NUM_REGEX`: Identifies explicit section numbers to synchronize the counter. (用於匹配顯式編號的正規表達式)
- `UNIT_ONLY_REGEX`: Filters out typical measurements to avoid false-positive headings. (過濾電壓與時間單位的正規表達式)
