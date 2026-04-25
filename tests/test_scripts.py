from scripts import checkpoint, config_loader, score


def test_checkpoint_logic():
    # 測試 snapshot 建立
    res = checkpoint.create_round_snapshot(1, {"linting": 100}, 80.5)
    assert res["round"] == 1
    assert res["overall_score"] == 80.5
    assert "dimensions" in res


def test_config_loader_validation():
    # 測試配置驗證
    config = {
        "dimensions": {
            "linting": {"enabled": True, "weight": 0.5},
            "security": {"enabled": False, "weight": 0.5},
        }
    }
    config_loader.normalize_weights(config)
    # 原地修改
    assert config["dimensions"]["linting"]["weight"] == 1.0


def test_score_calculation():
    # 測試評分權重計算
    config = {"dimensions": {"linting": {"enabled": True, "weight": 1.0, "target": 90}}}
    scores = {"linting": {"score": 100}}
    summary = score.compute_overall_score(scores, config)
    assert summary["overall_score"] == 100.0
    assert summary["meets_target"] is True
