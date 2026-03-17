# app/ml/clustering/insight_generator.py
"""
Insight Generator — turns cluster data into human-readable insights.

Generates:
1. Peak focus hours (when the user focuses best)
2. Best session length (optimal duration)
3. Worst patterns (what to avoid)
4. Personalized recommendations
"""

import numpy as np
from typing import Dict, List, Any
from app.ml.clustering.feature_extractor import FEATURE_NAMES


class InsightGenerator:

    def generate_all(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        profiles: List[Dict],
        sessions: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate all insights from clustering results.

        Returns:
            peak_hours:          Best hours to focus
            best_session_length: Optimal session duration
            worst_patterns:      Patterns to avoid
            insights:            Actionable text insights
            heatmap_data:        Hour × DayOfWeek focus grid
        """
        return {
            'peak_hours':          self._find_peak_hours(X, labels, profiles),
            'best_session_length': self._find_best_session_length(
                X, labels, profiles
            ),
            'worst_patterns':      self._find_worst_patterns(
                X, labels, profiles
            ),
            'insights':            self._generate_insights(
                X, labels, profiles, sessions
            ),
            'heatmap_data':        self._build_heatmap(X, labels, profiles)
        }

    # ── Peak hours ─────────────────────────────────────────────────────

    def _find_peak_hours(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        Find hours where the user focuses best.
        Looks at the best cluster (highest quality) and
        finds which hours have the most sessions in it.
        """
        if not profiles:
            return []

        # Best cluster = highest quality score
        best_cluster_id = profiles[0]['cluster_id']
        best_mask       = labels == best_cluster_id
        best_X          = X[best_mask]

        if len(best_X) == 0:
            return []

        # Count sessions per hour in best cluster
        hours  = best_X[:, 0].astype(int)
        counts = np.bincount(hours, minlength=24)

        # Get top 3 hours
        top_hours = np.argsort(counts)[::-1][:3]
        top_hours = [h for h in top_hours if counts[h] > 0]

        peak_hours = []
        for h in top_hours:
            peak_hours.append({
                'hour':          int(h),
                'hour_label':    self._format_hour(h),
                'session_count': int(counts[h]),
                'quality':       profiles[0]['quality_score']
            })

        return peak_hours

    # ── Best session length ────────────────────────────────────────────

    def _find_best_session_length(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        profiles: List[Dict]
    ) -> Dict:
        """
        Find the session duration that correlates with best focus.
        """
        if not profiles:
            return {}

        best_cluster_id = profiles[0]['cluster_id']
        best_mask       = labels == best_cluster_id
        best_X          = X[best_mask]

        if len(best_X) == 0:
            return {}

        durations = best_X[:, 2]   # duration_minutes is index 2

        avg_duration = float(durations.mean())
        min_duration = float(durations.min())
        max_duration = float(durations.max())

        # Determine bucket
        if avg_duration < 20:
            bucket = 'short'
            label  = 'Short (< 20 min)'
        elif avg_duration <= 45:
            bucket = 'medium'
            label  = 'Medium (20-45 min)'
        else:
            bucket = 'long'
            label  = 'Long (> 45 min)'

        return {
            'avg_minutes':  round(avg_duration, 1),
            'min_minutes':  round(min_duration, 1),
            'max_minutes':  round(max_duration, 1),
            'bucket':       bucket,
            'label':        label,
            'recommendation': (
                f"Your best sessions average "
                f"{round(avg_duration)} minutes. "
                f"Aim for {round(avg_duration - 5)}-"
                f"{round(avg_duration + 5)} minute sessions."
            )
        }

    # ── Worst patterns ─────────────────────────────────────────────────

    def _find_worst_patterns(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        Find patterns that correlate with poor focus.
        Looks at the worst cluster (lowest quality score).
        """
        if len(profiles) < 2:
            return []

        # Worst cluster = lowest quality score
        worst_profile   = profiles[-1]
        worst_cluster_id = worst_profile['cluster_id']
        worst_mask      = labels == worst_cluster_id
        worst_X         = X[worst_mask]

        if len(worst_X) == 0:
            return []

        patterns = []
        means    = worst_X.mean(axis=0)

        feature_dict = {
            name: float(means[i])
            for i, name in enumerate(FEATURE_NAMES)
        }

        # Check each pattern
        if feature_dict['is_evening'] > 0.6:
            patterns.append({
                'pattern':     'Evening Sessions',
                'description': 'Your focus drops significantly in the evening',
                'icon':        '🌙',
                'severity':    'high'
            })

        if feature_dict['is_weekend'] > 0.6:
            patterns.append({
                'pattern':     'Weekend Sessions',
                'description': 'You tend to struggle more on weekends',
                'icon':        '📅',
                'severity':    'medium'
            })

        if feature_dict['distraction_ratio'] > 0.5:
            pct = round(feature_dict['distraction_ratio'] * 100)
            patterns.append({
                'pattern':     'High Distraction Window',
                'description': (
                    f"Sessions in this pattern spend "
                    f"{pct}% of time on distracting sites"
                ),
                'icon':        '📱',
                'severity':    'high'
            })

        if feature_dict['session_completed'] < 0.4:
            patterns.append({
                'pattern':     'Low Completion Rate',
                'description': 'These sessions are often abandoned early',
                'icon':        '⏹️',
                'severity':    'medium'
            })

        if feature_dict['task_switches'] > 10:
            patterns.append({
                'pattern':     'Excessive Task Switching',
                'description': (
                    f"Switching between tasks "
                    f"{round(feature_dict['task_switches'])}+ times per session"
                ),
                'icon':        '🔀',
                'severity':    'medium'
            })

        return patterns[:4]

    # ── Text insights ──────────────────────────────────────────────────

    def _generate_insights(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        profiles: List[Dict],
        sessions: List[Dict]
    ) -> List[Dict]:
        """
        Generate 4-6 actionable text insights.
        """
        insights = []

        if not profiles:
            return insights

        best  = profiles[0]
        worst = profiles[-1] if len(profiles) > 1 else None

        # Insight 1: Best cluster summary
        insights.append({
            'type':    'success',
            'icon':    '🏆',
            'title':   f"Your Best Pattern: {best['name']}",
            'body': (
                f"{best['n_sessions']} of your sessions "
                f"({best['pct_of_total']}%) are high-quality. "
                f"These average {best['avg_duration']} minutes "
                f"with only {best['avg_distraction']}% distraction."
            )
        })

        # Insight 2: Peak hour
        peak_hour = best.get('peak_hour', 9)
        insights.append({
            'type':  'info',
            'icon':  '⏰',
            'title': 'Your Peak Focus Hour',
            'body': (
                f"You do your best work around "
                f"{self._format_hour(peak_hour)}. "
                f"Schedule your most important tasks then."
            )
        })

        # Insight 3: Worst pattern (if exists)
        if worst and worst['cluster_id'] != best['cluster_id']:
            insights.append({
                'type':  'warning',
                'icon':  '⚠️',
                'title': f"Watch Out: {worst['name']} Pattern",
                'body': (
                    f"{worst['n_sessions']} sessions "
                    f"({worst['pct_of_total']}%) follow this pattern. "
                    f"Average focus score: {worst['avg_focus_score']}/10. "
                    f"Distraction: {worst['avg_distraction']}%."
                )
            })

        # Insight 4: Completion rate
        all_completions = X[:, 7]   # session_completed index
        overall_completion = float(all_completions.mean()) * 100
        insights.append({
            'type':  'info',
            'icon':  '✅',
            'title': 'Session Completion Rate',
            'body': (
                f"You complete {round(overall_completion)}% of your "
                f"planned sessions. "
                + (
                    "Excellent consistency!"
                    if overall_completion >= 70
                    else "Try shorter sessions to improve completion."
                )
            )
        })

        # Insight 5: Distraction pattern
        all_distraction = X[:, 4].mean() * 100   # distraction_ratio
        insights.append({
            'type':  'warning' if all_distraction > 30 else 'success',
            'icon':  '📱' if all_distraction > 30 else '🎯',
            'title': 'Overall Distraction Level',
            'body': (
                f"On average, {round(all_distraction)}% of your "
                f"session time is spent on distracting sites. "
                + (
                    "This is above the 30% threshold. "
                    "Consider blocking sites during sessions."
                    if all_distraction > 30
                    else "Great job keeping distractions low!"
                )
            )
        })

        # Insight 6: Cluster diversity
        if len(profiles) >= 3:
            insights.append({
                'type':  'info',
                'icon':  '🧬',
                'title': f"{len(profiles)} Distinct Focus Patterns Found",
                'body': (
                    f"Your sessions fall into {len(profiles)} behavioral "
                    f"clusters. Understanding each pattern helps you "
                    f"replicate your best and avoid your worst."
                )
            })

        return insights

    # ── Heatmap ────────────────────────────────────────────────────────

    def _build_heatmap(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        Build hour × day-of-week focus quality heatmap.

        Returns list of {hour, day, quality, count} dicts.
        Used by the frontend to render a heatmap.
        """
        # Build quality score per (hour, day) cell
        heatmap: Dict[tuple, List[float]] = {}

        # Map cluster_id → quality score
        quality_map = {
            p['cluster_id']: p['quality_score']
            for p in profiles
        }

        for i, label in enumerate(labels):
            hour    = int(X[i, 0])
            day     = int(X[i, 1])
            quality = quality_map.get(int(label), 50)

            key = (hour, day)
            if key not in heatmap:
                heatmap[key] = []
            heatmap[key].append(quality)

        # Convert to list
        result = []
        for (hour, day), qualities in heatmap.items():
            result.append({
                'hour':    hour,
                'day':     day,
                'day_name': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day],
                'quality': round(sum(qualities) / len(qualities)),
                'count':   len(qualities)
            })

        return result

    # ── Helpers ────────────────────────────────────────────────────────

    def _format_hour(self, hour: int) -> str:
        """Format hour as human-readable string."""
        if hour == 0:
            return "12:00 AM"
        elif hour < 12:
            return f"{hour}:00 AM"
        elif hour == 12:
            return "12:00 PM"
        else:
            return f"{hour - 12}:00 PM"
