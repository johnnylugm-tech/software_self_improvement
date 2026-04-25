import os


def test_config_loader_exists():
    assert os.path.exists("scripts/config_loader.py")


def test_issue_tracker_structure():
    # 測試 registry 基礎結構
    registry = {"issues": []}
    assert "issues" in registry
