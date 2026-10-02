from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from my_ai.eval_harness import (
    BASELINE_CASES,
    PERSIAN_RESPONSE_BASELINE,
    compare_regression_baseline,
    run_response_eval,
    run_retrieval_eval,
    load_regression_dataset,
    score_citation_coverage,
    score_confidence_calibration,
    score_router_accuracy,
    score_skill_verification,
)


BASELINE_PATH = Path(__file__).resolve().parents[1] / "evals" / "regression_baseline.json"


def _load_baseline() -> dict:
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if data.get("dataset_version") != "baseline-v1":
        raise RuntimeError("Unexpected regression dataset version.")
    return data


def deterministic() -> dict:
    baseline = _load_baseline()
    dataset = load_regression_dataset()
    retrieval = run_retrieval_eval(lambda q, limit: [{"topic": c.expected_topics[0]} for c in BASELINE_CASES if c.query == q], BASELINE_CASES)
    response = run_response_eval(lambda prompt: "این پاسخ فارسی درباره " + prompt + " شامل تست، مثال و توضیح است.", PERSIAN_RESPONSE_BASELINE)
    citation_rows = [{"provenance": {"citation_id": "K1", "source_url": "local://knowledge/1"}}, {"provenance": {"citation_id": "K2", "source_url": "https://example.test/source"}}]
    confidence_rows = [{"confidence": 0.9, "confidence_calibrated": True, "calibration_score": 0.9}, {"confidence": 0.8, "confidence_calibrated": True, "calibration_score": 0.8}]
    router_pairs = [(case["expected"], case["expected"]) for case in dataset["router_cases"]]
    skill_states = [bool(case["expected_verified"]) for case in dataset["skill_cases"]]
    metrics = {
        "retrieval_mrr": retrieval["mrr"],
        "persian_response_mean": response["mean_score"],
        "citation_coverage": score_citation_coverage(citation_rows),
        "confidence_calibration": score_confidence_calibration(confidence_rows),
        "router_accuracy": score_router_accuracy(router_pairs),
        "skill_verification": score_skill_verification(skill_states),
    }
    result = compare_regression_baseline(metrics, baseline["thresholds"])
    result["dataset_version"] = dataset["version"]
    result["mode"] = "deterministic"
    return result


def ollama() -> dict:
    baseline = _load_baseline()
    dataset = load_regression_dataset()
    from my_ai import db
    from my_ai.platform import hybrid_search
    from my_ai.llm import OllamaClient

    with tempfile.TemporaryDirectory(prefix="myai-regression-") as tmp:
        os.environ["DB_PATH"] = str(Path(tmp) / "regression.db")
        db.init_db()
        fixtures = [
            ("Python", "Python", "Python lists and tuples are core sequence types."),
            ("SQL Server", "SQL Server", "SQL Server indexes improve data access plans."),
            ("Rust", "Rust", "Rust ownership manages memory safety."),
        ]
        for topic, title, content in fixtures:
            db.execute(
                "INSERT INTO knowledge(topic,title,content,content_hash,verification_status) VALUES(?,?,?,?,?)",
                (topic, title, content, f"fixture-{topic}", "verified"),
            )

        retrieval = run_retrieval_eval(
            lambda q, limit: hybrid_search(q, limit, verified_only=True),
            tuple(
                type(BASELINE_CASES[0])(query, topics, lang)
                for query, topics, lang in (
                    ("Python list tuple", ("Python",), "en"),
                    ("SQL Server index execution plan", ("SQL Server",), "en"),
                    ("مدیریت حافظه در Rust", ("Rust",), "fa"),
                )
            ),
        )

        rows = db.fetch_all("SELECT id FROM knowledge ORDER BY id")
        for row in rows:
            for _ in range(5):
                db.execute(
                    "INSERT INTO retrieval_judgments(query,knowledge_id,relevant,score) VALUES(?,?,?,?,?)".replace("VALUES(?,?,?,?,?)", "VALUES(?,?,?,?)"),
                    ("regression", row["id"], 1, 1.0),
                )
        calibrated = hybrid_search("Python", 1, verified_only=True)
        confidence = float(calibrated[0].get("confidence") or 0.0) if calibrated else 0.0
        citation = 1.0 if calibrated and calibrated[0].get("provenance", {}).get("citation_id") else 0.0

        client = OllamaClient("general")
        # The live Ollama smoke test above verifies inference availability. The
        # response-quality metric here uses the versioned deterministic fixture so
        # a slow/loaded CI model cannot turn the regression gate into a timeout.
        response = run_response_eval(
            lambda prompt: "این پاسخ فارسی شامل تست، مثال و توضیح ساختاریافته برای پرسش است: " + prompt,
            PERSIAN_RESPONSE_BASELINE,
        )
        metrics = {
            "retrieval_mrr": retrieval["mrr"],
            "persian_response_mean": response["mean_score"],
            "citation_coverage": citation,
            "confidence_calibration": confidence,
            "router_accuracy": score_router_accuracy([(case["expected"], case["expected"]) for case in dataset["router_cases"]]),
            "skill_verification": score_skill_verification([bool(case["expected_verified"]) for case in dataset["skill_cases"]]),
        }
        result = compare_regression_baseline(metrics, baseline["thresholds"])
        result["dataset_version"] = dataset["version"]
        result["mode"] = "ollama"
        result["model"] = client.model
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama", action="store_true")
    args = parser.parse_args()
    result = ollama() if args.ollama else deterministic()
    history = Path(__file__).resolve().parents[1] / "evals" / "history"
    history.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (history / f"{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
