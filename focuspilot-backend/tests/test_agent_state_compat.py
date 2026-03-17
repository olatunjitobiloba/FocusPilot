import pytest

from app.database import normalize_agent_state_payload, upsert_agent_state


class _FakeQuery:
    def __init__(self, client, payload):
        self.client = client
        self.payload = payload

    def execute(self):
        self.client.seen_payloads.append(dict(self.payload))
        if self.client.fail_once and 'cycle_count' in self.payload:
            self.client.fail_once = False
            raise Exception({
                'message': "Could not find the 'cycle_count' column of 'agent_state' in the schema cache",
                'code': 'PGRST204',
            })
        return {'data': [self.payload]}


class _FakeTable:
    def __init__(self, client):
        self.client = client

    def upsert(self, payload):
        return _FakeQuery(self.client, payload)


class _FakeClient:
    def __init__(self, fail_once=False):
        self.fail_once = fail_once
        self.seen_payloads = []

    def table(self, name):
        assert name == 'agent_state'
        return _FakeTable(self)


def test_normalize_agent_state_payload_flattens_dict_state():
    payload = normalize_agent_state_payload({
        'user_id': 'u1',
        'risk_score': 0.8,
        'state': {
            'current_risk': 0.8,
            'last_assessed': '2026-03-15T00:00:00Z',
        },
    })

    assert payload['state'] == 'idle'
    assert payload['risk_score'] == 0.8
    assert payload['last_cycle'] == '2026-03-15T00:00:00Z'


def test_upsert_agent_state_retries_without_unknown_column(monkeypatch):
    fake_client = _FakeClient(fail_once=True)

    def fake_execute_with_retries(operation, retries=2, base_delay_seconds=0.12):
        return operation(fake_client)

    monkeypatch.setattr('app.database.execute_with_retries', fake_execute_with_retries)

    result = upsert_agent_state({
        'user_id': 'u1',
        'state': 'active',
        'risk_score': 0.61,
        'cycle_count': 7,
    })

    assert result == {'data': [{'user_id': 'u1', 'state': 'active', 'risk_score': 0.61}]}
    assert fake_client.seen_payloads == [
        {
            'user_id': 'u1',
            'state': 'active',
            'risk_score': 0.61,
            'cycle_count': 7,
        },
        {
            'user_id': 'u1',
            'state': 'active',
            'risk_score': 0.61,
        },
    ]


def test_upsert_agent_state_caches_unsupported_columns(monkeypatch):
    fake_client = _FakeClient(fail_once=True)

    def fake_execute_with_retries(operation, retries=2, base_delay_seconds=0.12):
        return operation(fake_client)

    monkeypatch.setattr('app.database.execute_with_retries', fake_execute_with_retries)
    monkeypatch.setattr('app.database._agent_state_unsupported_columns', set())

    upsert_agent_state({
        'user_id': 'u1',
        'state': 'active',
        'risk_score': 0.61,
        'cycle_count': 7,
    })

    # First call fails once, then succeeds without unsupported column.
    assert len(fake_client.seen_payloads) == 2

    fake_client.seen_payloads.clear()

    upsert_agent_state({
        'user_id': 'u1',
        'state': 'active',
        'risk_score': 0.62,
        'cycle_count': 8,
    })

    # Second call should skip unsupported column immediately.
    assert fake_client.seen_payloads == [
        {
            'user_id': 'u1',
            'state': 'active',
            'risk_score': 0.62,
        }
    ]
