from scripts import verify, score, config_loader, report_gen
from pathlib import Path

def test_verify_logic():
    # 測試驗證邏輯
    assert verify.count_diff_lines("file | 10 +") == 10

def test_score_logic():
    # 測試評分邏輯
    config = {"dimensions": {"linting": {"enabled": True, "weight": 1.0, "target": 90}}}
    res = score.compute_overall_score({"linting": {"score": 100}}, config)
    assert res["overall_score"] == 100.0

def test_config_loader_defaults():
    # 測試預設配置
    config = {"dimensions": {"linting": {"enabled": True, "weight": 0.1}}}
    config_loader.normalize_weights(config)
    assert config["dimensions"]["linting"]["weight"] == 1.0

def test_report_gen_header():
    # 測試報告渲染
    header = report_gen.render_header(Path("test_repo"), 85.5, 85, "pass")
    assert "85.5" in header
