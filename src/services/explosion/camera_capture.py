"""One camera operation at a time, outside the Qt event loop."""
import math
from pathlib import Path
import threading
import time

from PySide6.QtCore import QObject, Signal


class CameraCaptureWorker(QObject):
    finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._cancel = threading.Event()
        self._latest_frame = None
        self._operation_lock = threading.Lock()
        self.capture_ready = threading.Event()
        self.acquisition_done = threading.Event()

    @property
    def busy(self):
        return self._thread is not None and self._thread.is_alive()

    def _start(self, operation, context, function):
        with self._operation_lock:
            return self._start_locked(operation, context, function)

    def _start_locked(self, operation, context, function):
        if self.busy:
            return False
        self._cancel = threading.Event()
        self.capture_ready = threading.Event()
        self.acquisition_done = threading.Event()

        def execute():
            report = {'operation': operation, 'context': context, 'success': False}
            try:
                report.update(function(self._cancel))
                if self._cancel.is_set():
                    raise RuntimeError('相机操作已取消，本次结果不用于实验')
                report['success'] = True
            except Exception as error:
                report['error'] = str(error)
            finally:
                self.acquisition_done.set()
                self.finished.emit(report)

        self._thread = threading.Thread(target=execute, name='CPIE-camera-' + operation, daemon=True)
        self._thread.start()
        return True

    def initialize(self, kit):
        def initialize(cancel):
            if not kit.initialize():
                raise RuntimeError('相机初始化失败')
            return {}
        return self._start('initialize', None, initialize)

    def capture(self, kit, directory, duration, context, *, delay=0.0, max_buffer_mb=256,
                required_after_event=None):
        for value, name in ((duration, '采集时长'), (delay, '触发延时'), (max_buffer_mb, '内存上限')):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(name + '必须为有限数值')
        if duration <= 0 or delay < 0 or max_buffer_mb <= 0:
            raise ValueError('采集时长和内存上限必须为正，触发延时不能为负')

        def capture(cancel):
            root = Path(directory).resolve()
            root.mkdir(parents=True, exist_ok=False)
            if cancel.wait(delay):
                raise RuntimeError('拍摄前已取消')
            started = time.monotonic()
            paths, count = kit.camera.capture_sequence(
                str(root), duration=duration, cancel_event=cancel,
                max_buffer_bytes=int(max_buffer_mb * 1024 * 1024),
                ready_event=self.capture_ready, acquisition_done_event=self.acquisition_done,
                required_after_event=required_after_event,
            )
            if count <= 0 or count != len(paths):
                raise RuntimeError('采集帧数与保存文件数不一致，不能用于分析')
            resolved = [Path(path).resolve() for path in paths]
            if len(set(resolved)) != count:
                raise RuntimeError('采集结果包含重复文件')
            for path in resolved:
                path.relative_to(root)
                if not path.is_file() or path.stat().st_size == 0:
                    raise RuntimeError('采集文件缺失或为空：' + path.name)
            return {'directory': str(root), 'paths': [str(path) for path in resolved],
                    'count': count, 'elapsed': time.monotonic() - started}

        return self._start('capture', context, capture)

    def preview(self, kit):
        self._latest_frame = None

        def preview(cancel):
            while not cancel.is_set():
                frame = kit.camera.capture_single_frame()
                if frame is not None:
                    self._latest_frame = frame.copy()
                cancel.wait(1 / 30)
            return {}
        return self._start('preview', None, preview)

    def latest_frame(self):
        return self._latest_frame

    def cancel(self):
        self._cancel.set()

    def wait(self, timeout=0):
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout)
        return not self.busy
