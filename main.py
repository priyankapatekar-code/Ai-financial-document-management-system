from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import os
import re
import hashlib
import time
import shutil
from datetime import datetime, timedelta, timezone
from jose import jwt , JWTError
from fastapi import UploadFile, File
import chromadb
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException
from app import db
from app import config
from app.config import SECRET_KEY, ALGORITHM
from app.security import hash_password, verify_password, is_hashed
from app.pdf_utils import extract_text, PdfProblem
from app import llm

# Persistent vector store: embeddings are kept on disk and survive restarts.
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(
    name="financial_documents"
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)

app = FastAPI()

@app.get("/test-gemini")
def test_gemini():
    return {
        "answer": llm.generate("What is a financial report?")
    }
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str
class UserLogin(BaseModel):
    email: str
    password: str

class SearchRequest(BaseModel):
    query: str

class DocumentMetadata(BaseModel):
    title: str
    company_name: str
    document_type: str

def get_current_user(token: str = Depends(oauth2_scheme)):
    
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    
@app.get("/")
def home():
    return {"message": "Hello Priyanka"}

VALID_ROLES = {"admin", "financial_analyst", "auditor", "client"}


def create_token(email: str, role: str) -> str:
    return jwt.encode(
        {
            "email": email,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(hours=config.TOKEN_EXPIRE_HOURS)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def check_password_and_upgrade(conn, row, password: str) -> bool:
    """Verify the password; silently upgrade legacy plain-text passwords to hashes."""
    if not verify_password(password, row[3]):
        return False
    if not is_hashed(row[3]):
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(password), row[0]))
        conn.commit()
    return True


@app.post("/auth/register")
def register(user: UserRegister):

    if user.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Choose one of: " + ", ".join(sorted(VALID_ROLES))
        )
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    conn = sqlite3.connect("database.db")
    try:
        cursor = conn.cursor()
        # Security: anyone could otherwise sign up as admin. Only the very first user may be admin.
        if user.role == "admin":
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] > 0:
                raise HTTPException(
                    status_code=403,
                    detail="Admin accounts can only be created for the first user. Ask an existing admin."
                )
        try:
            cursor.execute(
                """
                INSERT INTO users (username, email, password, role)
                VALUES (?, ?, ?, ?)
                """,
                (user.username, user.email, hash_password(user.password), user.role)
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="This email is already registered")
        conn.commit()
    finally:
        conn.close()
    return {
        "message": "Data received",
        "user": {"username": user.username, "email": user.email, "role": user.role}
    }

@app.post("/auth/login")
def login(user: UserLogin):

    conn = sqlite3.connect("database.db")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (user.email,)
        )
        result = cursor.fetchone()
        # Same message for both cases so emails can't be probed.
        if result is None or not check_password_and_upgrade(conn, result, user.password):
            raise HTTPException(status_code=401, detail="Wrong email or password")
    finally:
        conn.close()

    return {
        "access_token": create_token(user.email, result[4]),
        "token_type": "bearer"
     }

@app.post("/token")
def token_login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    conn = sqlite3.connect("database.db")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (form_data.username,)
        )
        result = cursor.fetchone()
        if result is None or not check_password_and_upgrade(conn, result, form_data.password):
            raise HTTPException(
                status_code=401,
                detail="Wrong email or password"
            )
    finally:
        conn.close()

    return {
        "access_token": create_token(result[2], result[4]),
        "token_type": "bearer"
    }

@app.get("/test")
def test(current_user = Depends(get_current_user)):
    return {
        "message": "Token is valid",
        "user": current_user
    }
    
def _safe_name(name: str) -> str:
    base = os.path.basename((name or "document.pdf").replace("\\", "/"))
    return re.sub(r"[^\w.\- ]", "_", base)[:120] or "document.pdf"


def _stored_path(content_hash, file_name):
    """Where an uploaded file lives on disk. Hash prefix prevents name collisions."""
    if content_hash:
        return os.path.join("uploads", f"{content_hash[:16]}_{_safe_name(file_name)}")
    return os.path.join("uploads", _safe_name(file_name))  # legacy rows


