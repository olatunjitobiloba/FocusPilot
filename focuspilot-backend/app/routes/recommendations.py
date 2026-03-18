# app/routes/recommendations.py
from fastapi import APIRouter, Depends
from app.auth import get_current_user_id
from app.database import get_supabase, execute_with_retries
from app.domain_whitelist import filter_activities_by_domain
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional
import re

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def parse_iso_datetime(value: str) -> datetime:
    if not value:
        raise ValueError("Missing datetime value")

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    if "." in text:
        match = re.match(r"^(.*?\.)(\d+)([+-]\d{2}:?\d{2})?$", text)
        if match:
            base, fraction, tz = match.groups()
            normalized_fraction = (fraction + "000000")[:6]
            text = f"{base}{normalized_fraction}{tz or ''}"

    return datetime.fromisoformat(text)


def normalize_domain(value: str) -> str:
    domain = (value or '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '')
    domain = domain.split('/')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def get_productive_domains(user_id: str) -> set[str]:
    result = execute_with_retries(
        lambda db: db.table('suggestion_feedback')
        .select('domain')
        .eq('user_id', user_id)
        .eq('action', 'productive')
        .execute()
    )
    return {
        normalize_domain(item.get('domain', ''))
        for item in (result.data or [])
        if item.get('domain')
    }


def build_block_sites_recommendation(
    sessions: list[dict],
    activities: list[dict],
    productive_domains: set[str],
    limit: int = 3,
) -> Optional[dict]:
    if not activities:
        return None

    low_focus_session_ids = {
        s['id']
        for s in sessions
        if s.get('focus_score') is not None and s.get('focus_score') < 5
    }

    domain_stats = defaultdict(lambda: {
        'total_seconds': 0,
        'visits': 0,
        'low_focus_visits': 0,
    })

    for activity in activities:
        domain = normalize_domain(activity.get('domain', ''))
        if not domain or domain in productive_domains:
            continue

        duration = activity.get('duration_seconds') or 0
        session_id = activity.get('session_id')
        stats = domain_stats[domain]
        stats['total_seconds'] += duration
        stats['visits'] += 1

        if session_id in low_focus_session_ids:
            stats['low_focus_visits'] += 1

    if not domain_stats:
        return None

    def rank_key(item: tuple[str, dict]) -> tuple[float, float, int]:
        _, stats = item
        visits = max(stats['visits'], 1)
        low_focus_ratio = stats['low_focus_visits'] / visits
        total_minutes = stats['total_seconds'] / 60

        # Favor low-focus correlation first, then total study-time spent.
        weighted_score = (low_focus_ratio * 0.7) + (min(total_minutes / 30, 1.0) * 0.3)
        return (weighted_score, total_minutes, stats['visits'])

    ranked = sorted(domain_stats.items(), key=rank_key, reverse=True)[:limit]
    if not ranked:
        return None

    has_low_focus_signal = any(stats['low_focus_visits'] > 0 for _, stats in ranked)
    top_domains = [domain for domain, _ in ranked]
    domain_list = ', '.join(top_domains)

    message = (
        f"You visit {domain_list} during low-focus sessions. Consider blocking them."
        if has_low_focus_signal
        else f"You spend the most study-time on {domain_list}. Consider blocking them to stay focused."
    )

    return {
        'type': 'block_sites',
        'title': 'Sites to Block',
        'message': message,
        'domains': top_domains,
        'priority': 'high'
    }

@router.get("/")
def get_recommendations(user_id: str = Depends(get_current_user_id)):
    """
    Generate personalized recommendations based on user data
    """
    supabase = get_supabase()
    
    # Get recent data (last 14 days)
    start_date = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    
    sessions_result = execute_with_retries(
        lambda db: db.table('focus_sessions').select("*").eq('user_id', user_id).gte('start_time', start_date).execute()
    )

    activities_result = execute_with_retries(
        lambda db: db.table('browsing_activity').select("*").eq('user_id', user_id).gte('timestamp', start_date).execute()
    )
    
    sessions = sessions_result.data
    activities = filter_activities_by_domain(activities_result.data)
    productive_domains = get_productive_domains(user_id)
    
    recommendations = []
    
    # Recommendation 1: Optimal session length
    if sessions:
        completed_sessions = [s for s in sessions if s['end_time'] and s['focus_score']]
        
        if completed_sessions:
            # Find sessions with high focus score
            high_focus_sessions = [s for s in completed_sessions if s['focus_score'] >= 7]
            
            if high_focus_sessions:
                avg_duration = sum(s['duration_minutes'] for s in high_focus_sessions) / len(high_focus_sessions)
                
                recommendations.append({
                    'type': 'session_length',
                    'title': 'Optimal Session Length',
                    'message': f"Your best focus sessions average {round(avg_duration)} minutes. Try this duration next time!",
                    'value': round(avg_duration),
                    'priority': 'high'
                })
    
    # Recommendation 2: Sites to block
    block_sites_recommendation = build_block_sites_recommendation(
        sessions=sessions,
        activities=activities,
        productive_domains=productive_domains,
    )
    if block_sites_recommendation:
        recommendations.append(block_sites_recommendation)
    
    # Recommendation 3: Best time to study
    if sessions:
        # Analyze hourly performance
        hourly_performance = defaultdict(lambda: {'total_score': 0, 'count': 0})
        
        for session in sessions:
            if not session.get('focus_score'):
                continue

            try:
                start_time = parse_iso_datetime(session.get('start_time'))
            except Exception:
                continue

            hour = start_time.hour
            hourly_performance[hour]['total_score'] += session['focus_score']
            hourly_performance[hour]['count'] += 1
        
        # Calculate average score per hour
        hourly_avg = {}
        for hour, stats in hourly_performance.items():
            hourly_avg[hour] = stats['total_score'] / stats['count']
        
        if hourly_avg:
            best_hour = max(hourly_avg, key=hourly_avg.get)
            best_score = hourly_avg[best_hour]
            
            if best_score >= 7:
                recommendations.append({
                    'type': 'best_time',
                    'title': 'Your Peak Hour',
                    'message': f"You focus best at {best_hour:02d}:00 (avg score: {best_score:.1f}). Schedule important tasks then!",
                    'hour': best_hour,
                    'score': round(best_score, 1),
                    'priority': 'medium'
                })
    
    # Recommendation 4: Consistency
    if sessions:
        # Check if user studies daily
        dates_with_sessions = set()
        for session in sessions:
            date = session['start_time'][:10]
            dates_with_sessions.add(date)
        
        days_studied = len(dates_with_sessions)
        
        if days_studied < 10:  # Less than 10 days in 14 days
            recommendations.append({
                'type': 'consistency',
                'title': 'Build Consistency',
                'message': f"You studied {days_studied} out of 14 days. Try to study daily for better results!",
                'days_studied': days_studied,
                'priority': 'medium'
            })
    
    # Recommendation 5: Break reminder
    if sessions:
        long_sessions = [s for s in sessions if s['duration_minutes'] and s['duration_minutes'] > 60]
        
        if len(long_sessions) > 3:
            recommendations.append({
                'type': 'breaks',
                'title': 'Take Breaks',
                'message': "You often study for over 60 minutes. Remember to take 5-10 minute breaks to maintain focus!",
                'priority': 'low'
            })
    
    # Sort by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations.sort(key=lambda x: priority_order[x['priority']])
    
    return {
        "recommendations": recommendations,
        "total": len(recommendations)
    }
