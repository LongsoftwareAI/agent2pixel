"""Local source ingestion. Source data cannot change agent permissions."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from services.worker.data_tools import create_source, fetch_web


class SourceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workspace_id: str
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=1024 * 1024)
    media_type: str


class WebSourceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workspace_id: str
    url: str = Field(min_length=1, max_length=2048)


def create_data_router(app):
    router = APIRouter()

    def workspace(id):
        if not app.state.store.get('workspace', id):
            raise HTTPException(404, 'Workspace not found')

    @router.get('/api/sources')
    def list_sources(workspace_id: str):
        workspace(workspace_id)
        return [{k: v for k, v in source.items() if k != 'content'} for source in app.state.store.list('source', workspace_id)]

    @router.post('/api/sources')
    def ingest(body: SourceInput):
        workspace(body.workspace_id)
        try:
            return create_source(app.state.store, **body.model_dump())
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.post('/api/sources/web')
    def ingest_web(body: WebSourceInput):
        workspace(body.workspace_id)
        try:
            result = fetch_web(body.url)
            return create_source(app.state.store, body.workspace_id, result['url'], result['content'], result['media_type'], result['url'], result['retrieved_at'])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.get('/api/sources/{id}')
    def read_source(id: str, workspace_id: str):
        workspace(workspace_id)
        source = app.state.store.get('source', id)
        if not source or source['workspace_id'] != workspace_id:
            raise HTTPException(404, 'Source not found in workspace')
        return source

    return router
