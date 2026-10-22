import sqlite3,os
from werkzeug.security import generate_password_hash
from backend.config import DB
def connect():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init_db():
 with connect() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',password_hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER DEFAULT 1,verified INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS otps(email TEXT,purpose TEXT,otp_hash TEXT,expires REAL,attempts INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,description TEXT DEFAULT '');
  CREATE TABLE IF NOT EXISTS semesters(id INTEGER PRIMARY KEY,course_id INTEGER,name TEXT,UNIQUE(course_id,name));
  CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY,semester_id INTEGER,name TEXT,code TEXT DEFAULT '',syllabus TEXT DEFAULT '');
  CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY,title TEXT,body TEXT,audience TEXT DEFAULT 'all',created_by INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,body TEXT,channel TEXT,status TEXT DEFAULT 'queued',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS chat_history(id INTEGER PRIMARY KEY,user_id INTEGER,role TEXT,message TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY,actor_id INTEGER,action TEXT,detail TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,course_id INTEGER NOT NULL,semester_id INTEGER,UNIQUE(user_id,course_id));
  CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL,subject_id INTEGER NOT NULL,att_date TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('present','absent','late')),marked_by INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(student_id,subject_id,att_date));
  CREATE TABLE IF NOT EXISTS marks(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL,subject_id INTEGER NOT NULL,exam_name TEXT NOT NULL,obtained REAL NOT NULL,max_marks REAL NOT NULL,entered_by INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(student_id,subject_id,exam_name));
  CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY,title TEXT NOT NULL,description TEXT DEFAULT '',subject_id INTEGER,due_date TEXT,created_by INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY,assignment_id INTEGER NOT NULL,student_id INTEGER NOT NULL,content TEXT DEFAULT '',file_name TEXT DEFAULT '',submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,grade TEXT DEFAULT '',feedback TEXT DEFAULT '',UNIQUE(assignment_id,student_id));
  CREATE TABLE IF NOT EXISTS timetable(id INTEGER PRIMARY KEY,course_id INTEGER,semester_id INTEGER,subject_id INTEGER,weekday TEXT NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,room TEXT DEFAULT '',created_by INTEGER);
  CREATE TABLE IF NOT EXISTS account_links(id INTEGER PRIMARY KEY,owner_id INTEGER NOT NULL,linked_user_id INTEGER NOT NULL,UNIQUE(owner_id,linked_user_id));
  """)
  email=os.getenv("BOOTSTRAP_ADMIN_EMAIL","");pw=os.getenv("BOOTSTRAP_ADMIN_PASSWORD","")
  if email and pw and not c.execute("SELECT id FROM users WHERE email=?",(email.lower(),)).fetchone():
   c.execute("INSERT INTO users(name,email,password_hash,role,active,verified) VALUES(?,?,?,?,1,1)",("Main Admin",email.lower(),generate_password_hash(pw),"admin"))
