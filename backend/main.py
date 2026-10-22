from fastapi import FastAPI
from backend.database import init_db
from backend.routes import auth, academic, admin, ai, notifications, student
app=FastAPI(title="SCMS_AI API",version="1.0.0")
@app.on_event("startup")
def startup():init_db()
@app.get("/")
def root():return {"message":"SCMS_AI FastAPI running","docs":"/docs"}
@app.get("/health")
def health():return {"status":"ok"}
app.include_router(auth.router,prefix="/auth",tags=["Authentication"])
app.include_router(academic.router,prefix="/academic",tags=["Academic"])
app.include_router(admin.router,prefix="/admin",tags=["Admin"])
app.include_router(ai.router,prefix="/ai",tags=["AI Agent"])
app.include_router(notifications.router,prefix="/notifications",tags=["Notifications"])
app.include_router(student.router,prefix="/student",tags=["Student and Academic Workflows"])
