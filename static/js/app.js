// State variables
let state = {
    documents: [],
    activeDocId: null,
    activeChunkId: null,
    activeTab: 'toc',
    deleteDocId: null
};

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const progressBar = document.getElementById('progress-bar');
const progressContainer = document.getElementById('progress-container');
const uploadStatus = document.getElementById('upload-status');
const docsList = document.getElementById('docs-list');
const docCountBadge = document.getElementById('doc-count');
const docFilterInput = document.getElementById('doc-filter');

// Tab elements
const tabTocBtn = document.getElementById('tab-toc-btn');
const tabSearchBtn = document.getElementById('tab-search-btn');
const tabToc = document.getElementById('tab-toc');
const tabSearch = document.getElementById('tab-search');

// TOC & Active Doc Info
const activeDocInfo = document.getElementById('active-doc-info');
const activeDocTitle = document.getElementById('active-doc-title');
const activeDocTime = document.getElementById('active-doc-time');
const activeDocChunks = document.getElementById('active-doc-chunks');
const tocTree = document.getElementById('toc-tree');

// Global Search
const globalSearchInput = document.getElementById('global-search-input');
const globalSearchBtn = document.getElementById('global-search-btn');
const searchCurrentOnly = document.getElementById('search-current-only');
const searchResultsList = document.getElementById('search-results-list');

// Reader Panel
const readerHeader = document.getElementById('reader-header');
const readerTitle = document.getElementById('reader-title');
const readerSecNum = document.getElementById('reader-sec-num');
const readerMeta = document.getElementById('reader-meta');
const readerMetaSource = document.getElementById('reader-meta-source');
const readerMetaPage = document.getElementById('reader-meta-page');
const readerBody = document.getElementById('reader-body');
const copyMarkdownBtn = document.getElementById('copy-markdown-btn');
const downloadChunkBtn = document.getElementById('download-chunk-btn');

// Confirm Modal
const confirmModal = document.getElementById('confirm-modal');
const confirmCancel = document.getElementById('confirm-cancel');
const confirmOk = document.getElementById('confirm-ok');

// Active Chunk Object (cache)
let activeChunkData = null;

// ==========================================================================
// Initialization & Event Listeners
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    fetchDocuments();
    setupUploadHandlers();
    setupTabHandlers();
    setupSearchHandlers();
    setupReaderActions();
    setupModalHandlers();

    // Setup filter/search on sidebar document list
    docFilterInput.addEventListener('input', (e) => {
        filterDocuments(e.target.value);
    });
});

// ==========================================================================
// API Operations
// ==========================================================================

// Fetch and render document list
async function fetchDocuments() {
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        if (data.success) {
            state.documents = data.documents;
            renderDocumentsList(data.documents);
            docCountBadge.textContent = data.documents.length;
        } else {
            showErrorNotification("無法載入文件列表: " + data.error);
        }
    } catch (err) {
        showErrorNotification("連接伺服器失敗: " + err.message);
    }
}

// Select a document to load its TOC
async function selectDocument(docId) {
    state.activeDocId = docId;
    
    // Set active class in sidebar
    document.querySelectorAll('.doc-item').forEach(el => {
        if (parseInt(el.dataset.id) === docId) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });

    try {
        const response = await fetch(`/api/documents/${docId}`);
        const data = await response.json();
        
        if (data.success) {
            // Update TOC panel UI
            const doc = data.document;
            activeDocTitle.textContent = doc.filename;
            activeDocTime.textContent = doc.upload_time;
            activeDocChunks.textContent = `${doc.chunk_count} 區塊`;
            activeDocInfo.style.display = 'block';
            
            renderTOC(data.toc);
            
            // Switch tab to TOC automatically
            switchTab('toc');
        } else {
            showErrorNotification("無法載入章節目錄: " + data.error);
        }
    } catch (err) {
        showErrorNotification("連接伺服器失敗: " + err.message);
    }
}

