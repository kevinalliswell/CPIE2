"""
口令存储安全性测试

- utils.password_hash: PBKDF2 哈希/校验，兼容旧版明文
- utils.password_manager.PasswordManager: 管理员口令（删除记录确认）哈希存储、明文配置自动升级、修改口令
- models.user_manager.UserManager: 登录用户口令哈希入库、旧版明文行登录后升级、修改口令
- views.dialogs.password_confirm_dialog.PasswordConfirmDialog: 通过 PasswordManager 校验
"""

import json
import sqlite3

import pytest

from utils.password_hash import hash_password, is_hashed, verify_password


# ---------------------------------------------------------------- password_hash
def test_hash_is_salted_and_verifies():
    h1 = hash_password("secret")
    h2 = hash_password("secret")

    assert is_hashed(h1) and is_hashed(h2)
    assert h1 != h2  # 随机盐
    assert verify_password("secret", h1)
    assert verify_password("secret", h2)
    assert not verify_password("Secret", h1)
    assert not verify_password("", h1)


def test_verify_accepts_legacy_plaintext_and_rejects_garbage():
    assert not is_hashed("1952")
    assert verify_password("1952", "1952")
    assert not verify_password("1953", "1952")
    assert not verify_password("x", None)
    assert not verify_password(None, "x")
    assert not verify_password("x", "pbkdf2_sha256$notanumber$!!$??")


# ---------------------------------------------------------------- PasswordManager
@pytest.fixture
def password_manager_cls():
    from utils.password_manager import PasswordManager

    return PasswordManager


def test_password_manager_defaults_and_change(tmp_path, password_manager_cls):
    config_file = tmp_path / "password_config.json"
    manager = password_manager_cls(config_file=str(config_file))

    assert manager.verify_password(password_manager_cls.DEFAULT_PASSWORD)
    assert manager.is_default_password()
    assert not manager.verify_password("wrong")

    assert not manager.change_password("wrong", "abcdef")
    assert not manager.change_password(password_manager_cls.DEFAULT_PASSWORD, "ab")  # 太短
    assert manager.change_password(password_manager_cls.DEFAULT_PASSWORD, "abcdef")

    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert set(saved) == {"admin_password_hash"}
    assert is_hashed(saved["admin_password_hash"])
    assert "abcdef" not in config_file.read_text(encoding="utf-8")

    reloaded = password_manager_cls(config_file=str(config_file))
    assert reloaded.verify_password("abcdef")
    assert not reloaded.verify_password(password_manager_cls.DEFAULT_PASSWORD)
    assert not reloaded.is_default_password()


def test_password_manager_upgrades_legacy_plaintext(tmp_path, password_manager_cls):
    config_file = tmp_path / "password_config.json"
    config_file.write_text(json.dumps({"admin_password": "oldpass"}), encoding="utf-8")

    manager = password_manager_cls(config_file=str(config_file))

    assert manager.verify_password("oldpass")
    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert "admin_password" not in saved
    assert is_hashed(saved["admin_password_hash"])


def test_password_manager_survives_corrupt_config(tmp_path, password_manager_cls):
    config_file = tmp_path / "password_config.json"
    config_file.write_text("{not json", encoding="utf-8")

    manager = password_manager_cls(config_file=str(config_file))

    assert not manager.verify_password(password_manager_cls.DEFAULT_PASSWORD)


@pytest.mark.parametrize('config', [{}, {'admin_password_hash': 'invalid'}, {'admin_password_hash': 'pbkdf2_sha256$broken', 'admin_password': '1952'}])
def test_invalid_existing_config_never_enables_default(tmp_path, password_manager_cls, config):
    config_file = tmp_path / 'password.json'
    config_file.write_text(json.dumps(config))
    assert not password_manager_cls(str(config_file)).verify_password('1952')


def test_failed_password_save_does_not_change_active_password(tmp_path, password_manager_cls, monkeypatch):
    import os
    config_file = tmp_path / 'password.json'
    manager = password_manager_cls(str(config_file))
    assert manager.change_password('1952', 'first-secret')
    saved = config_file.read_bytes()
    def fail_replace(*args):
        raise OSError('simulated read-only destination')
    monkeypatch.setattr(os, 'replace', fail_replace)
    assert not manager.change_password('first-secret', 'second-secret')
    assert config_file.read_bytes() == saved
    assert manager.verify_password('first-secret')
    assert not manager.verify_password('second-secret')


# ---------------------------------------------------------------- UserManager
@pytest.fixture
def user_manager(tmp_path):
    from models.user_manager import UserManager

    manager = UserManager(db_path=str(tmp_path / "users.db"))
    yield manager
    manager.set_current_user(None)
    manager.close()


def _stored_password(db_path, username):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        ).fetchone()[0]


def test_default_users_are_stored_hashed(user_manager):
    for username, password, role in user_manager.DEFAULT_USERS:
        stored = _stored_password(user_manager.db_path, username)
        assert is_hashed(stored)
        assert password not in stored

        user = user_manager.authenticate(username, password)
        assert user is not None and user.role == role
        assert user_manager.authenticate(username, password + "x") is None
    assert user_manager.authenticate("nobody", "admin123") is None


def test_legacy_plaintext_row_is_upgraded_on_login(user_manager):
    with sqlite3.connect(user_manager.db_path) as conn:
        conn.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            ("legacy", "plain123", "experimenter", "2024-01-01 00:00:00"),
        )

    assert user_manager.authenticate("legacy", "wrong") is None
    assert _stored_password(user_manager.db_path, "legacy") == "plain123"

    user = user_manager.authenticate("legacy", "plain123")

    assert user is not None and user.is_experimenter()
    upgraded = _stored_password(user_manager.db_path, "legacy")
    assert is_hashed(upgraded)
    assert user_manager.authenticate("legacy", "plain123") is not None


def test_change_password_rehashes(user_manager):
    assert not user_manager.change_password("admin", "wrong", "newpass1")
    assert not user_manager.change_password("admin", "admin123", "")
    assert not user_manager.change_password("ghost", "admin123", "newpass1")

    before = _stored_password(user_manager.db_path, "admin")
    assert user_manager.change_password("admin", "admin123", "newpass1")
    after = _stored_password(user_manager.db_path, "admin")

    assert after != before and is_hashed(after)
    assert user_manager.authenticate("admin", "admin123") is None
    assert user_manager.authenticate("admin", "newpass1") is not None


# ---------------------------------------------------------------- PasswordConfirmDialog
def test_password_confirm_dialog_uses_password_manager(qapp, tmp_path, password_manager_cls):
    from PySide6.QtWidgets import QDialog

    from views.dialogs.password_confirm_dialog import PasswordConfirmDialog

    manager = password_manager_cls(config_file=str(tmp_path / "password_config.json"))
    assert manager.change_password(password_manager_cls.DEFAULT_PASSWORD, "dialog-pass")

    dialog = PasswordConfirmDialog(password_manager=manager)
    try:
        dialog.on_confirm_clicked()  # 空口令
        assert dialog.error_label.isVisibleTo(dialog)
        assert dialog.result() != QDialog.DialogCode.Accepted

        dialog.password_input.setText(password_manager_cls.DEFAULT_PASSWORD)  # 已修改，默认口令不再有效
        dialog.on_confirm_clicked()
        assert dialog.error_label.isVisibleTo(dialog)
        assert dialog.password_input.text() == ""
        assert dialog.result() != QDialog.DialogCode.Accepted

        dialog.password_input.setText("dialog-pass")
        dialog.on_confirm_clicked()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert not dialog.error_label.isVisibleTo(dialog)
    finally:
        dialog.close()
        dialog.deleteLater()
