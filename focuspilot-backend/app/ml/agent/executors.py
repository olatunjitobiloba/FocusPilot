# app/ml/agent/executors.py
"""
Action Executors — the actual logic for each action type.

Each executor:
1. Validates input data
2. Executes the action
3. Returns a result dict
4. Raises an exception if it fails

Executors do NOT log. The ExecutionAgent handles logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from app.database import get_supabase


class SiteBlockExecutor:
    """Executes site blocking via the notification queue."""

    # Default distraction domains to block
    DEFAULT_BLOCK_DOMAINS = [
        'youtube.com',
        'twitter.com',
        'instagram.com',
        'tiktok.com',
        'reddit.com',
        'facebook.com',
        'netflix.com',
        'twitch.tv'
    ]

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    @staticmethod
    def _is_missing_extra_data_column_error(error: Exception) -> bool:
        error_text = str(error)
        return (
            'notification_queue' in error_text
            and 'extra_data' in error_text
            and 'Could not find' in error_text
        )

    def _insert_notification(self, payload: Dict[str, Any]) -> None:
        """
        Insert notification payload, retrying without extra_data for older DB schemas.
        """
        try:
            self.supabase.table('notification_queue').insert(payload).execute()
        except Exception as error:
            if (
                'extra_data' in payload
                and self._is_missing_extra_data_column_error(error)
            ):
                fallback_payload = dict(payload)
                fallback_payload.pop('extra_data', None)
                self.supabase.table('notification_queue').insert(
                    fallback_payload
                ).execute()
                return
            raise

    @staticmethod
    def _is_duplicate_site_block_state_user_error(error: Exception) -> bool:
        error_text = str(error)
        return (
            'duplicate key value violates unique constraint' in error_text
            and 'site_block_state_user_id_key' in error_text
        )

    def _save_block_state(self, payload: Dict[str, Any]) -> None:
        """
        Persist state, tolerating legacy upsert behavior that ignores unique user_id.
        """
        try:
            self.supabase.table('site_block_state').upsert(payload).execute()
        except Exception as error:
            if self._is_duplicate_site_block_state_user_error(error):
                self.supabase.table('site_block_state').update(payload).eq(
                    'user_id', self.user_id
                ).execute()
                return
            raise

    def block(
        self,
        domains: List[str] = None,
        duration_minutes: int = 25,
        reason: str = "Agent activated focus mode"
    ) -> Dict:
        """
        Block distraction sites.

        How it works:
        1. Save block state to DB
        2. Push block command to notification queue
        3. Extension polls queue and activates blocking
        4. Schedule auto-unblock
        """
        domains_to_block = domains or self.DEFAULT_BLOCK_DOMAINS
        now_utc          = datetime.now(timezone.utc)
        unblock_at       = now_utc + timedelta(minutes=duration_minutes)

        # ── Save block state ───────────────────────────────────────────
        self._save_block_state({
            'user_id':         self.user_id,
            'is_blocked':      True,
            'blocked_domains': domains_to_block,
            'blocked_at':      now_utc.isoformat(),
            'unblock_at':      unblock_at.isoformat(),
            'block_reason':    reason
        })

        # ── Push command to extension via notification queue ───────────
        self._insert_notification({
            'user_id': self.user_id,
            'title':   '🔒 Focus Mode Activated',
            'message': (
                f"Blocking {len(domains_to_block)} distraction sites "
                f"for {duration_minutes} minutes."
            ),
            'type':    'site_block',
            'read':    False,
            'created_at': now_utc.isoformat(),
            # Extra data for extension to read
            'extra_data': {
                'command':          'block_sites',
                'domains':          domains_to_block,
                'duration_minutes': duration_minutes,
                'unblock_at':       unblock_at.isoformat()
            }
        })

        # ── Schedule auto-unblock ──────────────────────────────────────
        self.supabase.table('scheduled_actions').insert({
            'user_id':      self.user_id,
            'action_type':  'unblock_sites',
            'action_data':  {'domains': domains_to_block},
            'scheduled_for': unblock_at.isoformat(),
            'status':       'pending'
        }).execute()

        print(
            f"   🔒 Blocked {len(domains_to_block)} sites "
            f"for {duration_minutes} minutes"
        )

        return {
            'blocked_domains':  domains_to_block,
            'duration_minutes': duration_minutes,
            'unblock_at':       unblock_at.isoformat(),
            'domains_count':    len(domains_to_block)
        }

    def unblock(self) -> Dict:
        """Remove all site blocks."""
        # Update block state
        self._save_block_state({
            'user_id':    self.user_id,
            'is_blocked': False,
            'blocked_domains': []
        })

        # Push unblock command to extension
        self._insert_notification({
            'user_id': self.user_id,
            'title':   '🔓 Sites Unblocked',
            'message': 'Focus mode ended. Sites are now accessible.',
            'type':    'site_unblock',
            'read':    False,
            'extra_data': {'command': 'unblock_sites'}
        })

        print("   🔓 Sites unblocked")

        return {'unblocked': True}

    def get_block_state(self) -> Dict:
        """Get current block state."""
        result = (
            self.supabase
            .table('site_block_state')
            .select("*")
            .eq('user_id', self.user_id)
            .execute()
        )

        if not result.data:
            return {
                'is_blocked':      False,
                'blocked_domains': [],
                'unblock_at':      None
            }

        state = result.data[0]

        # Check if block has expired
        if state.get('unblock_at'):
            unblock_at = datetime.fromisoformat(
                state['unblock_at'].replace('Z', '+00:00')
            )

            if unblock_at.tzinfo is None:
                unblock_at = unblock_at.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) >= unblock_at and state['is_blocked']:
                self.unblock()
                state['is_blocked'] = False

        return state


class SessionExecutor:
    """Executes session management actions."""

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def auto_start_session(
        self,
        duration_minutes: int = 25,
        reason: str = "Agent auto-started session"
    ) -> Dict:
        """
        Automatically start a new focus session.

        Only starts if no session is currently active.
        """
        # Check for active session
        active = (
            self.supabase
            .table('focus_sessions')
            .select("id")
            .eq('user_id', self.user_id)
            .is_('end_time', 'null')
            .execute()
        )

        if active.data:
            return {
                'started':  False,
                'reason':   'Session already active',
                'session_id': active.data[0]['id']
            }

        # Create new session
        result = (
            self.supabase
            .table('focus_sessions')
            .insert({
                'user_id':          self.user_id,
                'start_time':       datetime.utcnow().isoformat(),
                'duration_minutes': duration_minutes,
                'auto_started':     True,
                'start_reason':     reason
            })
            .execute()
        )

        session_id = result.data[0]['id'] if result.data else None

        # Notify user
        self.supabase.table('notification_queue').insert({
            'user_id': self.user_id,
            'title':   '▶️ Session Auto-Started',
            'message': (
                f"Your agent started a {duration_minutes}-minute "
                f"focus session. Let's make it count!"
            ),
            'type':    'session_start',
            'read':    False
        }).execute()

        print(f"   ▶️ Auto-started {duration_minutes}-min session")

        return {
            'started':          True,
            'session_id':       session_id,
            'duration_minutes': duration_minutes
        }

    def auto_end_session(
        self,
        session_id: str,
        reason: str = "Excessive procrastination detected"
    ) -> Dict:
        """
        End a session that has been too distracted to be productive.
        """
        self.supabase.table('focus_sessions').update({
            'end_time':   datetime.utcnow().isoformat(),
            'end_reason': reason,
            'auto_ended': True
        }).eq('id', session_id).execute()

        # Notify user
        self.supabase.table('notification_queue').insert({
            'user_id': self.user_id,
            'title':   '⏹️ Session Ended by Agent',
            'message': (
                f"Session ended: {reason}. "
                f"Take a 5-minute break and start fresh."
            ),
            'type':    'session_end',
            'read':    False
        }).execute()

        print(f"   ⏹️ Auto-ended session: {reason}")

        return {
            'ended':      True,
            'session_id': session_id,
            'reason':     reason
        }


class NudgeExecutor:
    """Executes nudge and notification actions."""

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def send_nudge(
        self,
        title: str,
        message: str,
        nudge_type: str = 'focus_nudge'
    ) -> Dict:
        """Send an immediate nudge notification."""
        result = (
            self.supabase
            .table('notification_queue')
            .insert({
                'user_id':    self.user_id,
                'title':      title,
                'message':    message,
                'type':       nudge_type,
                'read':       False,
                'created_at': datetime.utcnow().isoformat()
            })
            .execute()
        )

        print(f"   📢 Nudge sent: {title}")

        return {
            'sent':       True,
            'title':      title,
            'message':    message,
            'nudge_id':   result.data[0]['id'] if result.data else None
        }

    def schedule_nudge(
        self,
        message: str,
        scheduled_for: str,
        title: str = "⏰ Focus Reminder"
    ) -> Dict:
        """Schedule a nudge for a future time."""
        result = (
            self.supabase
            .table('scheduled_actions')
            .insert({
                'user_id':     self.user_id,
                'action_type': 'send_nudge',
                'action_data': {
                    'title':   title,
                    'message': message
                },
                'scheduled_for': scheduled_for,
                'status':        'pending'
            })
            .execute()
        )

        print(f"   ⏰ Nudge scheduled for {scheduled_for}")

        return {
            'scheduled':     True,
            'scheduled_for': scheduled_for,
            'schedule_id':   result.data[0]['id'] if result.data else None
        }
