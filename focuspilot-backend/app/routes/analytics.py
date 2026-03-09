# app/routes/analytics.py
from fastapi import APIRouter, Depends, Query
from app.auth import get_current_user_id
from app.database import get_supabase
from app.domain_whitelist import filter_activities_by_domain
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/distractions")
def get_distraction_analysis(
    days: int = Query(7, ge=1, le=30),
    user_id: str = Depends(get_current_user_id)
):
    """
    Analyze which sites distract user most
    Returns top distracting domains with time spent
    """
    supabase = get_supabase()
    
    # Get browsing activity from last N days
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    result = supabase.table('browsing_activity').select("*").eq('user_id', user_id).gte('timestamp', start_date).execute()
    
    activities = filter_activities_by_domain(result.data)
    
    # Group by domain
    domain_stats = defaultdict(lambda: {'total_seconds': 0, 'visit_count': 0})
    
    for activity in activities:
        domain = activity['domain']
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
    days: int = Query(7, ge=1, le=30),
    user_id: str = Depends(get_current_user_id)
):
    """
    Break down time by category (productive vs distracting)
    """
    supabase = get_supabase()
    
    # Get sessions and activities
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    sessions_result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).gte('start_time', start_date).execute()
    
    activities_result = supabase.table('browsing_activity').select("*").eq('user_id', user_id).gte('timestamp', start_date).execute()
    
    sessions = sessions_result.data
    activities = filter_activities_by_domain(activities_result.data)
    
    # Calculate focus time
    total_focus_minutes = sum(s['duration_minutes'] or 0 for s in sessions if s['end_time'])
    
    # Calculate distraction time (time on blocked sites during sessions)
    # For now, we'll use all browsing activity as potential distraction
    total_distraction_seconds = sum(a['duration_seconds'] or 0 for a in activities)
    total_distraction_minutes = total_distraction_seconds / 60
    
    # Calculate productive time (focus time - distraction time)
    productive_minutes = max(total_focus_minutes - total_distraction_minutes, 0)
    
    return {
        "period_days": days,
        "total_focus_minutes": round(total_focus_minutes, 1),
        "productive_minutes": round(productive_minutes, 1),
        "distraction_minutes": round(total_distraction_minutes, 1),
        "productive_hours": round(productive_minutes / 60, 2),
        "distraction_hours": round(total_distraction_minutes / 60, 2),
        "productivity_percentage": round((productive_minutes / max(total_focus_minutes, 1)) * 100, 1)
    }

@router.get("/hourly-pattern")
def get_hourly_pattern(
    days: int = Query(7, ge=1, le=30),
    user_id: str = Depends(get_current_user_id)
):
    """
    Analyze which hours user is most productive
    Returns focus time by hour of day
    """
    supabase = get_supabase()
    
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).gte('start_time', start_date).execute()
    
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
