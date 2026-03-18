# app/analytics/report_generator.py
"""
Weekly Report Generator — builds a structured weekly report.

The report contains:
- Week summary (sessions, hours, avg score)
- Improvement vs previous week
- Top achievements
- Areas to improve
- Agent performance
- Recommendations for next week
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Any
from app.analytics.aggregator import AnalyticsAggregator


class WeeklyReportGenerator:

    def __init__(self, user_id: str):
        self.user_id    = user_id
        self.aggregator = AnalyticsAggregator(user_id)

    def generate(self) -> Dict[str, Any]:
        """
        Generate this week's report.
        Compares to last week for improvement metrics.
        """
        print(f"📋 Generating weekly report for {self.user_id[:8]}")

        # This week (last 7 days)
        this_week = self.aggregator.compute_all(days=7)

        # Last week (days 8-14)
        last_week = self._compute_last_week()

        # Build report
        report = {
            'week_label':    self._get_week_label(),
            'generated_at':  datetime.utcnow().isoformat(),
            'this_week':     this_week['summary'],
            'last_week':     last_week,
            'improvement':   self._compute_improvement(
                this_week['summary'],
                last_week
            ),
            'achievements':  self._find_achievements(this_week),
            'improvements':  self._find_improvements(this_week),
            'agent_summary': this_week['agent_stats'],
            'streak':        this_week['streak'],
            'best_day':      this_week['best_day'],
            'best_hour':     this_week['best_hour'],
            'daily_data':    this_week['daily_breakdown'][-7:],
            'recommendations': self._generate_recommendations(
                this_week,
                last_week
            )
        }

        return report

    def _compute_last_week(self) -> Dict:
        """Compute summary for the previous week (days 8-14)."""
        supabase = self.aggregator.supabase
        since_14 = (
            datetime.utcnow() - timedelta(days=14)
        ).isoformat()
        since_7  = (
            datetime.utcnow() - timedelta(days=7)
        ).isoformat()

        # Load sessions from 14-7 days ago
        result = (
            supabase
            .table('focus_sessions')
            .select("*")
            .eq('user_id', self.user_id)
            .gte('start_time', since_14)
            .lt('start_time', since_7)
            .not_.is_('end_time', 'null')
            .execute()
        )
        sessions = result.data or []

        if not sessions:
            return {
                'total_sessions':      0,
                'total_focused_hours': 0.0,
                'avg_focus_score':     0.0,
                'completion_rate':     0.0
            }

        total_mins = 0.0
        for s in sessions:
            start = self.aggregator._parse_datetime(s['start_time'])
            end = self.aggregator._parse_datetime(s['end_time'])
            total_mins += (end - start).total_seconds() / 60

        scores = [
            s['focus_score'] for s in sessions
            if s.get('focus_score') is not None
        ]

        return {
            'total_sessions':      len(sessions),
            'total_focused_hours': round(total_mins / 60, 1),
            'avg_focus_score':     round(
                sum(scores) / len(scores), 1
            ) if scores else 0.0,
            'completion_rate':     round(
                len(scores) / len(sessions) * 100, 1
            )
        }

    def _compute_improvement(
        self,
        this_week: Dict,
        last_week: Dict
    ) -> Dict:
        """Compute % improvement vs last week."""

        def pct_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round((current - previous) / previous * 100, 1)

        return {
            'sessions_pct': pct_change(
                this_week.get('total_sessions', 0),
                last_week.get('total_sessions', 0)
            ),
            'hours_pct': pct_change(
                this_week.get('total_focused_hours', 0),
                last_week.get('total_focused_hours', 0)
            ),
            'score_pct': pct_change(
                this_week.get('avg_focus_score', 0),
                last_week.get('avg_focus_score', 0)
            ),
            'is_improving': (
                this_week.get('avg_focus_score', 0) >=
                last_week.get('avg_focus_score', 0)
            )
        }

    def _find_achievements(self, analytics: Dict) -> List[Dict]:
        """Find positive achievements this week."""
        achievements = []
        summary      = analytics.get('summary', {})
        streak       = analytics.get('streak', {})

        if summary.get('total_focused_hours', 0) >= 10:
            achievements.append({
                'icon':  '🏆',
                'title': '10+ Hours Focused',
                'body':  f"You focused for {summary['total_focused_hours']} hours this week!"
            })

        if summary.get('avg_focus_score', 0) >= 7.5:
            achievements.append({
                'icon':  '⭐',
                'title': 'High Focus Score',
                'body':  f"Average score of {summary['avg_focus_score']}/10 this week"
            })

        if streak.get('current_streak', 0) >= 3:
            achievements.append({
                'icon':  '🔥',
                'title': f"{streak['current_streak']}-Day Streak!",
                'body':  "You have focused every day for multiple days in a row"
            })

        if summary.get('completion_rate', 0) >= 80:
            achievements.append({
                'icon':  '✅',
                'title': 'High Completion Rate',
                'body':  f"{summary['completion_rate']}% of sessions completed"
            })

        if summary.get('total_sessions', 0) >= 14:
            achievements.append({
                'icon':  '📚',
                'title': '14+ Sessions This Week',
                'body':  'Excellent consistency — 2+ sessions per day!'
            })

        return achievements[:4]

    def _find_improvements(self, analytics: Dict) -> List[Dict]:
        """Find areas that need improvement."""
        improvements = []
        summary      = analytics.get('summary', {})
        agent_stats  = analytics.get('agent_stats', {})

        if summary.get('total_sessions', 0) < 5:
            improvements.append({
                'icon':  '📅',
                'title': 'Session Frequency',
                'body':  'Try to complete at least 1 session per day'
            })

        if summary.get('avg_focus_score', 0) < 5.0:
            improvements.append({
                'icon':  '🎯',
                'title': 'Focus Score',
                'body':  'Your average focus score is below 5. Try shorter sessions.'
            })

        if summary.get('total_distraction_mins', 0) > 60:
            improvements.append({
                'icon':  '📱',
                'title': 'Distraction Time',
                'body':  (
                    f"{summary['total_distraction_mins']} minutes spent on "
                    f"distracting sites. Use site blocking during sessions."
                )
            })

        if agent_stats.get('intervention_success_rate', 100) < 50:
            improvements.append({
                'icon':  '🤖',
                'title': 'Agent Response Rate',
                'body':  'You are ignoring most agent interventions. Try acting on them.'
            })

        return improvements[:3]

    def _generate_recommendations(
        self,
        this_week: Dict,
        last_week: Dict
    ) -> List[str]:
        """Generate 3-5 actionable recommendations."""
        recs    = []
        summary = this_week.get('summary', {})
        best_h  = this_week.get('best_hour', {})
        best_d  = this_week.get('best_day', {})

        if best_h.get('hour_label'):
            recs.append(
                f"Schedule your most important work at "
                f"{best_h['hour_label']} — your peak focus hour"
            )

        if best_d.get('day_name'):
            recs.append(
                f"Plan your hardest tasks on {best_d['day_name']}s "
                f"— your best focus day (avg {best_d['avg_score']}/10)"
            )

        avg_dur = summary.get('avg_session_duration', 25)
        recs.append(
            f"Your optimal session length is ~{round(avg_dur)} minutes. "
            f"Stick to this for best results."
        )

        if summary.get('total_distraction_mins', 0) > 30:
            recs.append(
                "Enable site blocking at the start of every session "
                "to cut distraction time"
            )

        if summary.get('total_sessions', 0) < 7:
            recs.append(
                "Aim for at least 1 session per day to build consistency"
            )

        return recs[:4]

    def _get_week_label(self) -> str:
        today     = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end   = week_start + timedelta(days=6)
        return (
            f"{week_start.strftime('%b %d')} – "
            f"{week_end.strftime('%b %d, %Y')}"
        )
