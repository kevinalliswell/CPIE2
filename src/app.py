from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from src.utils.single_instance import SingleInstance
from src.utils.tools import Tools
from src.views.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    # 单实例检测
    single_instance = SingleInstance("CPIE")

    if not single_instance.try_lock():
        SingleInstance.show_already_running_message()
        return 0

    try:
        Tools.apply_stylesheet("dark")

        window = MainWindow()
        window.show()
        return app.exec()
    finally:
        single_instance.unlock()


if __name__ == "__main__":
    sys.exit(main())
