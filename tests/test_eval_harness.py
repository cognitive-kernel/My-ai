from my_ai.eval_harness import EvalCase, reciprocal_rank, run_retrieval_eval

def test_reciprocal_rank_is_deterministic():
    assert reciprocal_rank([{"topic":"other"},{"topic":"Python"}], ("Python",)) == 0.5
    assert reciprocal_rank([], ("Python",)) == 0.0

def test_eval_harness_reports_baseline():
    cases = [EvalCase("python", ("Python",))]
    result = run_retrieval_eval(lambda q, limit: [{"topic":"Python","title":"lists"}], cases)
    assert result["mrr"] == 1.0
    assert result["baseline_cases"] == 1
    assert result["cases"][0]["passed"] is True
