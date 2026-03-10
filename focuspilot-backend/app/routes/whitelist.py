from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.database import get_supabase

router = APIRouter(prefix="/whitelist", tags=["Whitelist"])


def normalize_domain(value: str) -> str:
    domain = (value or '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '')
    domain = domain.split('/')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


@router.get("/")
def get_whitelist(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table('suggestion_feedback')
        .select('domain, created_at')
        .eq('user_id', user_id)
        .eq('action', 'productive')
        .order('created_at', desc=True)
        .execute()
    )

    seen = set()
    whitelist = []
    for item in result.data or []:
        domain = normalize_domain(item.get('domain', ''))
        if not domain or domain in seen:
            continue
        seen.add(domain)
        whitelist.append({
            'domain': domain,
            'created_at': item.get('created_at')
        })

    return {"whitelist": whitelist}


@router.post("/")
def add_to_whitelist(payload: dict, user_id: str = Depends(get_current_user_id)):
    domain = normalize_domain(payload.get('domain'))
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    supabase = get_supabase()

    existing = (
        supabase.table('suggestion_feedback')
        .select('id')
        .eq('user_id', user_id)
        .eq('domain', domain)
        .eq('action', 'productive')
        .limit(1)
        .execute()
    )

    if not existing.data:
        supabase.table('suggestion_feedback').insert({
            'user_id': user_id,
            'domain': domain,
            'action': 'productive'
        }).execute()

    # If it was blocked before, remove from blocklist so it stops being blocked
    supabase.table('blocklist').delete().eq('user_id', user_id).eq('domain', domain).execute()

    return {
        "message": f"{domain} marked as productive",
        "domain": domain,
        "action": "productive"
    }


@router.delete("/{domain}")
def remove_from_whitelist(domain: str, user_id: str = Depends(get_current_user_id)):
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    supabase = get_supabase()
    supabase.table('suggestion_feedback').delete()\
        .eq('user_id', user_id)\
        .eq('domain', normalized_domain)\
        .eq('action', 'productive')\
        .execute()

    return {"message": "Removed from whitelist", "domain": normalized_domain}
