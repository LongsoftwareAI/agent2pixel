"""Task-specific acceptance checks; a valid HTTP response alone is never sufficient."""
import json
from decimal import Decimal, InvalidOperation


def parse_object(text):
    if not isinstance(text, str) or len(text) > 20000:
        raise ValueError('Output must be bounded JSON text')
    text = text.strip()
    if text.startswith('```json\n') and text.endswith('\n```'):
        text = text[8:-4]
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError('Output must be a JSON object')
    return value


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a numeric fact')
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Invalid numeric fact') from None
    if not parsed.is_finite():
        raise ValueError('Numeric fact must be finite')
    return parsed


def validate(kind, text, source_id):
    value = parse_object(text)
    if value.get('source_id') != source_id:
        raise ValueError('Source citation does not match supplied source')
    if kind == 'csv':
        if set(value) != {'source_id', 'total', 'groups', 'rows'}:
            raise ValueError('CSV report schema mismatch')
        if number(value['total']) != Decimal('2.00') or type(value['rows']) is not int or value['rows'] != 3:
            raise ValueError('CSV total or row count contradicts actual tool facts')
        groups = value['groups']
        if not isinstance(groups, dict) or set(groups) != {'A', 'B'}:
            raise ValueError('CSV group schema mismatch')
        if number(groups['A']) != Decimal('.30') or number(groups['B']) != Decimal('1.70'):
            raise ValueError('CSV groups contradict actual Decimal calculations')
    elif kind == 'research':
        if set(value) != {'source_id', 'tickets', 'reviewer_capacity'} or type(value['tickets']) is not int or value['tickets'] != 12:
            raise ValueError('Research facts contradict supplied source')
        if value['reviewer_capacity'] != 'NOT_PROVIDED':
            raise ValueError('Research invented unknown reviewer capacity')
    elif kind == 'content':
        if set(value) != {'source_id', 'headline', 'seats', 'warranty'}:
            raise ValueError('Content schema mismatch')
        if type(value['seats']) is not int or value['seats'] != 12 or value['warranty'] != 'NOT_PROVIDED':
            raise ValueError('Content invented or changed supplied offer facts')
        if value['headline'] != 'A team workshop':
            raise ValueError('Content headline length constraint failed')
    else:
        raise ValueError('Unknown semantic test kind')
    return value
