from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from backend.database import connect
from backend.security import current_user,roles
from backend.services import notify_user
router=APIRouter()
class Enrollment(BaseModel):course_id:int;semester_id:int|None=None
class AttendanceIn(BaseModel):student_id:int;subject_id:int;att_date:str;status:str
class MarkIn(BaseModel):student_id:int;subject_id:int;exam_name:str;obtained:float=Field(ge=0);max_marks:float=Field(gt=0)
class AssignmentIn(BaseModel):title:str;description:str="";subject_id:int|None=None;due_date:str|None=None
class SubmitIn(BaseModel):content:str="";file_name:str=""
class GradeIn(BaseModel):grade:str;feedback:str=""
class TimetableIn(BaseModel):course_id:int;semester_id:int;subject_id:int;weekday:str;start_time:str;end_time:str;room:str=""
@router.get("/me")
def me(u=Depends(current_user)):
 with connect() as c:
  user=dict(c.execute("SELECT id,name,email,phone,role,active,verified FROM users WHERE id=?",(u["id"],)).fetchone())
  if u["role"]=="student":
   user["enrollments"]=[dict(x) for x in c.execute("SELECT e.*,co.name course_name,se.name semester_name FROM enrollments e JOIN courses co ON co.id=e.course_id LEFT JOIN semesters se ON se.id=e.semester_id WHERE e.user_id=?",(u["id"],))]
  return user
@router.post("/enrollments")
def enroll(x:Enrollment,u=Depends(current_user)):
 if u["role"]!="student": raise HTTPException(403,"Only students can self-enroll")
 with connect() as c:
  if not c.execute("SELECT id FROM courses WHERE id=?",(x.course_id,)).fetchone():raise HTTPException(404,"Course not found")
  try:c.execute("INSERT INTO enrollments(user_id,course_id,semester_id) VALUES(?,?,?)",(u["id"],x.course_id,x.semester_id))
  except Exception:raise HTTPException(409,"Already enrolled in this course")
 return {"message":"Enrollment saved"}
@router.get("/attendance")
def attendance(u=Depends(current_user)):
 with connect() as c:
  if u["role"]=="student": rows=c.execute("SELECT a.*,s.name subject_name,s.code FROM attendance a JOIN subjects s ON s.id=a.subject_id WHERE a.student_id=? ORDER BY att_date DESC",(u["id"],)).fetchall()
  elif u["role"] in ("faculty","admin"): rows=c.execute("SELECT a.*,s.name subject_name,u.name student_name FROM attendance a JOIN subjects s ON s.id=a.subject_id JOIN users u ON u.id=a.student_id ORDER BY att_date DESC LIMIT 500").fetchall()
  else: raise HTTPException(403,"Not allowed")
 return [dict(x) for x in rows]
@router.post("/attendance")
def mark_attendance(x:AttendanceIn,u=Depends(roles("faculty","admin"))):
 if x.status not in ("present","absent","late"):raise HTTPException(400,"status must be present, absent or late")
 with connect() as c:
  try:c.execute("INSERT INTO attendance(student_id,subject_id,att_date,status,marked_by) VALUES(?,?,?,?,?)",(x.student_id,x.subject_id,x.att_date,x.status,u["id"]))
  except Exception:raise HTTPException(409,"Attendance already marked for this student/subject/date")
 notify_user(x.student_id,"Attendance updated",f"Attendance for subject ID {x.subject_id} on {x.att_date}: {x.status}")
 return {"message":"Attendance saved"}
@router.get("/marks")
def marks(u=Depends(current_user)):
 with connect() as c:
  if u["role"]=="student":rows=c.execute("SELECT m.*,s.name subject_name FROM marks m JOIN subjects s ON s.id=m.subject_id WHERE student_id=? ORDER BY id DESC",(u["id"],)).fetchall()
  elif u["role"] in ("faculty","admin"):rows=c.execute("SELECT m.*,s.name subject_name,u.name student_name FROM marks m JOIN subjects s ON s.id=m.subject_id JOIN users u ON u.id=m.student_id ORDER BY id DESC LIMIT 500").fetchall()
  else:raise HTTPException(403,"Not allowed")
 return [dict(x) for x in rows]
@router.post("/marks")
def add_marks(x:MarkIn,u=Depends(roles("faculty","admin"))):
 if x.obtained>x.max_marks:raise HTTPException(400,"Obtained marks cannot exceed maximum marks")
 with connect() as c:
  try:c.execute("INSERT INTO marks(student_id,subject_id,exam_name,obtained,max_marks,entered_by) VALUES(?,?,?,?,?,?)",(x.student_id,x.subject_id,x.exam_name,x.obtained,x.max_marks,u["id"]))
  except Exception:raise HTTPException(409,"Marks already exist for this student/subject/exam")
 notify_user(x.student_id,"Marks published",f"{x.exam_name}: {x.obtained}/{x.max_marks} for subject ID {x.subject_id}")
 return {"message":"Marks saved"}
