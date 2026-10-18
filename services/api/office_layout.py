"""Authoritative additive Habblaud furniture layout, validated against pinned blueprints.

Base room furniture and seats are immutable. Client supplies positions, never geometry.
"""
import hashlib
import json
import re
from collections import deque
from pathlib import Path
from fastapi import APIRouter, HTTPException
from services.api.store import synchronized

BLUEPRINT_PATH = Path(__file__).resolve().parents[2] / 'packages/office-layout/blueprints.json'
KINDS = {'plant_tall', 'bookshelf', 'floor_lamp'}


def seed_for_room(workspace_id):
    return int.from_bytes(hashlib.sha256(str(workspace_id).encode()).digest()[:4], 'big') % 8 + 1


def slot_for_room(store, workspace_id):
    return next(i % 2 for i, w in enumerate(store.list('workspace')) if w['id'] == workspace_id)


def blueprints():
    data = json.loads(BLUEPRINT_PATH.read_text())
    result = dict(rooms={}, footprints={})
    for kind, value in data['footprints'].items():
        result['footprints'][kind] = dict(width=value['footprint']['w'], height=value['footprint']['h'], blocks=value['blocks'], variants=value.get('variants', []))
    for room in data['rooms']:
        occupied = set()
        for item in room['furniture']:
            occupied |= cells(item['x'], item['y'], item['w'], item['h'])
        blocked = {(x, y) for y, row in enumerate(room['grid']) for x, value in enumerate(row) if value == 0}
        occupied |= blocked
        door = room['door']
        doors = cells(door['x'], door['y'], door['w'], door['h'])
        # Preserve all native spots that are accessible in the pinned original layout.
        approaches = [(spot['x'], spot['y']) for spot in room['spots'] if any(reachable(d, (spot['x'], spot['y']), blocked, room['width'], room['height']) for d in doors)]
        result['rooms'][str(room['seed']) + ':' + str(room['slot'])] = dict(width=room['width'], height=room['height'], occupied=list(occupied), blocked=list(blocked), doors=list(doors), approaches=approaches,
            spots=[(spot['x'], spot['y']) for spot in room['spots']])
    return result


def room_furniture(store, workspace_id):
    if not store.get('workspace', workspace_id):
        raise HTTPException(404, 'Workspace not found')
    record = store.get('office_furniture', 'office-furniture:' + workspace_id)
    return dict(items=record['items'] if record else [], version=record['version'] if record else 0,
                seed=seed_for_room(workspace_id))


def custom_furniture(store, workspace_id):
    return room_furniture(store, workspace_id)['items']


def cells(x, y, width, height):
    return {(col, row) for col in range(x, x + width) for row in range(y, y + height)}


def reachable(start, target, blocked, width, height):
    if start in blocked or target in blocked:
        return False
    pending = deque([start]); seen = {start}
    while pending:
        point = pending.popleft()
        if point == target:
            return True
        for step in ((point[0]-1, point[1]), (point[0]+1, point[1]), (point[0], point[1]-1), (point[0], point[1]+1)):
            if 0 <= step[0] < width and 0 <= step[1] < height and step not in blocked and step not in seen:
                seen.add(step); pending.append(step)
    return False


def validate_items(items, blueprint, footprints):
    if not isinstance(items, list) or len(items) > 24:
        raise HTTPException(422, 'Furniture requires a list of at most 24 items')
    width, height = blueprint['width'], blueprint['height']
    occupied = {tuple(p) for p in blueprint['occupied']}
    blocked = {tuple(p) for p in blueprint['blocked']}
    protected = {tuple(p) for p in blueprint['doors']} | {tuple(p) for p in blueprint.get('spots', blueprint['approaches'])}
    seen = set(); result = []
    for item in items:
        if not isinstance(item, dict) or set(item) - {'id', 'kind', 'x', 'y', 'variant'}:
            raise HTTPException(422, 'Unknown furniture fields; geometry is server-owned')
        identifier = item.get('id'); kind = item.get('kind')
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', identifier) or identifier in seen:
            raise HTTPException(422, 'Furniture IDs must be unique visible identifiers')
        if not isinstance(kind, str) or kind not in KINDS:
            raise HTTPException(422, 'Unknown or non-editable furniture kind')
        x, y = item.get('x'), item.get('y')
        if type(x) is not int or type(y) is not int:
            raise HTTPException(422, 'Furniture coordinates must be integers')
        variant = item.get('variant')
        if variant is not None and (not isinstance(variant, str) or variant not in footprints[kind]['variants']):
            raise HTTPException(422, 'Invalid furniture variant for kind')
        geometry = footprints[kind]; footprint = cells(x, y, geometry['width'], geometry['height'])
        if x < 1 or y < 2 or x + geometry['width'] > width - 1 or y + geometry['height'] > height - 1:
            raise HTTPException(422, 'Furniture outside room bounds')
        if footprint & protected:
            raise HTTPException(422, 'Furniture blocks a door or workstation approach')
        if footprint & occupied:
            raise HTTPException(422, 'Furniture overlaps base furniture, wall, or another item')
        occupied |= footprint
        if geometry['blocks']:
            blocked |= footprint
        seen.add(identifier); normalized = dict(id=identifier, kind=kind, x=x, y=y)
        if variant is not None:
            normalized['variant'] = variant
        result.append(normalized)
    doors = [tuple(p) for p in blueprint['doors']]
    for approach in map(tuple, blueprint['approaches']):
        if not any(reachable(door, approach, blocked, width, height) for door in doors):
            raise HTTPException(422, 'Furniture disconnects a workstation from room entrance')
    for door in doors:
        if not all(reachable(door, other, blocked, width, height) for other in doors):
            raise HTTPException(422, 'Furniture disconnects room entrances')
    return result


@synchronized
def save_furniture(store, workspace_id, body):
    current = room_furniture(store, workspace_id)
    if not isinstance(body, dict) or set(body) != {'items', 'expected_version'}:
        raise HTTPException(422, 'Expected items and expected_version only; room seed is immutable')
    if type(body['expected_version']) is not int or body['expected_version'] != current['version']:
        raise HTTPException(409, 'Furniture version conflict; reload before saving')
    data = blueprints()
    blueprint = data['rooms'][str(current['seed']) + ':' + str(slot_for_room(store, workspace_id))]
    items = validate_items(body['items'], blueprint, data['footprints'])
    record = dict(id='office-furniture:' + workspace_id, workspace_id=workspace_id, items=items, version=current['version'] + 1)
    # Store IDs are globally unique across kinds. Never convert an existing user
    # resource into layout state through Store.put's upsert behavior.
    existing = store.db.execute('SELECT kind FROM resources WHERE id=?', (record['id'],)).fetchone()
    if existing and existing[0] != 'office_furniture':
        raise HTTPException(409, 'Furniture storage ID conflicts with an existing resource')
    store.put('office_furniture', record)
    store.event(workspace_id, 'office.furniture.updated', {'version': record['version'], 'item_count': len(items)})
    return dict(items=items, version=record['version'], seed=current['seed'])


def create_office_layout_router(app):
    router = APIRouter()
    @router.get('/api/office/rooms/{workspace_id}/furniture')
    def get_furniture(workspace_id: str):
        return room_furniture(app.state.store, workspace_id)
    @router.put('/api/office/rooms/{workspace_id}/furniture')
    def put_furniture(workspace_id: str, body: dict):
        return save_furniture(app.state.store, workspace_id, body)
    return router
