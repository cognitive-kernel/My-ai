from my_ai.advanced_agent import ResearchPipeline


def test_research_results_carry_provenance_before_use():
    pipeline = ResearchPipeline(
        search=lambda q, limit: ["https://docs.example/item"],
        fetch=lambda url: {"title": "Official", "content": "safe evidence"},
        verifier=lambda item: True,
    )
    result = pipeline.run("topic")
    assert result["evidence"][0]["url"] == "https://docs.example/item"
    assert result["provenance"][0]["title"] == "Official"