@app.post("/documents/upload")
def upload_document(
    title: str,
    company_name: str,
    document_type: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only Admin can upload documents"
        )

    os.makedirs("uploads", exist_ok=True)

    # 1. Save to a temp file while hashing and enforcing the size limit.
    tmp_path = os.path.join("uploads", f"tmp_{time.time_ns()}.pdf")
    sha = hashlib.sha256()
    size = 0
    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    too_big = False
    with open(tmp_path, "wb") as buffer:
        while True:
            block = file.file.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > limit:
                too_big = True
                break
            sha.update(block)
            buffer.write(block)
    if too_big:
        os.remove(tmp_path)
        raise HTTPException(413, f"File too large (max {config.MAX_UPLOAD_MB} MB)")
    content_hash = sha.hexdigest()

    # 2. Validate the PDF and extract text BEFORE touching the database.
    try:
        text = extract_text(tmp_path)
    except PdfProblem as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=422, detail=e.message)

    conn = sqlite3.connect("database.db")
    try:
        # 3. Reject exact duplicates (same content, any filename).
        existing = conn.execute(
            "SELECT id, title FROM documents WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f'This file was already uploaded as "{existing[1]}" (id {existing[0]}).'
            )

        file_name = _safe_name(file.filename)
        file_path = _stored_path(content_hash, file_name)
        os.replace(tmp_path, file_path)

        # 4. DB row + embeddings; roll both back if either fails so they stay consistent.
        doc_id = None
        try:
            cur = conn.execute(
                """
                INSERT INTO documents
                (title, company_name, document_type, uploaded_by, created_at, file_name, content_hash)
                VALUES (?, ?, ?, ?, datetime('now'), ?, ?)
                """,
                (title, company_name, document_type, current_user["email"], file_name, content_hash)
            )
            doc_id = cur.lastrowid
            chunks = [text[i:i+500] for i in range(0, len(text), 500)]
            collection.add(
                documents=chunks,
                ids=[f"doc{doc_id}_chunk{i+1}" for i in range(len(chunks))],
                metadatas=[{"doc_id": doc_id, "title": title} for _ in chunks]
            )
            conn.commit()
        except Exception:
            conn.rollback()
            if doc_id is not None:
                try:
                    collection.delete(where={"doc_id": doc_id})
                except Exception:
                    pass
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail="Could not index the document. Nothing was saved.")
    finally:
        conn.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {
        "message": "File saved successfully",
        "filename": file.filename,
        "document_id": doc_id,
        "chunks_created": len(chunks)
    }

@app.post("/documents/search")

def search_documents(
    request: SearchRequest,
    current_user = Depends(get_current_user)
):
    if current_user["role"] not in [
        "admin",
        "financial_analyst",
        "auditor"
    ]:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
       )

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Please enter a question")

    count = collection.count()
    if count == 0:
        return {"answer": "No documents have been uploaded yet, so there is nothing to search."}

    results = collection.query(
        query_texts=[request.query],
        n_results=min(5, count)
    )

    context = results["documents"][0]
    reranked_context = "\n".join(context[:2])

    answer = llm.generate(
        f"""
        Context:
        {reranked_context}

        Question:
        {request.query}

        Answer using only the provided context.
        """
    )

    return {
        "answer": answer
    }

@app.get("/documents")
def get_documents(
    current_user=Depends(get_current_user)
):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM documents"
    )

    documents = cursor.fetchall()

    conn.close()

    return {
        "documents": documents
    }
@app.get("/documents/{document_id}")
def get_document_by_id(
    document_id: int,
    current_user=Depends(get_current_user)
):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    )

    document = cursor.fetchone()

    conn.close()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return {
        "document": document
    }
@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only Admin can delete documents"
        )

    conn = sqlite3.connect("database.db")
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,)
        )

        document = cursor.fetchone()

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        # Remove embeddings first: if this fails the DB row is kept and nothing is out of sync.
        try:
            collection.delete(where={"doc_id": document_id})
        except Exception:
            raise HTTPException(status_code=500, detail="Could not remove the document's embeddings")

        path = _stored_path(document[7], document[6])
        if os.path.exists(path):
            os.remove(path)

        cursor.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,)
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "message": "Document deleted successfully"
    }


# --- Simple web interface (added; does not change the API above) ---
from fastapi.staticfiles import StaticFiles

os.makedirs("uploads", exist_ok=True)
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
