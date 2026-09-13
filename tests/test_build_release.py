"""Release safety checks without invoking PyInstaller or touching real artifacts."""
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from build_release import CPIEBuilder


@pytest.fixture
def builder(tmp_path):
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'configs/software.info').write_text(json.dumps({'name': 'CPIE', 'version': '1.2.1'}))
    instance = CPIEBuilder()
    instance.project_root = tmp_path
    instance.src_dir = tmp_path / 'src'
    instance.dist_dir = tmp_path / 'dist'
    instance.build_dir = tmp_path / 'build'
    instance.release_dir = tmp_path / 'release'
    instance.local_packages = {}
    instance.platform = 'windows'
    instance.app_version = '1.2.1'
    return instance


def test_failed_verification_never_creates_a_release(builder, monkeypatch):
    for name in ('_check_app_icons', 'check_local_packages', 'check_dependencies', 'clean_build',
                 'build_application', 'copy_additional_files', 'create_installer_script'):
        monkeypatch.setattr(builder, name, Mock(return_value=True))
    monkeypatch.setattr(builder, 'create_spec_file', Mock(return_value=Path('CPIE.spec')))
    monkeypatch.setattr(builder, 'verify_build', Mock(return_value=False))
    package = Mock(return_value=Path(__file__))
    monkeypatch.setattr(builder, 'create_release_package', package)
    assert builder.build() is False
    package.assert_not_called()


def test_debug_is_configured_in_spec_not_unsupported_cli_option(builder, monkeypatch):
    spec = builder.create_spec_file(debug=True)
    text = spec.read_text()
    assert 'console=True' in text
    assert 'debug=True' in text
    run = Mock()
    monkeypatch.setattr('build_release.subprocess.run', run)
    assert builder.build_application(spec, debug=True)
    assert not any(arg.startswith('--debug') for arg in run.call_args.args[0])
    assert 'collect_data_files("flamekit"' in text
    assert 'openpyxl' in text


def test_installer_is_per_user_and_keeps_existing_data_and_config(builder):
    builder.dist_dir.mkdir()
    builder.create_installer_script()
    text = (builder.dist_dir / 'install.bat').read_text()
    assert '%LOCALAPPDATA%\\Programs\\CPIE' in text
    assert '%PROGRAMFILES%' not in text
    assert '%~dp0CPIE' in text
    assert '/XD configs data logs exports' in text
    assert '/XC /XN /XO' in text
    assert 'if errorlevel 8 exit /b 1' in text


def test_release_checksum_and_dependency_inventory_match_archive(builder, monkeypatch):
    app_dir = builder.dist_dir / builder.app_name
    app_dir.mkdir(parents=True)
    (app_dir / 'CPIE.exe').write_bytes(b'test executable')
    monkeypatch.setattr(builder, 'get_build_metadata', lambda: {
        'app_version': '1.2.1', 'source_commit': 'a' * 40,
        'dependencies': {'flamekit': '1.1.2', 'pymodbus': '3.8.6'},
    })
    archive = builder.create_release_package()
    info = json.loads(archive.with_name(archive.stem + '_info.json').read_text())
    assert info['source_commit'] == 'a' * 40
    assert info['dependencies']['pymodbus'] == '3.8.6'
    assert info['package_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive.with_suffix('.zip.sha256').read_text().split()[0] == info['package_sha256']
