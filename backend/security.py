import base64,json,hmac,hashlib,time
from fastapi import Header,HTTPException,Depends
from backend.config import JWT_SECRET
from backend.database import connect
def token(uid,role):
 raw=base64.urlsafe_b64encode(json.dumps({"sub":uid,"role":role,"exp":time.time()+43200}).encode()).decode().rstrip("=")
 sig=base64.urlsafe_b64encode(hmac.new(JWT_SECRET.encode(),raw.encode(),hashlib.sha256).digest()).decode().rstrip("=")
 return raw+"."+sig
def current_user(authorization:str=Header(default="")):
 try:
  raw,sig=authorization.removeprefix("Bearer ").split(".");expected=base64.urlsafe_b64encode(hmac.new(JWT_SECRET.encode(),raw.encode(),hashlib.sha256).digest()).decode().rstrip("=")
  if not hmac.compare_digest(sig,expected):raise ValueError()
  p=json.loads(base64.urlsafe_b64decode(raw+"="*(-len(raw)%4)))
  if p["exp"]<time.time():raise ValueError()
  with connect() as c:r=c.execute("SELECT id,name,email,phone,role,active,verified FROM users WHERE id=?",(p["sub"],)).fetchone()
  if not r or not r["active"]:raise ValueError()
  return dict(r)
 except Exception:raise HTTPException(401,"Login required or session expired")
def roles(*allowed):
 def dep(u=Depends(current_user)):
  if u["role"] not in allowed:raise HTTPException(403,"Insufficient permissions")
  return u
 return dep
