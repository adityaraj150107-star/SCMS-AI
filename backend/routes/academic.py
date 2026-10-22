from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from backend.database import connect
from backend.security import roles
from backend.services import notify_user
router=APIRouter()
def notify_students(title,body):
 with connect() as c: ids=[r["id"] for r in c.execute("SELECT id FROM users WHERE role='student' AND active=1").fetchall()]
 for uid in ids: notify_user(uid,title,body)
class Course(BaseModel):name:str=Field(min_length=2);description:str=""
class Semester(BaseModel):course_id:int;name:str
class Subject(BaseModel):semester_id:int;name:str;code:str="";syllabus:str=""
class Notice(BaseModel):title:str;body:str;audience:str="all"
@router.get("/courses")
def courses():
 with connect() as c:return [dict(x) for x in c.execute("SELECT * FROM courses ORDER BY name")]
@router.post("/courses")
def add_course(x:Course,u=Depends(roles("admin","faculty"))):
 try:
  with connect() as c:
   cur=c.execute("INSERT INTO courses(name,description) VALUES(?,?)",(x.name,x.description));new_id=cur.lastrowid;c.execute("INSERT INTO audit_logs(actor_id,action,detail) VALUES(?,?,?)",(u["id"],"course_created",x.name))
 except Exception: raise HTTPException(409,"Course name already exists")
 notify_students("New course added",f"{x.name}: {x.description or 'Course details are available in the Academics section.'}")
 return {"id":new_id,"message":"Course created and student notifications attempted"}
@router.get("/semesters")
def semesters():
 with connect() as c:return [dict(x) for x in c.execute("SELECT s.*,c.name course_name FROM semesters s JOIN courses c ON c.id=s.course_id ORDER BY c.name,s.id")]
@router.post("/semesters")
def add_semester(x:Semester,u=Depends(roles("admin","faculty"))):
 with connect() as c:
  try:
   cur=c.execute("INSERT INTO semesters(course_id,name) VALUES(?,?)",(x.course_id,x.name));new_id=cur.lastrowid
   course=c.execute("SELECT name FROM courses WHERE id=?",(x.course_id,)).fetchone()
  except Exception:raise HTTPException(400,"Invalid course or semester already exists")
 notify_students("Semester added",f"{x.name} has been added to {course['name'] if course else 'a course' }.")
 return {"id":new_id,"message":"Semester created and student notifications attempted"}
@router.get("/subjects")
def subjects():
 with connect() as c:return [dict(x) for x in c.execute("SELECT sub.*,s.name semester_name,c.name course_name FROM subjects sub JOIN semesters s ON s.id=sub.semester_id JOIN courses c ON c.id=s.course_id ORDER BY c.name,s.id")]
@router.post("/subjects")
def add_subject(x:Subject,u=Depends(roles("admin","faculty"))):
 with connect() as c:
  cur=c.execute("INSERT INTO subjects(semester_id,name,code,syllabus) VALUES(?,?,?,?)",(x.semester_id,x.name,x.code,x.syllabus));new_id=cur.lastrowid
  sem=c.execute("SELECT name FROM semesters WHERE id=?",(x.semester_id,)).fetchone()
 notify_students("Subject added",f"{x.name} ({x.code or 'no code'}) has been added to {sem['name'] if sem else 'a semester'}.")
 return {"id":new_id,"message":"Subject created and student notifications attempted"}
@router.get("/notices")
def notices():
 with connect() as c:return [dict(x) for x in c.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 100")]
@router.post("/notices")
def add_notice(x:Notice,u=Depends(roles("admin","faculty"))):
 with connect() as c:
  cur=c.execute("INSERT INTO notices(title,body,audience,created_by) VALUES(?,?,?,?)",(x.title,x.body,x.audience,u["id"]))
  audience=x.audience.lower()
  role_filter = "student" if audience=="student" else "faculty" if audience=="faculty" else None
  query="SELECT id FROM users WHERE active=1"+(" AND role=?" if role_filter else "")
  recipients=c.execute(query,(role_filter,) if role_filter else ()).fetchall()
  c.execute("INSERT INTO audit_logs(actor_id,action,detail) VALUES(?,?,?)",(u["id"],"notice_published",x.title))
 from backend.services import notify_user
 for recipient in recipients: notify_user(recipient["id"],x.title,x.body)
 return {"id":cur.lastrowid,"message":"Notice published. In-app notification saved; email/SMS are attempted when configured."}
