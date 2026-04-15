# Smriti.ai: A Flagship Agentic AI Platform for Persistent Organizational Memory

## 1. Executive Vision
**Title:** Smriti.ai — Agentic RAG with Gemini 2.5 Pro, Secure Auth & UPI Credit Economy  
**Developer:** Divyanshu (MithilaStack)  
**Technology:** Google Gemini 2.5 Pro · FAISS · Flask · SQLite · Gmail OAuth2 · Google Sheets API

Smriti.ai is a final-year B.Tech CSE project that demonstrates a production-grade Agentic AI platform. It goes beyond a simple chatbot — featuring a secure multi-stage authentication system, an autonomous agent ecosystem powered by **Gemini 2.5 Pro** (Google's most capable model), a human-in-the-loop UPI credit economy, and deep integrations with Google Sheets and Gmail APIs.

---

## 2. System Architecture

| Reasoning | Context-aware generation & agentic tasks | **Gemini 2.5 Pro** |
| Persistence | User data, sessions, credits, query logs | SQLite3 (WAL) |
| Auth & API | Unified OAuth2 (Gmail + Sheets) | **Google Cloud Platform** |
| Config Mgmt | Environment-based vaulting | **.env (Dotenv)** |
| Integrations | Email dispatch & HR profile storage | Gmail API + Google Sheets API |

### B. Authentication Architecture (Secure Identity System)

Smriti.ai implements a multi-stage secure registration system designed to verify human users and prevent bot registrations through mandatory email validation:

**Secure Registration & Verification:**
1. **Identity Input**: User submits **Full Name**, **Username**, **Email**, and **Mobile Number**.
2. **Email Verification**: An OTP (6-digit, 1-minute validity for re-send, 10-minute session expiry) is dispatched via the integrated Gmail API.
3. **Validation**: User enters the received OTP. Upon success, they proceed to set a secure password.
4. **Access**: Login is managed via hashed password verification using `werkzeug.security`.

**Google Sign-In (Roadmap):** 
While the architecture is pre-configured for Google OAuth2, the UI for this feature is currently set to "Future Update" to prioritize the secure manual identity verification flow.

### C. Agentic Workflow Engine (Gemini 2.5 Pro)

All audit agents are powered by **Gemini 2.5 Pro**, ensuring the highest reasoning capability:

1. **Legal Audit Agent** — Audits documents against Indian IT Act 2000 and DPDP Act 2023. Identifies Section 43A data protection violations, intermediary due diligence gaps, similar court precedents, and delivers a Pro/Con summary for the document owner.

2. **Risk Audit Agent** — Scans uploaded documents for 5 highest-priority red flags: missing clauses, liability ambiguities, regulatory non-compliance, and security vulnerabilities.

3. **Profile Audit Agent (Google Sheets Integration)** — Extracts structured candidate data (Full Name, Experience, Top Skills, LinkedIn/Social, LLM Summary) from uploaded resumes and automatically appends to the configured Google Sheet for HR management.

4. **Email Agent** — Compiles AI-generated reports and dispatches them as premium branded HTML emails via Gmail OAuth2 API.

5. **Document Summarization Agent** — Auto-generates concise summaries on every document upload using long-context Gemini processing.

---

## 3. Credit Economy & UPI Payment Flow

Smriti.ai implements a transparent, human-in-the-loop credit system:

```
User selects credit amount (₹1 = 1 Credit, min ₹5) →
Dynamic UPI QR code generated (linked to admin UPI VPA) →
User pays via any UPI app →
User submits 12-digit UTR number →
Admin reviews UTR in dashboard →
Admin approves → Credits added to user account
```

This demonstrates a real-world fintech pattern: payment gateway with manual verification, audit trail, and role-based approval workflows.

---

## 4. Premium UI/UX Design

- **Glassmorphic Dark Theme**: Frosted glass cards on deep dark backgrounds with teal accent (`#66FCF1`).
- **Animated Particle Canvas**: tsParticles for dynamic background atmosphere.
- **Space Grotesk + Inter Typography**: Premium Google Fonts for professional readability.
- **Premium Auth Journey**: Distinct premium pages for Login, Register, OTP Verify, and Password Setup — each with consistent brand language.
- **Responsive Chat Interface**: Streaming-ready message rendering with Markdown support, source attribution badges, and timing metadata.

---

## 5. Database Schema

### `users` Table
| Column | Type | Purpose |
|:---|:---|:---|
| `full_name` | TEXT | Legal name of the user |
| `mobile` | TEXT | 10-digit mobile number |
| `email` | TEXT UNIQUE | Primary identity for OTP verification |
| `is_verified` | INTEGER (0/1) | Status flag (1 after OTP verification) |
| `otp` | TEXT | Active verification code |
| `otp_expiry` | TIMESTAMP | 10-minute validity window |
| `google_id` | TEXT | Reserved for future OAuth linking |
| `password_hash` | TEXT NULLABLE | BCrypt-hashed credentials |
| `credits` | INTEGER | Starts with 5 free credits |

### `credit_requests` Table
| Column | Type | Purpose |
|:---|:---|:---|
| `utr_number` | TEXT | 12-digit payment reference for admin verification |
| `status` | TEXT | `pending` → `approved` / `rejected` |

---

## 6. Key Technical Achievements

1. **Zero Hallucination Design**: RAG strictly grounds responses in uploaded documents. If the answer isn't in the KB, the system explicitly states this.

2. **PII Detection**: A regex-based security layer scans all LLM outputs and flags SSNs, high-volume emails, and phone numbers.

3. **Response Cache**: MD5-keyed in-memory cache (10-min TTL, 100-entry LRU) reduces redundant LLM calls.

4. **Retrieval Evaluation**: Built-in MRR and NDCG@4 metrics with t-SNE embedding space visualization for academic rigor.

5. **Environment-Driven Configuration**: Adheres to industry best practices by externalizing all sensitive IDs (Gmail Clients, Spreadsheet IDs) into `.env`, ensuring code portability and security.

6. **Schema Migration Safety**: SQLite ALTER TABLE wrapped in try-except blocks allows safe schema evolution without data loss.

---

## 7. Project Directory Structure

Smriti.ai is organized according to modular engineering standards:

- **`agents/`**: Contains autonomous agentic logic (Email Dispatch, Profile Auditing).
- **`utils/`**: Core RAG pipeline, database management, and evaluation metrics.
- **`scripts/`**: One-off diagnostic and OAuth2 setup utilities.
- **`docs/`**: Technical documentation, roadmap, and project reports.
- **`templates/` & `static/`**: High-end glassmorphic UI components.

---

## 8. Conclusion

Smriti.ai is a demonstration of production-level engineering discipline applied to a college project context. By integrating Gemini 2.5 Pro's reasoning capabilities with a secure multi-path authentication system, a transparent UPI-based payment economy, Google Sheets HR integration, and thorough retrieval evaluation metrics, it stands as a comprehensive capstone of modern AI engineering.

---
**Report Generated By:** Antigravity AI (Claude Sonnet 4.6)  
**Model Used:** Gemini 2.5 Pro (Google DeepMind)  
**Last Updated:** April 14, 2026
