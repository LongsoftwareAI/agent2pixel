import json
import pytest
from tests.phase6.live.semantics import validate


def report(kind):
    base = {'source_id': 'synthetic-source'}
    return {**base, **{
        'csv': {'total':'2.00','groups':{'A':'0.30','B':'1.70'},'rows':3},
        'research': {'tickets':12,'reviewer_capacity':'NOT_PROVIDED'},
        'content': {'headline':'A team workshop','seats':12,'warranty':'NOT_PROVIDED'},
    }[kind]}


@pytest.mark.parametrize('kind', ['csv','research','content'])
def test_accepts_exact_source_grounded_bounded_task_output(kind):
    assert validate(kind, json.dumps(report(kind)), 'synthetic-source') == report(kind)


@pytest.mark.parametrize('change', [
    {'total':'2.01'}, {'total':'NaN'}, {'total':True}, {'rows':True}, {'rows':4},
    {'groups':{'A':'0.3','B':'1.71'}}, {'groups':{'A':'.3','B':'1.7','C':'0'}},
    {'source_id':'foreign'}, {'invented_field':'not permitted'},
])
def test_rejects_incorrect_csv_facts_or_schema(change):
    with pytest.raises((ValueError, TypeError)):
        validate('csv', json.dumps({**report('csv'), **change}), 'synthetic-source')


@pytest.mark.parametrize('kind,change', [
    ('research', {'tickets':13}), ('research', {'reviewer_capacity':8}),
    ('content', {'warranty':'lifetime'}), ('content', {'seats':13}),
    ('content', {'headline':'x'*81}),
    ('content', {'headline':'Lifetime warranty and 90% discount tomorrow'}),
])
def test_rejects_fluent_but_invented_or_out_of_scope_company_output(kind, change):
    with pytest.raises(ValueError):
        validate(kind, json.dumps({**report(kind), **change}), 'synthetic-source')


def test_rejects_nonjson_extra_text_and_foreign_source():
    for text in ['success', '[]', json.dumps(report('csv'))+' commentary']:
        with pytest.raises(ValueError):
            validate('csv', text, 'synthetic-source')
    with pytest.raises(ValueError):
        validate('research', json.dumps(report('research')), 'foreign-source')
