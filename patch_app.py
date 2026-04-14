import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports for Auth
imports = """from functools import wraps
from flask import session, redirect, url_for, flash
import werkzeug.security
from utils.database import (
    create_user, get_user_by_username, deduct_credit, add_credit_request,
    get_all_users, get_pending_credit_requests, resolve_credit_request, admin_assign_credits
)
"""
content = content.replace("from dotenv import load_dotenv", imports + "from dotenv import load_dotenv")

# Add secret key config
secret_config = """
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-super-secret-key-123')
"""
content = content.replace("os.makedirs('static', exist_ok=True)", "os.makedirs('static', exist_ok=True)\n" + secret_config)

# Add Auth Decorators
decorators = """
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
"""
content = content.replace("# ─── Pages ────────────────────────────────────────────────────", decorators + "\n# ─── Pages ────────────────────────────────────────────────────")

# Add Auth Routes
auth_routes = """
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user_by_username(username)
        if user and werkzeug.security.check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['credits'] = user['credits']
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('register.html', error="Missing fields")
            
        hash_pw = werkzeug.security.generate_password_hash(password)
        uid = create_user(username, hash_pw)
        if uid:
            return redirect(url_for('login'))
        return render_template('register.html', error="Username already exists")
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET'])
@admin_required
def admin():
    users = get_all_users()
    requests = get_pending_credit_requests()
    return render_template('admin.html', users=users, reqs=requests)

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
    add_credit_request(session['user_id'], amt)
    return jsonify({"success": True})
"""
content = "".join(content.split("@app.route('/')", 1)[0]) + auth_routes + "\n@app.route('/')" + "".join(content.split("@app.route('/')", 1)[1])

# Apply login_required to Premium
content = content.replace("def premium():", "@login_required\ndef premium():")
content = content.replace("def premium_about():", "@login_required\ndef premium_about():")

# Apply Credit Checks to Audit and Action Api
content = re.sub(
    r"(@app\.route\('/api/audit', methods=\['POST'\]\)\n)def audit\(\):",
    r"\1@login_required\ndef audit():\n    if not deduct_credit(session['user_id'], 1):\n        return jsonify({'error': 'Insufficient credits'}), 403\n",
    content
)
content = re.sub(
    r"(@app\.route\('/api/action', methods=\['POST'\]\)\n)def action\(\):",
    r"\1@login_required\ndef action():\n    if not deduct_credit(session['user_id'], 1):\n        return jsonify({'error': 'Insufficient credits'}), 403\n",
    content
)

# Apply Credit check conditionally to Chat if mode != rag or model is advanced
chat_check = """@login_required
def chat():
    if session.get('role') != 'admin':
        data = request.json
        mode = data.get('mode', 'rag')
        model_name = data.get('model', 'gemini-2.0-flash-lite-preview-02-05')
        if mode != 'rag' or 'lite' not in model_name.lower():
            if not deduct_credit(session['user_id'], 1):
                return jsonify({'error': 'Insufficient credits for premium features.'}), 403
"""
content = re.sub(r"def chat\(\):", chat_check, content, count=1)

chat_stream_check = """@login_required
def chat_stream():
    if session.get('role') != 'admin':
        data = request.json
        mode = data.get('mode', 'rag')
        model_name = data.get('model', 'gemini-2.0-flash-lite-preview-02-05')
        if mode != 'rag' or 'lite' not in model_name.lower():
            if not deduct_credit(session['user_id'], 1):
                return jsonify({'error': 'Insufficient credits for premium features.'}), 403
"""
content = re.sub(r"def chat_stream\(\):", chat_stream_check, content, count=1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("App patched successfully!")
