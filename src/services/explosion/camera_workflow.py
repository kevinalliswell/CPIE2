"""Bind camera operations and analysis inputs to one immutable experiment round."""
from pathlib import Path
import threading
import time
import uuid

from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from models.experiment_states import ExplosionExperimentState as State
from .camera_capture import CameraCaptureWorker


class ExplosionCameraWorkflow(QObject):
    controls_changed = Signal()

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.worker = CameraCaptureWorker(self)
        self.worker.finished.connect(self._finished, Qt.QueuedConnection)
        self.controls_changed.connect(self.refresh_controls, Qt.QueuedConnection)
        self.root = Path(page.temp_dir)
        self.context = None
        self.result = None
        self.sequence_complete = False
        self._triggered = False
        self._spray_confirmed = None
        self._lock = threading.Lock()
        self._closing = False
        self.calibration_active = False
        self.preview_window = None
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._show_preview_frame)

    @property
    def busy(self):
        return self.worker.busy

    def available(self):
        return (not self.page._configuration_error and not self._closing and not self.calibration_active
                and not self.busy and self.context is None
                and self.page.flame_analyzer_window is None
                and self.page.controller.current_state not in {State.SEQUENCE_RUNNING, State.WAITING_ANALYSIS})

    def initialize(self):
        if self.available():
            self.worker.initialize(self.page.flame_kit)
            self.refresh_controls()

    def prepare_round(self, session_id, round_number):
        if (not self.available() or not self.page.camera_enabled
                or not self.page.config.get('camera', {}).get('enabled', True)):
            self.page.log_message.emit('✗ 相机未就绪或上一轮尚未处理，不能启动新一轮')
            return False
        with self._lock:
            self.context = (session_id, round_number, uuid.uuid4().hex)
            self.result = None
            self.sequence_complete = False
            self._triggered = False
            self._spray_confirmed = threading.Event()
        return True

    def trigger(self):
        """Direct controller connection: enqueue capture before ON, without QWidget calls."""
        with self._lock:
            controller = self.page.controller
            if (self._closing or self.context is None or self._triggered
                    or controller.current_state != State.SEQUENCE_RUNNING
                    or controller._stop_requested.is_set()
                    or self.context[:2] != (controller.current_session_id, controller.current_round_number)):
                return
            self._triggered = True
            context = self.context
            self._capture(context)

    def manual_capture(self):
        if not self.available() or not self.page.camera_enabled:
            self.page.log_message.emit('✗ 当前不能手动拍摄，请先处理当前轮次或停止预览')
            return False
        return self._capture(('manual', uuid.uuid4().hex))

    def guard_spray(self, phase):
        """Run in the sequence thread; protect the capture window around ON acknowledgement."""
        controller = self.page.controller
        if phase == 'before_spray':
            if self._spray_confirmed is not None and self._spray_confirmed.is_set():
                self.page.log_message.emit('✗ 本轮已执行喷吹，不能重复使用同一次采集证明')
                return False
            deadline = time.monotonic() + controller._control_timeout
            while not self.worker.capture_ready.wait(.01):
                if (self.worker.acquisition_done.is_set() or controller._stop_requested.is_set()
                        or self.context is None or time.monotonic() >= deadline):
                    self.page.log_message.emit('✗ 相机未取得第一帧，禁止喷吹')
                    return False
        with self._lock:
            valid = (self.context is not None and self._triggered and not self._closing
                     and self.context[:2] == (controller.current_session_id, controller.current_round_number)
                     and not controller._stop_requested.is_set()
                     and self.worker.capture_ready.is_set() and not self.worker.acquisition_done.is_set())
            if valid and phase == 'after_spray':
                # The library must also obtain a valid frame from a read that
                # starts after this acknowledgement, or reject the capture.
                self._spray_confirmed.set()
        if not valid:
            self.page.log_message.emit('✗ 喷吹未被有效采集窗口覆盖，本轮无效')
        return valid

    def _capture(self, context):
        settings = self.page.config.get('camera', {})
        directory = self.root / ('capture_' + '_'.join(map(str, context)))
        try:
            started = self.worker.capture(
                self.page.flame_kit, directory, settings.get('capture_duration', 1.0), context,
                max_buffer_mb=settings.get('max_buffer_mb', 256),
                required_after_event=None if context[0] == 'manual' else self._spray_confirmed,
            )
            if not started:
                raise RuntimeError('相机仍有操作未结束')
            self.controls_changed.emit()
            return True
        except Exception as error:
            self.worker.finished.emit({'operation': 'capture', 'context': context,
                                       'success': False, 'error': str(error)})
            return False

    def _finished(self, report):
        # The signal is emitted just before the Python thread returns. Avoid
        # offering another operation until it has actually exited.
        if not self.worker.wait(0):
            QTimer.singleShot(1, lambda: self._finished(report))
            return
        if self._closing:
            return
        operation = report['operation']
        if operation == 'initialize':
            self.page.camera_enabled = report['success']
            self.page.camera_panel.update_camera_status(report['success'])
        elif operation == 'preview':
            self.preview_timer.stop()
            if self.preview_window is not None:
                window, self.preview_window = self.preview_window, None
                window.close()
        elif operation == 'capture':
            context = report['context']
            if context[0] == 'manual':
                # Manual frames are never inputs to an experiment round.
                if report['success']:
                    self.page.log_message.emit(f"✓ 手动拍摄保存 {report['count']} 帧：{report['directory']}")
            elif context != self.context:
                self.refresh_controls()
                return  # Cancelled/old session results cannot advance a new round.
            elif report['success']:
                self.result = report
                self.page.log_message.emit(f"✓ 本轮采集并保存 {report['count']} 帧，采集与落盘总耗时 {report['elapsed']:.3f} 秒")
                self.maybe_analyze()
            else:
                self.page.log_message.emit('✗ 本轮采集失败，保留已有文件并停止实验：' + report.get('error', '未知错误'))
                self.page.controller.stop_experiment()
                self.cancel_round()
        if not report['success'] and operation != 'preview':
            self.page.log_message.emit('✗ 相机操作失败：' + report.get('error', '未知错误'))
        self.refresh_controls()

    def sequence_finished(self):
        self.sequence_complete = True
        self.maybe_analyze()

    def maybe_analyze(self):
        if (self.context is not None and self.sequence_complete and self.result is not None
                and not self.busy and self.page.controller.current_state == State.WAITING_ANALYSIS
                and self.page.flame_analyzer_window is None):
            self.page._analyze_flame()

    def analysis_input(self):
        if (self.context is None or self.result is None or not self.sequence_complete or self.busy
                or self.page.controller.current_state != State.WAITING_ANALYSIS
                or self.context[:2] != (self.page.controller.current_session_id,
                                       self.page.controller.current_round_number)):
            return None
        return self.context, self.result['directory']

    def accepts_analysis(self, context):
        current = self.analysis_input()
        return current is not None and current[0] == context

    def cancel_round(self):
        with self._lock:
            self.worker.cancel()
            self.context = None
            self.result = None
            self.sequence_complete = False
        self.controls_changed.emit()

    def consume_round(self):
        # Called only after the current result is committed to SQLite.
        self.cancel_round()

    def refresh_controls(self):
        page = self.page
        available = self.available()
        page.camera_panel.btn_init_camera.setEnabled(available)
        for button in (page.btn_capture, page.btn_calibrate):
            button.setEnabled(available and page.camera_enabled)
        page.btn_preview.setEnabled((available and page.camera_enabled) or self.preview_window is not None)
        page.btn_preview.setText('停止预览' if self.preview_window is not None else '开始预览')
        page.btn_analyze.setEnabled(self.analysis_input() is not None and page.flame_analyzer_window is None)
        page.btn_start.setEnabled(page.controller.current_state.can_start() and available)

    def toggle_preview(self):
        if self.preview_window is not None:
            self.preview_window.close()
            return
        if not self.available() or not self.page.camera_enabled:
            return
        window = QDialog(self.page)
        window.setWindowTitle('相机预览')
        self.preview_label = QLabel('等待图像', window)
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setAlignment(Qt.AlignCenter)
        QVBoxLayout(window).addWidget(self.preview_label)
        window.finished.connect(lambda _: self.worker.cancel())
        self.preview_window = window
        self.worker.preview(self.page.flame_kit)
        self.preview_timer.start(50)
        window.show()
        self.refresh_controls()

    def _show_preview_frame(self):
        frame = self.worker.latest_frame()
        if frame is None or self.preview_window is None:
            return
        if frame.ndim == 2:
            image_format = QImage.Format_Grayscale8
        else:
            image_format = QImage.Format_BGR888
        image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], image_format).copy()
        self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def prepare_shutdown(self):
        self._closing = True
        self.preview_timer.stop()
        self.cancel_round()
        if self.calibration_active:
            self.page.log_message.emit('请先关闭标定窗口，再重试退出')
            return False
        if not self.worker.wait(0):
            self.page.log_message.emit('相机操作正在结束，请稍后重试退出')
            return False
        if self.preview_window is not None:
            self.preview_window.close()
            self.preview_window = None
        return True
