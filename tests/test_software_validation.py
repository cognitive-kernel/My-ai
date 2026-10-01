from pathlib import Path

from my_ai.software_validation import validate_generated_project, validate_plan


def test_plan_requires_artifact_and_acceptance_criteria():
    validate_plan({
        "goal": "build app",
        "artifact_type": "web application",
        "language": "Python",
        "framework": "FastAPI",
        "requirements": ["API"],
        "architecture": ["backend"],
        "phases": ["implement"],
        "acceptance_criteria": ["GET /health returns 200"],
        "research_queries": ["FastAPI official docs"],
        "validation": ["pytest"],
        "constraints": [],
        "ambiguities": [],
    })


def test_mql4_indicator_rejects_mql5_and_trade_api(tmp_path: Path):
    source = tmp_path / "NewsIndicator.mq4"
    source.write_text(
        '#include <Trade\\Trade.mqh>\n'
        'void OnCalculate() { OrderSend(Symbol(), OP_BUY, 0.1, Ask, 3, 0, 0); }\n',
        encoding="utf-8",
    )
    defects = validate_generated_project(tmp_path, {"artifact_type": "custom indicator"}, "MQL4")
    assert any("MQL5-only" in defect for defect in defects)
    assert any("OrderSend" in defect for defect in defects)


def test_mql4_valid_indicator_is_not_rejected_for_normal_indicator_code(tmp_path: Path):
    (tmp_path / "NewsIndicator.mq4").write_text(
        "#property indicator_chart_window\n"
        "int OnInit(){ return(INIT_SUCCEEDED); }\n"
        "int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tick_volume[],const long &volume[],const int &spread[]){ return rates_total; }\n",
        encoding="utf-8",
    )
    defects = validate_generated_project(tmp_path, {"artifact_type": "custom indicator"}, "MQL4")
    assert defects == []


def test_unconditional_trade_placeholder_is_rejected(tmp_path: Path):
    (tmp_path / "x.mq4").write_text("bool ConditionToTrade(){ return true; }", encoding="utf-8")
    defects = validate_generated_project(tmp_path, {"artifact_type": "expert advisor"}, "MQL4")
    assert any("placeholder" in defect.lower() for defect in defects)