// Select a chunk to read
async function selectChunk(chunkId) {
    state.activeChunkId = chunkId;
    
    // Set active state in TOC UI
    document.querySelectorAll('.toc-item').forEach(el => {
        if (parseInt(el.dataset.id) === chunkId) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });

    // Set active state in search results if applicable
    document.querySelectorAll('.search-result-item').forEach(el => {
        if (parseInt(el.dataset.id) === chunkId) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });

    try {
        const response = await fetch(`/api/chunks/${chunkId}`);
        const data = await response.json();
        
        if (data.success) {
            const chunk = data.chunk;
            activeChunkData = chunk;
            
            // Render reader UI
            readerSecNum.textContent = chunk.section_number;
            readerTitle.textContent = chunk.title;
            readerMetaSource.textContent = chunk.document_name;
            readerMetaPage.textContent = chunk.page_start;
            
            readerHeader.style.display = 'flex';
            readerMeta.style.display = 'flex';
            
            // Generate Markdown HTML content
            readerBody.className = 'reader-body markdown-body';
            readerBody.innerHTML = marked.parse(chunk.content);
            
            // Update download button link
            downloadChunkBtn.href = `/${chunk.file_path}`;
            downloadChunkBtn.style.display = 'inline-flex';
            
            // Re-render lucide icons inside reader header
            lucide.createIcons();
            
            // Auto scroll to top of reader view
            readerBody.scrollTop = 0;
        } else {
            showErrorNotification("無法載入段落內容: " + data.error);
        }
    } catch (err) {
        showErrorNotification("連接伺服器失敗: " + err.message);
    }
}

// Global/Document Search
async function performSearch() {
    const query = globalSearchInput.value.trim();
    if (!query) return;
    
    let url = `/api/search?q=${encodeURIComponent(query)}`;
    if (searchCurrentOnly.checked && state.activeDocId) {
        url += `&doc_id=${state.activeDocId}`;
    }
    
    searchResultsList.innerHTML = `<div class="empty-state"><i data-lucide="loader" class="animate-spin"></i> 搜尋中...</div>`;
    lucide.createIcons();

    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            renderSearchResults(data.results);
        } else {
            searchResultsList.innerHTML = `<div class="empty-state text-danger">搜尋出錯: ${data.error}</div>`;
        }
    } catch (err) {
        searchResultsList.innerHTML = `<div class="empty-state text-danger">連接失敗: ${err.message}</div>`;
    }
}

