from my_ai.eval_harness import BASELINE_CASES, EvalCase, reciprocal_rank, run_retrieval_eval

def test_reciprocal_rank_is_deterministic():
    assert reciprocal_rank([{"topic":"other"},{"topic":"Python"}], ("Python",)) == 0.5
    assert reciprocal_rank([], ("Python",)) == 0.0

def test_eval_harness_reports_baseline():
    cases = [EvalCase("python", ("Python",))]
    result = run_retrieval_eval(lambda q, limit: [{"topic":"Python","title":"lists"}], cases)
    assert result["mrr"] == 1.0
    assert result["baseline_cases"] == 1
    assert result["cases"][0]["passed"] is True


def test_baseline_contains_persian_cases_and_reports_languages():
    result = run_retrieval_eval(lambda q, limit: [{"topic": "Python"}], BASELINE_CASES)
    assert result["baseline_cases"] == len(BASELINE_CASES)
    assert "fa" in result["languages"]
    assert "en" in result["languages"]
    assert "pass_rate" in result


def test_persian_response_baseline_is_deterministic():
    from my_ai.eval_harness import PERSIAN_RESPONSE_BASELINE, run_response_eval
    result = run_response_eval(
        lambda prompt: "پاسخ کامل درباره " + prompt + " شامل تست و مثال است.",
        PERSIAN_RESPONSE_BASELINE,
    )
    assert result["case_count"] == len(PERSIAN_RESPONSE_BASELINE)
    assert result["baseline_met"] is True


def test_persian_response_quality_rejects_unknown_marker():
    from my_ai.eval_harness import ResponseEvalCase, score_response
    result = score_response(
        "__MYAI_UNKNOWN__",
        ResponseEvalCase("سؤال", ("پایتون",), "fa"),
    )
    assert result["passed"] is False
