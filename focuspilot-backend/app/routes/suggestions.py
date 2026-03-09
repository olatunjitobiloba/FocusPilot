# app/routes/suggestions.py
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.database import get_supabase
from app.domain_whitelist import filter_activities_by_domain, is_whitelisted_domain
from app.ml.distraction_scorer import DistractionScorer
from datetime import datetime, timedelta

router = APIRouter(prefix="/suggestions", tags=["Site Suggestions"])

scorer = DistractionScorer()


# ── GET /suggestions/ ─────────────────────────────────────────────────
@router.get("/")
def get_site_suggestions(user_id: str = Depends(get_current_user_id)):
    """
    Returns ML-generated list of sites the user should block,
    ranked by distraction score.
    """
    supabase = get_supabase()

    # Fetch last 14 days of data
    start_date = (datetime.utcnow() - timedelta(days=14)).isoformat()

    sessions_result = (
        supabase.table('focus_sessions')
        .select("*")
        .eq('user_id', user_id)
        .gte('start_time', start_date)
        .execute()
    )

    activities_result = (
        supabase.table('browsing_activity')
        .select("*")
        .eq('user_id', user_id)
        .gte('timestamp', start_date)
        .execute()
    )

    sessions   = sessions_result.data
    activities = filter_activities_by_domain(activities_result.data)

    if not activities:
        return {
            "suggestions": [],
            "message": "No browsing data yet. Complete a few sessions first!",
            "data_points": 0
        }

    # Get current blocklist so we can mark already-blocked domains
    blocklist_result = (
        supabase.table('blocklist')
        .select("domain")
        .eq('user_id', user_id)
        .execute()
    )
    blocked_domains = {item['domain'] for item in blocklist_result.data}

    # Run ML scoring
    scored = scorer.score_domains(sessions, activities)

    # Enrich with blocked status
    suggestions = []
    for item in scored:
        item['already_blocked'] = item['domain'] in blocked_domains
        suggestions.append(item)

    # Separate new suggestions from already-blocked
    new_suggestions     = [s for s in suggestions if not s['already_blocked']]
    already_blocked     = [s for s in suggestions if s['already_blocked']]

    return {
        "suggestions":       new_suggestions,
        "already_blocked":   already_blocked,
        "total_analyzed":    len(scored),
        "data_points":       len(activities),
        "sessions_analyzed": len(sessions),
        "message": (
            f"Analyzed {len(activities)} browsing events "
            f"across {len(sessions)} sessions"
        )
    }


# ── POST /suggestions/accept ──────────────────────────────────────────
@router.post("/accept")
def accept_suggestion(
    payload: dict,
    user_id: str = Depends(get_current_user_id)
):
    """
    User accepts a suggestion → add domain to blocklist.
    """
    domain = payload.get('domain')
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    supabase = get_supabase()

    # Add to blocklist
    try:
        supabase.table('blocklist').insert({
            'user_id': user_id,
            'domain':  domain,
            'reason':  'ML suggestion accepted'
        }).execute()
    except Exception as e:
        if 'duplicate' in str(e).lower():
            return {"message": f"{domain} is already in your blocklist"}
        raise

    # Log feedback
    supabase.table('suggestion_feedback').insert({
        'user_id': user_id,
        'domain':  domain,
        'action':  'blocked'
    }).execute()

    return {
        "message":  f"✅ {domain} added to blocklist",
        "domain":   domain,
        "action":   "blocked"
    }


# ── POST /suggestions/dismiss ─────────────────────────────────────────
@router.post("/dismiss")
def dismiss_suggestion(
    payload: dict,
    user_id: str = Depends(get_current_user_id)
):
    """
    User dismisses a suggestion → don't show it again.
    """
    domain = payload.get('domain')
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    supabase = get_supabase()

    # Log feedback
    supabase.table('suggestion_feedback').insert({
        'user_id': user_id,
        'domain':  domain,
        'action':  'dismissed'
    }).execute()

    return {
        "message": f"Suggestion for {domain} dismissed",
        "domain":  domain,
        "action":  "dismissed"
    }


# ── GET /suggestions/score/{domain} ──────────────────────────────────
@router.get("/score/{domain}")
def get_domain_score(
    domain: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get distraction score for a specific domain.
    Useful when user manually adds a site to blocklist.
    """
    supabase = get_supabase()
    normalized_domain = domain.strip().lower().replace('www.', '')

    blocklist_result = (
        supabase.table('blocklist')
        .select("domain")
        .eq('user_id', user_id)
        .eq('domain', normalized_domain)
        .execute()
    )
    already_blocked = len(blocklist_result.data) > 0

    start_date = (datetime.utcnow() - timedelta(days=14)).isoformat()

    sessions_result = (
        supabase.table('focus_sessions')
        .select("*")
        .eq('user_id', user_id)
        .gte('start_time', start_date)
        .execute()
    )

    activities_result = (
        supabase.table('browsing_activity')
        .select("*")
        .eq('user_id', user_id)
        .eq('domain', normalized_domain)
        .gte('timestamp', start_date)
        .execute()
    )

    sessions   = sessions_result.data
    activities = activities_result.data

    if is_whitelisted_domain(normalized_domain):
        return {
            "domain":            normalized_domain,
            "distraction_score": 0,
            "already_blocked":   already_blocked,
            "message":           "Domain is excluded by whitelist"
        }

    if not activities:
        if already_blocked:
            return {
                "domain":            normalized_domain,
                "distraction_score": None,
                "already_blocked":   True,
                "message":           "This domain is already blocked. No visit history available."
            }

        return {
            "domain":            normalized_domain,
            "distraction_score": 0,
            "already_blocked":   False,
            "message":           "No data for this domain yet"
        }

    scored = scorer.score_domains(sessions, activities)

    if not scored:
        return {
            "domain":            normalized_domain,
            "distraction_score": 0,
            "already_blocked":   already_blocked,
            "message":           "Domain does not appear to be a significant distractor"
        }

    top_score = scored[0]
    top_score['already_blocked'] = already_blocked
    return top_score
