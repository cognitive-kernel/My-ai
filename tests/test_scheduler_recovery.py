from my_ai.scheduler import StudyScheduler

def test_supervisor_restarts_missing_worker(monkeypatch):
    scheduler=StudyScheduler(interval_seconds=1)
    started=[]
    scheduler.start=lambda language, session_id=None: started.append((language,session_id))
    monkeypatch.setattr("my_ai.scheduler.fetch_all", lambda sql, params=(): [{"language":"Python","session_id":7,"status":"retrying"}])
    scheduler._supervisor_loop.__wrapped__ if hasattr(scheduler._supervisor_loop, "__wrapped__") else None
    scheduler._supervisor_stop.set()
    scheduler._supervisor_stop.clear()
    original=scheduler._supervisor_stop.is_set
    calls=[False,True]
    scheduler._supervisor_stop.is_set=lambda: calls.pop(0)
    scheduler._supervisor_stop.wait=lambda _: None
    scheduler._workers={}
    scheduler._supervisor_loop()
    assert started==[("Python",7)]
    scheduler._supervisor_stop.is_set=original
