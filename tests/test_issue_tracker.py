import pytest
import json
from scripts import issue_tracker


def test_issue_tracker_workflow():
    # 建立臨時 registry
    reg = {"issues": []}

    # 測試新增 finding
    finding = {
        "severity": "HIGH",
        "message": "Test message",
        "evidence": "Test evidence",
    }
    # 正確順序: (registry, finding, dimension, round_num)
    issue_id = issue_tracker.add_finding(reg, finding, "test_dim", 1)

    assert len(reg["issues"]) == 1
    assert reg["issues"][0]["dimension"] == "test_dim"
    assert reg["issues"][0]["id"] == issue_id

    # 測試標記固定
    # 正確順序: (registry, issue_id, round_num, resolution_note)
    issue_tracker.mark_fixed(reg, issue_id, 2, "Fixed it")
    assert reg["issues"][0]["status"] == "fixed"
    assert reg["issues"][0]["round_resolved"] == 2
