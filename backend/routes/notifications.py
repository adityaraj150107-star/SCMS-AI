from fastapi import APIRouter,Depends
from backend.database import connect
from backend.security import current_user
router=APIRouter()
@router.get("")
def mine(u=Depends(current_user)):
 with connect() as c:return [dict(x) for x in c.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100",(u["id"],))]
