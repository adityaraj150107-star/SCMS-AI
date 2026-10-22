import os, requests
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import webbrowser
import threading
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")

app=Flask(__name__,template_folder='frontend/templates',static_folder='frontend/static')
app.secret_key=os.getenv('FLASK_SECRET_KEY','dev-only-change-this-secret')
API=os.getenv('SCMS_API_BASE','http://127.0.0.1:8000')

@app.get('/')
def home():
    if session.get('token'): return redirect('/dashboard')
    return render_template('index.html')

@app.post('/login')
def login():
    try:
        r=requests.post(API+'/auth/login',json={'email':request.form.get('email','').strip(),'password':request.form.get('password','')},timeout=20)
        if r.ok:
            d=r.json()
            selected_role=request.form.get('portal','').strip().lower()
            actual_role=str(d['user'].get('role','')).strip().lower()
            if selected_role and selected_role != actual_role:
                flash('This account belongs to the '+actual_role.title()+' portal. Please select the correct portal.')
                return redirect('/')
            session['token']=d['access_token']; session['user']=d['user']['name']; session['email']=d['user']['email']; session['role']=d['user']['role']; session['uid']=d['user']['id']
            accounts=session.get('accounts',[])
            if not any(a.get('email')==session['email'] for a in accounts): accounts.append({'email':session['email'],'name':session['user']})
            session['accounts']=accounts[-5:]
            return redirect('/dashboard')
        flash(r.json().get('detail','Login failed'))
    except Exception: flash('FastAPI backend is not running. Start port 8000 first.')
    return redirect('/')

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='GET': return render_template('signup.html')
    payload={'name':request.form.get('name','').strip(),'email':request.form.get('email','').strip(),'password':request.form.get('password',''),'phone':request.form.get('phone','').strip(),'role':request.form.get('role','student')}
    try:
        r=requests.post(API+'/auth/signup',json=payload,timeout=30)
        if r.ok:
            session['pending_email']=payload['email']; flash(r.json().get('message','OTP sent.')); return redirect('/verify-otp')
        flash(r.json().get('detail','Could not create account.'))
    except Exception: flash('FastAPI backend is not running.')
    return redirect('/signup')

@app.route('/verify-otp',methods=['GET','POST'])
def verify_otp():
    if request.method=='GET': return render_template('verify.html',email=session.get('pending_email',''))
    try:
        r=requests.post(API+'/auth/verify-otp',json={'email':request.form.get('email','').strip(),'code':request.form.get('code','').strip(),'purpose':'signup'},timeout=20)
        if r.ok:
            d=r.json()
            if d.get('access_token') and d.get('user'):
                session['token']=d['access_token'];session['uid']=d['user']['id'];session['user']=d['user']['name'];session['email']=d['user']['email'];session['role']=d['user']['role']
                accounts=session.get('accounts',[])
                if not any(a.get('email')==session['email'] for a in accounts):accounts.append({'email':session['email'],'name':session['user']})
                session['accounts']=accounts[-5:]
                flash('Email verified. Welcome to SCMS_AI!')
                return redirect('/dashboard')
            flash('Email verified. Please sign in.')
            return redirect('/')
        flash(r.json().get('detail','OTP verification failed.'))
    except Exception: flash('FastAPI backend is not running.')
    return redirect('/verify-otp')

@app.get('/dashboard')
def dashboard():
    if not session.get('token'): return redirect('/')
    return render_template('dashboard.html',user=session['user'],email=session['email'],role=session['role'],uid=session.get('uid'),accounts=session.get('accounts',[]))

@app.post('/switch-account')
def switch_account():
    email=request.form.get('email','').strip(); password=request.form.get('password','')
    try:
        r=requests.post(API+'/auth/login',json={'email':email,'password':password},timeout=20)
        if r.ok:
            d=r.json();session['token']=d['access_token'];session['user']=d['user']['name'];session['email']=d['user']['email'];session['role']=d['user']['role'];session['uid']=d['user']['id']
            accounts=session.get('accounts',[])
            if not any(a.get('email')==email for a in accounts):accounts.append({'email':email,'name':d['user']['name']})
            session['accounts']=accounts[-5:]
            return redirect('/dashboard')
        flash(r.json().get('detail','Could not switch account.'))
    except Exception: flash('FastAPI backend is not running.')
    return redirect('/dashboard')


