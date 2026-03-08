# app/routes/blocklist.py
from fastapi import APIRouter, Depends, HTTPException
from app.models import BlocklistItem
from app.auth import get_current_user_id
from app.database import get_supabase

router = APIRouter(prefix="/blocklist", tags=["Blocklist"])

@router.get("/")
def get_blocklist(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    result = supabase.table('blocklist').select("*").eq('user_id', user_id).execute()
    return {"blocklist": result.data}

@router.post("/")
def add_to_blocklist(
    item: BlocklistItem,
    user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()
    
    try:
        result = supabase.table('blocklist').insert({
            'user_id': user_id,
            'domain': item.domain,
            'reason': item.reason
        }).execute()
        
        return {"message": "Added to blocklist", "item": result.data[0]}
    except Exception as e:
        if 'duplicate' in str(e).lower():
            raise HTTPException(status_code=400, detail="Domain already in blocklist")
        raise

@router.delete("/{domain}")
def remove_from_blocklist(
    domain: str,
    user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()
    
    supabase.table('blocklist').delete().eq('user_id', user_id).eq('domain', domain).execute()
    
    return {"message": "Removed from blocklist"}
