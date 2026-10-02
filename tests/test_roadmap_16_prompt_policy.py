from my_ai import registries


def test_prompt_and_policy_registries_are_versioned():
    captured = []
    monkey = lambda *args, **kwargs: captured.append((args, kwargs)) or {}
    original = registries.put_record
    registries.put_record = monkey
    try:
        registries.publish_prompt("prompt", "text", version="4")
        registries.publish_policy("policy", {"allow": False}, version="5")
    finally:
        registries.put_record = original
    assert captured[0][0][2]["version"] == "4"
    assert captured[1][0][2]["version"] == "5"


def test_prompt_history_and_rollback(monkeypatch):
    import my_ai.registries as registries
    current={"name":"demo","payload":{"text":"old","version":"1","task":"default","metadata":{}},"version":1}
    history=[]
    def fake_get(namespace,name): return current if namespace=="prompts.registry" and name=="demo" else None
    def fake_put(namespace,name,payload,**kwargs):
        if namespace=="prompts.registry.history":
            history.append({"name":name,"payload":payload,"version":1})
            return history[-1]
        current["payload"]=payload; current["version"]+=1; return current
    monkeypatch.setattr(registries,"get_record",fake_get)
    monkeypatch.setattr(registries,"put_record",fake_put)
    monkeypatch.setattr(registries,"list_records",lambda namespace: history if namespace=="prompts.registry.history" else [])
    registries.publish_prompt("demo","new",version="2")
    assert history
    restored=registries.rollback_prompt("demo",1)
    assert restored["payload"]["text"]=="old"
