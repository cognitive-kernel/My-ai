from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"MYAI-ENC-1\n"
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1

def _key(password: str, salt: bytes) -> bytes:
    if not password or len(password) < 12:
        raise ValueError("Encryption password must contain at least 12 characters.")
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_SIZE)

def encrypt_bytes(data: bytes, password: str) -> bytes:
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _key(password, salt)
    header = {"v": 1, "kdf": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P}
    aad = json.dumps(header, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, data, aad)
    envelope = {**header, "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode(), "data": base64.b64encode(ciphertext).decode()}
    return MAGIC + json.dumps(envelope, separators=(",", ":")).encode("utf-8")

def decrypt_bytes(blob: bytes, password: str) -> bytes:
    if not blob.startswith(MAGIC):
        raise ValueError("Not a My-AI encrypted backup.")
    envelope = json.loads(blob[len(MAGIC):].decode("utf-8"))
    salt = base64.b64decode(envelope["salt"])
    nonce = base64.b64decode(envelope["nonce"])
    header = {k: envelope[k] for k in ("v", "kdf", "n", "r", "p")}
    aad = json.dumps(header, separators=(",", ":")).encode("utf-8")
    key = _key(password, salt)
    return AESGCM(key).decrypt(nonce, base64.b64decode(envelope["data"]), aad)

def encrypt_file(source: str | Path, destination: str | Path, password: str) -> str:
    data = Path(source).read_bytes()
    dst = Path(destination).expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(encrypt_bytes(data, password))
    return str(dst)

def decrypt_file(source: str | Path, destination: str | Path, password: str) -> str:
    data = decrypt_bytes(Path(source).expanduser().read_bytes(), password)
    dst = Path(destination).expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return str(dst)
