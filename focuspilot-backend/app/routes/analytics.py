"""
Analytics endpoints — expose analytics data.
"""

# app/routes/analytics.py
from fastapi import APIRouter, Depends, Query, HTTPException
from app.auth import get_current_user_id
from app.database import execute_with_retries
from app.domain_whitelist import filter_activities_by_domain
from app.analytics.aggregator import AnalyticsAggregator
from app.analytics.report_generator import WeeklyReportGenerator
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def run_db(operation, failure_message: str):
    try:
        return execute_with_retries(operation)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail=failure_message)


def normalize_domain(value: str) -> str:
    domain = (value or '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '')
    domain = domain.split('/')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def get_productive_domains(supabase, user_id: str) -> set[str]:
    result = run_db(
        lambda client: client.table('suggestion_feedback')
        .select('domain')
        .eq('user_id', user_id)
        .eq('action', 'productive')
        .execute(),
        "Database unavailable while loading productive domains"
    )
    return {
        normalize_domain(item.get('domain', ''))
        for item in (result.data or [])
        if item.get('domain')
    }


def get_analytics_snapshot(user_id: str, days: int):
    """Load aggregated analytics safely for endpoint responses."""
    try:
        aggregator = AnalyticsAggregator(user_id)
        return aggregator.compute_all(days=days)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail='Analytics unavailable right now'
        )


@router.get("/overview")
def get_overview(
    days: int = Query(default=30, ge=7, le=90),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get full analytics overview for the last N days.
    Includes summary, trends, breakdowns, and session history.
    """
    return get_analytics_snapshot(user_id, days)


@router.get("/summary")
def get_summary(
    days: int = Query(default=7, ge=1, le=90),
    user_id: str = Depends(get_current_user_id)
):
    """Get just the summary metrics."""
    data = get_analytics_snapshot(user_id, days)
    return {
        'summary': data.get('summary', {}),
        'streak': data.get('streak', {}),
        'best_day': data.get('best_day', {}),
        'best_hour': data.get('best_hour', {})
    }


@router.get("/trends")
def get_trends(
    days: int = Query(default=30, ge=7, le=90),
    user_id: str = Depends(get_current_user_id)
):
    """Get trend data for charts."""
    data = get_analytics_snapshot(user_id, days)
    return {
        'weekly_trend': data.get('weekly_trend', []),
        'daily_breakdown': data.get('daily_breakdown', []),
        'risk_trend': data.get('risk_trend', [])
    }


@router.get("/sessions")
def get_session_history(
    days: int = Query(default=30, ge=7, le=90),
    user_id: str = Depends(get_current_user_id)
):
    """Get formatted session history."""
    data = get_analytics_snapshot(user_id, days)
    sessions = data.get('sessions', [])
    return {
        'sessions': sessions,
        'total': len(sessions)
    }


@router.get("/weekly-report")
def get_weekly_report(user_id: str = Depends(get_current_user_id)):
    """
    Get this week's full report with improvement metrics
    and personalized recommendations.
    """
    try:
        generator = WeeklyReportGenerator(user_id)
        return generator.generate()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail='Weekly report unavailable right now'
        )


@router.get("/agent-stats")
def get_agent_stats(
    days: int = Query(default=30, ge=7, le=90),
    user_id: str = Depends(get_current_user_id)
):
    """Get agent effectiveness statistics."""
    data = get_analytics_snapshot(user_id, days)
    return data.get('agent_stats', {})

@router.get("/distractions")
def get_distraction_analysis(
    days: int = Query(7, ge=1, le=30),
    user_id: str = Depends(get_current_user_id)
):
    """
    Analyze which sites distract user most
    Returns top distracting domains with time spent
    """
    # Get browsing activity from last N days
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = run_db(
        lambda supabase: supabase.table('browsing_activity').select("*").eq('user_id', user_id).gte('timestamp', start_date).execute(),
        "Database unavailable while loading distraction analytics"
    )

    productive_domains = get_productive_domains(None, user_id)
    activities = [
        activity for activity in filter_activities_by_domain(result.data)
        if normalize_domain(activity.get('domain', '')) not in productive_domains
    ]
    
    # Group by domain
    domain_stats = defaultdict(lambda: {'total_seconds': 0, 'visit_count': 0})
    
    for activity in activities:
        domain = normalize_domain(activity.get('domain', ''))
        if not domain:
            continue
        duration = activity['duration_seconds'] or 0
        
        domain_stats[domain]['total_seconds'] += duration
        domain_stats[domain]['visit_count'] += 1
    
    # Convert to list and sort by time spent
    distraction_list = []
    for domain, stats in domain_stats.items():
        total_minutes = round(stats['total_seconds'] / 60, 1)
        total_hours = round(total_minutes / 60, 2)
        
        distraction_list.append({
            'domain': domain,
            'total_minutes': total_minutes,
            'total_hours': total_hours,
            'visit_count': stats['visit_count'],
            'avg_minutes_per_visit': round(total_minutes / stats['visit_count'], 1)
        })
    
    # Sort by total time
    distraction_list.sort(key=lambda x: x['total_minutes'], reverse=True)
    
    # Calculate totals
    total_distraction_minutes = sum(d['total_minutes'] for d in distraction_list)
    total_distraction_hours = round(total_distraction_minutes / 60, 2)
    
    return {
        "period_days": days,
        "total_distraction_hours": total_distraction_hours,
        "total_distraction_minutes": total_distraction_minutes,
        "unique_sites": len(distraction_list),
        "top_distractions": distraction_list[:10],  # Top 10
        "all_distractions": distraction_list
    }

@router.get("/time-breakdown")
def get_time_breakdown(
    days: int = Query(30, ge=7, le=90),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get time breakdown by site category.
    """
    data = get_analytics_snapshot(user_id, days)
    return data.get('time_breakdown', {})

@router.get("/hourly-pattern")
def get_hourly_pattern(
    days: int = Query(7, ge=1, le=30),
    user_id: str = Depends(get_current_user_id)
):
    """
    Analyze which hours user is most productive
    Returns focus time by hour of day
    """
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).gte('start_time', start_date).execute(),
        "Database unavailable while loading hourly analytics"
    )
    
    sessions = result.data
    
    # Group by hour
    hourly_stats = defaultdict(lambda: {'total_minutes': 0, 'session_count': 0, 'avg_focus_score': []})
    
    for session in sessions:
        if not session['end_time']:
            continue
        
        # Extract hour from start_time
        start_time = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00'))
        hour = start_time.hour
        
        hourly_stats[hour]['total_minutes'] += session['duration_minutes'] or 0
        hourly_stats[hour]['session_count'] += 1
        
        if session['focus_score']:
            hourly_stats[hour]['avg_focus_score'].append(session['focus_score'])
    
    # Convert to list
    hourly_breakdown = []
    for hour in range(24):
        stats = hourly_stats[hour]
        
        avg_score = 0
        if stats['avg_focus_score']:
            avg_score = round(sum(stats['avg_focus_score']) / len(stats['avg_focus_score']), 1)
        
        hourly_breakdown.append({
            'hour': hour,
            'hour_label': f"{hour:02d}:00",
            'total_minutes': stats['total_minutes'],
            'session_count': stats['session_count'],
            'avg_focus_score': avg_score
        })
    
    # Find peak hour
    peak_hour = max(hourly_breakdown, key=lambda x: x['total_minutes'])
    
    return {
        "period_days": days,
        "hourly_breakdown": hourly_breakdown,
        "peak_hour": peak_hour['hour'],
        "peak_hour_label": peak_hour['hour_label'],
        "peak_hour_minutes": peak_hour['total_minutes']
    }
