from my_ai.agent import Agent


def test_retrieval_citations_are_mandatory_and_local_provenance_is_addressable():
    knowledge = [
        {
            "id": 12,
            "title": "Local fact",
            "provenance": {
                "citation_id": "K12",
                "source_url": "local://knowledge/12",
                "title": "Local fact",
            },
            "confidence": None,
            "confidence_calibrated": False,
        }
    ]
    citations = Agent._required_citations(knowledge)
    assert "[K12]" in citations
    assert "local://knowledge/12" in citations
    assert "confidence: uncalibrated" in citations
