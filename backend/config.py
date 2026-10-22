import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
DB=os.getenv("DATABASE_PATH","scms_ai.db")
JWT_SECRET=os.getenv("JWT_SECRET","change-this-jwt-secret")
OLLAMA_URL=os.getenv("OLLAMA_BASE_URL","http://localhost:11434")
OLLAMA_MODEL=os.getenv("OLLAMA_MODEL","llama3.2")
GEMINI_KEY=os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
SMTP_HOST=os.getenv("SMTP_HOST","");SMTP_PORT=int(os.getenv("SMTP_PORT","587"))
SMTP_USER=os.getenv("SMTP_USER","");SMTP_PASSWORD=os.getenv("SMTP_PASSWORD","");SMTP_FROM=os.getenv("SMTP_FROM",SMTP_USER)

DEV_SHOW_OTP=os.getenv("DEV_SHOW_OTP","true").lower()=="true"
