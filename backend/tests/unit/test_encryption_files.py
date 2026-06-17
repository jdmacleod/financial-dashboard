"""Unit tests for encrypt_file / decrypt_file_to_devnull."""

from __future__ import annotations

import pathlib

import pytest

from app.core import encryption


def test_encrypt_file_produces_encrypted_file(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "input.txt"
    dst = tmp_path / "output.enc"
    src.write_bytes(b"hello world")

    encryption.encrypt_file(str(src), str(dst))

    assert dst.exists()
    assert dst.read_bytes() != b"hello world"
    assert len(dst.read_bytes()) > 12  # nonce + ciphertext


def test_decrypt_file_to_devnull_accepts_valid_file(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "input.bin"
    enc = tmp_path / "output.enc"
    src.write_bytes(b"sensitive data")

    encryption.encrypt_file(str(src), str(enc))
    # Should not raise
    encryption.decrypt_file_to_devnull(str(enc))


def test_decrypt_file_to_devnull_raises_on_tampered_file(tmp_path: pathlib.Path) -> None:
    from cryptography.exceptions import InvalidTag

    src = tmp_path / "input.bin"
    enc = tmp_path / "tampered.enc"
    src.write_bytes(b"data")

    encryption.encrypt_file(str(src), str(enc))
    data = enc.read_bytes()
    # Flip a byte in the ciphertext
    tampered = data[:-1] + bytes([data[-1] ^ 0xFF])
    enc.write_bytes(tampered)

    with pytest.raises(InvalidTag):
        encryption.decrypt_file_to_devnull(str(enc))
