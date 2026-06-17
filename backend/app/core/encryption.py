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


def encrypt_file(src: "os.PathLike[str]", dst: "os.PathLike[str]") -> None:
    """Encrypt a file using AES-256-GCM. Writes nonce + ciphertext to dst."""
    import pathlib

    data = pathlib.Path(src).read_bytes()
    nonce = os.urandom(12)
    ct = AESGCM(_key).encrypt(nonce, data, None)
    pathlib.Path(dst).write_bytes(nonce + ct)


def decrypt_file_to_devnull(src: "os.PathLike[str]") -> None:
    """Verify an encrypted file by decrypting it. Raises on authentication failure."""
    import pathlib

    data = pathlib.Path(src).read_bytes()
    nonce, ct = data[:12], data[12:]
    AESGCM(_key).decrypt(nonce, ct, None)  # raises InvalidTag on corruption
