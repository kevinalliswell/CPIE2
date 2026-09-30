"""Exercise production Qt controls, not a copied version of their logic."""
import pytest
from models.experiment_states import IgnitionExperimentState as State
from views.widgets.ignition.control_panel import ControlPanelWidget


class TestButtonStates:
    @pytest.mark.parametrize('state, connect, new, start, finalize, text', [
        (State.IDLE, True, False, False, False, '启动实验'),
        (State.CONNECTED, False, True, False, False, '启动实验'),
        (State.PREPARED, False, False, True, False, '启动实验'),
        (State.RUNNING, False, False, True, True, '停止实验'),
        (State.STOPPED, False, False, False, True, '启动实验'),
        (State.COMPLETED, False, True, False, False, '启动实验'),
    ])
    def test_state(self, qapp, state, connect, new, start, finalize, text):
        panel = ControlPanelWidget()
        try:
            panel.update_button_states(state)
            assert panel.btn_connect.isEnabled() is connect
            assert panel.btn_new_experiment.isEnabled() is new
            assert panel.btn_start.isEnabled() is start
            assert panel.btn_finalize.isEnabled() is finalize
            assert panel.btn_start.text() == text
            assert panel.btn_start.objectName() == ('dangerButton' if state == State.RUNNING else 'successButton')
        finally:
            panel.close()
            panel.deleteLater()
