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
* Google Gemini API
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

## Installation

### Clone Repository

git clone 

cd financial-document-management-system

### Create Virtual Environment

python -m venv venv

### Activate Environment

Windows:

venv\Scripts\activate

### Install Dependencies

pip install -r requirements.txt

### Configure Environment Variables

Create a .env file and add:

GEMINI_API_KEY=your_api_key

JWT_SECRET_KEY=your_secret_key

### Run Application

python -m uvicorn main:app --reload

### Swagger Documentation

http://127.0.0.1:8000/docs

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
