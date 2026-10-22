from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
import requests
from backend.config import OLLAMA_URL,OLLAMA_MODEL,GEMINI_KEY,GEMINI_MODEL
from backend.database import connect
from backend.security import current_user
router=APIRouter()
class Chat(BaseModel):message:str=Field(min_length=1,max_length=22000);provider:str='ollama'
SYSTEM='''You are SCMS_AI, a helpful college management and learning AI Agent. Explain in clear, practical language and use Hinglish when the user does. You can help with computer science, exam preparation, and navigating college workflows. Use the supplied live SCMS_AI database context for college-specific questions. Do not invent student records, marks, attendance, dates, or policies. Never claim to have changed an official record; records must be changed through authenticated forms. Project creator: Aditya Rajput. If asked where Aditya Rajput is from, answer Vaishali district, Bihar. If information is missing from context, say so and guide the user to the appropriate portal.'''
def college_context():
    sections=[]
    try:
        with connect() as c:
            courses=[dict(x) for x in c.execute('SELECT id,name,description FROM courses ORDER BY name LIMIT 40')]
            subjects=[dict(x) for x in c.execute('SELECT sub.name,sub.code,se.name semester,co.name course FROM subjects sub JOIN semesters se ON se.id=sub.semester_id JOIN courses co ON co.id=se.course_id ORDER BY co.name,se.id LIMIT 100')]
            notices=[dict(x) for x in c.execute('SELECT title,body,audience,created_at FROM notices ORDER BY id DESC LIMIT 15')]
            assignments=[dict(x) for x in c.execute('SELECT title,description,due_date FROM assignments ORDER BY id DESC LIMIT 20')]
        if courses: sections.append('COURSES: '+str(courses))
        if subjects: sections.append('SUBJECTS: '+str(subjects))
        if notices: sections.append('RECENT NOTICES: '+str(notices))
        if assignments: sections.append('ASSIGNMENTS: '+str(assignments))
    except Exception: pass
    return '\n\n'.join(sections) if sections else 'No college catalogue records have been added to the database yet.'
@router.post('/chat')
def chat(x:Chat,u=Depends(current_user)):
    # Recent chat turns are scoped to the authenticated account.
    with connect() as c:
        history=[dict(r) for r in c.execute('SELECT role,message FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 8',(u['id'],)).fetchall()][::-1]
    messages=[{'role':'system','content':SYSTEM+'\n\nCURRENT COLLEGE DATABASE CONTEXT:\n'+college_context()}]
    for row in history:
        if row['role'] in ('user','assistant'):
            messages.append({'role':'assistant' if row['role']=='assistant' else 'user','content':row['message'][:4000]})
    messages.append({'role':'user','content':x.message})
    try:
        if x.provider=='ollama':
            r=requests.post(OLLAMA_URL.rstrip('/')+'/api/chat',json={'model':OLLAMA_MODEL,'messages':messages,'stream':False},timeout=180);r.raise_for_status();reply=r.json()['message']['content'];model=OLLAMA_MODEL
        elif x.provider=='gemini':
            if not GEMINI_KEY: raise HTTPException(503,'Set GEMINI_API_KEY in .env to use Gemini.')
            contents=[]
            for m in messages:
                if m['role']=='system': continue
                contents.append({'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]})
            r=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}',json={'systemInstruction':{'parts':[{'text':messages[0]['content']}]},'contents':contents},timeout=180);r.raise_for_status();reply=r.json()['candidates'][0]['content']['parts'][0]['text'];model=GEMINI_MODEL
        else: raise HTTPException(400,'provider must be ollama or gemini')
    except HTTPException: raise
    except requests.exceptions.ConnectionError: raise HTTPException(503,'AI provider is unreachable. Start Ollama or check your internet/API settings.')
    except requests.exceptions.Timeout: raise HTTPException(504,'AI provider timed out. Try a smaller question or a lighter model.')
    except Exception as e: raise HTTPException(503,'AI provider error: '+str(e)[:200])
    with connect() as c:
        c.execute('INSERT INTO chat_history(user_id,role,message) VALUES(?,?,?)',(u['id'],'user',x.message))
        c.execute('INSERT INTO chat_history(user_id,role,message) VALUES(?,?,?)',(u['id'],'assistant',reply))
    return {'reply':reply,'provider':x.provider,'model':model}
