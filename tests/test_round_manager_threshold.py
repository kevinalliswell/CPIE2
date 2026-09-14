"""
RoundManager 阶段判定阈值测试

test-rounds.phase-decision-threshold 决定"前 N 轮平均火焰长度是否需要进入第二阶段"，
未配置时沿用 explosion-thresholds.no-explosion。
"""

from services.explosion.round_manager import RoundManager

BASE_CONFIG = {
    "test-rounds": {"max-rounds": 10, "phase-rounds": 5, "phase-decision-threshold": 20.0},
    "explosion-thresholds": {"no-explosion": 25.0, "weak-explosion": 400.0, "strong-explosion": 800.0},
}


def _records(*lengths):
    return [{"round": i + 1, "flame_length": length} for i, length in enumerate(lengths)]


def test_phase_threshold_read_from_config():
    manager = RoundManager(BASE_CONFIG)

    assert manager.phase_decision_threshold == 20.0
    assert manager.threshold_no_explosion == 25.0


def test_phase_threshold_falls_back_to_no_explosion_threshold():
    config = {
        "test-rounds": {"max-rounds": 10, "phase-rounds": 5},
        "explosion-thresholds": {"no-explosion": 25.0},
    }
    assert RoundManager(config).phase_decision_threshold == 25.0

    config["test-rounds"]["phase-decision-threshold"] = "not-a-number"
    assert RoundManager(config).phase_decision_threshold == 25.0


def test_should_continue_phase2_uses_phase_threshold():
    manager = RoundManager(BASE_CONFIG)

    # 平均 22 mm：高于 20 mm 判定阈值（但低于 25 mm 无爆炸性上限）→ 不需要第二阶段
    need_phase2, reason = manager.should_continue_phase2(_records(22, 22, 22, 22, 22))
    assert need_phase2 is False
    assert "20" in reason

    need_phase2, reason = manager.should_continue_phase2(_records(10, 15, 20, 25, 25))
    assert need_phase2 is True
    assert "20" in reason

    assert manager.should_continue_phase2(_records(10, 10)) == (False, "未完成第一阶段")


def test_get_next_action_uses_phase_threshold():
    manager = RoundManager(BASE_CONFIG)

    action = manager.get_next_action(5, _records(22, 22, 22, 22, 22))
    assert action["action"] == "complete"
    assert action["meets_standard"] is True

    action = manager.get_next_action(5, _records(10, 10, 10, 10, 10))
    assert action["action"] == "phase2"
    assert action["meets_standard"] is False
    assert "20mm" in action["message"]

    assert manager.get_next_action(3, _records(10, 10, 10))["action"] == "continue"
    assert manager.get_next_action(10, _records(*([10] * 10)))["action"] == "complete"
