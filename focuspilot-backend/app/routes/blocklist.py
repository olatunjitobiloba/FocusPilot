# app/routes/blocklist.py
from fastapi import APIRouter, Depends, HTTPException
from app.models import BlocklistItem
from app.auth import get_current_user_id
from app.database import get_supabase

router = APIRouter(prefix="/blocklist", tags=["Blocklist"])


def normalize_domain(value: str) -> str:
    domain = (value or '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '')
    domain = domain.split('/')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

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
    normalized_domain = normalize_domain(item.domain)

    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required")
    
    try:
        # If user marks this as distracting now, remove productive classification if present.
        supabase.table('suggestion_feedback').delete()\
            .eq('user_id', user_id)\
            .eq('domain', normalized_domain)\
            .eq('action', 'productive')\
            .execute()

        result = supabase.table('blocklist').insert({
            'user_id': user_id,
            'domain': normalized_domain,
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
    normalized_domain = normalize_domain(domain)
    
    supabase.table('blocklist').delete().eq('user_id', user_id).eq('domain', normalized_domain).execute()
    
    return {"message": "Removed from blocklist"}

@router.get("/check")
def check_domain(
    domain: str,
    user_id: str = Depends(get_current_user_id)
):
    """Check if a domain is in the user's blocklist"""
    supabase = get_supabase()
    normalized_domain = normalize_domain(domain)
    
    result = supabase.table('blocklist').select("*")\
        .eq('user_id', user_id)\
        .eq('domain', normalized_domain)\
        .execute()
    
    is_blocked = len(result.data) > 0
    return {"domain": normalized_domain, "is_blocked": is_blocked}