// Delete Document
async function deleteDocument(docId) {
    try {
        const response = await fetch(`/api/documents/${docId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (data.success) {
            // Remove from list and reset UI if it was the active document
            state.documents = state.documents.filter(d => d.id !== docId);
            renderDocumentsList(state.documents);
            docCountBadge.textContent = state.documents.length;
            
            if (state.activeDocId === docId) {
                state.activeDocId = null;
                activeDocInfo.style.display = 'none';
                tocTree.innerHTML = `<div class="empty-state">請選擇左側文件以查看章節目錄</div>`;
                resetReaderPlaceholder();
            }
            
            showSuccessNotification("文件刪除成功！");
        } else {
            showErrorNotification("刪除失敗: " + data.error);
        }
    } catch (err) {
        showErrorNotification("連接伺服器失敗: " + err.message);
    }
}

// ==========================================================================
// Rendering Helpers
// ==========================================================================

// Render list of documents in the sidebar
function renderDocumentsList(docs) {
    if (docs.length === 0) {
        docsList.innerHTML = `<div class="empty-state">尚無上傳文件</div>`;
        return;
    }
    
    docsList.innerHTML = docs.map(doc => `
        <div class="doc-item ${state.activeDocId === doc.id ? 'active' : ''}" data-id="${doc.id}">
            <div class="doc-info">
                <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
                <div class="doc-meta">
                    <span>${doc.chunk_count} 段落</span>
                    <span>•</span>
                    <span>${formatTime(doc.upload_time)}</span>
                </div>
            </div>
            <button class="btn-delete" data-id="${doc.id}" title="刪除此文件與其段落">
                <i data-lucide="trash-2"></i>
            </button>
        </div>
    `).join('');
    
    lucide.createIcons();
    
    // Attach event listeners to document items
    document.querySelectorAll('.doc-item').forEach(el => {
        el.addEventListener('click', (e) => {
            // If delete button clicked, don't trigger select
            if (e.target.closest('.btn-delete')) return;
            const docId = parseInt(el.dataset.id);
            selectDocument(docId);
        });
    });

    // Attach event listeners to delete buttons
    document.querySelectorAll('.btn-delete').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            state.deleteDocId = parseInt(el.dataset.id);
            confirmModal.style.display = 'flex';
        });
    });
}

// Render TOC tree in the middle panel
function renderTOC(toc) {
    if (toc.length === 0) {
        tocTree.innerHTML = `<div class="empty-state">此文件無段落資訊</div>`;
        return;
    }
    
    tocTree.innerHTML = toc.map(chunk => `
        <div class="toc-item ${state.activeChunkId === chunk.id ? 'active' : ''}" data-id="${chunk.id}">
            <span class="toc-sec-num">${chunk.section_number}</span>
            <span class="toc-title" title="${chunk.title}">${chunk.title}</span>
        </div>
    `).join('');
    
    // Attach click listeners to TOC items
    document.querySelectorAll('.toc-item').forEach(el => {
        el.addEventListener('click', () => {
            const chunkId = parseInt(el.dataset.id);
            selectChunk(chunkId);
        });
    });
}

// Render search results in the middle panel
function renderSearchResults(results) {
    if (results.length === 0) {
        searchResultsList.innerHTML = `<div class="empty-state">找不到符合關鍵字的內容</div>`;
        return;
    }
    
    searchResultsList.innerHTML = results.map(res => `
        <div class="search-result-item ${state.activeChunkId === res.id ? 'active' : ''}" data-id="${res.id}">
            <div class="result-header">
                <span class="result-doc-name" title="${res.document_name}">${res.document_name}</span>
                <span class="result-sec-num">${res.section_number}</span>
            </div>
            <div class="result-title" title="${res.title}">${res.title}</div>
            <div class="result-snippet">${escapeHtml(res.snippet)}</div>
        </div>
    `).join('');
    
    // Attach click listeners to search results
    document.querySelectorAll('.search-result-item').forEach(el => {
        el.addEventListener('click', () => {
            const chunkId = parseInt(el.dataset.id);
            selectChunk(chunkId);
        });
    });
}

// Reset reader view to default blank state
function resetReaderPlaceholder() {
    readerHeader.style.display = 'none';
    readerMeta.style.display = 'none';
    readerBody.className = 'reader-body';
    readerBody.innerHTML = `
        <div class="reader-placeholder">
            <i data-lucide="book-open-check" class="placeholder-icon"></i>
            <h2>閱讀器</h2>
            <p>在左側章節目錄點擊任一章節，或使用全域搜尋，即可在此顯示結構化的 Markdown 內容與元資料。</p>
        </div>
    `;
    lucide.createIcons();
    activeChunkData = null;
}

// Filter document list based on sidebar input
function filterDocuments(query) {
    const cleanQuery = query.toLowerCase().trim();
    if (!cleanQuery) {
        renderDocumentsList(state.documents);
        return;
    }
    const filtered = state.documents.filter(doc => doc.filename.toLowerCase().includes(cleanQuery));
    renderDocumentsList(filtered);
}

// ==========================================================================
// Upload Handling Logic
// ==========================================================================
function setupUploadHandlers() {
    // Open file selector on click
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // Drag and drop events
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove('dragover');
        }, false);
    });

    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    }, false);
}

async function handleFileUpload(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pdf' && ext !== 'docx') {
        showErrorNotification("不支援的檔案格式！僅限 PDF 與 DOCX。");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    
    // UI Progress Show
    progressContainer.style.display = 'block';
    progressBar.style.width = '20%';
    uploadStatus.textContent = "上傳並解析中...";
    uploadZone.style.pointerEvents = 'none';

    try {
        progressBar.style.width = '50%';
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        progressBar.style.width = '90%';
        const data = await response.json();
        
        if (data.success) {
            progressBar.style.width = '100%';
            uploadStatus.textContent = "解析完成！";
            setTimeout(() => {
                progressContainer.style.display = 'none';
                uploadStatus.textContent = "";
                uploadZone.style.pointerEvents = 'auto';
            }, 1500);
            
            // Reload documents and select the newly uploaded one
            await fetchDocuments();
            selectDocument(data.document_id);
            showSuccessNotification(`成功解析並結構化 "${file.name}"！`);
        } else {
            throw new Error(data.error);
        }
    } catch (err) {
        progressContainer.style.display = 'none';
        uploadStatus.textContent = "";
        uploadZone.style.pointerEvents = 'auto';
        showErrorNotification(`解析失敗: ${err.message}`);
    }
}

// ==========================================================================
// Event Handler Helpers (Tabs, Search, Modal, Actions)
// ==========================================================================
function setupTabHandlers() {
    tabTocBtn.addEventListener('click', () => switchTab('toc'));
    tabSearchBtn.addEventListener('click', () => switchTab('search'));
}

function switchTab(tabName) {
    state.activeTab = tabName;
    if (tabName === 'toc') {
        tabTocBtn.classList.add('active');
        tabSearchBtn.classList.remove('active');
        tabToc.classList.add('active');
        tabSearch.classList.remove('active');
    } else {
        tabTocBtn.classList.remove('active');
        tabSearchBtn.classList.add('active');
        tabToc.classList.remove('active');
        tabSearch.classList.add('active');
        
        // Focus the search input
        setTimeout(() => globalSearchInput.focus(), 50);
    }
}

function setupSearchHandlers() {
    globalSearchBtn.addEventListener('click', performSearch);
    globalSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

function setupReaderActions() {
    // Copy Markdown to Clipboard
    copyMarkdownBtn.addEventListener('click', () => {
        if (!activeChunkData) return;
        const textToCopy = `# ${activeChunkData.section_number} ${activeChunkData.title}\n\nmetadata:\n- source file: ${activeChunkData.document_name}\n- section number: ${activeChunkData.section_number}\n- page start: ${activeChunkData.page_start}\n\ncontent:\n${activeChunkData.content}`;
        
        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalHTML = copyMarkdownBtn.innerHTML;
            copyMarkdownBtn.innerHTML = `<i data-lucide="check"></i> 已複製`;
            lucide.createIcons();
            copyMarkdownBtn.style.color = 'var(--accent)';
            setTimeout(() => {
                copyMarkdownBtn.innerHTML = originalHTML;
                lucide.createIcons();
                copyMarkdownBtn.style.color = '';
            }, 2000);
        }).catch(err => {
            showErrorNotification("複製失敗: " + err);
        });
    });
}

