from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,EmailStr,Field
from werkzeug.security import generate_password_hash
from backend.database import connect
from backend.security import roles
from backend.services import send_otp
router=APIRouter()
class NewUser(BaseModel):name:str;email:EmailStr;password:str=Field(min_length=8);phone:str="";role:str
@router.get("/users")
def users(u=Depends(roles("admin"))):
 with connect() as c:return [dict(x) for x in c.execute("SELECT id,name,email,phone,role,active,verified FROM users ORDER BY id DESC")]
@router.post("/users")
def create(x:NewUser,u=Depends(roles("admin"))):
 if x.role not in ("student","faculty","admin"):raise HTTPException(400,"Invalid role")
 with connect() as c:
  if c.execute("SELECT id FROM users WHERE email=?",(x.email.lower(),)).fetchone():raise HTTPException(409,"Email exists")
  c.execute("INSERT INTO users(name,email,phone,password_hash,role,verified) VALUES(?,?,?,?,?,0)",(x.name,x.email.lower(),x.phone,generate_password_hash(x.password),x.role))
 ok,msg=send_otp(x.email.lower(),"signup")
 return {"message":"Created; OTP sent" if ok else "Created but email not configured: "+msg}
@router.delete("/users/{uid}")
def deactivate(uid:int,u=Depends(roles("admin"))):
 if uid==u["id"]:raise HTTPException(400,"Cannot deactivate your own account")
 with connect() as c:c.execute("UPDATE users SET active=0 WHERE id=?",(uid,))
 return {"message":"Account deactivated; records retained"}

@router.patch("/users/{uid}/activate")
def activate(uid:int,u=Depends(roles("admin"))):
 with connect() as c:
  cur=c.execute("UPDATE users SET active=1 WHERE id=?",(uid,))
  if not cur.rowcount:raise HTTPException(404,"User not found")
 return {"message":"Account activated"}
@router.patch("/users/{uid}/role")
def change_role(uid:int,x:dict,u=Depends(roles("admin"))):
 role=x.get("role")
 if role not in ("student","faculty","admin"):raise HTTPException(400,"Invalid role")
 if uid==u["id"] and role!="admin":raise HTTPException(400,"Cannot remove your own admin role")
 with connect() as c:
  cur=c.execute("UPDATE users SET role=? WHERE id=?",(role,uid))
  if not cur.rowcount:raise HTTPException(404,"User not found")
 return {"message":"Role updated"}
