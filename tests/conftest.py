"""Isolated application paths and a shared Qt application for automated tests."""
import os
import shutil
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLBACKEND', 'Agg')

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    """Constructors must never create/open the developer's experiment database."""
    from src.utils.path_manager import PathManager as QualifiedPaths
    from utils.path_manager import PathManager as LegacyPaths

    root = tmp_path / 'runtime'
    root.mkdir()
    shutil.copytree(PROJECT_ROOT / 'configs', root / 'configs')
    # Resources are read-only inputs. Point directly to the installed source copy.
    for paths in (QualifiedPaths, LegacyPaths):
        monkeypatch.setattr(paths, 'get_project_root', staticmethod(lambda: str(root)))
        monkeypatch.setattr(paths, 'get_resources_path', staticmethod(
            lambda filename=None: str(PROJECT_ROOT / 'resources' / (filename or ''))
        ))
    monkeypatch.chdir(root)
    yield root