@app.post('/remove-account')
def remove_account():
    email=request.form.get('email','').strip().lower()
    accounts=session.get('accounts',[])
    session['accounts']=[a for a in accounts if str(a.get('email','')).lower()!=email]
    # Removing here only removes the remembered account shortcut from this browser session.
    # It does not delete the user's real college account or academic records.
    flash('Account removed from this device list. The actual account and records are unchanged.')
    return redirect('/dashboard')

@app.post('/api/chat')
def chat():
    if not session.get('token'): return jsonify(error='Login required'),401
    try:
        r=requests.post(API+'/ai/chat',json=request.get_json(silent=True) or {},headers={'Authorization':'Bearer '+session['token']},timeout=180)
        return (r.text,r.status_code,{'Content-Type':'application/json'})
    except Exception as e: return jsonify(error='AI service unavailable. Check Ollama/Gemini configuration.',detail=str(e)[:200]),502

@app.route('/proxy/<path:path>',methods=['GET','POST','PATCH','DELETE'])
def proxy(path):
    if not session.get('token'): return jsonify(detail='Please sign in first'),401
    try:
        r=requests.request(request.method,API+'/'+path,params=request.args,json=request.get_json(silent=True),headers={'Authorization':'Bearer '+session['token']},timeout=60)
        return (r.text,r.status_code,{'Content-Type':r.headers.get('Content-Type','application/json')})
    except Exception as e: return jsonify(detail='FastAPI backend unavailable: '+str(e)[:180]),502


@app.post('/upload')
def upload_file():
    if not session.get('token'): return jsonify(error='Login required'),401
    f=request.files.get('file')
    if not f or not f.filename: return jsonify(error='Choose a file first'),400
    original=secure_filename(f.filename)
    ext=Path(original).suffix.lower()
    allowed={'.pdf','.docx','.txt','.png','.jpg','.jpeg','.webp'}
    if ext not in allowed: return jsonify(error='Supported files: PDF, DOCX, TXT, PNG, JPG, WEBP'),400
    data=f.read()
    if len(data)>12*1024*1024: return jsonify(error='Maximum file size is 12 MB'),413
    upload_dir=Path(app.static_folder)/'uploads'; upload_dir.mkdir(parents=True,exist_ok=True)
    safe_name=f"{session.get('uid','user')}_{os.urandom(5).hex()}_{original}"
    target=upload_dir/safe_name; target.write_bytes(data)
    extracted=''; preview=None
    try:
        if ext=='.txt': extracted=data.decode('utf-8',errors='replace')
        elif ext=='.pdf':
            from pypdf import PdfReader
            import io
            reader=PdfReader(io.BytesIO(data)); extracted='\n'.join((page.extract_text() or '') for page in reader.pages[:40])
        elif ext=='.docx':
            from docx import Document
            import io
            doc=Document(io.BytesIO(data)); extracted='\n'.join(p.text for p in doc.paragraphs)
        elif ext in {'.png','.jpg','.jpeg','.webp'}:
            preview='/static/uploads/'+safe_name
            try:
                from PIL import Image
                import pytesseract
                extracted=pytesseract.image_to_string(Image.open(target))
            except Exception:
                extracted=''
    except Exception as e:
        return jsonify(error='Could not read this file: '+str(e)[:160]),400
    return jsonify(filename=original,preview=preview,text=extracted[:30000],message='File uploaded')

@app.get('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    url='http://127.0.0.1:5000'
    threading.Timer(1.0, lambda: webbrowser.open_new(url)).start()
    app.run(host='127.0.0.1',port=5000,debug=False)
