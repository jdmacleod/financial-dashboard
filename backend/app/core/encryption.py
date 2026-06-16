import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_key = base64.b64decode(settings.secret_encryption_key)


def encrypt(plaintext: str) -> bytes:
    nonce = os.urandom(12)
    ct = AESGCM(_key).encrypt(nonce, plaintext.encode(), None)
    return nonce + ct  # prepend nonce; stored as BYTEA


def decrypt(ciphertext: bytes) -> str:
    nonce, ct = ciphertext[:12], ciphertext[12:]
    return AESGCM(_key).decrypt(nonce, ct, None).decode()
