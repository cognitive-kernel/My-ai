from my_ai.config import settings
from my_ai.llm import OllamaClient


def test_ollama_task_routing(monkeypatch):
    monkeypatch.setattr(settings, "coding_model", "coding-test")
    monkeypatch.setattr(settings, "routing_model", "routing-test")
    monkeypatch.setattr(settings, "fallback_model", "fallback-test")
    assert OllamaClient("coding").model == "coding-test"
    assert OllamaClient("patch").model == "coding-test"
    assert OllamaClient("routing").model == "routing-test"
    assert OllamaClient("classify").model == "routing-test"
    assert OllamaClient("general").model == settings.ollama_model
