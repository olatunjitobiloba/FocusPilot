from app.ml.agent import observer
from app.routes import agent as agent_routes


def test_observer_parse_datetime_handles_high_precision_fractional_seconds():
    dt = observer._parse_datetime("2026-03-17T16:59:40.07506123Z")
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 17
    assert dt.hour == 16
    assert dt.minute == 59
    assert dt.second == 40
    assert dt.microsecond == 75061


def test_notifications_uses_retry_wrapper_for_queries(monkeypatch):
    calls = {"retry": 0}

    class _Result:
        def __init__(self, data):
            self.data = data

    class _TableQuery:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            if self.table_name == "notification_queue":
                return _Result([
                    {
                        "type": "site_block",
                        "extra_data": None,
                        "title": "Procrastination detected",
                        "message": "",
                    }
                ])
            return _Result([
                {"blocked_domains": ["youtube.com"], "unblock_at": None}
            ])

    class _Supabase:
        def table(self, name):
            return _TableQuery(name)

    def _fake_retry(operation, retries=3, base_delay_seconds=0.15):
        calls["retry"] += 1
        return operation(_Supabase())

    monkeypatch.setattr("app.routes.agent.get_supabase", lambda: _Supabase())
    monkeypatch.setattr("app.routes.agent.execute_with_retries", _fake_retry)

    payload = agent_routes.get_notifications(
        unread_only=True,
        limit=50,
        user_id="user-1",
    )

    assert payload["unread_count"] == 1
    assert payload["notifications"][0]["title"] == "Focus Reminder"
    assert calls["retry"] >= 2
