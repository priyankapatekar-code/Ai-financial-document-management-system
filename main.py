from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from dotenv import load_dotenv
import os
from jose import jwt , JWTError
from fastapi import UploadFile, File
import shutil
from pypdf import PdfReader
import chromadb
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException
import google.generativeai as genai
from app import db
#import app.db
client = chromadb.Client()
collection = client.create_collection(
    name="financial_documents"
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)

app = FastAPI()

@app.get("/test-gemini")
def test_gemini():

    model = genai.GenerativeModel("gemini-2.5-flash")

    response = model.generate_content(
        "What is a financial report?"
    )

    return {
        "answer": response.text
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

@app.post("/auth/register")
def register(user: UserRegister):
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
    """
    INSERT INTO users (username, email, password, role)
    VALUES (?, ?, ?, ?)
    """,
    (user.username, user.email, user.password, user.role)
    )
    conn.commit()
    return {
        "message": "Data received",
        "user": user
    }
@app.post("/auth/login")    
def login(user: UserLogin):
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (user.email,)
    )
    result = cursor.fetchone()
    if result is None:
        return {"message": "User not found"}


    if user.password != result[3]:
        return {"message": "Wrong password"}

    token = jwt.encode(
        {
        "email": user.email,
        "role": result[4]
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
     }

@app.post("/token")
def token_login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (form_data.username,)
    )

    result = cursor.fetchone()

    if result is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if form_data.password != result[3]:
        raise HTTPException(
            status_code=401,
            detail="Wrong password"
        )

    token = jwt.encode(
        {
            "email": result[2],
            "role": result[4]
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/test")
def test(current_user = Depends(get_current_user)):
    return {
        "message": "Token is valid",
        "user": current_user
    }
    
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
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
        conn = sqlite3.connect("database.db")
        
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents
        (title, company_name, document_type, uploaded_by, created_at, file_name)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
        """,
        (
            title,
            company_name,
            document_type,
            current_user["email"],
            file.filename
        )
    )

    conn.commit()
    conn.close()

    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text

    print("Text length:", len(text))
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    for i, chunk in enumerate(chunks):
        collection.add(
        documents=[chunk],
        ids=[f"{file.filename}_chunk{i+1}"]
        )
    print("Number of chunks:", len(chunks))
    

    return {
        "message": "File saved successfully",
        "filename": file.filename,
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
    

    results = collection.query(
        query_texts=[request.query],
        n_results=5
    )

    context = results["documents"][0]
    reranked_context = "\n".join(context[:2])
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    response = model.generate_content(
        f"""
        Context:
        {reranked_context}
 
        Question:
        {request.query}

        Answer using only the provided context.
        """
    )
    
    return {
        "answer": response.text
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
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    )

    document = cursor.fetchone()

    if document is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    cursor.execute(
        "DELETE FROM documents WHERE id = ?",
        (document_id,)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Document deleted successfully"
    }