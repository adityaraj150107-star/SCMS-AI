# SCMS_AI — Smart College Management System (Flask + FastAPI + SQLite + AI)

SCMS_AI is a local-development college management project with a Flask web UI, FastAPI REST API, SQLite persistence, role-based access, academic workflows and an AI chat agent. The AI can use a local Ollama model or optional Gemini API.

## Requirements
- Python 3.11 or newer
- Windows + VS Code recommended
- Ollama installed for local AI (optional if using Gemini)
- SMTP credentials for real OTP/email delivery; Twilio credentials for real SMS delivery

## Setup on Windows / VS Code
1. Extract the ZIP and open the `SCMS_AI` folder in VS Code.
2. Copy `backend\.env.example` to `backend\.env` and set a strong `FLASK_SECRET_KEY`, `JWT_SECRET`, `BOOTSTRAP_ADMIN_EMAIL`, and `BOOTSTRAP_ADMIN_PASSWORD`.
3. In a PowerShell terminal:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend\requirements.txt
   ```
4. For local AI, install Ollama from https://ollama.com and run:
   ```powershell
   ollama pull llama3.2
   ```
   Ollama normally runs in the background. If needed, start it with `ollama serve` in another terminal.
5. Terminal 1 — FastAPI backend:
   ```powershell
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
6. Terminal 2 — Flask UI:
   ```powershell
   py app.py
   ```
7. Open `http://127.0.0.1:5000`. API docs are at `http://127.0.0.1:8000/docs`.

## First login
The Main Admin is bootstrapped from `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in `.env` when the database is first initialized. Sign in using those values. The database file defaults to `scms_ai.db` in the folder from which you launch the FastAPI command (normally the project root).

## OTP and delivery configuration
- Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM` for real email OTP delivery. Gmail generally requires an App Password.
- `DEV_SHOW_OTP=true` allows local development to return an OTP in the API response message if SMTP delivery fails. This is for local testing only. Set `DEV_SHOW_OTP=false` before any shared or production deployment.
- Optional SMS uses Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`. Recipient phone numbers should include the country code. SMS is not sent unless valid credentials and phone numbers are configured.
- Delivery attempts and statuses are recorded in the notifications table; a queued/failed message is not proof that a provider delivered it.

## Included workflows
- Sign in, public student/faculty signup, OTP verification, account switching by signing in to another account
- Separate UI capabilities for Student, Faculty and Main Admin
- Course, semester and subject catalogue; notices and role-targeted notifications
- Student enrollment, attendance, marks, assignments/submissions and timetable APIs/UI
- Admin user creation, role updates and activation/deactivation
- AI chat with saved per-user history, quick prompts, optional voice input/output, PDF/DOCX/TXT upload and image preview. Text extraction for image OCR requires optional Tesseract installed on the machine; without it, image preview still works but image contents are not interpreted by the model.
- Responsive sidebar, animated panels, mobile layouts and dashboard counters

## Important honest limitations
This is a functional local project foundation, not a certified production ERP. Before using real student data or exposing it to the internet, add a security review, HTTPS, CSRF protection, stronger session/token management, backups, audit/retention policies, rate limiting and institution-specific authorization rules. OTP/email/SMS delivery depends on provider configuration. AI does not automatically modify academic records; official changes are made through the relevant forms/API. Image preview works, but full vision-model image reasoning is not included in the current chat API. Faculty/admin workflows are intended for local demonstration and need institution-specific permissions and testing.
