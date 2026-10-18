"""Independent geometry and persisted API contract checks, no browser dependency."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from services.api.office_layout import (blueprints, validate_items, room_furniture, save_furniture,
    create_office_layout_router, seed_for_room, slot_for_room, custom_furniture)
from services.api.store import Store


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path)
    for identifier in ('coding', 'research'):
        result.put('workspace', dict(id=identifier, name=identifier, root_path=str(tmp_path / identifier)))
    yield result
    result.db.close()


def item(x, y, kind='plant_tall', identifier='plant'):
    return dict(id=identifier, kind=kind, x=x, y=y)


def available(blueprint, footprints, kind='plant_tall'):
    for y in range(2, 11):
        for x in range(1, 15):
            try:
                validate_items([item(x,y,kind)], blueprint, footprints)
                yield item(x,y,kind)
            except HTTPException:
                pass


def test_all_sixteen_pinned_rooms_allow_actual_native_furniture():
    data = blueprints()
    assert len(data['rooms']) == 16
    for key, blueprint in data['rooms'].items():
        assert validate_items([], blueprint, data['footprints']) == []
        for kind in ('plant_tall','bookshelf','floor_lamp'):
            positions = list(available(blueprint, data['footprints'], kind))
            assert len(positions) >= 2, (key, kind)
            assert validate_items([positions[0]], blueprint, data['footprints']) == [positions[0]]


def test_save_move_delete_persists_and_preserves_workspace_resource(store):
    data=blueprints(); b=data['rooms'][f'{seed_for_room("coding")}:0']
    choices=list(available(b,data['footprints']))
    assert room_furniture(store,'coding')['version']==0
    saved=save_furniture(store,'coding',dict(items=[choices[0]],expected_version=0))
    assert saved['version']==1
    moved=save_furniture(store,'coding',dict(items=[choices[1]],expected_version=1))
    assert moved['items']==[choices[1]]
    assert custom_furniture(store,'research')==[]
    reopened=Store(store.root)
    assert custom_furniture(reopened,'coding')==[choices[1]]
    reopened.db.close()
    assert store.get('workspace','coding')['name']=='coding'
    assert save_furniture(store,'coding',dict(items=[],expected_version=2))['items']==[]
    assert store.events('coding')[-1]['event_type']=='office.furniture.updated'


@pytest.mark.parametrize('items',[
    [item(-1,3)],[item(14,3,'bookshelf')],[item(2,1)],[item(2,11)],
    [item(2.5,3)],[item(True,3)],[item(2,3,'shell')],
    [dict(item(2,3),width=0)],[dict(item(2,3),variant='script')],
    [dict(item(2,3,'bookshelf'),variant='palm')],
    [item(2,3,identifier='../escape')], [item(2,3,kind=[])], [item(2,3,kind={})],
    [item(2,3),item(3,3)], # same id
])
def test_invalid_fields_coordinates_kinds_and_client_geometry_rejected(items):
    data=blueprints()
    with pytest.raises(HTTPException) as error:
        validate_items(items,data['rooms']['1:0'],data['footprints'])
    assert error.value.status_code==422


def test_base_overlap_custom_overlap_and_door_protected():
    data=blueprints(); b=data['rooms']['1:0']; footprints=data['footprints']
    baseline=json.loads(open('packages/office-layout/blueprints.json').read())['rooms'][0]
    furniture=baseline['furniture'][0]
    with pytest.raises(HTTPException,match='overlaps'):
        validate_items([item(furniture['x'],furniture['y'])],b,footprints)
    choice=next(available(b,footprints))
    with pytest.raises(HTTPException,match='overlaps'):
        validate_items([choice,dict(choice,id='other')],b,footprints)
    # Interior door cell (north room uses y11 threshold and is outside editable bounds).
    for x,y in b['doors']:
        with pytest.raises(HTTPException): validate_items([item(x,y)],b,footprints)


def test_blocking_a_corridor_rejected_even_without_direct_overlap():
    # A narrow aisle has one unoccupied choke point; endpoints stay untouched.
    b=dict(width=7,height=7,occupied=[(x,y) for x in range(7) for y in range(7) if x!=3],
           blocked=[(x,y) for x in range(7) for y in range(7) if x!=3],doors=[(3,6)],approaches=[(3,2)])
    with pytest.raises(HTTPException,match='disconnects'):
        validate_items([item(3,4)],b,blueprints()['footprints'])


def test_unknown_workspace_seed_tamper_stale_version_and_optimistic_lock(store):
    with pytest.raises(HTTPException) as error: room_furniture(store,'missing')
    assert error.value.status_code==404
    with pytest.raises(HTTPException) as error: save_furniture(store,'coding',dict(items=[],expected_version=0,seed=1))
    assert error.value.status_code==422
    def save():
        try: return save_furniture(store,'coding',dict(items=[],expected_version=0))['version']
        except HTTPException as e: return e.status_code
    with ThreadPoolExecutor(2) as executor:
        assert sorted(executor.map(lambda _:save(),range(2)))==[1,409]
    assert slot_for_room(store,'coding')==0 and slot_for_room(store,'research')==1


def test_http_contract_reads_and_writes_only_validated_fields(store):
    app=FastAPI();app.state.store=store;app.include_router(create_office_layout_router(app))
    with TestClient(app) as client:
        response=client.get('/api/office/rooms/coding/furniture')
        assert response.status_code==200
        assert response.json()==dict(items=[],version=0,seed=seed_for_room('coding'))
        assert client.put('/api/office/rooms/coding/furniture',json=dict(items=[],expected_version=0)).json()['version']==1
        assert client.put('/api/office/rooms/coding/furniture',json=dict(items=[],expected_version=0)).status_code==409
        assert client.put('/api/office/rooms/coding/furniture',json=dict(items=[],expected_version=1,footprints={})).status_code==422
        assert client.get('/api/office/rooms/missing/furniture').status_code==404


def test_layout_storage_never_overwrites_a_different_resource_kind(store):
    original = dict(id='office-furniture:coding', name='Existing user resource')
    store.put('skill', original)
    with pytest.raises(HTTPException) as error:
        save_furniture(store, 'coding', dict(items=[], expected_version=0))
    assert error.value.status_code == 409
    assert store.get('skill', original['id']) == original
    assert store.events('coding') == []
