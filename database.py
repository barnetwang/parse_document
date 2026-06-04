import sqlite3
import os
from datetime import datetime

DATABASE_FILE = "documents.db"

def get_db_connection(db_path=DATABASE_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DATABASE_FILE):
    """Initialize the database tables if they do not exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            upload_time TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success'
        );
    """)
    
    # Create chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            section_number TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            page_start INTEGER NOT NULL,
            file_path TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        );
    """)
    
    conn.commit()
    conn.close()

def save_document(filename, chunks, db_path=DATABASE_FILE):
    """Save document metadata and its associated chunks into the database and write physical files."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        # Delete existing document if it has the same filename to avoid duplicates
        cursor.execute("SELECT id FROM documents WHERE filename = ?", (filename,))
        existing = cursor.fetchone()
        if existing:
            existing_id = existing['id']
            cursor.execute("DELETE FROM documents WHERE id = ?", (existing_id,))
            import shutil
            old_dir = os.path.join("output", str(existing_id))
            if os.path.exists(old_dir):
                shutil.rmtree(old_dir)
        
        # Insert document row
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO documents (filename, upload_time, chunk_count, status)
            VALUES (?, ?, ?, 'success')
        """, (filename, upload_time, len(chunks)))
        
        document_id = cursor.lastrowid
        
        # Create physical directory
        from pathlib import Path
        import shutil
        doc_dir = Path("output") / str(document_id)
        chunks_dir = doc_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        
        toc = {}
        
        # Insert chunks and write physical files
        for chunk in chunks:
            from parse_document import sanitize_filename
            number = chunk["number"]
            title = chunk["title"]
            clean_title = sanitize_filename(title)
            chunk_filename = f"{number}_{clean_title}.md" if number != "0" else f"0_{clean_title}.md"
            
            # Write physical chunk file
            filepath = chunks_dir / chunk_filename
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
                    "file": chunk_filename,
                    "title": title,
                    "page_start": chunk["page_start"],
                }
                
            db_file_path = f"output/{document_id}/chunks/{chunk_filename}"
            
            cursor.execute("""
                INSERT INTO chunks (document_id, section_number, title, content, page_start, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                number,
                title,
                chunk["content"],
                chunk["page_start"],
                db_file_path
            ))
            
        # Write toc.json for this document
        with open(doc_dir / "toc.json", "w", encoding="utf-8") as f:
            import json
            json.dump(toc, f, indent=2, ensure_ascii=False)
            
        # Generate index.md for this document
        generate_document_index_file(doc_dir, toc)
            
        conn.commit()
        return document_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def generate_document_index_file(doc_dir, toc):
    index_path = doc_dir / "index.md"
    
    def sort_key(k):
        return [int(x) for x in k.split('.') if x.isdigit()]
    
    sorted_keys = sorted(toc.keys(), key=sort_key)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# 📄 Document Knowledge Base\n\n")
        f.write("> 此目錄與文件區塊由自動化腳本生成，為後續 LLM 與 RAG 查詢使用。\n\n")

        f.write("## 📁 Directory Structure\n\n")
        f.write("```text\n")
        f.write("output/\n")
        f.write("└── chunks/\n")
        
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
            
            f.write(f"{indent}* [{k} {title}](chunks/{filename})\n")

def list_documents(db_path=DATABASE_FILE):
    """Retrieve list of all documents."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, filename, upload_time, chunk_count, status 
        FROM documents 
        ORDER BY upload_time DESC
    """)
    docs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return docs

def get_document_toc(document_id, db_path=DATABASE_FILE):
    """Get the table of contents (list of chunks without full content) for a document."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, section_number, title, page_start, file_path 
        FROM chunks 
        WHERE document_id = ?
    """, (document_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Sort section numbers correctly (e.g. 1.2.3 before 1.10)
    def parse_section_num(sec):
        parts = sec.split('.')
        result = []
        for p in parts:
            if p.isdigit():
                result.append(int(p))
            else:
                result.append(p)
        return result
        
    rows.sort(key=lambda r: parse_section_num(r['section_number']))
    return rows

def get_chunk(chunk_id, db_path=DATABASE_FILE):
    """Retrieve a single chunk with its document information."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.id, c.document_id, c.section_number, c.title, c.content, c.page_start, c.file_path, d.filename as document_name
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.id = ?
    """, (chunk_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def search_chunks(query, document_id=None, db_path=DATABASE_FILE):
    """Search for keywords in chunk titles and contents."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    sql = """
        SELECT c.id, c.document_id, c.section_number, c.title, c.page_start, c.file_path, d.filename as document_name,
               substr(c.content, 1, 200) as snippet
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE (c.title LIKE ? OR c.content LIKE ?)
    """
    params = [f"%{query}%", f"%{query}%"]
    
    if document_id is not None:
        sql += " AND c.document_id = ?"
        params.append(document_id)
        
    sql += " ORDER BY d.upload_time DESC, c.section_number ASC LIMIT 100"
    
    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # We can clean up snippet newlines
    for r in results:
        r['snippet'] = r['snippet'].replace('\n', ' ').strip() + '...'
        
    return results

def delete_document(document_id, db_path=DATABASE_FILE):
    """Delete a document, its chunks, and its physical files."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        # Get filename first
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        if not row:
            return None
        filename = row['filename']
        
        # Delete document row (foreign key constraint with ON DELETE CASCADE will handle deleting the chunks)
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        
        # Delete physical directory
        import shutil
        doc_dir = os.path.join("output", str(document_id))
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)
            
        return filename
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
