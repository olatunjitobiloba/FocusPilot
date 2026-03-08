# app/routes/recommendations.py
from fastapi import APIRouter, Depends
from app.auth import get_current_user_id
from app.database import get_supabase
from datetime import datetime, timedelta
from collections import defaultdict

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get("/")
def get_recommendations(user_id: str = Depends(get_current_user_id)):
    """
    Generate personalized recommendations based on user data
    """
    supabase = get_supabase()
    
    # Get recent data (last 14 days)
    start_date = (datetime.utcnow() - timedelta(days=14)).isoformat()
    
    sessions_result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).gte('start_time', start_date).execute()
    
    activities_result = supabase.table('browsing_activity').select("*").eq('user_id', user_id).gte('timestamp', start_date).execute()
    
    sessions = sessions_result.data
    activities = activities_result.data
    
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
    if activities:
        # Find sites visited during low-focus sessions
        low_focus_sessions = [s for s in sessions if s['focus_score'] and s['focus_score'] < 5]
        
        if low_focus_sessions:
            low_focus_session_ids = [s['id'] for s in low_focus_sessions]
            
            # Get activities during these sessions
            problem_activities = [a for a in activities if a['session_id'] in low_focus_session_ids]
            
            if problem_activities:
                # Count domain frequency
                domain_count = defaultdict(int)
                for activity in problem_activities:
                    domain_count[activity['domain']] += 1
                
                # Get top 3 problematic domains
                top_domains = sorted(domain_count.items(), key=lambda x: x[1], reverse=True)[:3]
                
                if top_domains:
                    domain_list = ', '.join([d[0] for d in top_domains])
                    
                    recommendations.append({
                        'type': 'block_sites',
                        'title': 'Sites to Block',
                        'message': f"You visit {domain_list} during low-focus sessions. Consider blocking them.",
                        'domains': [d[0] for d in top_domains],
                        'priority': 'high'
                    })
    
    # Recommendation 3: Best time to study
    if sessions:
        # Analyze hourly performance
        hourly_performance = defaultdict(lambda: {'total_score': 0, 'count': 0})
        
        for session in sessions:
            if session['focus_score']:
                hour = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00')).hour
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
