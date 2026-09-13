from pathlib import Path
import argparse
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / 'src'
for path in (PROJECT_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def configure_console_streams():
    """Keep dependency output usable in frozen Windows and windowless starts.

    Frozen Python may ignore PYTHONIOENCODING. Qt's runtime hook can also
    replace absent console streams with locale-encoded handles to devnull.
    Configure them before importing code that prints Chinese diagnostics.
    """
    for name in ('stdout', 'stderr'):
        stream = getattr(sys, name, None)
        if stream is None:
            setattr(sys, name, open(os.devnull, 'w', encoding='utf-8', errors='backslashreplace'))
        elif hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')


def recover_interrupted_sessions(window):
    """Recover once, after the application lock and controller initialization."""
    recovered = {}
    for index, name in ((1, 'explosion'), (2, 'ignition')):
        database = window.stacked_widget.widget(index).controller.db
        recovered[name] = database.recover_interrupted_sessions()
    if any(recovered.values()):
        window.logger.warning('已恢复中断实验会话: %s', recovered)
        window.stacked_widget.widget(3).load_experiments()
    return recovered


def main() -> int:
    configure_console_streams()
    if '--smoke-test' in sys.argv:
        parser = argparse.ArgumentParser(description='Isolated, hardware-free startup verification')
        parser.add_argument('--smoke-test', action='store_true')
        parser.add_argument('--smoke-output', required=True)
        options = parser.parse_args()
        from scripts.smoke_check import application_smoke
        return application_smoke(options.smoke_output)

    from PySide6.QtWidgets import QApplication
    from src.utils.single_instance import SingleInstance
    from src.utils.tools import Tools
    from src.views.main_window import MainWindow

    app = QApplication(sys.argv)
    single_instance = SingleInstance('CPIE')
    if not single_instance.try_lock():
        SingleInstance.show_already_running_message()
        return 0
    try:
        Tools.apply_stylesheet('dark')
        window = MainWindow()
        recover_interrupted_sessions(window)
        window.show()
        return app.exec()
    finally:
        single_instance.unlock()


if __name__ == '__main__':
    sys.exit(main())
