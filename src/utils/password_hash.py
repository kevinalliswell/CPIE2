#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口令哈希工具

统一使用带随机盐的 PBKDF2-HMAC-SHA256，存储格式：
    pbkdf2_sha256$<iterations>$<salt_b64>$<digest_b64>

`verify_password` 同时兼容旧版本的明文存储（不以 pbkdf2_sha256$ 开头的值按明文比较），
调用方可据此在验证成功后升级为哈希存储。
"""

import base64
import hashlib
import hmac
import os

HASH_PREFIX = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 200_000


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS, salt: bytes = None) -> str:
    """生成口令哈希字符串（每次调用使用新的随机盐）"""
    if password is None:
        raise ValueError("password must not be None")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return "$".join([
        HASH_PREFIX,
        str(int(iterations)),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ])


def is_hashed(stored: str) -> bool:
    """判断存储值是否已经是哈希格式"""
    return isinstance(stored, str) and stored.startswith(HASH_PREFIX + "$")


def verify_password(password: str, stored: str) -> bool:
    """
    校验口令。

    stored 为哈希格式时按 PBKDF2 校验；否则视为旧版明文，做常量时间比较。
    """
    if password is None or stored is None:
        return False
    if is_hashed(stored):
        try:
            _, iterations, salt_b64, digest_b64 = stored.split("$", 3)
            iterations = int(iterations)
            if not 1 <= iterations <= 1_000_000:
                return False
            salt = base64.b64decode(salt_b64, validate=True)
            expected = base64.b64decode(digest_b64, validate=True)
            if len(salt) != 16 or len(expected) != 32:
                return False
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)
    return hmac.compare_digest(str(stored).encode("utf-8"), password.encode("utf-8"))
