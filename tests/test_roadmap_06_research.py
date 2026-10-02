from my_ai.advanced_agent import ResearchPipeline


def test_research_pipeline_deduplicates_sources_and_preserves_provenance():
    pipeline = ResearchPipeline(
        search=lambda question, limit: ["https://example.com/a", "https://example.com/a"],
        fetch=lambda url: {"url": url, "title": "A", "claim": "fact"},
        verifier=lambda record: True,
    )
    result = pipeline.run("q", manual_sources=["https://example.com/a"])
    assert result["sources"] == ["https://example.com/a"]
    assert result["provenance"][0]["url"] == "https://example.com/a"


def test_research_pipeline_applies_domain_allowlist_and_verification():
    pipeline = ResearchPipeline(
        search=lambda question, limit: ["https://allowed.example/a", "https://blocked.example/a"],
        fetch=lambda url: {"url": url, "title": url, "content": "x"},
        verifier=lambda record: record["url"].startswith("https://allowed.example"),
    )
    result = pipeline.run("q", allowed_domains=["allowed.example"])
    assert result["sources"] == ["https://allowed.example/a"]
