import pytest
from scripts import verify, score
import json
from pathlib import Path

def test_verify_self_consistency():
    # 案例 1: 正常 (小幅度跳變)
    dim_res = {"score": 10, "llm_score": 10, "tool_score": 10}
    res = verify.self_consistency_gate(dim_res, "linting", 5, 10)
    assert res["flagged"] is False
    
    # 案例 2: 異常 (大幅度跳變但無證據)
    # 預設 CONSISTENCY_JUMP_THRESHOLD 通常是 15
    dim_res_jump = {"score": 90, "llm_score": 90, "tool_score": 90, "findings": []}
    res_jump = verify.self_consistency_gate(dim_res_jump, "linting", 10, 0)
    assert res_jump["flagged"] is True
    assert "jumped" in res_jump["reason"]

def test_score_crg_adjustments():
    scores = {"architecture": {"score": 100}}
    crg_metrics = {"community_cohesion": {"score": 30}}
    
    score._apply_crg_subscores(scores, crg_metrics)
    assert scores["architecture"]["score"] == 30

def test_verify_load_result(tmp_path):
    res_file = tmp_path / "res.json"
    data = {"dimension": "test", "score": 100}
    res_file.write_text(json.dumps(data))
    
    loaded = verify.load_result(str(res_file))
    assert loaded["score"] == 100
