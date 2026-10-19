"""Cross-cutting persisted optimistic locking; app reopen is not process restart.

No model/network fixture or credentials. Production endpoints/store are exercised.
"""
from fastapi.testclient import TestClient
from services.api.main import create_app


def test_stale_multi_panel_edits_after_app_reopen_and_legacy_writer(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        workspace, foreign = [w['id'] for w in client.get('/api/workspaces').json()]
        params = {'workspace_id': workspace}
        preferences = '/api/console/preferences'
        budget = '/api/console/budget'
        memory = client.post('/api/memories', json={
            'workspace_id': workspace, 'content': 'initial evidence',
        }).json()
        # Legacy creation response omits revision; the API's initial version is1.
        initial_revision = memory.get('revision', 1)
        path = '/api/memories/' + memory['id']
        pref_revision = client.get(preferences, params=params).json()['revision']
        budget_revision = client.get(budget, params=params).json()['policy']['revision']
        assert client.patch(preferences, params=params, json={
            'revision': pref_revision, 'theme': 'light',
        }).status_code == 200
        assert client.patch(budget, params=params, json={
            'revision': budget_revision, 'monthly_token_threshold': 71,
        }).status_code == 200
        # Legacy clients intentionally remain supported. Their writes must still
        # invalidate versioned clients' previously read revision across reopen.
        assert client.patch(path, json={'content': 'legacy committed fact'}).status_code == 200

    with TestClient(create_app(tmp_path)) as client:
        assert client.patch(preferences, params=params, json={
            'revision': pref_revision, 'theme': 'dark',
        }).status_code == 409
        assert client.patch(budget, params=params, json={
            'revision': budget_revision, 'monthly_token_threshold': 999,
        }).status_code == 409
        assert client.patch(path, params=params, json={
            'expected_revision': initial_revision, 'content': 'stale overwrite',
        }).status_code == 409
        assert client.delete(path, params={
            **params, 'expected_revision': initial_revision,
        }).status_code == 409
        assert client.patch(path, params={'workspace_id': foreign}, json={
            'expected_revision': initial_revision + 1, 'content': 'foreign overwrite',
        }).status_code == 404
        assert client.get(preferences, params=params).json()['theme'] == 'light'
        policy = client.get(budget, params=params).json()['policy']
        assert policy['monthly_token_threshold'] == 71
        assert policy['revision'] == budget_revision + 1
        stored = next(m for m in client.get('/api/memories', params=params).json()
                      if m['id'] == memory['id'])
        assert stored['content'] == 'legacy committed fact'
        assert stored['revision'] == initial_revision + 1
        assert len(client.get(path + '/history').json()) == 1
        assert len(client.get(budget + '/history', params=params).json()) == 1
        # Reload-and-retry succeeds: conflict handling has not wedged the record.
        assert client.patch(path, params=params, json={
            'expected_revision': stored['revision'], 'content': 'reconciled evidence',
        }).status_code == 200
        assert client.patch(budget, params=params, json={
            'revision': policy['revision'], 'monthly_cost_threshold': 2,
        }).status_code == 200
        assert client.get(budget, params={'workspace_id': foreign}).json()['policy']['revision'] == 1

    with TestClient(create_app(tmp_path)) as client:
        stored = next(m for m in client.get('/api/memories', params=params).json()
                      if m['id'] == memory['id'])
        assert stored['content'] == 'reconciled evidence'
        assert stored['revision'] == initial_revision + 2
        policy = client.get(budget, params=params).json()['policy']
        assert policy['monthly_token_threshold'] == 71
        assert policy['monthly_cost_threshold'] == 2
