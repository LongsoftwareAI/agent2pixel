"""Console memory edits use compare-and-swap; legacy unversioned clients still work."""
from fastapi.testclient import TestClient
from services.api.main import create_app


def test_stale_editor_delete_and_foreign_workspace_cannot_overwrite_memory(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        workspaces = client.get('/api/workspaces').json()
        workspace, foreign = [w['id'] for w in workspaces]
        memory = client.post('/api/memories', json={
            'workspace_id': workspace, 'content': 'original evidence',
        }).json()
        path = '/api/memories/' + memory['id']
        params = {'workspace_id': workspace}
        edited = client.patch(path, params=params, json={
            'content': 'first editor committed', 'expected_revision': 1,
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['revision'] == 2
        assert 'expected_revision' not in edited.json()
        assert client.patch(path, params=params, json={
            'content': 'stale editor must not win', 'expected_revision': 1,
        }).status_code == 409
        assert client.delete(path, params={**params, 'expected_revision': 1}).status_code == 409
        assert client.patch(path, params={'workspace_id': foreign}, json={
            'content': 'foreign must not win', 'expected_revision': 2,
        }).status_code == 404
        assert client.delete(path, params={'workspace_id': foreign, 'expected_revision': 2}).status_code == 404
        for invalid in [True, 0, '2', 2.0]:
            assert client.patch(path, params=params, json={
                'content': 'invalid version', 'expected_revision': invalid,
            }).status_code == 422
        stored = client.get('/api/memories', params=params).json()
        assert stored[0]['content'] == 'first editor committed'
        assert len(client.get(path + '/history').json()) == 1
        assert client.delete(path, params={**params, 'expected_revision': 2}).status_code == 200
        assert client.get('/api/memories', params=params).json() == []


def test_legacy_editor_remains_compatible_and_still_advances_revision(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        workspace = client.get('/api/workspaces').json()[0]['id']
        memory = client.post('/api/memories', json={'workspace_id': workspace, 'content': 'legacy'}).json()
        changed = client.patch('/api/memories/' + memory['id'], json={'content': 'legacy edit'})
        assert changed.status_code == 200 and changed.json()['revision'] == 2
        assert client.patch('/api/memories/' + memory['id'], json={'expected_revision': 2}).status_code == 422
