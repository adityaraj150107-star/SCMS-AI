from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,EmailStr,Field
from werkzeug.security import generate_password_hash,check_password_hash
from backend.database import connect
from backend.security import token
from backend.services import send_otp,verify_otp
router=APIRouter()
class Signup(BaseModel):
 name:str=Field(min_length=2);email:EmailStr;password:str=Field(min_length=8);phone:str="";role:str="student"
class Login(BaseModel):email:EmailStr;password:str
class Otp(BaseModel):email:EmailStr;code:str=Field(min_length=6,max_length=6);purpose:str="signup"
@router.post("/signup")
def signup(x:Signup):
 role=x.role.lower()
 if role not in ("student","faculty"):raise HTTPException(400,"Public signup allowed for student/faculty only")
 with connect() as c:
  if c.execute("SELECT id FROM users WHERE email=?",(x.email.lower(),)).fetchone():raise HTTPException(409,"Email already exists")
  c.execute("INSERT INTO users(name,email,phone,password_hash,role,verified) VALUES(?,?,?,?,?,0)",(x.name,x.email.lower(),x.phone,generate_password_hash(x.password),role))
 ok,msg=send_otp(x.email.lower(),"signup")
 if not ok:raise HTTPException(503,"Account created but OTP email failed: "+msg)
 return {"message":msg}
@router.post("/verify-otp")
def verify(x:Otp):
 ok,msg=verify_otp(x.email.lower(),x.purpose,x.code)
 if not ok:raise HTTPException(400,msg)
 if x.purpose=="signup":
  with connect() as c:
   c.execute("UPDATE users SET verified=1 WHERE email=?",(x.email.lower(),))
   user=c.execute("SELECT id,name,email,role FROM users WHERE email=? AND active=1",(x.email.lower(),)).fetchone()
  if user:
   return {"message":"Email verified","access_token":token(user["id"],user["role"]),"user":dict(user)}
 return {"message":"Email verified"}
@router.post("/request-otp")
def request(x:dict):
 ok,msg=send_otp(str(x.get("email","")).lower(),str(x.get("purpose","signup")))
 if not ok:raise HTTPException(503,msg)
 return {"message":"OTP sent"}
@router.post("/login")
def login(x:Login):
 with connect() as c:r=c.execute("SELECT * FROM users WHERE email=?",(x.email.lower(),)).fetchone()
 if not r or not check_password_hash(r["password_hash"],x.password):raise HTTPException(401,"Invalid email/password")
 if not r["active"]:raise HTTPException(403,"Account disabled")
 if not r["verified"] and r["role"]!="admin":raise HTTPException(403,"Verify email by OTP first")
 return {"access_token":token(r["id"],r["role"]),"user":{"id":r["id"],"name":r["name"],"email":r["email"],"role":r["role"]}}
