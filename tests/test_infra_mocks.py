import pytest
from unittest.mock import MagicMock, patch
from scripts import setup_target, verify_tools
from pathlib import Path
import sys

def test_setup_target_mock_resolve():
    # 全面 mock Path.exists
    with patch.object(Path, "exists") as mock_exists:
        mock_exists.return_value = True
        # 由於 resolve_target 內部會再次 Path() 化，我們必須確保邏輯連貫
        res = setup_target.resolve_target("/fake/path")
        assert "/fake/path" in str(res)

def test_verify_tools_check_tools():
    # 模擬工具掃描
    test_tools = {"python3": ("python3", "test")}
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/python3"
        results = verify_tools.check_tools(test_tools, "core")
        # 根據源碼，應存取 ["tools"]["python3"]
        assert results["tools"]["python3"]["installed"] is True

def test_verify_tools_missing():
    test_tools = {"eslint": ("eslint", "test")}
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        results = verify_tools.check_tools(test_tools, "core")
        assert results["tools"]["eslint"]["installed"] is False
