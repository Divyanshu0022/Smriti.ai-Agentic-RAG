import os
import shutil
import time
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from utils.rag import (
    process_file, query_rag, query_direct_llm, query_long_context, 
    perform_document_audit, generate_summary, VECTOR_STORE_DIR, clear_cache
)
from utils.email_sender import send_email
from utils.evaluation import calculate_metrics, generate_tsne_plot
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, flash
from utils.database import (
    init_db, insert_document, get_all_documents, clear_all_documents,
    insert_summary, get_all_summaries,
    insert_query_log, get_query_history, get_query_stats, clear_query_logs,
    create_user, get_user_by_username, deduct_credit, add_credit_request,
    get_all_users, get_pending_credit_requests, resolve_credit_request, admin_assign_credits,
    get_all_blogs, insert_blog, delete_blog,
    get_user_by_email, get_user_by_google_id, update_user_otp, verify_user, update_user_password, get_user_by_id
)
from utils.profile_audit import audit_profile_and_save, get_profile_summary
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-super-secret-key-123')


# Initialize database
init_db()

# OAuth Configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GMAIL_CLIENT_ID'),
    client_secret=os.environ.get('GMAIL_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ─── Pages ────────────────────────────────────────────────────


# ─── Authentication ───

@app.route('/login', methods=['GET', 'POST'])
def login():
    blogs = get_all_blogs()
    if request.method == 'POST':
        identifier = request.form.get('username') # can be username or email
        password = request.form.get('password')
        
        user = get_user_by_username(identifier)
        if not user:
            user = get_user_by_email(identifier)
            
        if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
            if not user['is_verified'] and user['email']:
                flash("Please verify your email first.")
                return redirect(url_for('verify_otp', user_id=user['id']))
                
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['credits'] = user['credits']
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials", blogs=blogs)
    return render_template('login.html', blogs=blogs)

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    email = user_info['email']
    google_id = user_info['id']
    username = user_info.get('name', email.split('@')[0])

    user = get_user_by_google_id(google_id)
    if not user:
        # Check if user with this email exists
        user = get_user_by_email(email)
        if user:
            # Link google account? For simplicity, we just log them in
            pass
        else:
            uid = create_user(username=username, email=email, google_id=google_id, is_verified=1)
            user = get_user_by_id(uid)

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['credits'] = user['credits']
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        mobile = request.form.get('mobile')
        if not email or not username or not full_name or not mobile:
            return render_template('register.html', error="Missing fields")
            
        # Check if exists
        if get_user_by_email(email) or get_user_by_username(username):
            return render_template('register.html', error="User already exists")
            
        uid = create_user(username=username, email=email, is_verified=0, full_name=full_name, mobile=mobile)
        if uid:
            # Generate and send OTP
            otp = str(random.randint(100000, 999999))
            expiry = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
            update_user_otp(uid, otp, expiry)
            
            # Use email template
            email_res = send_email(
                to=email, 
                subject="Smriti.ai - Your Verification OTP", 
                content=f"Your Smriti.ai verification code is: {otp}. It expires in 10 minutes."
            )
            
            if email_res.get('success'):
                return redirect(url_for('verify_otp', user_id=uid))
            else:
                return render_template('register.html', error=f"Failed to send OTP email: {email_res.get('message')}. Please contact admin or check .env config.")
        return render_template('register.html', error="Registration failed")
    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = request.args.get('user_id') or request.form.get('user_id')
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        user = get_user_by_id(user_id)
        if user and user['otp'] == otp_input:
            # Check expiry
            if datetime.strptime(user['otp_expiry'], '%Y-%m-%d %H:%M:%S') > datetime.now():
                verify_user(user_id)
                return render_template('set_password.html', user_id=user_id)
            else:
                return render_template('verify_otp.html', user_id=user_id, error="OTP expired")
        return render_template('verify_otp.html', user_id=user_id, error="Invalid OTP")
    return render_template('verify_otp.html', user_id=user_id)

@app.route('/set_password', methods=['POST'])
def set_password():
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    if user_id and password:
        hash_pw = generate_password_hash(password)
        update_user_password(user_id, hash_pw)
        flash("Password set successfully! Please login.")
        return redirect(url_for('login'))
    return redirect(url_for('register'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET'])
@admin_required
def admin():
    users = get_all_users()
    requests = get_pending_credit_requests()
    blogs = get_all_blogs()
    return render_template('admin.html', users=users, reqs=requests, blogs=blogs)

@app.route('/api/admin/create_blog', methods=['POST'])
@admin_required
def create_blog():
    data = request.json
    title = data.get('title')
    content = data.get('content')
    if title and content:
        insert_blog(title, content)
        return jsonify({"success": True})
    return jsonify({"error": "Missing data"}), 400

@app.route('/api/admin/delete_blog', methods=['POST'])
@admin_required
def delete_blog_route():
    data = request.json
    blog_id = data.get('blog_id')
    delete_blog(blog_id)
    return jsonify({"success": True})

@app.route('/api/admin/assign_credits', methods=['POST'])
@admin_required
def assign_credits():
    data = request.json
    uid = data.get('user_id')
    amt = data.get('amount')
    if admin_assign_credits(uid, amt):
        return jsonify({"success": True})
    return jsonify({"error": "Failed"}), 500

@app.route('/api/admin/resolve_request', methods=['POST'])
@admin_required
def resolve_request():
    data = request.json
    req_id = data.get('request_id')
    status = data.get('status')
    if resolve_credit_request(req_id, status):
        return jsonify({"success": True})
    return jsonify({"error": "Failed"}), 500

@app.route('/api/request_credits', methods=['POST'])
@login_required
def request_credits():
    data = request.json
    amt = data.get('amount', 5)
    utr = data.get('utr_number')
    if not utr:
        return jsonify({"error": "UTR Number is required for verification."}), 400
    add_credit_request(session['user_id'], amt, utr)
    return jsonify({"success": True, "message": "Credit request submitted. Waiting for admin approval."})

@app.route('/payment')
@login_required
def payment():
    return render_template('payment.html')

@app.route('/api/profile_audit', methods=['POST'])
@login_required
def profile_audit():
    if not deduct_credit(session['user_id'], 5):
        return jsonify({'error': 'Insufficient credits. Profile Audit costs 5 credits.'}), 403
    
    result = audit_profile_and_save()
    if result['success']:
        return jsonify(result)
    return jsonify({"error": result['message']}), 500

@app.route('/profile_audit')
@login_required
def profile_audit_page():
    return render_template('profile_audit.html')

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/premium')
@login_required
def premium():
    if session.get('role') != 'admin' and session.get('credits', 0) < 1:
        return "Insufficient Credits. Please request credits from the admin to access Premium View.", 403
    return render_template('premium.html')

@app.route('/premium/about')
@login_required
def premium_about():
    return render_template('premium_about.html')

# ─── Chat API ─────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    if session.get('role') != 'admin':
        data = request.json
        mode = data.get('mode', 'rag')
        model_name = data.get('model', 'gemini-2.0-flash-lite-preview-02-05')
        if mode != 'rag' or 'lite' not in model_name.lower():
            if not deduct_credit(session['user_id'], 1):
                return jsonify({'error': 'Insufficient credits for premium features.'}), 403

    data = request.json
    query = data.get('query')
    mode = data.get('mode', 'rag')  # 'rag', 'direct', or 'long_context'
    model_name = data.get('model', 'gemini-2.0-flash-lite-preview-02-05')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        if mode == 'direct':
            response = query_direct_llm(query)
        elif mode == 'long_context':
            response = query_long_context(query, model_name=model_name)
        else:
            response = query_rag(user_query=query)
        
        # Log the query to SQLite
        avg_score = None
        if response.get('scores'):
            avg_score = sum(response['scores']) / len(response['scores'])
        
        insert_query_log(
            query=query,
            answer=response.get('answer', ''),
            num_chunks=len(response.get('chunks', [])),
            avg_score=avg_score,
            response_time_ms=response.get('response_time_ms'),
            mode=mode
        )
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat_stream', methods=['POST'])
@login_required
def chat_stream():
    if session.get('role') != 'admin':
        data = request.json
        mode = data.get('mode', 'rag')
        model_name = data.get('model', 'gemini-2.0-flash-lite-preview-02-05')
        if mode != 'rag' or 'lite' not in model_name.lower():
            if not deduct_credit(session['user_id'], 1):
                return jsonify({'error': 'Insufficient credits for premium features.'}), 403

    data = request.json
    query = data.get('query')
    mode = data.get('mode', 'rag')
    model_name = data.get('model', 'gemini-2.0-flash-lite-preview-02-05')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
        
    def generate():
        from utils.rag import query_rag_stream, query_direct_llm_stream, query_long_context_stream
        import json
        try:
            if mode == 'direct':
                metadata, chunk_generator = query_direct_llm_stream(query)
            elif mode == 'long_context':
                metadata, chunk_generator = query_long_context_stream(query, model_name=model_name)
            else:
                metadata, chunk_generator = query_rag_stream(query)
                
            # Log the query metadata
            avg_score = None
            if metadata.get('scores'):
                avg_score = sum(metadata['scores']) / max(1, len(metadata['scores']))
                
            insert_query_log(
                query=query,
                answer="[Streamed Response]",
                num_chunks=len(metadata.get('chunks', [])),
                avg_score=avg_score,
                response_time_ms=metadata.get('response_time_ms'),
                mode=mode
            )
            
            # Send chunks to the frontend as Server-Sent Events
            for chunk_text in chunk_generator:
                payload = json.dumps({"type": "chunk", "content": chunk_text})
                yield f"data: {payload}\n\n"
                
            # Finally, send metadata to render UI pills/context
            meta_payload = json.dumps({"type": "metadata", "data": metadata})
            yield f"data: {meta_payload}\n\n"
            
        except Exception as e:
            err_payload = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {err_payload}\n\n"
            
    from flask import Response
    return Response(generate(), mimetype='text/event-stream')

# ─── Upload API ───────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        
        try:
            # Process file and get chunks + full text
            chunks_count, full_text = process_file(filepath)
            
            # Generate summary using LLM
            summary = None
            try:
                summary = generate_summary(full_text)
            except Exception as e:
                print(f"Summary generation failed: {e}")
                summary = "Summary generation failed. The document has been indexed for search."
            
            # Store in SQLite
            doc_id = insert_document(filename, filepath, file_size, chunks_count, summary)
            if summary:
                insert_summary(doc_id, summary)
            
            return jsonify({
                "message": f"Successfully processed {chunks_count} chunks from '{filename}'!",
                "summary": summary,
                "doc_id": doc_id
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# ─── Knowledge Base Status ────────────────────────────────────

@app.route('/api/kb-status', methods=['GET'])
def kb_status():
    """Returns the number of documents currently stored in the FAISS vector store."""
    try:
        documents = get_all_documents()
        
        if not os.path.exists(VECTOR_STORE_DIR):
            return jsonify({"doc_count": 0, "file_count": len(documents), "status": "empty", "documents": documents})
        
        from langchain_community.vectorstores import FAISS
        from utils.rag import get_embeddings
        embeddings = get_embeddings()
        vector_store = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
        doc_count = len(vector_store.docstore._dict)
        return jsonify({
            "doc_count": doc_count,
            "file_count": len(documents),
            "status": "ready",
            "documents": documents
        })
    except Exception as e:
        return jsonify({"doc_count": 0, "status": "error", "error": str(e)})

@app.route('/api/clear-kb', methods=['POST'])
def clear_kb():
    """Clears the FAISS vector store, uploaded files, and database records."""
    try:
        if os.path.exists(VECTOR_STORE_DIR):
            shutil.rmtree(VECTOR_STORE_DIR)
        upload_dir = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_dir):
            for f in os.listdir(upload_dir):
                os.remove(os.path.join(upload_dir, f))
        # Clear database records
        clear_all_documents()
        clear_query_logs()
        clear_cache()
        return jsonify({"message": "Knowledge Base cleared successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Summaries API ────────────────────────────────────────────

@app.route('/api/summaries', methods=['GET'])
def summaries():
    """Returns all document summaries."""
    try:
        all_summaries = get_all_summaries()
        return jsonify({"summaries": all_summaries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Query History API ────────────────────────────────────────

@app.route('/api/query-history', methods=['GET'])
def query_history():
    """Returns recent query logs and stats."""
    try:
        history = get_query_history(limit=50)
        stats = get_query_stats()
        return jsonify({"history": history, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Evaluation API ───────────────────────────────────────────

@app.route('/api/evaluate', methods=['GET'])
def evaluate():
    metrics = calculate_metrics()
    plot_url = generate_tsne_plot(static_dir='static')
    return jsonify({
        "metrics": metrics,
        "plot_url": f"/static/{plot_url}" if plot_url else None
    })

# ─── Comparison API ───────────────────────────────────────────

@app.route('/api/compare', methods=['POST'])
def compare():
    """Runs the same query through RAG and Direct LLM for comparison."""
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        rag_response = query_rag(query)
        direct_response = query_direct_llm(query)
        
        return jsonify({
            "rag": rag_response,
            "direct": direct_response
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── New 'Rare' Features: Audit & Actions ─────────────────────

@app.route('/api/audit', methods=['POST'])
@login_required
def audit():
    if not deduct_credit(session['user_id'], 1):
        return jsonify({'error': 'Insufficient credits'}), 403

    """Performs specialized document auditing (Risk detection, Professional extraction)."""
    data = request.json
    audit_type = data.get('type', 'general')
    
    try:
        result = perform_document_audit(audit_type)
        return jsonify({"audit": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/action', methods=['POST'])
@login_required
def action():
    if not deduct_credit(session['user_id'], 1):
        return jsonify({'error': 'Insufficient credits'}), 403

    """
    Agentic action: send the AI-generated content as a real email via Gmail OAuth2.
    """
    data       = request.json
    action_type = data.get('action', 'email')
    content    = data.get('content', '').strip()
    recipient  = data.get('recipient', '').strip()
    subject    = data.get('subject', 'AI Knowledge Worker — Document Report')

    if not content:
        return jsonify({"error": "No content to send."}), 400
    if not recipient:
        return jsonify({"error": "No recipient email provided."}), 400

    if action_type == 'email':
        result = send_email(to=recipient, subject=subject, content=content)
        status_code = 200 if result['success'] else 500
        return jsonify({"message": result['message'], "success": result['success']}), status_code

    elif action_type == 'export':
        # Professional brief — same email with a different subject line
        result = send_email(
            to=recipient,
            subject='Professional Brief — AI Knowledge Worker',
            content=content
        )
        status_code = 200 if result['success'] else 500
        return jsonify({"message": result['message'], "success": result['success']}), status_code

    return jsonify({"error": f"Unknown action type: {action_type}"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
