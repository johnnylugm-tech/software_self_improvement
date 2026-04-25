import pytest
from scripts import report_gen, verify, crg_analysis
import json

def test_report_gen_recommendation():
    # 模擬成果報告：只有 Low issues 時應回傳 pass
    report = {"summary": {"open_total": 5, "open_critical": 0, "open_high": 0, "open_medium": 0}, "accepted_risks": []}
    assert report_gen.determine_recommendation(report, []) == "pass"
    
    # 模擬包含 Medium issue 時應回傳 partial
    report_partial = {"summary": {"open_total": 1, "open_critical": 0, "open_high": 0, "open_medium": 1}}
    assert report_gen.determine_recommendation(report_partial, []) == "partial"

def test_verify_diff_logic():
    # 模擬 git diff --stat 輸出
    diff_stat = "scripts/verify.py | 12 +++\n README.md | 5 -"
    assert verify.count_diff_lines(diff_stat) == 17

def test_crg_metrics_computation():
    # 測試指標計算邏輯
    recon = {
        "communities": [{"cohesion": 0.8}],
        "flows": [{"node_count": 5}],
        "risk_score": 0.2
    }
    metrics = crg_analysis.compute_metrics(recon)
    assert "community_cohesion" in metrics
    assert metrics["risk_score"] == 0.2
