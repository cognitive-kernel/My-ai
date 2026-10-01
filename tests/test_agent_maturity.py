from pathlib import Path

from my_ai.agent_maturity import (
    CircuitBreaker, create_task, create_task_workspace, memory_lifecycle,
    task_trace, task_transaction, transition_task, verify_critique_repair_verify,
)

def test_task_state_machine_rejects_invalid_transition():
    task = create_task('build a test artifact')
    transition_task(task['id'], 'understood')
    try:
        transition_task(task['id'], 'completed')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid transition must fail closed')

def test_task_trace_records_state_transitions():
    task = create_task('trace me')
    transition_task(task['id'], 'understood', 'understanding')
    transition_task(task['id'], 'planned', 'planning')
    events = task_trace(task['id'])
    assert [x['state'] for x in events][-3:] == ['received', 'understood', 'planned']

def test_verify_critique_repair_verify_runs_independent_repair():
    state = {'ok': False, 'repairs': 0}
    def validate(): return state['ok']
    def critique(validation): return 'missing acceptance criterion'
    def repair(defect, validation):
        assert defect == 'missing acceptance criterion'
        state['repairs'] += 1
        state['ok'] = True
        return {'action': 'add acceptance criterion'}
    result = verify_critique_repair_verify(validate, critique, repair, max_iterations=3)
    assert result.status == 'passed'
    assert result.iterations == 1
    assert state['repairs'] == 1

def test_task_workspace_isolated_and_transaction_rolls_back():
    task = create_task('transaction')
    root = create_task_workspace(task['id'], 'transaction-test')
    target = Path(root) / 'artifact.txt'
    with task_transaction(task['id']) as tx:
        tx.stage_write('artifact.txt', 'temporary')
    assert not target.exists()
    with task_transaction(task['id']) as tx:
        tx.stage_write('artifact.txt', 'committed')
        tx.commit()
    assert target.read_text(encoding='utf-8') == 'committed'

def test_memory_lifecycle_and_circuit_breaker():
    from my_ai.db import execute
    knowledge_id = execute(
        'INSERT INTO knowledge(topic,title,content,category) VALUES(?,?,?,?)',
        ('maturity', 'lifecycle', 'value', 'project_facts'),
    )
    assert memory_lifecycle(knowledge_id, 'validated')['status'] == 'validated'
    breaker = CircuitBreaker(threshold=2, reset_seconds=60)
    assert breaker.allow()
    breaker.failure()
    breaker.failure()
    assert breaker.allow() is False
    assert breaker.status()['open'] is True
