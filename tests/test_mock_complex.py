import pytest
from unittest.mock import MagicMock, patch
from scripts import report_gen, checkpoint
from pathlib import Path
import json

def test_report_gen_evidence_with_git_mock():
    # 模擬 git log 輸出
    with patch("subprocess.check_output") as mock_git:
        mock_git.return_value = b"fa9eac7 chore: mock testing\n2308f1e chore: cleanup"
        evidence = report_gen.render_evidence(Path("."), [{"round": 1, "dir": "round_1", "source": "result.json"}])
        assert "fa9eac7" in evidence
        assert "Recent Commits" in evidence

def test_checkpoint_final_report_aggregation(tmp_path):
    # 模擬多輪數據聚合邏輯
    work_dir = tmp_path / "work"
    round_dir = work_dir / "round_1"
    round_dir.mkdir(parents=True)
    
    # 建立符合 report_gen 期望的 result.json
    res_data = {"overall_score": 85.5, "dimensions": {}}
    (round_dir / "result.json").write_text(json.dumps(res_data))
    
    # 測試 load_round_scores 是否能正確找到數據
    rounds = report_gen.load_round_scores(work_dir)
    assert len(rounds) == 1
    assert rounds[0]["data"]["overall_score"] == 85.5

def test_checkpoint_save_mechanism(tmp_path):
    # 測試 checkpoint 的磁碟寫入邏輯
    with patch("scripts.checkpoint.create_round_snapshot") as mock_snap:
        mock_snap.return_value = {"round": 1}
        # 這裡測試 save_round_checkpoint 函式
        # 需先確認該函式的正確參數 (round_num, scores, overall_score, work_dir, repo_path)
        pass # 待進一步精確 Mock
