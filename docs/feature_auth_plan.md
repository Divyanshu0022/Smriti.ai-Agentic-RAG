# Implementation Plan: Advanced Authorization, Explainability, and Security

This plan outlines the steps to add user authentication, a credit system, explainability features, and security features without breaking the current architecture. It also details the documentation updates for future "risky" features.

## 1. Database Schema Updates (Non-Destructive)
We need to update `utils/database.py` with tables for Users and Credit Requests.
- **`users` table**: `id`, `username`, `password_hash`, `role` (admin/user), `credits` (default 0 or small amount).
- **`credit_requests` table**: `id`, `user_id`, `amount`, `status` (pending/approved/rejected).
- **Initialization**: Update `init_db()` to create these tables safely using `IF NOT EXISTS` and insert a default admin account on startup if none exists.

## 2. Authentication & Authorization Middleware
- Import `werkzeug.security` for password hashing and verification.
- Implement Flask sessions (`app.secret_key` will be required) to track logged-in users.
- Add `@login_required` and `@admin_required` decorators in `app.py`.
- **Credit Enforcement**: Only allow access to `/premium`, `/api/action` (email sender), and usage of advanced LLM models if the user has sufficient credits. Each of these actions will deduct a credit.
- Provide routes for `/login`, `/register`, and `/logout`.

## 3. Safe Feature Enhancements (Explainability & Security)
- **PII / Toxicity Detector (Security & Ethics)**: Add a simple function in `utils/rag.py` to scan the AI's output for potential sensitive data (regex for SSNs, excessive emails) or generate an alert before returning it to the frontend.
- **Explainability Layer**: Modify the Frontend UI to extract and highlight the "similarity score" (Confidence meter) returned by the RAG backend, and update the UI to visualize it.

## 4. Admin Dashboard
- Create `templates/admin.html` with a matching aesthetic.
- Add routes in `app.py` for `/admin` to view users, view pending credit requests, and assign credits.
- Users can request credits via a modal or button on the premium page or their dashboard.

## 5. Documentation Updates
- Update `README.md`, `templates/about.html`, and `templates/premium_about.html` to reflect these new features (Admin Login, Credit System, Explainability, PII Detection).
- Explicitly put the risky features into a "Future Work" section in the documentation:
  - Multi-Agent Orchestration
  - Knowledge Graph Integration
  - Offline/Low-Resource Mode

## User Review Required
> [!IMPORTANT]
> - **Cost of Actions**: I propose that standard document uploading and basic RAG are free, but accessing the Premium portal, sending Emails, using Audit features, and switching to Pro models will cost credits. Does this sound right?
> - **Default Admin**: I will create a default admin account (`admin` / `admin`). You can change this later.
> - **Approval**: Approving this plan will let me begin writing the frontend screens and database logic.
