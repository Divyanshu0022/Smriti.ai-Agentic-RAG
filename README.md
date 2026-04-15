# 🧠 Smriti.ai — Next-Gen Agentic RAG Platform

**Smriti.ai** is a flagship Agentic AI platform for *Persistent Organizational Memory*. It transforms static documents into a reasoning-capable assistant that retrieves context from user-uploaded PDFs and text files using **Gemini 2.5 Pro** and **FAISS** vector search — minimizing hallucinations while offering enterprise-grade agentic workflows.

---

## 🏗️ System Architecture

Smriti.ai follows a **Multi-Stage Agentic RAG Pipeline**:

1.  **Ingestion Layer**: Recursive character splitting with semantic overlap preserves context integrity.
2.  **Vector Layer**: **Google Gemini Neural Embeddings** (`gemini-embedding-001`) + **FAISS** for sub-second semantic retrieval.
3.  **Persistence Layer**: **SQLite (WAL Mode)** — user management, query history, credit transactions.
4.  **Reasoning Layer**: **Gemini 2.5 Pro** — the highest-quality model for in-depth legal, profile, and document analysis.
5.  **Agentic Layer**: Specialized agents for Legal Compliance, Profile Auditing, Document Risk Detection, and Gmail-powered Email Dispatch.
### 🔐 Secure Authentication System
- **Secure Registration**: Users provide **Full Name**, **Username**, **Email**, and **Mobile Number**.
- **Email/OTP Verification**: Instant 6-digit OTP sent via Gmail API to verify user identity before account creation.
- **Login**: Secure access via Username or Email with hashed password verification.
- **Role-Based Access**: Dedicated **Admin** (`admin`/`admin`) and **User** roles with credit-scoped permissions.
- **Google Sign-In**: *Planned for future update* (currently disabled in UI).

### 🤖 Agentic Workflows (Gemini 2.5 Pro Powered)
| Agent | Function | Credit Cost |
|:---|:---|:---|
| **Legal Audit Agent** | Indian IT Act 2000 & DPDP 2023 compliance review, risk flags, case precedents | 1 Credit |
| **Risk Audit Agent** | Document red-flag detection, missing clauses, liability analysis | 1 Credit |
| **Profile Audit Agent** | Resume parsing → structured extraction → auto-sync to Google Sheets | 5 Credits |
| **Email Agent** | Send AI-generated reports via Gmail OAuth2 API | 1 Credit |
| **Summarization Agent** | Auto-generates concise summaries on document upload | Free |

### 💳 UPI Credit System (Human-in-the-Loop)
- Dynamic UPI QR code generation (₹1 = 1 Credit, min 5 Credits).
- Users submit their 12-digit UTR number after payment.
- Admin verifies and approves credit requests from the dashboard.

### 🏢 Admin Dashboard
- User management & credit assignment.
- Pending credit request queue with **UTR number display** for verification.
- Blog/SEO content management.

### 📊 RAG Intelligence
- **Standard RAG Mode**: FAISS vector retrieval → Gemini generation with source attribution.
- **Long Context Mode**: Bypasses vector DB, feeds entire document corpus to Gemini.
- **Direct LLM Mode**: No-RAG baseline for comparison.
- **Compare Mode**: Side-by-side RAG vs Direct LLM output.
- **t-SNE Visualization**: Embedding cluster map for knowledge graph exploration.
- **MRR & NDCG Metrics**: Retrieval quality evaluation built-in.

---

## 🛠️ Technology Stack

| Category | Technology |
|:---|:---|
| **Backend** | Python 3.10+, Flask |
| **AI Core** | Google Gemini 2.5 Pro (Generation), Gemini Embedding-001 |
| **Vector DB** | FAISS (Dense Semantic Retrieval) |
| **Auth** | Google OAuth2 (Authlib), Email/OTP via Gmail API |
| **Database** | SQLite3 (WAL Mode) |
| **Frontend** | HTML5, Vanilla CSS (Glassmorphism), JavaScript ES6+ |
| **Integrations** | Gmail API & Google Sheets API (Unified OAuth2) |

---

## 🚀 Setup & Execution

### 1. Prerequisites
- **Python 3.10+**
- A **Google Cloud Project** with the following APIs enabled:
  - Gmail API
  - Google Sheets API

### 2. Google Cloud Configuration
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project named `Smriti-AI`.
3. Enable **Gmail API** and **Google Sheets API**.
4. Configure the **OAuth Consent Screen** (External) and add your email as a test user.
5. Create **OAuth 2.0 Client IDs** (Desktop Application).
6. Download your `Client ID` and `Client Secret`.

### 3. Environment Setup
Copy `.env.example` to `.env` and fill in your credentials:
```env
GOOGLE_API_KEY=your_gemini_api_key
GMAIL_CLIENT_ID=your_oauth_client_id
GMAIL_CLIENT_SECRET=your_oauth_client_secret
GMAIL_SENDER_EMAIL=you@gmail.com
GOOGLE_SHEETS_ID=your_spreadsheet_id
```

### 4. Install Requirements
```bash
pip install -r requirements.txt
```

### 5. Generate Refresh Token (Unified Setup)
Run this utility once to authorize both Gmail and Google Sheets access. This will automatically update your `.env` with the `GMAIL_REFRESH_TOKEN`:
```bash
python setup_gmail_token.py
```

### 6. Run Application
```bash
python app.py
```
Navigate to `http://localhost:5000/`

### 4. Run Application
```bash
python app.py
```
Navigate to `http://localhost:5000/`

**Default Admin:** username `admin`, password `admin`

---

## 📁 Project Structure & File Guide

```
major_project/
├── app.py                  # Main Flask Server: Routing, API endpoints, and session logic.
├── requirements.txt        # Dependencies: Flask, Gemini, FAISS, LangChain.
├── .env                    # Configuration: Secure storage for API keys and OAuth tokens.
├── knowledge_base.db       # Database: SQLite file storing users, query logs, and credits.
├── faiss_index/            # Vector Storage: Persisted semantic embeddings.
├── agents/                 # Specialized Agentic Workers
│   ├── email_sender.py     # Gmail Agent: Dispatches premium HTML reports via OAuth2.
│   ├── profile_audit.py    # Sheets Agent: HR parsing and automated Google Sheets sync.
│   └── __init__.py         # Package manifest.
├── utils/                  # Core RAG & Logic
│   ├── rag.py              # RAG Pipeline: Ingestion, Chunking, and Gemini reasoning.
│   ├── database.py         # DB Operations: User, Credit, and Blog management.
│   └── evaluation.py       # Metrics Layer: MRR/NDCG and t-SNE visualizations.
├── scripts/                # Utility & Setup Scripts
│   ├── setup_gmail_token.py # Unified OAuth2 setup for Gmail and Sheets.
│   └── debug_sheets.py     # Diagnostics for Google Sheets integration.
├── docs/                   # Project Documentation
│   ├── report.md           # Comprehensive technical project report.
│   ├── skills.md           # Project roadmap and skills breakdown.
│   └── feature_auth_plan.md# Authentication system architecture.
├── templates/              # UI Layer (Jinja2 Templates)
└── static/                 # Frontend Assets (CSS/JS/Images)
```

---

## 🔮 Future Roadmap
- **Multi-Modal RAG**: Support images and charts inside PDFs.
- **Cross-Document Reasoning**: Compare facts across multiple documents.
- **Real-Time Notifications**: Email/SMS alerts on credit approval.
- **Slack/Discord Bot**: Deploy Smriti.ai as an enterprise assistant.
