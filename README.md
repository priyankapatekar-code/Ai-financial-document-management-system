# Financial Document Management System

## Overview

A FastAPI-based Financial Document Management System that enables secure document upload, semantic search, and AI-powered question answering over financial documents using Retrieval-Augmented Generation (RAG).

The system supports authentication, role-based access control, document storage, vector search with ChromaDB, and answer generation using Google Gemini.

---

## Features

* User Registration and Login
* JWT Authentication
* Role-Based Access Control (Admin, Financial Analyst, Auditor, Client)
* PDF Upload and Storage
* PDF Text Extraction using pypdf
* Text Chunking
* ChromaDB Vector Storage
* Semantic Search
* Retrieval-Augmented Generation (RAG)
* Gemini-based Answer Generation
* Document Metadata Storage in SQLite
* Document Listing and Retrieval
* Document Deletion

---

## Technology Stack

* FastAPI
* Python
* SQLite
* ChromaDB
* Google Gemini API (google-genai SDK)
* JWT Authentication
* pypdf

---

## System Architecture

User Login
→ JWT Authentication
→ Role-Based Access Control
→ PDF Upload
→ Text Extraction
→ Text Chunking
→ ChromaDB Storage
→ Semantic Search
→ Retrieve Relevant Chunks
→ Basic Reranking
→ Gemini LLM
→ Answer Generation

---

## API Endpoints

### Authentication

* POST /auth/register
* POST /auth/login
* POST /token

### Documents

* POST /documents/upload
* POST /documents/search
* GET /documents
* GET /documents/{document_id}
* DELETE /documents/{document_id}

---

## Installation (Windows PowerShell)

```powershell
# 1. Go to the project folder
cd "C:\Users\YourName\Downloads\Ai-financial-document-management-system-main"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1
# If PowerShell blocks the script, run once:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Install dependencies
pip install -r requirements.txt
```

### Configure environment variables

```powershell
Copy-Item .env.example .env
notepad .env
```

| Variable | What to put |
|---|---|
| `LLM_PROVIDER` | `gemini` (default) or `openrouter` |
| `GEMINI_API_KEY` | Free key from https://aistudio.google.com/apikey (when provider is `gemini`) |
| `OPENROUTER_API_KEY` | Key from https://openrouter.ai/keys (when provider is `openrouter`) |
| `OPENROUTER_MODEL` | Model ID, e.g. `meta-llama/llama-3.3-70b-instruct:free` (free models end in `:free`) |
| `SECRET_KEY` | A long random string. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | `HS256` |

Optional: `GEMINI_MODEL` (default `gemini-2.5-flash`), `TOKEN_EXPIRE_HOURS` (default 8), `MAX_UPLOAD_MB` (default 25).

The app refuses to start with a clear message if `SECRET_KEY` or `ALGORITHM` is missing. If `GEMINI_API_KEY` is missing the app starts, but AI answers return a "not configured" error. `.env` is git-ignored - never commit it.

### Run (always from the project folder)

```powershell
python -m uvicorn main:app --reload
```

* Web interface: http://127.0.0.1:8000/ui
* API docs (Swagger): http://127.0.0.1:8000/docs

The first upload/search downloads a ~80 MB embedding model (one time, needs internet).

### Data stored locally (all git-ignored)

* `database.db` - users and document records (SQLite)
* `chroma_db/` - persistent embeddings (survive restarts)
* `uploads/` - uploaded PDFs

### First use

1. **Create account** in the web interface. The **first** account may choose the role **Admin**; later sign-ups cannot self-register as admin.
2. Admin uploads text-based PDFs. Exact duplicate files (same content) are rejected.
3. Admin / Financial analyst / Auditor can ask questions; Clients can only list documents.

### Optional: OCR for scanned PDFs

Scanned/image-only PDFs are rejected with a clear message unless OCR is installed:
install the Tesseract program, then `pip install pytesseract pillow`.

---

## Testing

The application was tested end-to-end for:

* User Registration
* User Login
* JWT Authentication
* PDF Upload
* Metadata Storage
* ChromaDB Ingestion
* Semantic Search
* RAG Retrieval
* Gemini Answer Generation
* Document Retrieval
* Document Deletion

---

## Future Improvements

* Advanced Reranking
* Hybrid Search (Keyword + Semantic)
* Docker Deployment
* PostgreSQL Integration
* Audit Logging
* Multi-document Querying
* Background Processing
* Cloud Storage Integration

---

## Author

Priyanka Patekar
BE Computer Science
AI/ML Enthusiast
