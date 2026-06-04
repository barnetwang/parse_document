import os
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
import database
import parse_document

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB Max Upload

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "css"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "js"), exist_ok=True)

# Initialize Database
database.init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/documents", methods=["GET"])
def get_documents():
    try:
        docs = database.list_documents()
        return jsonify({"success": True, "documents": docs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/documents/<int:doc_id>", methods=["GET"])
def get_document_details(doc_id):
    try:
        # Find the document in the list to check if it exists and get its metadata
        docs = database.list_documents()
        doc = next((d for d in docs if d["id"] == doc_id), None)
        if not doc:
            return jsonify({"success": False, "error": "Document not found"}), 404
            
        toc = database.get_document_toc(doc_id)
        return jsonify({"success": True, "document": doc, "toc": toc})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/chunks/<int:chunk_id>", methods=["GET"])
def get_chunk_details(chunk_id):
    try:
        chunk = database.get_chunk(chunk_id)
        if not chunk:
            return jsonify({"success": False, "error": "Chunk not found"}), 404
        return jsonify({"success": True, "chunk": chunk})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    doc_id_str = request.args.get("doc_id", "").strip()
    
    if not query:
        return jsonify({"success": True, "results": []})
        
    doc_id = None
    if doc_id_str:
        try:
            doc_id = int(doc_id_str)
        except ValueError:
            pass
            
    try:
        results = database.search_chunks(query, doc_id)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def delete_document_route(doc_id):
    try:
        filename = database.delete_document(doc_id)
        if not filename:
            return jsonify({"success": False, "error": "Document not found"}), 404
        return jsonify({"success": True, "message": f"Document '{filename}' deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in the request"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400
        
    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    if ext not in [".pdf", ".docx"]:
        return jsonify({"success": False, "error": "Unsupported file format. Only PDF and DOCX are allowed."}), 400
        
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    try:
        # Save uploaded file temporarily
        file.save(file_path)
        
        # Parse document
        if ext == ".pdf":
            lines = parse_document.extract_pdf_lines(file_path)
        elif ext == ".docx":
            lines = parse_document.extract_docx_lines(file_path)
            
        chunks = parse_document.parse_into_chunks(lines, filename)
        
        if not chunks:
            return jsonify({"success": False, "error": "No content could be extracted or parsed from the file."}), 400
            
        # Save to database and write physical chunk markdown files
        doc_id = database.save_document(filename, chunks)
        
        return jsonify({
            "success": True, 
            "document_id": doc_id, 
            "filename": filename, 
            "chunk_count": len(chunks)
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to parse and save document: {str(e)}"}), 500
    finally:
        # Clean up temp file in upload directory
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route("/output/<path:filepath>")
def serve_output_file(filepath):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    return send_from_directory(output_dir, filepath, as_attachment=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
