import os
import sys
import re
import json
import shutil
from pathlib import Path
import fitz
import pymupdf4llm
from docx import Document

# -----------------------------
# Config
# -----------------------------
OUTPUT_DIR = "output"
CHUNKS_DIR = "chunks"
VALID_MAJOR_RANGE = range(1, 100)

MD_HEADING_REGEX = re.compile(
    r'^(#+)\s*(?:\*\*\s*)?(.*?)(?:\s*\*\*)?$'
)

EXPLICIT_NUM_REGEX = re.compile(
    r'^(?:Chapter|Section)?\s*(\d+(?:\.\d+)*)\.?(?:[\s:-]+(.*))?$',
    re.IGNORECASE
)

TOC_IGNORE_REGEX = re.compile(r'\.{3,}\s*\d+$')
UNIT_ONLY_REGEX = re.compile(
    r'^\d+(?:\.\d+)?\s*(MHz|GHz|W|V|A|mV|mA|s|ns|ms|us|bytes|KB|MB|GB)$',
    re.IGNORECASE
)

IGNORE_PATTERNS = [
    re.compile(r'^AMD Confidential.*$', re.IGNORECASE),
    re.compile(r'^Page\s+\d+.*$', re.IGNORECASE),
    re.compile(r'^Overclocking Guidance for AMD Family.*$', re.IGNORECASE),
    re.compile(r'^Table of Contents$', re.IGNORECASE),
]

BAD_KEYWORDS = [
    "updated",
    "corrected",
    "release",
    "initial nda",
    "revision history",
]


# -----------------------------
# Heading & Section Number Tracker
# -----------------------------
class SectionNumberTracker:
    def __init__(self, max_depth=10):
        self.current_nums = [0] * max_depth

    def sync(self, section_num: str):
        """Synchronize tracker with an explicit section number (e.g., '1.2.3')."""
        parts = section_num.split('.')
        for i, part in enumerate(parts):
            if i < len(self.current_nums):
                try:
                    self.current_nums[i] = int(part)
                except ValueError:
                    self.current_nums[i] = 1  # Fallback
        # Reset subsequent levels
        for i in range(len(parts), len(self.current_nums)):
            self.current_nums[i] = 0

    def generate(self, level: int) -> str:
        """Generate a pseudo-section number for a given level (1-indexed)."""
        idx = level - 1
        if idx >= len(self.current_nums):
            idx = len(self.current_nums) - 1
            
        # Increment the target level
        self.current_nums[idx] += 1
        
        # Reset all sub-levels
        for i in range(idx + 1, len(self.current_nums)):
            self.current_nums[i] = 0
            
        # Construct the section number string
        parts = []
        for i in range(level):
            val = self.current_nums[i]
            if val == 0:
                self.current_nums[i] = 1
                val = 1
            parts.append(str(val))
            
        return ".".join(parts)


# -----------------------------
# Utilities
# -----------------------------
def is_ignored(line: str, is_markdown: bool = False) -> bool:
    clean_line = line.strip()
    
    if not clean_line:
        return not is_markdown 

    if TOC_IGNORE_REGEX.search(clean_line):
        return True

    for pattern in IGNORE_PATTERNS:
        if pattern.match(clean_line):
            return True

    if not is_markdown and re.match(r'^\d+$', clean_line):
        return True

    return False


def sanitize_filename(name: str) -> str:
    clean_name = name.replace('*', '').replace('#', '')
    return re.sub(r'[\\/*?:"<>|]', '', clean_name).replace(' ', '_')


