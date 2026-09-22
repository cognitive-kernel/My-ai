from my_ai.config import settings
from my_ai.llm import OllamaClient


def test_ollama_task_routing():
    assert OllamaClient("coding").model == settings.coding_model
    assert OllamaClient("patch").model == settings.coding_model
    assert OllamaClient("routing").model == settings.routing_model
    assert OllamaClient("classify").model == settings.routing_model
    assert OllamaClient("general").model == settings.ollama_model