@router.get("/assignments")
def assignments(u=Depends(current_user)):
 with connect() as c:return [dict(x) for x in c.execute("SELECT a.*,s.name subject_name,u.name created_by_name FROM assignments a LEFT JOIN subjects s ON s.id=a.subject_id LEFT JOIN users u ON u.id=a.created_by ORDER BY a.id DESC")]
@router.post("/assignments")
def create_assignment(x:AssignmentIn,u=Depends(roles("faculty","admin"))):
 with connect() as c:
  cur=c.execute("INSERT INTO assignments(title,description,subject_id,due_date,created_by) VALUES(?,?,?,?,?)",(x.title,x.description,x.subject_id,x.due_date,u["id"]))
  assignment_id=cur.lastrowid
  students=[r["id"] for r in c.execute("SELECT id FROM users WHERE role='student' AND active=1").fetchall()]
 for student_id in students:
  notify_user(student_id,"New assignment",f"{x.title}. Due date: {x.due_date or 'Not specified'}. {x.description}")
 return {"id":assignment_id,"message":"Assignment published"}
@router.post("/assignments/{aid}/submit")
def submit(aid:int,x:SubmitIn,u=Depends(current_user)):
 if u["role"]!="student":raise HTTPException(403,"Only students can submit")
 with connect() as c:
  if not c.execute("SELECT id FROM assignments WHERE id=?",(aid,)).fetchone():raise HTTPException(404,"Assignment not found")
  c.execute("INSERT INTO submissions(assignment_id,student_id,content,file_name) VALUES(?,?,?,?) ON CONFLICT(assignment_id,student_id) DO UPDATE SET content=excluded.content,file_name=excluded.file_name,submitted_at=CURRENT_TIMESTAMP",(aid,u["id"],x.content,x.file_name))
 return {"message":"Assignment submission saved"}
@router.get("/submissions")
def submissions(u=Depends(roles("faculty","admin"))):
 with connect() as c:return [dict(x) for x in c.execute("SELECT sub.*,a.title assignment_title,u.name student_name,u.email FROM submissions sub JOIN assignments a ON a.id=sub.assignment_id JOIN users u ON u.id=sub.student_id ORDER BY sub.submitted_at DESC LIMIT 500")]
@router.post("/submissions/{sid}/grade")
def grade(sid:int,x:GradeIn,u=Depends(roles("faculty","admin"))):
 with connect() as c:
  r=c.execute("SELECT student_id FROM submissions WHERE id=?",(sid,)).fetchone()
  if not r:raise HTTPException(404,"Submission not found")
  c.execute("UPDATE submissions SET grade=?,feedback=? WHERE id=?",(x.grade,x.feedback,sid))
 notify_user(r["student_id"],"Assignment graded",f"Grade: {x.grade}. Feedback: {x.feedback}")
 return {"message":"Grade saved"}
@router.get("/timetable")
def timetable(u=Depends(current_user)):
 with connect() as c:return [dict(x) for x in c.execute("SELECT t.*,co.name course_name,se.name semester_name,s.name subject_name FROM timetable t JOIN courses co ON co.id=t.course_id JOIN semesters se ON se.id=t.semester_id JOIN subjects s ON s.id=t.subject_id ORDER BY CASE t.weekday WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END,t.start_time")]
@router.post("/timetable")
def add_timetable(x:TimetableIn,u=Depends(roles("faculty","admin"))):
 with connect() as c:cur=c.execute("INSERT INTO timetable(course_id,semester_id,subject_id,weekday,start_time,end_time,room,created_by) VALUES(?,?,?,?,?,?,?,?)",(x.course_id,x.semester_id,x.subject_id,x.weekday,x.start_time,x.end_time,x.room,u["id"]))
 return {"id":cur.lastrowid,"message":"Timetable entry saved"}
@router.get("/chat-history")
def history(u=Depends(current_user)):
 with connect() as c:return [dict(x) for x in c.execute("SELECT id,role,message,created_at FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 100",(u["id"],))][::-1]
@router.get("/dashboard-stats")
def stats(u=Depends(current_user)):
 with connect() as c:
  if u["role"]=="student":
   return {"courses":c.execute("SELECT COUNT(*) n FROM enrollments WHERE user_id=?",(u["id"],)).fetchone()["n"],"attendance_records":c.execute("SELECT COUNT(*) n FROM attendance WHERE student_id=?",(u["id"],)).fetchone()["n"],"marks_records":c.execute("SELECT COUNT(*) n FROM marks WHERE student_id=?",(u["id"],)).fetchone()["n"],"assignments":c.execute("SELECT COUNT(*) n FROM assignments").fetchone()["n"]}
  return {"students":c.execute("SELECT COUNT(*) n FROM users WHERE role='student' AND active=1").fetchone()["n"],"faculty":c.execute("SELECT COUNT(*) n FROM users WHERE role='faculty' AND active=1").fetchone()["n"],"courses":c.execute("SELECT COUNT(*) n FROM courses").fetchone()["n"],"notices":c.execute("SELECT COUNT(*) n FROM notices").fetchone()["n"]}
