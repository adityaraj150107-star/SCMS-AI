import smtplib,ssl,secrets,hashlib,requests,time
from email.message import EmailMessage
from backend.config import *
def email(to,subject,body):
 if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):return False,"SMTP is not configured"
 m=EmailMessage();m["Subject"]=subject;m["From"]=SMTP_FROM;m["To"]=to;m.set_content(body)
 try:
  with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=15) as s:s.starttls(context=ssl.create_default_context());s.login(SMTP_USER,SMTP_PASSWORD);s.send_message(m)
  return True,"sent"
 except Exception as e:return False,str(e)
def send_otp(to,purpose):
 code=f"{secrets.randbelow(1000000):06d}";digest=hashlib.sha256(code.encode()).hexdigest()
 with __import__("backend.database",fromlist=["connect"]).connect() as c:
  c.execute("DELETE FROM otps WHERE email=? AND purpose=?",(to,purpose));c.execute("INSERT INTO otps VALUES(?,?,?,?,0)",(to,purpose,digest,time.time()+600))
 ok,msg=email(to,"SCMS_AI verification code",f"Your code is {code}. It expires in 10 minutes. Do not share it.")
 if not ok and DEV_SHOW_OTP:
  return True, f"Development mode OTP: {code} (email delivery unavailable: {msg})"
 return ok,msg
def verify_otp(to,purpose,code):
 digest=hashlib.sha256(code.encode()).hexdigest()
 with __import__("backend.database",fromlist=["connect"]).connect() as c:
  r=c.execute("SELECT rowid,* FROM otps WHERE email=? AND purpose=?",(to,purpose)).fetchone()
  if not r:return False,"OTP not found"
  if r["expires"]<time.time():return False,"OTP expired"
  if r["attempts"]>=5:return False,"Too many attempts"
  if not secrets.compare_digest(r["otp_hash"],digest):c.execute("UPDATE otps SET attempts=attempts+1 WHERE rowid=?",(r["rowid"],));return False,"Incorrect OTP"
  c.execute("DELETE FROM otps WHERE rowid=?",(r["rowid"],));return True,"verified"


def sms(to, body):
    account=os.getenv("TWILIO_ACCOUNT_SID",""); token=os.getenv("TWILIO_AUTH_TOKEN",""); sender=os.getenv("TWILIO_FROM_NUMBER","")
    if not (account and token and sender and to): return False,"Twilio SMS is not configured"
    try:
        from requests.auth import HTTPBasicAuth
        r=requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{account}/Messages.json",data={"From":sender,"To":to,"Body":body},auth=HTTPBasicAuth(account,token),timeout=15)
        r.raise_for_status(); return True,"sent"
    except Exception as e:return False,str(e)

def notify_user(user_id, title, body, channels=("in_app", "email", "sms")):
    db=__import__("backend.database",fromlist=["connect"])
    with db.connect() as c:
        user=c.execute("SELECT email,phone,active FROM users WHERE id=?",(user_id,)).fetchone()
        if not user or not user["active"]: return
        for channel in channels:
            if channel=="in_app": ok,msg=True,"saved"
            elif channel=="email": ok,msg=email(user["email"],title,body)
            elif channel=="sms": ok,msg=sms(user["phone"],f"{title}: {body}")
            else: continue
            c.execute("INSERT INTO notifications(user_id,title,body,channel,status) VALUES(?,?,?,?,?)",(user_id,title,body,channel,"sent" if ok else "not_configured_or_failed"))
