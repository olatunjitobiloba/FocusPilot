"""
Tests for execution endpoints.
Run with: pytest tests/test_executions.py -v
"""


class TestBlockState:
    """Test GET /execution/block-state"""

    def test_get_block_state_success(self, client, auth_headers):
        response = client.get('/execution/block-state', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert 'is_blocked' in data
        assert 'blocked_domains' in data

    def test_get_block_state_returns_degraded_on_executor_error(self, client, auth_headers, monkeypatch):
        def raise_error(*args, **kwargs):
            raise Exception('simulated block-state failure')

        monkeypatch.setattr('app.routes.executions.SiteBlockExecutor.get_block_state', raise_error)

        response = client.get('/execution/block-state', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['is_blocked'] is False
        assert data['blocked_domains'] == []
        assert data['status'] == 'degraded'
        assert 'error' in data