# -----------------------------
# Heading validation
# -----------------------------
def is_valid_heading(section_num: str, title: str) -> bool:
    try:
        major = int(section_num.split('.')[0])
    except Exception:
        return False

    if major not in VALID_MAJOR_RANGE:
        return False

    # Heuristic: Real headings are rarely excessively long
    if len(title) > 120:
        return False

    # Heuristic: Real headings must contain some letters/numbers
    if not re.search(r'[a-zA-Z0-9\u4e00-\u9fa5]', title):
        return False

    full_line = f"{section_num} {title}".strip()
    if UNIT_ONLY_REGEX.match(full_line):
        return False

    if section_num.count('.') == 1:
        minor = section_num.split('.')[1]
        if len(minor) >= 2 and minor.startswith('0'):
            return False

    lowered = title.lower()
    for kw in BAD_KEYWORDS:
        if kw in lowered:
            return False

    return True


# -----------------------------
# Extractors
# -----------------------------
def extract_pdf_lines(file_path: str):
    doc = fitz.open(file_path)
    lines = []

    for page_index in range(len(doc)):
        page_num = page_index + 1
        page_md = pymupdf4llm.to_markdown(doc, pages=[page_index])

        for raw_line in page_md.splitlines():
            if not is_ignored(raw_line, is_markdown=True):
                lines.append((page_num, raw_line.rstrip()))

    doc.close()
    return lines


def is_bold_paragraph(para) -> bool:
    runs = [r for r in para.runs if r.text.strip()]
    if not runs:
        return False
    return all(run.bold for run in runs)


def extract_docx_lines(file_path: str):
    doc = Document(file_path)
    lines = []

    page_num = 1
    for para in doc.paragraphs:
        line = para.text.strip()
        if not line:
            continue

        # Convert paragraph styles to markdown headers
        if para.style and para.style.name:
            style_name = para.style.name
            if style_name.startswith('Heading '):
                try:
                    level = int(style_name.split(' ')[1])
                    line = '#' * level + ' ' + line
                except ValueError:
                    pass
            elif style_name == 'Title':
                line = '# ' + line
            elif style_name == 'Subtitle':
                line = '## ' + line
        # Fallback: if paragraph is short and entirely bold, treat as a heading
        elif len(line) < 80 and is_bold_paragraph(para):
            line = '## ' + line

        if not is_ignored(line, is_markdown=True):
            lines.append((page_num, line))

    return merge_split_headings(lines)


def merge_split_headings(lines):
    merged = []
    i = 0

    while i < len(lines):
        page_num, line = lines[i]

        if re.match(r'^\d+(\.\d+)*$', line) and i + 1 < len(lines):
            _, next_line = lines[i + 1]
            if not re.match(r'^\d+(\.\d+)*$', next_line):
                merged.append((page_num, f"{line} {next_line}"))
                i += 2
                continue

        merged.append((page_num, line))
        i += 1

    return merged


# -----------------------------
# Parser
# -----------------------------
def parse_into_chunks(lines, source_file):
    chunks = []

    current = {
        "number": "0",
        "title": "Introduction",
        "content": [],
        "page_start": 1,
    }

    tracker = SectionNumberTracker()

    for page_num, line in lines:
        clean_line = line.strip()
        
        is_heading = False
        section_num = ""
        title = ""

        # First try to match markdown headings
        md_match = MD_HEADING_REGEX.match(clean_line)
        if md_match:
            level = len(md_match.group(1))
            title_text = md_match.group(2).strip()
            
            # Clean title from any markdown decorators (e.g. bold/italic)
            title_text = re.sub(r'^[\*_#\s]+|[\*_#\s]+$', '', title_text).strip()
            
            # Check if title starts with explicit section number
            num_match = EXPLICIT_NUM_REGEX.match(title_text)
            if num_match:
                section_num = num_match.group(1)
                title = num_match.group(2) or "Overview"
                title = re.sub(r'^[\*_#\s]+|[\*_#\s]+$', '', title).strip()
                if is_valid_heading(section_num, title):
                    tracker.sync(section_num)
                    is_heading = True
            else:
                title = title_text
                section_num = tracker.generate(level)
                if is_valid_heading(section_num, title):
                    is_heading = True
        else:
            # Check if it has an explicit section number without markdown prefix
            num_match = EXPLICIT_NUM_REGEX.match(clean_line)
            if num_match:
                section_num = num_match.group(1)
                title = num_match.group(2) or "Overview"
                title = re.sub(r'^[\*_#\s]+|[\*_#\s]+$', '', title).strip()
                if is_valid_heading(section_num, title):
                    tracker.sync(section_num)
                    is_heading = True

        if is_heading:
            if current["content"] or current["number"] != "0":
                chunks.append({
                    "number": current["number"],
                    "title": current["title"],
                    "content": "\n".join(current["content"]).strip(),
                    "page_start": current["page_start"],
                    "source": source_file,
                })

            current = {
                "number": section_num,
                "title": title,
                "content": [],
                "page_start": page_num,
            }
            continue

        current["content"].append(line)

    chunks.append({
        "number": current["number"],
        "title": current["title"],
        "content": "\n".join(current["content"]).strip(),
        "page_start": current["page_start"],
        "source": source_file,
    })

    return chunks