function setupModalHandlers() {
    confirmCancel.addEventListener('click', () => {
        confirmModal.style.display = 'none';
        state.deleteDocId = null;
    });
    
    confirmOk.addEventListener('click', () => {
        if (state.deleteDocId) {
            deleteDocument(state.deleteDocId);
        }
        confirmModal.style.display = 'none';
        state.deleteDocId = null;
    });

    // Close modal if user clicks background
    confirmModal.addEventListener('click', (e) => {
        if (e.target === confirmModal) {
            confirmModal.style.display = 'none';
            state.deleteDocId = null;
        }
    });
}

// ==========================================================================
// Global Utilities
// ==========================================================================
function formatTime(timeStr) {
    if (!timeStr) return '';
    // Format YYYY-MM-DD HH:MM:SS to MM/DD HH:MM
    try {
        const parts = timeStr.split(' ');
        const dateParts = parts[0].split('-');
        const timeParts = parts[1].split(':');
        return `${dateParts[1]}/${dateParts[2]} ${timeParts[0]}:${timeParts[1]}`;
    } catch (e) {
        return timeStr;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showSuccessNotification(message) {
    // Simple custom notification alert
    const alertDiv = document.createElement('div');
    alertDiv.style.position = 'fixed';
    alertDiv.style.bottom = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.backgroundColor = '#10b981';
    alertDiv.style.color = '#fff';
    alertDiv.style.padding = '12px 24px';
    alertDiv.style.borderRadius = '8px';
    alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.fontSize = '0.9rem';
    alertDiv.style.fontWeight = '500';
    alertDiv.style.animation = 'modalSlideIn 0.2s ease-out';
    alertDiv.textContent = message;
    
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transition = 'opacity 0.5s';
        setTimeout(() => alertDiv.remove(), 500);
    }, 3000);
}

function showErrorNotification(message) {
    const alertDiv = document.createElement('div');
    alertDiv.style.position = 'fixed';
    alertDiv.style.bottom = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.backgroundColor = '#ef4444';
    alertDiv.style.color = '#fff';
    alertDiv.style.padding = '12px 24px';
    alertDiv.style.borderRadius = '8px';
    alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.fontSize = '0.9rem';
    alertDiv.style.fontWeight = '500';
    alertDiv.style.animation = 'modalSlideIn 0.2s ease-out';
    alertDiv.textContent = message;
    
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transition = 'opacity 0.5s';
        setTimeout(() => alertDiv.remove(), 500);
    }, 4000);
}
