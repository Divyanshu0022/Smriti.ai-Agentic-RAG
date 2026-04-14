import sqlite3
import os
from datetime import datetime

DB_PATH = "knowledge_base.db"

def get_db():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Creates all required tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Documents table — stores metadata about uploaded files
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_size INTEGER,
            chunk_count INTEGER DEFAULT 0,
            summary TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Query logs table — tracks all user queries and responses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            answer TEXT,
            num_chunks_retrieved INTEGER DEFAULT 0,
            avg_similarity_score REAL,
            response_time_ms INTEGER,
            mode TEXT DEFAULT 'rag',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Summaries table — stores per-document summaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            summary_text TEXT NOT NULL,
            word_count INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT DEFAULT NULL,
            role TEXT DEFAULT 'user',
            credits INTEGER DEFAULT 5,
            is_verified INTEGER DEFAULT 0,
            otp TEXT DEFAULT NULL,
            otp_expiry TIMESTAMP DEFAULT NULL,
            google_id TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Blogs table for SEO and Landing page content
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT DEFAULT 'Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Credit requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            utr_number TEXT DEFAULT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Migration: Add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
    except: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
    except: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN otp TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN otp_expiry TIMESTAMP")
    except: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE credit_requests ADD COLUMN utr_number TEXT")
    except: pass
    # Also adjust password_hash to be nullable for Google-only users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT NULL") # SQLite doesn't support MODIFY
    except: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT") 
    except: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN mobile TEXT") 
    except: pass
    
    conn.commit()
    
    # Insert default admin if no users exist
    user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash('admin')
        cursor.execute("INSERT INTO users (username, password_hash, role, credits) VALUES (?, ?, 'admin', 9999)", ('admin', admin_hash))
        conn.commit()

    # Insert default blogs if none exist
    blog_count = cursor.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
    if blog_count == 0:
        default_blogs = [
            ("The Evolution of RAG: From Keyword to Vector Search", 
             "Retrieval-Augmented Generation (RAG) has transformed how we interact with LLMs. Originally, systems relied on keyword matching, but the shift to dense vector embeddings with FAISS and HNSW has enabled semantic understanding. This allows models to find contextually relevant information even when exact keywords don't match, significantly reducing hallucinations and improving factual accuracy in domain-specific tasks.", 
             "Admin"),
            ("Agentic RAG: The Next Frontier in AI Architecture", 
             "Traditional RAG is passive—it retrieves and then generates. Agentic RAG introduces iterative reasoning. An agent can decide if the retrieved context is sufficient, perform multi-hop retrieval across different data sources, or even use tools to verify facts. This shift from 'chains' to 'agents' makes AI knowledge workers much more robust for legal and technical document analysis.", 
             "Admin"),
            ("Hybrid Search Strategies for Enterprise Knowledge Bases", 
             "While vector search is powerful, it can fail on specific acronyms or unique IDs. Hybrid search combines the semantic depth of dense embeddings with the lexical precision of BM25 (keyword search). By reranking these results, systems achieve the best of both worlds, ensuring that 'Nvidia H100' finds the exact datasheet while also understanding general queries about high-performance GPUs.", 
             "Admin")
        ]
        cursor.executemany("INSERT INTO blogs (title, content, author) VALUES (?, ?, ?)", default_blogs)
        conn.commit()
        
    conn.close()

# ─── User & Credit Operations ───────────────────────────────────

def get_user_by_username(username):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username, password_hash=None, email=None, role='user', credits=5, google_id=None, is_verified=0, full_name=None, mobile=None):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, credits, google_id, is_verified, full_name, mobile) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, role, credits, google_id, is_verified, full_name, mobile))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None  # Username or Email exists
    finally:
        conn.close()

def update_user_otp(user_id, otp, expiry):
    conn = get_db()
    conn.execute("UPDATE users SET otp = ?, otp_expiry = ? WHERE id = ?", (otp, expiry, user_id))
    conn.commit()
    conn.close()

