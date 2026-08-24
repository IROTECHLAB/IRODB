"""Authenticated page encryption for IRODB.

The preferred backend is PyCryptodome's AES-GCM implementation because it does
not require Rust. A cryptography AESGCM fallback remains available for existing
installations. Both backends emit the same nonce + ciphertext + 16-byte tag
layout, so the IRODB page format remains compatible.
"""
from __future__ import annotations

import hashlib
import os
import struct
from typing import Union

MAGIC = b"ENC1"
NONCE_SIZE = 12
SALT_SIZE = 16
KEY_SIZE = 32
TAG_SIZE = 16

_BACKEND = None
_BACKEND_ERROR = None
try:
    from Crypto.Cipher import AES as _CryptoAES
    _BACKEND = "pycryptodome"
except ImportError as crypto_exc:  # pragma: no cover - depends on environment
    _CryptoAES = None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
        _BACKEND = "cryptography"
    except ImportError as cryptography_exc:  # pragma: no cover - depends on environment
        _AESGCM = None
        _BACKEND_ERROR = (crypto_exc, cryptography_exc)


def backend_name() -> str:
    """Return the active authenticated-encryption backend name."""
    return _BACKEND or "unavailable"


def _require_backend() -> None:
    if _BACKEND is None:
        raise RuntimeError(
            "encrypted IRODB databases require 'pycryptodome' "
            "(recommended, no Rust) or the legacy 'cryptography' package"
        ) from (_BACKEND_ERROR[0] if _BACKEND_ERROR else None)


def derive_key(secret: Union[str, bytes], salt: bytes) -> bytes:
    """Derive a 256-bit AES key from a passphrase or accept a raw 32-byte key."""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
        return hashlib.scrypt(secret, salt=salt, n=2**14, r=8, p=1, dklen=KEY_SIZE)
    if isinstance(secret, bytes) and len(secret) == KEY_SIZE:
        return secret
    raise ValueError("encryption key must be a passphrase or exactly 32 raw bytes")


def _aad(page_number: int, version: int) -> bytes:
    return struct.pack("<HQ", version, page_number)


def _encrypt_gcm(plaintext: bytes, key: bytes, nonce: bytes, aad: bytes) -> bytes:
    if _BACKEND == "pycryptodome":
        cipher = _CryptoAES.new(key, _CryptoAES.MODE_GCM, nonce=nonce, mac_len=TAG_SIZE)
        cipher.update(aad)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return ciphertext + tag
    return _AESGCM(key).encrypt(nonce, plaintext, aad)


def _decrypt_gcm(ciphertext_and_tag: bytes, key: bytes, nonce: bytes, aad: bytes) -> bytes:
    if len(ciphertext_and_tag) < TAG_SIZE:
        raise ValueError("encrypted IRODB page is missing its authentication tag")
    if _BACKEND == "pycryptodome":
        ciphertext = ciphertext_and_tag[:-TAG_SIZE]
        tag = ciphertext_and_tag[-TAG_SIZE:]
        cipher = _CryptoAES.new(key, _CryptoAES.MODE_GCM, nonce=nonce, mac_len=TAG_SIZE)
        cipher.update(aad)
        plaintext = cipher.decrypt(ciphertext)
        cipher.verify(tag)
        return plaintext
    return _AESGCM(key).decrypt(nonce, ciphertext_and_tag, aad)


def encrypt_page(plaintext: bytes, key: bytes, page_number: int, version: int) -> bytes:
    _require_backend()
    nonce = os.urandom(NONCE_SIZE)
    body = nonce + _encrypt_gcm(plaintext, key, nonce, _aad(page_number, version))
    return MAGIC + struct.pack("<Q", len(body)) + body


def decrypt_page(payload: bytes, key: bytes, page_number: int, version: int) -> bytes:
    _require_backend()
    if len(payload) < len(MAGIC) + 8 + NONCE_SIZE + TAG_SIZE or payload[:4] != MAGIC:
        raise ValueError("invalid encrypted IRODB page")
    body_size = struct.unpack_from("<Q", payload, 4)[0]
    body_start = 12
    body_end = body_start + body_size
    if body_end > len(payload) or any(payload[body_end:]):
        raise ValueError("invalid encrypted IRODB page length")
    body = payload[body_start:body_end]
    nonce = body[:NONCE_SIZE]
    ciphertext_and_tag = body[NONCE_SIZE:]
    try:
        return _decrypt_gcm(ciphertext_and_tag, key, nonce, _aad(page_number, version))
    except Exception as exc:
        raise ValueError("IRODB page authentication failed; wrong key or corrupted data") from exc