# -----------------------------
# Index Generator
# -----------------------------
def generate_markdown_index(toc: dict):
    index_path = Path(OUTPUT_DIR) / "index.md"
    
    def sort_key(k):
        return [int(x) for x in k.split('.') if x.isdigit()]
    
    sorted_keys = sorted(toc.keys(), key=sort_key)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# 📄 Document Knowledge Base\n\n")
        f.write("> 此目錄與文件區塊由自動化腳本生成，為後續 LLM 與 RAG 查詢使用。\n\n")

        f.write("## 📁 Directory Structure\n\n")
        f.write("```text\n")
        f.write("output/\n")
        f.write("├── toc.json\n")
        f.write("├── index.md\n")
        f.write(f"└── {CHUNKS_DIR}/\n")
        
        for i, k in enumerate(sorted_keys):
            connector = "    └── " if i == len(sorted_keys) - 1 else "    ├── "
            f.write(f"{connector}{toc[k]['file']}\n")
        f.write("```\n\n")

        f.write("## 🔗 Section Index\n\n")
        for k in sorted_keys:
            title = toc[k]['title']
            filename = toc[k]['file']
            
            depth = k.count('.')
            indent = "  " * depth
            
            f.write(f"{indent}* [{k} {title}]({CHUNKS_DIR}/{filename})\n")


# -----------------------------
# Save output
# -----------------------------
def save_chunks(chunks):
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    chunks_dir = Path(OUTPUT_DIR) / CHUNKS_DIR
    chunks_dir.mkdir(parents=True, exist_ok=True)

    toc = {}

    for chunk in chunks:
        number = chunk["number"]
        title = chunk["title"]

        filename = f"{number}_{sanitize_filename(title)}.md"
        filepath = chunks_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {number} {title}\n\n")
            f.write("metadata:\n")
            f.write(f"- source file: {chunk['source']}\n")
            f.write(f"- section number: {number}\n")
            f.write(f"- page start: {chunk['page_start']}\n\n")
            f.write("content:\n")
            f.write(chunk["content"])

        if number != "0":
            toc[number] = {
                "file": filename,
                "title": title,
                "page_start": chunk["page_start"],
            }

    with open(Path(OUTPUT_DIR) / "toc.json", "w", encoding="utf-8") as f:
        json.dump(toc, f, indent=2, ensure_ascii=False)
        
    generate_markdown_index(toc)


# -----------------------------
# Main
# -----------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_document.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        sys.exit(1)

    ext = Path(input_file).suffix.lower()
    source_name = Path(input_file).name

    print(f"Parsing entire document {source_name}...")

    if ext == ".pdf":
        lines = extract_pdf_lines(input_file)
    elif ext == ".docx":
        lines = extract_docx_lines(input_file)
    else:
        print("Unsupported file type")
        sys.exit(1)

    chunks = parse_into_chunks(lines, source_name)
    save_chunks(chunks)

    print(f"Done. Generated {len(chunks)} chunks.")
    print(f"Please check ./output/index.md for the complete directory structure and section links.")


if __name__ == "__main__":
    main()