def verify_user(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET is_verified = 1, otp = NULL, otp_expiry = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_google_id(google_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_password(user_id, password_hash):
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()

def deduct_credit(user_id, amount=1):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = credits - ? WHERE id = ? AND credits >= ?", (amount, user_id, amount))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def add_credit_request(user_id, amount, utr_number=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO credit_requests (user_id, amount, utr_number) VALUES (?, ?, ?)", (user_id, amount, utr_number))
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return req_id

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT id, username, role, credits, created_at FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_credit_requests():
    conn = get_db()
    rows = conn.execute("""
        SELECT cr.id, cr.user_id, cr.amount, cr.status, cr.created_at, cr.utr_number, u.username
        FROM credit_requests cr
        JOIN users u ON cr.user_id = u.id
        WHERE cr.status = 'pending'
        ORDER BY cr.created_at ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def resolve_credit_request(request_id, status_val):
    # status_val should be 'approved' or 'rejected'
    conn = get_db()
    cursor = conn.cursor()
    
    # Get request
    req = cursor.execute("SELECT * FROM credit_requests WHERE id = ?", (request_id,)).fetchone()
    if req and req['status'] == 'pending':
        cursor.execute("UPDATE credit_requests SET status = ? WHERE id = ?", (status_val, request_id))
        
        if status_val == 'approved':
            cursor.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (req['amount'], req['user_id']))
            
        conn.commit()
        success = True
    else:
        success = False
        
    conn.close()
    return success

def admin_assign_credits(user_id, amount):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return True


def insert_document(filename, filepath, file_size, chunk_count, summary=None):
    """Inserts a new document record and returns its ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (filename, filepath, file_size, chunk_count, summary) VALUES (?, ?, ?, ?, ?)",
        (filename, filepath, file_size, chunk_count, summary)
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def get_all_documents():
    """Returns all uploaded documents."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_document_by_id(doc_id):
    """Returns a single document by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def clear_all_documents():
    """Deletes all document records."""
    conn = get_db()
    conn.execute("DELETE FROM documents")
    conn.execute("DELETE FROM summaries")
    conn.commit()
    conn.close()

# ─── Summary Operations ──────────────────────────────────────

def insert_summary(document_id, summary_text):
    """Inserts an auto-generated summary for a document."""
    word_count = len(summary_text.split())
    conn = get_db()
    conn.execute(
        "INSERT INTO summaries (document_id, summary_text, word_count) VALUES (?, ?, ?)",
        (document_id, summary_text, word_count)
    )
    # Also update the document's summary field
    conn.execute(
        "UPDATE documents SET summary = ? WHERE id = ?",
        (summary_text, document_id)
    )
    conn.commit()
    conn.close()

def get_all_summaries():
    """Returns all summaries joined with document info."""
    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.summary_text, s.word_count, s.generated_at,
               d.filename, d.chunk_count
        FROM summaries s
        JOIN documents d ON s.document_id = d.id
        ORDER BY s.generated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Query Log Operations ────────────────────────────────────

def insert_query_log(query, answer, num_chunks=0, avg_score=None, response_time_ms=None, mode='rag'):
    """Logs a user query and its response."""
    conn = get_db()
    conn.execute(
        "INSERT INTO query_logs (query, answer, num_chunks_retrieved, avg_similarity_score, response_time_ms, mode) VALUES (?, ?, ?, ?, ?, ?)",
        (query, answer, num_chunks, avg_score, response_time_ms, mode)
    )
    conn.commit()
    conn.close()

def get_query_history(limit=50):
    """Returns the most recent queries."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM query_logs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_query_stats():
    """Returns aggregate statistics about queries."""
    conn = get_db()
    stats = {}
    
    row = conn.execute("SELECT COUNT(*) as total, AVG(response_time_ms) as avg_time, AVG(avg_similarity_score) as avg_score FROM query_logs").fetchone()
    stats['total_queries'] = row['total']
    stats['avg_response_time_ms'] = round(row['avg_time'], 1) if row['avg_time'] else 0
    stats['avg_similarity_score'] = round(row['avg_score'], 4) if row['avg_score'] else 0
    
    # Top queries 
    top = conn.execute("""
        SELECT query, COUNT(*) as count FROM query_logs 
        GROUP BY query ORDER BY count DESC LIMIT 5
    """).fetchall()
    stats['top_queries'] = [{'query': r['query'], 'count': r['count']} for r in top]
    
    conn.close()
    return stats

def clear_query_logs():
    """Deletes all query logs."""
    conn = get_db()
    conn.execute("DELETE FROM query_logs")
    conn.commit()
    conn.close()

# ─── Blog Operations ──────────────────────────────────────────

def insert_blog(title, content, author='Admin'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO blogs (title, content, author) VALUES (?, ?, ?)", (title, content, author))
    blog_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return blog_id

def get_all_blogs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM blogs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_blog(blog_id):
    conn = get_db()
    conn.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
    conn.commit()
    conn.close()
    return True

# Initialize database on import
init_db()
